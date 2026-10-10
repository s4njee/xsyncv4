#!/usr/bin/env python3
"""Verify bounded APFS subtree transactions against rsync and clone interposition."""
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time
import unittest

import link_dest_test as snapshots
from xattrs_test import DARWIN, RSYNC


@unittest.skipUnless(DARWIN, 'APFS subtree cloning requires macOS')
class SubtreeCloneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): snapshots.LinkDestFailures.setUpClass.__func__(cls)
    environment = snapshots.LinkDestFailures.environment

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-subtree-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / 'source'
        self.branch = self.source / 'branch'
        self.branch.mkdir(parents=True)

    def contents(self, path):
        result = {}
        for p in [path, *sorted(path.rglob('*'))]:
            s = p.lstat()
            result[str(p.relative_to(path))] = (s.st_mode, s.st_uid, s.st_gid, s.st_mtime_ns,
                p.read_bytes() if stat.S_ISREG(s.st_mode) else os.readlink(p) if p.is_symlink() else None)
        return result

    def fix_times(self):
        for path in [self.source, *self.source.rglob('*')]:
            os.utime(path, ns=(1500000000123456789, 1500000000123456789), follow_symlinks=False)

    def compare(self, flags=('-a',), mask=0o22, fault=None):
        self.fix_times()
        before = self.contents(self.source)
        marker = self.root / 'clone-notify'
        reads = self.root / 'read-notify'
        for p in (marker, reads.with_name('read-notify.1')):
            if p.exists(): p.unlink()
        env = self.environment(self.source)
        env['XSYNC_CONFIG'] = env['XSYNC_OPTS'] = ''
        env.update(XSYNC_FAULT_CLONE_NOTIFY=str(marker), XSYNC_FAULT_READ_NOTIFY=str(reads))
        if fault: env['XSYNC_FAULT_CLONE_EXDEV'] = '1'
        for binary, name in ((RSYNC, 'oracle'), (str(self.injected_binary), 'candidate')):
            target = self.root / name
            if target.exists(): shutil.rmtree(target)
            command = [binary, *flags]
            if name == 'candidate': command += ['--no-fallback', '--no-progress', '-j1']
            command += [str(self.source) + '/', str(target) + '/']
            done = subprocess.run(command, env=env if name == 'candidate' else None,
                                  capture_output=True, umask=mask, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
        proof = subprocess.run([RSYNC, '-anci', '--delete', str(self.root/'oracle')+'/',
                                str(self.root/'candidate')+'/'], capture_output=True, timeout=60)
        self.assertEqual((proof.returncode, proof.stdout), (0, b''), proof.stderr)
        self.assertEqual(self.contents(self.root/'oracle'), self.contents(self.root/'candidate'))
        self.assertEqual(before, self.contents(self.source), 'source changed')
        self.assertTrue(marker.exists(), 'clone interposition did not observe a clone')
        return marker.read_text(), reads.with_name('read-notify.1').exists()

    def test_nested_clone_corrects_omitted_modes_and_requested_groups(self):
        inner = self.branch / 'inner' / 'leaf'
        inner.mkdir(parents=True)
        groups = [g for g in os.getgroups() if g != os.getegid()]
        if groups:
            os.chown(self.branch, -1, groups[0])
            os.chown(inner, -1, groups[0])
        for n in range(6):
            p = inner / f'file-{n}'
            p.write_bytes(bytes([n]) * 1024)
            p.chmod(0o444 if n % 2 else 0o644)
            if groups and n % 2: os.chown(p, -1, groups[0])
        (inner / 'link').symlink_to('file-0')
        for flag in ('-a', '-rt', '-rlt', '-rltg'):
            for mask in (0o22, 0o77):
                with self.subTest(flag=flag, mask=mask):
                    clone, reads = self.compare((flag,), mask)
                    if flag == '-rt':
                        self.assertNotEqual(clone, str(self.branch), 'unrequested nested link must not be cloned')
                    else:
                        self.assertEqual(clone, str(self.branch))
                    self.assertFalse(reads, 'whole clone fell back to file reads')

    def test_total_entry_bound_includes_all_sibling_subtrees(self):
        for dirname in ('a', 'b'):
            leaf = self.branch / dirname
            leaf.mkdir()
            for n in range(2047): (leaf / f'file-{n}').write_bytes(str(n).encode())
        clone, _ = self.compare()
        self.assertEqual(clone, str(self.branch), '4096 descendants should fit one transaction')
        (self.branch/'b'/'extra').write_bytes(b'over the complete tree limit')
        clone, _ = self.compare()
        self.assertNotEqual(clone, str(self.branch), '4097 descendants exceeded the transaction limit')

    def test_deep_small_tree_falls_back_to_a_bounded_child(self):
        leaf = self.branch
        for _ in range(33): leaf /= 'd'; leaf.mkdir()
        (leaf/'file').write_bytes(b'deep payload')
        clone, _ = self.compare()
        self.assertNotEqual(clone, str(self.branch), '33 levels exceeded the root transaction limit')

    def test_unsafe_nested_symlink_is_excluded(self):
        inner = self.branch/'inner'
        inner.mkdir()
        (inner/'file').write_bytes(b'safe')
        (inner/'escape').symlink_to('/outside-source')
        clone, _ = self.compare(('-a', '--safe-links'))
        self.assertNotEqual(clone, str(self.branch))
        self.assertFalse((self.root/'candidate'/'branch'/'inner'/'escape').exists())

    def test_failed_whole_clone_falls_back_to_byte_copy(self):
        inner = self.branch/'inner'
        inner.mkdir()
        (inner/'file').write_bytes(b'fallback payload' * 1024)
        clone, reads = self.compare(fault=True)
        self.assertEqual(clone, str(self.branch))
        self.assertTrue(reads, 'failed clone did not reach the byte-copy path')

    def test_nontrailing_source_updates_parent_mtime(self):
        inner = self.branch/'inner'
        inner.mkdir()
        (inner/'file').write_bytes(b'parent timestamp')
        self.fix_times()
        for binary, name in ((RSYNC, 'oracle'), (str(self.injected_binary), 'candidate')):
            target = self.root/name
            target.mkdir()
            os.utime(target, ns=(1500000000000000000, 1500000000000000000))
            started = time.time_ns()
            command = [binary, '-a']
            if name == 'candidate': command += ['--no-fallback', '--no-progress', '-j1']
            done = subprocess.run(command+[str(self.branch), str(target)+'/'], capture_output=True, timeout=30)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertGreaterEqual(target.stat().st_mtime_ns, started)
            self.assertLessEqual(target.stat().st_mtime_ns, time.time_ns())
        self.assertEqual(self.contents(self.root/'oracle'/'branch'), self.contents(self.root/'candidate'/'branch'))


if __name__ == '__main__': unittest.main()
