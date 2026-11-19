//! Worker budget and the two small pools the transfer engine needs.
//!
//! `-j/--jobs` is the same integer HELLO option as the C++ engine's: zero means
//! the default budget, an explicit value above one also permits splitting one
//! large file into ranges (`fs.cpp:parallel_file_ranges`). The sender reads
//! ranges in parallel and the receiver writes them in parallel; a single file
//! stays serial unless the caller asked for `-jN` with N > 1, as the C++ does.

use std::fs::File;
use std::io;
use std::os::raw::{c_int, c_void};
use std::os::unix::io::AsRawFd;
use std::path::Path;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::ops::Range;
use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::Arc;
use std::thread::JoinHandle;

/// The port's default worker budget when `-j` was not given.
pub const DEFAULT_JOBS: usize = 4;
/// A sender's default workers when `-j` was not given: more than the CPU budget, because a sender
/// mostly waits on opening and reading files. Eight readers read many small files 3-4x faster than
/// one on both Raspberry Pis in the compression study, and sixteen no faster than eight.
pub const DEFAULT_SENDER_JOBS: usize = 8;
/// `MAX_WORKERS` in `src/progress.h`.
pub const MAX_WORKERS: usize = 64;
/// The C++ sender uses this range size for remote transfers (`remote.cpp:1562`).
pub const RANGE_SPAN: u64 = 4 << 20;
/// A file this size or larger may be split across ranges (`fs.cpp:1765`).
pub const RANGE_MIN: u64 = 32 << 20;

/// The sending side's workers: `-j` when given, else `DEFAULT_SENDER_JOBS`.
pub fn sender_jobs(jobs: i64) -> usize {
    if jobs > 0 {
        (jobs as usize).min(MAX_WORKERS)
    } else {
        DEFAULT_SENDER_JOBS
    }
}

pub fn effective_jobs(jobs: i64) -> usize {
    if jobs > 0 {
        (jobs as usize).min(MAX_WORKERS)
    } else {
        DEFAULT_JOBS
    }
}

/// Whether an explicit `-jN` asks for range splitting. The C++ checks the raw
/// `g_opt.jobs <= 1`, so the default (zero) remains file-serial for one file.
pub fn explicit_ranges(jobs: i64) -> bool {
    jobs > 1
}

extern "C" {
    fn pread(fd: c_int, buffer: *mut c_void, count: usize, offset: i64) -> isize;
    fn pwrite(fd: c_int, buffer: *const c_void, count: usize, offset: i64) -> isize;
}

const EINTR: i32 = 4;

fn read_at(file: &File, offset: u64, want: usize) -> io::Result<Vec<u8>> {
    let mut buffer = vec![0u8; want];
    let mut done = 0usize;
    while done < want {
        let count = unsafe {
            pread(
                file.as_raw_fd(),
                buffer[done..].as_mut_ptr().cast(),
                want - done,
                (offset + done as u64) as i64,
            )
        };
        if count < 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error() == Some(EINTR) {
                continue;
            }
            return Err(error);
        }
        if count == 0 {
            break;
        }
        done += count as usize;
    }
    buffer.truncate(done);
    Ok(buffer)
}

