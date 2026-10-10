#!/usr/bin/env python3
"""Fetch validated incremental pair evidence without restarting its live job."""
import argparse
import json
import pathlib
import re
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=pathlib.Path, default=pathlib.Path('.bench/p3-state.json'))
    parser.add_argument('--dataset', choices=('mixed', 'large', 'tiny', 'congress', 'update-1pct'), required=True)
    parser.add_argument('--direction', choices=('push', 'pull'), required=True)
    parser.add_argument('--output', type=pathlib.Path, default=pathlib.Path('benchmarks/results'))
    args = parser.parse_args()
    state = json.loads(args.state.read_text())
    run_id = state['run_id']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', run_id):
        parser.error('unsafe run ID')
    if state['neo'].startswith('-') or not state['root'].startswith('/'):
        parser.error('invalid staged host or root')
    source = state['root'] + '/logs/' + args.dataset + '-' + args.direction + '.json'
    command = ['ssh', '-oBatchMode=yes', '-oConnectTimeout=10', state['neo'],
               'cat -- ' + shlex.quote(source)]
    # The live runner writes JSON between samples. Retry a concurrent write,
    # preserving the last local checkpoint if a read is incomplete.
    for attempt in range(3):
        raw = subprocess.check_output(command, text=True, timeout=20)
        try:
            data = json.loads(raw)
            break
        except json.JSONDecodeError:
            if attempt == 2:
                raise
    if data.get('label') != args.dataset or data.get('direction') != args.direction:
        raise ValueError('checkpoint does not match the requested case')
    if data.get('target') != state['freya'] + ':' + state['root']:
        raise ValueError('checkpoint target does not match staged hosts')
    if not all(r.get('verified') and r.get('returncode') == 0 and
               r.get('remote', {}).get('returncode') == 0 for r in data.get('records', [])):
        raise ValueError('checkpoint contains an unverified record')
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / (run_id + '-' + args.dataset + '-' + args.direction + '.json')
    temporary = destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(destination)
    print(f"{destination}: {len(data.get('records', []))} verified samples, complete={bool(data.get('complete'))}")


if __name__ == '__main__':
    main()
