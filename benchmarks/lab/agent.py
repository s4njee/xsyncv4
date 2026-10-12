#!/usr/bin/env python3
"""Execute a block plan and append one self-describing record per sample.

Runs detached on the driver host, with only the standard library. It reaches
the other endpoint over SSH, and runs every timed transfer under measure.py
on the host that acts as the SSH client, so neither the controller nor this
process is in the timed path. Records go to samples.jsonl and one line per
block attempt to blocks.jsonl, each flushed as it is written.
"""
import datetime
import fcntl
import json
import os
import pathlib
import re
import shlex
import signal
import socket
import subprocess
import sys
import time

SCHEMA = 1
HELPER = '/usr/local/sbin/xsbench-helper'
SSH = ('ssh', '-oBatchMode=yes', '-oConnectTimeout=10')
# What the transfer itself uses to reach the peer, as benchmarks/run.py does.
RSH = 'ssh -oBatchMode=yes -oCompression=no -oControlMaster=no -oConnectTimeout=10'
CLEAN_ENV = ('env', 'XSYNC_CONFIG=', 'XSYNC_OPTS=')
GATES = {'max_busy': 0.10, 'max_dirty_bytes': 16 << 20, 'max_temp_c': 70.0, 'settle_timeout_s': 120}
# vcgencmd get_throttled: bits 0-3 are current conditions, 16-19 "has occurred".
THROTTLE_NOW, THROTTLE_EVER = 0xF, 0xF0000


class Void(Exception):
    """A sample is unusable for a reason that does not depend on how long it took."""


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds')


class Host:
    """One endpoint: this machine, or a peer reached over SSH."""

    def __init__(self, name, spec, local):
        self.name, self.local = name, local
        self.ssh, self.root, self.interface = spec['ssh'], spec['root'], spec['interface']
        self.has_helper = spec.get('helper', False)
        self.gates = dict(GATES, **spec.get('gates', {}))

    def shell(self, script, check=True, timeout=None):
        argv = ['sh', '-c', script] if self.local else [*SSH, self.ssh, script]
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        if check and done.returncode:
            raise RuntimeError(f'{self.name}: `{script[:200]}` exited {done.returncode}: {done.stderr.strip()[-400:]}')
        return done

    def run(self, *argv, **options):
        return self.shell(shlex.join(map(str, argv)), **options)

    def bin(self, name):
        return f'{self.root}/bin/{name}'

    def probe(self, *arguments):
        return json.loads(self.run('python3', self.bin('probe.py'), *arguments, timeout=120).stdout)

    def snapshot(self):
        return self.probe('snapshot', '--interface', self.interface)

    def helper(self, *verb):
        if self.has_helper:
            self.run('sudo', '-n', HELPER, *verb, timeout=120)


def parse_stats(text):
    """The numbers of an rsync-style --stats report, keyed by their labels."""
    result = {}
    for line in text.splitlines():
        match = re.match(r'\s*([A-Za-z][A-Za-z ]+?):\s+([\d,.]+)', line)
        if match:
            value = match.group(2).replace(',', '').rstrip('.')
            result[match.group(1).strip().lower().replace(' ', '_')] = float(value) if '.' in value else int(value)
    return result


def busy_fraction(before, after):
    """Share of CPU time not idle between two /proc/stat `cpu` lines."""
    first, second = (list(map(int, line.split()[1:])) for line in (before, after))
    total = sum(second) - sum(first)
    idle = (second[3] + second[4]) - (first[3] + first[4])
    return 1.0 - idle / total if total > 0 else 0.0


def gate_problem(host, previous, current):
    """Why a host is not ready for a sample, or None."""
    gates, memory = host.gates, current.get('memory', {})
    if previous.get('cpu_jiffies') and current.get('cpu_jiffies'):
        busy = busy_fraction(previous['cpu_jiffies'][0], current['cpu_jiffies'][0])
        if busy > gates['max_busy']:
            return f'{host.name} is {busy:.0%} busy'
    dirty = memory.get('Dirty', 0) + memory.get('Writeback', 0)
    if dirty > gates['max_dirty_bytes']:
        return f'{host.name} has {dirty >> 20} MiB dirty'
    hottest = max(current.get('temp_millic', {}).values(), default=0) / 1000
    if hottest > gates['max_temp_c']:
        return f'{host.name} is at {hottest:.0f} C'
    if int(current.get('throttled', '0x0'), 16) & THROTTLE_NOW:
        return f'{host.name} is throttled ({current["throttled"]})'
    return None


