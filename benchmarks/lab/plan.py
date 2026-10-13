#!/usr/bin/env python3
"""Turn an experiment spec into a randomized block plan, and run it on the driver host.

A spec (benchmarks/experiments/*.toml) names arms, cells and a block budget.
`make` expands it into explicit blocks: every arm once per block, in an order
drawn from the seed, with the cells interleaved. `start` checks the hosts,
copies the plan to the driver and launches agent.py there, detached; `status`,
`fetch` and `stop` follow it up.
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
    return {'schema': 1, 'experiment': spec['id'], 'spec_sha256': spec['sha256'], 'kind': spec['kind'],
            'hypothesis': spec['hypothesis'], 'primary': spec['primary'], 'delta': spec.get('delta'),
            'control': spec['control'], 'seed': seed, 'run_id': run_id, 'driver': driver,
            'sample_timeout_s': spec.get('sample_timeout_s', 3600),
            'results': link.get('results', 'lab'), 'background': bool(link.get('background')),
            'eager_cleanup': spec.get('cleanup') == 'eager',
            'hosts': hosts, 'links': {spec['matrix']['link']: {key: link[key] for key in link if key != 'interface'}},
            'arms': arms, 'cells': cells, 'corpora': corpora, 'blocks': blocks,
            'scripts': {path.name: stage.sha256(path) for path in stage.SCRIPTS}}


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


def new_run_id(spec):
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + spec['id']


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


def prepare_run(spec_path, config, seed):
    """Make a plan, keep it locally and put it on the driver. Returns (plan, remote directory)."""
    spec = load_spec(spec_path)
    pins = json.loads((HERE / 'corpora.json').read_text())
    plan = make_plan(spec, config, pins, seed, new_run_id(spec), load_baseline(spec))
    for name, host in plan['hosts'].items():
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
    if not skip_preflight:
        preflight_or_exit(spec['matrix']['link'], sorted({stage.resolve(arm['rev'])[:12] for arm in spec['arms'].values()
                                                           if arm['tool'] == 'xs'}))
    plan, directory = prepare_run(spec_path, config, seed)
    driver = driver_of(plan)
    # The backgrounded command must be the agent alone, with every descriptor redirected, or SSH waits for it.
    if driver.get('local'):
        # This machine is the driver: detach the agent into its own session, and keep the machine awake.
        with open(pathlib.Path(directory) / 'agent.log', 'w') as log:
            subprocess.Popen(['caffeinate', '-i', sys.executable, driver['root'] + '/bin/agent.py', 'plan.json'],
                             cwd=directory, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True)
        return plan
    launch = (f'cd {shlex.quote(directory)} || exit 1; setsid nohup python3 '
              f'{shlex.quote(driver["root"] + "/bin/agent.py")} plan.json > agent.log 2>&1 < /dev/null & echo started')
    remote(driver, launch, check=True, timeout=60)
    return plan


def queued_runs(driver):
    """Run ids in the driver's queue, in order."""
    done = remote(driver, f'cat {shlex.quote(driver["root"] + "/runs/queue.txt")} 2>/dev/null', timeout=60)
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def enqueue(spec_path, config, seed):
    plan, _ = prepare_run(spec_path, config, seed)
    driver = driver_of(plan)
    remote(driver, f'echo {shlex.quote(plan["run_id"])} >> {shlex.quote(driver["root"] + "/runs/queue.txt")}', check=True)
    return plan


def night(config, opens, closes):
    """Check the hosts now, then start overnight.py on the driver for the given window."""
    driver = config['hosts'][config.get('driver') or next(iter(config['hosts']))]
    runs = queued_runs(driver)
    if not runs:
        raise SystemExit('the queue is empty: enqueue a spec first')
    plans = [find_plan(run_id)[1] for run_id in runs]
    # A run still in progress holds the performance governor; that is not a leftover.
    expected = ('left the governor changed',) if run_in_progress(driver) else ()
    for link in sorted({name for plan in plans for name in plan['links']}):
        preflight_or_exit(link, sorted({revision for plan in plans for revision in revisions_of(plan)}), expected)
    root = driver['root']
    launch = (f'cd {shlex.quote(root + "/runs")} || exit 1; setsid nohup python3 {shlex.quote(root + "/bin/overnight.py")} '
              f'--root {shlex.quote(root)} --not-before {shlex.quote(opens)} --deadline {shlex.quote(closes)} '
              f'> overnight.log 2>&1 < /dev/null & echo started')
    remote(driver, launch, check=True, timeout=60)
    return runs


