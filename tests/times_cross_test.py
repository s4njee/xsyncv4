#!/usr/bin/env python3
"""Opt-in real SSH access-time differentials between Darwin and Linux."""
import os
import subprocess
import unittest

import acls_cross_test as rig
import output_test as transfer
from xattrs_test import RSYNC


class CrossPlatformTimeTests(rig.CrossStyleAclTests):
    test_cross_style_refusal_and_rsync_fallback = None

    def test_access_times_over_cross_platform_ssh(self):
        for direction in ('push', 'pull'):
            for flags in ('-rtUi', '-rtUUi'):
                with self.subTest(direction=direction, flags=flags):
                    results = []
                    for native in (False, True):
                        name = direction + flags + str(native)
                        local = self.root / name; remote = '/rig/' + name
                        os.utime(self.source / 'file', ns=(1200000000123456789, 1500000000000000000))
                        self.remote('python3', '-c', "import os; os.utime('/rig/source/file',ns=(1200000000123456789,1500000000000000000))")
                        args = [str(transfer.BINARY) if native else RSYNC, flags, '--out-format=%i|%n', '-e', self.rsh]
                        if native: args += ['--no-fallback', '--rsync-path=/rig/helper']
                        if direction == 'push': args += [str(self.source) + '/', 'root@127.0.0.1:' + remote + '/']
                        else: args += ['root@127.0.0.1:/rig/source/', str(local) + '/']
                        result = subprocess.run(args, capture_output=True, timeout=30,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
                        if direction == 'push':
                            times = self.remote('python3', '-c', "import pathlib,sys; p=pathlib.Path(sys.argv[1]); s=p.stat(); print(s.st_atime_ns,s.st_mtime_ns); assert p.read_bytes()==b'contents'", remote + '/file')
                        else:
                            file = local / 'file'; st = file.stat()
                            times = str(st.st_atime_ns) + ' ' + str(st.st_mtime_ns)
                            self.assertEqual(file.read_bytes(), b'contents')
                        self.assertEqual(times, '1200000000000000000 1500000000000000000')
                        results.append((times, sorted(row for row in result.stdout.splitlines() if b'|' in row)))
                    self.assertEqual(results[1], results[0])


if __name__ == '__main__': unittest.main()