def throttle_problem(host, before, after):
    """A throttle condition that arose during a sample, or None."""
    first, second = (int(state.get('throttled', '0x0'), 16) for state in (before, after))
    if second & THROTTLE_NOW or (second & THROTTLE_EVER) != (first & THROTTLE_EVER):
        return f'{host.name} throttled during the sample ({before.get("throttled")} -> {after.get("throttled")})'
    return None


def work_path(host, run_id, *parts):
    """A path under the host's owned work directory for this run; never anything else."""
    for part in (run_id, *parts):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', part):
            raise ValueError(f'unsafe path component {part!r}')
    return '/'.join((host.root, 'work', run_id, *parts))


def client_role(arm, cell):
    """Which end starts the transfer: the arm's choice if it makes one, else the cell's."""
    return arm.get('client') or cell['client']


def transfer_command(arm, cell, hosts, run_id, tag):
    """(client host, shell script) for one timed transfer, measured on both ends."""
    sender, receiver = hosts[cell['sender']], hosts[cell['receiver']]
    client = sender if client_role(arm, cell) == 'sender' else receiver
    peer = receiver if client is sender else sender
    source = f'{sender.root}/corpora/{cell["corpus"]}/'
    destination = work_path(receiver, run_id, cell['id'], arm['name']) + '/'
    program = arm['binary'][peer.name]
    peer_program = shlex.join(['python3', peer.bin('measure.py'), '--metrics',
                               work_path(peer, run_id, 'logs', f'{tag}.peer.json'), '--', program])
    fixed = ['--stats'] + (['--no-fallback', '--no-progress'] if arm['tool'] == 'xs' else [])
    remote = lambda path: f'{peer.ssh}:{path}'
    paths = [source, remote(destination)] if client is sender else [remote(source), destination]
    tool = [arm['binary'][client.name]]
    if delay := arm.get('delay_s', {}).get(cell['id']):
        # An injected, known slowdown, inside the measured region.
        tool = ['sh', '-c', 'sleep "$0"; exec "$@"', f'{delay:.4f}', *tool]
    # An arm may add options to the SSH client the transfer uses, such as a cipher.
    rsh = ' '.join([RSH, *map(shlex.quote, arm.get('ssh_options', []))])
    argv = [*CLEAN_ENV, 'python3', client.bin('measure.py'), '--metrics',
            work_path(client, run_id, 'logs', f'{tag}.client.json'), '--', *tool,
            *arm['flags'], *fixed, '-e', rsh, f'--rsync-path={peer_program}', *paths]
    log = work_path(client, run_id, 'logs', tag)
    return client, peer, argv, f'{shlex.join(argv)} > {shlex.quote(log + ".out")} 2> {shlex.quote(log + ".err")}'


