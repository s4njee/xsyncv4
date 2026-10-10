#!/usr/bin/env python3
"""Compare anchored path reuse and worker budgets with verified byte copies."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import shlex
import shutil
import statistics
import subprocess

from measure import measure
from prepare import inventory


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', type=pathlib.Path, required=True)
    p.add_argument('--work', type=pathlib.Path, required=True)
    p.add_argument('--reference', type=pathlib.Path, required=True)
    p.add_argument('--candidate', type=pathlib.Path, required=True)
    p.add_argument('--rsync', default='rsync')
    p.add_argument('--samples', type=int, default=6)
    p.add_argument('--output', type=pathlib.Path, required=True)
    args = p.parse_args()
    if args.samples < 1: p.error('samples must be positive')
    source, work = args.corpus.resolve(), args.work.resolve()
    if not source.is_dir(): p.error('corpus is missing')
    if source == work or source in work.parents or work in source.parents:
        p.error('source and work must be disjoint')
    if work.exists() and any(work.iterdir()): p.error('use a fresh empty work directory')
    work.mkdir(parents=True, exist_ok=True)
    (work / '.xs-path-walks-owned').write_text('created by path_walks.py\n')
    os.environ['XSYNC_CONFIG'] = os.environ['XSYNC_OPTS'] = ''
    binaries = {'reference': str(args.reference.resolve()), 'candidate': str(args.candidate.resolve()),
                'rsync': shutil.which(args.rsync) or args.rsync}
    tools = [('reference-j4', 'reference', 4), *[(f'candidate-j{n}', 'candidate', n) for n in (1, 2, 4, 8)],
             ('rsync', 'rsync', None)]
    data = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'platform': platform.platform(), 'host': platform.node(), 'cpus': os.cpu_count(),
            'initial_loadavg': list(os.getloadavg()), 'cache': 'retained OS caches',
            'corpus': {'path': str(source), **inventory(source)},
            'disk': subprocess.check_output(['df', '-k', str(source), str(work)], text=True),
            'harness_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
            'binaries': {}, 'records': [], 'warmups': []}
    for name, binary in binaries.items():
        version = subprocess.check_output([binary, '--version'], text=True).splitlines()[0]
        if name != 'rsync' and ('-dirty' in version or 'git unknown' in version):
            p.error('qualifying measurements require a clean identified product')
        data['binaries'][name] = {'version': version, 'sha256': hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest()}

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, indent=2) + '\n')
        temporary.replace(args.output)

    save()
    try:
        for case in ('fresh-byte', 'noop'):
            for run in range(args.samples + 1):
                order = tools[run % len(tools):] + tools[:run % len(tools)]
                for label, binary, jobs in order:
                    destination = work / (case + '-' + label)
                    if case == 'noop' and run == 0:
                        subprocess.run([binaries['rsync'], '-a', str(source) + '/', str(destination) + '/'],
                                       check=True, capture_output=True)
                    command = [binaries[binary], '-a']
                    if jobs: command += ['--no-fallback', '--no-progress', '--no-clone', '-j' + str(jobs)]
                    command += [str(source) + '/', str(destination) + '/']
                    with (work / 'stdout').open('wb') as out, (work / 'stderr').open('wb') as err:
                        record = measure(command, stdout=out, stderr=err)
                    record.update({'case': case, 'tool': label, 'sample': run, 'command': command,
                                   'verified': False, 'stderr': (work / 'stderr').read_text(errors='replace')})
                    (data['warmups'] if run == 0 else data['records']).append(record)
                    save()
                    if record['returncode']: raise RuntimeError('copy failed: ' + shlex.join(command))
                    proof = subprocess.run([binaries['rsync'], '-anci', '--delete', str(source) + '/',
                                            str(destination) + '/'], capture_output=True, text=True)
                    if proof.returncode or proof.stdout.strip():
                        raise RuntimeError('checksum/metadata verification failed: ' + proof.stdout + proof.stderr)
                    record['verified'] = True
                    save()
                    print(f'{case} {label} {run}/{args.samples}: {record["wall_seconds"]:.4f}s verified', flush=True)
                    if case == 'fresh-byte': shutil.rmtree(destination)
            if case == 'noop':
                for label, _, _ in tools: shutil.rmtree(work / (case + '-' + label))
        data['summary'] = []
        for case in ('fresh-byte', 'noop'):
            row = {'case': case, 'tools': {}}
            for label, _, _ in tools:
                records = [r for r in data['records'] if r['case'] == case and r['tool'] == label]
                row['tools'][label] = {'wall_seconds': statistics.median(r['wall_seconds'] for r in records),
                                      'cpu_seconds': statistics.median(r['user_seconds'] + r['system_seconds'] for r in records),
                                      'peak_rss_bytes': max(r['max_rss_bytes'] for r in records)}
            data['summary'].append(row)
        data['complete'] = True
        data['final_loadavg'] = list(os.getloadavg())
        save()
        print(json.dumps(data['summary'], indent=2), flush=True)
    except BaseException as error:
        data['error'] = str(error)
        save()
        raise


if __name__ == '__main__': main()
