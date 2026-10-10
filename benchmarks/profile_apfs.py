#!/usr/bin/env python3
"""Sample a verified APFS no-op run, separately from timed benchmarks."""
import argparse
import fcntl
import pathlib
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=pathlib.Path, required=True)
    parser.add_argument('--work', type=pathlib.Path, required=True)
    parser.add_argument('--xsync', type=pathlib.Path, required=True)
    parser.add_argument('--rsync', default='/opt/homebrew/bin/rsync')
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('requires macOS /usr/bin/sample')
    source = args.corpus.resolve()
    work = args.work.resolve()
    if not source.is_dir() or work == source or work in source.parents or source in work.parents:
        parser.error('source and work must be existing, disjoint benchmark paths')
    if not (work / '.xs-benchmark-work').is_file():
        parser.error('work directory lacks benchmark ownership marker')
    lock = (work / '.xs-benchmark-lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error('another benchmark owns this work directory')
    destination = work / 'profile-apfs'
    if destination.exists():
        parser.error('profile destination already exists; do not overwrite it')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([args.rsync, '-a', str(source) + '/', str(destination) + '/'], check=True)
    command = [str(args.xsync.resolve()), '-a', '-j1', '--no-progress', '--no-fallback', '--stats',
               str(source) + '/', str(destination) + '/']
    with args.output.with_suffix('.stdout').open('w') as out, args.output.with_suffix('.stderr').open('w') as err:
        child = subprocess.Popen(command, stdout=out, stderr=err)
        try:
            sampled = subprocess.run(['/usr/bin/sample', str(child.pid), '3', '1', '-file', str(args.output)],
                                     capture_output=True, text=True, timeout=20)
        finally:
            status = child.wait(timeout=30)
    if status:
        raise RuntimeError(f'no-op xs failed with {status}; destination retained for diagnosis')
    if sampled.returncode:
        raise RuntimeError('sample failed: ' + sampled.stdout + sampled.stderr)
    verified = subprocess.run([args.rsync, '-anci', '--delete', str(source) + '/', str(destination) + '/'],
                              capture_output=True, text=True, check=True)
    if verified.stdout.strip():
        raise RuntimeError('profile verification failed: ' + verified.stdout)
    shutil.rmtree(destination)
    print(f'Verified APFS no-op profile: {args.output}')


if __name__ == '__main__':
    main()
