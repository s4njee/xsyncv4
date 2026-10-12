#!/usr/bin/env python3
"""Check the lab's probes, preflight verdicts and the helper's argument guard."""
import copy
import datetime
import json
import math
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

import agent
import analyze
import corpus
import plan
import preflight
import probe
import report
import stage

HERE = pathlib.Path(__file__).resolve().parent
HELPER = HERE / 'xsbench-helper'
GOLDEN_DRAWS = (21844, 260, 5364032292144503359)

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


class Corpora(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name) / 'corpora'

    def generate(self, name, workers=1, replace=False):
        return corpus.generate(name, 'test', self.root, workers, replace)

    def test_draws_are_pinned(self):
        stream = corpus.Stream('golden')
        self.assertEqual((stream.bits(16), stream.below(1000), stream.bits(64)), GOLDEN_DRAWS)
        self.assertEqual((corpus.exp2(10 << 16), corpus.exp2((10 << 16) + 32768), corpus.exp2(-1)), (1024, 1536, 0))

    def test_every_named_corpus_matches_its_pinned_digest(self):
        pinned = json.loads((HERE / 'corpora.json').read_text())
        for name in corpus.SPECS:
            header = self.generate(name)
            self.assertEqual(header['digest'], pinned[f'{name}:test']['digest'], name)
            self.assertEqual(header['bytes'], pinned[f'{name}:test']['bytes'], name)

    def test_worker_count_does_not_change_the_corpus(self):
        first = self.generate('small-flat')['digest']
        self.assertEqual(self.generate('small-flat', workers=4, replace=True)['digest'], first)

    def test_deep_and_flat_hold_the_same_files(self):
        self.generate('small-flat')
        self.generate('small-deep')

        def files(label):
            lines = (self.root / f'{label}.files.jsonl').read_text().splitlines()
            return sorted((entry['size'], entry['data']) for entry in map(json.loads, lines) if entry['type'] == 'f')
        self.assertEqual(files('small-flat-test'), files('small-deep-test'))

    def test_verify_detects_content_time_and_extra_files(self):
        self.generate('small-flat')
        tree, manifest = self.root / 'small-flat-test', self.root / 'small-flat-test.manifest.json'
        self.assertTrue(corpus.verify(tree, manifest, False, 1)[0])
        victim = tree / 'd0000' / 'f0000000.txt'
        times, data = victim.stat(), bytearray(victim.read_bytes())
        data[0] ^= 1
        victim.write_bytes(data)
        os.utime(victim, ns=(times.st_atime_ns, times.st_mtime_ns))
        os.utime(victim.parent, (corpus.MTIME, corpus.MTIME))
        ok, _, different = corpus.verify(tree, manifest, False, 1)
        self.assertEqual((ok, different), (False, ['d0000/f0000000.txt']))
        self.assertTrue(corpus.verify(tree, manifest, True, 1)[0], 'a quick check does not read content')
        os.utime(victim, (corpus.MTIME + 99, corpus.MTIME + 99))
        self.assertFalse(corpus.verify(tree, manifest, True, 1)[0])
        (tree / 'd0000' / 'extra').write_text('x')
        self.assertIn('d0000/extra', corpus.verify(tree, manifest, True, 1)[2])

    def test_refuses_unowned_and_existing_destinations(self):
        self.root.mkdir(parents=True)
        (self.root / 'valuable').write_text('keep')
        with self.assertRaises(SystemExit):
            self.generate('tiny-one')
        self.assertEqual((self.root / 'valuable').read_text(), 'keep')
        (self.root / 'valuable').unlink()
        self.generate('tiny-one')
        with self.assertRaises(SystemExit):
            self.generate('tiny-one')
        with self.assertRaises(ValueError):
            self.generate('no-such-corpus')

    def test_real_tree_manifest_records_links(self):
        tree = pathlib.Path(self.tmp.name) / 'real'
        (tree / 'sub').mkdir(parents=True)
        (tree / 'sub' / 'a').write_bytes(b'payload')
        os.link(tree / 'sub' / 'a', tree / 'b')
        os.symlink('sub/a', tree / 'link')
        entries = {entry['path']: entry for entry in corpus.scan(tree, True, 1)}
        self.assertEqual(entries['link']['data'], 'sub/a')
        self.assertEqual(entries['sub/a']['link'], 'b')  # the later name points at the first
        self.assertIsNone(entries['b']['link'])
        self.assertEqual(entries['b']['data'], entries['sub/a']['data'])
        header = corpus.describe('real', 'real', tree, list(entries.values()))
        self.assertEqual((header['files'], header['directories'], header['symlinks'], header['hardlinks']),
                         (2, 1, 1, 1))
        self.assertEqual(corpus.digest_of(corpus.scan(tree, True, 1)), corpus.digest_of(corpus.scan(tree, True, 2)))
        inside = subprocess.run([sys.executable, str(HERE / 'corpus.py'), 'manifest', str(tree), '--name', 'real',
                                 '--output', str(tree / 'pin')], capture_output=True, text=True)
        self.assertIn('outside the tree', inside.stderr)


