//! The writer thread both engines send through: a bounded queue of frames, one thread that
//! writes them with the rate limiter and feeds the compression policy, and the `FrameTx`
//! handle producers use. `send` never waits; `send_bounded` waits while `MAX_QUEUED` is full.

use std::collections::VecDeque;
use std::io::{self, BufWriter, Write};
use std::sync::{Arc, Condvar, Mutex, OnceLock};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use xs_wire::io_control::IoControl;

use crate::compression::{CompressionLink, Transport};
use crate::protocol::{frame_type, msg_kind};

/// Nanoseconds on the same monotonic clock for every compression observation.
fn link_now() -> u64 {
    static START: OnceLock<Instant> = OnceLock::new();
    START.get_or_init(Instant::now).elapsed().as_nanos() as u64
}

/// Write one frame, charging the rate limiter and giving the compression policy what the
/// transport saw. A keep-alive is not charged and does not count as activity.
fn write_observed(
    output: &mut impl Write,
    link: Option<&CompressionLink>,
    control: &IoControl,
    kind: u8,
    payload: &[u8],
    activity: bool,
) -> io::Result<()> {
    let mut header = [0u8; xs_wire::HEADER_LEN];
    header[..4].copy_from_slice(&(payload.len() as u32).to_le_bytes());
    header[4] = kind;
    let total = header.len() + payload.len();
    let started = activity.then(Instant::now);
    // The header and the payload go out as they are, in pieces the rate limiter grants: the
    // buffered writer gathers small frames, and a large payload passes straight through it.
    // Unlimited, a frame is one piece, and one of 256 KiB or more is written without a copy.
    let piece = if activity && control.rate_limit() != 0 { 65536 } else { total };
    let mut written = 0;
    while written < total {
        let wanted = (total - written).min(piece);
        let count = if activity { control.limiter().acquire(wanted) } else { wanted };
        if count == 0 {
            return Err(io::Error::new(io::ErrorKind::TimedOut, "I/O timeout"));
        }
        control.begin_write();
        let end = written + count;
        if written < header.len() {
            output.write_all(&header[written..end.min(header.len())])?;
        }
        if end > header.len() {
            output.write_all(&payload[written.max(header.len()) - header.len()..end - header.len()])?;
        }
        written = end;
        control.note_write(activity);
    }
    if let (Some(started), Some(link)) = (started, link) {
        link.observe(
            total as u64,
            started.elapsed().as_nanos() as u64,
            Transport::Queued,
            link_now(),
            control.rate_limit(),
        );
    }
    Ok(())
}

/// Frames waiting for the writer thread, with the bytes they hold.
#[derive(Default)]
struct Queue {
    frames: VecDeque<(u8, Vec<u8>, bool)>,
    bytes: usize,
    /// No more frames: `finish` was called, or the writer stopped.
    closed: bool,
}

#[derive(Default)]
struct Outbox {
    queue: Mutex<Queue>,
    /// The writer waits here for frames,
    ready: Condvar,
    /// and the sender's threads for room.
    room: Condvar,
}

/// `Conn::MAX_Q` (`remote.cpp:254`): a sender's listings and data wait while this much is queued.
const MAX_QUEUED: usize = 48 << 20;
impl Outbox {
    fn push(&self, kind: u8, payload: Vec<u8>, activity: bool, bounded: bool) -> io::Result<()> {
        let mut queue = self.queue.lock().unwrap();
        while bounded && queue.bytes >= MAX_QUEUED && !queue.closed {
            queue = self.room.wait(queue).unwrap();
        }
        if queue.closed {
            return Err(io::Error::new(io::ErrorKind::BrokenPipe, "the writer thread stopped"));
        }
        queue.bytes += payload.len();
        queue.frames.push_back((kind, payload, activity));
        drop(queue);
        self.ready.notify_one();
        Ok(())
    }

    fn close(&self) {
        self.queue.lock().unwrap().closed = true;
        self.ready.notify_all();
        self.room.notify_all();
    }
}

