#!/usr/bin/env python3
"""Build and verify musl releases; copy the already-built native artifact."""
import argparse
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import uuid

REPO = pathlib.Path(__file__).resolve().parent.parent


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', required=True, type=pathlib.Path)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    out = REPO / 'dist'
    out.mkdir(exist_ok=True)
    artifacts = []
    if platform.system() == 'Darwin':
        arches = run('lipo', '-archs', args.native, capture_output=True, text=True).stdout.split()
        if set(arches) != {'arm64', 'x86_64'}:
            raise RuntimeError('native macOS release must contain arm64 and x86_64')
        dependencies = run('otool', '-L', args.native, capture_output=True, text=True).stdout
        if any('/opt/' in line or '/usr/local/' in line for line in dependencies.splitlines()[1:]):
            raise RuntimeError('macOS release still depends on third-party dynamic libraries')
        binary = out / 'xsync-darwin-universal'
        shutil.copy2(args.native, binary)
        artifacts.append(binary)
    for arch in ('amd64', 'arm64'):
        image = 'xsync-release-' + arch
        run('docker', 'build', '--platform', 'linux/' + arch, '--build-arg', 'XSYNC_GIT_HASH=' + args.revision,
            '-t', image, '-f', REPO / 'tools/release.Dockerfile', REPO)
        container = 'xsync-release-' + uuid.uuid4().hex[:10]
        try:
            run('docker', 'create', '--platform', 'linux/' + arch, '--name', container, image, '/xsync', '--version',
                stdout=subprocess.DEVNULL)
            binary = out / ('xsync-linux-' + arch)
            run('docker', 'cp', container + ':/xsync', binary)
            binary.chmod(0o755)
            # A scratch image has no loader, libc, ICU data, or compression libraries.
            run('docker', 'start', '-a', container)
            status = run('docker', 'inspect', '-f', '{{.State.ExitCode}}', container,
                         capture_output=True, text=True).stdout.strip()
            if status != '0':
                raise RuntimeError('standalone Linux executable failed: ' + status)
            smoke = r'''set -eu
bin=/releases/xsync-linux-ARCH
mkdir /tmp/source
head -c 2097152 /dev/zero >/tmp/source/file
printf 'unicode contents\n' >'/tmp/source/straße with spaces'
ln -s file '/tmp/source/space link'
"$bin" --no-fallback -a /tmp/source/ /tmp/local/
cmp /tmp/source/file /tmp/local/file
cmp '/tmp/source/straße with spaces' '/tmp/local/straße with spaces'
printf '#!/bin/sh\nshift\nexec /bin/sh -c "$*"\n' >/tmp/fakessh
chmod 755 /tmp/fakessh
"$bin" --no-fallback -az -e /tmp/fakessh --rsync-path="$bin" /tmp/source/ fake:/tmp/pushed/
"$bin" --no-fallback -az -e /tmp/fakessh --rsync-path="$bin" fake:/tmp/pushed/ /tmp/pulled/
cmp /tmp/source/file /tmp/pulled/file
cmp '/tmp/source/straße with spaces' '/tmp/pulled/straße with spaces'
test "$(readlink '/tmp/pulled/space link')" = file
"$bin" --version
'''.replace('ARCH', arch)
            run('docker', 'run', '--rm', '--platform', 'linux/' + arch,
                '-v', str(out) + ':/releases:ro', 'debian:bookworm-slim', 'sh', '-ec', smoke)
            artifacts.append(binary)
        finally:
            subprocess.run(['docker', 'rm', '-f', container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    manifest = {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                         'bytes': p.stat().st_size, 'git': args.revision} for p in artifacts}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Verified releases: ' + ', '.join(manifest), flush=True)


if __name__ == '__main__':
    main()
