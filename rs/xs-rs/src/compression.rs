//! Compression policy: the worthwhile sample before spending CPU, and the adaptive level.
//!
//! This is `compression.cpp` and the parts of `remote.cpp` that use it. The suffix list
//! itself is parsed by `xs_wire::compress`, which is where the configuration validation
//! lives. A frame is always one independent zstd frame after a `var` raw length.

use std::sync::atomic::{AtomicI32, AtomicU64, Ordering};
use std::sync::Mutex;

use xs_wire::Suffixes;

/// What the send queue showed when the writer took the bytes it then wrote.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Transport {
    /// Producers had to wait for room in the queue: the transport is the bottleneck.
    Saturated,
    /// A deep queue was waiting, though producers were not held up.
    Queued,
    /// Little was waiting: the writer is keeping up with what is produced.
    KeepingUp,
}

const DROP_BYTES: u64 = 16 << 20;
/// The writer rate (bytes per second of writing) above which automatic compression stops.
const AUTO_COMPRESS_BELOW: f64 = 256.0 * 1024.0 * 1024.0;
const WINDOW_BYTES: u64 = 4 << 20;

#[derive(Debug, Default)]
struct WriterState {
    keeping_up_bytes: u64,
    keeping_up_since: u64,
    window_bytes: u64,
    window_ns: u64,
    window_saturated: u64,
    sustained: f64,
}

/// How fast levels 3 and 6 compress against level 1 on one core, and how much smaller their output
/// is, where a level has not been measured itself. From the compression study's zstd measurements on
/// a Raspberry Pi 4 and 5 (docs/compression-study.md): 0.67-0.78 and 0.16 of level 1's speed, and
/// 0.77 and 0.61 of its size on congress; rounded towards caution.
const SPEED_AGAINST_LEVEL_1: [f64; 3] = [1.0, 0.6, 0.15];
const SIZE_AGAINST_LEVEL_1: [f64; 3] = [1.0, 0.85, 0.75];
/// A level's speed and ratio are trusted from this much input on.
const MEASURED_BYTES: u64 = 1 << 20;

/// `CompressionLink`: chooses the zstd level from the rate of active transport writes, and from how
/// fast this machine's workers compress at each level.
#[derive(Debug, Default)]
pub struct CompressionLink {
    bytes: AtomicU64,
    nanoseconds: AtomicU64,
    cap: AtomicI32,
    last_level: AtomicI32,
    compressed_input: [AtomicU64; 3],
    writer: Mutex<WriterState>,
    /// Per level (1, 3, 6): input bytes, output bytes and nanoseconds spent compressing, by all workers.
    cpu_input: [AtomicU64; 3],
    cpu_output: [AtomicU64; 3],
    cpu_ns: [AtomicU64; 3],
    workers: AtomicU64,
}

fn slot(level: i32) -> usize {
    if level >= 6 {
        2
    } else if level >= 3 {
        1
    } else {
        0
    }
}

impl CompressionLink {
    pub fn new() -> Self {
        Self { cap: AtomicI32::new(6), last_level: AtomicI32::new(1), ..Self::default() }
    }

