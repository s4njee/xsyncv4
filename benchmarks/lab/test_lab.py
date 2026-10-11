#!/usr/bin/env python3
"""Check the lab's probes, preflight verdicts and the helper's argument guard."""
import copy
import datetime
import os
import pathlib
import subprocess
import tempfile
import unittest

import preflight
import probe

HERE = pathlib.Path(__file__).resolve().parent
HELPER = HERE / 'xsbench-helper'

HOSTS = {'neo': {'ssh': 'u@neo.local', 'name': 'neo.local', 'hostname': 'neo', 'root': '/bench',
                 'root_fstype': 'ext4', 'helper': True},
         'freya': {'ssh': 'u@freya.local', 'name': 'freya.local', 'hostname': 'freya', 'root': '/mnt/nvme/x',
                   'root_fstype': 'ext4', 'helper': True}}
LINK = {'hosts': ['neo', 'freya'], 'medium': 'wired', 'min_speed_mbps': 1000, 'max_rtt_ms': 2.0,
        'interface': {'neo': 'eth0', 'freya': 'enp10s0'}}
ROUTE = {'hostname': 'neo', 'peer': 'freya.local', 'resolved': ['192.168.1.156'], 'address': '192.168.1.156',
         'ssh': {'target': 'u@freya.local', 'ok': True, 'client_ip': '192.168.1.219', 'client_port': 4,
                 'server_ip': '192.168.1.156', 'server_port': 22, 'peer_hostname': 'freya'},
         'dev': 'eth0', 'source': '192.168.1.219',
         'interface': {'name': 'eth0', 'operstate': 'up', 'speed_mbps': 1000, 'mtu': 1500, 'medium': 'wired'},
         'interface_addresses': ['192.168.1.219'], 'qdisc': 'qdisc fq_codel 0: root refcnt 2',
         'ping': {'loss_pct': 0.0, 'rtt_avg_ms': 0.36}}
NOW = datetime.datetime(2026, 10, 11, 22, 0, tzinfo=datetime.timezone.utc)
INVENTORY = {'utc': '2026-10-11T22:00:00.500+00:00', 'hostname': 'neo', 'system': 'Linux',
             'tools': {'rsync': '/usr/bin/rsync', 'ip': '/usr/bin/ip', 'tc': '/usr/sbin/tc',
                       'ping': '/usr/bin/ping', 'findmnt': '/usr/bin/findmnt'},
             'paths': [{'path': '/bench', 'exists': True, 'writable': True, 'fstype': 'ext4'}],
             'helper': {'installed': True, 'sha256': preflight.helper_sha256(), 'sudo': True,
                        'status': {'config': 'ok', 'netem': 'off', 'netem_timer': 'off', 'governor_saved': 'no'}}}


def route(**changes):
    report = copy.deepcopy(ROUTE)
    for key, value in changes.items():
        if isinstance(value, dict):
            report[key].update(value)
        else:
            report[key] = value
    return report


def inventory(**changes):
    report = copy.deepcopy(INVENTORY)
    report.update(changes)
    return report


class RouteVerdicts(unittest.TestCase):
    def problems(self, report, link=LINK):
        return preflight.check_route('lan', link, 'neo', 'freya', HOSTS, report)

    def test_declared_path_passes(self):
        self.assertEqual(self.problems(route()), [])

    def test_wrong_interface_fails(self):
        link = dict(LINK, interface={'neo': 'wlan0', 'freya': 'enp10s0'})
        self.assertIn('lan neo->freya: traffic leaves by eth0, declared wlan0', self.problems(route(), link))

    def test_undeclared_interface_fails(self):
        link = dict(LINK, interface={'freya': 'enp10s0'})
        self.assertTrue(any('no interface is declared for neo' in p for p in self.problems(route(), link)))

    def test_wireless_interface_on_wired_link_fails(self):
        problems = self.problems(route(dev='wlan0', interface={'name': 'wlan0', 'medium': 'wireless',
                                                               'speed_mbps': None}))
        self.assertTrue(any('wlan0 is wireless, the link is declared wired' in p for p in problems))

    def test_mesh_link_accepts_either_medium(self):
        link = dict(LINK, medium='mesh', min_speed_mbps=0, max_rtt_ms=0, interface={'neo': 'wlan0'})
        report = route(dev='wlan0', interface={'name': 'wlan0', 'medium': 'wireless', 'speed_mbps': None})
        self.assertEqual(self.problems(report, link), [])

    def test_stale_address_reaching_another_host_fails(self):
        problems = self.problems(route(ssh={'peer_hostname': 'mars'}))
        self.assertIn('lan neo->freya: reached a host called mars, expected freya', problems)

    def test_ssh_failure_fails(self):
        problems = self.problems(route(ssh={'ok': False, 'error': 'Permission denied (publickey).'}))
        self.assertTrue(any('neo cannot SSH to freya: Permission denied' in p for p in problems))

    def test_connection_from_another_interface_fails(self):
        problems = self.problems(route(ssh={'client_ip': '10.0.0.7'}))
        self.assertTrue(any('10.0.0.7, which is not on eth0' in p for p in problems))

    def test_degraded_link_fails(self):
        self.assertTrue(any('negotiated 100 Mb/s' in p for p in self.problems(route(interface={'speed_mbps': 100}))))
        self.assertTrue(any('round trip averages 5.3 ms' in p for p in self.problems(route(ping={'rtt_avg_ms': 5.3}))))
        self.assertTrue(any('pings were lost' in p for p in self.problems(route(ping={'loss_pct': 10.0}))))

    def test_leftover_netem_fails(self):
        problems = self.problems(route(qdisc='qdisc netem 8001: root refcnt 2 limit 100000 delay 20ms'))
        self.assertTrue(any('netem qdisc' in p for p in problems))

    def test_probe_error_is_the_only_problem(self):
        self.assertEqual(self.problems({'error': 'cannot resolve freya.local'}),
                         ['lan neo->freya: cannot resolve freya.local'])


