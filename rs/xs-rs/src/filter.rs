//! rsync filter rules as `src/filter.cpp` implements them.

use std::fs;
use std::path::Path;

#[derive(Clone, Debug)]
struct Rule {
    text: Vec<u8>,
    pat: Vec<u8>,
    path: bool,
    anchored: bool,
    include: bool,
    negate: bool,
    dir_only: bool,
    sides: u8,
    prefix: u8,
    modifiers: Vec<u8>,
    merged: Option<Box<FilterList>>,
    merge: bool,
    cvs: bool,
}

#[derive(Clone, Default, Debug)]
pub struct FilterList {
    rules: Vec<Rule>,
    pub from0: bool,
}

fn wildmatch(pat: &[u8], text: &[u8], is_dir: bool) -> bool {
    let mut pat = pat;
    if pat.ends_with(b"***") && is_dir {
        let mut owned = text.to_vec();
        owned.push(b'/');
        return dowild(pat, &owned);
    }
    if pat.starts_with(b"**/") && !text.contains(&b'/') {
        pat = &pat[3..];
    }
    dowild(pat, text)
}

fn dowild(p: &[u8], t: &[u8]) -> bool {
    if p.is_empty() {
        return t.is_empty();
    }
    match p[0] {
        b'*' => {
            let mut starstar = false;
            let mut pi = 1;
            if pi < p.len() && p[pi] == b'*' {
                while pi < p.len() && p[pi] == b'*' {
                    pi += 1;
                }
                starstar = true;
            }
            if pi == p.len() {
                return starstar || !t.contains(&b'/');
            }
            if starstar {
                (0..=t.len()).any(|k| dowild(&p[pi..], &t[k..]))
            } else {
                let mut k = 0;
                loop {
                    if dowild(&p[pi..], &t[k..]) {
                        return true;
                    }
                    if k == t.len() || t[k] == b'/' {
                        return false;
                    }
                    k += 1;
                }
            }
        }
        _ if t.is_empty() => false,
        b'?' => t[0] != b'/' && dowild(&p[1..], &t[1..]),
        b'\\' => p.len() > 1 && t[0] == p[1] && dowild(&p[2..], &t[1..]),
        pc => t[0] == pc && dowild(&p[1..], &t[1..]),
    }
}

impl FilterList {
    pub fn empty(&self) -> bool {
        self.rules.is_empty()
    }

    pub fn needs_extended(&self) -> bool {
        self.rules.iter().any(|r| {
            r.merge
                || r.cvs
                || r.sides != 0
                || r.modifiers.iter().any(|m| matches!(m, b'/' | b'p' | b'x'))
        })
    }

    pub fn has_merges(&self) -> bool {
        self.rules.iter().any(|r| r.merge)
    }

    pub fn has_cvs(&self) -> bool {
        self.rules.iter().any(|r| r.cvs)
    }

    pub fn add_old_style(&mut self, whole: &[u8], include: bool) -> Result<(), String> {
        if whole.is_empty() {
            return Ok(());
        }
        let pat = whole;
        if pat.is_empty() {
            return Err(format!("unexpected end of filter rule: {}", String::from_utf8_lossy(whole)));
        }
        self.add_rule(pat, include, false);
        Ok(())
    }

    pub fn add_filter(&mut self, rule: &[u8]) -> Result<(), String> {
        if rule.is_empty() {
            return Ok(());
        }
        let fail = |what: &str| Err(format!("{what}: {}", String::from_utf8_lossy(rule)));
        let at = |i: usize| rule.get(i).copied().unwrap_or(0);
        let ch = rule[0];
        let mut i = usize::from(at(1) == b',');
        if !matches!(ch, b'+' | b'-' | b'!' | b'H' | b'S' | b'P' | b'R' | b'.' | b':') {
            return fail("unknown filter rule");
        }
        let merge = ch == b'.' || ch == b':';
        let mut sides = if matches!(ch, b'H' | b'S') {
            1
        } else if matches!(ch, b'P' | b'R') {
            2
        } else {
            0
        };
        let mut negate = false;
        let mut modifiers = Vec::new();
        if ch != b'!' {
            loop {
                i += 1;
                let m = at(i);
                if m == 0 || m == b' ' || m == b'_' {
                    break;
                }
                if !b"!/sprxCenw+-".contains(&m) {
                    return fail(if b"/Cenprswx".contains(&m) {
                        "unsupported modifier in filter rule"
                    } else {
                        "invalid modifier in filter rule"
                    });
                }
                negate |= m == b'!';
                sides |= if m == b's' { 1 } else if m == b'r' { 2 } else { 0 };
                modifiers.push(m);
            }
        }
        let pat = rule.get(i.saturating_add(1).min(rule.len())..).unwrap_or_default();
        if ch == b'!' {
            if !pat.is_empty() {
                return fail("'!' rule has trailing characters");
            }
            self.rules.clear();
            return Ok(());
        }
        let cvs = modifiers.contains(&b'C');
        if pat.is_empty() && !cvs {
            return fail("unexpected end of filter rule");
        }
        let mut rule = self.base_rule(pat, ch, matches!(ch, b'+' | b'S' | b'R'), negate, sides, &modifiers);
        if cvs && !merge {
            rule.cvs = true;
            rule.merged = Some(Box::new(FilterList::default()));
        } else if merge {
            if ch == b'.' {
                return Ok(());
            }
            rule.merge = true;
            rule.text = if pat.is_empty() { b".cvsignore".to_vec() } else { pat.to_vec() };
        } else {
            let mut pat = rule.pat.clone();
            if pat.len() > 1 && pat.ends_with(b"/") {
                pat.pop();
                rule.dir_only = true;
            }
            rule.anchored = pat.first() == Some(&b'/');
            if rule.anchored {
                pat.remove(0);
            }
            rule.path = pat.contains(&b'/');
            rule.pat = pat;
        }
        self.rules.push(rule);
        Ok(())
    }

