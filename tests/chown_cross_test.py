#!/usr/bin/env python3
"""Ownership names resolve on the receiving host across real SSH."""
import grp
import json
import os
import pwd
import subprocess
import time
import unittest

import acls_cross_test as rig
import output_test as transfer
from chmod_cross_test import FIXTURE
from xattrs_test import RSYNC

SNAPSHOT = '''import json,pathlib,sys
p=pathlib.Path(sys.argv[1]); print(json.dumps({f.name:[f.stat().st_mode & 4095,f.stat().st_uid,f.stat().st_gid,f.read_bytes().hex()] for f in p.iterdir()}))
'''


class CrossPlatformOwnershipTests(rig.CrossStyleAclTests):
    test_cross_style_refusal_and_rsync_fallback = None

    def test_fresh_named_group_is_described_after_source_retry(self):
        user = pwd.getpwuid(os.getuid()).pw_name
        choices = [gid for gid in os.getgroups() if gid not in (0, os.getgid())]
        if not choices: self.skipTest('requires another local group membership')
        fresh_gid = choices[0]
        fresh_group = grp.getgrgid(fresh_gid).gr_name
        self.remote('python3', '-c', '''import grp,pwd,subprocess,sys
user,group=sys.argv[1:]
try: grp.getgrnam(group)
except KeyError: subprocess.run(['groupadd','-g','62002',group],check=True)
try: pwd.getpwnam(user)
except KeyError: subprocess.run(['useradd','-u','62000','-g',group,'-M',user],check=True)
''', user, fresh_group)
        fault = self.root / 'fault.dylib'
        self.checked(['clang++', '-std=c++20', '-dynamiclib', '-fPIC', str(transfer.REPO / 'tests/fault_io.cpp'), '-o', str(fault)])
        source = self.root / 'fresh-source'
        data = b'x' * (4 * 1024 * 1024)
        for whole in (False, True):
            for inplace in (False, True):
                with self.subTest(whole=whole, inplace=inplace):
                    source.write_bytes(data + b'end'); os.chown(source, -1, os.getgid()); source.chmod(0o755)
                    os.utime(source, (1500000000, 1500000000))
                    remote = '/rig/fresh-destination' + str(whole) + str(inplace)
                    self.remote('python3', '-c', '''import pathlib,sys,os
p=pathlib.Path(sys.argv[1]);p.write_bytes(b'x'*(4*1024*1024));p.chmod(0o640);os.utime(p,(1500000000,1500000000))
''', remote)
                    marker = self.root / 'source-read'
                    env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', DYLD_INSERT_LIBRARIES=str(fault),
                               XSYNC_FAULT_PATH=str(source.resolve()))
                    if whole: env.update(XSYNC_FAULT_READ_NOTIFY=str(marker), XSYNC_FAULT_READ_DELAY_US='300000')
                    else: env.update(XSYNC_FAULT_PREAD_NOTIFY=str(marker), XSYNC_FAULT_PREAD_MIN_SIZE=str(512 * 1024),
                                     XSYNC_FAULT_PREAD_DELAY_US='300000')
                    args = [str(transfer.BINARY), '--no-fallback', '--no-clone', '-a', '--chown=' + user,
                            '-e', self.rsh, '--rsync-path=/rig/helper']
                    if whole: args.append('--whole-file')
                    if inplace: args.append('--inplace')
                    proc = subprocess.Popen(args + [str(source), 'root@127.0.0.1:' + remote],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                    try:
                        observed = marker.with_name(marker.name + '.1') if whole else marker
                        deadline = time.monotonic() + 10
                        while not observed.exists() and proc.poll() is None and time.monotonic() < deadline: time.sleep(.002)
                        if not observed.exists():
                            out, err = proc.communicate(timeout=10)
                            self.fail(('source read never reached delay', proc.returncode, out, err))
                        os.chown(source, -1, fresh_gid)
                        out, err = proc.communicate(timeout=30)
                        self.assertEqual(proc.returncode, 0, (out, err))
                        result = json.loads(self.remote('python3', '-c', '''import pathlib,sys,json,hashlib,pwd,grp
p=pathlib.Path(sys.argv[1]);s=p.stat();print(json.dumps([s.st_uid,s.st_gid,hashlib.sha256(p.read_bytes()).hexdigest(),pwd.getpwnam(sys.argv[2]).pw_uid,grp.getgrnam(sys.argv[3]).gr_gid]))
''', remote, user, fresh_group))
                        import hashlib
                        self.assertEqual(result[:2], result[3:])
                        self.assertNotEqual(result[1], fresh_gid)
                        self.assertEqual(result[2], hashlib.sha256(data + b'end').hexdigest())
                    finally:
                        if proc.poll() is None: proc.kill()
                        proc.communicate()
                        for p in self.root.glob(marker.name + '*'): p.unlink()

    def test_receiver_names_and_numeric_ids_over_ssh(self):
        user = pwd.getpwuid(os.getuid()).pw_name
        group = grp.getgrgid(os.getgid()).gr_name
        # The Linux fixture deliberately assigns our account name a different
        # numeric ID. Its built-in staff group also differs from macOS's.
        self.remote('python3', '-c', '''import grp,pwd,subprocess,sys
user,group=sys.argv[1:]
try: grp.getgrnam(group)
except KeyError: subprocess.run(['groupadd','-g','62001',group],check=True)
try: pwd.getpwnam(user)
except KeyError: subprocess.run(['useradd','-u','62000','-g',group,'-M',user],check=True)
''', user, group)
        target = '--chown=' + user + ':' + group
        cases = (['-a', target], ['-a', f'--chown={os.getuid()}:{os.getgid()}'],
                 ['-a', '--chown=:' + group], ['-a', '--chown=' + user],
                 ['-a', target, '-n'])
        for direction in ('push', 'pull'):
            for index, flags in enumerate(cases):
                with self.subTest(direction=direction, flags=flags):
                    results = []
                    for native in (False, True):
                        name = direction + str(index) + str(native)
                        local, remote = self.root / name, '/rig/' + name
                        self.checked(['python3', '-c', FIXTURE, str(self.source), 'source'])
                        self.remote('python3', '-c', FIXTURE, '/rig/source', 'source')
                        if direction == 'push': self.remote('python3', '-c', FIXTURE, remote, 'destination')
                        else: self.checked(['python3', '-c', FIXTURE, str(local), 'destination'])
                        args = [str(transfer.BINARY) if native else RSYNC, *flags, '--out-format=%i|%n', '-e', self.rsh]
                        if native: args += ['--no-fallback', '--no-clone', '--rsync-path=/rig/helper']
                        if direction == 'push': args += [str(self.source) + '/', 'root@127.0.0.1:' + remote + '/']
                        else: args += ['root@127.0.0.1:/rig/source/', str(local) + '/']
                        result = subprocess.run(args, capture_output=True, timeout=30,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
                        state = json.loads(self.remote('python3', '-c', SNAPSHOT, remote) if direction == 'push' else
                                           self.checked(['python3', '-c', SNAPSHOT, str(local)]))
                        results.append((state, sorted(row for row in result.stdout.splitlines() if b'|' in row)))
                    self.assertEqual(results[1], results[0])

        # With --no-owner after --chown, rsync's sender omits owner IDs and
        # the remote receiver uses owner 0. Native negotiation retains IDs and
        # applies the receiver's requested override. Exercise the distinction
        # with a named account whose remote ID differs from our local ID.
        results = []
        for native in (False, True):
            remote = '/rig/owner-option-boundary' + str(native)
            self.remote('python3', '-c', FIXTURE, remote, 'destination')
            args = [str(transfer.BINARY) if native else RSYNC, '-a', target, '--no-owner', '-e', self.rsh]
            if native: args += ['--no-fallback', '--no-clone', '--rsync-path=/rig/helper']
            result = subprocess.run(args + [str(self.source) + '/', 'root@127.0.0.1:' + remote + '/'],
                                    capture_output=True, timeout=30,
                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads(self.remote('python3', '-c', SNAPSHOT, remote))
            self.assertTrue(all(row[1] == (62000 if native else 0) for row in state.values()))
            results.append({name: [row[0], *row[2:]] for name, row in state.items()})
        self.assertEqual(results[1], results[0])


if __name__ == '__main__': unittest.main()