class InventoryVerdicts(unittest.TestCase):
    def problems(self, report, host=HOSTS['neo']):
        return preflight.check_inventory('neo', host, report, NOW)

    def test_ready_host_passes(self):
        self.assertEqual(self.problems(inventory()), [])

    def test_wrong_host_fails(self):
        self.assertTrue(any('called orion, expected neo' in p for p in self.problems(inventory(hostname='orion'))))

    def test_clock_skew_fails(self):
        problems = self.problems(inventory(utc='2026-10-11T22:00:09+00:00'))
        self.assertTrue(any('clock differs from the controller by 9.0 s' in p for p in problems))

    def test_root_must_exist_be_writable_and_on_the_declared_filesystem(self):
        for path, expected in (({'exists': False}, 'does not exist'), ({'writable': False}, 'not writable'),
                               ({'fstype': 'zfs'}, 'is on zfs, expected ext4')):
            report = inventory(paths=[dict(INVENTORY['paths'][0], **path)])
            self.assertTrue(any(expected in p for p in self.problems(report)), expected)
        self.assertTrue(any('no benchmark root' in p for p in self.problems(inventory(), dict(HOSTS['neo'], root=''))))

    def test_helper_states_fail(self):
        cases = (({'installed': False}, 'is not installed'),
                 ({'sha256': 'stale'}, 'differs from benchmarks/lab/xsbench-helper'),
                 ({'sudo': False, 'error': 'a password is required'}, 'a password is required'),
                 ({'status': {'config': '/etc/xsbench-helper.conf is missing'}}, 'is missing'),
                 ({'status': dict(INVENTORY['helper']['status'], netem='on')}, 'netem qdisc or its timer'),
                 ({'status': dict(INVENTORY['helper']['status'], governor_saved='yes')}, 'left the governor'))
        for change, expected in cases:
            report = inventory(helper=dict(INVENTORY['helper'], **change))
            self.assertTrue(any(expected in p for p in self.problems(report)), expected)

    def test_missing_tool_fails(self):
        report = inventory(tools=dict(INVENTORY['tools'], tc=None))
        self.assertIn('neo: tc is not installed', self.problems(report))

    def test_unreachable_host_is_one_problem(self):
        self.assertEqual(self.problems({'error': 'ssh: connect timed out'}), ['neo: ssh: connect timed out'])


class Configuration(unittest.TestCase):
    def load(self, text):
        with tempfile.NamedTemporaryFile('w', suffix='.toml') as stream:
            stream.write(text)
            stream.flush()
            return preflight.load(stream.name)

    def test_checked_in_hosts_file_loads(self):
        config = preflight.load(HERE / 'hosts.toml')
        self.assertEqual(config['links']['lan']['hosts'], ['neo', 'freya'])

    def test_bad_entries_are_rejected(self):
        host = '[hosts.a]\nssh="u@a"\nname="a.local"\nhostname="a"\n'
        peer = '[hosts.b]\nssh="u@b"\nname="b.local"\nhostname="b"\n'
        for text in ('[hosts.a]\nssh="-oProxyCommand=x"\nname="a"\nhostname="a"\n',
                     host + 'root="relative"\n',
                     host + '[links.l]\nhosts=["a","missing"]\nmedium="wired"\n',
                     host + peer + '[links.l]\nhosts=["a","b"]\nmedium="fibre"\n',
                     host + peer + '[links.l]\nhosts=["a","b"]\nmedium="wired"\ninterface={c="eth0"}\n'):
            with self.assertRaises(preflight.ConfigError, msg=text):
                self.load(text)


