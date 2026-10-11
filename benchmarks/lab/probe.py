#!/usr/bin/env python3
"""Report one benchmark endpoint's hardware, state or route to a peer as JSON.

Runs on the endpoint with only the standard library, and changes nothing.
The controller can run it without staging: ssh HOST python3 - ARGS < probe.py
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import re
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time

HELPER = '/usr/local/sbin/xsbench-helper'
# A non-interactive SSH session's PATH often omits the sbin directories.
SEARCH = os.environ.get('PATH', '').split(os.pathsep) + ['/usr/sbin', '/sbin', '/usr/local/sbin']
CPUFREQ = pathlib.Path('/sys/devices/system/cpu/cpufreq')
NET = pathlib.Path('/sys/class/net')
MEMINFO = ('MemTotal', 'MemAvailable', 'Cached', 'Buffers', 'Dirty', 'Writeback', 'SwapTotal', 'SwapFree')
TOOLS = ('rsync', 'ssh', 'ip', 'tc', 'iw', 'ping', 'strace', 'perf', 'vcgencmd', 'zstd', 'findmnt',
         'lsblk', 'systemd-run', 'sudo', 'iperf3')


def which(name):
    return shutil.which(name, path=os.pathsep.join(SEARCH))


def run(argv, timeout=15):
    """Return (status, stdout, stderr); status is None if the tool is missing or hung."""
    tool = which(argv[0])
    if not tool:
        return None, '', argv[0] + ' is not installed'
    try:
        done = subprocess.run([tool, *argv[1:]], capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None, '', argv[0] + ' timed out'
    return done.returncode, done.stdout, done.stderr


def read(path):
    try:
        return pathlib.Path(path).read_text().strip()
    except OSError:
        return None


def read_int(path):
    value = read(path)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds')


def parse_meminfo(text):
    """kB values of the fields in MEMINFO, converted to bytes."""
    result = {}
    for line in text.splitlines():
        key, _, value = line.partition(':')
        fields = value.split()
        if key in MEMINFO and fields:
            result[key] = int(fields[0]) * 1024
    return result


def parse_snmp_tcp(text):
    """The Tcp counters of /proc/net/snmp as a dict."""
    rows = [line.split()[1:] for line in text.splitlines() if line.startswith('Tcp:')]
    if len(rows) != 2:
        return {}
    wanted = ('RetransSegs', 'OutSegs', 'InSegs', 'InErrs', 'OutRsts')
    return {name: int(value) for name, value in zip(*rows) if name in wanted}


def parse_ping(text):
    """Packet loss and round-trip statistics from iputils or BSD ping."""
    result = {}
    loss = re.search(r'([\d.]+)% packet loss', text)
    if loss:
        result['loss_pct'] = float(loss.group(1))
    rtt = re.search(r'= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms', text)
    if rtt:
        result.update(zip(('rtt_min_ms', 'rtt_avg_ms', 'rtt_max_ms', 'rtt_mdev_ms'), map(float, rtt.groups())))
    return result


def parse_ssh_connection(text):
    """SSH_CONNECTION is 'client_ip client_port server_ip server_port'."""
    fields = text.split()
    if len(fields) != 4:
        return None
    return {'client_ip': fields[0], 'client_port': int(fields[1]),
            'server_ip': fields[2], 'server_port': int(fields[3])}


def parse_iw_link(text):
    """Signal and bitrates from `iw dev IF link`."""
    result = {'connected': text.startswith('Connected to')}
    for key, pattern in (('signal_dbm', r'signal: (-?\d+) dBm'), ('rx_bitrate_mbps', r'rx bitrate: ([\d.]+) MBit/s'),
                         ('tx_bitrate_mbps', r'tx bitrate: ([\d.]+) MBit/s'), ('freq_mhz', r'freq: ([\d.]+)')):
        match = re.search(pattern, text)
        if match:
            result[key] = float(match.group(1))
    return result


def parse_key_values(text):
    return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)


def is_wireless(name):
    return (NET / name / 'wireless').exists() or (NET / name / 'phy80211').exists()


def interface(name):
    base = NET / name
    if not base.exists():
        return None
    return {'name': name, 'operstate': read(base / 'operstate'), 'speed_mbps': read_int(base / 'speed'),
            'mtu': read_int(base / 'mtu'), 'duplex': read(base / 'duplex'),
            'medium': 'wireless' if is_wireless(name) else 'wired'}


def addresses(name=None):
    """Addresses per interface from `ip -j addr`: {interface: [address, ...]}."""
    status, out, _ = run(['ip', '-j', 'addr', 'show'] + (['dev', name] if name else []))
    if status != 0:
        return {}
    return {entry['ifname']: [info['local'] for info in entry.get('addr_info', [])] for entry in json.loads(out)}


def governors():
    return sorted({value for policy in CPUFREQ.glob('policy*') if (value := read(policy / 'scaling_governor'))})


def cpu_model():
    for line in (read('/proc/cpuinfo') or '').splitlines():
        if line.startswith(('model name', 'Model')):
            return line.split(':', 1)[1].strip()
    return platform.processor() or None


def mount_of(path):
    """The filesystem holding a path, or the one that would hold it once created."""
    present = pathlib.Path(path)
    while not present.exists() and present != present.parent:
        present = present.parent
    status, out, _ = run(['findmnt', '-J', '-T', str(present), '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS'])
    entry = json.loads(out)['filesystems'][0] if status == 0 else {}
    try:
        usage = os.statvfs(present)
        entry.update(free_bytes=usage.f_bavail * usage.f_frsize, total_bytes=usage.f_blocks * usage.f_frsize)
    except OSError as error:
        entry['error'] = str(error)
    entry.update(path=str(path), exists=os.path.isdir(path), writable=os.access(path, os.W_OK))
    return entry


def block_devices():
    for mounts in ('MOUNTPOINTS', 'MOUNTPOINT'):  # MOUNTPOINTS needs util-linux 2.37
        status, out, _ = run(['lsblk', '-J', '-b', '-o', f'NAME,TYPE,SIZE,FSTYPE,{mounts},MODEL,TRAN,ROTA'])
        if status == 0:
            return [device for device in json.loads(out)['blockdevices']
                    if not device['name'].startswith(('loop', 'zram', 'ram'))]
    return []


def tool_versions():
    result = {name: which(name) for name in TOOLS}
    status, out, _ = run(['rsync', '--version'])
    result['rsync_version'] = out.splitlines()[0] if status == 0 and out else None
    status, _, err = run(['ssh', '-V'])
    result['ssh_version'] = err.strip() if status == 0 else None
    return result


def helper_state():
    if not os.path.exists(HELPER):
        return {'installed': False}
    result = {'installed': True, 'sha256': hashlib.sha256(pathlib.Path(HELPER).read_bytes()).hexdigest()}
    status, out, err = run(['sudo', '-n', HELPER, 'status'])
    result['sudo'] = status == 0
    if status == 0:
        result['status'] = parse_key_values(out)
    else:
        result['error'] = err.strip()
    return result


def inventory(paths):
    system = platform.system()
    result = {'utc': utc(), 'hostname': socket.gethostname(), 'user': os.environ.get('USER'), 'system': system,
              'kernel': platform.release(), 'machine': platform.machine(), 'python': platform.python_version(),
              'cpus': os.cpu_count(), 'cpu_model': cpu_model(), 'tools': tool_versions(),
              'open_files_limit': resource.getrlimit(resource.RLIMIT_NOFILE)[0],
              'paths': [mount_of(path) for path in paths]}
    if system != 'Linux':
        result['note'] = 'only Linux endpoints are inventoried in full'
        return result
    os_release = parse_key_values(read('/etc/os-release') or '')
    policy = CPUFREQ / 'policy0'
    result.update({
        'os': os_release.get('PRETTY_NAME', '').strip('"'),
        'board': (read('/sys/firmware/devicetree/base/model') or '').rstrip('\x00') or None,
        'memory_bytes': parse_meminfo(read('/proc/meminfo') or '').get('MemTotal'),
        'cpufreq': {'driver': read(policy / 'scaling_driver'), 'governors': governors(),
                    'available': (read(policy / 'scaling_available_governors') or '').split(),
                    'max_khz': read_int(policy / 'cpuinfo_max_freq'),
                    'epp': read(policy / 'energy_performance_preference')},
        'thermal_zones': sorted(filter(None, (read(zone / 'type')
                                              for zone in pathlib.Path('/sys/class/thermal').glob('thermal_zone*')))),
        'interfaces': [interface(name) for name in sorted(os.listdir(NET)) if name != 'lo'],
        'addresses': addresses(),
        'default_qdisc': read('/proc/sys/net/core/default_qdisc'),
        'tcp_congestion_control': read('/proc/sys/net/ipv4/tcp_congestion_control'),
        'block_devices': block_devices(),
        'zfs': os.path.exists('/proc/spl/kstat/zfs/arcstats'),
        'systemd': os.path.isdir('/run/systemd/system'),
        'helper': helper_state(),
    })
    return result


def snapshot(name=None):
    result = {'utc': utc(), 'monotonic': time.monotonic(), 'hostname': socket.gethostname(),
              'loadavg': list(os.getloadavg())}
    if platform.system() != 'Linux':
        return result
    result['memory'] = parse_meminfo(read('/proc/meminfo') or '')
    result['cpu_jiffies'] = (read('/proc/stat') or '').splitlines()[:1]
    result['governors'] = governors()
    result['freq_khz'] = [value for policy in sorted(CPUFREQ.glob('policy*'))
                          if (value := read_int(policy / 'scaling_cur_freq')) is not None]
    result['temp_millic'] = {read(zone / 'type') or zone.name: value
                             for zone in sorted(pathlib.Path('/sys/class/thermal').glob('thermal_zone*'))
                             if (value := read_int(zone / 'temp')) is not None}
    status, out, _ = run(['vcgencmd', 'get_throttled'], timeout=5)
    if status == 0 and '=' in out:
        result['throttled'] = out.strip().split('=', 1)[1]
    result['tcp'] = parse_snmp_tcp(read('/proc/net/snmp') or '')
    arc = read('/proc/spl/kstat/zfs/arcstats')
    if arc:
        result['zfs_arc_bytes'] = next((int(fields[2]) for line in arc.splitlines()
                                        if (fields := line.split())[:1] == ['size']), None)
    if name:
        statistics = NET / name / 'statistics'
        result['interface'] = interface(name)
        result['counters'] = {key: read_int(statistics / key) for key in
                              ('rx_bytes', 'tx_bytes', 'rx_packets', 'tx_packets', 'rx_errors', 'tx_errors',
                               'rx_dropped', 'tx_dropped')}
        status, out, _ = run(['tc', 'qdisc', 'show', 'dev', name, 'root'], timeout=5)
        result['qdisc'] = out.strip().splitlines()[0] if status == 0 and out.strip() else None
        if is_wireless(name):
            status, out, _ = run(['iw', 'dev', name, 'link'], timeout=5)
            result['wireless'] = parse_iw_link(out) if status == 0 else {}
    return result


def route(peer, ssh_target, pings):
    """How this host reaches a peer: the address SSH uses, the interface it leaves by, and the delay."""
    result = {'utc': utc(), 'hostname': socket.gethostname(), 'peer': peer}
    try:
        resolved = sorted({info[4][0] for info in socket.getaddrinfo(peer, 22, proto=socket.IPPROTO_TCP)})
    except socket.gaierror as error:
        result['error'] = f'cannot resolve {peer}: {error}'
        return result
    result['resolved'] = resolved
    target = next((address for address in resolved if ':' not in address), resolved[0])
    if ssh_target:
        # The same client and target the transfers use, so this is the path they take.
        status, out, err = run(['ssh', '-oBatchMode=yes', '-oConnectTimeout=8', ssh_target,
                                'printf "%s\\n" "$SSH_CONNECTION"; hostname'], timeout=20)
        lines = out.splitlines()
        connection = parse_ssh_connection(lines[0]) if status == 0 and lines else None
        result['ssh'] = {'target': ssh_target, 'ok': bool(connection)}
        if connection:
            result['ssh'].update(connection, peer_hostname=lines[1] if len(lines) > 1 else None)
            target = connection['server_ip']
        else:
            result['ssh']['error'] = (err.strip() or 'no SSH_CONNECTION').splitlines()[-1]
    result['address'] = target
    status, out, err = run(['ip', '-j', 'route', 'get', target.split('%')[0]])
    if status == 0 and (hops := json.loads(out)):
        hop = hops[0]
        result.update(dev=hop.get('dev'), source=hop.get('prefsrc'), gateway=hop.get('gateway'))
        result['interface'] = interface(hop.get('dev', ''))
        result['interface_addresses'] = addresses(hop.get('dev')).get(hop.get('dev'), [])
        status, out, _ = run(['tc', 'qdisc', 'show', 'dev', hop.get('dev', ''), 'root'], timeout=5)
        result['qdisc'] = out.strip().splitlines()[0] if status == 0 and out.strip() else None
    else:
        result['error'] = (err.strip() or 'ip route get failed')
    if pings:
        status, out, _ = run(['ping', '-n', '-q', '-c', str(pings), '-i', '0.2', target], timeout=pings + 15)
        result['ping'] = parse_ping(out) if status is not None else {}
    return result


def file_sha256(path):
    try:
        digest = hashlib.sha256()
        with open(path, 'rb') as stream:
            while chunk := stream.read(1 << 20):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def staged(root, names):
    """Hashes of the named files under ROOT/bin, what each xs there says it is, and this host's rsync."""
    result = {'utc': utc(), 'hostname': socket.gethostname(), 'machine': platform.machine(),
              'files': {name: file_sha256(os.path.join(root, 'bin', name)) for name in names}, 'versions': {}}
    for name in names:
        if name.startswith('xs-') and result['files'][name]:
            status, out, _ = run([os.path.join(root, 'bin', name), '--version'], timeout=10)
            result['versions'][name] = out.splitlines()[0] if status == 0 and out else None
    rsync = which('rsync')
    status, out, _ = run(['rsync', '--version'])
    result['rsync'] = {'path': rsync, 'sha256': file_sha256(rsync) if rsync else None,
                       'version': out.splitlines()[0] if status == 0 and out else None}
    return result


