#!/usr/bin/env python3
"""Transparent child resource measurement, including remote rsync/xs helpers."""
import argparse
import json
import os
import pathlib
import signal
import subprocess
import sys
import time


def measure(command, *, stdin=None, stdout=None, stderr=None):
    started = time.perf_counter()
    child = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr)
    previous = {}
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        previous[signum] = signal.signal(signum, lambda s, frame: child.send_signal(s) if child.poll() is None else None)
    try:
        while True:
            try:
                _, status, usage = os.wait4(child.pid, 0)
                break
            except InterruptedError:
                continue
        child.returncode = os.waitstatus_to_exitcode(status)
        return {'returncode':child.returncode, 'wall_seconds':time.perf_counter()-started,
                'user_seconds':usage.ru_utime, 'system_seconds':usage.ru_stime,
                'max_rss_bytes':usage.ru_maxrss*(1 if sys.platform=='darwin' else 1024),
                'voluntary_switches':usage.ru_nvcsw, 'involuntary_switches':usage.ru_nivcsw}
    finally:
        for signum, handler in previous.items(): signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics', required=True, type=pathlib.Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1]==['--'] else args.command
    if not command: parser.error('missing child command')
    result = measure(command)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.metrics.with_suffix('.tmp')
    temporary.write_text(json.dumps(result)+'\n'); temporary.replace(args.metrics)
    return result['returncode'] if result['returncode']>=0 else 128-result['returncode']


if __name__=='__main__': sys.exit(main())
