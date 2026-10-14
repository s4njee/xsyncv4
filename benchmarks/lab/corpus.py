#!/usr/bin/env python3
"""Generate seeded benchmark corpora, and pin any tree by a manifest digest.

A generated corpus is a pure function of its name and tier: the same bytes,
names, modes and times on every host, so one digest identifies it everywhere.
Nothing here uses floating point or Python's random module; every draw comes
from SHAKE-256 and integer arithmetic. A real tree is pinned the same way
with `manifest`, and either kind is checked with `verify`.
"""
import argparse
import datetime
import functools
import hashlib
import json
import multiprocessing
import os
import pathlib
import platform
import shutil
import socket
import stat
import subprocess
import sys
import threading

GENERATOR = 1          # bump whenever generated output would change
SEED = 20261011
MTIME = 1_700_000_000  # generated files carry MTIME + index, directories MTIME
MARKER = '.xsbench-corpora'
HERE = pathlib.Path(__file__).resolve().parent
KIB, MIB = 1 << 10, 1 << 20
TIERS = {'full': 1, 'smoke': 10, 'test': 500}
TEXT_SUFFIXES = ('.txt', '.json', '.xml', '.md')
# All of these are in xs's default --skip-compress list (src/compression.h).
SKIP_SUFFIXES = ('.jpg', '.png', '.gz', '.zip', '.mp4', '.zst')
CONSONANTS, VOWELS = 'bdfgklmnprstvz', 'aeiou'
BATCH = 256
RATIO_SAMPLE = 64 * MIB

# Sizes are ('fixed', bytes), ('lognormal', log2 of the median, sigma in
# 1/65536 octaves, minimum, maximum) or ('loguniform', log2 low, log2 high).
# `text` is the share of files, per thousand, with compressible content.
SMALL = {'weight': 1000, 'size': ('lognormal', 10, 141820, 16, MIB), 'text': 1000}
SPECS = {
    'tiny-one': {'files': 1, 'family': 'tiny', 'layout': ('flat', 0),
                 'parts': [{'weight': 1000, 'size': ('fixed', 19), 'text': 1000}]},
    'small-flat': {'files': 100_000, 'family': 'small', 'layout': ('flat', 100), 'parts': [SMALL]},
    'small-deep': {'files': 100_000, 'family': 'small', 'layout': ('deep', 6), 'parts': [SMALL]},
    'small-opaque': {'files': 100_000, 'family': 'small', 'layout': ('flat', 100),
                     'parts': [dict(SMALL, text=0)], 'skip_suffix': 500},
    'mixed-bimodal': {'files': 20_000, 'family': 'bimodal', 'layout': ('tree', 20), 'parts': [
        {'weight': 830, 'size': ('loguniform', 6, 13), 'text': 700},
        {'weight': 166, 'size': ('loguniform', 13, 19), 'text': 500},
        {'weight': 4, 'size': ('loguniform', 23, 24), 'text': 250}]},
    'mixed-threshold': {'files': 1_500, 'family': 'threshold', 'layout': ('tree', 8),
                        'parts': [{'weight': 1000, 'size': ('loguniform', 10, 23), 'text': 500}]},
    # Large files, for link-rate copies; incompressible. large-one is a real 8 GB ISO, pinned with `manifest`.
    'large-four': {'files': 4, 'family': 'large', 'layout': ('flat', 0),
                   'parts': [{'weight': 1000, 'size': ('fixed', 2048 * MIB), 'text': 0}]},
    'large-mixed': {'files': 32, 'family': 'large', 'layout': ('flat', 0),
                    'parts': [{'weight': 1000, 'size': ('loguniform', 24, 30), 'text': 0}]},
}


