//! `PF_IO_CONTROL`: the token bucket, the idle deadline and the keep-alive frames.
//!
//! This follows `rate_limit.cpp` and `Conn::configure`, `Conn::check_timeout` and the writer
//! loop in `remote.cpp`. A rate of zero disables the bucket; the bucket holds at most 0.1
//! seconds and 16 KiB, even after a long idle period. `--bwlimit` is parsed exactly as
//! `parse_rate` does in `src/main.cpp`: a bare rate is KiB/s and the result is a multiple of
//! 1024 bytes per second.

use std::io::{self, Read};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use crate::consts::{feature, frame_type};
use crate::frame::Frame;

/// Nanoseconds from one process-wide monotonic origin, like `now_ns()` in the C++ xs.
pub fn now_ns() -> u64 {
    static START: OnceLock<Instant> = OnceLock::new();
    START.get_or_init(Instant::now).elapsed().as_nanos() as u64
}

/// Parse `--bwlimit`, matching `parse_rate` in `src/main.cpp` byte for byte.
pub fn parse_rate(value: &str) -> Result<u64, String> {
    let (number, suffix) = number_prefix(value)
        .ok_or_else(|| format!("--bwlimit requires a nonnegative rate: {value}"))?;
    if !number.is_finite() || number < 0.0 {
        return Err(format!("--bwlimit requires a nonnegative rate: {value}"));
    }
    let suffix = suffix.to_ascii_lowercase();
    let multiplier = if suffix.is_empty() {
        1024.0
    } else if suffix == "b" {
        1.0
    } else {
        let bytes = suffix.as_bytes();
        let power = b"kmgtp"
            .iter()
            .position(|&letter| letter == bytes[0])
            .ok_or_else(|| format!("--bwlimit has an invalid suffix: {value}"))?;
        let binary = match bytes.len() {
            1 => true,
            2 if bytes[1] == b'b' => false,
            3 if &suffix[1..] == "ib" => true,
            _ => return Err(format!("--bwlimit has an invalid suffix: {value}")),
        };
        let base: f64 = if binary { 1024.0 } else { 1000.0 };
        base.powi(power as i32 + 1)
    };
    let kib = ((number * multiplier + 512.0) / 1024.0).floor();
    if !kib.is_finite()
        || kib > (i64::MAX as f64 / 1024.0)
        || (number > 0.0 && kib < 1.0)
    {
        return Err(format!("--bwlimit rate is out of range: {value}"));
    }
    Ok((kib as u64) * 1024)
}

/// Parse `--timeout`: nonnegative ASCII digits no greater than `INT_MAX`.
pub fn parse_timeout(value: &str) -> Result<u32, String> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err("--timeout requires nonnegative integer seconds".into());
    }
    match value.parse::<u64>() {
        Ok(seconds) if seconds <= i32::MAX as u64 => Ok(seconds as u32),
        _ => Err("--timeout seconds are out of range".into()),
    }
}

/// The numeric prefix `strtold` would consume, plus the suffix it leaves behind.
fn number_prefix(value: &str) -> Option<(f64, &str)> {
    let bytes = value.as_bytes();
    let mut start = 0;
    if matches!(bytes.first(), Some(b'+' | b'-')) {
        start = 1;
    }
    let lower = value[start..].to_ascii_lowercase();
    for word in ["infinity", "inf", "nan"] {
        if lower.starts_with(word) {
            let end = start + word.len();
            return Some((value[..end].parse().ok()?, &value[end..]));
        }
    }
    let mut index = start;
    let mut digits = false;
    let mut dot = false;
    while index < bytes.len() {
        match bytes[index] {
            byte if byte.is_ascii_digit() => {
                digits = true;
                index += 1;
            }
            b'.' if !dot => {
                dot = true;
                index += 1;
            }
            _ => break,
        }
    }
    if !digits {
        return None;
    }
    if index < bytes.len() && matches!(bytes[index], b'e' | b'E') {
        let mut exponent = index + 1;
        if exponent < bytes.len() && matches!(bytes[exponent], b'+' | b'-') {
            exponent += 1;
        }
        let first = exponent;
        while exponent < bytes.len() && bytes[exponent].is_ascii_digit() {
            exponent += 1;
        }
        if exponent > first {
            index = exponent;
        }
    }
    Some((value[..index].parse().ok()?, &value[index..]))
}

