#!/usr/bin/env python3
"""Verified regression ratios against a pinned xs reference on the same runner."""
import argparse
import datetime
import hashlib
import itertools
import json
import os
import pathlib
import platform
import random
import re
import shlex
import shutil
import socket
import statistics
import subprocess
import sys

from measure import measure

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
CASES = {
    'local-fresh': ('small', ['-a'], False, False),
    'local-noop': ('small', ['-a'], False, True),
    'local-checksum': ('small', ['-ac'], False, True),
    'local-update': ('update', ['-a'], False, True),
    'local-rt': ('small', ['-rt'], False, False),
    'local-rlt': ('small', ['-rlt'], False, False),
    'pipe-fresh': ('small', ['-a'], True, False),
    'pipe-compressed': ('small', ['-az'], True, False),
    'pipe-noop': ('small', ['-a'], True, True),
    'pipe-checksum': ('small', ['-ac'], True, True),
    'pipe-update': ('update', ['-a'], True, True),
    'large-local': ('large', ['-a'], False, False),
    'large-pipe': ('large', ['-a'], True, False),
    'large-compressed': ('large', ['-az'], True, False),
    'large-single-local': ('large-single-random', ['-aW'], False, False),
    'large-single-pipe': ('large-single-random', ['-aW'], True, False),
    'large-single-compressed': ('large-single-compressible', ['-aWz'], True, False),
    'tiny-pipe': ('tiny', ['-a'], True, False),
}


