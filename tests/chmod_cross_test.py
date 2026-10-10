#!/usr/bin/env python3
"""Permission override differentials over real Darwin/Linux SSH."""
import json
import os
import subprocess
import unittest

import acls_cross_test as rig
import output_test as transfer
from xattrs_test import RSYNC

FIXTURE = '''import os,pathlib,sys
p=pathlib.Path(sys.argv[1]); p.mkdir(exist_ok=True); source=sys.argv[2]=='source'
for name,sm,dm in [('same',0o744,0o640),('changed',0o600,0o751),('already',0o744,0o601),('new',0o751,0)]:
 if name=='new' and not source: continue
 f=p/name; f.write_bytes(b'contents' if source or name!='changed' else b'old');f.chmod(sm if source else dm);os.utime(f,(1500000000,1500000000))
p.chmod(0o755); os.utime(p,(1500000000,1500000000))
'''
SNAPSHOT = '''import json,pathlib,sys
p=pathlib.Path(sys.argv[1]); print(json.dumps({f.name:[f.stat().st_mode & 4095,f.read_bytes().hex()] for f in p.iterdir()}))
'''


class CrossPlatformChmodTests(rig.CrossStyleAclTests):
    test_cross_style_refusal_and_rsync_fallback = None

    def test_permission_overrides_over_cross_platform_ssh(self):
        for direction in ('push', 'pull'):
            for flags in (['-rltp', '--chmod=D2775,F640'], ['-rlt', '--chmod=ugo=rwX'], ['-rltE', '--chmod=a-x,a+X'], ['-rltp', '--chmod=D2775,F640', '-n']):
                with self.subTest(direction=direction, flags=flags):
                    results = []
                    for native in (False, True):
                        name = direction + str(len(flags)) + flags[0] + str(native)
                        local, remote = self.root / name, '/rig/' + name
                        self.checked(['python3', '-c', FIXTURE, str(self.source), 'source'])
                        self.remote('python3', '-c', FIXTURE, '/rig/source', 'source')
                        if direction == 'push': self.remote('python3', '-c', FIXTURE, remote, 'destination')
                        else: self.checked(['python3', '-c', FIXTURE, str(local), 'destination'])
                        args = [str(transfer.BINARY) if native else RSYNC, *flags, '--out-format=%i|%n', '-e', self.rsh]
                        if native: args += ['--no-fallback', '--no-clone', '--rsync-path=/rig/helper']
                        if direction == 'push': args += [str(self.source) + '/', 'root@127.0.0.1:' + remote + '/']
                        else: args += ['root@127.0.0.1:/rig/source/', str(local) + '/']
                        result = subprocess.run(args, capture_output=True, timeout=30, env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
                        data = json.loads(self.remote('python3', '-c', SNAPSHOT, remote) if direction == 'push' else
                                          self.checked(['python3', '-c', SNAPSHOT, str(local)]))
                        results.append((data, sorted(row for row in result.stdout.splitlines() if b'|' in row)))
                    self.assertEqual(results[1], results[0])


if __name__ == '__main__': unittest.main()