    /// Record a writer batch: `count` bytes took `elapsed` ns to write, finishing at `now`.
    pub fn observe(&self, count: u64, elapsed: u64, state: Transport, now: u64, rate_limit: u64) {
        if count == 0 || elapsed == 0 {
            return;
        }
        self.nanoseconds.fetch_add(elapsed, Ordering::Relaxed);
        self.bytes.fetch_add(count, Ordering::Relaxed);
        let mut writer = self.writer.lock().unwrap_or_else(|poison| poison.into_inner());
        if state != Transport::KeepingUp {
            writer.keeping_up_bytes = 0;
        } else {
            if writer.keeping_up_bytes == 0 {
                writer.keeping_up_since = now.saturating_sub(elapsed);
            }
            writer.keeping_up_bytes += count;
            if writer.keeping_up_bytes >= DROP_BYTES {
                let in_force = self.level(false, 0, rate_limit);
                if in_force > 1 && now > writer.keeping_up_since {
                    writer.sustained =
                        writer.keeping_up_bytes as f64 * 1e9 / (now - writer.keeping_up_since) as f64;
                    self.cap.store(if in_force == 6 { 3 } else { 1 }, Ordering::Relaxed);
                }
                writer.keeping_up_bytes = 0;
            }
        }
        writer.window_bytes += count;
        writer.window_ns += elapsed;
        if state == Transport::Saturated {
            writer.window_saturated += count;
        }
        if writer.window_bytes < WINDOW_BYTES {
            return;
        }
        if self.cap.load(Ordering::Relaxed) < 6
            && writer.window_saturated * 2 >= writer.window_bytes
            && writer.window_ns != 0
            && (writer.window_bytes as f64 * 1e9 / writer.window_ns as f64) < 0.9 * writer.sustained
        {
            self.cap.store(6, Ordering::Relaxed);
        }
        writer.window_bytes = 0;
        writer.window_ns = 0;
        writer.window_saturated = 0;
    }

    /// The level to compress the next frame at. Explicit levels bypass the rate rule.
    pub fn level(&self, explicit_level: bool, requested: i64, rate_limit: u64) -> i32 {
        if explicit_level {
            return requested.clamp(i32::MIN as i64, i32::MAX as i64) as i32;
        }
        let count = self.bytes.load(Ordering::Relaxed);
        let elapsed = self.nanoseconds.load(Ordering::Relaxed);
        // Level 1 until the link is known: the cheapest level that still compresses well, and the one
        // a slow CPU can always afford (level 3 cost a Raspberry Pi 4 two to five times level 1's time).
        if count < 256 * 1024 || elapsed < 1_000_000 {
            return 1.min(self.cap());
        }
        let mut rate = count as f64 * 1e9 / elapsed as f64;
        if rate_limit != 0 {
            rate = rate.min(rate_limit as f64);
        }
        let mut chosen = if rate >= 64.0 * 1024.0 * 1024.0 {
            1
        } else if rate < 8.0 * 1024.0 * 1024.0 {
            6
        } else {
            3
        };
        // A higher level pays only while this machine compresses at it faster than the link would
        // carry the lower level's output (the study's model: level L+ beats L when the link is
        // slower than ratio(L) x speed(L+)). Step down until it does, or to level 1.
        while chosen > 1 {
            let lower = if chosen == 6 { 3 } else { 1 };
            match self.capacity(chosen) {
                Some(capacity) if capacity < rate / self.ratio(lower) => chosen = lower,
                _ => break,
            }
        }
        chosen.min(self.cap())
    }

    /// Record that the workers compressed `input` bytes into `output` at `level`, in `nanoseconds`.
    pub fn record_compression(&self, level: i32, input: u64, output: u64, nanoseconds: u64) {
        let i = slot(level);
        self.cpu_input[i].fetch_add(input, Ordering::Relaxed);
        self.cpu_output[i].fetch_add(output, Ordering::Relaxed);
        self.cpu_ns[i].fetch_add(nanoseconds, Ordering::Relaxed);
    }

    /// How many workers compress at once, which scales one worker's measured speed to the machine's.
    pub fn set_workers(&self, workers: usize) {
        self.workers.store(workers as u64, Ordering::Relaxed);
    }

    /// Raw bytes per second all workers together compress at `level`: measured at that level, or else
    /// from a measured level by zstd's usual speeds. None until some level has been measured.
    fn capacity(&self, level: i32) -> Option<f64> {
        let workers = self.workers.load(Ordering::Relaxed).max(1) as f64;
        let per_worker = |i: usize| {
            let (input, ns) = (self.cpu_input[i].load(Ordering::Relaxed), self.cpu_ns[i].load(Ordering::Relaxed));
            (input >= MEASURED_BYTES && ns > 0).then(|| input as f64 * 1e9 / ns as f64)
        };
        let target = slot(level);
        if let Some(rate) = per_worker(target) {
            return Some(rate * workers);
        }
        (0..3).find_map(|i| {
            per_worker(i).map(|rate| rate / SPEED_AGAINST_LEVEL_1[i] * SPEED_AGAINST_LEVEL_1[target] * workers)
        })
    }