#[derive(Debug)]
struct Bucket {
    rate: u64,
    capacity: f64,
    tokens: f64,
    last: u64,
}

/// The token bucket of `RateLimiter` in rate_limit.cpp.
#[derive(Debug)]
pub struct RateLimiter {
    bucket: Mutex<Bucket>,
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new()
    }
}

impl RateLimiter {
    pub fn new() -> Self {
        Self {
            bucket: Mutex::new(Bucket { rate: 0, capacity: 1.0, tokens: 1.0, last: now_ns() }),
        }
    }

    pub fn configure(&self, bytes_per_second: u64) {
        let mut bucket = self.bucket.lock().unwrap_or_else(|poison| poison.into_inner());
        bucket.rate = bytes_per_second;
        bucket.capacity = 1.0_f64.max(16_384.0_f64.min(bytes_per_second as f64 / 10.0));
        bucket.tokens = bucket.capacity;
        bucket.last = now_ns();
    }

    pub fn rate(&self) -> u64 {
        self.bucket.lock().unwrap_or_else(|poison| poison.into_inner()).rate
    }

    /// Reserve up to `wanted` bytes, waiting in bounded sleeps for tokens, as the C++ does.
    pub fn acquire(&self, wanted: usize) -> usize {
        loop {
            let delay;
            {
                let mut bucket = self.bucket.lock().unwrap_or_else(|poison| poison.into_inner());
                if bucket.rate == 0 {
                    return wanted;
                }
                let now = now_ns();
                bucket.tokens = bucket.capacity.min(
                    bucket.tokens + (now.saturating_sub(bucket.last)) as f64 * (bucket.rate as f64 / 1e9),
                );
                bucket.last = now;
                let n = wanted.min(bucket.capacity as usize);
                if bucket.tokens >= n as f64 {
                    bucket.tokens -= n as f64;
                    return n;
                }
                delay = ((n as f64 - bucket.tokens) * 1e6 / bucket.rate as f64).ceil();
            }
            let micros = delay.clamp(1.0, 50_000.0) as u64;
            std::thread::sleep(Duration::from_micros(micros));
        }
    }
}

/// The shared deadline and keep-alive state of one connection.
#[derive(Debug)]
pub struct IoControl {
    limiter: RateLimiter,
    timeout_ns: AtomicU64,
    timeout_seconds: AtomicU64,
    heartbeat_ns: AtomicU64,
    keepalive: AtomicBool,
    last_activity: AtomicU64,
    last_send: AtomicU64,
    last_write: AtomicU64,
    writer_active: AtomicBool,
    reading: AtomicBool,
    timed_out: AtomicBool,
    done: AtomicBool,
}

impl Default for IoControl {
    fn default() -> Self {
        Self::new()
    }
}

impl IoControl {
    pub fn new() -> Self {
        let now = now_ns();
        Self {
            limiter: RateLimiter::new(),
            timeout_ns: AtomicU64::new(0),
            timeout_seconds: AtomicU64::new(0),
            heartbeat_ns: AtomicU64::new(10_000_000_000),
            keepalive: AtomicBool::new(false),
            last_activity: AtomicU64::new(now),
            last_send: AtomicU64::new(now),
            last_write: AtomicU64::new(now),
            writer_active: AtomicBool::new(false),
            reading: AtomicBool::new(false),
            timed_out: AtomicBool::new(false),
            done: AtomicBool::new(false),
        }
    }

