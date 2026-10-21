//! Receiver-side hard links: group source inodes, elect an anchor that holds the
//! data, publish aliases as links, and itemize them as `src/hardlink.cpp` does.

use std::collections::BTreeMap;
use std::fs;
use std::io::{self, Write};
use std::os::unix::fs::MetadataExt;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use xs_wire::OutputEvent;

use crate::output::Output;
use crate::protocol::{feature, Attrs, EntryMeta, HardlinkKey, Options, T_BLK, T_CHR, T_LNK, T_REG};

use super::{report_event, FrameOut};

#[derive(Clone, Debug)]
pub(super) struct HLinkMember {
    rel: Vec<u8>,
    path: PathBuf,
    source: Vec<u8>,
    kind: u8,
    attrs: Attrs,
    existed: bool,
    before_inode: Option<(u64, u64)>,
    follower: bool,
    event: Option<OutputEvent>,
}

#[derive(Clone, Debug, Default)]
pub(super) struct HLinkGroup {
    members: Vec<HLinkMember>,
    leader: Option<usize>,
}

/// The receiver's view of `src/hardlink.cpp`: source inodes are claimed by the
/// first name that holds their data, later new names follow it, and every group
/// is linked once all data has arrived.
#[derive(Clone, Debug)]
pub(super) struct HardLinks {
    pub(super) enabled: bool,
    groups: BTreeMap<HardlinkKey, HLinkGroup>,
}

impl HardLinks {
    pub(super)     fn new(enabled: bool) -> Self {
        Self { enabled, groups: BTreeMap::new() }
    }

    pub(super)     fn key(entry: &EntryMeta, features: u64) -> Option<HardlinkKey> {
        if features & feature::HLINK == 0 {
            return None;
        }
        entry.attrs.hardlink_key(entry.kind, &entry.link)
    }

    pub(super)     fn register_ready(&mut self, key: HardlinkKey, member: HLinkMember) {
        let group = self.groups.entry(key).or_default();
        let index = group.members.len();
        group.members.push(member);
        if group.leader.is_none() {
            group.leader = Some(index);
        }
    }

    /// Returns true when this new name may reuse an inode another name holds.
    pub(super)     fn register_transfer(&mut self, key: HardlinkKey, mut member: HLinkMember, may_follow: bool) -> bool {
        let group = self.groups.entry(key).or_default();
        if may_follow && group.leader.is_some() {
            member.follower = true;
            group.members.push(member);
            return true;
        }
        let index = group.members.len();
        group.members.push(member);
        if group.leader.is_none() {
            group.leader = Some(index);
        }
        false
    }

    pub(super)     fn defer_event(&mut self, key: &HardlinkKey, rel: &[u8], event: OutputEvent) {
        if let Some(member) = self.groups.get_mut(key).and_then(|group| group.members.iter_mut().find(|m| m.rel == rel)) {
            member.event = Some(event);
        }
    }
}

pub(super) fn hardlink_member(entry: &EntryMeta, rel: &[u8], path: &Path, before: Option<&super::file::Stat>) -> HLinkMember {
    let existed = before.map(|m| m.kind() == entry.kind).unwrap_or(false);
    HLinkMember {
        rel: rel.to_vec(),
        path: path.to_path_buf(),
        source: entry.output_source.clone(),
        kind: entry.kind,
        attrs: entry.attrs.clone(),
        existed,
        before_inode: if existed { before.map(|m| (m.dev(), m.ino())) } else { None },
        follower: false,
        event: None,
    }
}

pub(super) fn hardlink_dir(rel: &[u8]) -> &[u8] {
    match rel.iter().rposition(|&byte| byte == b'/') {
        Some(slash) => &rel[..slash],
        None => &[],
    }
}

pub(super) fn kind_letter(kind: u8) -> u8 {
    match kind {
        T_REG => b'f',
        T_LNK => b'L',
        T_CHR | T_BLK => b'D',
        _ => b'S',
    }
}

pub(super) fn linked_event(member: &HLinkMember, anchor: &HLinkMember, already: bool) -> OutputEvent {
    let mut event = member.event.clone().unwrap_or_default();
    event.path = member.rel.clone();
    event.source = member.source.clone();
    event.kind = member.kind;
    event.size = member.attrs.size;
    if already {
        event.code = b"hf         ".to_vec();
        event.target = Vec::new();
        event.hardlink_target = false;
    } else {
        event.target = anchor.rel.clone();
        event.hardlink_target = true;
        if !member.existed {
            event.code = b"hf+++++++++".to_vec();
        } else if event.code.is_empty() {
            event.code = b".f         ".to_vec();
        }
    }
    if event.code.len() >= 2 {
        event.code[0] = b'h';
        event.code[1] = kind_letter(member.kind);
    }
    event
}