    /// Compressed bytes per raw byte at `level`: measured, or from level 1's by zstd's usual sizes,
    /// or a third, as text and the congress corpus compress at level 1 in xs's frames.
    fn ratio(&self, level: i32) -> f64 {
        let measured = |i: usize| {
            let input = self.cpu_input[i].load(Ordering::Relaxed);
            (input >= MEASURED_BYTES).then(|| self.cpu_output[i].load(Ordering::Relaxed) as f64 / input as f64)
        };
        let target = slot(level);
        measured(target)
            .or_else(|| (0..3).find_map(|i| measured(i).map(|r| r / SIZE_AGAINST_LEVEL_1[i] * SIZE_AGAINST_LEVEL_1[target])))
            .unwrap_or(0.33 * SIZE_AGAINST_LEVEL_1[target])
            .clamp(0.01, 1.0)
    }

    /// The level for compression this end chose (not the peer's `-z`). A transient stall
    /// in the writer must not push it to a level whose CPU then keeps the writer slow:
    /// automatic compression stays at level 3 or below. `-z` keeps the adaptive rule.
    pub fn automatic_level(&self, rate_limit: u64) -> i32 {
        self.level(false, 3, rate_limit).min(3)
    }

    /// Without `-z`, whether compressing still pays: from the start, and then while the
    /// writer moves less than `AUTO_COMPRESS_BELOW`. Over an internet link the writer waits
    /// on ssh, so its rate is the link's, and fewer bytes on the wire are worth level 1-3
    /// CPU; a local pipe or a 10 GbE link is better served by the raw bytes.
    pub fn auto_worthwhile(&self) -> bool {
        let count = self.bytes.load(Ordering::Relaxed);
        let elapsed = self.nanoseconds.load(Ordering::Relaxed);
        if count < 4 << 20 || elapsed < 1_000_000 {
            return true;
        }
        (count as f64 * 1e9 / elapsed as f64) < AUTO_COMPRESS_BELOW
    }

    /// Record that a worker compressed `raw` bytes at an automatic level.
    pub fn count(&self, level: i32, raw: u64) {
        self.compressed_input[slot(level)].fetch_add(raw, Ordering::Relaxed);
    }

    pub fn set_last_level(&self, level: i32) {
        self.last_level.store(level, Ordering::Relaxed);
    }

    pub fn cap(&self) -> i32 {
        self.cap.load(Ordering::Relaxed)
    }

    /// `"3 (automatic)"`, or the level that compressed the most with shares of the input.
    #[allow(dead_code)]
    pub fn summary(&self) -> String {
        const LEVELS: [i32; 3] = [1, 3, 6];
        let mut bytes = [0u64; 3];
        let mut total = 0u64;
        let mut most = 0usize;
        let mut used_levels = 0usize;
        for (index, slot) in bytes.iter_mut().enumerate() {
            *slot = self.compressed_input[index].load(Ordering::Relaxed);
        }
        for (index, &count) in bytes.iter().enumerate() {
            total += count;
            if count != 0 {
                used_levels += 1;
            }
            if count > bytes[most] {
                most = index;
            }
        }
        if total == 0 {
            return format!("{} (automatic)", self.last_level.load(Ordering::Relaxed));
        }
        let mut text = format!("{} (automatic", LEVELS[most]);
        if used_levels < 2 {
            text.push(')');
            return text;
        }
        let mut separator = "; ";
        for (index, &count) in bytes.iter().enumerate() {
            if count == 0 {
                continue;
            }
            let share = (count * 100 + total / 2) / total;
            text.push_str(&format!("{separator}level {}: {share}%", LEVELS[index]));
            separator = ", ";
        }
        text.push_str(" of compressed input)");
        text
    }
}

