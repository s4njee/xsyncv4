#!/usr/bin/env python3
"""Copy a tree as plain tar streams: the lab's yardstick for what a bare pipe can do.

    xspipe.py push --src DIR --dest DIR [--streams N] [--codec none|zstd1]
                   [--rsh 'ssh ...' --target USER@HOST --measure 'python3 .../measure.py'
                    --metrics-base PATH]

The tree's files are taken in sorted order and cut into N contiguous shares. Each share
goes out as its own tar stream, through `zstd -1` if asked, to its own extracting tar
on the receiver, all at once: extraction overlaps the transfer and nothing waits for a
whole archive. The directories follow alone, after every file, so their modes and times
are set last and nothing written afterwards changes them.

With --target, each receiving tar runs over its own SSH connection, under measure.py
(metrics in METRICS_BASE.<share>.json and METRICS_BASE.dirs.json). Without it, both
ends run on this host: the receiver's own ceiling, with no network at all.
Exit status 0 only if every stream on both ends succeeded.
"""
import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

# On macOS, GNU tar (Homebrew's gtar) when there is one: it reads small files about a quarter
# faster than the system bsdtar (25 s against 32 s for 100,000 files), and stores no extended
# attributes or resource forks. bsdtar has to be told not to, or GNU tar at the far end warns.
GTAR = next((path for path in ('/opt/homebrew/bin/gtar', '/usr/local/bin/gtar') if os.access(path, os.X_OK)), None)
if sys.platform == 'darwin' and not GTAR:
    CREATE_OPTIONS = ['--no-mac-metadata', '--no-xattrs', '--no-acls', '--no-fflags']
else:
    CREATE_OPTIONS = []


def program(name):
    """A tool's path: a non-login shell on macOS may not have Homebrew on its PATH."""
    found = shutil.which(name) or next((path for path in (f'/opt/homebrew/bin/{name}', f'/usr/local/bin/{name}')
                                        if os.access(path, os.X_OK)), None)
    if not found:
        sys.exit(f'xspipe: {name} is not installed')
    return found


def walk(source):
    """(files, directories) under source, relative to it, in sorted order; symlinks count as files."""
    files, directories = [], []
    for root, names, leaves in os.walk(source):
        names.sort()
        relative = os.path.relpath(root, source)
        prefix = '' if relative == '.' else relative + '/'
        if prefix:
            directories.append(relative)
        for name in list(names):
            if os.path.islink(os.path.join(root, name)):
                names.remove(name)
                leaves.append(name)
        files.extend(prefix + name for name in sorted(leaves))
    return files, directories


def name_list(names, scratch, label):
    path = os.path.join(scratch, label)
    with open(path, 'wb') as stream:
        stream.write(b''.join(os.fsencode(name) + b'\0' for name in names))
    return path


def start_stream(args, names_path, label, recursion=True):
    """Start one sender -> receiver pipeline; returns its processes, last one the receiver."""
    create = [GTAR if sys.platform == 'darwin' and GTAR else program('tar'), '-cf', '-', *CREATE_OPTIONS, *([] if recursion else ['--no-recursion']),
              '-C', args.src, '--null', '-T', names_path]
    stages = [subprocess.Popen(create, stdout=subprocess.PIPE)]
    compressed = args.codec == 'zstd1' and recursion
    if compressed:
        stages.append(subprocess.Popen([program('zstd'), '-1', '-T0', '-q', '-c'], stdin=stages[-1].stdout,
                                       stdout=subprocess.PIPE))
    extract = ('zstd -d -q -c | ' if compressed else '') + 'tar -xpf - -C ' + shlex.quote(args.dest)
    receive = f'mkdir -p {shlex.quote(args.dest)} && {extract}'
    if args.target:
        measured = [*shlex.split(args.measure), '--metrics', f'{args.metrics_base}.{label}.json', '--', 'sh', '-c', receive]
        receiver = [*shlex.split(args.rsh), args.target, shlex.join(measured)]
    else:
        receiver = ['sh', '-c', receive]
    stages.append(subprocess.Popen(receiver, stdin=stages[-1].stdout))
    for stage in stages[:-1]:
        stage.stdout.close()  # only the next stage holds each pipe, so a failure downstream is seen upstream
    return stages


def finish(streams):
    failed = []
    for label, stages in streams:
        codes = [stage.wait() for stage in stages]
        if any(codes):
            failed.append(f'{label}: exit statuses {codes}')
    return failed


def push(args):
    files, directories = walk(args.src)
    with tempfile.TemporaryDirectory(prefix='xspipe-') as scratch:
        count = max(1, min(args.streams, len(files)))
        shares = [files[i * len(files) // count:(i + 1) * len(files) // count] for i in range(count)]
        streams = [(str(i), start_stream(args, name_list(share, scratch, f'share{i}'), str(i)))
                   for i, share in enumerate(shares) if share]
        failed = finish(streams)
        if not failed and directories:
            failed = finish([('dirs', start_stream(args, name_list(directories, scratch, 'dirs'), 'dirs', recursion=False))])
    for problem in failed:
        print(f'xspipe: {problem}', file=sys.stderr)
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('push')
    p.add_argument('--src', required=True)
    p.add_argument('--dest', required=True)
    p.add_argument('--streams', type=int, default=1)
    p.add_argument('--codec', choices=('none', 'zstd1'), default='none')
    p.add_argument('--rsh')
    p.add_argument('--target')
    p.add_argument('--measure')
    p.add_argument('--metrics-base')
    args = parser.parse_args()
    if args.target and not (args.rsh and args.measure and args.metrics_base):
        parser.error('--target needs --rsh, --measure and --metrics-base')
    if args.streams < 1:
        parser.error('--streams must be at least 1')
    return push(args)


if __name__ == '__main__':
    sys.exit(main())