    /// `Conn::configure`: the rate, the idle deadline and whether this side sends heartbeats.
    pub fn configure(&self, rate: u64, seconds: u32, heartbeat: bool) {
        self.limiter.configure(rate);
        let idle = u64::from(seconds) * 1_000_000_000;
        self.timeout_ns.store(idle, Ordering::Relaxed);
        self.timeout_seconds.store(u64::from(seconds), Ordering::Relaxed);
        let beat = if seconds == 0 { 10_000_000_000 } else { (idle / 3).clamp(100_000_000, 10_000_000_000) };
        self.heartbeat_ns.store(beat, Ordering::Relaxed);
        self.keepalive.store(heartbeat, Ordering::Relaxed);
    }

    pub fn limiter(&self) -> &RateLimiter {
        &self.limiter
    }

    pub fn rate_limit(&self) -> u64 {
        self.limiter.rate()
    }

    pub fn timeout(&self) -> u64 {
        self.timeout_ns.load(Ordering::Relaxed)
    }

    pub fn keepalive_enabled(&self) -> bool {
        self.keepalive.load(Ordering::Relaxed)
    }

    pub fn timed_out(&self) -> bool {
        self.timed_out.load(Ordering::Relaxed)
    }

    /// Incoming or ordinary outgoing bytes count as activity; a heartbeat does not.
    pub fn touch_activity(&self) {
        let now = now_ns();
        self.last_activity.store(now, Ordering::Relaxed);
    }

    pub fn note_write(&self, activity: bool) {
        let now = now_ns();
        self.last_send.store(now, Ordering::Relaxed);
        self.last_write.store(now, Ordering::Relaxed);
        if activity {
            self.last_activity.store(now, Ordering::Relaxed);
        }
    }

    /// Called just before a write so a writer blocked in the transport has a fresh deadline.
    pub fn begin_write(&self) {
        self.last_write.store(now_ns(), Ordering::Relaxed);
    }

    pub fn heartbeat_due(&self) -> bool {
        self.keepalive.load(Ordering::Relaxed)
            && now_ns().saturating_sub(self.last_send.load(Ordering::Relaxed))
                >= self.heartbeat_ns.load(Ordering::Relaxed)
    }

    pub fn set_writer_active(&self, active: bool) {
        self.writer_active.store(active, Ordering::Relaxed);
    }

    pub fn finish(&self) {
        self.done.store(true, Ordering::Relaxed);
    }

    fn expired(&self) -> bool {
        let deadline = self.timeout_ns.load(Ordering::Relaxed);
        if deadline == 0 {
            return false;
        }
        let now = now_ns();
        let read = self.reading.load(Ordering::Relaxed)
            && now.saturating_sub(self.last_activity.load(Ordering::Relaxed)) >= deadline;
        let write = self.writer_active.load(Ordering::Relaxed)
            && now.saturating_sub(self.last_write.load(Ordering::Relaxed)) >= deadline;
        read || write
    }
}

/// Owns the watchdog thread. Dropping it stops the thread before the process exits normally.
pub struct Watchdog {
    control: Arc<IoControl>,
    handle: Option<JoinHandle<()>>,
}

impl Watchdog {
    pub fn spawn(control: Arc<IoControl>) -> Self {
        let shared = control.clone();
        let handle = std::thread::spawn(move || {
            while !shared.done.load(Ordering::Relaxed) {
                if shared.expired() && !shared.timed_out.swap(true, Ordering::Relaxed) {
                    let seconds = shared.timeout_seconds.load(Ordering::Relaxed);
                    eprintln!(
                        "xs-rs: I/O timeout after {seconds} second{}",
                        if seconds == 1 { "" } else { "s" }
                    );
                    std::process::exit(30);
                }
                std::thread::park_timeout(Duration::from_millis(50));
            }
        });
        Self { control, handle: Some(handle) }
    }
}

impl Drop for Watchdog {
    fn drop(&mut self) {
        self.control.finish();
        if let Some(handle) = self.handle.take() {
            // Wake it rather than wait out its sleep: both ends of every transfer drop one.
            handle.thread().unpark();
            let _ = handle.join();
        }
    }
}

/// A reader that records every byte the peer sends, so a slowly arriving frame is activity too.
pub struct ActivityReader<R> {
    inner: R,
    control: Arc<IoControl>,
}

