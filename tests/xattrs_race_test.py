#!/usr/bin/env python3
"""Source xattr changes during data reads must retry with fresh metadata."""
import os
import shlex
import subprocess
import sys
import time
import unittest

import delta_test as delta
REPO, BINARY = delta.REPO, delta.BINARY
from xattrs_test import DARWIN, attr_name, get_attrs, set_attr
PRIVILEGED_LINKS = sys.platform.startswith('linux') and os.environ.get('XSYNC_TEST_PRIVILEGED_XATTRS') == '1'


class XattrRaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        delta.DeltaTests.setUpClass.__func__(cls)
        if DARWIN:
            subprocess.run(['c++','-std=c++20','-dynamiclib','-fPIC','-arch','arm64','-arch','x86_64',
                            str(REPO / 'tests/fault_io.cpp'),'-o',str(cls.fault)],check=True,capture_output=True)
    tearDownClass = delta.DeltaTests.__dict__['tearDownClass']
    setUp = delta.DeltaTests.setUp

    def check_race(self, direction, link, whole, inplace):
        if link:
            self.source.symlink_to('referent')
        delta.DeltaTests.prepare(self, self.data + b'end', self.data)
        changing = 'trusted.xsync-changing' if link and PRIVILEGED_LINKS else attr_name('changing')
        set_attr(self.source, changing, b'old attribute')
        set_attr(self.dest, attr_name('stale'), b'remove me')
        source_data = self.source.read_bytes()
        marker = self.root / 'source-read'
        source, dest = str(self.source), str(self.dest)
        command = [str(BINARY), '--no-fallback', '--no-clone', '-aXL', '-j8']
        if whole: command += ['--whole-file']
        if inplace: command += ['--inplace']
        if direction != 'local':
            command += ['-e', shlex.quote(str(REPO / 'tests/fakessh.sh')), '--rsync-path=' + shlex.quote(str(BINARY))]
            if direction == 'push': dest = 'fake:' + dest
            else: source = 'fake:' + source
        env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')
        env['DYLD_INSERT_LIBRARIES' if DARWIN else 'LD_PRELOAD'] = str(self.fault)
        env.update(XSYNC_FAULT_PATH=str(self.source.resolve()))
        if whole:
            env.update(XSYNC_FAULT_READ_NOTIFY=str(marker), XSYNC_FAULT_READ_DELAY_US='300000')
        else:
            env.update(XSYNC_FAULT_PREAD_NOTIFY=str(marker), XSYNC_FAULT_PREAD_MIN_SIZE=str(512 * 1024),
                       XSYNC_FAULT_PREAD_DELAY_US='300000')
        if direction != 'local':
            # Apple's system shell clears DYLD variables. Put interposition back
            # in the explicit helper command after the shell has started.
            injected = [key + '=' + value for key, value in env.items() if key.startswith('XSYNC_FAULT_') or key in ('DYLD_INSERT_LIBRARIES','LD_PRELOAD')]
            command = [('--rsync-path=' + shlex.join(['env', *injected, str(BINARY)])) if arg.startswith('--rsync-path=') else arg for arg in command]
        if DARWIN and os.environ.get('XSYNC_TEST_ARCH'):
            actual = os.environ['XSYNC_TEST_EXECUTABLE']
            launcher = ['/usr/bin/arch','-' + os.environ['XSYNC_TEST_ARCH'],'-e','DYLD_INSERT_LIBRARIES=' + str(self.fault),actual]
            command = launcher + command[1:]
            command = [('--rsync-path=' + shlex.join(['env', *injected, *launcher])) if arg.startswith('--rsync-path=') else arg for arg in command]
        observed_marker = marker.with_name(marker.name + '.1') if whole else marker
        proc = subprocess.Popen(command + [source, dest], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            deadline = time.monotonic() + 10
            while not observed_marker.exists() and proc.poll() is None and time.monotonic() < deadline: time.sleep(.002)
            self.assertTrue(observed_marker.exists(), 'sender did not reach delayed source read')
            set_attr(self.source, changing, b'new binary attribute\0\xff')
            expected = get_attrs(self.source)
            out, err = proc.communicate(timeout=30)
            self.assertEqual(proc.returncode, 0, (out, err))
            self.assertEqual(self.dest.read_bytes(), source_data)
            self.assertEqual(get_attrs(self.dest), expected)
            self.assertEqual(self.source.read_bytes(), source_data)
            self.assertEqual(get_attrs(self.source), expected)
            self.assertEqual(self.dest.stat().st_mtime_ns, self.source.stat().st_mtime_ns)
        finally:
            if proc.poll() is None: proc.kill()
            proc.communicate()
            if self.source.is_symlink(): self.source.unlink()
            for file in self.root.glob(marker.name + '*'): file.unlink()

    def test_file_attributes_refresh_on_retry(self):
        for direction in ('local', 'push', 'pull'):
            for whole in (False, True):
                for inplace in (False, True):
                    with self.subTest(direction=direction, whole=whole, inplace=inplace):
                        self.check_race(direction, False, whole, inplace)

    @unittest.skipUnless(DARWIN or PRIVILEGED_LINKS, 'physical symlink attrs require Darwin or the privileged Linux fixture')
    def test_followed_link_attributes_refresh_on_retry(self):
        for direction in ('local', 'push', 'pull'):
            for whole in (False, True):
                with self.subTest(direction=direction, whole=whole):
                    self.check_race(direction, True, whole, False)


if __name__ == '__main__': unittest.main()
