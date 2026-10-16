#!/usr/bin/env python3
"""Stream the state of every benchmark runner as JSON lines, for the dashboard server.

Each line is one message:

  {"type": "runner", "driver": NAME, "links": [...], "ok": bool, "error": str|null, "route": str, "snapshot": {...}}
  {"type": "host", "host": NAME, "ok": bool, "load": [...], "cpus": N, "disk_free": B, "disk_total": B, ...}
  {"type": "results", "experiments": [...]}

Drivers are the hosts that drive a link in hosts.toml. Each is probed with
probe_runner.py: run in place for a local driver, piped over SSH otherwise.
A host that cannot be reached directly is tried through the address a link
declares for another host (the Mac reaches neo through mars's direct cable
when it is on another Wi-Fi network). Nothing here changes any host.
"""
import argparse
import json
import re
import pathlib
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
LAB = HERE.parent / 'lab'
RESULTS = HERE.parent / 'results'
sys.path.insert(0, str(LAB))
import preflight  # noqa: E402  (hosts.toml loader)

PROBE = (HERE / 'probe_runner.py').read_text()
HEALTH = ('import json,os,shutil,socket,sys;r=sys.argv[1];d=shutil.disk_usage(r) if os.path.exists(r) else None;'
          'print(json.dumps({"hostname":socket.gethostname(),"load":list(os.getloadavg()),"cpus":os.cpu_count(),'
          '"disk_free":d.free if d else None,"disk_total":d.total if d else None}))')
# Byte counters of a network interface: Linux sysfs, or netstat on macOS.
COUNTERS = ('i={iface}; if [ -r /sys/class/net/$i/statistics/rx_bytes ]; then '
            'cat /sys/class/net/$i/statistics/rx_bytes /sys/class/net/$i/statistics/tx_bytes; '
            "else netstat -ibn -I $i | awk 'NR==2{{print $7; print $10}}'; fi")
lock = threading.Lock()


def emit(message):
    with lock:
        sys.stdout.write(json.dumps(message, separators=(',', ':')) + '\n')
        sys.stdout.flush()


