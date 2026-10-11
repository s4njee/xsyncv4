#!/usr/bin/env python3
"""Inventory the benchmark hosts and prove which path each link takes.

Runs on the controller. Every check compares hosts.toml with what probe.py
reports from the host itself; a run may start only when nothing is reported.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import tomllib

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE.parent / 'results' / 'lab' / 'preflight'
SSH = ('ssh', '-oBatchMode=yes', '-oConnectTimeout=10')
MEDIA = ('wired', 'wireless', 'mesh')
MAX_CLOCK_SKEW_S = 2.0


class ConfigError(ValueError):
    pass


def load(path):
    """Read hosts.toml and reject entries that cannot be checked."""
    with open(path, 'rb') as stream:
        config = tomllib.load(stream)
    hosts, links = config.get('hosts', {}), config.get('links', {})
    for name, host in hosts.items():
        for key in ('ssh', 'name', 'hostname'):
            if not host.get(key) or str(host[key]).startswith('-'):
                raise ConfigError(f'host {name} needs a valid {key}')
        if host.get('root') and not host['root'].startswith('/'):
            raise ConfigError(f'host {name}: root must be an absolute path')
    for name, link in links.items():
        ends = link.get('hosts', [])
        if len(ends) != 2 or any(end not in hosts for end in ends):
            raise ConfigError(f'link {name} needs two declared hosts')
        if link.get('medium') not in MEDIA:
            raise ConfigError(f'link {name}: medium must be one of {", ".join(MEDIA)}')
        if any(end not in ends for end in link.get('interface', {})):
            raise ConfigError(f'link {name} declares an interface for a host that is not on it')
    return config


def probe(host, *arguments, timeout=90):
    """Run probe.py on a host over SSH. Returns the report, or {'error': ...}."""
    command = [*SSH, host['ssh'], 'python3', '-', *arguments]
    try:
        with open(HERE / 'probe.py', 'rb') as script:
            done = subprocess.run(command, stdin=script, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'error': 'probe timed out'}
    if done.returncode:
        lines = done.stderr.decode(errors='replace').strip().splitlines()
        return {'error': lines[-1] if lines else f'ssh exited {done.returncode}'}
    try:
        return json.loads(done.stdout)
    except ValueError:
        return {'error': 'probe printed no JSON'}


def helper_sha256():
    return hashlib.sha256((HERE / 'xsbench-helper').read_bytes()).hexdigest()


def check_inventory(name, host, report, now=None):
    """Problems with one host's inventory, as a list of sentences."""
    if 'error' in report:
        return [f'{name}: {report["error"]}']
    problems = []
    if report.get('hostname') != host['hostname']:
        problems.append(f'{name}: reached a host called {report.get("hostname")}, expected {host["hostname"]}')
    if report.get('system') != 'Linux':
        problems.append(f'{name}: {report.get("system")} endpoints are not supported yet')
    if now is not None and report.get('utc'):
        skew = abs((datetime.datetime.fromisoformat(report['utc']) - now).total_seconds())
        if skew > MAX_CLOCK_SKEW_S:
            problems.append(f'{name}: clock differs from the controller by {skew:.1f} s')
    for tool in ('rsync', 'ip', 'tc', 'ping', 'findmnt'):
        if not report.get('tools', {}).get(tool):
            problems.append(f'{name}: {tool} is not installed')
    if not host.get('root'):
        problems.append(f'{name}: no benchmark root is declared')
    else:
        root = next((entry for entry in report.get('paths', []) if entry.get('path') == host['root']), {})
        if not root.get('exists'):
            problems.append(f'{name}: benchmark root {host["root"]} does not exist')
        elif not root.get('writable'):
            problems.append(f'{name}: benchmark root {host["root"]} is not writable')
        wanted = host.get('root_fstype')
        if wanted and root.get('fstype') and root['fstype'] != wanted:
            problems.append(f'{name}: {host["root"]} is on {root.get("fstype")}, expected {wanted}')
    if host.get('helper'):
        helper = report.get('helper', {})
        state = helper.get('status', {})
        if not helper.get('installed'):
            problems.append(f'{name}: xsbench-helper is not installed')
        elif helper.get('sha256') != helper_sha256():
            problems.append(f'{name}: the installed xsbench-helper differs from benchmarks/lab/xsbench-helper')
        elif not helper.get('sudo'):
            problems.append(f'{name}: sudo -n xsbench-helper status failed: {helper.get("error")}')
        elif state.get('config') != 'ok':
            problems.append(f'{name}: xsbench-helper configuration: {state.get("config")}')
        else:
            if state.get('netem') != 'off' or state.get('netem_timer') != 'off':
                problems.append(f'{name}: a netem qdisc or its timer is still active')
            if state.get('governor_saved') != 'no':
                problems.append(f'{name}: a previous run left the governor changed')
    return problems


