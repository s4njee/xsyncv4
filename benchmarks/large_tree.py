#!/usr/bin/env python3
"""Prepare an owned, reproducible five-million-file memory benchmark fixture."""
import argparse
import datetime
import fcntl
import json
import os
import pathlib
import struct
import time

from prepare import inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--files', type=int, default=5_000_000)
    parser.add_argument('--files-per-directory', type=int, default=1000)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.files < 1 or args.files_per_directory < 1:
        parser.error('file counts must be positive')
    root = args.root.resolve()
    if not (root / '.xsync-benchmark-owner.json').is_file():
        parser.error('missing benchmark ownership marker')
    source = root / 'data/large-tree'
    manifest = root / 'logs/dataset-large-tree.json'
    manifest.parent.mkdir(parents=True, exist_ok=True)
    lock = (manifest.parent / '.large-tree-prepare.lock').open('a+')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: parser.error('another process is preparing this fixture')
    if source.is_symlink() or (source.exists() and not source.is_dir()):
        parser.error('source must be an ordinary owned directory')
    if source.exists() and not args.resume and (manifest.exists() or any(source.iterdir())):
        parser.error('fixture exists; use --resume to validate and continue it')
    if args.resume:
        if not manifest.is_file(): parser.error('resume requires the fixture manifest')
        previous = json.loads(manifest.read_text())
        if previous.get('requested_files') != args.files or previous.get('files_per_directory') != args.files_per_directory:
            parser.error('resume parameters differ from the existing manifest')
    before = os.statvfs(source if source.exists() else source.parent if source.parent.exists() else root)
    missing = args.files - (previous.get('prepared_files', 0) if args.resume else 0)
    # Reserve 4 KiB data plus 4 KiB metadata per tiny file on each side. ZFS's
    # statvfs accounting unit can be 128 KiB even when a tiny file uses 512 B;
    # it is not a minimum per-file allocation size.
    reserved_bytes = (missing + args.files) * 8192
    if before.f_bavail * before.f_frsize < reserved_bytes:
        parser.error('insufficient free space for source and a verified destination')
    if before.f_favail and before.f_favail < missing + args.files + 10_000:
        parser.error('insufficient free inodes for source and destination')
    source.mkdir(parents=True, exist_ok=True)
    info = {'schema': 1, 'dataset': 'large-tree', 'path': str(source),
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'requested_files': args.files, 'files_per_directory': args.files_per_directory,
            'record_bytes': 16, 'payload': 'little-endian uint64 index, index XOR 0x58534d454d4f5259',
            'mtime_ns': 1_500_000_000_000_000_000, 'prepared_files': 0,
            'space_before': {'available_bytes': before.f_bavail * before.f_frsize, 'available_inodes': before.f_favail},
            'reserved_bytes': reserved_bytes,
            'complete': False}

    def save():
        temporary = manifest.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(info, indent=2) + '\n')
        temporary.replace(manifest)

    save()
    started = time.monotonic()
    total_directories = (args.files + args.files_per_directory - 1) // args.files_per_directory
    expected_dirs = {f'leaf-{number:07d}' for number in range(total_directories)}
    if any(p.name not in expected_dirs or p.is_symlink() or not p.is_dir() for p in source.iterdir()):
        raise RuntimeError('unexpected entry in owned source fixture')
    for number in range(total_directories):
        directory = source / f'leaf-{number:07d}'
        directory.mkdir(exist_ok=True)
        end = min(args.files, (number + 1) * args.files_per_directory)
        expected_files = {f'file-{index:010d}.bin' for index in range(number * args.files_per_directory, end)}
        if any(p.name not in expected_files or p.is_symlink() or not p.is_file() for p in directory.iterdir()):
            raise RuntimeError('unexpected entry in owned source directory')
        for index in range(number * args.files_per_directory, end):
            path = directory / f'file-{index:010d}.bin'
            payload = struct.pack('<QQ', index, index ^ 0x58534d454d4f5259)
            if path.exists():
                if path.read_bytes() != payload:
                    raise RuntimeError('existing fixture payload differs: ' + str(path))
            else:
                with path.open('xb') as out: out.write(payload)
            path.chmod(0o644)
            os.utime(path, ns=(info['mtime_ns'], info['mtime_ns']))
        directory.chmod(0o755)
        os.utime(directory, ns=(info['mtime_ns'], info['mtime_ns']))
        info['prepared_files'] = end
        save()
        if (number + 1) % 100 == 0 or number + 1 == total_directories:
            print(f'Prepared {end:,}/{args.files:,} files in {time.monotonic()-started:.1f}s', flush=True)
    source.chmod(0o755)
    os.utime(source, ns=(info['mtime_ns'], info['mtime_ns']))
    actual = inventory(source)
    if actual != {'files': args.files, 'directories': total_directories, 'bytes': args.files * 16}:
        raise RuntimeError('fixture inventory differs from requested shape')
    info.update(actual)
    info['complete'] = True
    info['prepared_seconds'] = time.monotonic() - started
    save()
    print(json.dumps(info, indent=2), flush=True)


if __name__ == '__main__': main()
