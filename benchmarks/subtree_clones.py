#!/usr/bin/env python3
"""Compare bounded APFS subtree clones with the leaf-only product and rsync."""
import argparse
import datetime
import hashlib
import itertools
import json
import os
import pathlib
import platform
import shutil
import statistics
import subprocess

from clone_modes import metadata
from measure import measure
from prepare import inventory


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=pathlib.Path, required=True)
    p.add_argument('--candidate', type=pathlib.Path, required=True)
    p.add_argument('--rsync', default='rsync')
    p.add_argument('--work', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--samples', type=int, default=6)
    p.add_argument('--smoke-fixtures', action='store_true')
    args = p.parse_args()
    if platform.system() != 'Darwin' or args.samples < 1: p.error('requires macOS and positive samples')
    work = args.work.resolve()
    if work.exists() and any(work.iterdir()): p.error('use a fresh empty work directory')
    work.mkdir(parents=True, exist_ok=True)
    (work/'.xs-subtree-clones-owned').write_text('created by subtree_clones.py\n')
    os.environ['XSYNC_CONFIG'] = os.environ['XSYNC_OPTS'] = ''
    os.umask(0o77)
    binaries = {'reference': str(args.reference.resolve()), 'candidate': str(args.candidate.resolve()),
                'rsync': shutil.which(args.rsync) or args.rsync}
    data = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'platform': platform.platform(), 'host': platform.node(), 'cpus': os.cpu_count(),
            'initial_loadavg': list(os.getloadavg()), 'cache': 'retained OS caches', 'jobs': 4,
            'umask': '0077', 'samples_per_tool': args.samples, 'smoke_fixtures': args.smoke_fixtures,
            'harness_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
            'disk': subprocess.check_output(['df', '-k', str(work)], text=True),
            'binaries': {}, 'fixtures': {}, 'records': [], 'warmups': []}
    for name, binary in binaries.items():
        version = subprocess.check_output([binary, '--version'], text=True).splitlines()[0]
        if name != 'rsync' and ('-dirty' in version or 'git unknown' in version):
            p.error('qualifying comparisons require clean identified products')
        data['binaries'][name] = {'version': version, 'sha256': hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest()}

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix('.json.tmp')
        temp.write_text(json.dumps(data, indent=2)+'\n')
        temp.replace(args.output)

    save()
    try:
        shapes = {'bounded': (4, 8, 32), 'near-limit': (8, 12, 40), 'over-limit': (16, 16, 32)}
        sources = work/'sources'
        sources.mkdir()
        for name, (groups, leaves, files) in shapes.items():
            if args.smoke_fixtures: groups, leaves, files = 2, 2, 4
            source = sources/name
            branch = source/'branch'
            branch.mkdir(parents=True)
            for g in range(groups):
                group = branch/f'group-{g:02}'
                for leaf in range(leaves):
                    parent = group/f'leaf-{leaf:02}'
                    parent.mkdir(parents=True)
                    for f in range(files):
                        path = parent/f'file-{f:03}'
                        path.write_bytes(hashlib.sha256(f'{name}/{g}/{leaf}/{f}'.encode()).digest()*16)
                        path.chmod(0o444 if f % 2 else 0o644)
                (group/'link').symlink_to('leaf-00/file-000')
            for path in [source, *source.rglob('*')]:
                if path.is_dir(): path.chmod(0o755)
                os.utime(path, ns=(1500000000123456789, 1500000000123456789), follow_symlinks=False)
            count = inventory(source)
            data['fixtures'][name] = {**count, 'symlinks': groups,
                                      'branch_descendant_entries': count['files'] + count['directories'] - 1 + groups}
        save()
        tools = list(binaries)
        orders = list(itertools.permutations(tools))
        for name in shapes:
            source = sources/name
            before = metadata(source)
            for flags in ('-a', '-rlt'):
                case = name + flags
                oracle = work/'oracle'
                subprocess.run([binaries['rsync'], flags, str(source)+'/', str(oracle)+'/'],
                               check=True, capture_output=True)
                expected = metadata(oracle)
                for sample in range(args.samples+1):
                    order = tools if not sample else orders[(sample-1) % len(orders)]
                    for tool in order:
                        destination = work/'destination'
                        command = [binaries[tool], flags]
                        if tool != 'rsync': command += ['--no-fallback', '--no-progress', '-j4']
                        command += [str(source)+'/', str(destination)+'/']
                        with (work/'stdout').open('wb') as out, (work/'stderr').open('wb') as err:
                            record = measure(command, stdout=out, stderr=err)
                        record.update(case=case, tool=tool, sample=sample, command=command, verified=False,
                                      stdout=(work/'stdout').read_text(errors='replace'),
                                      stderr=(work/'stderr').read_text(errors='replace'))
                        (data['warmups'] if not sample else data['records']).append(record)
                        save()
                        if record['returncode']: raise RuntimeError('copy failed: '+record['stderr'])
                        proof = subprocess.run([binaries['rsync'], '-anci', '--delete', str(oracle)+'/',
                                                str(destination)+'/'], capture_output=True, text=True)
                        if proof.returncode or proof.stdout.strip() or metadata(destination) != expected:
                            raise RuntimeError('checksum/metadata verification failed: '+proof.stdout+proof.stderr)
                        if metadata(source) != before: raise RuntimeError('source metadata changed')
                        record['verified'] = True
                        save()
                        print(f'{case} {tool} {sample}/{args.samples}: {record["wall_seconds"]:.4f}s verified', flush=True)
                        shutil.rmtree(destination)
                shutil.rmtree(oracle)
        data['summary'] = []
        for case in sorted({r['case'] for r in data['records']}):
            row = {'case': case, 'tools': {}}
            for tool in tools:
                records = [r for r in data['records'] if r['case']==case and r['tool']==tool]
                row['tools'][tool] = {'wall_seconds': statistics.median(r['wall_seconds'] for r in records),
                                     'cpu_seconds': statistics.median(r['user_seconds']+r['system_seconds'] for r in records),
                                     'peak_rss_bytes': max(r['max_rss_bytes'] for r in records)}
            data['summary'].append(row)
        data['complete'] = True
        data['final_loadavg'] = list(os.getloadavg())
        save()
        print(json.dumps(data['summary'], indent=2), flush=True)
        shutil.rmtree(sources)
    except BaseException as error:
        data['error'] = repr(error)
        save()
        raise


if __name__ == '__main__': main()
