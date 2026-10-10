#!/usr/bin/env python3
"""macOS/Linux xattr namespace parity using an explicitly supplied QA container.

Set XSYNC_XATTR_LINUX_CONTAINER to an existing container with xsync, rsync and
Python. The test uses its /tmp directories, and removes only those directories.
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

import output_test as transfer
from filter_diff_test import RSYNC
from xattrs_test import DARWIN, get_attrs, set_attr

CONTAINER = os.environ.get('XSYNC_XATTR_LINUX_CONTAINER')


@unittest.skipUnless(DARWIN and CONTAINER, 'requires macOS and an explicit Linux QA container')
class CrossPlatformXattrTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync-cross-xattrs-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = '/tmp/' + self.root.name
        self.addCleanup(self.remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1],ignore_errors=True)', self.remote)

    def remote_code(self, code, *args):
        result = subprocess.run(['docker', 'exec', CONTAINER, 'python3', '-c', code, *map(str, args)],
                                check=True, capture_output=True, timeout=30)
        return result.stdout

    def fixture(self, direction, symlink_attrs):
        for path in self.root.iterdir():
            if path.is_dir(): shutil.rmtree(path)
            else: path.unlink()
        for top in ('src', 'dst'):
            p = self.root / top
            p.mkdir(); (p / 'sub').mkdir()
            (p / 'file').write_bytes(b'same data')
            (p / 'sub' / 'nested').write_bytes(b'nested data' if top == 'src' else b'old')
            (p / 'link').symlink_to('file')
            for name in ('', 'file', 'sub', 'sub/nested'):
                set_attr(p / name, 'foo', b'source\0\xff' if top == 'src' else b'old value')
                set_attr(p / name, 'keep', b'source keep' if top == 'src' else b'dest keep')
                if top == 'dst': set_attr(p / name, 'stale', b'delete me')
            set_attr(p / 'file', 'rsync.%test', top.encode())
            if symlink_attrs: set_attr(p / 'link', 'linkattr', top.encode())
        code = '''import os,pathlib,shutil,sys
r=pathlib.Path(sys.argv[1]); shutil.rmtree(r,ignore_errors=True); r.mkdir()
for top in ('src','dst'):
 p=r/top; p.mkdir(); (p/'sub').mkdir(); (p/'file').write_bytes(b'same data')
 (p/'sub/nested').write_bytes(b'nested data' if top=='src' else b'old'); (p/'link').symlink_to('file')
 for name in ('','file','sub','sub/nested'):
  os.setxattr(p/name,'user.foo',b'source\\0\\xff' if top=='src' else b'old value')
  os.setxattr(p/name,'user.keep',b'source keep' if top=='src' else b'dest keep')
  if top=='dst': os.setxattr(p/name,'user.stale',b'delete me')
 os.setxattr(p/'file','user.rsync.%test',top.encode())
'''
        self.remote_code(code, self.remote)

    def snapshot(self, direction):
        if direction == 'push':
            code = '''import base64,json,os,pathlib,sys,hashlib
p=pathlib.Path(sys.argv[1]); d={}
for f in [p,*p.rglob('*')]:
 n=str(f.relative_to(p)); d[n]={'attrs':{a:base64.b64encode(os.getxattr(f,a,follow_symlinks=False)).decode() for a in os.listxattr(f,follow_symlinks=False)}}
 if f.is_symlink():d[n]['link']=str(f.readlink())
 elif f.is_file():d[n]['data']=hashlib.sha256(f.read_bytes()).hexdigest()
print(json.dumps(d))
'''
            return json.loads(self.remote_code(code, self.remote + '/dst'))
        import hashlib
        p = self.root / 'dst'; result = {}
        for f in (p, *p.rglob('*')):
            result[str(f.relative_to(p))] = {'attrs': get_attrs(f)}
            if f.is_symlink(): result[str(f.relative_to(p))]['link'] = str(f.readlink())
            elif f.is_file(): result[str(f.relative_to(p))]['data'] = hashlib.sha256(f.read_bytes()).hexdigest()
        return result

    def test_namespaces_filters_and_internal_attributes(self):
        for direction in ('push', 'pull'):
            for flags, rules in ((['-rX'], []), (['-rlX'], []), (['-rXX'], []),
                                  (['-rX'], ['-x keep']), (['-rX','--delete'], ['-xr keep']),
                                  (['-rX'], ['+x *'])):
                for symlink_attrs in (False, True):
                    with self.subTest(direction=direction, flags=flags, rules=rules, symlink_attrs=symlink_attrs):
                        results = []
                        for native in (False, True):
                            self.fixture(direction, symlink_attrs)
                            command = [str(transfer.BINARY) if native else RSYNC, *flags]
                            if native: command += ['--no-fallback','--no-clone','-j8']
                            server = '/usr/local/bin/xs' if native else 'rsync'
                            command += ['-e',transfer.RSH,'--rsync-path=' + shlex.join(['docker','exec','-i',CONTAINER,server])]
                            command += ['--filter=' + rule for rule in rules]
                            src, dst = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
                            if direction == 'push': dst = 'fake:' + self.remote + '/dst/'
                            else: src = 'fake:' + self.remote + '/src/'
                            result = subprocess.run(command + [src,dst],capture_output=True,timeout=30)
                            results.append((result.returncode,self.snapshot(direction),result.stderr))
                        self.assertEqual(results[1][0],results[0][0],results)
                        self.assertEqual(results[1][1],results[0][1],results)


if __name__ == '__main__': unittest.main()