/// A writer thread and its queue. `send` never waits, so a receiver that answers each
/// listing with a NEED never deadlocks against a sender that is busy writing; the sender's
/// threads write through `FrameTx::send_bounded`, which waits while `MAX_QUEUED` is queued.
pub(super) struct FrameOut<W: Write + Send + 'static> {
    outbox: Arc<Outbox>,
    handle: Option<JoinHandle<io::Result<()>>>,
    _marker: std::marker::PhantomData<W>,
}

/// A handle on a `FrameOut`'s queue that other threads can hold.
#[derive(Clone)]
pub(super) struct FrameTx {
    outbox: Arc<Outbox>,
}

impl FrameTx {
    pub(super) fn send(&self, kind: u8, payload: Vec<u8>) -> io::Result<()> {
        self.outbox.push(kind, payload, true, false)
    }

    pub(super) fn send_bounded(&self, kind: u8, payload: Vec<u8>) -> io::Result<()> {
        self.outbox.push(kind, payload, true, true)
    }

    /// Stop the stream: queued frames are still written, and waiting or later sends fail.
    pub(super) fn close(&self) {
        self.outbox.close();
    }
}

impl<W: Write + Send + 'static> FrameOut<W> {
    pub(super) fn new(output: W, link: Option<Arc<CompressionLink>>, control: Arc<IoControl>) -> Self {
        let outbox = Arc::new(Outbox::default());
        control.set_writer_active(true);
        let worker_control = control.clone();
        let writer_outbox = outbox.clone();
        let handle = std::thread::spawn(move || -> io::Result<()> {
            let outbox = writer_outbox;
            let result = (|| -> io::Result<()> {
                let mut output = BufWriter::with_capacity(256 << 10, output);
                loop {
                    let mut queue = outbox.queue.lock().unwrap();
                    if queue.frames.is_empty() && !queue.closed {
                        queue = outbox.ready.wait_timeout(queue, Duration::from_millis(100)).unwrap().0;
                    }
                    if queue.frames.is_empty() {
                        let closed = queue.closed;
                        drop(queue);
                        if closed {
                            break;
                        }
                        if worker_control.heartbeat_due() {
                            write_observed(&mut output, link.as_deref(), &worker_control, frame_type::KEEPALIVE, &[], false)?;
                            output.flush()?;
                        }
                        if worker_control.timed_out() {
                            return Err(io::Error::new(io::ErrorKind::TimedOut, "I/O timeout"));
                        }
                        continue;
                    }
                    // Take everything queued at once, as `Conn::writer` swaps its queue out.
                    let frames = std::mem::take(&mut queue.frames);
                    queue.bytes = 0;
                    drop(queue);
                    outbox.room.notify_all();
                    for (kind, payload, activity) in frames {
                        write_observed(&mut output, link.as_deref(), &worker_control, kind, &payload, activity)?;
                    }
                    if outbox.queue.lock().unwrap().frames.is_empty() {
                        output.flush()?;
                    }
                }
                output.flush()
            })();
            outbox.close();
            control.set_writer_active(false);
            result
        });
        Self { outbox, handle: Some(handle), _marker: std::marker::PhantomData }
    }

    pub(super) fn tx(&self) -> FrameTx {
        FrameTx { outbox: self.outbox.clone() }
    }

    pub(super) fn send(&mut self, kind: u8, payload: &[u8]) -> io::Result<()> {
        self.send_with(kind, payload, true)
    }

    pub(super) fn send_with(&mut self, kind: u8, payload: &[u8], activity: bool) -> io::Result<()> {
        self.outbox.push(kind, payload.to_vec(), activity, false)
    }

    pub(super) fn finish(mut self) -> io::Result<()> {
        self.outbox.close();
        match self.handle.take().unwrap().join() {
            Ok(result) => result,
            Err(_) => Err(io::Error::other("the writer thread panicked")),
        }
    }
}

impl<W: Write + Send + 'static> Drop for FrameOut<W> {
    fn drop(&mut self) {
        self.outbox.close();
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}

pub(super) fn send_fatal(output: &mut FrameOut<impl Write + Send + 'static>, text: &str) -> io::Result<()> {
    let message = xs_wire::Message { kind: msg_kind::FATAL, code: 2, text: text.to_string() };
    output.send(frame_type::MSG, &message.encode())
}
