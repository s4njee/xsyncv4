#!/usr/bin/env python3
"""Build the pinned upstream flags reference in a new disposable directory.

This does not install rsync. Use the printed path as XSYNC_FILEFLAGS_RSYNC.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ARCHIVE = ('https://download.samba.org/pub/rsync/src/rsync-3.3.0.tar.gz',
           '7399e9a6708c32d678a72a63219e96f23be0be2336e50fd1348498d07041df90')
PATCH = ('https://raw.githubusercontent.com/RsyncProject/rsync-patches/10ab5e57446d10ef641ceb045ef3094e7d2bd439/fileflags.diff',
         '9ea66199451cd42589113fd19df9f105bbd9c9ef00af70a339b955f25c27da67')


def download(spec, target):
    url, digest = spec
    with urllib.request.urlopen(url, timeout=30) as response: data = response.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('reference download checksum mismatch: ' + url)
    target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='new directory to retain the build (default: a fresh /tmp directory)')
    args = parser.parse_args()
    if sys.platform != 'darwin': parser.error('the BSD flags reference requires Darwin')
    root = args.output
    if root: root.mkdir(parents=True, exist_ok=False)
    else: root = Path(tempfile.mkdtemp(prefix='xsync-fileflags-reference-'))
    root = root.resolve()
    archive, patch = root / 'rsync.tar.gz', root / 'fileflags.diff'
    download(ARCHIVE, archive); download(PATCH, patch)
    with tarfile.open(archive) as tar:
        for entry in tar:
            name = Path(entry.name)
            if name.is_absolute() or '..' in name.parts or name.parts[0] != 'rsync-3.3.0' or not (entry.isfile() or entry.isdir() or (entry.issym() and Path(entry.linkname).name == entry.linkname and entry.linkname not in ('.', '..'))):
                raise RuntimeError('invalid reference archive member: ' + entry.name)
            target = root / name
            if entry.isdir(): target.mkdir(parents=True, exist_ok=True)
            elif entry.issym():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(entry.linkname)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(entry).read()); target.chmod(entry.mode & 0o777)
    source = root / 'rsync-3.3.0'
    with patch.open('rb') as incoming, (root / 'patch.log').open('wb') as log:
        subprocess.run(['patch', '--batch', '--fuzz=0', '-p1'], cwd=source, stdin=incoming, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
    for command, name in ((['./configure', '--disable-openssl', '--disable-xxhash', '--disable-zstd', '--disable-lz4'], 'configure'),
                          (['make', '-j8', 'rsync'], 'build')):
        with (root / (name + '.log')).open('wb') as log:
            subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    result = subprocess.run([str(source / 'rsync'), '--version'], capture_output=True, check=True, timeout=10)
    if b'file-flags' not in result.stdout: raise RuntimeError('reference has no file-flags support')
    print(source / 'rsync')


if __name__ == '__main__': main()
