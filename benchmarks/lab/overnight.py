#!/usr/bin/env python3
"""Run queued plans one after another inside a time window, unattended.

Runs detached on the driver host. It waits until the window opens, then
hands each run in ROOT/runs/queue.txt to agent.py in turn, giving the agent
the window's end as its deadline so no block starts that could run past it.
A run that already has a status is never repeated, a run that fails does not
stop the queue, and nothing here needs the controller to be awake.
"""
import argparse
import datetime
import fcntl
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

RESERVE_S = 300  # do not start a run with less than this left in the window


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=pathlib.Path, help='the benchmark root on this host')
    parser.add_argument('--not-before', required=True, help='ISO-8601 time the window opens')
    parser.add_argument('--deadline', required=True, help='ISO-8601 time the window closes')
    parser.add_argument('--agent', type=pathlib.Path, help='agent to run (default ROOT/bin/agent.py)')
    args = parser.parse_args(argv)
    opens, closes = (datetime.datetime.fromisoformat(value) for value in (args.not_before, args.deadline))
    if opens.tzinfo is None or closes.tzinfo is None or closes <= opens:
        parser.error('the window needs two times with UTC offsets, the second after the first')
    runs = args.root / 'runs'
    agent = args.agent or args.root / 'bin' / 'agent.py'
    finished, child, stopping = [], None, []

    def status(state, current=None):
        temporary = runs / 'queue-status.json.tmp'
        temporary.write_text(json.dumps({'state': state, 'current': current, 'utc': now().isoformat(timespec='seconds'),
                                         'pid': os.getpid(), 'window': [args.not_before, args.deadline],
                                         'runs': finished}, indent=1) + '\n')
        temporary.replace(runs / 'queue-status.json')

    def stop(*_):
        stopping.append(True)
        if child and child.poll() is None:
            child.terminate()  # the agent finishes its current sample, restores the hosts and exits

    signal.signal(signal.SIGTERM, stop)
    while now() < opens and not stopping:
        status('waiting for the window')
        time.sleep(min(30.0, max(0.0, (opens - now()).total_seconds())))
    queue = [line.strip() for line in (runs / 'queue.txt').read_text().splitlines() if line.strip()]
    for run_id in queue:
        directory = runs / run_id
        if stopping:
            break
        if not (directory / 'plan.json').exists():
            finished.append({'run': run_id, 'state': 'skipped', 'detail': 'no plan'})
            continue
        if (directory / 'status.json').exists():
            finished.append({'run': run_id, 'state': 'skipped', 'detail': 'already run'})
            continue
        # Another run may still hold the hosts; wait for it rather than fail.
        with open(runs / '.lock', 'a+') as lock:
            while not stopping and (closes - now()).total_seconds() > RESERVE_S:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    status('waiting for a running experiment', run_id)
                    time.sleep(15.0)
        if stopping:
            break
        if (closes - now()).total_seconds() <= RESERVE_S:
            finished.append({'run': run_id, 'state': 'skipped', 'detail': 'the window closed first'})
            continue
        status('running', run_id)
        with open(directory / 'agent.log', 'a') as log:
            child = subprocess.Popen([sys.executable, str(agent), str(directory / 'plan.json'), '--deadline',
                                      closes.isoformat()], stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, cwd=directory)
            code = child.wait()
        try:
            result = json.loads((directory / 'status.json').read_text())
        except (OSError, ValueError):
            result = {'state': 'failed', 'detail': 'the agent left no status'}
        finished.append({'run': run_id, 'state': result.get('state'), 'detail': result.get('detail'), 'exit': code})
    status('stopped' if stopping else 'finished')


if __name__ == '__main__':
    main()
