#!/usr/bin/env python3
"""Source ownership changes refresh omitted fields across transfer retries."""
import os
import shlex
import subprocess
import time
import unittest

import delta_test as delta
import xattrs_race_test as race
from xattrs_test import DARWIN


@unittest.skipUnless(not DARWIN and os.geteuid() == 0, 'Linux root ownership mutations')
class OwnershipRaceTests(unittest.TestCase):
    setUpClass = race.XattrRaceTests.__dict__['setUpClass']
    tearDownClass = delta.DeltaTests.__dict__['tearDownClass']
    setUp = delta.DeltaTests.setUp

    def test_fresh_ownership_preserves_overrides_and_refreshes_omitted_fields(self):
        for direction in ('local', 'push', 'pull'):
            for whole in (False, True):
                for inplace in (False, True):
                    for target, expected in (('0', (0, 60003)), (':0', (60002, 0)), ('0:0', (0, 0))):
                        with self.subTest(direction=direction, whole=whole, inplace=inplace, target=target):
                            delta.DeltaTests.prepare(self, self.data + b'end', self.data)
                            os.chown(self.source, 60000, 60001); os.chown(self.dest, 60004, 60005)
                            self.source.chmod(0o755); self.dest.chmod(0o640)
                            marker = self.root / 'source-read'
                            command = [str(delta.BINARY), '--no-fallback', '--no-clone', '-j8', '-a', '--chown=' + target]
                            if whole: command += ['--whole-file']
                            if inplace: command += ['--inplace']
                            source, dest = str(self.source), str(self.dest)
                            env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FAULT_PATH=str(self.source.resolve()),
                                       LD_PRELOAD=str(self.fault))
                            if whole: env.update(XSYNC_FAULT_READ_NOTIFY=str(marker), XSYNC_FAULT_READ_DELAY_US='300000')
                            else: env.update(XSYNC_FAULT_PREAD_NOTIFY=str(marker), XSYNC_FAULT_PREAD_MIN_SIZE=str(512 * 1024),
                                             XSYNC_FAULT_PREAD_DELAY_US='300000')
                            injected = [k + '=' + v for k, v in env.items() if k.startswith('XSYNC_FAULT_') or k == 'LD_PRELOAD']
                            if direction != 'local':
                                command += ['-e', shlex.quote(str(delta.REPO / 'tests/fakessh.sh')),
                                            '--rsync-path=' + shlex.join(['env', *injected, str(delta.BINARY)])]
                                if direction == 'push': dest = 'fake:' + dest
                                else: source = 'fake:' + source
                            proc = subprocess.Popen(command + [source, dest], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                            try:
                                observed = marker.with_name(marker.name + '.1') if whole else marker
                                deadline = time.monotonic() + 10
                                while not observed.exists() and proc.poll() is None and time.monotonic() < deadline: time.sleep(.002)
                                if not observed.exists():
                                    out, err = proc.communicate(timeout=10)
                                    self.fail(('source read never reached delay', proc.returncode, out, err))
                                os.chown(self.source, 60002, 60003)
                                out, err = proc.communicate(timeout=30)
                                self.assertEqual(proc.returncode, 0, (out, err))
                                st = self.dest.stat()
                                self.assertEqual((st.st_uid, st.st_gid), expected)
                                self.assertEqual(st.st_mode & 0o7777, 0o755)
                                self.assertEqual(self.dest.read_bytes(), self.data + b'end')
                                st = self.source.stat(); self.assertEqual((st.st_uid, st.st_gid), (60002, 60003))
                            finally:
                                if proc.poll() is None: proc.kill()
                                proc.communicate()
                                for path in self.root.glob(marker.name + '*'): path.unlink()


if __name__ == '__main__': unittest.main()
