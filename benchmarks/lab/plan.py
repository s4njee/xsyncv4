#!/usr/bin/env python3
"""Turn an experiment spec into a randomized block plan, and run it on the driver host.

A spec (benchmarks/experiments/*.toml) names arms, cells and a block budget.
`make` expands it into explicit blocks: every arm once per block, in an order
drawn from the seed, with the cells interleaved.

A driver host works around the clock under runner.py. `enqueue` adds a spec
to its backlog, `standing` gives it sentinel runs to repeat at an interval,
`runner` starts, pauses and steers it, `queue` shows what it is doing and
`collect` brings finished runs back. `start` runs one spec at once, outside
the queue, for a link the runner does not own; `status`, `fetch` and `stop`
follow a single run.
"""
import argparse
import datetime
import hashlib
import itertools
import json
import pathlib
import re
import shlex
import subprocess
import sys
import tomllib

import corpus
import preflight
import stage

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE.parent / 'results' / 'lab'  # path experiments; a link may name another folder
SCENARIOS = ('fresh', 'noop')
SAFE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
RETRIES = 2  # extra attempts at a block that was voided
TUNE_VALUE = re.compile(r'[a-z0-9_]+=[0-9]+(,[a-z0-9_]+=[0-9]+)*')  # safe unquoted in a remote command


class SpecError(ValueError):
    pass


def load_spec(path):
    text = pathlib.Path(path).read_bytes()
    spec = tomllib.loads(text.decode())
    spec['sha256'] = hashlib.sha256(text).hexdigest()
    for key in ('id', 'hypothesis', 'kind', 'primary', 'control', 'blocks', 'arms', 'matrix'):
        if key not in spec:
            raise SpecError(f'the spec needs `{key}`')
    if not SAFE.fullmatch(spec['id']) or spec['kind'] not in ('screening', 'confirmatory'):
        raise SpecError('`id` must be a plain name and `kind` screening or confirmatory')
    if spec['control'] not in spec['arms'] or len(spec['arms']) < 2:
        raise SpecError('`control` must name one of at least two arms')
    if len(spec['arms']) > 6:
        raise SpecError('at most six arms fit in a block')
    for name, arm in spec['arms'].items():
        if not SAFE.fullmatch(name) or arm.get('tool') not in ('xs', 'rsync'):
            raise SpecError(f'arm {name}: needs a plain name and tool xs or rsync')
        if arm['tool'] == 'xs' and not arm.get('rev'):
            raise SpecError(f'arm {name}: an xs arm names the commit it runs')
    if not isinstance(spec['blocks'], int) or spec['blocks'] < 1:
        raise SpecError('`blocks` must be a positive integer')
    return spec


def cells_of(spec, config):
    """Every cell of the spec's matrix, checked against the declared hosts and links."""
    matrix = spec['matrix']
    link = config['links'].get(matrix.get('link'))
    if not link:
        raise SpecError('`matrix.link` must name a link in hosts.toml')
    cells = []
    for name, scenario, direction, client, cache in itertools.product(
            matrix['corpus'], matrix['scenario'], matrix['direction'], matrix.get('client', ['sender']),
            matrix.get('cache', ['warm'])):
        sender, _, receiver = direction.partition('>')
        if {sender, receiver} != set(link['hosts']):
            raise SpecError(f'direction {direction} is not between the hosts of link {matrix["link"]}')
        if scenario not in SCENARIOS or client not in ('sender', 'receiver', 'arm', 'initiator') \
                or cache not in ('warm', 'cold'):
            raise SpecError(f'unsupported scenario, client or cache in {scenario}/{client}/{cache}')
        # On a link only one host can start connections from, that host is the client either way.
        initiator = link.get('initiator')
        if client == 'initiator':
            if not initiator:
                raise SpecError(f'link {matrix["link"]} declares no initiator')
            client = 'sender' if sender == initiator else 'receiver'
        elif initiator and (client == 'arm' or (sender if client == 'sender' else receiver) != initiator):
            raise SpecError(f'on link {matrix["link"]} only {initiator} can be the SSH client: use client = ["initiator"]')
        cells.append({'id': f'{name}.{scenario}.{sender}-{receiver}.{client}.{cache}', 'corpus': name,
                      'scenario': scenario, 'sender': sender, 'receiver': receiver, 'client': client,
                      'link': matrix['link'], 'cache': cache})
    return cells