/// Read `total` bytes from `path` in `span`-sized ranges using up to `jobs`
/// workers, passing each completed range to `emit` on the calling thread.
/// Returns false if any range came up short; the emitted ranges are padded so
/// the peer sees a complete, well-formed attempt and the END marks failure.
pub fn read_ranges<F>(path: &Path, total: u64, jobs: usize, span: u64, mut emit: F) -> io::Result<bool>
where
    F: FnMut(u64, Vec<u8>) -> io::Result<()>,
{
    if total == 0 {
        return Ok(true);
    }
    let ranges = total.div_ceil(span) as usize;
    let workers = jobs.clamp(1, ranges.max(1));
    let next = AtomicUsize::new(0);
    let (tx, rx) = channel::<(u64, Vec<u8>, bool)>();
    std::thread::scope(|scope| -> io::Result<bool> {
        for _ in 0..workers {
            let tx = tx.clone();
            let next = &next;
            scope.spawn(move || {
                let file = File::open(path);
                loop {
                    let index = next.fetch_add(1, Ordering::Relaxed);
                    if index >= ranges {
                        break;
                    }
                    let offset = index as u64 * span;
                    let want = (total - offset).min(span) as usize;
                    let (mut bytes, complete) = match file.as_ref() {
                        Ok(file) => match read_at(file, offset, want) {
                            Ok(bytes) => {
                                let complete = bytes.len() == want;
                                (bytes, complete)
                            }
                            Err(_) => (Vec::new(), false),
                        },
                        Err(_) => (Vec::new(), false),
                    };
                    bytes.resize(want, 0);
                    if tx.send((offset, bytes, complete)).is_err() {
                        break;
                    }
                }
            });
        }
        drop(tx);
        let mut complete = true;
        for _ in 0..ranges {
            let (offset, bytes, ok) = rx.recv().map_err(|_| io::Error::other("a range worker stopped"))?;
            complete &= ok;
            emit(offset, bytes)?;
        }
        Ok(complete)
    })
}

pub struct WriteJob {
    fd: c_int,
    /// A DATA frame's records, and where in them this write's bytes are.
    records: Arc<Vec<u8>>,
    bytes: Range<usize>,
    offset: i64,
    key: (u32, u32, u32),
    end: i64,
}

pub struct WriteDone {
    pub key: (u32, u32, u32),
    pub start: i64,
    pub end: i64,
    pub result: io::Result<()>,
}

fn write_at(fd: c_int, bytes: &[u8], offset: i64) -> io::Result<()> {
    let mut done = 0usize;
    while done < bytes.len() {
        let count = unsafe {
            pwrite(fd, bytes[done..].as_ptr().cast(), bytes.len() - done, offset + done as i64)
        };
        if count < 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error() == Some(EINTR) {
                continue;
            }
            return Err(error);
        }
        if count == 0 {
            return Err(io::Error::new(io::ErrorKind::WriteZero, "pwrite wrote nothing"));
        }
        done += count as usize;
    }
    Ok(())
}

/// A pool of receiving writers. Files are only published after every queued
/// write has completed, so the event loop can keep parsing DATA frames while
/// several ranges of one file are written at once.
pub struct WritePool {
    jobs: Vec<Sender<WriteJob>>,
    done: Receiver<WriteDone>,
    workers: Vec<JoinHandle<()>>,
    next: usize,
}

impl WritePool {
    pub fn new(count: usize) -> Self {
        let count = count.clamp(1, MAX_WORKERS);
        let (done_tx, done) = channel();
        let mut jobs = Vec::with_capacity(count);
        let mut workers = Vec::with_capacity(count);
        for _ in 0..count {
            let (tx, rx) = channel::<WriteJob>();
            jobs.push(tx);
            let done_tx = done_tx.clone();
            workers.push(std::thread::spawn(move || {
                while let Ok(job) = rx.recv() {
                    let result = write_at(job.fd, &job.records[job.bytes.clone()], job.offset);
                    let _ = done_tx.send(WriteDone { key: job.key, start: job.offset, end: job.end, result });
                }
            }));
        }
        Self { jobs, done, workers, next: 0 }
    }

    pub fn submit(&mut self, fd: c_int, records: Arc<Vec<u8>>, bytes: Range<usize>, offset: i64, end: i64, key: (u32, u32, u32)) {
        let index = self.next % self.jobs.len();
        self.next = self.next.wrapping_add(1);
        let _ = self.jobs[index].send(WriteJob { fd, records, bytes, offset, key, end });
    }

    pub fn try_done(&self) -> Option<WriteDone> {
        self.done.try_recv().ok()
    }

    pub fn recv_done(&self) -> Option<WriteDone> {
        self.done.recv().ok()
    }
}

impl Drop for WritePool {
    fn drop(&mut self) {
        self.jobs.clear();
        for worker in self.workers.drain(..) {
            let _ = worker.join();
        }
    }
}
