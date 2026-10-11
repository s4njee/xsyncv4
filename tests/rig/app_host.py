#!/usr/bin/env python3
"""Exercise the native host app engine against an isolated Linux SSH helper."""
import os
import pathlib
import subprocess
import sys
import tempfile
import uuid

REPO = pathlib.Path(__file__).resolve().parents[2]
IMAGE = 'xsync-p0-rig'


def docker(*args, capture=False):
    return subprocess.run(['docker', *map(str, args)], check=True,
                          capture_output=capture, text=capture)


def main():
    docker('build', '-t', IMAGE, '-f', REPO / 'tests/rig/Dockerfile', REPO)
    server = 'xsync-app-host-' + uuid.uuid4().hex[:10]
    with tempfile.TemporaryDirectory(prefix='xsync-host-keys-') as temp:
        keys = pathlib.Path(temp)
        key = keys / 'id test'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
        created = False
        try:
            docker('run', '-d', '--name', server, '--rm', '-p', '127.0.0.1::22',
                   '-p', '127.0.0.1::2223', '-v', str(keys)+':/keys:ro', IMAGE, capture=True)
            created = True
            docker('cp', str(key)+'.pub', server+':/root/.ssh/authorized_keys')
            docker('exec', server, 'chown', 'root:root', '/root/.ssh/authorized_keys')
            docker('exec', server, 'chmod', '600', '/root/.ssh/authorized_keys')
            docker('exec', server, 'mkdir', '-p', '/rig')
            docker('exec', '-d', server, '/usr/sbin/sshd', '-D', '-E', '/rig/sshd.log')
            port = docker('port', server, '22/tcp', capture=True).stdout.strip().rsplit(':', 1)[1]
            auth_port = docker('port', server, '2223/tcp', capture=True).stdout.strip().rsplit(':', 1)[1]
            env = dict(os.environ, PYTHONPATH=str(REPO/'tests'), XSYNC_RIG_HOST='127.0.0.1',
                       XSYNC_TEST_BINARY=str(REPO/'build/xs'), XSYNC_APP_SSH_TEST_TMP='/tmp',
                       XSYNC_APP_SSH_TEST_IDENTITY=str(key), XSYNC_APP_SSH_TEST_PORT=port,
                       XSYNC_APP_SSH_TEST_AUTH_PORT=auth_port)
            # These bootstrap options apply only to the isolated test fixture.
            # The app transport itself always enforces known-host verification.
            code = '''import os,unittest,ssh_test
ssh_test.SSH[:]=['ssh','-l','root','-p',os.environ['XSYNC_APP_SSH_TEST_PORT'],'-i',os.environ['XSYNC_APP_SSH_TEST_IDENTITY'],'-oBatchMode=yes','-oStrictHostKeyChecking=no','-oUserKnownHostsFile=/dev/null','-oLogLevel=ERROR']
import app_ssh_test
unittest.main(module=app_ssh_test,argv=['app_ssh_test','-v',*__import__('sys').argv[1:]])
'''
            result = subprocess.run([sys.executable, '-c', code, *sys.argv[1:]], env=env)
            return result.returncode
        finally:
            if created:
                subprocess.run(['docker', 'rm', '-f', server], capture_output=True)


if __name__ == '__main__':
    raise SystemExit(main())