def find_plan(run_id):
    matches = list((HERE.parent / 'results').glob(f'*/*/{run_id}/plan.json'))
    if len(matches) != 1:
        raise SystemExit(f'no local plan for run {run_id}')
    return matches[0].parent, json.loads(matches[0].read_text())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hosts', type=pathlib.Path, default=HERE / 'hosts.toml')
    commands = parser.add_subparsers(dest='command', required=True)
    for command, text in (('make', 'print the plan a spec expands to'), ('start', 'run a spec on the driver, detached')):
        p = commands.add_parser(command, help=text)
        p.add_argument('spec', type=pathlib.Path)
        p.add_argument('--seed', type=int, default=1)
        if command == 'start':
            p.add_argument('--skip-preflight', action='store_true')
    for command, text in (('status', 'what the agent is doing'), ('fetch', 'copy the records back'),
                          ('stop', 'ask the agent to stop after the current sample')):
        commands.add_parser(command, help=text).add_argument('run_id')
    p = commands.add_parser('enqueue', help='put a spec in the driver\'s overnight queue')
    p.add_argument('spec', type=pathlib.Path)
    p.add_argument('--seed', type=int, default=1)
    p = commands.add_parser('night', help='run the queue unattended inside a time window')
    p.add_argument('--from', dest='opens', required=True, help='ISO-8601 with offset, e.g. 2026-10-11T22:00-05:00')
    p.add_argument('--until', dest='closes', required=True, help='ISO-8601 with offset')
    commands.add_parser('queue', help='what the overnight queue is doing')
    commands.add_parser('collect', help='fetch every queued run and write its experiment\'s report')
    commands.add_parser('stop-queue', help='stop the overnight queue after the current sample')
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
        if args.command == 'start':
            plan = start(args.spec, config, args.seed, args.skip_preflight)
            print(f'{plan["run_id"]} started on {plan["driver"]}: {len(plan["blocks"])} blocks, '
                  f'{len(plan["blocks"]) * len(plan["arms"])} samples')
            return
        if args.command == 'enqueue':
            plan = enqueue(args.spec, config, args.seed)
            print(f'{plan["run_id"]} queued on {plan["driver"]}: {len(plan["blocks"])} blocks, '
                  f'{len(plan["blocks"]) * len(plan["arms"])} samples')
            return
        if args.command == 'night':
            runs = night(config, args.opens, args.closes)
            print(f'the queue will run from {args.opens} until {args.closes}:')
            print('\n'.join('  ' + run for run in runs))
            return
    except (SpecError, preflight.ConfigError, OSError) as error:
        parser.error(str(error))
    if args.command in ('queue', 'collect', 'stop-queue'):
        driver = config['hosts'][config.get('driver') or next(iter(config['hosts']))]
        runs_directory = shlex.quote(driver['root'] + '/runs')
        if args.command == 'stop-queue':
            remote(driver, f'kill -TERM "$(python3 -c \'import json;print(json.load(open("{driver["root"]}/runs/'
                           f'queue-status.json"))["pid"])\')"', check=True, timeout=60)
            print('asked the queue to stop after the current sample')
            return
        print(remote(driver, f'cat {runs_directory}/queue-status.json 2>/dev/null || echo "no queue has been started"',
                     timeout=60).stdout.strip())
        for run_id in queued_runs(driver):
            status = remote(driver, f'cat {runs_directory}/{shlex.quote(run_id)}/status.json 2>/dev/null', timeout=60)
            print(run_id, status.stdout.strip() or 'not started')
        if args.command == 'collect':
            experiments = set()
            for run_id in queued_runs(driver):
                local, _ = find_plan(run_id)
                done = subprocess.run(['rsync', '-a', '--exclude=plan.json', f'{driver["ssh"]}:{driver["root"]}/runs/{run_id}/',
                                       f'{local}/'])
                if done.returncode == 0 and (local / 'samples.jsonl').exists():
                    experiments.add(local.parent)
            for experiment in sorted(experiments):
                subprocess.run([sys.executable, str(HERE / 'report.py'), str(experiment)])
        return
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
