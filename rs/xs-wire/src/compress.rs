//! Compression suffixes: rsync's slash-separated list of names not worth compressing.
//!
//! `CompressionSuffixes::assign` and `matches` in `src/compression.cpp` are the reference,
//! including its literal character classes of the form `mp[34]` and the lazy default list.

/// `DEFAULT_SKIP_COMPRESS` in `src/compression.h`: the suffixes xs skips unless told otherwise.
pub const DEFAULT_SKIP_COMPRESS: &str = "3g2/3gp/7z/aac/ace/apk/avi/bz2/deb/dmg/ear/f4v/flac/flv/gpg/gz/iso/jar/jpeg/jpg/\
lrz/lz/lz4/lzma/lzo/m1a/m1v/m2a/m2ts/m2v/m4a/m4b/m4p/m4r/m4v/mka/mkv/mov/mp1/mp2/\
mp3/mp4/mpa/mpeg/mpg/mpv/mts/odb/odf/odg/odi/odm/odp/ods/odt/oga/ogg/ogm/ogv/ogx/\
opus/otg/oth/otp/ots/ott/oxt/png/qt/rar/rpm/rz/rzip/spx/squashfs/sxc/sxd/sxg/sxm/sxw/\
sz/tbz/tbz2/tgz/tlz/ts/txz/tzo/vob/war/webm/webp/xz/z/zip/zst";

/// The parsed form of a `--skip-compress` list.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Suffixes {
    literals: Vec<Vec<u8>>,
    classes: Vec<Vec<u8>>,
}

impl Default for Suffixes {
    fn default() -> Self {
        let mut suffixes = Self { literals: Vec::new(), classes: Vec::new() };
        // The constant is valid; if it ever were not, the empty list is still safe.
        let _ = suffixes.assign(DEFAULT_SKIP_COMPRESS.as_bytes());
        suffixes
    }
}

impl Suffixes {
    /// A list that skips nothing, for `--skip-compress=`.
    pub fn empty() -> Self {
        Self { literals: Vec::new(), classes: Vec::new() }
    }

    /// Parse `list`, replacing this policy only when the whole list is valid.
    ///
    /// A pattern is lowercased, then either a literal suffix or one carrying `[`...`]`
    /// character classes. A closing bracket without an opener, an empty class, and a
    /// nested opener are refused, as `assign` refuses them.
    pub fn assign(&mut self, list: &[u8]) -> bool {
        if list.len() > 65536 || list.contains(&0) {
            return false;
        }
        let mut literals = Vec::new();
        let mut classes = Vec::new();
        let mut start = 0;
        while start < list.len() {
            let end = list[start..].iter().position(|&byte| byte == b'/').map_or(list.len(), |at| start + at);
            let mut pattern = list[start..end].to_vec();
            pattern.make_ascii_lowercase();
            let mut has_class = false;
            let mut index = 0;
            while index < pattern.len() {
                if pattern[index] == b']' {
                    return false;
                }
                if pattern[index] != b'[' {
                    index += 1;
                    continue;
                }
                let Some(close) = pattern[index + 1..].iter().position(|&byte| byte == b']').map(|at| index + 1 + at)
                else {
                    return false;
                };
                if close == index + 1 || pattern[index + 1..close].contains(&b'[') {
                    return false;
                }
                has_class = true;
                index = close + 1;
            }
            if !pattern.is_empty() {
                if has_class {
                    classes.push(pattern);
                } else {
                    literals.push(pattern);
                }
            }
            start = end + 1;
        }
        self.literals = literals;
        self.classes = classes;
        true
    }

    /// True when the part after the last dot is in the list, ignoring case.
    pub fn matches(&self, name: &[u8]) -> bool {
        let Some(slash) = name.iter().rposition(|&byte| byte == b'/') else { return self.matches_one(name) };
        self.matches_one(&name[slash + 1..])
    }

    fn matches_one(&self, name: &[u8]) -> bool {
        let Some(dot) = name.iter().rposition(|&byte| byte == b'.') else { return false };
        if dot + 1 == name.len() {
            return false;
        }
        let mut suffix = name[dot + 1..].to_vec();
        suffix.make_ascii_lowercase();
        if self.literals.contains(&suffix) {
            return true;
        }
        self.classes.iter().any(|pattern| suffix_match(pattern, &suffix))
    }
}

/// `suffix_match` in compression.cpp: a pattern such as `mp[34]` against the suffix.
fn suffix_match(pattern: &[u8], suffix: &[u8]) -> bool {
    let mut position = 0;
    let mut index = 0;
    while index < pattern.len() {
        if position == suffix.len() {
            return false;
        }
        if pattern[index] == b'[' {
            let Some(close) = pattern[index + 1..].iter().position(|&byte| byte == b']').map(|at| index + 1 + at)
            else {
                return false;
            };
            if !pattern[index + 1..close].contains(&suffix[position]) {
                return false;
            }
            index = close + 1;
        } else {
            if pattern[index] != suffix[position] {
                return false;
            }
            index += 1;
        }
        position += 1;
    }
    position == suffix.len()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_defaults_match_as_compression_cpp_does() {
        let suffixes = Suffixes::default();
        assert!(suffixes.matches(b"path.to/file.JPG"));
        assert!(suffixes.matches(b"movie.MP4"));
        assert!(suffixes.matches(b"archive.gz"));
        assert!(!suffixes.matches(b"path.gz/file"));
        assert!(!suffixes.matches(b"file.txt"));
        assert!(!suffixes.matches(b"plain"));
        assert!(!suffixes.matches(b"trailing."));
        assert!(!suffixes.matches(b".gz/"));
    }

    #[test]
    fn literals_character_classes_and_failed_assignments() {
        let mut suffixes = Suffixes::default();
        assert!(suffixes.assign(b"gz/jpg/mp[34]/literal*/q?/dash[a-]"));
        assert!(suffixes.matches(b"file.MP3") && suffixes.matches(b"file.mp4"));
        assert!(!suffixes.matches(b"file.mp5") && !suffixes.matches(b"file.literal-anything"));
        assert!(suffixes.matches(b"file.literal*") && suffixes.matches(b"file.q?"));
        assert!(suffixes.matches(b"file.dash-") && suffixes.matches(b"file.dasha"));
        for invalid in [&b"["[..], &b"[]"[..], &b"foo]"[..], &b"[nested[x]"[..]] {
            assert!(!suffixes.assign(invalid));
        }
        // A failed assignment keeps the previous policy.
        assert!(suffixes.matches(b"file.mp4"));
        assert!(!suffixes.assign(&vec![b'x'; 65537]));
        assert!(!suffixes.assign(b"gz\0jpg"));
    }

    #[test]
    fn an_empty_list_skips_nothing_and_an_empty_pattern_is_ignored() {
        let mut suffixes = Suffixes::default();
        assert!(suffixes.assign(b""));
        assert!(!suffixes.matches(b"file.mp4"));
        assert!(suffixes.assign(b"/gz//zip/"));
        assert!(suffixes.matches(b"file.gz") && suffixes.matches(b"file.zip") && !suffixes.matches(b"file.mp4"));
    }
}
