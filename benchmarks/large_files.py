#!/usr/bin/env python3
"""Verified large-file comparisons: serial control, parallel ranges and kernel copies."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import random
import shlex
import shutil
import socket
import statistics
import subprocess

from measure import measure

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
CASES = ('byte-local', 'auto-local', 'pipe', 'pipe-z', 'single-byte-local', 'single-pipe', 'single-pipe-z')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=pathlib.Path, required=True)
    parser.add_argument('--candidate', type=pathlib.Path, required=True)
    parser.add_argument('--rsync', default='rsync')
    parser.add_argument('--work', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--samples', type=int, default=4)
    parser.add_argument('--candidate-jobs', type=int, default=4,
                        help='range budget (2..64); 0 measures automatic worker selection')
    parser.add_argument('--file-mib', type=int, default=256)
    parser.add_argument('--cases', default=','.join(CASES))
    args = parser.parse_args()
    cases = args.cases.split(',')
    if args.samples < 4 or args.samples % 4 or args.file_mib < 32 or any(c not in CASES for c in cases) or len(set(cases)) != len(cases) or args.candidate_jobs not in (0, *range(2, 65)):
        parser.error('use complete four-order cycles, files >=32 MiB and unique known cases')
    work = args.work.resolve()
    if work.exists() and any(work.iterdir()): parser.error('use a fresh empty owned work directory')
    work.mkdir(parents=True, exist_ok=True)
    (work / '.xs-large-owned').write_text('created by benchmarks/large_files.py\n')
    source, destinations, logs = work / 'source', work / 'destinations', work / 'logs'
    for directory in (source, destinations, logs): directory.mkdir()
    candidate = 'candidate-default' if not args.candidate_jobs else 'candidate-j' + str(args.candidate_jobs)
    tools = {'reference': str(args.reference.resolve()), 'candidate-j1': str(args.candidate.resolve()),
             candidate: str(args.candidate.resolve()), 'rsync': shutil.which(args.rsync) or args.rsync}
    result = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'host': socket.gethostname(), 'platform': platform.platform(), 'cpus': os.cpu_count(),
              'loadavg': list(os.getloadavg()), 'cache': 'retained caches, one verified warmup per tool/case',
              'filesystem': subprocess.check_output(['stat', '-f', '-c', '%T', str(work)], text=True).strip() if platform.system() == 'Linux' else 'see host filesystem metadata',
              'disk_usage': dict(zip(('total', 'used', 'free'), shutil.disk_usage(work))),
              'logical_bytes': args.file_mib * 2 * 2**20, 'samples_per_tool': args.samples,
              'candidate_jobs': args.candidate_jobs,
              'warmups': [], 'records': [], 'summary': []}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(result, indent=2) + '\n')
        temporary.replace(args.output)
    save()
    try:
        result['binaries'] = {tool: {'sha256': hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest(),
                                    'version': subprocess.check_output([binary, '--version'], text=True).splitlines()[0]}
                               for tool, binary in tools.items()}
        rng = random.Random(941)
        for name in ('compressible', 'random'):
            path = source / (name + '.bin')
            with path.open('wb') as out:
                for _ in range(args.file_mib): out.write(bytes(2**20) if name == 'compressible' else rng.randbytes(2**20))
            path.chmod(0o640)
            os.utime(path, ns=(1600000000123456789, 1600000000123456789))
        result['fixture_hashes'] = {}
        for path in source.iterdir():
            with path.open('rb') as stream: result['fixture_hashes'][path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
        ordered = list(tools)
        for case in cases:
            single = case.startswith('single-')
            pipe = 'pipe' in case
            verification_source = source
            if single:
                verification_source = work / ('source-' + case)
                verification_source.mkdir()
                name = 'compressible.bin' if case.endswith('-z') else 'random.bin'
                os.link(source / name, verification_source / name)
            for run in range(-1, args.samples):
                order = ordered[run % 4:] + ordered[:run % 4]
                for tool in order:
                    destination = destinations / tool
                    if destination.exists(): shutil.rmtree(destination)
                    if result['filesystem'] == 'btrfs':
                        # Settle delayed frees/writeback before the next timed
                        # copy, without flushing unrelated mounts.
                        subprocess.run(['sync', '-f', str(work)], check=True)
                    command = [tools[tool], '-aW' + ('z' if case.endswith('-z') else ''), '--stats']
                    if tool != 'rsync':
                        command += ['--no-fallback', '--no-progress']
                        if tool == 'reference': command += ['-j4']
                        elif tool == 'candidate-j1': command += ['-j1']
                        elif args.candidate_jobs: command += ['-j' + str(args.candidate_jobs)]
                        if case.endswith('byte-local'): command += ['--no-clone']
                    peer_path = logs / 'peer.json'
                    if pipe:
                        helper = shlex.join([__import__('sys').executable, str(HERE / 'measure.py'), '--metrics', str(peer_path), '--', tools[tool]])
                        command += ['-e', str(ROOT / 'tests/fakessh.sh'), '--rsync-path=' + helper]
                    command += [str(verification_source) + '/', ('test:' if pipe else '') + str(destination) + '/']
                    stdout, stderr = logs / 'stdout', logs / 'stderr'
                    with stdout.open('wb') as out, stderr.open('wb') as err: metrics = measure(command, stdout=out, stderr=err)
                    if metrics['returncode']: raise RuntimeError('transfer failed: ' + stderr.read_text(errors='replace'))
                    remote = json.loads(peer_path.read_text()) if pipe else None
                    if remote and remote['returncode']: raise RuntimeError('peer failed: ' + repr(remote))
                    verified = subprocess.run([tools['rsync'], '-anci', '--delete', str(verification_source) + '/', str(destination) + '/'], capture_output=True, text=True)
                    if verified.returncode or verified.stdout.strip(): raise RuntimeError('verification failed: ' + verified.stdout + verified.stderr)
                    metrics.update(case=case, tool=tool, run=run+1, verified=True, logical_bytes=args.file_mib * 2**20 * (1 if single else 2), remote=remote, command=command,
                                   stdout=stdout.read_text(errors='replace'), stderr=stderr.read_text(errors='replace'))
                    result['warmups' if run < 0 else 'records'].append(metrics)
                    save()
                    print(f'{case} {tool} {"warmup" if run < 0 else run+1}: {metrics["wall_seconds"]:.4f}s verified', flush=True)
                    shutil.rmtree(destination)
            medians = {tool: statistics.median(r['wall_seconds'] for r in result['records'] if r['case'] == case and r['tool'] == tool) for tool in tools}
            result['summary'].append({'case': case, 'median_seconds': medians,
                                      'candidate_speedup_over_reference': medians['reference']/medians[candidate],
                                      'parallel_speedup_over_one_worker': medians['candidate-j1']/medians[candidate],
                                      'candidate_speedup_over_rsync': medians['rsync']/medians[candidate]})
            save()
        result['complete'] = True
        save()
        return 0
    except Exception as error:
        result['error'] = str(error)
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
