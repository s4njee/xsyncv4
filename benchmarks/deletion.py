#!/usr/bin/env python3
"""Verified deletion measurements for many stale subtrees and one stale root."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess

from measure import measure


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--rsync', default='rsync')
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runs', type=int, default=4)
    p.add_argument('--files', type=int, default=65536)
    args = p.parse_args()
    if args.runs < 1 or args.files < 1024 or args.files % 1024: p.error('positive runs and files divisible by 1024 required')
    work = args.work.resolve()
    if work.exists() and any(work.iterdir()): p.error('use a fresh empty owned directory')
    work.mkdir(parents=True, exist_ok=True)
    (work / '.xs-deletion-owned').write_text('created by benchmarks/deletion.py\n')
    os.environ['XSYNC_CONFIG'] = os.environ['XSYNC_OPTS'] = ''
    tools = {'reference': str(args.reference.resolve()), 'candidate-j1': str(args.candidate.resolve()),
             'candidate-j4': str(args.candidate.resolve()), 'rsync': shutil.which(args.rsync) or args.rsync}
    result = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'platform': platform.platform(), 'host': platform.node(), 'cpus': os.cpu_count(),
              'initial_loadavg': list(os.getloadavg()), 'cache': 'retained OS caches',
              'disk': subprocess.check_output(['df', '-k', str(work)], text=True),
              'files_per_case': args.files, 'runs': args.runs, 'records': [],
              'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'binaries': {tool: {'sha256': hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                                  'version': subprocess.check_output([binary, '--version'], text=True).splitlines()[0]}
                           for tool, binary in tools.items()}}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, indent=2) + '\n'); temporary.replace(args.output)
    save()
    source = work / 'source'; source.mkdir()
    os.utime(source, ns=(1700000000000000000, 1700000000000000000))
    seed = work / 'seed'; seed.mkdir()
    for number in range(args.files):
        leaf = seed / f'stale-{number // (args.files // 64):03}' / f'leaf-{number // 64:04}'
        leaf.mkdir(parents=True, exist_ok=True)
        (leaf / f'file-{number % 64:02}').write_bytes(b'stale fixture data\n')
    for case in ('many-subtrees', 'single-stale-root'):
        wrapped = work / 'wrapped'
        if case == 'single-stale-root':
            wrapped.mkdir(); shutil.move(str(seed), wrapped / 'stale')
        fixture = seed if case == 'many-subtrees' else wrapped
        for run in range(args.runs):
            order = list(tools); order = order[run % 4:] + order[:run % 4]
            for tool in order:
                destination = work / 'destination'
                subprocess.run([tools['rsync'], '-a', str(fixture) + '/', str(destination) + '/'],
                               check=True, stdout=subprocess.DEVNULL)
                command = [tools[tool], '-a', '--delete', '--stats']
                if tool != 'rsync': command += ['--no-fallback', '--no-progress', '-j1' if tool == 'candidate-j1' else '-j4']
                command += [str(source) + '/', str(destination) + '/']
                log = work / f'{case}-{tool}-{run+1}.stdout'
                with log.open('wb') as out, log.with_suffix('.stderr').open('wb') as err:
                    record = measure(command, stdout=out, stderr=err)
                check = subprocess.run([tools['rsync'], '-anci', '--delete', str(source) + '/', str(destination) + '/'],
                                       capture_output=True, text=True)
                if record['returncode'] or check.returncode or check.stdout.strip():
                    result['error'] = {'command': command, 'metrics': record, 'verification': check.stdout + check.stderr}
                    save(); raise RuntimeError(str(result['error']))
                record.update(case=case, tool=tool, run=run+1, command=command, verified=True,
                              stdout=log.read_text(), stderr=log.with_suffix('.stderr').read_text())
                result['records'].append(record); save()
                print(f"{case} {tool} {run+1}/{args.runs}: {record['wall_seconds']:.3f}s verified", flush=True)
                destination.rmdir()
    result['medians'] = {case: {tool: statistics.median(r['wall_seconds'] for r in result['records']
                                                       if r['case'] == case and r['tool'] == tool)
                               for tool in tools} for case in ('many-subtrees', 'single-stale-root')}
    result['final_loadavg'] = list(os.getloadavg()); result['complete'] = True; save()
    shutil.rmtree(wrapped)
    print(json.dumps(result['medians'], indent=2))


if __name__ == '__main__': main()