class Parsers(unittest.TestCase):
    def test_meminfo_is_in_bytes(self):
        text = 'MemTotal:        4142208 kB\nDirty:               12 kB\nHugePages_Total:       0\n'
        self.assertEqual(probe.parse_meminfo(text), {'MemTotal': 4142208 * 1024, 'Dirty': 12 * 1024})

    def test_tcp_counters(self):
        text = ('Ip: Forwarding DefaultTTL\nIp: 1 64\n'
                'Tcp: RtoAlgorithm InSegs OutSegs RetransSegs InErrs OutRsts\nTcp: 1 10 20 3 0 4\n')
        self.assertEqual(probe.parse_snmp_tcp(text),
                         {'InSegs': 10, 'OutSegs': 20, 'RetransSegs': 3, 'InErrs': 0, 'OutRsts': 4})

    def test_ping_summaries(self):
        linux = '5 packets transmitted, 5 received, 0% packet loss, time 804ms\nrtt min/avg/max/mdev = 0.323/0.362/0.410/0.029 ms\n'
        self.assertEqual(probe.parse_ping(linux), {'loss_pct': 0.0, 'rtt_min_ms': 0.323, 'rtt_avg_ms': 0.362,
                                                   'rtt_max_ms': 0.41, 'rtt_mdev_ms': 0.029})
        self.assertEqual(probe.parse_ping('5 packets transmitted, 0 received, 100% packet loss, time 4s\n'),
                         {'loss_pct': 100.0})

    def test_ssh_connection(self):
        self.assertEqual(probe.parse_ssh_connection('192.168.1.219 49296 192.168.1.156 22\n'),
                         {'client_ip': '192.168.1.219', 'client_port': 49296,
                          'server_ip': '192.168.1.156', 'server_port': 22})
        self.assertIsNone(probe.parse_ssh_connection(''))

    def test_wireless_link(self):
        text = ('Connected to aa:bb:cc:dd:ee:ff (on wlan0)\n\tfreq: 5180.0\n\tsignal: -52 dBm\n'
                '\trx bitrate: 866.7 MBit/s VHT-MCS 9\n\ttx bitrate: 650.0 MBit/s VHT-MCS 7\n')
        self.assertEqual(probe.parse_iw_link(text), {'connected': True, 'signal_dbm': -52.0, 'freq_mhz': 5180.0,
                                                     'rx_bitrate_mbps': 866.7, 'tx_bitrate_mbps': 650.0})
        self.assertEqual(probe.parse_iw_link('Not connected.\n'), {'connected': False})

    def test_snapshot_and_inventory_run_here(self):
        self.assertIn('loadavg', probe.snapshot())
        self.assertIn('tools', probe.inventory([str(HERE)]))


class HelperArguments(unittest.TestCase):
    """Bad arguments are rejected before anything is done, whoever calls."""

    def run_helper(self, *arguments):
        return subprocess.run(['sh', str(HELPER), *arguments], capture_output=True, text=True, timeout=20)

    def test_malformed_requests_are_usage_errors(self):
        for arguments in ((), ('bogus',), ('status', 'extra'), ('governor', 'fast'), ('netem',),
                          ('netem', 'set', '5', '0'), ('netem', 'set', '5', '0', '10', 'eth1'),
                          ('netem', 'set', 'x', '0', '10'), ('netem', 'set', '-5', '0', '10'),
                          ('netem', 'set', '5; reboot', '0', '10'), ('netem', 'set', '5', '101', '10'),
                          ('netem', 'set', '5', '1.234', '10'), ('netem', 'set', '5', '0', '0'),
                          ('netem', 'set', '5', '0', '3601'), ('netem', 'set', '1001', '0', '10'),
                          ('netem', 'clear', 'eth1'), ('mount-scratch', '/dev/sda1'), ('drop-caches', '1')):
            result = self.run_helper(*arguments)
            self.assertEqual(result.returncode, 2, arguments)
            self.assertEqual(result.stdout, '', arguments)

    @unittest.skipIf(os.geteuid() == 0, 'as root these would act on this machine')
    def test_valid_requests_need_root(self):
        for arguments in (('drop-caches',), ('governor', 'performance'), ('governor', 'restore'),
                          ('netem', 'set', '20', '0.5', '60'), ('netem', 'clear'), ('mount-scratch',)):
            result = self.run_helper(*arguments)
            self.assertEqual(result.returncode, 4, arguments)
            self.assertIn('must run as root', result.stderr)

    def test_status_never_needs_root(self):
        result = self.run_helper('status')
        self.assertEqual(result.returncode, 0)
        self.assertIn('version=1', result.stdout)


if __name__ == '__main__':
    unittest.main()
