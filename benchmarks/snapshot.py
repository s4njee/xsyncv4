#!/usr/bin/env python3
"""Capture small, read-only Linux load/cache/I/O snapshots over SSH."""
import argparse
import datetime
import json
import pathlib
import shlex
import subprocess

PROBE = r'''
import datetime, json, os, pathlib, socket
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'host': socket.gethostname(), 'loadavg': list(os.getloadavg())}
mem = {}
for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
    key, value = line.split(':', 1)
    if key in ('MemTotal', 'MemAvailable', 'Cached', 'Buffers', 'SwapTotal', 'SwapFree', 'SReclaimable', 'Dirty', 'Writeback'):
        mem[key] = value.strip()
result['memory'] = mem
result['cpu_jiffies'] = pathlib.Path('/proc/stat').read_text().splitlines()[0]
disks = {}
for line in pathlib.Path('/proc/diskstats').read_text().splitlines():
    fields = line.split()
    name = fields[2]
    if name.startswith(('loop', 'ram', 'zram')):
        continue
    disks[name] = {'reads': int(fields[3]), 'read_sectors': int(fields[5]),
                   'writes': int(fields[7]), 'write_sectors': int(fields[9]),
                   'inflight': int(fields[11]), 'io_ms': int(fields[12])}
result['disks'] = disks
arc = pathlib.Path('/proc/spl/kstat/zfs/arcstats')
if arc.exists():
    wanted = {'size', 'c', 'c_min', 'c_max', 'data_size', 'metadata_size',
              'hits', 'misses', 'demand_data_hits', 'demand_data_misses',
              'demand_metadata_hits', 'demand_metadata_misses',
              'prefetch_data_hits', 'prefetch_data_misses', 'compressed_size',
              'uncompressed_size'}
    result['zfs_arc'] = {f[0]: int(f[2]) for line in arc.read_text().splitlines()
                         if len(f := line.split()) == 3 and f[0] in wanted}
print(json.dumps(result))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', action='append', required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    snapshots = []
    for target in args.target:
        if target.startswith('-'):
            parser.error('invalid SSH target')
        command = ['ssh', '-oBatchMode=yes', '-oConnectTimeout=10', target,
                   shlex.join(['python3', '-c', PROBE])]
        snapshots.append(json.loads(subprocess.check_output(command, text=True, timeout=20)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'snapshots': snapshots}, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