pub(super) fn same_inode(left: &Path, right: &Path) -> bool {
    match (fs::symlink_metadata(left), fs::symlink_metadata(right)) {
        (Ok(a), Ok(b)) => a.dev() == b.dev() && a.ino() == b.ino(),
        _ => false,
    }
}

pub(super) fn publish_hardlink(source: &Path, target: &Path) -> io::Result<()> {
    if same_inode(source, target) {
        return Ok(());
    }
    static ATTEMPT: AtomicU64 = AtomicU64::new(0);
    let parent = target.parent().filter(|p| !p.as_os_str().is_empty()).unwrap_or(Path::new("."));
    for _ in 0..100 {
        let temp = parent.join(format!(".xsync-hardlink-{}-{}", std::process::id(), ATTEMPT.fetch_add(1, Ordering::Relaxed)));
        match fs::hard_link(source, &temp) {
            Ok(()) => {
                let result = fs::rename(&temp, target);
                if result.is_err() {
                    let _ = fs::remove_file(&temp);
                }
                return result;
            }
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error),
        }
    }
    Err(io::Error::new(io::ErrorKind::AlreadyExists, "cannot create a temporary hard link"))
}

#[allow(clippy::too_many_arguments)]
pub(super) fn finalize_hardlinks<W: Write + Send + 'static>(
    hardlinks: &mut HardLinks,
    output: &mut FrameOut<W>,
    features: u64,
    opts: &Options,
    created_files: &mut u64,
    mut local_output: Option<&mut Output>,
) -> io::Result<()> {
    let groups = std::mem::take(&mut hardlinks.groups);
    for (_, mut group) in groups {
        if group.members.is_empty() {
            continue;
        }
        // `hardlink_finalize` sorts by parent directory then relative name. A
        // regular group's first choice is its last member; an existing name wins.
        let mut order: Vec<usize> = (0..group.members.len()).collect();
        order.sort_by(|&left, &right| {
            let a = &group.members[left];
            let b = &group.members[right];
            (hardlink_dir(&a.rel), &a.rel).cmp(&(hardlink_dir(&b.rel), &b.rel))
        });
        let mut anchor_index = order[0];
        if group.members[anchor_index].kind == T_REG {
            anchor_index = *order.last().unwrap();
        }
        for &index in &order {
            if group.members[index].existed {
                anchor_index = index;
                break;
            }
        }
        if fs::symlink_metadata(&group.members[anchor_index].path).is_err() {
            // The name reported as transferred may be an alias. Link the name
            // that holds the data into it first, as hardlink_finalize does.
            let holder_index = group
                .leader
                .filter(|&i| fs::symlink_metadata(&group.members[i].path).is_ok())
                .or_else(|| order.iter().copied().find(|&i| fs::symlink_metadata(&group.members[i].path).is_ok()));
            let Some(holder_index) = holder_index else {
                if group.members.len() > 1 {
                    eprintln!(
                        "xs-rs: cannot link \"{}\": its data was not transferred",
                        String::from_utf8_lossy(&group.members[0].rel)
                    );
                }
                continue;
            };
            if holder_index != anchor_index {
                let holder_path = group.members[holder_index].path.clone();
                let holder_event = group.members[holder_index].event.clone();
                publish_hardlink(&holder_path, &group.members[anchor_index].path)?;
                if !group.members[anchor_index].existed {
                    *created_files += 1;
                }
                if let Some(mut event) = holder_event {
                    event.path = group.members[anchor_index].rel.clone();
                    event.source = group.members[anchor_index].source.clone();
                    group.members[anchor_index].event = Some(event);
                }
            }
        }
        let anchor = group.members[anchor_index].clone();
        if let Some(event) = anchor.event.clone() {
            report_event(output, local_output.as_deref_mut(), features, opts, event)?;
        }
        for (index, member) in group.members.iter().enumerate() {
            if index == anchor_index {
                continue;
            }
            let already = same_inode(&anchor.path, &member.path);
            if !already {
                publish_hardlink(&anchor.path, &member.path)?;
                if !member.existed {
                    *created_files += 1;
                }
            }
            let original = member.existed
                && anchor.existed
                && member.before_inode == anchor.before_inode;
            let already_output = original && already;
            if !already_output || opts.output_unchanged {
                let event = linked_event(member, &anchor, already_output);
                report_event(output, local_output.as_deref_mut(), features, opts, event)?;
            }
        }
    }
    Ok(())
}
