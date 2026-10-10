#!/usr/bin/env python3
"""Measure disk-free, uncompressed SSH streams with exact byte-count checks."""
import argparse
import datetime
import json
import os
import pathlib
import shlex
import socket
import statistics
import subprocess
import sys

from measure import measure

RSH = ['ssh', '-oBatchMode=yes', '-oCompression=no', '-oControlMaster=no', '-oConnectTimeout=10']


def send_bytes(fd, count):
    block = bytes(1024 * 1024)
    remaining = count
    while remaining:
        chunk = memoryview(block)[:min(remaining, len(block))]
        while chunk:
            written = os.write(fd, chunk)
            chunk = chunk[written:]
            remaining -= written


def receive_bytes(fd, expected):
    received = 0
    while block := os.read(fd, 1024 * 1024):
        received += len(block)
        if received > expected:
            raise RuntimeError('stream exceeded expected byte count')
    if received != expected:
        raise RuntimeError(f'truncated stream: {received} != {expected}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('probe', 'pipeline', 'send', 'receive'), default='probe')
    p.add_argument('--bytes', type=int, default=2**31)
    p.add_argument('--host')
    p.add_argument('--remote-root')
    p.add_argument('--direction', choices=('push', 'pull'), default='push')
    p.add_argument('--runs', type=int, default=3)
    p.add_argument('--peer-metrics')
    p.add_argument('--output', type=pathlib.Path)
    args = p.parse_args()
    if args.bytes < 1 or args.runs < 1:
        p.error('byte count and runs must be positive')
    if args.mode == 'send':
        send_bytes(1, args.bytes)
        return
    if args.mode == 'receive':
        receive_bytes(0, args.bytes)
        return
    if not args.host or args.host.startswith('-') or not args.remote_root or not args.remote_root.startswith('/'):
        p.error('probe requires --host and an absolute --remote-root')
    role = 'receive' if args.direction == 'push' else 'send'
    if args.mode == 'pipeline':
        if not args.peer_metrics:
            p.error('pipeline requires a peer metrics path')
        command = ['python3', args.remote_root + '/bin/measure.py', '--metrics', args.peer_metrics,
                   '--', 'python3', args.remote_root + '/bin/stream_probe.py', '--mode', role,
                   '--bytes', str(args.bytes)]
        child = subprocess.Popen([*RSH, args.host, shlex.join(command)],
                                 stdin=subprocess.PIPE if args.direction == 'push' else subprocess.DEVNULL,
                                 stdout=subprocess.PIPE if args.direction == 'pull' else subprocess.DEVNULL)
        try:
            if args.direction == 'push':
                send_bytes(child.stdin.fileno(), args.bytes)
                child.stdin.close()
            else:
                receive_bytes(child.stdout.fileno(), args.bytes)
                child.stdout.close()
        except BaseException:
            child.terminate()
            child.wait()
            raise
        if child.wait():
            raise RuntimeError('SSH stream failed')
        return
    if not args.output:
        p.error('probe requires --output')
    # The operator stages these scripts; never write into installed helper paths.
    subprocess.run([*RSH, args.host, 'test -f ' + shlex.quote(args.remote_root + '/.xsync-benchmark-owner.json')], check=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'client': socket.gethostname(), 'host': args.host, 'direction': args.direction,
            'bytes': args.bytes, 'rsh': RSH, 'disk_io': False,
            'compression': 'none', 'records': []}
    for run in range(args.runs):
        peer_path = args.remote_root + '/logs/stream-' + args.direction + '-' + str(run + 1) + '.json'
        command = [sys.executable, str(pathlib.Path(__file__).resolve()), '--mode', 'pipeline',
                   '--host', args.host, '--remote-root', args.remote_root, '--direction', args.direction,
                   '--bytes', str(args.bytes), '--peer-metrics', peer_path]
        with args.output.with_suffix('.stderr').open('ab') as err:
            result = measure(command, stderr=err)
        if result['returncode']:
            raise RuntimeError('local stream failed: ' + repr(result))
        peer = json.loads(subprocess.check_output([*RSH, args.host, 'cat ' + shlex.quote(peer_path)], text=True))
        if peer['returncode']:
            raise RuntimeError('remote stream failed: ' + repr(peer))
        result.update({'run': run + 1, 'remote': peer, 'verified_bytes': args.bytes,
                       'bytes_per_second': args.bytes / result['wall_seconds']})
        data['records'].append(result)
        args.output.write_text(json.dumps(data, indent=2) + '\n')
        print(f"{args.direction} stream {run+1}/{args.runs}: {result['bytes_per_second']/1e6:.2f} MB/s", flush=True)
    data['median_bytes_per_second'] = statistics.median(r['bytes_per_second'] for r in data['records'])
    data['complete'] = True
    args.output.write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
