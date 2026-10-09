#!/usr/bin/env python3
"""Opt-in Darwin/Linux ACL compatibility rig; owns only its disposable container.

Build tests/rig/Dockerfile as xsync-p0-rig, then run with XSYNC_ACL_CROSS_RIG=1.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
import uuid

import acls_test as acl
import output_test as transfer
from xattrs_test import DARWIN, RSYNC

LINUX_FIXTURE = '''import os,pathlib,struct
p=pathlib.Path('/rig/source');p.mkdir();(p/'file').write_bytes(b'contents')
for f in (p,p/'file'):
 entries=[(1,7,0xffffffff),(2,7,0),(2,4,60000),(4,5,0xffffffff),(8,5,0),(16,5,0xffffffff),(32,4,0xffffffff)]
 data=struct.pack('<I',2)+b''.join(struct.pack('<HHI',*e) for e in entries)
 os.setxattr(f,'system.posix_acl_access',data)
 if f.is_dir(): os.setxattr(f,'system.posix_acl_default',data)
'''
LINUX_SNAPSHOT = '''import base64,hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); result={}
if p.exists():
 import os
 for f in [p]+sorted(p.rglob('*')):
  s=f.stat(); result[str(f.relative_to(p))]=[s.st_mode,s.st_uid,s.st_gid,s.st_mtime_ns,
   hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None,
   {n:base64.b64encode(os.getxattr(f,n)).decode() for n in os.listxattr(f)}]
print(json.dumps(result,sort_keys=True))
'''


@unittest.skipUnless(DARWIN and os.environ.get('XSYNC_ACL_CROSS_RIG') == '1',
                     'opt-in Darwin/Linux Docker SSH rig')
class CrossStyleAclTests(unittest.TestCase):
    def checked(self, args, **kwargs):
        result = subprocess.run(args, capture_output=True, timeout=30, **kwargs)
        self.assertEqual(result.returncode, 0, (args, result.stdout, result.stderr))
        return result.stdout.decode().strip()

    def remote(self, *args):
        return self.checked(['docker', 'exec', self.container, *args])

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='xsync ACL cross ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        key = self.root / 'key'
        self.checked(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)])
        self.container = 'xsync-acl-cross-' + uuid.uuid4().hex[:12]
        self.checked(['docker', 'run', '-d', '--name', self.container, '-p',
                      '127.0.0.1::22', os.environ.get('XSYNC_ACL_RIG_IMAGE', 'xsync-p0-rig')])
        self.addCleanup(subprocess.run, ['docker', 'rm', '-f', self.container], capture_output=True, timeout=30)
        self.checked(['docker', 'cp', str(key) + '.pub', self.container + ':/root/.ssh/authorized_keys'])
        self.remote('chown', 'root:root', '/root/.ssh/authorized_keys')
        self.remote('chmod', '700', '/root/.ssh')
        self.remote('chmod', '600', '/root/.ssh/authorized_keys')
        self.checked(['docker', 'exec', '-d', self.container, '/usr/sbin/sshd', '-D'])
        port = self.checked(['docker', 'port', self.container, '22/tcp']).split(':')[-1]
        self.rsh = shlex.join(['ssh', '-i', str(key), '-p', port, '-oBatchMode=yes',
                              '-oStrictHostKeyChecking=no', '-oUserKnownHostsFile=/dev/null', '-oLogLevel=ERROR'])
        self.source = self.root / 'source'; self.source.mkdir()
        (self.source / 'file').write_bytes(b'contents')
        acl.set_acl(self.source, inherit=True); acl.set_acl(self.source / 'file')
        self.remote('mkdir', '-p', '/rig')
        self.remote('python3', '-c', LINUX_FIXTURE)
        # Explicit --rsync-path is kept by fallback, so this fixture dispatches
        # native and rsync server invocations to their respective binaries.
        wrapper = '#!/bin/sh\nif [ "$#" = 1 ] && [ "$1" = --server ]; then exec /usr/local/bin/xsync "$@"; fi\nexec /usr/bin/rsync "$@"\n'
        self.remote('python3', '-c', "import pathlib,sys; p=pathlib.Path('/rig/helper'); p.write_text(sys.argv[1]); p.chmod(0o755)", wrapper)

    def remote_snapshot(self, path):
        return json.loads(self.remote('python3', '-c', LINUX_SNAPSHOT, path))

    def local_snapshot(self, path):
        return (acl.get_acl(path), acl.snapshot(path)) if path.exists() else None

    def test_cross_style_refusal_and_rsync_fallback(self):
        source_before = self.local_snapshot(self.source)
        remote_before = self.remote_snapshot('/rig/source')
        for direction in ('push', 'pull'):
            for existing in (False, True):
                for mode in ('rsync', 'strict', 'fallback'):
                    with self.subTest(direction=direction, existing=existing, mode=mode):
                        name = direction + '-' + mode + '-' + str(existing)
                        local = self.root / name
                        remote = '/rig/' + name
                        if existing:
                            if direction == 'pull':
                                local.mkdir(); (local / 'keep').write_bytes(b'keep'); acl.set_acl(local, 1)
                            else:
                                self.remote('python3', '-c', "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/'keep').write_bytes(b'keep')", remote)
                        before = self.remote_snapshot(remote) if direction == 'push' else self.local_snapshot(local)
                        args = [RSYNC if mode == 'rsync' else str(transfer.BINARY), '-rtAi', '-e', self.rsh]
                        if mode != 'rsync':
                            args += ['--rsync-path=/rig/helper']
                            if mode == 'strict': args += ['--no-fallback']
                        if direction == 'push': args += [str(self.source) + '/', 'root@127.0.0.1:' + remote + '/']
                        else: args += ['root@127.0.0.1:/rig/source/', str(local) + '/']
                        result = subprocess.run(args, capture_output=True, timeout=30,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 4 if mode == 'strict' else 12, (result.stdout, result.stderr))
                        if mode == 'fallback': self.assertIn(b'falling back to rsync:', result.stderr)
                        elif mode == 'strict': self.assertNotIn(b'falling back', result.stderr)
                        after = self.remote_snapshot(remote) if direction == 'push' else self.local_snapshot(local)
                        self.assertEqual(after, before)
                        self.assertEqual(self.local_snapshot(self.source), source_before)
                        self.assertEqual(self.remote_snapshot('/rig/source'), remote_before)


if __name__ == '__main__': unittest.main()