def spec_for(name):
    """The specification of a named corpus, including the scale-* series."""
    if name in SPECS:
        return SPECS[name]
    kind, _, value = name.rpartition('-')
    if kind in ('scale-size', 'scale-count') and value.isdigit() and int(value) > 0:
        number = int(value)
        if kind == 'scale-count':  # the first N files of the small family
            return {'files': number, 'family': 'small', 'layout': ('flat', max(1, number // 1000)), 'parts': [SMALL]}
        if number <= 256 * MIB:    # 256 MiB in equal files
            files = 256 * MIB // number
            return {'files': files, 'family': f'size{number}', 'layout': ('flat', max(1, files // 1000)),
                    'parts': [{'weight': 1000, 'size': ('fixed', number), 'text': 1000}]}
    raise ValueError(f'unknown corpus {name}')


class Stream:
    """Integers from SHAKE-256: identical on every platform and Python version."""

    def __init__(self, *key):
        self.key = '/'.join(map(str, key)).encode()
        self.block, self.buffer, self.offset = 0, b'', 0

    def take(self, count):
        while len(self.buffer) - self.offset < count:
            fresh = hashlib.shake_256(self.key + b'#%d' % self.block).digest(4096)
            self.buffer, self.offset, self.block = self.buffer[self.offset:] + fresh, 0, self.block + 1
        self.offset += count
        return self.buffer[self.offset - count:self.offset]

    def bits(self, count):
        return int.from_bytes(self.take((count + 7) // 8), 'big') >> (-count % 8)

    def below(self, limit):
        width = (limit - 1).bit_length()
        while True:
            value = self.bits(width) if width else 0
            if value < limit:
                return value


def exp2(fixed):
    """2 ** (fixed / 65536), interpolated linearly inside the octave, in integers."""
    whole, part = fixed >> 16, fixed & 0xFFFF
    return ((65536 + part) << whole) >> 16 if whole >= 0 else 0


def draw_size(stream, size):
    if size[0] == 'fixed':
        return size[1]
    if size[0] == 'loguniform':
        return exp2((size[1] << 16) + stream.below((size[2] - size[1]) << 16))
    # Twelve uniform 16-bit draws, centred: close to normal with deviation 65536.
    normal = sum(stream.bits(16) for _ in range(12)) - 393210
    return min(size[4], max(size[3], exp2((size[1] << 16) + ((normal * size[2]) >> 16))))


def relative_path(layout, files, index, suffix):
    name = f'f{index:07d}{suffix}'
    kind, value = layout
    if kind == 'flat':
        return f'd{index % value:04d}/{name}' if value else name
    if kind == 'tree':
        return f'd{index % value:02d}/d{index // value % value:02d}/{name}'
    base = 2  # deep: one directory per file, `value` levels, the narrowest tree that holds them all
    while base ** value < files:
        base += 1
    digits = [index // base ** level % base for level in range(value)]
    return '/'.join(f'd{digit}' for digit in digits[::-1]) + '/' + name


def plan(name, tier='full'):
    """Every file of a corpus as (index, path, size, is_text), in index order."""
    spec = spec_for(name)
    stream = Stream('meta', SEED, spec['family'])
    files = []
    for index in range(max(1, spec['files'] // TIERS[tier])):
        pick, part = stream.below(1000), None
        for part in spec['parts']:
            if pick < part['weight']:
                break
            pick -= part['weight']
        size = draw_size(stream, part['size'])
        # Both draws are always taken so every corpus of a family sees the same stream.
        text, skip = stream.below(1000) < part['text'], stream.below(1000) < spec.get('skip_suffix', 0)
        if skip:
            suffix = SKIP_SUFFIXES[index % len(SKIP_SUFFIXES)]
        else:
            suffix = TEXT_SUFFIXES[index % len(TEXT_SUFFIXES)] if text else '.bin'
        files.append((index, relative_path(spec['layout'], spec['files'], index, suffix), size, text))
    return spec, files


@functools.lru_cache(maxsize=None)
def phrases():
    stream, pool = Stream('phrases', SEED), []
    for _ in range(2048):
        words = [''.join(CONSONANTS[stream.below(14)] + VOWELS[stream.below(5)] for _ in range(1 + stream.below(3)))
                 for _ in range(3 + stream.below(6))]
        pool.append(' '.join(words).encode() + b' ')
    return tuple(pool)


def content(family, index, size, text):
    """Yield at least `size` bytes: records of pooled phrases and hex tokens, or noise."""
    key, block, made = f'{SEED}/{family}/{index}/'.encode(), 0, 0
    pool = phrases() if text else None
    while made < size:
        if text:
            count = min(1024, (size - made) // 40 + 2)
            raw = hashlib.shake_256(key + b't%d' % block).digest(4 * count + 12)
            noise = raw.hex().encode()
            chunk = b''.join([pool[(raw[i] << 8 | raw[i + 1]) & 2047]
                              + noise[2 * i + 4:2 * i + 12 + (raw[i + 2] & 15)] + b'\n'
                              for i in range(0, 4 * count, 4)])
        else:
            chunk = hashlib.shake_256(key + b'o%d' % block).digest(min(MIB, size - made))
        block, made = block + 1, made + len(chunk)
        yield chunk


def write_batch(job):
    """Write a batch of planned files; return (path, size, sha256, class) for each."""
    root, family, batch = job
    done = []
    for index, path, size, text in batch:
        digest, left = hashlib.sha256(), size
        descriptor = os.open(os.path.join(root, path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, 'wb') as stream:
            for chunk in content(family, index, size, text):
                chunk = chunk[:left]
                stream.write(chunk)
                digest.update(chunk)
                left -= len(chunk)
            os.fchmod(descriptor, 0o644)
        os.utime(os.path.join(root, path), (MTIME + index, MTIME + index))
        done.append((path, size, digest.hexdigest(), 'text' if text else 'opaque'))
    return done


def hash_batch(job):
    root, paths = job
    done = []
    for path in paths:
        digest = hashlib.sha256()
        with open(os.path.join(root, path), 'rb') as stream:
            while chunk := stream.read(MIB):
                digest.update(chunk)
        done.append((path, digest.hexdigest()))
    return done


def pooled(function, jobs, workers):
    """Apply a batch function to jobs, in worker processes when that helps."""
    if workers <= 1 or len(jobs) <= 1:
        return [item for job in jobs for item in function(job)]
    with multiprocessing.Pool(workers) as pool:
        return [item for batch in pool.imap_unordered(function, jobs) for item in batch]


def batches(items, size=BATCH):
    return [items[start:start + size] for start in range(0, len(items), size)]


def scan(root, hashes, workers):
    """Manifest entries of everything under root, sorted by path."""
    root = os.fspath(root)
    entries, regular, inodes = [], [], {}
    for directory, names, files in os.walk(root):
        for name in names + files:
            full = os.path.join(directory, name)
            path = os.path.relpath(full, root).replace(os.sep, '/')
            info = os.lstat(full)
            entry = {'path': path, 'type': 'o', 'mode': stat.S_IMODE(info.st_mode), 'size': 0,
                     'mtime': info.st_mtime_ns // 10**9, 'data': None, 'link': None, 'depth': path.count('/')}
            if stat.S_ISLNK(info.st_mode):
                # A symlink's own mode and time are not portable between systems.
                entry.update(type='l', mode=0, mtime=0, data=os.readlink(full))
            elif stat.S_ISDIR(info.st_mode):
                entry['type'] = 'd'
            elif stat.S_ISREG(info.st_mode):
                entry.update(type='f', size=info.st_size)
                regular.append(path)
                if info.st_nlink > 1:
                    inodes.setdefault((info.st_dev, info.st_ino), []).append(path)
            entries.append(entry)
    entries.sort(key=lambda entry: entry['path'])
    by_path = {entry['path']: entry for entry in entries}
    if hashes:
        for path, digest in pooled(hash_batch, [(root, batch) for batch in batches(regular)], workers):
            by_path[path]['data'] = digest
    for paths in inodes.values():  # later names of one inode point at its first
        first = min(paths)
        for path in paths:
            if path != first:
                by_path[path]['link'] = first
    return entries


def canonical(entry, hashes=True):
    data = entry['data'] if hashes or entry['type'] != 'f' else None
    return json.dumps([entry['path'], entry['type'], entry['mode'], entry['size'], entry['mtime'], data,
                       entry['link']], ensure_ascii=True, separators=(',', ':'))


def digest_of(entries, hashes=True):
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(canonical(entry, hashes).encode() + b'\n')
    return digest.hexdigest()


def zstd_ratio(root, entries):
    """zstd -3 ratio of the first files in path order, as one stream; None without zstd."""
    tool = shutil.which('zstd')
    if not tool:
        return None
    process = subprocess.Popen([tool, '-3', '-c', '-q'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    raw = 0

    def feed():
        nonlocal raw
        for entry in entries:
            if entry['type'] == 'f' and raw < RATIO_SAMPLE:
                with open(os.path.join(root, entry['path']), 'rb') as stream:
                    while chunk := stream.read(MIB):
                        process.stdin.write(chunk)
                        raw += len(chunk)
        process.stdin.close()

    feeder = threading.Thread(target=feed)
    feeder.start()
    packed = sum(len(chunk) for chunk in iter(lambda: process.stdout.read(MIB), b''))
    feeder.join()
    process.stdout.close()
    return round(raw / packed, 3) if process.wait() == 0 and packed else None


def describe(name, tier, root, entries, extra=None):
    """The manifest header: counts, size quantiles and both digests."""
    sizes = sorted(entry['size'] for entry in entries if entry['type'] == 'f')
    count = lambda kind: sum(entry['type'] == kind for entry in entries)
    header = {'schema': 1, 'name': name, 'tier': tier, 'files': len(sizes), 'directories': count('d'),
              'symlinks': count('l'), 'other': count('o'),
              'hardlinks': sum(entry['link'] is not None for entry in entries), 'bytes': sum(sizes),
              'size_quantiles': {label: sizes[(len(sizes) - 1) * part // 1000] if sizes else 0
                                 for label, part in (('p10', 100), ('p50', 500), ('p90', 900), ('p99', 990),
                                                     ('max', 1000))},
              'max_depth': max((entry['depth'] for entry in entries), default=0),
              'digest': digest_of(entries), 'quick_digest': digest_of(entries, hashes=False),
              'zstd3_ratio_sample': zstd_ratio(root, entries),
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
              'host': socket.gethostname(), 'python': platform.python_version()}
    header.update(extra or {})
    return header


def save(prefix, header, entries):
    """Write PREFIX.manifest.json and PREFIX.files.jsonl."""
    with open(f'{prefix}.files.jsonl', 'w') as stream:
        for entry in entries:
            stream.write(json.dumps(entry, separators=(',', ':')) + '\n')
    pathlib.Path(f'{prefix}.manifest.json').write_text(json.dumps(header, indent=2) + '\n')


def pinned(name, tier):
    try:
        return json.loads((HERE / 'corpora.json').read_text()).get(f'{name}:{tier}')
    except (OSError, ValueError):
        return None


def pin(root):
    """Record the digests of the corpora whose manifests are under root in corpora.json."""
    path = HERE / 'corpora.json'
    table = json.loads(path.read_text()) if path.exists() else {}
    for manifest in sorted(pathlib.Path(root).glob('*.manifest.json')):
        header = json.loads(manifest.read_text())
        if header.get('generator') == GENERATOR:
            keys = ('generator', 'files', 'directories', 'bytes', 'digest', 'quick_digest')
        elif header['tier'] == 'real':  # a frozen copy of a real tree: pinned as found
            keys = ('files', 'directories', 'symlinks', 'hardlinks', 'bytes', 'size_quantiles', 'digest',
                    'quick_digest', 'utc')
        else:
            continue
        table[f'{header["name"]}:{header["tier"]}'] = {key: header[key] for key in keys}
    path.write_text(json.dumps(dict(sorted(table.items())), indent=1) + '\n')
    return table


def generate(name, tier, root, workers, replace):
    spec, files = plan(name, tier)
    root = pathlib.Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()) and not (root / MARKER).exists():
        raise SystemExit(f'{root} is not empty and has no {MARKER} marker; refusing to write there')
    (root / MARKER).write_text('owned by benchmarks/lab/corpus.py\n')
    label = name if tier == 'full' else f'{name}-{tier}'
    tree = root / label
    if tree.exists():
        if not replace:
            raise SystemExit(f'{tree} exists; pass --replace to rebuild it')
        shutil.rmtree(tree)
    tree.mkdir()
    directories = sorted({parent for _, path, _, _ in files for parent in pathlib.PurePosixPath(path).parents
                          if str(parent) != '.'}, key=str)
    for directory in directories:
        (tree / directory).mkdir(parents=True, exist_ok=True)
    jobs = [(str(tree), spec['family'], batch) for batch in batches(files)]
    written = {path: (size, digest, kind) for path, size, digest, kind in pooled(write_batch, jobs, workers)}
    for directory in sorted(directories, key=lambda path: -len(path.parts)):
        os.chmod(tree / directory, 0o755)
        os.utime(tree / directory, (MTIME, MTIME))
    # What is on disk, with the hashes computed while writing.
    entries = scan(tree, hashes=False, workers=1)
    for entry in entries:
        if entry['type'] == 'f':
            entry['data'], entry['class'] = written[entry['path']][1], written[entry['path']][2]
    if len(written) != len(files) or sum(entry['type'] == 'f' for entry in entries) != len(files):
        raise SystemExit(f'{tree}: wrote {len(written)} of {len(files)} planned files')
    header = describe(name, tier, tree, entries, {'generator': GENERATOR, 'seed': SEED, 'spec': spec})
    save(root / label, header, entries)
    expected = pinned(name, tier)
    if expected and expected.get('generator') == GENERATOR and expected['digest'] != header['digest']:
        raise SystemExit(f'{label}: digest {header["digest"]} differs from the pinned {expected["digest"]}')
    return header


def verify(tree, manifest, quick, workers):
    """Compare a tree with a manifest. Returns (ok, header, differing paths)."""
    header = json.loads(pathlib.Path(manifest).read_text())
    entries = scan(tree, hashes=not quick, workers=workers)
    key = 'quick_digest' if quick else 'digest'
    if digest_of(entries, hashes=not quick) == header[key]:
        return True, header, []
    listing = pathlib.Path(str(manifest).removesuffix('.manifest.json') + '.files.jsonl')
    if not listing.exists():
        return False, header, []
    recorded = {entry['path']: canonical(entry, not quick)
                for entry in map(json.loads, listing.read_text().splitlines())}
    found = {entry['path']: canonical(entry, not quick) for entry in entries}
    return False, header, sorted(path for path in recorded.keys() | found.keys()
                                 if recorded.get(path) != found.get(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list', help='the named corpora and their planned sizes')
    p = commands.add_parser('generate', help='build a named corpus under ROOT and write its manifest')
    p.add_argument('name')
    p.add_argument('--root', required=True, type=pathlib.Path)
    p.add_argument('--tier', choices=TIERS, default='full')
    p.add_argument('--replace', action='store_true')
    p = commands.add_parser('manifest', help='pin an existing tree: write PREFIX.manifest.json and .files.jsonl')
    p.add_argument('tree', type=pathlib.Path)
    p.add_argument('--name', required=True)
    p.add_argument('--output', required=True, help='PREFIX, outside the tree')
    p = commands.add_parser('verify', help='check a tree against a manifest')
    p.add_argument('tree', type=pathlib.Path)
    p.add_argument('--manifest', required=True, type=pathlib.Path)
    p.add_argument('--quick', action='store_true', help='compare names, types, sizes, modes and times only')
    for p in commands.choices.values():
        p.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    p = commands.add_parser('pin', help='record the digests of the manifests under ROOT in corpora.json')
    p.add_argument('root', type=pathlib.Path)
    args = parser.parse_args(argv)
    if args.command == 'list':
        for name in SPECS:
            _, files = plan(name)
            print(f'{name:16} {len(files):>7} files {sum(size for _, _, size, _ in files) / MIB:>8.0f} MiB')
        print('scale-size-BYTES  256 MiB in equal files; scale-count-FILES  the first files of small-flat')
        return
    if args.command == 'pin':
        print(f'{len(pin(args.root))} corpora pinned in {HERE / "corpora.json"}')
        return
    if args.command == 'generate':
        try:
            header = generate(args.name, args.tier, args.root, args.jobs, args.replace)
        except ValueError as error:
            parser.error(str(error))
    elif args.command == 'manifest':
        if not args.tree.is_dir():
            parser.error('tree is not a directory')
        tree, output = args.tree.resolve(), pathlib.Path(args.output).resolve()
        if tree == output.parent or tree in output.parents:
            parser.error('--output must be outside the tree')
        entries = scan(tree, hashes=True, workers=args.jobs)
        header = describe(args.name, 'real', tree, entries)
        save(output, header, entries)
    else:
        ok, header, different = verify(args.tree, args.manifest, args.quick, args.jobs)
        if not ok:
            for path in different[:20]:
                print('DIFFERS', path)
            sys.exit(f'{args.tree} does not match {args.manifest} ({len(different)} paths differ)')
    json.dump({key: header[key] for key in ('name', 'tier', 'files', 'directories', 'bytes', 'size_quantiles',
                                             'zstd3_ratio_sample', 'digest', 'quick_digest')}, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
