#!/usr/bin/env python3
"""Profile an identified xs peer without changing its protocol input/output."""
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys


def main():
    # This helper is staged as ROOT/bin/xs-f14-profile.
    root = pathlib.Path(__file__).resolve().parent.parent
    if not (root / '.xsync-benchmark-owner.json').is_file():
        raise RuntimeError('missing benchmark ownership marker')
    config = json.loads((root / 'logs/f14-profile-config.json').read_text())
    revision = config['revision']
    if not re.fullmatch(r'[0-9a-f]{12}', revision):
        raise RuntimeError('expected a clean twelve-digit revision')
    xs = str(root / 'bin' / ('xs-' + revision))
    if hashlib.sha256(pathlib.Path(xs).read_bytes()).hexdigest() != config['xs_sha256']:
        raise RuntimeError('peer product does not match its recorded hash')
    if sys.argv[1:] == ['--version']:
        os.execv(xs, [xs, '--version'])
    if sys.argv[1:] != ['--server']:
        raise RuntimeError('profile helper expects the native xs server entry point')
    proof = json.loads((root / 'logs/f14-profiler-products.json').read_text())
    if not proof.get('complete'):
        raise RuntimeError('profiler product qualification is incomplete')
    parent = pathlib.Path('/proc') / str(os.getppid()) / 'cmdline'
    args = parent.read_bytes().decode().strip('\0').split('\0')
    metrics = pathlib.Path(args[args.index('--metrics') + 1])
    if metrics.parent != root / 'logs':
        raise RuntimeError('peer metrics are outside the owned log directory')
    # The native role is negotiated inside the protocol, not in --server argv.
    match = re.fullmatch(r'f14-(push|pull)-(noop|checksum)-xs-remote', metrics.stem)
    if not match:
        raise RuntimeError('unrecognized checksum-profile measurement label')
    flow, case = match.groups()
    role = 'receiver' if flow == 'push' else 'source'
    output = root / 'logs' / (metrics.stem + '-' + role + '-' + str(os.getpid()) + '.perf.data')
    record = {
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'flow': flow, 'scenario': case, 'role': role, 'metrics': str(metrics),
        'output': str(output), 'xs': xs, 'xs_sha256': config['xs_sha256'],
        'argv': sys.argv[1:], 'event': 'cpu-clock:u', 'frequency_hz': 99,
        'call_graph': 'dwarf,8192', 'profiler': proof['version'],
    }
    with (root / 'logs/f14-profile-index.jsonl').open('a') as out:
        out.write(json.dumps(record) + '\n')
    prefix = root / 'tools/perf'
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / 'usr/lib'),
               PERF_EXEC_PATH=str(prefix / 'usr/lib/perf-core'),
               XSYNC_CONFIG='', XSYNC_OPTS='')
    perf = str(prefix / 'usr/bin/perf')
    os.execve(perf, [perf, 'record', '-q', '-e', 'cpu-clock:u', '-F', '99',
                    '--call-graph', 'dwarf,8192', '-o', str(output), '--', xs, '--server'], env)


if __name__ == '__main__':
    main()