def sample(name, interval, output):
    """Append one snapshot per interval until SIGTERM or SIGINT."""
    stop = []
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.append(True))
    with open(output, 'a', buffering=1) as stream:
        deadline = time.monotonic()
        while not stop:
            stream.write(json.dumps(snapshot(name)) + '\n')
            deadline += interval
            time.sleep(max(0.0, deadline - time.monotonic()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('inventory', help='static hardware, software and storage facts')
    p.add_argument('--path', action='append', default=[], help='directory whose filesystem to describe')
    p = commands.add_parser('snapshot', help='load, memory, frequency, temperature and interface counters')
    p.add_argument('--interface')
    p = commands.add_parser('route', help='how this host reaches a peer')
    p.add_argument('--peer', required=True, help='host name to resolve')
    p.add_argument('--ssh', help='SSH target to connect to, as the transfers will')
    p.add_argument('--pings', type=int, default=10)
    p = commands.add_parser('staged', help='hashes and versions of files staged under ROOT/bin')
    p.add_argument('--root', required=True)
    p.add_argument('names', nargs='+')
    p = commands.add_parser('sample', help='append snapshots at an interval until signalled')
    p.add_argument('--interface')
    p.add_argument('--interval', type=float, default=1.0)
    p.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    if args.command == 'inventory':
        result = inventory(args.path)
    elif args.command == 'snapshot':
        result = snapshot(args.interface)
    elif args.command == 'route':
        if args.peer.startswith('-') or (args.ssh or '').startswith('-'):
            parser.error('invalid peer')
        result = route(args.peer, args.ssh, args.pings)
    elif args.command == 'staged':
        if not args.root.startswith('/') or any('/' in name or name.startswith('.') for name in args.names):
            parser.error('staged needs an absolute root and plain file names')
        result = staged(args.root, args.names)
    else:
        if args.interval <= 0:
            parser.error('--interval must be positive')
        return sample(args.interface, args.interval, args.output)
    json.dump(result, sys.stdout)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