class StagedBuilds(unittest.TestCase):
    RECORD = {'rev12': 'abcdef012345', 'artifacts': {'xs-linux-arm64': {'sha256': 'arm'},
                                                    'xs-linux-amd64': {'sha256': 'amd'}}}
    SCRIPTS = {'probe.py': 'p', 'measure.py': 'm'}
    VERSION = 'xs  version 0.1.0  protocol version 4  git abcdef012345'

    def report(self, **changes):
        report = {'machine': 'aarch64', 'files': {'xs-abcdef012345': 'arm', 'probe.py': 'p', 'measure.py': 'm'},
                  'versions': {'xs-abcdef012345': self.VERSION},
                  'rsync': {'path': '/usr/bin/rsync', 'sha256': 'r', 'version': 'rsync  version 3.4.1'}}
        for key, value in changes.items():
            if isinstance(value, dict):
                report[key] = dict(report[key], **value)
            else:
                report[key] = value
        return report

    def problems(self, report):
        return stage.check_host('neo', self.RECORD, self.SCRIPTS, report)

    def test_recorded_build_passes(self):
        self.assertEqual(self.problems(self.report()), [])
        self.assertEqual(self.problems(self.report(machine='x86_64', files={'xs-abcdef012345': 'amd'})), [])

    def test_stale_binary_is_refused(self):
        problems = self.problems(self.report(files={'xs-abcdef012345': 'older build'}))
        self.assertEqual(problems, ['neo: xs-abcdef012345 is not the recorded build of abcdef012345 '
                                    '(stale or replaced)'])

    def test_binary_for_the_other_architecture_is_refused(self):
        self.assertTrue(any('stale or replaced' in p for p in self.problems(self.report(machine='x86_64'))))

    def test_missing_binary_is_refused(self):
        self.assertIn('neo: xs-abcdef012345 is not staged', self.problems(self.report(files={'xs-abcdef012345': None})))

    def test_dirty_or_other_revision_is_refused(self):
        dirty = self.report(versions={'xs-abcdef012345': self.VERSION + '-dirty'})
        self.assertTrue(any('built from a dirty tree' in p for p in self.problems(dirty)))
        other = self.report(versions={'xs-abcdef012345': self.VERSION.replace('abcdef012345', '111111111111')})
        self.assertTrue(any('expected git abcdef012345' in p for p in self.problems(other)))
        longer = self.report(versions={'xs-abcdef012345': self.VERSION + '9'})
        self.assertTrue(any('expected git abcdef012345' in p for p in self.problems(longer)))
        silent = self.report(versions={'xs-abcdef012345': None})
        self.assertTrue(any('does not run' in p for p in self.problems(silent)))

    def test_changed_or_missing_script_is_refused(self):
        self.assertIn('neo: probe.py differs from the working copy', self.problems(self.report(files={'probe.py': 'x'})))
        self.assertIn('neo: measure.py is not staged', self.problems(self.report(files={'measure.py': None})))

    def test_unsupported_host_and_probe_failure(self):
        self.assertEqual(self.problems(self.report(machine='riscv64')), ['neo: no build for a riscv64 host'])
        self.assertEqual(self.problems({'error': 'ssh timed out'}), ['neo: ssh timed out'])

    def test_only_commits_can_be_built(self):
        with self.assertRaises(SystemExit):
            stage.resolve('no-such-revision')
        self.assertEqual(len(stage.resolve('HEAD')), 40)

    def test_staged_probe_reports_hashes_and_refuses_paths(self):
        with tempfile.TemporaryDirectory() as root:
            (pathlib.Path(root) / 'bin').mkdir()
            (pathlib.Path(root) / 'bin' / 'probe.py').write_bytes(b'x')
            report = probe.staged(root, ['probe.py', 'absent'])
            self.assertEqual(report['files'], {
                'probe.py': '2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881', 'absent': None})
        result = subprocess.run([sys.executable, str(HERE / 'probe.py'), 'staged', '--root', '/tmp', '../etc/passwd'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


class Plans(unittest.TestCase):
    SPEC = {'id': 'E99', 'sha256': 'spec', 'kind': 'screening', 'hypothesis': 'h', 'primary': 'wall_s',
            'control': 'rsync', 'blocks': 4, 'verify': 'first-last',
            'arms': {'rsync': {'tool': 'rsync'}, 'fast': {'tool': 'rsync', 'flags': ['-a', '-W']},
                     'other': {'tool': 'rsync', 'flags': ['-rt']}},
            'matrix': {'link': 'lan', 'corpus': ['tiny-one', 'small-flat'], 'scenario': ['fresh', 'noop'],
                       'direction': ['neo>freya', 'freya>neo'], 'client': ['sender', 'receiver']}}

    def setUp(self):
        self.config = preflight.load(HERE / 'hosts.toml')
        self.pins = json.loads((HERE / 'corpora.json').read_text())

    def make(self, seed=1, **changes):
        return plan.make_plan(dict(self.SPEC, **changes), self.config, self.pins, seed, 'run')

    def test_every_block_holds_every_arm_once(self):
        made = self.make()
        self.assertEqual(len(made['cells']), 16)
        self.assertEqual(len(made['blocks']), 16 * 4)
        for block in made['blocks']:
            for order in block['orders']:
                self.assertEqual(sorted(order), ['fast', 'other', 'rsync'])

    def test_cells_are_interleaved_round_by_round(self):
        blocks = self.make()['blocks']
        for start in range(0, len(blocks), 16):
            round_ = blocks[start:start + 16]
            self.assertEqual(len({block['cell'] for block in round_}), 16)
            self.assertEqual({block['block'] for block in round_}, {start // 16})

    def test_order_depends_only_on_the_seed(self):
        self.assertEqual(self.make(seed=7)['blocks'], self.make(seed=7)['blocks'])
        self.assertNotEqual(self.make(seed=7)['blocks'], self.make(seed=8)['blocks'])
        orders = {tuple(block['orders'][0]) for block in self.make()['blocks']}
        self.assertGreater(len(orders), 3, 'arm order is not randomized')

    def test_first_and_last_blocks_are_verified_in_full(self):
        made = self.make()
        self.assertEqual({block['block'] for block in made['blocks'] if block['verify_full']}, {0, 3})
        self.assertTrue(all(block['verify_full'] for block in self.make(verify='full')['blocks']))

    def test_plan_names_pinned_corpora_and_declared_interfaces(self):
        made = self.make()
        self.assertEqual(made['corpora']['small-flat']['digest'], self.pins['small-flat:full']['digest'])
        self.assertEqual(made['hosts']['neo']['interface'], 'eth0')
        self.assertEqual(made['driver'], 'neo')
        self.assertIn('agent.py', made['scripts'])

    def test_injected_slowdown_is_a_share_of_the_baseline(self):
        arms = dict(self.SPEC['arms'], slow={'tool': 'rsync', 'inject_fraction': 0.06})
        with self.assertRaises(plan.SpecError):
            self.make(arms=arms)
        baseline = {cell['id']: 10.0 for cell in self.make()['cells']}
        made = plan.make_plan(dict(self.SPEC, arms=arms), self.config, self.pins, 1, 'run', baseline)
        slow = next(arm for arm in made['arms'] if arm['name'] == 'slow')
        self.assertEqual(set(slow['delay_s'].values()), {0.6})
        self.assertNotIn('delay_s', made['arms'][0])

    def test_bad_specs_are_rejected(self):
        for changes in ({'matrix': dict(self.SPEC['matrix'], corpus=['unpinned'])},
                        {'matrix': dict(self.SPEC['matrix'], direction=['neo>mars'])},
                        {'matrix': dict(self.SPEC['matrix'], scenario=['update-1pct'])},
                        {'matrix': dict(self.SPEC['matrix'], link='nowhere')}):
            with self.assertRaises(plan.SpecError, msg=changes):
                self.make(**changes)
        for text in ('id="x"\n', 'id="E1"\nhypothesis="h"\nkind="guess"\nprimary="wall_s"\ncontrol="a"\nblocks=1\n'
                     '[arms.a]\ntool="rsync"\n[arms.b]\ntool="rsync"\n[matrix]\n',
                     'id="E1"\nhypothesis="h"\nkind="screening"\nprimary="wall_s"\ncontrol="a"\nblocks=1\n'
                     '[arms.a]\ntool="rsync"\n[arms.b]\ntool="xs"\n[matrix]\n'):
            with tempfile.NamedTemporaryFile('w', suffix='.toml') as stream:
                stream.write(text)
                stream.flush()
                with self.assertRaises(plan.SpecError, msg=text):
                    plan.load_spec(stream.name)

    def test_checked_in_smoke_spec_loads(self):
        spec = plan.load_spec(HERE.parent / 'experiments' / 'E00-smoke.toml')
        self.assertEqual(spec['control'], 'rsync')


class AgentPieces(unittest.TestCase):
    def hosts(self):
        spec = lambda root, ssh: {'ssh': ssh, 'root': root, 'interface': 'eth0', 'helper': True}
        return {'neo': agent.Host('neo', spec('/n', 'u@neo.local'), True),
                'freya': agent.Host('freya', spec('/f', 'u@freya.local'), False)}

    CELL = {'id': 'tiny-one.fresh.neo-freya.sender.warm', 'corpus': 'tiny-one', 'scenario': 'fresh',
            'sender': 'neo', 'receiver': 'freya', 'client': 'sender', 'link': 'lan', 'cache': 'warm'}
    XS = {'name': 'xs', 'tool': 'xs', 'flags': ['-a'], 'binary': {'neo': '/n/bin/xs-r', 'freya': '/f/bin/xs-r'}}
    RSYNC = {'name': 'rsync', 'tool': 'rsync', 'flags': ['-a'], 'binary': {'neo': 'rsync', 'freya': 'rsync'}}

    def test_push_runs_on_the_sender_and_measures_both_ends(self):
        client, peer, argv, script = agent.transfer_command(self.XS, self.CELL, self.hosts(), 'run1', 'tag')
        self.assertEqual((client.name, peer.name), ('neo', 'freya'))
        self.assertEqual(argv[:3], ['env', 'XSYNC_CONFIG=', 'XSYNC_OPTS='])
        self.assertEqual(argv[3:8], ['python3', '/n/bin/measure.py', '--metrics', '/n/work/run1/logs/tag.client.json', '--'])
        self.assertEqual(argv[8:13], ['/n/bin/xs-r', '-a', '--stats', '--no-fallback', '--no-progress'])
        self.assertIn('--rsync-path=python3 /f/bin/measure.py --metrics /f/work/run1/logs/tag.peer.json -- /f/bin/xs-r', argv)
        self.assertEqual(argv[-2:], ['/n/corpora/tiny-one/',
                                     'u@freya.local:/f/work/run1/tiny-one.fresh.neo-freya.sender.warm/xs/'])
        self.assertTrue(script.endswith('> /n/work/run1/logs/tag.out 2> /n/work/run1/logs/tag.err'))

    def test_injected_delay_sleeps_inside_the_measured_command(self):
        arm = dict(self.XS, delay_s={self.CELL['id']: 0.25})
        _, _, argv, _ = agent.transfer_command(arm, self.CELL, self.hosts(), 'run1', 'tag')
        start = argv.index('--') + 1
        self.assertEqual(argv[start:start + 6], ['sh', '-c', 'sleep "$0"; exec "$@"', '0.2500', '/n/bin/xs-r', '-a'])
        _, _, plain, _ = agent.transfer_command(self.XS, self.CELL, self.hosts(), 'run1', 'tag')
        self.assertNotIn('sh', plain)

    def test_pull_runs_on_the_receiver(self):
        cell = dict(self.CELL, client='receiver')
        client, peer, argv, _ = agent.transfer_command(self.RSYNC, cell, self.hosts(), 'run1', 'tag')
        self.assertEqual((client.name, peer.name), ('freya', 'neo'))
        self.assertNotIn('--no-fallback', argv)
        self.assertEqual(argv[-2:], ['u@neo.local:/n/corpora/tiny-one/',
                                     '/f/work/run1/tiny-one.fresh.neo-freya.sender.warm/rsync/'])
        self.assertIn('--rsync-path=python3 /n/bin/measure.py --metrics /n/work/run1/logs/tag.peer.json -- rsync', argv)

    def test_work_paths_stay_inside_the_owned_directory(self):
        host = self.hosts()['freya']
        self.assertEqual(agent.work_path(host, 'run1', 'cell.a', 'xs'), '/f/work/run1/cell.a/xs')
        for parts in (('..',), ('a/b',), ('',), ('-rf',), ('run1', '..')):
            with self.assertRaises(ValueError, msg=parts):
                agent.work_path(host, *parts)

    def test_stats_are_parsed(self):
        text = ('\nNumber of files: 10,103 (reg: 10,002, dir: 101)\nNumber of regular files transferred: 10,002\n'
                'Total file size: 578,000 bytes\nTotal bytes sent: 1,234\nTotal bytes received: 56\n'
                'File list generation time: 0.001 seconds\n\nsent 1,234 bytes  received 56 bytes  2.00 bytes/sec\n')
        self.assertEqual(agent.parse_stats(text), {
            'number_of_files': 10103, 'number_of_regular_files_transferred': 10002, 'total_file_size': 578000,
            'total_bytes_sent': 1234, 'total_bytes_received': 56, 'file_list_generation_time': 0.001})

    def test_gates(self):
        host = self.hosts()['neo']
        idle = {'cpu_jiffies': ['cpu  100 0 100 1000 0 0 0 0 0 0'], 'memory': {'Dirty': 0, 'Writeback': 0},
                'temp_millic': {'cpu-thermal': 50000}, 'throttled': '0x0'}
        later = lambda **changes: {**idle, 'cpu_jiffies': ['cpu  101 0 101 1098 0 0 0 0 0 0'], **changes}
        self.assertAlmostEqual(agent.busy_fraction(idle['cpu_jiffies'][0], later()['cpu_jiffies'][0]), 0.02)
        self.assertIsNone(agent.gate_problem(host, idle, later()))
        self.assertIn('busy', agent.gate_problem(host, idle, later(cpu_jiffies=['cpu  150 0 150 1000 0 0 0 0 0 0'])))
        self.assertIn('dirty', agent.gate_problem(host, idle, later(memory={'Dirty': 64 << 20, 'Writeback': 0})))
        self.assertIn('at 81 C', agent.gate_problem(host, idle, later(temp_millic={'cpu-thermal': 81000})))
        self.assertIn('throttled', agent.gate_problem(host, idle, later(throttled='0x4')))

    def test_throttling_during_a_sample_voids_it(self):
        host = self.hosts()['neo']
        self.assertIsNone(agent.throttle_problem(host, {'throttled': '0x50000'}, {'throttled': '0x50000'}))
        self.assertIsNone(agent.throttle_problem(host, {}, {}))
        self.assertIn('throttled during', agent.throttle_problem(host, {'throttled': '0x0'}, {'throttled': '0x40000'}))
        self.assertIn('throttled during', agent.throttle_problem(host, {'throttled': '0x0'}, {'throttled': '0x4'}))


class Statistics(unittest.TestCase):
    def test_t_quantiles_match_tables(self):
        for probability, df, expected in ((0.975, 1, 12.706205), (0.975, 7, 2.364624), (0.975, 11, 2.200985),
                                          (0.975, 30, 2.042272), (0.995, 7, 3.499483), (0.975, 1000, 1.962339)):
            self.assertAlmostEqual(analyze.t_quantile(probability, df), expected, places=5)
        self.assertAlmostEqual(analyze.t_cdf(0.0, 5), 0.5)
        self.assertAlmostEqual(analyze.t_cdf(-2.570582, 5), 0.025, places=6)

    def test_signed_rank_distribution_is_exact(self):
        self.assertEqual(analyze.signed_rank_cdf(6)[:3], [1 / 64, 2 / 64, 3 / 64])
        self.assertEqual(analyze.signed_rank_cdf(8)[3], 5 / 256)
        self.assertEqual(analyze.signed_rank_cdf(10)[-1], 1.0)

    def test_hodges_lehmann(self):
        estimate, low, high = analyze.hodges_lehmann([0.05, 0.02, 0.08, 0.01, 0.06, 0.03, 0.04, 0.07], 0.05)
        self.assertAlmostEqual(estimate, 0.045)
        self.assertAlmostEqual(low, 0.02)
        self.assertAlmostEqual(high, 0.07)
        self.assertEqual(analyze.hodges_lehmann([0.1, 0.2, 0.3, 0.4, 0.5], 0.05)[1:], (None, None),
                         'five blocks cannot give a 95% interval')
        self.assertIsNotNone(analyze.hodges_lehmann([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], 0.05)[1])

    def test_sign_flip_p_is_exact(self):
        self.assertEqual(analyze.sign_flip_p([0.05, 0.02, 0.08, 0.01, 0.06, 0.03, 0.04, 0.07]), 2 / 256)
        self.assertEqual(analyze.sign_flip_p([1.0, -1.0]), 1.0)
        self.assertEqual(analyze.sign_flip_p([0.3, 0.1, -0.2]), 0.75)
        many = analyze.sign_flip_p([0.01 * (1 + index % 3) for index in range(24)])
        self.assertLess(many, 1e-4, 'sampled above twenty blocks')

    def test_classification_against_delta(self):
        self.assertEqual(analyze.classify(0.90, 0.96, 0.03), 'faster')
        self.assertEqual(analyze.classify(1.04, 1.10, 0.03), 'slower')
        self.assertEqual(analyze.classify(0.98, 1.02, 0.03), 'equivalent')
        self.assertEqual(analyze.classify(0.96, 1.01, 0.03), 'inconclusive')
        self.assertEqual(analyze.classify(0.90, 0.975, 0.03), 'inconclusive', 'real but inside delta')

    def test_comparison_and_minimum_blocks(self):
        steady = [math.log(0.9) + shift for shift in (-.010, .012, -.004, .006, .0, .003, -.008, .009)]
        result = analyze.compare(steady, 0.03)
        self.assertEqual(result['verdict'], 'faster')
        self.assertAlmostEqual(result['ratio'], 0.9009, places=4)
        self.assertLess(result['lo'], result['ratio'])
        self.assertLess(result['hi'], 1 / 1.03)
        self.assertEqual(analyze.compare(steady[:7], 0.03)['verdict'], 'too few blocks')
        self.assertEqual(analyze.compare(steady[:1], 0.03)['verdict'], 'too few blocks')
        wild = steady[:7] + [math.log(3.0)]  # one block three times slower
        self.assertEqual(analyze.compare(wild, 0.03)['verdict'], 'inconclusive')

    def test_holm(self):
        for found, expected in zip(analyze.holm([0.01, 0.04, 0.03, 0.005]), [0.03, 0.06, 0.06, 0.02]):
            self.assertAlmostEqual(found, expected)
        self.assertEqual(analyze.holm([0.5, 0.9]), [1.0, 1.0])

    def test_block_counts_match_the_plan(self):
        self.assertEqual([analyze.blocks_needed(sigma, delta) for sigma, delta in
                          ((0.02, 0.02), (0.05, 0.03), (0.10, 0.05), (0.20, 0.10), (0.02, 0.10))],
                         [10, 25, 35, 37, 8])
        self.assertGreater(analyze.blocks_for_equivalence(0.05, 0.03), analyze.blocks_needed(0.05, 0.03))


class Analysis(unittest.TestCase):
    """A whole synthetic experiment through load, analyse, write and render."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.experiment = pathlib.Path(self.tmp.name) / 'E98'

    def run_directory(self, run_id, ratios, kind='confirmatory', void_last=False):
        directory = self.experiment / run_id
        directory.mkdir(parents=True)
        cell = {'id': 'c1', 'corpus': 'small-flat', 'scenario': 'fresh', 'sender': 'neo', 'receiver': 'freya',
                'client': 'sender', 'link': 'lan', 'cache': 'warm'}
        (directory / 'plan.json').write_text(json.dumps({
            'experiment': 'E98', 'run_id': run_id, 'spec_sha256': 's', 'kind': kind, 'hypothesis': 'h',
            'primary': 'wall_s', 'control': 'rsync', 'delta': 0.03, 'cells': [cell],
            'arms': [{'name': 'rsync'}, {'name': 'xs'}]}))
        samples, blocks = [], []
        for number, ratio in enumerate(ratios):
            valid = not (void_last and number == len(ratios) - 1)
            base = 10.0 * (1 + 0.2 * (number % 3))  # drift between blocks, shared by both arms
            for arm, wall in (('rsync', base), ('xs', base * ratio)):
                ends = {'user_seconds': 1.0, 'system_seconds': 1.0, 'max_rss_bytes': 1 << 20}
                samples.append({'run_id': run_id, 'cell_id': 'c1', 'block': number, 'attempt': 0, 'arm': arm,
                                'valid': valid, 'wall_s': wall, 'durable_s': wall + 1.0, 'client': ends, 'peer': ends,
                                'stats': {'total_bytes_sent': 10, 'total_bytes_received': 1}})
            blocks.append({'cell_id': 'c1', 'block': number, 'attempt': 0, 'valid': valid,
                           'void_reason': None if valid else 'neo throttled during the sample'})
        (directory / 'samples.jsonl').write_text(''.join(json.dumps(sample) + '\n' for sample in samples))
        (directory / 'blocks.jsonl').write_text(''.join(json.dumps(block) + '\n' for block in blocks))

    RATIOS = (0.90, 0.91, 0.89, 0.905, 0.895, 0.90, 0.91, 0.89, 0.90, 0.905)

    def test_drift_cancels_and_blocks_pool_across_runs(self):
        self.run_directory('r1', self.RATIOS[:5])
        self.run_directory('r2', self.RATIOS[5:])
        result = analyze.analyse(analyze.run_directories(self.experiment))
        row = next(row for row in result['effects'] if row['primary'])
        self.assertEqual((row['n_blocks'], row['verdict'], row['corpus'], row['link']), (10, 'faster', 'small-flat', 'lan'))
        self.assertAlmostEqual(row['ratio'], 0.9005, places=3)
        self.assertLess(row['hi'] - row['lo'], 0.02, 'a 20% drift between blocks must not widen the interval')
        self.assertAlmostEqual(row['err_plus'], row['hi'] - row['ratio'])
        self.assertEqual(row['p_holm'], row['p'])
        self.assertEqual(len(result['pairs']), 10)
        self.assertEqual({row['verdict'] for row in result['effects'] if not row['primary']}, {'descriptive'})
        absolute = {row['arm']: row for row in result['absolutes'] if row['metric'] == 'wall_s'}
        self.assertGreater(absolute['rsync']['geomean'], absolute['xs']['geomean'])

    def test_another_arm_can_be_the_control(self):
        self.run_directory('r1', self.RATIOS)
        result = analyze.analyse(analyze.run_directories(self.experiment), control='xs')
        row = next(row for row in result['effects'] if row['primary'])
        self.assertEqual((row['arm'], row['control']), ('rsync', 'xs'))
        self.assertAlmostEqual(row['ratio'], 1 / 0.9005, places=2)
        self.assertEqual(analyze.output_name('analysis', 'xs'), 'analysis-vs-xs')
        with self.assertRaises(SystemExit):
            analyze.analyse(analyze.run_directories(self.experiment), control='absent')

    def test_void_blocks_are_excluded_and_reported(self):
        self.run_directory('r1', self.RATIOS + (5.0,), void_last=True)
        result = analyze.analyse(analyze.run_directories(self.experiment))
        row = next(row for row in result['effects'] if row['primary'])
        self.assertEqual(row['n_blocks'], 10)
        self.assertEqual(result['summary']['void_attempts'], 1)
        self.assertIn('neo throttled during the sample', result['summary']['void_reasons'])

    def test_tables_and_report_are_written(self):
        self.run_directory('r1', self.RATIOS)
        result = analyze.analyse(analyze.run_directories(self.experiment))
        analyze.write(result, self.experiment / 'analysis')
        header = (self.experiment / 'analysis' / 'effects.csv').read_text().splitlines()[0].split(',')
        for column in ('corpus', 'scenario', 'sender', 'receiver', 'client', 'link', 'cache', 'arm', 'ratio', 'lo',
                       'hi', 'err_minus', 'err_plus', 'n_blocks', 'p', 'p_holm', 'verdict'):
            self.assertIn(column, header)
        text = report.render(result)
        self.assertIn('| `c1` | xs | 10 | 0.900 [', text)
        self.assertIn('faster', text)
        self.assertIn('p (Holm)', text)
        self.run_directory('r2', self.RATIOS[:3], kind='screening')
        few = report.render(analyze.analyse([self.experiment / 'r2']))
        self.assertIn('estimates only, no verdict', few)
        self.assertIn('nothing here is a claim', few)


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