    fn base_rule(&self, pat: &[u8], prefix: u8, include: bool, negate: bool, sides: u8, modifiers: &[u8]) -> Rule {
        Rule {
            text: pat.to_vec(),
            pat: pat.to_vec(),
            path: false,
            anchored: false,
            include,
            negate,
            dir_only: false,
            sides,
            prefix,
            modifiers: modifiers.to_vec(),
            merged: None,
            merge: false,
            cvs: false,
        }
    }

    fn add_rule(&mut self, pat: &[u8], include: bool, negate: bool) {
        let mut rule = self.base_rule(pat, if include { b'+' } else { b'-' }, include, negate, 0, b"");
        let mut pat = rule.pat.clone();
        if pat.len() > 1 && pat.ends_with(b"/") {
            pat.pop();
            rule.dir_only = true;
        }
        rule.anchored = pat.first() == Some(&b'/');
        if rule.anchored {
            pat.remove(0);
        }
        rule.path = pat.contains(&b'/');
        rule.pat = pat;
        self.rules.push(rule);
    }

    pub fn to_strings(&self) -> Vec<Vec<u8>> {
        self.rules
            .iter()
            .map(|r| {
                let mut s = vec![r.prefix];
                s.extend_from_slice(&r.modifiers);
                s.push(b' ');
                s.extend_from_slice(&r.text);
                s
            })
            .collect()
    }

    pub fn excluded(&self, path: &[u8], is_dir: bool) -> bool {
        self.decide(path, is_dir) == Some(false)
    }

    fn decide(&self, path: &[u8], is_dir: bool) -> Option<bool> {
        if path.is_empty() {
            return None;
        }
        let slash = path.iter().rposition(|&c| c == b'/');
        let base = slash.map(|at| &path[at + 1..]).unwrap_or(path);
        for r in &self.rules {
            if r.merge || r.cvs {
                if let Some(merged) = &r.merged {
                    if let Some(result) = merged.decide(path, is_dir) {
                        return Some(result);
                    }
                }
                continue;
            }
            let sides = if r.sides != 0 { r.sides } else { 3 };
            if sides & 1 == 0 || (!is_dir && r.dir_only) {
                continue;
            }
            let matched = if !r.path {
                wildmatch(&r.pat, base, false)
            } else if r.anchored {
                wildmatch(&r.pat, path, is_dir)
            } else {
                let mut text = path;
                let mut matched = wildmatch(&r.pat, text, is_dir);
                while !matched {
                    let Some(at) = text.iter().position(|&c| c == b'/') else { break };
                    text = &text[at + 1..];
                    matched = wildmatch(&r.pat, text, is_dir);
                }
                matched
            };
            if matched != r.negate {
                return Some(r.include);
            }
        }
        None
    }

    pub fn in_directory(&self, physical: &Path, receiver: bool) -> FilterList {
        let mut result = self.clone();
        for rule in &mut result.rules {
            if !rule.merge || (rule.sides != 0 && rule.sides & if receiver { 2 } else { 1 } == 0) {
                continue;
            }
            let file = physical.join(String::from_utf8_lossy(&rule.text).as_ref());
            let mut local = FilterList { rules: Vec::new(), from0: self.from0 };
            if let Ok(content) = fs::read(file) {
                let no_prefix = rule.modifiers.iter().any(|m| matches!(m, b'+' | b'-' | b'C'));
                local.load_merge(&content, rule, no_prefix);
            }
            if let Some(inherited) = &rule.merged {
                if !rule.modifiers.iter().any(|m| matches!(m, b'n' | b'C')) {
                    local.rules.extend(inherited.rules.iter().cloned());
                }
            }
            rule.merged = Some(Box::new(local.in_directory(physical, receiver)));
        }
        result
    }

    fn load_merge(&mut self, content: &[u8], defaults: &Rule, no_prefix: bool) {
        let from0 = self.from0;
        let mut rest = content;
        loop {
            let end = if from0 {
                rest.iter().position(|&b| b == 0)
            } else {
                rest.iter().position(|&b| b == b'\r' || b == b'\n')
            };
            let line = &rest[..end.unwrap_or(rest.len())];
            let line = &line[..line.iter().position(|&b| b == 0).unwrap_or(line.len())];
            if !line.is_empty() && !matches!(line[0], b'#' | b';') {
                let before = self.rules.len();
                if no_prefix {
                    self.add_rule(line, defaults.include || defaults.modifiers.contains(&b'+'), defaults.negate);
                } else {
                    let _ = self.add_filter(line);
                }
                for rule in &mut self.rules[before..] {
                    rule.sides |= defaults.sides;
                    rule.negate |= defaults.negate;
                }
            }
            match end {
                Some(at) => rest = &rest[at + 1..],
                None => break,
            }
        }
    }
}