def shuffled(items, stream):
    """A Fisher-Yates shuffle driven by a deterministic stream."""
    items = list(items)
    for last in range(len(items) - 1, 0, -1):
        other = stream.below(last + 1)
        items[last], items[other] = items[other], items[last]
    return items


def make_plan(spec, config, pins, seed, run_id, baseline=None):
    """The complete, self-contained instructions for one run."""
    cells = cells_of(spec, config)
    link = config['links'][spec['matrix']['link']]
    hosts = {}
    for name in link['hosts']:
        host = config['hosts'][name]
        if not host.get('root') or not link.get('interface', {}).get(name):
            raise SpecError(f'{name} needs a root and an interface on the link in hosts.toml')
        hosts[name] = {key: host[key] for key in ('ssh', 'name', 'hostname', 'root') if key in host}
        hosts[name].update(interface=link['interface'][name], helper=host.get('helper', False),
                           gates=host.get('gates', {}), local=host.get('local', False))
    driver = spec.get('driver') or link.get('driver') or config.get('driver') or link['hosts'][0]
    if driver not in hosts:
        raise SpecError(f'the driver {driver} is not on the link')
    arms = []
    for name, arm in spec['arms'].items():
        entry = {'name': name, 'tool': arm['tool'], 'flags': list(arm.get('flags', ['-a']))}
        if options := arm.get('ssh_options'):
            if not isinstance(options, list) or not all(isinstance(option, str) for option in options):
                raise SpecError(f'arm {name}: `ssh_options` must be a list of strings')
            entry['ssh_options'] = options
        if arm.get('client') in ('sender', 'receiver'):
            entry['client'] = arm['client']  # this arm chooses which end starts the transfer
        elif 'client' in arm or any(cell['client'] == 'arm' for cell in cells):
            raise SpecError(f'arm {name}: `client` must be sender or receiver when the matrix leaves it to the arms')
        if fraction := arm.get('inject_fraction'):
            # A known slowdown: sleep this share of the control's usual time before the tool starts.
            missing = [cell['id'] for cell in cells if cell['id'] not in (baseline or {})]
            if missing:
                raise SpecError(f'arm {name}: no baseline time for {", ".join(missing)}')
            entry['inject_fraction'] = fraction
            entry['delay_s'] = {cell['id']: fraction * baseline[cell['id']] for cell in cells}
        if arm['tool'] == 'xs':
            build = stage.load_build(arm['rev'])
            entry['rev'] = build['rev12']
            # Engine constants for each end, and the engine's own counters: tunables builds only.
            tune = arm.get('tune', {})
            if isinstance(tune, str):
                tune = {'sender': tune, 'receiver': tune}
            if not isinstance(tune, dict) or set(tune) - {'sender', 'receiver'} or \
                    not all(isinstance(value, str) and TUNE_VALUE.fullmatch(value) for value in tune.values()):
                raise SpecError(f'arm {name}: `tune` is "key=value,..." or a table of that for sender and receiver')
            if (tune or arm.get('metrics')) and not build.get('tunables'):
                raise SpecError(f'arm {name}: `tune` and `metrics` need a tunables build (rev = "{arm["rev"]}-tune")')
            if tune:
                entry['tune'] = tune
            if arm.get('metrics'):
                entry['metrics'] = True
            entry['binary'] = {host: f'{hosts[host]["root"]}/bin/xs-{build["rev12"]}' for host in hosts}
            entry['sha256'] = {}  # filled per host architecture by `start`
            entry['artifacts'] = {name: artifact['sha256'] for name, artifact in build['artifacts'].items()}
        else:
            entry['binary'] = {host: 'rsync' for host in hosts}
        arms.append(entry)
    corpora = {}
    for name in spec['matrix']['corpus']:
        pin = pins.get(f'{name}:full') or pins.get(f'{name}:real')
        if not pin:
            raise SpecError(f'corpus {name} is not pinned in corpora.json')
        corpora[name] = {key: pin[key] for key in ('files', 'directories', 'bytes', 'digest', 'quick_digest')}
    stream = corpus.Stream('plan', spec['id'], seed)
    names = [arm['name'] for arm in arms]
    blocks = []
    for number in range(spec['blocks']):
        # Cells are interleaved: one block of each, in a fresh order, before the next round.
        for cell in shuffled(cells, stream):
            full = spec.get('verify', 'full') == 'full' or number in (0, spec['blocks'] - 1)
            blocks.append({'cell': cell['id'], 'block': number, 'verify_full': full,
                           'orders': [shuffled(names, stream) for _ in range(1 + RETRIES)]})
    # Bytes each host's drive will take: every fresh sample rewrites its corpus on the receiver, and
    # an unchanged destination is made once for each arm of a no-op cell.
    writes, by_id = {name: 0 for name in hosts}, {cell['id']: cell for cell in cells}
    for block in blocks:
        cell = by_id[block['cell']]
        if cell['scenario'] == 'fresh':
            writes[cell['receiver']] += corpora[cell['corpus']]['bytes'] * len(arms)
    for cell in cells:
        if cell['scenario'] != 'fresh':
            writes[cell['receiver']] += corpora[cell['corpus']]['bytes'] * len(arms)
    return {'schema': 1, 'experiment': spec['id'], 'spec_sha256': spec['sha256'], 'kind': spec['kind'],
            'bundle': stage.bundle_id(), 'writes': writes,
            'hypothesis': spec['hypothesis'], 'primary': spec['primary'], 'delta': spec.get('delta'),
            'control': spec['control'], 'seed': seed, 'run_id': run_id, 'driver': driver,
            'sample_timeout_s': spec.get('sample_timeout_s', 3600),
            'results': link.get('results', 'lab'), 'background': bool(link.get('background')),
            'eager_cleanup': spec.get('cleanup') == 'eager', 'hours': hours_of(spec),
            'hosts': hosts, 'links': {spec['matrix']['link']: {key: link[key] for key in link if key != 'interface'}},
            'arms': arms, 'cells': cells, 'corpora': corpora, 'blocks': blocks,
            'scripts': {path.name: stage.sha256(path) for path in stage.SCRIPTS}}