class Reach:
    """How this machine runs a command on a host: in place, over SSH, or over SSH through a jump host."""

    def __init__(self, name, host, jumps):
        self.name, self.host, self.routes = name, host, []
        if host.get('local'):
            self.routes = [('local', None)]
        else:
            self.routes = [('direct', None)] + [(f'via {jump}', jump) for jump in jumps]
        self.working = None

    def argv(self, route, remote):
        _, jump = route
        if route[0] == 'local':
            return ['sh', '-c', remote]
        options = ['ssh', '-oBatchMode=yes', '-oConnectTimeout=4', '-oServerAliveInterval=5', '-oControlMaster=auto',
                   f'-oControlPath=/tmp/xsdash-{self.name}-%C', '-oControlPersist=120']
        if jump:
            options += ['-J', jump]
        return [*options, self.host['ssh'], remote]

    def run(self, remote, stdin=None, timeout=30):
        """(route label, completed process) on the first route that works, preferring the last one that did."""
        order = ([self.working] if self.working else []) + [r for r in self.routes if r != self.working]
        last = None
        for route in order:
            try:
                done = subprocess.run(self.argv(route, remote), input=stdin, capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                last = (route[0], None)
                continue
            if done.returncode != 255:  # 255 is ssh's own failure: try the next route
                self.working = route
                return route[0], done
            last = (route[0], done)
        self.working = None
        return last


def jumps_of(config):
    """user@address for each address a link declares for a host, to reach other hosts through it."""
    found = []
    for link in config['links'].values():
        for host, address in link.get('address', {}).items():
            user = config['hosts'][host]['ssh'].rpartition('@')[0]
            target = f'{user}@{address}' if user else address
            if target not in found:
                found.append(target)
    return found


def drivers_of(config):
    """{driver host: [links it drives]}."""
    default = config.get('driver') or next(iter(config['hosts']))
    drivers = {}
    for name, link in config['links'].items():
        drivers.setdefault(link.get('driver') or default, []).append(name)
    return drivers


def watch_driver(name, links, reach, root, interval):
    while True:
        started = time.time()
        quoted = root.replace("'", "'\\''")
        result = reach.run(f"python3 - '{quoted}'", stdin=PROBE, timeout=60)
        message = {'type': 'runner', 'driver': name, 'links': links, 'utc': time.time()}
        if result and result[1] is not None and result[1].returncode == 0:
            try:
                message.update(ok=True, error=None, route=result[0], snapshot=json.loads(result[1].stdout))
            except ValueError as error:
                message.update(ok=False, error=f'bad probe output: {error}', route=result[0])
        else:
            detail = (result[1].stderr.strip()[-300:] if result and result[1] is not None else 'timed out') if result else 'unreachable'
            message.update(ok=False, error=detail or 'unreachable', route=result[0] if result else None)
        emit(message)
        time.sleep(max(0.5, interval - (time.time() - started)))


def watch_speed(name, reach, interfaces, interval):
    """Bytes per second in and out of each of a driver's link interfaces, about once a second.

    One remote command samples every interface twice, `interval` apart, so the rate is
    measured on the host itself and the SSH round trip does not distort it.
    """
    # Each interface's negotiated speed, read again every half minute: it sets the chart's axis and
    # the card's label, and a cable can be moved to another port (10 GbE to 2.5 GbE on 2026-10-16).
    def link_speeds():
        speeds = {}
        for iface in interfaces:
            result = reach.run(f"cat /sys/class/net/{iface}/speed 2>/dev/null || ifconfig {iface} 2>/dev/null | grep -o 'media:.*'", timeout=30)
            text = result[1].stdout.strip() if result and result[1] is not None else ''
            found = re.search(r'(\d+(?:\.\d+)?)(G?)base', text, re.I)
            speeds[iface] = round(float(found.group(1)) * (1000 if found.group(2) else 1)) if found else (int(text) if text.isdigit() and int(text) > 0 else None)
        return speeds
    link, checked = link_speeds(), time.monotonic()
    script = '; '.join(f'echo {i}; ' + COUNTERS.format(iface=i) for i in interfaces)
    probe = f'{script}; echo -; sleep {interval}; {script}; echo -; python3 -c "import time; print(time.time())"'
    while True:
        if time.monotonic() - checked > 30:
            link, checked = link_speeds(), time.monotonic()
        result = reach.run(probe, timeout=interval + 20)
        if not (result and result[1] is not None and result[1].returncode == 0):
            time.sleep(5)
            continue
        lines = result[1].stdout.split()
        try:
            halves, current = [], {}
            for token in lines[:-1]:
                if token == '-':
                    halves.append(current)
                    current = {}
                elif not token.isdigit():
                    current[token] = []
                    key = token
                else:
                    current[key].append(int(token))
            first, second = halves[0], halves[1]
        except (IndexError, KeyError, UnboundLocalError):
            time.sleep(5)
            continue
        for iface in interfaces:
            a, b = first.get(iface), second.get(iface)
            if not a or not b or len(a) < 2 or len(b) < 2:
                continue
            emit({'type': 'speed', 'driver': name, 'iface': iface, 'utc': time.time(), 'link_mbps': link.get(iface),
                  'rx_bps': max(0, b[0] - a[0]) * 8 / interval, 'tx_bps': max(0, b[1] - a[1]) * 8 / interval})


def watch_host(name, reach, root, interval):
    while True:
        quoted = root.replace("'", "'\\''")
        result = reach.run(f"python3 -c '{HEALTH}' '{quoted}'", timeout=30)
        message = {'type': 'host', 'host': name, 'utc': time.time()}
        if result and result[1] is not None and result[1].returncode == 0:
            try:
                message.update(ok=True, route=result[0], **json.loads(result[1].stdout))
            except ValueError:
                message.update(ok=False, error='bad output')
        else:
            message.update(ok=False, error='unreachable')
        emit(message)
        time.sleep(interval)


def results_index():
    """Every analysed experiment under benchmarks/results, with its verdict counts."""
    experiments = []
    for effects in sorted(RESULTS.glob('*/*/analysis/effects.json')):
        directory = effects.parent.parent
        try:
            rows = json.loads(effects.read_text())
        except (OSError, ValueError):
            continue
        primary = [row for row in rows if row.get('primary')]
        if not primary:
            continue
        verdicts = {}
        for row in primary:
            verdicts[row['verdict']] = verdicts.get(row['verdict'], 0) + 1
        runs = [p.name for p in directory.iterdir() if p.is_dir() and p.name[:2] == '20']
        experiments.append({'group': directory.parent.name, 'experiment': directory.name, 'kind': primary[0].get('kind'),
                            'metric': primary[0].get('metric'), 'comparisons': len(primary), 'verdicts': verdicts,
                            'cells': len({row['cell_id'] for row in primary}), 'arms': sorted({row['arm'] for row in primary}),
                            'runs': len(runs), 'last_run': max(runs) if runs else None, 'mtime': effects.stat().st_mtime})
    return experiments


def watch_results(interval):
    seen = None
    while True:
        index = results_index()
        stamp = [(e['group'], e['experiment'], e['mtime']) for e in index]
        if stamp != seen:
            emit({'type': 'results', 'utc': time.time(), 'experiments': index})
            seen = stamp
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--interval', type=float, default=5.0, help='seconds between runner snapshots')
    parser.add_argument('--host-interval', type=float, default=30.0)
    parser.add_argument('--once', action='store_true', help='print one round and exit')
    args = parser.parse_args()
    config = preflight.load(LAB / 'hosts.toml')
    jumps = jumps_of(config)
    drivers = drivers_of(config)
    reaches = {name: Reach(name, host, jumps) for name, host in config['hosts'].items() if host.get('root')}
    if args.once:
        for name, links in drivers.items():
            threading.Thread(target=watch_driver, args=(name, links, reaches[name], config['hosts'][name]['root'], 1e9),
                             daemon=True).start()
        emit({'type': 'results', 'utc': time.time(), 'experiments': results_index()})
        time.sleep(20)
        return
    emit({'type': 'config', 'utc': time.time(), 'drivers': drivers,
          'links': {name: {key: link.get(key) for key in ('hosts', 'medium', 'driver', 'results', 'initiator')}
                    for name, link in config['links'].items()},
          'hosts': {name: {key: host.get(key) for key in ('name', 'hostname', 'root', 'local', 'helper')}
                    for name, host in config['hosts'].items()}})
    for name, links in drivers.items():
        threading.Thread(target=watch_driver, args=(name, links, reaches[name], config['hosts'][name]['root'], args.interval),
                         daemon=True).start()
    for name, links in drivers.items():
        interfaces = sorted({config['links'][link].get('interface', {}).get(name) for link in links} - {None})
        if interfaces:
            threading.Thread(target=watch_speed, args=(name, reaches[name], interfaces, 1.0), daemon=True).start()
    for name, reach in reaches.items():
        if name not in drivers:
            threading.Thread(target=watch_host, args=(name, reach, config['hosts'][name]['root'], args.host_interval),
                             daemon=True).start()
    threading.Thread(target=watch_results, args=(60.0,), daemon=True).start()
    while True:
        time.sleep(3600)


if __name__ == '__main__':
    main()