class Run:
    def __init__(self, plan_path):
        self.directory = pathlib.Path(plan_path).resolve().parent
        self.plan = json.loads(pathlib.Path(plan_path).read_text())
        self.run_id = self.plan['run_id']
        self.hosts = {name: Host(name, spec, name == self.plan['driver']) for name, spec in self.plan['hosts'].items()}
        self.arms = {arm['name']: arm for arm in self.plan['arms']}
        self.cells = {cell['id']: cell for cell in self.plan['cells']}
        self.samples = open(self.directory / 'samples.jsonl', 'a', buffering=1)
        self.blocks = open(self.directory / 'blocks.jsonl', 'a', buffering=1)
        self.done = 0
        self.total = sum(len(block['orders'][0]) for block in self.plan['blocks'])
        self.seeded = set()
        self.stopping = False

    def status(self, state, detail=''):
        temporary = self.directory / 'status.json.tmp'
        temporary.write_text(json.dumps({'state': state, 'detail': detail, 'utc': utc(), 'pid': os.getpid(),
                                         'samples_done': self.done, 'samples_planned': self.total}) + '\n')
        temporary.replace(self.directory / 'status.json')

    def append(self, stream, record):
        stream.write(json.dumps(record, separators=(',', ':')) + '\n')
        os.fsync(stream.fileno())

    # -- once per run ------------------------------------------------------

    def prepare(self):
        """Refuse to start unless every host holds what the plan names."""
        self.status('preparing')
        for host in self.hosts.values():
            names = sorted({pathlib.PurePosixPath(arm['binary'][host.name]).name for arm in self.arms.values()
                            if arm['tool'] == 'xs'} | set(self.plan['scripts']))
            report = host.probe('staged', '--root', host.root, *names)
            for arm in self.arms.values():
                name = pathlib.PurePosixPath(arm['binary'][host.name]).name
                if arm['tool'] == 'xs' and report['files'].get(name) != arm['sha256'][host.name]:
                    raise RuntimeError(f'{host.name}: {name} is not the recorded build')
            for name, digest in self.plan['scripts'].items():
                if report['files'].get(name) != digest:
                    raise RuntimeError(f'{host.name}: {name} differs from the planned copy')
            arm_rsync = report.get('rsync', {})
            self.plan.setdefault('observed', {})[host.name] = {'rsync': arm_rsync, 'hostname': report['hostname']}
            if host.has_helper:
                state = dict(line.split('=', 1) for line in
                             host.run('sudo', '-n', HELPER, 'status').stdout.splitlines() if '=' in line)
                if state.get('netem') != 'off' or state.get('netem_timer') != 'off':
                    raise RuntimeError(f'{host.name}: a netem qdisc is active')
                # Exit 3 means this host has no scratch mount configured, which is fine.
                trimmed = None
                for verb in ('mount-scratch', 'trim-scratch'):
                    done = host.run('sudo', '-n', HELPER, verb, check=False, timeout=3600)
                    if done.returncode not in (0, 3):
                        raise RuntimeError(f'{host.name}: {verb}: {done.stderr.strip()}')
                    trimmed = done.stdout.strip() if verb == 'trim-scratch' and done.returncode == 0 else trimmed
                self.plan['observed'][host.name]['trim'] = trimmed
            host.run('mkdir', '-p', work_path(host, self.run_id, 'logs'))
        for name, corpus in self.plan['corpora'].items():
            for sender in sorted({cell['sender'] for cell in self.cells.values() if cell['corpus'] == name}):
                host = self.hosts[sender]
                manifest = f'{host.root}/corpora/{name}.manifest.json'
                found = json.loads(host.run('python3', host.bin('corpus.py'), 'verify', f'{host.root}/corpora/{name}',
                                            '--manifest', manifest, '--quick', timeout=1800).stdout)
                if found['digest'] != corpus['digest']:
                    raise RuntimeError(f'{sender}: corpus {name} is not the pinned one')
        if any(observed.get('trim') for observed in self.plan['observed'].values()):
            time.sleep(15)  # a drive works through a large trim for a few seconds afterwards
        for host in self.hosts.values():
            host.helper('governor', 'performance')
        (self.directory / 'run.json').write_text(json.dumps(
            {'schema': SCHEMA, 'run_id': self.run_id, 'started_utc': utc(), 'driver': socket.gethostname(),
             'plan': self.plan}, indent=1) + '\n')

    def finish(self):
        for host in self.hosts.values():
            try:
                host.helper('governor', 'restore')
                host.run('rm', '-rf', '--', work_path(host, self.run_id), check=False, timeout=600)
            except Exception as error:  # every host gets its turn
                print(f'cleanup on {host.name}: {error}', flush=True)

    # -- once per sample ---------------------------------------------------

    def prepare_destination(self, cell, arm, destination):
        receiver, sender = self.hosts[cell['receiver']], self.hosts[cell['sender']]
        if cell['scenario'] == 'fresh':
            receiver.run('rm', '-rf', '--', destination, timeout=1800)
            receiver.run('mkdir', '-p', os.path.dirname(destination))
        elif (cell['id'], arm['name']) not in self.seeded:
            # noop: an identical destination, made once and left unchanged by every sample
            receiver.run('rm', '-rf', '--', destination, timeout=1800)
            receiver.run('mkdir', '-p', destination)
            sender.shell(f'rsync -aH -e {shlex.quote(RSH)} {shlex.quote(sender.root + "/corpora/" + cell["corpus"] + "/")} '
                         f'{shlex.quote(receiver.ssh + ":" + destination + "/")}', timeout=7200)
            self.seeded.add((cell['id'], arm['name']))

    def apply_cache(self, cell, destination):
        sender, receiver = self.hosts[cell['sender']], self.hosts[cell['receiver']]
        if cell['cache'] == 'cold':
            for host in (sender, receiver):
                host.helper('drop-caches')
            return
        source = shlex.quote(f'{sender.root}/corpora/{cell["corpus"]}')
        sender.shell(f'find {source} -type f -exec cat {{}} + > /dev/null', timeout=3600)
        if cell['scenario'] != 'fresh':
            receiver.shell(f'find {shlex.quote(destination)} -type f -size +0 > /dev/null', timeout=3600)

    def settle(self, cell, destination):
        """Flush the destination filesystem, then wait until both hosts are quiet. Returns their states."""
        sender, receiver = self.hosts[cell['sender']], self.hosts[cell['receiver']]
        receiver.run('sync', '-f', os.path.dirname(destination), timeout=1800)
        started = time.monotonic()
        previous = {host.name: host.snapshot() for host in (sender, receiver)}
        while True:
            time.sleep(1.0)
            current = {host.name: host.snapshot() for host in (sender, receiver)}
            problems = [problem for host in (sender, receiver)
                        if (problem := gate_problem(host, previous[host.name], current[host.name]))]
            waited = time.monotonic() - started
            if not problems:
                return current, waited
            if waited > min(sender.gates['settle_timeout_s'], receiver.gates['settle_timeout_s']):
                raise Void('did not settle: ' + '; '.join(problems))
            previous = current

    def sample(self, cell, arm, block, attempt, position, previous_arm, verify_full):
        sender, receiver = self.hosts[cell['sender']], self.hosts[cell['receiver']]
        tag = f'{cell["id"]}.b{block}.a{attempt}.{arm["name"]}'
        destination = work_path(receiver, self.run_id, cell['id'], arm['name'])
        record = {'schema': SCHEMA, 'experiment': self.plan['experiment'], 'spec_sha256': self.plan['spec_sha256'],
                  'run_id': self.run_id, 'seed': self.plan['seed'], 'kind': self.plan['kind'],
                  'cell_id': cell['id'], 'cell': {key: cell[key] for key in
                                                  ('corpus', 'scenario', 'sender', 'receiver', 'client', 'link',
                                                   'cache')},
                  'block': block, 'attempt': attempt, 'position': position, 'arm': arm['name'],
                  'previous_arm': previous_arm, 'control': arm['name'] == self.plan['control'],
                  'tool': arm['tool'], 'rev': arm.get('rev'), 'flags': arm['flags'],
                  'injected_delay_s': arm.get('delay_s', {}).get(cell['id']),
                  'client_role': client_role(arm, cell), 'ssh_options': arm.get('ssh_options', []),
                  'corpus_files': self.plan['corpora'][cell['corpus']]['files'],
                  'corpus_bytes': self.plan['corpora'][cell['corpus']]['bytes'],
                  'valid': False, 'void_reason': None}
        try:
            self.prepare_destination(cell, arm, destination)
            self.apply_cache(cell, destination)
            before, record['settle_s'] = self.settle(cell, destination)
            client, peer, argv, script = transfer_command(arm, cell, self.hosts, self.run_id, tag)
            record.update(client_host=client.name, peer_host=peer.name, argv=argv, utc_start=utc())
            exit_status = client.shell(script, check=False, timeout=self.plan['sample_timeout_s']).returncode
            record['utc_end'] = utc()
            sync = receiver.run('python3', '-c', 'import subprocess,sys,time; s=time.perf_counter(); '
                                'subprocess.run(["sync","-f",sys.argv[1]],check=True); print(time.perf_counter()-s)',
                                destination, check=False, timeout=1800)  # a failed transfer may leave nothing to sync
            after = {host.name: host.snapshot() for host in (sender, receiver)}
            record['host_state'] = {name: {'before': before[name], 'after': after[name]} for name in before}
            log = work_path(client, self.run_id, 'logs', tag)
            output = client.shell(f'cat {shlex.quote(log + ".out")}; printf "\\036"; tail -c 2000 {shlex.quote(log + ".err")}',
                                  check=False).stdout
            record['stdout'], _, record['stderr'] = output.partition('\x1e')
            record['stats'] = parse_stats(record['stdout'])
            for role, host in (('client', client), ('peer', peer)):
                metrics = host.run('cat', work_path(host, self.run_id, 'logs', f'{tag}.{role}.json'), check=False)
                record[role] = json.loads(metrics.stdout) if metrics.returncode == 0 and metrics.stdout else None
            if exit_status or not record['client'] or record['client']['returncode']:
                raise Void(f'the transfer exited {exit_status}: {record["stderr"].strip()[-300:]}')
            if not record['peer'] or record['peer']['returncode']:
                raise Void('the peer process failed or left no metrics')
            if sync.returncode:
                raise Void('could not sync the destination filesystem: ' + sync.stderr.strip()[-200:])
            record['wall_s'] = record['client']['wall_seconds']
            record['sync_s'] = float(sync.stdout)
            record['durable_s'] = record['wall_s'] + record['sync_s']
            counters = lambda name, key: (after[name].get('counters', {}).get(key) or 0) - \
                                         (before[name].get('counters', {}).get(key) or 0)
            record['wire'] = {'sender_tx_bytes': counters(sender.name, 'tx_bytes'),
                              'receiver_rx_bytes': counters(receiver.name, 'rx_bytes'),
                              'sender_retransmits': after[sender.name].get('tcp', {}).get('RetransSegs', 0)
                              - before[sender.name].get('tcp', {}).get('RetransSegs', 0)}
            quick = cell['scenario'] != 'fresh' or not verify_full
            manifest = f'{receiver.root}/corpora/{cell["corpus"]}.manifest.json'
            checked = receiver.run('python3', receiver.bin('corpus.py'), 'verify', destination, '--manifest', manifest,
                                   *(['--quick'] if quick else []), check=False, timeout=7200)
            record['verify'] = {'mode': 'quick' if quick else 'full', 'ok': checked.returncode == 0}
            if checked.returncode:
                raise Void('the destination does not match the corpus manifest: ' + checked.stdout.strip()[:300])
            for host in (sender, receiver):
                if problem := throttle_problem(host, before[host.name], after[host.name]):
                    raise Void(problem)
            record['valid'] = True
        except Void as void:
            record['void_reason'] = str(void)
        except (RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
            record['void_reason'] = f'harness error: {error}'
        self.append(self.samples, record)
        self.done += 1
        return record

    def link_probe(self, cell):
        """Round-trip statistics and the interface used, from the sender's side."""
        sender, receiver = self.hosts[cell['sender']], self.hosts[cell['receiver']]
        report = sender.probe('route', '--peer', self.plan['hosts'][receiver.name]['name'], '--pings', '10')
        limit = self.plan['links'][cell['link']].get('max_rtt_ms')
        if report.get('dev') != sender.interface:
            raise Void(f'{sender.name} reaches {receiver.name} by {report.get("dev")}, not {sender.interface}')
        if 'rtt_avg_ms' not in report.get('ping', {}):
            raise Void(f'{receiver.name} does not answer ping')
        if limit and report['ping']['rtt_avg_ms'] > limit:
            raise Void(f'round trip is {report["ping"]["rtt_avg_ms"]} ms, above {limit}')
        return report

    def block(self, entry):
        cell = self.cells[entry['cell']]
        for attempt, order in enumerate(entry['orders']):
            summary = {'schema': SCHEMA, 'run_id': self.run_id, 'cell_id': cell['id'], 'block': entry['block'],
                       'attempt': attempt, 'order': order, 'utc': utc(), 'valid': False, 'void_reason': None}
            try:
                summary['link'] = self.link_probe(cell)
                previous = None
                for position, name in enumerate(order):
                    self.status('running', f'{cell["id"]} block {entry["block"]} attempt {attempt} {name}')
                    record = self.sample(cell, self.arms[name], entry['block'], attempt, position, previous,
                                         entry['verify_full'])
                    if not record['valid']:
                        raise Void(f'{name}: {record["void_reason"]}')
                    previous = name
                    if self.stopping:
                        raise Void('stopped')
                summary['valid'] = True
            except Void as void:
                summary['void_reason'] = str(void)
            self.append(self.blocks, summary)
            if summary['valid'] or self.stopping:
                return summary['valid']
        return False

    def execute(self, deadline=None):
        """Run the plan. With a deadline (epoch seconds), start no block that might run past it."""
        lock = open(pathlib.Path(self.plan['hosts'][self.plan['driver']]['root']) / 'runs' / '.lock', 'a+')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.status('refused', 'another run holds the lock')
            return 1
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, 'stopping', True))
        valid, attempted, longest, expired = 0, 0, 180.0, False
        try:
            self.prepare()
            for entry in self.plan['blocks']:
                if self.stopping:
                    break
                if deadline and time.time() + longest > deadline:
                    expired = True
                    break
                started = time.monotonic()
                valid += self.block(entry)
                attempted += 1
                longest = max(longest, time.monotonic() - started)
        except Exception as error:
            self.finish()
            self.status('failed', f'{type(error).__name__}: {error}')
            raise
        self.finish()
        state = 'stopped' if self.stopping else 'deadline' if expired else 'complete'
        self.status(state, f'{valid} of {attempted} blocks valid, {len(self.plan["blocks"])} planned')
        return 0


if __name__ == '__main__':
    if len(sys.argv) not in (2, 4) or (len(sys.argv) == 4 and sys.argv[2] != '--deadline'):
        sys.exit('usage: agent.py RUN_DIRECTORY/plan.json [--deadline ISO-8601]')
    limit = datetime.datetime.fromisoformat(sys.argv[3]).timestamp() if len(sys.argv) == 4 else None
    sys.exit(Run(sys.argv[1]).execute(limit))