def check_route(link_name, link, source, target, hosts, report):
    """Problems with the path from one end of a link to the other."""
    label = f'{link_name} {source}->{target}'
    if 'error' in report:
        return [f'{label}: {report["error"]}']
    problems = []
    ssh = report.get('ssh', {})
    if not ssh.get('ok'):
        problems.append(f'{label}: {source} cannot SSH to {target}: {ssh.get("error", "not attempted")}')
    elif ssh.get('peer_hostname') != hosts[target]['hostname']:
        problems.append(f'{label}: reached a host called {ssh.get("peer_hostname")}, '
                        f'expected {hosts[target]["hostname"]}')
    declared = link.get('interface', {}).get(source)
    device = report.get('dev')
    if not declared:
        problems.append(f'{label}: no interface is declared for {source}; it uses {device}')
    elif device != declared:
        problems.append(f'{label}: traffic leaves by {device}, declared {declared}')
    if ssh.get('ok') and ssh.get('client_ip') not in report.get('interface_addresses', []):
        problems.append(f'{label}: the SSH connection came from {ssh.get("client_ip")}, which is not on {device}')
    interface = report.get('interface') or {}
    if interface.get('operstate') != 'up':
        problems.append(f'{label}: {device} is {interface.get("operstate")}')
    if link['medium'] in ('wired', 'wireless') and interface.get('medium') != link['medium']:
        problems.append(f'{label}: {device} is {interface.get("medium")}, the link is declared {link["medium"]}')
    minimum = link.get('min_speed_mbps')
    if minimum and (interface.get('speed_mbps') or 0) < minimum:
        problems.append(f'{label}: {device} negotiated {interface.get("speed_mbps")} Mb/s, below {minimum}')
    if 'netem' in (report.get('qdisc') or ''):
        problems.append(f'{label}: {device} has a netem qdisc')
    ping = report.get('ping', {})
    if 'rtt_avg_ms' not in ping:
        problems.append(f'{label}: ping got no reply')
    else:
        limit = link.get('max_rtt_ms')
        if limit and ping['rtt_avg_ms'] > limit:
            problems.append(f'{label}: round trip averages {ping["rtt_avg_ms"]} ms, above {limit}')
        if link['medium'] == 'wired' and ping.get('loss_pct'):
            problems.append(f'{label}: {ping["loss_pct"]}% of pings were lost')
    return problems


def survey(config, link_names, pings):
    """Inventory every host on the chosen links and probe each link both ways."""
    hosts, links = config['hosts'], config['links']
    record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
              'helper_sha256': helper_sha256(), 'config': config, 'inventory': {}, 'routes': {}, 'problems': []}
    for name in sorted({end for link in link_names for end in links[link]['hosts']}):
        host = hosts[name]
        arguments = ['inventory'] + (['--path', host['root']] if host.get('root') else [])
        now = datetime.datetime.now(datetime.timezone.utc)
        report = record['inventory'][name] = probe(host, *arguments)
        record['problems'] += check_inventory(name, host, report, now)
    for link_name in link_names:
        link = links[link_name]
        for source, target in (link['hosts'], link['hosts'][::-1]):
            if 'error' in record['inventory'][source]:
                continue  # already reported; its route would only repeat the failure
            report = probe(hosts[source], 'route', '--peer', hosts[target]['name'],
                           '--ssh', hosts[target]['ssh'], '--pings', str(pings))
            record['routes'][f'{link_name}:{source}->{target}'] = report
            record['problems'] += check_route(link_name, link, source, target, hosts, report)
    return record


def describe(record):
    """A short human summary of a survey record."""
    lines = []
    for name, report in record['inventory'].items():
        if 'error' in report:
            continue
        root = next(iter(report.get('paths', [])), {})
        lines.append(f'{name}: {report.get("board") or report.get("cpu_model")}, {report.get("cpus")} CPUs, '
                     f'{(report.get("memory_bytes") or 0) / 2**30:.0f} GiB, {report.get("os")}, '
                     f'kernel {report.get("kernel")}, root on {root.get("fstype", "?")} ({root.get("source", "?")})')
    for name, report in record['routes'].items():
        if 'error' in report:
            continue
        interface, ping = report.get('interface') or {}, report.get('ping', {})
        lines.append(f'{name}: via {report.get("dev")} ({interface.get("medium")}, '
                     f'{interface.get("speed_mbps")} Mb/s) to {report.get("address")}, '
                     f'RTT {ping.get("rtt_avg_ms", "?")} ms')
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hosts', type=pathlib.Path, default=HERE / 'hosts.toml')
    parser.add_argument('--link', action='append', help='link to check (default: all)')
    parser.add_argument('--pings', type=int, default=10)
    parser.add_argument('--rev', help='also require every host to have the recorded build of this commit')
    parser.add_argument('--output', type=pathlib.Path, default=RESULTS, help='directory for the record')
    args = parser.parse_args(argv)
    try:
        config = load(args.hosts)
    except (OSError, ConfigError, tomllib.TOMLDecodeError) as error:
        parser.error(str(error))
    link_names = args.link or sorted(config['links'])
    if unknown := [name for name in link_names if name not in config['links']]:
        parser.error('unknown link: ' + ', '.join(unknown))
    record = survey(config, link_names, args.pings)
    if args.rev:
        import stage  # stage imports this module
        build = record['build'] = stage.load_build(args.rev)
        names = [name for name in record['inventory'] if config['hosts'][name].get('root')]
        record['staged'], problems = stage.check(config, names, build)
        record['problems'] += problems
    args.output.mkdir(parents=True, exist_ok=True)
    stamp = record['utc'].replace('-', '').replace(':', '').replace('+0000', 'Z')
    output = args.output / f'{stamp}-{"-".join(link_names)}.json'
    output.write_text(json.dumps(record, indent=2) + '\n')
    print('\n'.join(describe(record)))
    print(output)
    for problem in record['problems']:
        print('PROBLEM', problem)
    if record['problems']:
        sys.exit(1)
    print('preflight passed')


if __name__ == '__main__':
    main()