def fixtures(root, seed, smoke):
    rng = random.Random(seed)
    small = root / 'small'
    small.mkdir()
    files = []
    leaves, per_leaf = (32, 4) if smoke else (2048, 4)
    for leaf in range(leaves):
        parent = small / f'group-{leaf//64:03}' / f'branch-{leaf//4:04}' / f'leaf-{leaf:05}'
        parent.mkdir(parents=True)
        for index in range(per_leaf):
            path = parent / f'file-{index:02}.json'
            prefix = f'{{"leaf":{leaf},"file":{index},"value":"'.encode()
            payload = prefix + b'x' * ((512 if smoke else 4096) - len(prefix) - 3) + b'"}\n'
            path.write_bytes(payload)
            path.chmod(0o666 if index == 0 else 0o444 if index == 1 else 0o644)
            os.utime(path, ns=(1700000000000000000, 1700000000000000000))
            files.append(path)
    update = root / 'update'
    shutil.copytree(small, update)
    changed = max(1, len(files) // 100)
    for path in files[:changed]:
        target = update / path.relative_to(small)
        data = target.read_bytes()
        mode = target.stat().st_mode & 0o777
        target.chmod(mode | 0o200)
        target.write_bytes(bytes([data[0] ^ 1]) + data[1:])
        target.chmod(mode)
        os.utime(target, ns=(1700000002000000000, 1700000002000000000))
    large = root / 'large'
    large.mkdir()
    large_bytes = 2**20 if smoke else 256 * 2**20
    for name in ('compressible', 'random'):
        with (large / (name + '.bin')).open('wb') as out:
            for _ in range(large_bytes // 2**20):
                out.write(bytes(2**20) if name == 'compressible' else rng.randbytes(2**20))
        single = root / ('large-single-' + name)
        single.mkdir()
        os.link(large / (name + '.bin'), single / (name + '.bin'))
    tiny = root / 'tiny'
    tiny.mkdir()
    (tiny / 'file').write_bytes(b'one small transfer\n')
    return {'small_files': len(files), 'small_file_bytes': 512 if smoke else 4096,
            'changed_files': changed, 'changed_fraction': changed / len(files),
            'large_files': 2, 'large_file_bytes': large_bytes, 'tiny_bytes': 19}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', type=pathlib.Path, required=True)
    p.add_argument('--reference', type=pathlib.Path, required=True)
    p.add_argument('--rsync', default='rsync')
    p.add_argument('--work', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--policy', type=pathlib.Path, default=HERE / 'ci-policy.json')
    p.add_argument('--samples', type=int)
    p.add_argument('--scenarios', default=','.join(CASES))
    p.add_argument('--smoke-fixtures', action='store_true', help='small fixtures for gate validation only')
    args = p.parse_args(argv)
    policy = json.loads(args.policy.read_text())
    samples = args.samples if args.samples is not None else policy['samples']
    floor = float(policy['minimum_relative_ratio'])
    cases = args.scenarios.split(',')
    if samples < 1 or not 0 < floor <= 1 or len(set(cases)) != len(cases) or any(case not in CASES for case in cases):
        p.error('invalid samples, ratio policy or scenario')
    binaries = {'reference': str(args.reference.resolve()), 'candidate': str(args.candidate.resolve()),
                'rsync': shutil.which(args.rsync) or args.rsync}
    work = args.work.resolve()
    if work.exists() and any(work.iterdir()):
        p.error('CI work directory must be empty; use a fresh owned directory')
    work.mkdir(parents=True, exist_ok=True)
    (work / '.xs-ci-owned').write_text('created by benchmarks/ci.py\n')
    source = work / 'source'
    source.mkdir()
    destinations = work / 'destinations'
    destinations.mkdir()
    logs = work / 'logs'
    logs.mkdir()
    results = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'host': socket.gethostname(), 'platform': platform.platform(), 'cpus': os.cpu_count(),
               'initial_loadavg': list(os.getloadavg()), 'cache': 'retained OS caches',
               'policy': policy, 'policy_sha256': hashlib.sha256(args.policy.read_bytes()).hexdigest(),
               'samples_per_tool': samples, 'smoke_fixtures': args.smoke_fixtures,
               'warmups_per_tool': 1, 'warmups': [], 'records': [], 'ratios': []}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(results, indent=2) + '\n')
        temporary.replace(args.output)
    save()
    try:
        results['binaries'] = {tool: {'path': binary, 'sha256': hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest(),
                                    'version': subprocess.check_output([binary, '--version'], text=True).splitlines()[0]}
                               for tool, binary in binaries.items()}
        reference_hash = re.search(r'\bgit ([0-9a-f]{12,40})(\S*)', results['binaries']['reference']['version'])
        if not args.smoke_fixtures and (not reference_hash or reference_hash[2] or
                                        not policy['reference'].startswith(reference_hash[1])):
            raise RuntimeError('reference binary does not identify the pinned clean source revision')
        results['fixtures'] = fixtures(source, policy['fixture_seed'], args.smoke_fixtures)
        save()
        orders = list(itertools.permutations(('rsync', 'reference', 'candidate')))
        for case in cases:
            dataset, flags, pipe, seeded = CASES[case]
            verification_source = source / dataset
            if case in ('local-rt', 'local-rlt'):
                # Without -p, newly created modes are limited by the inherited
                # umask. Compare against rsync's result, not source permissions.
                verification_source = work / ('oracle-' + case)
                subprocess.run([binaries['rsync'], *flags, str(source / dataset) + '/',
                                str(verification_source) + '/'], check=True,
                               stdout=subprocess.DEVNULL)
            # Warm code and fixture caches equally, then rotate through all six
            # orders in production so no tool is favored by its position.
            for run in range(-1, samples):
                for tool in orders[run % len(orders)]:
                    name = case + '-' + tool
                    destination = destinations / name
                    if destination.exists():
                        shutil.rmtree(destination)
                    if seeded:
                        baseline = source / ('small' if dataset == 'update' else dataset)
                        subprocess.run([binaries['rsync'], '-a', str(baseline) + '/', str(destination) + '/'],
                                       check=True, stdout=subprocess.DEVNULL)
                    command = [binaries[tool], *flags, '--stats']
                    if tool != 'rsync':
                        command += ['--no-progress', '--no-fallback']
                        if case == 'large-single-local':
                            command += ['--no-clone']
                    peer_path = logs / (name + '-peer.json')
                    if pipe:
                        helper = shlex.join([sys.executable, str(HERE / 'measure.py'), '--metrics', str(peer_path), '--', binaries[tool]])
                        command += ['-e', str(ROOT / 'tests/fakessh.sh'), '--rsync-path=' + helper]
                    command += [str(source / dataset) + '/', ('ci:' if pipe else '') + str(destination) + '/']
                    stdout = logs / (name + '-' + str(run + 1) + '.stdout')
                    stderr = stdout.with_suffix('.stderr')
                    with stdout.open('wb') as out, stderr.open('wb') as err:
                        metrics = measure(command, stdout=out, stderr=err)
                    if metrics['returncode']:
                        results['failed_sample'] = {'case': case, 'tool': tool, 'run': run + 1,
                                                   'command': command, 'metrics': metrics,
                                                   'stderr': stderr.read_text(errors='replace')[:4000]}
                        raise RuntimeError('transfer failed: ' + repr(results['failed_sample']))
                    peer = json.loads(peer_path.read_text()) if pipe else None
                    if peer and peer['returncode']:
                        raise RuntimeError('remote helper failed: ' + repr(peer))
                    verified = subprocess.run([binaries['rsync'], '-anci', '--delete', str(verification_source) + '/', str(destination) + '/'],
                                              capture_output=True, text=True)
                    if verified.returncode or verified.stdout.strip():
                        raise RuntimeError(f'{case} {tool} verification failed: ' + verified.stdout[:4000] + verified.stderr[:4000])
                    metrics.update({'case': case, 'tool': tool, 'run': run + 1, 'verified': True,
                                    'command': command, 'remote': peer,
                                    'stdout': stdout.read_text(errors='replace'), 'stderr': stderr.read_text(errors='replace')})
                    metrics['warmup'] = run < 0
                    results['warmups' if run < 0 else 'records'].append(metrics)
                    save()
                    label = 'warmup' if run < 0 else f'{run+1}/{samples}'
                    print(f"{case} {tool} {label}: {metrics['wall_seconds']:.4f}s verified", flush=True)
                    shutil.rmtree(destination)
            medians = {tool: statistics.median(r['wall_seconds'] for r in results['records'] if r['case'] == case and r['tool'] == tool)
                       for tool in binaries}
            reference_ratio = medians['rsync'] / medians['reference']
            candidate_ratio = medians['rsync'] / medians['candidate']
            minimum_ratio = reference_ratio * floor
            ratio = {'case': case, 'median_seconds': medians, 'reference_to_rsync': reference_ratio,
                     'minimum_to_rsync': minimum_ratio, 'candidate_to_rsync': candidate_ratio,
                     'passed': candidate_ratio >= minimum_ratio}
            results['ratios'].append(ratio)
            save()
            print(f"{case}: xs speedup relative to rsync {candidate_ratio:.3f}, recorded minimum {minimum_ratio:.3f}: " +
                  ('PASS' if ratio['passed'] else 'REGRESSION'), flush=True)
        results['complete'] = True
        results['passed'] = all(r['passed'] for r in results['ratios'])
        save()
        return 0 if results['passed'] else 1
    except Exception as error:
        results['error'] = str(error)
        results['passed'] = False
        save()
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
