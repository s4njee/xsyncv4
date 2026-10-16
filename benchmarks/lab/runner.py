#!/usr/bin/env python3
"""Keep a driver host working through its queues, around the clock, unattended.

Runs detached on the driver and never finishes on its own. It hands one plan
at a time to that plan's agent.py and chooses the next from two lists under
ROOT/runs:

  backlog.txt      the backlog: experiments in the order they should run
  standing.txt   short sentinel runs, one of which is due every
                 `standing_every_s` whatever else is waiting

A run that has a status is never repeated, with one exception: a run that
failed or was interrupted before it took a single sample (a host was down,
say) is tried again, up to `retries` more times. Before a run starts, the
bytes it will write to each host's drive are charged against that host's
allowance for the last 24 hours (`write_budget` in control.json); a run that
does not fit is passed over until it does. `halt_after` failed runs in a row
halt the runner for `halt_cooldown_s`, then it tries again; a host that
stays down is retried hourly rather than burning the backlog.

A directory with job.json instead of plan.json is maintenance, such as
generating corpora: its steps run in order on their hosts, under the same
lock as experiments, and it is never retried.

On start, a run left with an unfinished status by a runner that died (a
reboot) is marked interrupted, or queued again if it took no samples.

Files that steer it, all under ROOT/runs:

  control.json   {"standing_every_s": N, "write_budget": {host: bytes}, "halt_after": N,
                  "halt_cooldown_s": N, "retries": N}
  .pause         while this exists no run is started
  .resume        clears a halt at once

SIGTERM stops the current run after its sample and exits. SIGUSR1 exits at
once and leaves the current run alone, so that a newer runner can take over:
it waits for that run to release the hosts. Nothing here needs the
controller to be awake.
"""
import argparse
import datetime
import fcntl
import json
import os
import shlex
import pathlib
import signal
import subprocess
import sys
import time

DAY_S = 86400
DEFAULTS = {'standing_every_s': 6 * 3600, 'write_budget': {}, 'halt_after': 3, 'halt_cooldown_s': 3600, 'retries': 3}
FINAL = ('complete', 'stopped', 'deadline', 'failed', 'refused', 'interrupted')
SSH = ['ssh', '-oBatchMode=yes', '-oConnectTimeout=10']


def utc(moment=None):
    moment = moment or datetime.datetime.now(datetime.timezone.utc)
    return moment.isoformat(timespec='seconds')


def read_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError):
        return default


def read_lines(path):
    try:
        return [line.strip() for line in pathlib.Path(path).read_text().splitlines() if line.strip()]
    except OSError:
        return []


def pending(runs, name):
    """Run ids in a list file that have a plan or a job and have not been run, in order."""
    return [run_id for run_id in read_lines(runs / name)
            if ((runs / run_id / 'plan.json').exists() or (runs / run_id / 'job.json').exists())
            and not (runs / run_id / 'status.json').exists()]


def samples_taken(directory):
    try:
        with open(directory / 'samples.jsonl') as stream:
            return sum(1 for line in stream if line.strip())
    except OSError:
        return 0


def attempts(directory):
    return len(list(directory.glob('status.attempt-*.json')))


def requeue(directory):
    """Set a run's status aside so that it runs again from the start."""
    (directory / 'status.json').replace(directory / f'status.attempt-{attempts(directory) + 1}.json')


def last_finished(runs, name):
    """Epoch seconds at which the most recent run of a list file last reported, or 0."""
    latest = 0.0
    for run_id in read_lines(runs / name):
        status = read_json(runs / run_id / 'status.json')
        if status and status.get('utc'):
            latest = max(latest, datetime.datetime.fromisoformat(status['utc']).timestamp())
    return latest


def written(runs, now):
    """Bytes charged to each host's drive in the 24 hours before `now`."""
    totals = {}
    for line in read_lines(runs / 'writes.jsonl'):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if now - DAY_S < entry.get('epoch', 0) <= now:
            for host, count in entry.get('bytes', {}).items():
                totals[host] = totals.get(host, 0) + count
    return totals


def fits(plan, used, budget):
    """Whether a plan's writes fit in what is left of each host's allowance.

    A plan larger than a whole day's allowance may run when nothing has been
    charged to that host in the last day, or it would never run at all.
    """
    for host, count in plan.get('writes', {}).items():
        allowance = budget.get(host)
        if allowance is not None and count and used.get(host, 0) and used.get(host, 0) + count > allowance:
            return False
    return True


def in_hours(plan, now):
    """Whether a plan's declared window of local hours includes `now` (epoch seconds)."""
    hours = plan.get('hours')
    if not hours:
        return True
    start, end = hours
    hour = time.localtime(now).tm_hour
    return start <= hour < end if start < end else hour >= start or hour < end


