#!/usr/bin/env python3
"""Source BSD flag changes during reads must survive the retry."""
import os
import shlex
import subprocess
import time
import stat
import unittest

import delta_test as delta
import xattrs_race_test as race
from xattrs_test import DARWIN


@unittest.skipUnless(DARWIN, 'native BSD flags')
class FileflagsRaceTests(unittest.TestCase):
    setUpClass = race.XattrRaceTests.__dict__['setUpClass']
    tearDownClass = delta.DeltaTests.__dict__['tearDownClass']
    setUp = delta.DeltaTests.setUp

    def test_flags_refresh_on_retry(self):
        for direction in ('local', 'push', 'pull'):
            for whole in (False, True):
                for inplace in (False, True):
                    for initial, fresh, expected in ((stat.UF_NODUMP, stat.UF_IMMUTABLE, stat.UF_IMMUTABLE), (stat.UF_IMMUTABLE, stat.UF_HIDDEN, stat.UF_HIDDEN)):
                        with self.subTest(direction=direction, whole=whole, inplace=inplace, fresh=fresh):
                            delta.DeltaTests.prepare(self, self.data + b'end', self.data)
                            os.chflags(self.source, initial); os.chflags(self.dest, 0)
                            marker = self.root / 'source-read'
                            command = [str(delta.BINARY), '--no-fallback', '--no-clone', '-a', '--fileflags', '-j8']
                            if whole: command += ['--whole-file']
                            if inplace: command += ['--inplace']
                            source, dest = str(self.source), str(self.dest)
                            env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FAULT_PATH=str(self.source.resolve()))
                            env['DYLD_INSERT_LIBRARIES' if DARWIN else 'LD_PRELOAD'] = str(self.fault)
                            if whole: env.update(XSYNC_FAULT_READ_NOTIFY=str(marker), XSYNC_FAULT_READ_DELAY_US='300000')
                            else: env.update(XSYNC_FAULT_PREAD_NOTIFY=str(marker), XSYNC_FAULT_PREAD_MIN_SIZE=str(512 * 1024),
                                             XSYNC_FAULT_PREAD_DELAY_US='300000')
                            injected = [k + '=' + v for k, v in env.items() if k.startswith('XSYNC_FAULT_') or k in ('DYLD_INSERT_LIBRARIES', 'LD_PRELOAD')]
                            helper = ['env', *injected, str(delta.BINARY)]
                            if DARWIN and os.environ.get('XSYNC_TEST_ARCH'):
                                launcher = ['/usr/bin/arch', '-' + os.environ['XSYNC_TEST_ARCH'], '-e',
                                            'DYLD_INSERT_LIBRARIES=' + str(self.fault), os.environ['XSYNC_TEST_EXECUTABLE']]
                                command = launcher + command[1:]; helper = ['env', *injected, *launcher]
                            if direction != 'local':
                                command += ['-e', shlex.quote(str(delta.REPO / 'tests/fakessh.sh')), '--rsync-path=' + shlex.join(helper)]
                                if direction == 'push': dest = 'fake:' + dest
                                else: source = 'fake:' + source
                            proc = subprocess.Popen(command + [source, dest], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                            try:
                                observed = marker.with_name(marker.name + '.1') if whole else marker
                                deadline = time.monotonic() + 10
                                while not observed.exists() and proc.poll() is None and time.monotonic() < deadline: time.sleep(.002)
                                if not observed.exists():
                                    out, err = proc.communicate(timeout=10)
                                    self.fail(('source read never reached the delay', proc.returncode, out, err))
                                os.chflags(self.source, fresh)
                                out, err = proc.communicate(timeout=30)
                                self.assertEqual(proc.returncode, 0, (out, err))
                                self.assertEqual(self.dest.stat().st_flags, expected)
                                self.assertEqual(self.dest.read_bytes(), self.data + b'end')
                                self.assertEqual(self.source.stat().st_flags, fresh)
                            finally:
                                if proc.poll() is None: proc.kill()
                                proc.communicate()
                                for path in (self.source, self.dest):
                                    if path.exists(): os.chflags(path, 0)
                                for path in self.root.glob(marker.name + '*'): path.unlink()


if __name__ == '__main__': unittest.main()
