#!/usr/bin/env python3
"""Serialize the Pi-local and paired five-million-file memory checks."""
import argparse
import datetime
import fcntl
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--peer', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--rss-limit-mib', type=int, default=512)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{12}', args.revision) or args.rss_limit_mib < 1:
        parser.error('provide a clean twelve-digit revision and a positive RSS limit')
    if args.peer.startswith('-') or ':' in args.peer:
        parser.error('peer must be an SSH host, without a path')
    root = args.root.resolve()
    if not (root / '.xsync-benchmark-owner.json').is_file():
        parser.error('missing benchmark ownership marker')
    label = 'large-tree-' + args.revision[:3]
    output = root / 'logs' / (label + '-qualification.json')
    lock = output.with_suffix('.lock').open('a+')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: parser.error('another large-tree qualification is running')
    if output.exists(): parser.error('qualification output exists; inspect it before starting another run')
    state = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'root': str(root), 'peer': args.peer, 'revision': args.revision,
             'rss_limit_mib_per_measured_xs_process': args.rss_limit_mib,
             'harness_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
             'complete': False, 'stages': []}

    def save():
        temp = output.with_suffix('.json.tmp')
        temp.write_text(json.dumps(state, indent=2) + '\n')
        temp.replace(output)

    save()
    try:
        print('Waiting for fixture preparation and the prior ext4 work lock', flush=True)
        manifest = root / 'logs/dataset-large-tree.json'
        deadline = time.monotonic() + 2 * 60 * 60
        while not manifest.exists() or not json.loads(manifest.read_text()).get('complete'):
            if time.monotonic() >= deadline:
                raise RuntimeError('fixture preparation did not complete within two hours')
            time.sleep(2)
        with (root / 'work/.xs-benchmark-lock').open('a+') as prior:
            fcntl.flock(prior, fcntl.LOCK_EX)
            fixture = json.loads(manifest.read_text())
        expected = {'files': 5_000_000, 'directories': 5000, 'bytes': 80_000_000}
        if not fixture.get('complete') or any(fixture.get(k) != v for k, v in expected.items()):
            raise RuntimeError('local five-million-file fixture is not complete')
        binary = root / 'bin' / ('xs-' + args.revision)
        version = subprocess.check_output([str(binary), '--version'], text=True).splitlines()[0]
        if not version.endswith('git ' + args.revision):
            raise RuntimeError('local product does not identify the requested clean revision')
        rsh = ['ssh', '-oBatchMode=yes', '-oCompression=no', '-oControlMaster=no', '-oConnectTimeout=10']
        probe = ('import hashlib,json,pathlib,subprocess; r=pathlib.Path(' + repr(str(root)) + '); '
                 'assert (r/".xsync-benchmark-owner.json").is_file(); b=r/"bin"/' + repr(binary.name) + '; '
                 'print(json.dumps({"fixture":json.loads((r/"logs/dataset-large-tree.json").read_text()),'
                 '"version":subprocess.check_output([str(b),"--version"],text=True).splitlines()[0],'
                 '"sha256":hashlib.sha256(b.read_bytes()).hexdigest()}))')
        peer = json.loads(subprocess.check_output([*rsh, args.peer, 'python3 -c ' + shlex.quote(probe)], text=True))
        if not peer['fixture'].get('complete') or any(peer['fixture'].get(k) != v for k, v in expected.items()):
            raise RuntimeError('peer five-million-file fixture is not complete')
        if not peer['version'].endswith('git ' + args.revision):
            raise RuntimeError('peer product does not identify the requested clean revision')
        state.update(fixture=fixture, local_product={'version': version,
                     'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}, peer_product=peer)
        save()
        for stage in ('local', 'push', 'pull'):
            result_path = root / 'logs' / (label + '-' + stage + '.json')
            command = ['python3', str(root / 'bin/run.py'), '--corpus', str(root / 'data/large-tree'),
                       '--work', str(root / ('work-large-tree-local' if stage == 'local' else 'work-large-tree-pair')),
                       '--xsync', str(binary), '--runs', '1', '--scenarios', 'fresh',
                       '--label', label, '--output', str(result_path)]
            if stage != 'local':
                command += ['--target', args.peer + ':' + str(root), '--direction', stage,
                            '--remote-xs', str(binary), '--remote-measure', str(root / 'bin/measure.py'),
                            '--rsh', shlex.join(rsh)]
            if result_path.exists(): raise RuntimeError('stage output already exists: ' + str(result_path))
            print('Starting ' + stage + ' memory qualification', flush=True)
            subprocess.run(command, check=True)
            result = json.loads(result_path.read_text())
            if not result.get('complete') or len(result['records']) != 2:
                raise RuntimeError('stage did not complete both tool measurements')
            for record in result['records']:
                if not record.get('verified') or record['returncode']:
                    raise RuntimeError('unverified or failed stage sample')
                if stage != 'local' and (not record.get('remote') or record['remote']['returncode']):
                    raise RuntimeError('missing or failed peer measurement')
                if record['tool'] == 'xs':
                    peaks = [record['max_rss_bytes']]
                    if record.get('remote'): peaks.append(record['remote']['max_rss_bytes'])
                    if max(peaks) > args.rss_limit_mib * 1024**2:
                        raise RuntimeError('xs process peak exceeds the stated memory budget')
            state['stages'].append({'stage': stage, 'output': str(result_path), 'passed': True})
            save()
        state['complete'] = True
        save()
    except BaseException as error:
        state['error'] = repr(error)
        save()
        raise


if __name__ == '__main__': main()
