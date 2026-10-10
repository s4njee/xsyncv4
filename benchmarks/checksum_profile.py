#!/usr/bin/env python3
"""Run verified paired checksum profiles after full-size memory qualification."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import re
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--peer', required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{12}', args.revision):
        parser.error('provide a clean twelve-digit revision')
    if args.peer.startswith('-') or ':' in args.peer:
        parser.error('peer must be an SSH host without a path')
    root = args.root.resolve()
    if not (root / '.xsync-benchmark-owner.json').is_file():
        parser.error('missing benchmark ownership marker')
    output = root / 'logs/f14-profile-state.json'
    lock = output.with_suffix('.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error('another checksum-profile coordinator is running')
    if output.exists():
        parser.error('profile state exists; inspect it before another run')
    state = {
        'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'root': str(root), 'peer': args.peer, 'revision': args.revision,
        'harness_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        'complete': False, 'stages': [],
        'purpose': 'user-CPU checksum profiling; instrumented timings are not throughput qualification',
    }

    def save():
        temp = output.with_suffix('.tmp')
        temp.write_text(json.dumps(state, indent=2) + '\n')
        temp.replace(output)

    save()
    try:
        print('Waiting for the complete large-tree memory qualification', flush=True)
        deadline = time.monotonic() + 21600
        prior = root / 'logs' / ('large-tree-' + args.revision[:3] + '-qualification.json')
        while True:
            if prior.exists():
                data = json.loads(prior.read_text())
                if data.get('error'):
                    raise RuntimeError('prior memory qualification failed: ' + data['error'])
                if data.get('complete'):
                    if data.get('revision') != args.revision or data.get('peer') != args.peer:
                        raise RuntimeError('prior qualification identifies a different product or peer')
                    break
            if time.monotonic() > deadline:
                raise RuntimeError('memory qualification has not finished in six hours')
            time.sleep(10)
        env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')
        for flow in ('push', 'pull'):
            print('Starting checksum profile ' + flow, flush=True)
            path = root / 'logs' / ('f14-' + flow + '-profile.json')
            if path.exists():
                raise RuntimeError('profile output exists: ' + str(path))
            subprocess.run([
                'python3', str(root / 'bin/run.py'), '--corpus', str(root / 'data/congress'),
                '--work', str(root / 'work-f14-profile'), '--target', args.peer + ':' + str(root),
                '--direction', flow, '--xsync', str(root / 'bin' / ('xs-' + args.revision)),
                '--remote-xs', str(root / 'bin/xs-f14-profile'),
                '--remote-measure', str(root / 'bin/measure.py'), '--runs', '1',
                '--scenarios', 'noop,checksum', '--label', 'f14-' + flow, '--output', str(path),
            ], env=env, check=True)
            result = json.loads(path.read_text())
            if not result.get('complete') or len(result['records']) != 4:
                raise RuntimeError('profile did not complete both tool/scenario pairs')
            for record in result['records']:
                if (not record.get('verified') or record['returncode'] or
                        not record.get('remote') or record['remote']['returncode']):
                    raise RuntimeError('profile has a failed or unverified measurement')
            state['stages'].append({'flow': flow, 'output': str(path), 'verified': True})
            save()
        state['complete'] = True
        save()
    except BaseException as error:
        state['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