def choose(runs, control, now):
    """(run id, lane) of the next run to start, or (None, reason for waiting)."""
    used, budget = written(runs, now), control['write_budget']
    waiting_for_budget = False
    standing = pending(runs, 'standing.txt')
    if standing and now - last_finished(runs, 'standing.txt') >= control['standing_every_s']:
        if fits(read_json(runs / standing[0] / 'plan.json', {}), used, budget):
            return standing[0], 'standing'
        waiting_for_budget = True
    waiting_for_hours = False
    for run_id in pending(runs, 'backlog.txt'):
        plan = read_json(runs / run_id / 'plan.json', {})
        if not in_hours(plan, now):
            waiting_for_hours = True  # passed over until its window opens; later runs may go first
            continue
        if fits(plan, used, budget):
            return run_id, 'queue'
        waiting_for_budget = True
    return None, ('waiting for the write budget' if waiting_for_budget
                  else 'waiting for a run\'s hours' if waiting_for_hours else 'idle')


def agent_for(root, plan):
    """The agent a plan was made for: its own bundle's, or the unbundled one of older plans."""
    bundle = plan.get('bundle')
    return root / 'lib' / bundle / 'agent.py' if bundle else root / 'bin' / 'agent.py'


class Runner:
    def __init__(self, root, opens=None):
        self.root, self.runs, self.opens = root, root / 'runs', opens
        self.child, self.current, self.stopping, self.detached = None, None, False, False
        self.recent, self.failures, self.state, self.halted_at = [], 0, 'starting', None

    def control(self):
        return {**DEFAULTS, **(read_json(self.runs / 'control.json') or {})}

    def status(self, state, detail=None):
        self.state = state
        control = self.control()
        report = {'state': state, 'detail': detail, 'current': self.current, 'utc': utc(), 'pid': os.getpid(),
                  'runner': str(pathlib.Path(__file__).resolve()),
                  'queue_pending': len(pending(self.runs, 'backlog.txt')),
                  'standing_pending': len(pending(self.runs, 'standing.txt')),
                  'standing_every_s': control['standing_every_s'],
                  'standing_last_utc': utc(datetime.datetime.fromtimestamp(last, datetime.timezone.utc))
                  if (last := last_finished(self.runs, 'standing.txt')) else None,
                  'written_24h': written(self.runs, time.time()), 'write_budget': control['write_budget'],
                  'consecutive_failures': self.failures, 'recent': self.recent[-20:]}
        temporary = self.runs / 'runner-status.json.tmp'
        temporary.write_text(json.dumps(report, indent=1) + '\n')
        temporary.replace(self.runs / 'runner-status.json')

    def stop(self, *_):
        self.stopping = True
        if self.child and self.child.poll() is None:
            self.child.terminate()  # the agent finishes its current sample, restores the hosts and exits

    def detach(self, *_):
        self.detached = True

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline and not (self.stopping or self.detached):
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))

    def recover(self):
        """Settle runs that an earlier runner left unfinished, as after a reboot."""
        with open(self.runs / '.lock', 'a+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return  # a run is still going: it is not unfinished
            for name in ('backlog.txt', 'standing.txt'):
                for run_id in read_lines(self.runs / name):
                    directory = self.runs / run_id
                    status = read_json(directory / 'status.json')
                    if status is None or status.get('state') in FINAL:
                        continue
                    if samples_taken(directory) == 0 and attempts(directory) < self.control()['retries']:
                        requeue(directory)
                        self.recent.append({'run': run_id, 'state': 'requeued', 'detail': 'interrupted before a sample',
                                            'finished_utc': utc()})
                    else:
                        (directory / 'status.json').write_text(json.dumps(
                            {'state': 'interrupted', 'utc': utc(), 'detail': f'left {status.get("state")} by a runner '
                             f'that stopped; {samples_taken(directory)} samples kept'}) + '\n')

    def job(self, directory, log):
        """Run a maintenance job's steps in order. True if every step succeeded."""
        job = read_json(directory / 'job.json', {})
        for step in job.get('steps', []):
            argv = ['sh', '-c', step['command']] if step.get('local') else [*SSH, step['ssh'], 'sh -c ' + shlex.quote(step['command'])]
            log.write(f'[{utc()}] {step.get("host")}: {step["command"]}\n')
            log.flush()
            self.child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                          start_new_session=True)
            while self.child.poll() is None and not self.detached:
                if self.stopping:
                    self.child.terminate()
                time.sleep(0.5)
            if self.detached or self.child.returncode != 0:
                return False
        return True

    def run(self, run_id, lane):
        directory = self.runs / run_id
        plan = read_json(directory / 'plan.json', {})
        is_job = not plan and (directory / 'job.json').exists()
        # Another run, started by hand or left by an earlier runner, may hold the hosts.
        waited = False
        with open(self.runs / '.lock', 'a+') as lock:
            while not (self.stopping or self.detached):
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    waited = True
                    self.status('waiting for a running experiment', run_id)
                    self.wait(5)
        if self.stopping or self.detached or waited or (directory / 'status.json').exists():
            # After a wait, choose again: a sentinel may have come due, or it was this very run
            # that held the hosts, under a runner this one replaced.
            return
        with open(self.runs / 'writes.jsonl', 'a') as ledger:
            ledger.write(json.dumps({'epoch': time.time(), 'utc': utc(), 'run': run_id,
                                     'bytes': plan.get('writes', {})}) + '\n')
        self.current = {'run': run_id, 'lane': lane, 'started_utc': utc()}
        self.status('running')
        if is_job:
            with open(directory / 'job.log', 'a') as log:
                ok = self.job(directory, log)
            if self.detached:
                return
            result = {'state': 'complete' if ok else 'failed', 'utc': utc(),
                      'detail': 'every step succeeded' if ok else f'a step exited {self.child.returncode}'}
            (directory / 'status.json').write_text(json.dumps(result) + '\n')
            self.failures = 0 if ok else self.failures + 1
            self.recent.append({'run': run_id, 'lane': lane, 'state': result['state'], 'detail': result['detail'],
                                'finished_utc': utc()})
            self.current = self.child = None
            return
        with open(directory / 'agent.log', 'a') as log:
            # Its own session: stopping or replacing the runner must not signal the agent by accident.
            self.child = subprocess.Popen([sys.executable, str(agent_for(self.root, plan)), str(directory / 'plan.json')],
                                          stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                          cwd=directory, start_new_session=True)
            while self.child.poll() is None and not self.detached:
                time.sleep(0.2)
        if self.detached:
            return
        result = read_json(directory / 'status.json') or {}
        if result.get('state') not in FINAL:
            # The agent died before or during the run. Give the run a final status, or it would be started again.
            result = {'state': 'failed', 'utc': utc(), 'detail': f'the agent exited {self.child.returncode} '
                      + (f'while {result["state"]}' if result.get('state') else 'and left no status')}
            (directory / 'status.json').write_text(json.dumps(result) + '\n')
        failed = result.get('state') in ('failed', 'refused') or self.child.returncode != 0
        self.failures = self.failures + 1 if failed else 0
        retried = failed and samples_taken(directory) == 0 and attempts(directory) < self.control()['retries']
        if retried:
            requeue(directory)  # nothing was measured, so nothing is lost by starting it again
        self.recent.append({'run': run_id, 'lane': lane, 'state': result.get('state'), 'detail': result.get('detail'),
                            'exit': self.child.returncode, 'finished_utc': utc(), 'requeued': retried})
        self.current = self.child = None

    def loop(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGUSR1, self.detach)
        while self.opens and time.time() < self.opens and not (self.stopping or self.detached):
            self.status('waiting to begin', utc(datetime.datetime.fromtimestamp(self.opens, datetime.timezone.utc)))
            self.wait(min(30.0, max(0.0, self.opens - time.time())))
        self.recover()
        while not (self.stopping or self.detached):
            control = self.control()
            if (self.runs / '.resume').exists():
                (self.runs / '.resume').unlink()
                self.failures, self.halted_at = 0, None
            if self.failures >= control['halt_after']:
                self.halted_at = self.halted_at or time.time()
                if time.time() - self.halted_at >= control['halt_cooldown_s']:
                    # Unattended: try again after the cool-down. Another failure halts it again.
                    self.failures, self.halted_at = control['halt_after'] - 1, None
                    continue
                self.status('halted', f'{self.failures} runs failed in a row; trying again at '
                            + utc(datetime.datetime.fromtimestamp(self.halted_at + control['halt_cooldown_s'],
                                                                  datetime.timezone.utc)))
                self.wait(10)
            elif (self.runs / '.pause').exists():
                self.status('paused')
                self.wait(15)
            else:
                run_id, lane = choose(self.runs, control, time.time())
                if run_id:
                    self.run(run_id, lane)
                else:
                    self.status(lane)
                    self.wait(10)
        self.status('detached' if self.detached else 'stopped')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', required=True, type=pathlib.Path, help='the benchmark root on this host')
    parser.add_argument('--not-before', help='ISO-8601 time with offset before which nothing is started')
    args = parser.parse_args(argv)
    opens = None
    if args.not_before:
        moment = datetime.datetime.fromisoformat(args.not_before)
        if moment.tzinfo is None:
            parser.error('--not-before needs a UTC offset')
        opens = moment.timestamp()
    runs = args.root / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    single = open(runs / '.runner.lock', 'a+')
    for _ in range(60):  # a runner being replaced needs a moment to go
        try:
            fcntl.flock(single, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            time.sleep(1.0)
    else:
        sys.exit('another runner is working this root')
    Runner(args.root, opens).loop()


if __name__ == '__main__':
    main()