impl<R> ActivityReader<R> {
    pub fn new(inner: R, control: Arc<IoControl>) -> Self {
        Self { inner, control }
    }
}

impl<R: Read> Read for ActivityReader<R> {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        self.control.reading.store(true, Ordering::Relaxed);
        let result = self.inner.read(buffer);
        self.control.reading.store(false, Ordering::Relaxed);
        let count = result?;
        if count != 0 {
            self.control.touch_activity();
        }
        Ok(count)
    }
}

/// The empty frame both sides send while idle (`new_frame(F_KEEPALIVE)`).
pub fn keepalive() -> Frame {
    Frame::new(frame_type::KEEPALIVE, Vec::new())
}

/// Whether a received frame is an allowed, negotiated keep-alive.
pub fn valid_keepalive(frame: &Frame, negotiated: bool) -> bool {
    negotiated && frame.kind == frame_type::KEEPALIVE && frame.payload.is_empty()
}

/// IO_CONTROL is what makes a keep-alive legal; a version 3 peer has no feature word.
pub fn negotiated(features: u64) -> bool {
    features & feature::IO_CONTROL != 0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rates_round_like_parse_rate() {
        for (value, expected) in [
            ("0", 0),
            ("1", 1024),
            ("0.5", 1024),
            ("1.5KiB", 2048),
            ("1.5KB", 1024),
            ("256k", 262_144),
            ("1m", 1_048_576),
            ("1MB", 1_000_448),
            ("1.5mib", 1_572_864),
        ] {
            let parsed = parse_rate(value).unwrap_or(0);
            assert_eq!(parsed, expected, "{value}");
        }
        assert!(parse_rate("1b").is_err());
        for invalid in ["-1", "nan", "inf", "1e999", "0.1", "1junk", "1K/s", "1e30", ""] {
            assert!(parse_rate(invalid).is_err(), "{invalid}");
        }
    }

    #[test]
    fn timeouts_are_plain_nonnegative_seconds() {
        assert_eq!(parse_timeout("0"), Ok(0));
        assert_eq!(parse_timeout("2147483647"), Ok(i32::MAX as u32));
        for invalid in ["-1", "nan", "inf", "0.5", "1s", "2147483648", "184467440737095516160", ""] {
            assert!(parse_timeout(invalid).is_err(), "{invalid}");
        }
    }

    #[test]
    fn the_bucket_caps_at_a_tenth_of_a_second_and_sixteen_kibibytes() {
        let limiter = RateLimiter::new();
        limiter.configure(1 << 20);
        // 0.1 s at 1 MiB/s is 104 KiB, but the cap is 16 KiB.
        assert_eq!(limiter.acquire(1 << 20), 16 << 10);
        limiter.configure(256);
        // 0.1 s at 256 B/s is 25.6 bytes; whole-byte reservations only.
        assert_eq!(limiter.acquire(1000), 25);
        limiter.configure(0);
        assert_eq!(limiter.acquire(123_456), 123_456);
    }

    #[test]
    fn keepalives_are_empty_and_need_the_feature() {
        let frame = keepalive();
        assert_eq!(frame.to_bytes(), [0, 0, 0, 0, 18]);
        assert!(valid_keepalive(&frame, true));
        assert!(!valid_keepalive(&frame, false));
        assert!(!valid_keepalive(&Frame::new(frame_type::KEEPALIVE, vec![1]), true));
        assert!(!valid_keepalive(&Frame::new(frame_type::DONE, vec![]), true));
        assert!(negotiated(feature::CORE | feature::IO_CONTROL));
        assert!(!negotiated(feature::CORE));
    }

    #[test]
    fn configure_uses_a_third_of_the_deadline_for_heartbeats() {
        let control = IoControl::new();
        control.configure(0, 30, true);
        assert!(control.keepalive_enabled());
        assert_eq!(control.timeout(), 30_000_000_000);
        control.configure(0, 0, true);
        assert!(control.keepalive_enabled());
        assert_eq!(control.timeout(), 0);
    }
}