def hours_of(spec):
    """[start, end) local hours on the driver in which the runner may start this plan, or None for any time.

    A window may wrap midnight: [22, 7] is ten at night to seven in the morning.
    """
    hours = spec.get('hours')
    if hours is None:
        return None
    if not (isinstance(hours, list) and len(hours) == 2 and all(isinstance(h, int) and 0 <= h <= 24 for h in hours)
            and hours[0] != hours[1]):
        raise SpecError('`hours` is [start, end], whole local hours on the driver, e.g. [22, 7]')
    return hours


def load_baseline(spec):
    """Per-cell geometric mean time of an arm in an analysed experiment, for injected slowdowns."""
    source = spec.get('baseline')
    if not source:
        return None
    path = RESULTS / source['experiment'] / 'analysis' / 'absolutes.json'
    if not path.exists():
        raise SpecError(f'baseline {source["experiment"]} has not been analysed')
    return {row['cell_id']: row['geomean'] for row in json.loads(path.read_text())
            if row['arm'] == source['arm'] and row['metric'] == spec['primary']}


def new_run_id(spec, suffix=''):
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + spec['id'] + suffix


def driver_of(plan):
    return plan['hosts'][plan['driver']]


def remote(host, script, **options):
    """Run a shell command on a plan's host: directly if it is this machine, else over SSH."""
    command = ['sh', '-c', script] if host.get('local') else [*preflight.SSH, host['ssh'], 'sh -c ' + shlex.quote(script)]
    return subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL, **options)


def preflight_or_exit(link, revisions, expected=()):
    """Run preflight; exit on any problem other than those containing an `expected` phrase."""
    for revision in revisions or [None]:
        arguments = ['--link', link] + (['--rev', revision] if revision else [])
        done = subprocess.run([sys.executable, str(HERE / 'preflight.py'), *arguments], capture_output=True, text=True)
        problems = [line for line in done.stdout.splitlines() if line.startswith('PROBLEM')
                    and not any(phrase in line for phrase in expected)]
        if done.returncode and (problems or 'PROBLEM' not in done.stdout):
            raise SystemExit('preflight failed:\n' + done.stdout + done.stderr)