/// `compression_worthwhile`: sample four spaced 2 KiB regions before compressing a large block.
pub fn worthwhile(raw: &[u8]) -> bool {
    if raw.len() < 16 * 1024 {
        return true;
    }
    const SPAN: usize = 2048;
    let mut sample = Vec::with_capacity(SPAN * 4);
    for index in 0..4 {
        let at = (raw.len() - SPAN) * index / 3;
        sample.extend_from_slice(&raw[at..at + SPAN]);
    }
    match crate::ffi::zstd_compress_exact(&sample, 1) {
        // A codec error means try the real block: only a successful sample decides.
        Err(_) => true,
        Ok(compressed) => compressed.len() < sample.len() * 95 / 100,
    }
}

/// The suffixes a sender should not compress. An unset policy uses the C++ defaults.
pub fn suffixes(list: &[u8]) -> Suffixes {
    let mut parsed = Suffixes::empty();
    if !parsed.assign(list) {
        return Suffixes::default();
    }
    parsed
}

#[cfg(test)]
mod tests {
    use super::*;

    const MIB: u64 = 1024 * 1024;
    const SECOND: u64 = 1_000_000_000;

    fn write(link: &CompressionLink, megabytes: u64, bytes_per_second: u64, state: Transport, clock: &mut u64) -> i32 {
        for _ in 0..megabytes {
            let elapsed = MIB * SECOND / bytes_per_second;
            *clock += elapsed;
            link.observe(MIB, elapsed, state, *clock, 0);
        }
        link.level(false, 3, 0)
    }

    #[test]
    fn the_rate_rule_is_the_one_compression_cpp_documents() {
        // Unlike the C++ (level 3), an unknown link starts at level 1.
        let unknown = CompressionLink::new();
        assert_eq!(unknown.level(false, 3, 0), 1);
        unknown.observe(128 * 1024, SECOND, Transport::Saturated, SECOND, 0);
        assert_eq!(unknown.level(false, 3, 0), 1);

        let fast = CompressionLink::new();
        let medium = CompressionLink::new();
        let slow = CompressionLink::new();
        fast.observe(16 * MIB, SECOND / 10, Transport::Saturated, SECOND, 0);
        medium.observe(4 * MIB, SECOND / 10, Transport::Saturated, SECOND, 0);
        slow.observe(MIB, SECOND, Transport::Saturated, SECOND, 0);
        assert_eq!(fast.level(false, 3, 0), 1);
        assert_eq!(medium.level(false, 3, 0), 3);
        assert_eq!(slow.level(false, 3, 0), 6);
        assert_eq!(fast.level(false, 3, MIB), 6);
        // Compression this end chose never escalates into the CPU-heavy levels.
        assert_eq!(slow.automatic_level(0), 3);
        assert_eq!(medium.automatic_level(0), 3);
        assert_eq!(fast.automatic_level(0), 1);
        for level in [-1000, -5, 0, 1, 9, 22] {
            assert_eq!(fast.level(true, level, 0), level as i32);
            assert_eq!(slow.level(true, level, 0), level as i32);
        }
    }

