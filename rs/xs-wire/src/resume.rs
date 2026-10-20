//! The verified resume prefix in NEED and DATA, as `Sender::on_need`,
//! `Receiver::generate_dir` and `Receiver::data` write it in src/remote.cpp.
//!
//! A nonzero prefix carries the size and the XXH3-128 of the destination bytes the
//! receiver already has. A zero prefix is only its size, one `var(0)`, with no sums.

use crate::codec::{DecodeError, Decoder, Encoder};

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct ResumePrefix {
    pub size: i64,
    pub sum: [u64; 2],
}

impl ResumePrefix {
    pub fn is_empty(&self) -> bool {
        self.size == 0
    }

    /// `var(size)`, then the two sums when the size is nonzero.
    pub fn put(&self, e: &mut Encoder) {
        e.var(self.size.max(0) as u64);
        if self.size > 0 {
            e.var(self.sum[0]).var(self.sum[1]);
        }
    }

    pub fn get(d: &mut Decoder<'_>) -> Result<Self, DecodeError> {
        let raw = d.var()?;
        let size = i64::try_from(raw).map_err(|_| DecodeError::Invalid("bad resume prefix".into()))?;
        let sum = if size > 0 { [d.var()?, d.var()?] } else { [0, 0] };
        Ok(Self { size, sum })
    }
}

/// The receiver's check in `Receiver::data`: a prefix is valid only when it was
/// offered in NEED, is not a retry, fits the file, and does not overlap data
/// already sent below it.
pub fn verified(offered: Option<&ResumePrefix>, prefix: i64, total: i64, attempt: u32, offset: i64, ending: bool) -> bool {
    if prefix < 0 || prefix > total {
        return false;
    }
    if prefix != 0 && (attempt != 0 || offered.map(|p| p.size) != Some(prefix)) {
        return false;
    }
    ending || offset >= prefix
}

#[cfg(test)]
mod tests {
    use super::*;

    fn prefix_bytes(prefix: ResumePrefix) -> Vec<u8> {
        let mut e = Encoder::new();
        prefix.put(&mut e);
        e.into_bytes()
    }

    #[test]
    fn a_zero_prefix_is_a_single_var_zero() {
        assert_eq!(prefix_bytes(ResumePrefix::default()), [0]);
        let mut d = Decoder::new(&[0]);
        assert_eq!(ResumePrefix::get(&mut d).unwrap(), ResumePrefix::default());
        assert!(d.is_empty());
    }

    #[test]
    fn a_nonzero_prefix_is_the_size_then_low_and_high_sums() {
        let prefix = ResumePrefix { size: 2 * 1024 * 1024, sum: [0x0302_0100, 0x0706_0504] };
        // 2 MiB is LEB128 0x80 0x80 0x80 0x01; the sums follow little-value-first.
        assert_eq!(
            prefix_bytes(prefix),
            [0x80, 0x80, 0x80, 0x01, 0x80, 0x82, 0x88, 0x18, 0x84, 0x8a, 0x98, 0x38]
        );
        let encoded = prefix_bytes(prefix);
        let mut d = Decoder::new(&encoded);
        assert_eq!(ResumePrefix::get(&mut d).unwrap(), prefix);
    }

    #[test]
    fn the_receivers_prefix_checks_are_exact() {
        let offered = ResumePrefix { size: 100, sum: [1, 2] };
        assert!(verified(Some(&offered), 100, 200, 0, 100, false));
        assert!(verified(Some(&offered), 0, 200, 1, 0, false));
        assert!(!verified(None, 1, 200, 0, 1, false), "unoffered prefix");
        assert!(!verified(Some(&offered), 99, 200, 0, 99, false), "wrong size");
        assert!(!verified(Some(&offered), 100, 90, 0, 100, false), "past the file");
        assert!(!verified(Some(&offered), 100, 200, 1, 100, false), "retry prefix");
        assert!(!verified(Some(&offered), 100, 200, 0, 99, false), "chunk below the prefix");
        assert!(verified(Some(&offered), 100, 200, 0, 0, true), "END has no offset");
    }
}