def run_in_progress(driver):
    """Whether an agent holds the driver's lock right now."""
    test = ('import fcntl,sys\ntry:\n fcntl.flock(open(sys.argv[1],"a+"),fcntl.LOCK_EX|fcntl.LOCK_NB)\n'
            'except BlockingIOError:\n sys.exit(1)')
    return remote(driver, f'python3 -c {shlex.quote(test)} {shlex.quote(driver["root"] + "/runs/.lock")}',
                  timeout=60).returncode == 1


def prepare_run(spec_path, config, seed, suffix=''):
    """Make a plan, keep it locally and put it on the driver. Returns (plan, remote directory)."""
    spec = load_spec(spec_path)
    pins = json.loads((HERE / 'corpora.json').read_text())
    plan = make_plan(spec, config, pins, seed, new_run_id(spec, suffix), load_baseline(spec))
    for name, host in plan['hosts'].items():
        stage.push_bundle(name, host)  # the scripts this plan was made with, if the host lacks them
        host['system'], machine = remote(host, 'uname -s; uname -m', timeout=30).stdout.split()
        artifact = stage.artifact_for(host['system'], machine)
        for arm in plan['arms']:
            if arm['tool'] == 'xs':
                if artifact not in arm['artifacts']:
                    raise SystemExit(f'{name}: {arm["rev"]} has no {artifact}; run stage.py build --rev {arm["rev"]}')
                arm['sha256'][name] = arm['artifacts'][artifact]
    driver = driver_of(plan)
    directory = f'{driver["root"]}/runs/{plan["run_id"]}'
    local = HERE.parent / 'results' / plan['results'] / spec['id'] / plan['run_id']
    while local.exists():  # two runs of a spec queued within one second
        plan['run_id'] = new_run_id(spec, f'{suffix}-{seed}-{len(list(local.parent.glob(plan["run_id"] + "*")))}')
        local = local.parent / plan['run_id']
    local.mkdir(parents=True)
    (local / 'plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    (local / 'spec.toml').write_bytes(pathlib.Path(spec_path).read_bytes())
    remote(driver, f'mkdir -p {shlex.quote(directory)}', check=True)
    stage.copy_to(driver, [local / 'plan.json'], directory)
    return plan, directory


def revisions_of(plan):
    return sorted({arm['rev'] for arm in plan['arms'] if arm['tool'] == 'xs'})


def start(spec_path, config, seed, skip_preflight):
    spec = load_spec(spec_path)
    link = config['links'][spec['matrix']['link']]
    for name in link['hosts']:
        stage.push_bundle(name, config['hosts'][name])  # preflight looks for the scripts in their bundle
    if not skip_preflight:
        preflight_or_exit(spec['matrix']['link'], sorted({stage.build_id(arm['rev']) for arm in spec['arms'].values()
                                                           if arm['tool'] == 'xs'}))
    plan, directory = prepare_run(spec_path, config, seed)
    driver = driver_of(plan)
    detach(driver, directory, [f'{driver["root"]}/lib/{plan["bundle"]}/agent.py', 'plan.json'], 'agent.log')
    return plan


def detach(host, directory, argv, log):
    """Start a Python script on a host, detached from this session, with its output in a log there."""
    if host.get('local'):
        # This machine: its own session, and kept awake while the script lives.
        with open(pathlib.Path(directory) / log, 'a') as stream:
            subprocess.Popen(['caffeinate', '-i', sys.executable, *argv], cwd=directory, stdout=stream,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        return
    # The backgrounded command must be the script alone, with every descriptor redirected, or SSH waits for it.
    launch = (f'cd {shlex.quote(directory)} || exit 1; setsid nohup python3 {shlex.join(argv)} '
              f'> {shlex.quote(log)} 2>&1 < /dev/null & echo started')
    remote(host, launch, check=True, timeout=60)


# -- the driver's queues -----------------------------------------------------

def driver_named(config, name=None):
    name = name or config.get('driver') or next(iter(config['hosts']))
    if name not in config['hosts'] or not config['hosts'][name].get('root'):
        raise SystemExit(f'{name} is not a host with a benchmark root')
    return config['hosts'][name]


def listed_runs(driver, name='backlog.txt'):
    """Run ids in one of the driver's list files, in order."""
    done = remote(driver, f'cat {shlex.quote(driver["root"] + "/runs/" + name)} 2>/dev/null', timeout=60)
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def staged_or_exit(plan, config):
    """Every host of a plan must hold the builds it names; the scripts were put there with the plan."""
    for revision in revisions_of(plan):
        _, problems = stage.check(config, list(plan['hosts']), stage.load_build(revision))
        if problems:
            raise SystemExit('not staged:\n' + '\n'.join(problems) + f'\nrun stage.py push --rev {revision}')


def enqueue(spec_path, config, seed, front=False, name='backlog.txt', suffix=''):
    """Make a plan and add it to one of its driver's lists; the runner there takes it when its turn comes."""
    plan, _ = prepare_run(spec_path, config, seed, suffix)
    staged_or_exit(plan, config)
    driver = driver_of(plan)
    path, run_id = shlex.quote(f'{driver["root"]}/runs/{name}'), shlex.quote(plan['run_id'])
    if front:
        # Replace the list in one rename, so the runner never reads half of it.
        script = f'{{ echo {run_id}; cat {path} 2>/dev/null; }} > {path}.tmp && mv {path}.tmp {path}'
    else:
        script = f'echo {run_id} >> {path}'
    remote(driver, script, check=True, timeout=60)
    return plan


def enqueue_job(config, name, hosts, command, front=False, driver_name=None):
    """Queue maintenance: `command` on each host in turn, with {root} and {bundle} filled in for that host."""
    if not SAFE.fullmatch(name):
        raise SystemExit('a job needs a plain name')
    driver_key = driver_name or config.get('driver') or next(iter(config['hosts']))
    driver = driver_named(config, driver_key)
    bundle = stage.bundle_id()
    steps = []
    for host_name in hosts:
        host = config['hosts'].get(host_name)
        if not host or not host.get('root'):
            raise SystemExit(f'{host_name} is not a host with a benchmark root')
        stage.push_bundle(host_name, host)
        steps.append({'host': host_name, 'ssh': host['ssh'], 'local': host_name == driver_key,
                      'command': command.format(root=shlex.quote(host['root']), bundle=bundle)})
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-job-' + name
    local = HERE.parent / 'results' / 'lab' / 'jobs' / run_id
    local.mkdir(parents=True)
    (local / 'job.json').write_text(json.dumps({'name': name, 'steps': steps}, indent=1) + '\n')
    directory = f'{driver["root"]}/runs/{run_id}'
    remote(driver, f'mkdir -p {shlex.quote(directory)}', check=True, timeout=60)
    stage.copy_to(driver, [local / 'job.json'], directory)
    path, quoted = shlex.quote(f'{driver["root"]}/runs/backlog.txt'), shlex.quote(run_id)
    script = (f'{{ echo {quoted}; cat {path} 2>/dev/null; }} > {path}.tmp && mv {path}.tmp {path}' if front
              else f'echo {quoted} >> {path}')
    remote(driver, script, check=True, timeout=60)
    return run_id, steps


def runner_status(driver):
    done = remote(driver, f'cat {shlex.quote(driver["root"] + "/runs/runner-status.json")} 2>/dev/null', timeout=60)
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


def runner_alive(driver, status):
    return bool(status) and remote(driver, f'kill -0 {int(status["pid"])} 2>/dev/null', timeout=60).returncode == 0


def runner(config, action, driver_name=None, not_before=None, settings=None):
    """Start, stop, pause or adjust the runner on a driver host."""
    name = driver_name or config.get('driver') or next(iter(config['hosts']))
    driver = driver_named(config, name)
    runs = driver['root'] + '/runs'
    status = runner_status(driver)
    alive = runner_alive(driver, status)
    if action == 'start':
        if alive:
            raise SystemExit(f'a runner is already working {name} (pid {status["pid"]}); `runner restart` replaces it')
        bundle = stage.push_bundle(name, driver)
        remote(driver, f'mkdir -p {shlex.quote(runs)}', check=True, timeout=60)
        argv = [f'{driver["root"]}/lib/{bundle}/runner.py', '--root', driver['root']]
        # What a reboot should start: the same runner. An @reboot line in the operator's crontab runs this.
        boot = (f'#!/bin/sh\n# Written by plan.py runner start; starts the current runner after a reboot.\n'
                f'cd {shlex.quote(runs)} || exit 1\nexec python3 {shlex.join(argv)} >> runner.log 2>&1 < /dev/null\n')
        remote(driver, f'printf %s {shlex.quote(boot)} > {shlex.quote(driver["root"] + "/runner.sh")}', check=True, timeout=60)
        detach(driver, runs, [*argv, *(['--not-before', not_before] if not_before else [])], 'runner.log')
        return f'runner started on {name} from bundle {bundle}'
    if action == 'restart':
        # The old runner leaves its current run alone; the new one waits for that run, then carries on.
        if alive:
            gone = remote(driver, f'kill -USR1 {int(status["pid"])}; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do '
                                  f'kill -0 {int(status["pid"])} 2>/dev/null || exit 0; sleep 1; done; exit 1', timeout=60)
            if gone.returncode:
                raise SystemExit(f'the runner on {name} (pid {status["pid"]}) did not let go')
        return runner(config, 'start', driver_name, not_before)
    if action == 'set':
        current = remote(driver, f'cat {shlex.quote(runs + "/control.json")} 2>/dev/null', timeout=60).stdout
        control = json.loads(current) if current.strip() else {}
        control.update({key: value for key, value in (settings or {}).items() if key != 'write_budget'})
        control['write_budget'] = {**control.get('write_budget', {}), **(settings or {}).get('write_budget', {})}
        text = shlex.quote(json.dumps(control, indent=1))
        remote(driver, f'mkdir -p {shlex.quote(runs)} && printf "%s\\n" {text} > {shlex.quote(runs + "/control.json.tmp")} && '
                       f'mv {shlex.quote(runs + "/control.json.tmp")} {shlex.quote(runs + "/control.json")}',
               check=True, timeout=60)
        return json.dumps(control, indent=1)
    if action in ('pause', 'resume'):
        if action == 'pause':
            remote(driver, f'touch {shlex.quote(runs + "/.pause")}', check=True, timeout=60)
            return f'{name}: no further run will start; the current one finishes (`stop RUN` ends it sooner)'
        remote(driver, f'rm -f {shlex.quote(runs + "/.pause")}; touch {shlex.quote(runs + "/.resume")}', check=True, timeout=60)
        return f'{name}: resumed'
    if action == 'stop':
        if not alive:
            return f'no runner is working {name}'
        remote(driver, f'kill -TERM {int(status["pid"])}', check=True, timeout=60)
        return f'{name}: the runner stops after the current sample'
    return json.dumps(dict(status or {}, alive=alive), indent=1)


def show_queue(config, driver_name=None):
    driver = driver_named(config, driver_name)
    status = runner_status(driver)
    alive = runner_alive(driver, status)
    if not status:
        print('no runner has been started')
    else:
        gib = lambda count: f'{count / 2**30:.0f} GiB'
        print(f'runner: {status["state"] if alive else "NOT RUNNING (last state " + status["state"] + ")"}'
              f'{" - " + str(status["detail"]) if status.get("detail") else ""}, as of {status["utc"]}')
        if status.get('current'):
            current = status['current']
            progress = remote(driver, f'cat {shlex.quote(driver["root"] + "/runs/" + current["run"] + "/status.json")} '
                                      f'2>/dev/null', timeout=60).stdout.strip()
            print(f'  running ({current["lane"]}): {current["run"]} since {current["started_utc"]} {progress}')
        for host in sorted(set(status.get('written_24h', {})) | set(status.get('write_budget', {}))):
            allowance = status.get('write_budget', {}).get(host)
            print(f'  {host}: {gib(status.get("written_24h", {}).get(host, 0))} charged in 24 h'
                  + (f' of {gib(allowance)}' if allowance else ', no limit'))
        print(f'  sentinel: every {status["standing_every_s"] / 3600:g} h, last {status.get("standing_last_utc") or "never"}, '
              f'{status["standing_pending"]} left')
        for done in status.get('recent', [])[-5:]:
            print(f'  finished: {done["run"]} {done["state"]} {done.get("detail") or ""}')
    for label, name in (('backlog', 'backlog.txt'), ('sentinel', 'standing.txt')):
        runs = listed_runs(driver, name)
        states = remote(driver, 'cd ' + shlex.quote(driver['root'] + '/runs') + ' && for r in ' + ' '.join(map(shlex.quote, runs))
                        + '; do test -f "$r/status.json" || echo "$r"; done', timeout=60).stdout.split() if runs else []
        print(f'{label}: {len(states)} waiting of {len(runs)}')
        for run_id in states[:12]:
            try:
                plan = find_plan(run_id)[1]
                size = f'{sum(len(block["orders"][0]) for block in plan["blocks"])} samples, ' \
                       f'{sum(plan.get("writes", {}).values()) / 2**30:.0f} GiB of writes'
            except SystemExit:
                size = 'maintenance job' if '-job-' in run_id else 'no local plan'
            print(f'  {run_id}  {size}')
        if len(states) > 12:
            print(f'  ... and {len(states) - 12} more')


def collect(config, driver_name=None):
    """Bring back every listed run that is not already complete here, and rewrite the reports they touch."""
    driver = driver_named(config, driver_name)
    experiments = set()
    for run_id in [*listed_runs(driver), *listed_runs(driver, 'standing.txt')]:
        try:
            local, _ = find_plan(run_id)
        except SystemExit:
            continue  # queued from another checkout
        try:
            have = json.loads((local / 'status.json').read_text()).get('state')
        except (OSError, ValueError):
            have = None
        if have in ('complete', 'stopped', 'deadline', 'failed', 'refused'):
            continue
        source = f'{driver["root"]}/runs/{run_id}/' if driver.get('local') else f'{driver["ssh"]}:{driver["root"]}/runs/{run_id}/'
        done = subprocess.run(['rsync', '-a', '--exclude=plan.json', source, f'{local}/'])
        if done.returncode == 0 and (local / 'samples.jsonl').exists():
            status = json.loads((local / 'status.json').read_text()) if (local / 'status.json').exists() else {}
            print(f'{run_id}: {status.get("state", "no status")} {status.get("detail", "")}')
            experiments.add(local.parent)
    for experiment in sorted(experiments):
        subprocess.run([sys.executable, str(HERE / 'report.py'), str(experiment)])
    if not experiments:
        print('nothing new to collect')


def find_plan(run_id):
    matches = list((HERE.parent / 'results').glob(f'*/*/{run_id}/plan.json'))
    if len(matches) != 1:
        raise SystemExit(f'no local plan for run {run_id}')
    return matches[0].parent, json.loads(matches[0].read_text())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hosts', type=pathlib.Path, default=HERE / 'hosts.toml')
    commands = parser.add_subparsers(dest='command', required=True)
    for command, text in (('make', 'print the plan a spec expands to'),
                          ('start', 'run a spec at once, detached, outside the queue'),
                          ('enqueue', 'add a spec to its driver\'s backlog')):
        p = commands.add_parser(command, help=text)
        p.add_argument('spec', type=pathlib.Path)
        p.add_argument('--seed', type=int, default=1)
        if command == 'start':
            p.add_argument('--skip-preflight', action='store_true')
        if command == 'enqueue':
            p.add_argument('--front', action='store_true', help='run it next, ahead of the backlog')
    p = commands.add_parser('standing', help='give the driver sentinel runs of a spec to repeat at an interval')
    p.add_argument('spec', type=pathlib.Path)
    p.add_argument('--count', type=int, required=True, help='how many runs to prepare')
    p.add_argument('--first-seed', type=int, default=1)
    for command, text in (('status', 'what the agent is doing'), ('fetch', 'copy the records back'),
                          ('stop', 'ask the agent to stop after the current sample')):
        commands.add_parser(command, help=text).add_argument('run_id')
    p = commands.add_parser('runner', help='start, stop, pause or adjust the runner on a driver')
    p.add_argument('action', choices=('start', 'restart', 'stop', 'pause', 'resume', 'status', 'set'))
    p.add_argument('--driver', help='host the runner works (default: the configured driver)')
    p.add_argument('--not-before', help='start: ISO-8601 time with offset before which nothing is started')
    p.add_argument('--standing-every', type=float, metavar='HOURS', help='set: hours between sentinel runs')
    p.add_argument('--write-budget', action='append', default=[], metavar='HOST=GIB',
                   help='set: bytes a host\'s drive may be given in any 24 hours')
    p.add_argument('--halt-after', type=int, help='set: failed runs in a row that halt the runner')
    p = commands.add_parser('job', help='queue maintenance, such as generating corpora, to run between experiments')
    p.add_argument('name')
    p.add_argument('--host', action='append', required=True, help='host to run it on, in turn')
    p.add_argument('--command', dest='shell', required=True, help='shell command; {root} and {bundle} are filled in per host')
    p.add_argument('--front', action='store_true')
    p.add_argument('--driver')
    for command, text in (('queue', 'what the runner is doing and what is waiting'),
                          ('collect', 'fetch finished runs and write their experiments\' reports')):
        commands.add_parser(command, help=text).add_argument('--driver')
    args = parser.parse_args(argv)
    try:
        config = preflight.load(args.hosts)
        if args.command == 'make':
            spec = load_spec(args.spec)
            plan = make_plan(spec, config, json.loads((HERE / 'corpora.json').read_text()), args.seed, new_run_id(spec),
                             load_baseline(spec))
            json.dump(plan, sys.stdout, indent=1)
            print(f'\n{len(plan["cells"])} cells, {len(plan["blocks"])} blocks, '
                  f'{len(plan["blocks"]) * len(plan["arms"])} samples', file=sys.stderr)
            return
        if args.command in ('start', 'enqueue'):
            plan = start(args.spec, config, args.seed, args.skip_preflight) if args.command == 'start' \
                else enqueue(args.spec, config, args.seed, args.front)
            print(f'{plan["run_id"]} {"started" if args.command == "start" else "queued"} on {plan["driver"]}: '
                  f'{len(plan["blocks"])} blocks, {len(plan["blocks"]) * len(plan["arms"])} samples, '
                  f'{sum(plan["writes"].values()) / 2**30:.0f} GiB of writes')
            return
        if args.command == 'standing':
            for number in range(args.count):
                plan = enqueue(args.spec, config, args.first_seed + number, name='standing.txt',
                               suffix=f'-s{args.first_seed + number:04d}')
            print(f'{args.count} sentinel runs of {plan["experiment"]} prepared on {plan["driver"]}, each '
                  f'{len(plan["blocks"]) * len(plan["arms"])} samples and {sum(plan["writes"].values()) / 2**30:.0f} GiB of writes')
            return
        if args.command == 'runner':
            settings = {}
            if args.standing_every is not None:
                settings['standing_every_s'] = int(args.standing_every * 3600)
            if args.halt_after is not None:
                settings['halt_after'] = args.halt_after
            for item in args.write_budget:
                host, _, amount = item.partition('=')
                if host not in config['hosts'] or not amount.replace('.', '', 1).isdigit():
                    parser.error(f'--write-budget {item} is not HOST=GIB')
                settings.setdefault('write_budget', {})[host] = int(float(amount) * 2**30)
            if settings and args.action != 'set':
                parser.error('--standing-every, --write-budget and --halt-after go with `runner set`')
            print(runner(config, args.action, args.driver, args.not_before, settings))
            return
        if args.command == 'queue':
            show_queue(config, args.driver)
            return
        if args.command == 'job':
            run_id, steps = enqueue_job(config, args.name, args.host, args.shell, args.front, args.driver)
            print(f'{run_id} queued: ' + '; '.join(f'{step["host"]}: {step["command"]}' for step in steps))
            return
        if args.command == 'collect':
            collect(config, args.driver)
            return
    except (SpecError, preflight.ConfigError, OSError) as error:
        parser.error(str(error))
    local, plan = find_plan(args.run_id)
    driver = driver_of(plan)
    directory = shlex.quote(f'{driver["root"]}/runs/{args.run_id}')
    if args.command == 'status':
        done = remote(driver, f'cat {directory}/status.json 2>/dev/null || echo "{{}}"; tail -n 3 {directory}/agent.log',
                      timeout=60)
        print(done.stdout.strip() or done.stderr.strip())
    elif args.command == 'stop':
        remote(driver, f'kill -TERM "$(python3 -c \'import json;print(json.load(open("{directory}/status.json"))["pid"])\')"',
               check=True, timeout=60)
        print('asked the agent to stop after the current sample')
    else:
        source = f'{driver["root"]}/runs/{args.run_id}/' if driver.get('local') else f'{driver["ssh"]}:{directory}/'
        subprocess.run(['rsync', '-a', '--exclude=plan.json', source, f'{local}/'], check=True)
        status = json.loads((local / 'status.json').read_text()) if (local / 'status.json').exists() else {}
        print(f'{local}: {status.get("state", "no status")} {status.get("detail", "")}')


if __name__ == '__main__':
    main()