    #[test]
    fn a_machine_too_slow_for_its_level_caps_it_until_the_link_slows() {
        let mut clock = 0;
        let weak = CompressionLink::new();
        assert_eq!(write(&weak, 15, 46 * MIB, Transport::KeepingUp, &mut clock), 3);
        assert_eq!(write(&weak, 1, 46 * MIB, Transport::KeepingUp, &mut clock), 1);
        assert_eq!(write(&weak, 64, 100 * MIB, Transport::Saturated, &mut clock), 1);
        assert_eq!(write(&weak, 64, 50 * MIB, Transport::Saturated, &mut clock), 1);

        let mut clock = 0;
        let slowing = CompressionLink::new();
        write(&slowing, 16, 30 * MIB, Transport::KeepingUp, &mut clock);
        assert_eq!(slowing.level(false, 3, 0), 1);
        assert_eq!(write(&slowing, 8, 28 * MIB, Transport::Saturated, &mut clock), 1);
        assert_eq!(write(&slowing, 8, 20 * MIB, Transport::Saturated, &mut clock), 3);

        let mut clock = 0;
        let crawling = CompressionLink::new();
        assert_eq!(write(&crawling, 15, 4 * MIB, Transport::KeepingUp, &mut clock), 6);
        assert_eq!(write(&crawling, 1, 4 * MIB, Transport::KeepingUp, &mut clock), 3);
        assert_eq!(write(&crawling, 15, 4 * MIB, Transport::KeepingUp, &mut clock), 3);
        assert_eq!(write(&crawling, 1, 4 * MIB, Transport::KeepingUp, &mut clock), 1);

        let scanning = CompressionLink::new();
        let mut clock = 0;
        for _ in 0..60 {
            clock += SECOND;
            scanning.observe(64 * 1024, SECOND, Transport::KeepingUp, clock, 0);
        }
        assert_eq!(scanning.cap(), 6);

        let mut clock = 0;
        let flickering = CompressionLink::new();
        for _ in 0..40 {
            write(&flickering, 12, 46 * MIB, Transport::KeepingUp, &mut clock);
            write(&flickering, 1, 46 * MIB, Transport::Queued, &mut clock);
        }
        assert_eq!(flickering.cap(), 6);
        assert_eq!(flickering.level(false, 3, 0), 3);

        let mut clock = 0;
        let busy = CompressionLink::new();
        assert_eq!(write(&busy, 256, 20 * MIB, Transport::Saturated, &mut clock), 3);
        assert_eq!(busy.cap(), 6);
    }

    #[test]
    fn a_level_this_cpu_cannot_feed_the_link_with_steps_down() {
        // A 20 MiB/s link: the rate rule alone picks level 3.
        let link = || {
            let link = CompressionLink::new();
            link.observe(20 * MIB, SECOND, Transport::Saturated, SECOND, 0);
            link
        };
        assert_eq!(link().level(false, 3, 0), 3);
        // One slow worker at level 1, 50 MB/s of input into a third of it: at level 3 it would
        // manage about 30 MB/s, below the 63 MB/s of input level 1 fills that link with.
        let slow = link();
        slow.set_workers(1);
        slow.record_compression(1, 50 << 20, (50 << 20) / 3, SECOND);
        assert_eq!(slow.level(false, 3, 0), 1);
        // Four workers at 500 MB/s each afford level 3, and are measured at it from then on.
        let fast = link();
        fast.set_workers(4);
        fast.record_compression(1, 500 << 20, (500 << 20) / 3, SECOND);
        assert_eq!(fast.level(false, 3, 0), 3);
        fast.record_compression(3, 8 << 20, 2 << 20, SECOND);
        assert_eq!(fast.level(false, 3, 0), 1);
        // A 4 MiB/s link: level 6 by the rate rule, which a 50 MB/s worker cannot sustain, but level 3 it can.
        let crawling = CompressionLink::new();
        crawling.observe(4 * MIB, SECOND, Transport::Saturated, SECOND, 0);
        crawling.set_workers(1);
        crawling.record_compression(1, 50 << 20, (50 << 20) / 3, SECOND);
        assert_eq!(crawling.level(false, 3, 0), 3);
        // Explicit levels are never second-guessed.
        assert_eq!(slow.level(true, 6, 0), 6);
    }

    #[test]
    fn the_summary_names_the_dominant_level_and_its_share() {
        let report = CompressionLink::new();
        assert_eq!(report.summary(), "1 (automatic)");
        report.count(1, 600);
        assert_eq!(report.summary(), "1 (automatic)");
        report.count(3, 300);
        report.count(6, 2100);
        assert_eq!(report.summary(), "6 (automatic; level 1: 20%, level 3: 10%, level 6: 70% of compressed input)");
    }

    #[test]
    fn sampling_trusts_small_records_and_spots_random_large_ones() {
        assert!(worthwhile(b"small record"));
        assert!(worthwhile(&vec![b'x'; 1 << 20]));
        let mut random = vec![0u8; 1 << 20];
        let mut state = 0x9e37_79b9_7f4a_7c15u64;
        for byte in random.iter_mut() {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            *byte = state as u8;
        }
        assert!(!worthwhile(&random));
        random[..512 * 1024].fill(b'x');
        assert!(worthwhile(&random));
    }
}
