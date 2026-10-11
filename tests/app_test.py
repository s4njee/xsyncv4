#!/usr/bin/env python3
"""Schema-1 subprocess acceptance: framing, byte paths, lifecycle and isolation."""
import json
import errno
import os
import pathlib
import select
import signal
import sys
import subprocess
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', ROOT / 'build/xs')).resolve()


def endpoint(path, kind='local'):
    return {'kind': kind, 'path': {'bytes_hex': os.fsencode(path).hex()}}


def copy_request(source, destination, mode='contents', policy='replace', **options):
    return {'id': 'copy', 'op': 'copy', 'sources': [{'endpoint': endpoint(source), 'mode': mode}],
            'destination': endpoint(destination), 'options': {
                'on_conflict': policy, 'preserve_times': True, 'preserve_permissions': True, **options}}


def inventory(events, request_id='copy'):
    sys.path.insert(0, str(ROOT / 'tools'))
    from app_client import TransferInventory
    view = TransferInventory(request_id)
    for event in events:
        view.accept(event)
    return view


class Client:
    def __init__(self, env=None, prefix=()):
        self.proc = subprocess.Popen([*prefix, str(BINARY), '--app'], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=env, start_new_session=True)
        self.pending = b''
        self.events = []
        self.send({'id': 'hello', 'op': 'hello', 'schema': '1'})
        self.capabilities = self.read()

    def send(self, message):
        self.proc.stdin.write(json.dumps(message).encode() + b'\n')
        self.proc.stdin.flush()

    def read(self, timeout=10):
        deadline = time.monotonic() + timeout
        while b'\n' not in self.pending:
            wait = deadline - time.monotonic()
            if wait <= 0 or not select.select([self.proc.stdout], [], [], max(0, wait))[0]:
                raise AssertionError('timed out waiting for event')
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                raise AssertionError('EOF before result: ' + self.proc.stderr.read().decode(errors='replace'))
            self.pending += chunk
        line, self.pending = self.pending.split(b'\n', 1)
        event = json.loads(line)
        self.events.append(event)
        return event

    def finish(self, timeout=10):
        while True:
            event = self.read(timeout)
            if event['type'] == 'result':
                self.proc.wait(timeout=timeout)
                return event

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            stream.close()


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xs-app-fault-')
        cls.addClassCleanup(cls.library_tmp.cleanup)
        cls.fault = pathlib.Path(cls.library_tmp.name) / 'fault_io.so'
        args = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                '-fPIC', str(ROOT / 'tests/fault_io.cpp'), '-o', str(cls.fault)]
        if sys.platform != 'darwin': args += ['-ldl']
        subprocess.run(args, check=True, capture_output=True)
        cls.deny = pathlib.Path(cls.library_tmp.name) / 'deny-syscall'
        if sys.platform.startswith('linux'):
            subprocess.run(['c++', '-std=c++20', str(ROOT / 'tests/deny_syscall.cpp'), '-o', str(cls.deny)],
                           check=True, capture_output=True)

    def fault_env(self, path, **settings):
        return dict(os.environ, **{
            'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD': str(self.fault),
            'XSYNC_FAULT_PATH': str(path.resolve()), **settings})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-app-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.dest = self.root / 'destination'
        self.dest.mkdir()

    def client(self, env=None, prefix=()):
        c = Client(env, prefix)
        self.addCleanup(c.close)
        self.assertEqual(c.capabilities['type'], 'capabilities')
        return c

    def job(self, request, env=None):
        c = self.client(env)
        c.send(request)
        result = c.finish()
        sequence = [int(e['seq']) for e in c.events]
        self.assertEqual(sequence, list(range(1, len(sequence)+1)))
        self.assertEqual(sum(e['type'] == 'result' for e in c.events), 1)
        self.assertTrue(all(e['id'] == request['id'] for e in c.events[1:]))
        return c, result

    def test_probe_negotiation_and_shutdown(self):
        c = self.client()
        self.assertEqual(c.capabilities['endpoint_kinds'], ['local', 'ssh'])
        self.assertEqual(c.capabilities['copy_endpoint_kinds'], ['local', 'ssh'])
        self.assertFalse(c.capabilities['fallback'])
        c.send({'id': 'probe', 'op': 'probe'})
        self.assertEqual(c.read()['backend'], 'native-local')
        c.send({'id': 'exit', 'op': 'shutdown'})
        self.assertEqual(c.finish()['status'], 'success')

    def test_incompatible_schema_before_writes(self):
        for schema in ('2', 1):
            p = subprocess.run([str(BINARY), '--app'], input=json.dumps(
                {'id': 'hello', 'op': 'hello', 'schema': schema}).encode()+b'\n', capture_output=True, timeout=5)
            events = [json.loads(line) for line in p.stdout.splitlines()]
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(events[-1]['status'], 'failure')
            self.assertEqual(list(self.dest.iterdir()), [])

    def test_native_bridge_revalidates_paths_and_options_before_writes(self):
        import struct
        import wire_test as wire
        protected = self.root / 'outside'
        protected.mkdir()
        (protected / 'keep').write_text('good')
        features = 1 | 32 | 64 | 1024 | 2147483648 | 34359738368 | 68719476736
        for case in ('path', 'deletion', 'jobs', 'features', 'path_count', 'oversized'):
            with self.subTest(case=case):
                c = self.client()
                c.send({'id': 'bridge', 'op': '_native_transfer', 'role': 'receiver',
                        'destination': endpoint(self.dest), 'idle_timeout_seconds': '0',
                        'options': {'on_conflict': 'replace', 'preserve_times': True,
                                    'preserve_permissions': True}})
                self.assertEqual(c.read()['type'], 'started')
                self.assertEqual(c.read()['type'], 'transfer_ready')
                self.assertEqual(c.pending, b'')
                flags = {'recursive', 'links', 'perms', 'times', 'ignore_times', 'itemize'}
                if case == 'deletion': flags.add('del')
                options = bytes(name in flags for name in wire.BOOLS)
                options += b''.join(wire.var(2 if case == 'jobs' and name == 'jobs' else 0) for name in wire.INTS)
                selected = str(protected if case == 'path' else self.dest) + '/'
                hello = b'XSYNC\1' + wire.var(4) + b'R' + wire.var(features | (2048 if case == 'features' else 0))
                hello += options + b'\0' + (wire.var(1025) if case == 'path_count' else b'\1' + wire.string(selected))
                data = struct.pack('<IB', 1048577, 1) if case == 'oversized' else wire.frame(1, hello)
                c.proc.stdin.write(data); c.proc.stdin.flush()
                if case != 'oversized':
                    kind, message = wire.read_frame(c.proc)
                    self.assertEqual((kind, message[:2]), (8, b'\2\2'))
                c.proc.wait(timeout=5)
                self.assertEqual(c.proc.returncode, 2)
                self.assertEqual(list(self.dest.iterdir()), [])
                self.assertEqual((protected / 'keep').read_text(), 'good')

    def test_defaults_cannot_delete_filter_log_or_change_output(self):
        (self.source / 'file').write_text('data')
        (self.dest / 'unselected').write_text('keep')
        log = self.root / 'unwanted-log'
        config = self.root / 'config'
        config.write_text('--delete\n--exclude=*\n--log-file=' + str(log) + '\n')
        env = dict(os.environ, XSYNC_CONFIG=str(config), XSYNC_OPTS='--delete --exclude=*',
                   XSYNC_RSH='/does/not/exist', XSYNC_FALLBACK='1', XSYNC_PROGRESS='1')
        c, result = self.job(copy_request(self.source, self.dest), env)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'file').read_text(), 'data')
        self.assertEqual((self.dest / 'unselected').read_text(), 'keep')
        self.assertFalse(log.exists())
        self.assertEqual(c.proc.stderr.read(), b'')
        env['XSYNC_CONFIG'] = '/no/such/config'
        self.job({'id': 'list', 'op': 'list', 'endpoint': endpoint(self.source)}, env)

    def test_listing_bytes_types_link_target_and_exact_time(self):
        names = [b'colon:a', b'*?', b'-leading', b'new\nline', 'é'.encode()]
        for name in names:
            p = os.fsencode(self.source) + b'/' + name
            with open(p, 'wb') as f:
                f.write(b'hello')
            os.utime(p, ns=(1600000000123456789,)*2)
        os.symlink(b'new\nline', os.fsencode(self.source) + b'/link')
        (self.source / 'dir').mkdir()
        os.mkfifo(self.source / 'fifo')
        c, result = self.job({'id': 'listing', 'op': 'list', 'endpoint': endpoint(self.source)})
        self.assertEqual(result['status'], 'success')
        entries = [e for event in c.events if event['type'] == 'entries' for e in event['entries']]
        by_name = {bytes.fromhex(e['name']['bytes_hex']): e for e in entries}
        for name in names:
            self.assertEqual(by_name[name]['size'], '5')
            self.assertEqual(by_name[name]['mtime_seconds'], '1600000000')
            self.assertEqual(by_name[name]['mtime_nanoseconds'], '123456789')
        self.assertEqual(by_name[b'link']['link_target']['bytes_hex'], b'new\nline'.hex())
        self.assertEqual(by_name[b'dir']['type'], 'directory')
        self.assertEqual(by_name[b'fifo']['type'], 'fifo')

    def test_bounded_batches_and_empty_missing_nondirectory(self):
        c, result = self.job({'id': 'empty', 'op': 'list', 'endpoint': endpoint(self.source)})
        self.assertEqual(result['status'], 'success')
        self.assertFalse(any(e['type'] == 'entries' for e in c.events))
        for i in range(300):
            (self.source / str(i)).touch()
        c, result = self.job({'id': 'many', 'op': 'list', 'endpoint': endpoint(self.source)})
        batches = [e['entries'] for e in c.events if e['type'] == 'entries']
        self.assertEqual(sum(map(len, batches)), 300)
        self.assertTrue(all(len(b) <= 128 for b in batches))
        for path, category in ((self.root / 'missing', 'missing'), (self.source / '0', 'not_directory')):
            c, result = self.job({'id': 'bad', 'op': 'list', 'endpoint': endpoint(path)})
            self.assertEqual(result['status'], 'failure')
            self.assertEqual(next(e for e in c.events if e['type'] == 'error')['category'], category)

    def test_lstat_stat_and_resolution(self):
        (self.source / 'file').write_text('data')
        (self.source / 'link').symlink_to('file')
        for op, kind in (('lstat', 'symlink'), ('stat', 'file')):
            c, r = self.job({'id': op, 'op': op, 'endpoint': endpoint(self.source / 'link')})
            self.assertEqual(r['status'], 'success')
            self.assertEqual(next(e for e in c.events if e['type'] == 'entry')['entry']['type'], kind)
        for location in ('home', 'root'):
            c, r = self.job({'id': location, 'op': 'resolve', 'location': location})
            resolved = next(e for e in c.events if e['type'] == 'resolved')['endpoint']['path']
            self.assertTrue(bytes.fromhex(resolved['bytes_hex']).startswith(b'/'))

    def test_partial_listing_keeps_batches_and_exact_failure(self):
        for i in range(300):
            (self.source / f'entry-{i}').touch()
        for settings, count, operation, code in (
            ({'XSYNC_FAULT_LIST_AFTER': '140'}, 140, 'readdir', errno.EIO),
            ({'XSYNC_FAULT_STAT_NAME': 'entry-137'}, 299, 'lstat', errno.ENOENT)):
            with self.subTest(operation=operation):
                c, result = self.job({'id': 'partial', 'op': 'list', 'endpoint': endpoint(self.source)},
                                     self.fault_env(self.source, **settings))
                self.assertEqual(result['status'], 'partial_failure', c.events)
                entries = [entry for e in c.events if e['type'] == 'entries' for entry in e['entries']]
                self.assertEqual(len(entries), count)
                self.assertEqual(len({e['name']['bytes_hex'] for e in entries}), count)
                errors = [e for e in c.events if e['type'] == 'error']
                self.assertEqual(len(errors), 1)
                self.assertEqual((errors[0]['operation'], errors[0]['native_code']), (operation, str(code)))
                if operation == 'lstat':
                    self.assertEqual(errors[0]['path']['bytes_hex'], os.fsencode(self.source / 'entry-137').hex())

    def test_listing_cancel_and_late_navigation_events(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from app_client import ListingView
        for i in range(400):
            (self.source / f'entry-{i}').touch()
        view = ListingView('old-pane')
        old = self.client(self.fault_env(self.source, XSYNC_FAULT_LIST_DELAY_US='3000'))
        old.send({'id': 'old-pane', 'op': 'list', 'endpoint': endpoint(self.source)})
        while True:
            event = old.read()
            view.accept(event)
            if event['type'] == 'entries': break
        self.assertEqual(len(view.entries), 128)
        view.begin('new-pane')
        new, result = self.job({'id': 'new-pane', 'op': 'list', 'endpoint': endpoint(self.dest)})
        for event in new.events: view.accept(event)
        self.assertEqual(view.status, 'success')
        old.send({'id': 'cancel-old', 'op': 'cancel', 'job_id': 'old-pane'})
        self.assertEqual(old.finish()['status'], 'cancellation')
        for event in old.events: self.assertFalse(view.accept(event))
        self.assertEqual(view.status, 'success')
        self.assertEqual(view.entries, [])
        self.assertEqual(view.errors, [])

    def test_published_bytes_and_metadata_phase_during_staged_copy(self):
        source = self.source / 'file'
        source.write_bytes(b'x' * (1024 * 1024))
        target = self.dest / 'file'
        target.write_bytes(b'old good copy')
        marker = self.root / 'metadata-started'
        release = self.root / 'metadata-release'
        c = self.client(self.fault_env(self.dest, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker),
                                      XSYNC_FAULT_FUTIMENS_RELEASE=str(release)))
        c.send(copy_request(source, self.dest, mode='entry', bandwidth_bytes_per_second='1048576'))
        observed = False
        while True:
            e = c.read()
            if not observed and e['type'] == 'progress' and e['phase'] == 'applying_metadata' and marker.exists():
                self.assertEqual(e['logical_bytes_completed'], '0')
                self.assertEqual(e['files_completed'], '0')
                self.assertEqual(target.read_bytes(), b'old good copy')
                self.assertFalse(any(x['type'] == 'item_result' for x in c.events), c.events)
                observed = True
                release.touch()
            if e['type'] == 'result':
                self.assertEqual(e['status'], 'success', c.events)
                c.proc.wait(timeout=5)
                break
        self.assertTrue(observed, c.events)
        summary = next(e for e in c.events if e['type'] == 'summary')
        self.assertEqual(summary['logical_bytes_completed'], str(source.stat().st_size))
        self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_delta_hashing_reuse_and_publication_are_separate_live_work(self):
        basis = os.urandom(2 * 1024 * 1024)
        payload = basis[:800000] + b'changed block' * 200 + basis[802600:]
        source = self.source / 'file'; source.write_bytes(payload)
        target = self.dest / 'file'; target.write_bytes(basis)
        marker, release = self.root / 'delta-metadata', self.root / 'delta-release'
        c = self.client(self.fault_env(self.dest, XSYNC_FAULT_PREAD_NOTIFY=str(self.root / 'hashing'),
                                      XSYNC_FAULT_PREAD_DELAY_US='500000', XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker),
                                      XSYNC_FAULT_FUTIMENS_RELEASE=str(release)))
        c.send(copy_request(source, self.dest, mode='entry'))
        hashing = metadata = False
        while True:
            event = c.read()
            if event['type'] == 'progress' and event['phase'] == 'hashing':
                hashing = True
                self.assertEqual((event['logical_bytes_completed'], event['files_completed']), ('0', '0'))
            if event['type'] == 'progress' and event['phase'] == 'applying_metadata' and marker.exists():
                metadata = True
                self.assertEqual((event['logical_bytes_completed'], event['files_completed']), ('0', '0'))
                self.assertEqual(target.read_bytes(), basis)
                self.assertFalse(any(e['type'] == 'item_result' for e in c.events))
                release.touch()
            if event['type'] == 'result':
                self.assertEqual(event['status'], 'success', c.events); c.proc.wait(timeout=5); break
        self.assertTrue(hashing and metadata, c.events)
        item = inventory(c.events).items[b'file'.hex()]
        self.assertEqual((item['status'], item['bytes_processed']), ('success', str(len(payload))))
        self.assertGreater(int(item['reused_bytes']), len(payload) // 2)
        self.assertLess(int(item['reused_bytes']), len(payload))
        stages = [e['stage'] for e in c.events if e['type'] == 'item_stage']
        self.assertEqual(stages.count('hashing'), 2)
        self.assertEqual(target.read_bytes(), payload)
        summary = next(e for e in c.events if e['type'] == 'summary')
        self.assertEqual((summary['logical_bytes_completed'], summary['reused_bytes']),
                         (str(len(payload)), item['reused_bytes']))

    def test_delta_checksum_read_failure_has_no_published_bytes_or_success_item(self):
        basis = os.urandom(2 * 1024 * 1024)
        source = self.source / 'file'; source.write_bytes(basis[:10000] + b'new' + basis[10003:])
        target = self.dest / 'file'; target.write_bytes(basis)
        c, result = self.job(copy_request(source, self.dest, mode='entry'),
                             self.fault_env(self.dest, XSYNC_FAULT_PREAD_WRITABLE_ERROR=str(errno.EIO)))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['category'], error['operation'], error['native_code'], error['item_id']),
                         ('content', 'verify reconstructed delta', str(errno.EIO), b'file'.hex()))
        item = inventory(c.events).items[b'file'.hex()]
        self.assertEqual((item['status'], item['content_published'], item['metadata_complete']), ('failure', False, False))
        self.assertGreater(int(item['reused_bytes']), 0)
        self.assertEqual(target.read_bytes(), basis)
        self.assertEqual([p.name for p in self.dest.iterdir()], ['file'])
        summary = next(e for e in c.events if e['type'] == 'summary')
        self.assertEqual((summary['logical_bytes_completed'], summary['files_completed']), ('0', '0'))

    def test_source_errors_are_typed_for_every_failed_retry_selection(self):
        for i in range(32):
            (self.source / f'file-{i:02}').write_bytes(b'new bytes' * 100)
            (self.dest / f'file-{i:02}').write_text('old good copy')
        c, result = self.job(copy_request(self.source, self.dest, jobs='8'),
                             self.fault_env(self.source, XSYNC_FAULT_READ_ERROR='1'))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        errors = [e for e in c.events if e['type'] == 'error' and e['operation'] == 'read_source']
        self.assertEqual(len(errors), 32)
        view = inventory(c.events)
        self.assertEqual(sum(i['status'] == 'failure' for i in view.items.values()), 32)
        self.assertTrue(all(e['item_id'] in view.items for e in errors))
        failed_paths = {bytes.fromhex(e['path']['bytes_hex']) for e in errors}
        self.assertEqual(failed_paths, {os.fsencode(p) for p in self.source.iterdir()})
        self.assertTrue(all(e['native_code'] == str(errno.EIO) and e['category'] == 'content' and
                            e['side'] == 'source' and e['retryable'] for e in errors))
        self.assertTrue(all(p.read_text() == 'old good copy' for p in self.dest.iterdir()))
        summary = next(e for e in c.events if e['type'] == 'summary')
        self.assertEqual((summary['logical_bytes_completed'], summary['files_completed']), ('0', '0'))
        request = copy_request(self.source / 'unused', self.dest, mode='entry')
        request['sources'] = view.retry_selections()
        self.assertEqual({bytes.fromhex(s['endpoint']['path']['bytes_hex']) for s in request['sources']}, failed_paths)
        _, retry = self.job(request)
        self.assertEqual(retry['status'], 'success')
        self.assertTrue(all((self.dest / p.name).read_bytes() == p.read_bytes() for p in self.source.iterdir()))

    def test_failed_destination_removal_has_failed_item_and_explicit_retry(self):
        for incoming in ('directory', 'symlink'):
            with self.subTest(incoming=incoming):
                source = self.source / incoming
                if incoming == 'directory': source.mkdir(); (source / 'child').write_text('copied child')
                else: source.symlink_to('literal target')
                target = self.dest / incoming; target.write_text('protected old file')
                sibling = self.dest / f'unselected-{incoming}'; sibling.write_text('unselected')
                c, result = self.job(copy_request(source, self.dest, mode='entry'),
                                     self.fault_env(self.dest, XSYNC_FAULT_UNLINK_NAME=incoming))
                self.assertEqual(result['status'], 'partial_failure', c.events)
                error = next(e for e in c.events if e['type'] == 'error')
                self.assertEqual((error['category'], error['operation'], error['side'], error['native_code']),
                                 ('permission', 'unlink_destination', 'destination', str(errno.EPERM)))
                self.assertEqual(error['path']['bytes_hex'], os.fsencode(target).hex())
                item = inventory(c.events).items[incoming.encode().hex()]
                self.assertEqual((item['status'], item['content_published'], item['metadata_complete']), ('failure', False, False))
                self.assertEqual(target.read_text(), 'protected old file')
                retry = copy_request(source, self.dest, mode='entry')
                retry['sources'] = inventory(c.events).retry_selections()
                _, result = self.job(retry)
                self.assertEqual(result['status'], 'success')
                if incoming == 'directory': self.assertEqual((target / 'child').read_text(), 'copied child')
                else: self.assertEqual(target.readlink(), pathlib.Path('literal target'))
                self.assertEqual(sibling.read_text(), 'unselected')

    def test_transfer_scanning_keeps_exact_child_native_errors_and_container_retry(self):
        (self.source / 'good').write_text('observed child')
        (self.source / 'missing-stat').write_text('temporarily unobservable')
        (self.source / 'link').symlink_to('good')
        cases = [({'XSYNC_FAULT_STAT_NAME': 'missing-stat'}, 'stat_source', 'missing-stat', errno.ENOENT),
                 ({'XSYNC_FAULT_READLINK_NAME': 'link'}, 'readlink_source', 'link', errno.EIO)]
        for settings, operation, name, code in cases:
            with self.subTest(operation=operation):
                prefix = [str(self.deny), 'statx', str(errno.ENOSYS)] if sys.platform.startswith('linux') else ()
                c = self.client(self.fault_env(self.source, **settings), prefix=prefix)
                c.send(copy_request(self.source, self.dest))
                result = c.finish()
                self.assertEqual(result['status'], 'partial_failure', c.events)
                error = next(e for e in c.events if e['type'] == 'error' and e['operation'] == operation)
                self.assertEqual((error['side'], error['native_code'], error['stage']), ('source', str(code), 'scanning'))
                self.assertEqual(error['path']['bytes_hex'], os.fsencode(self.source / name).hex())
                view = inventory(c.events)
                self.assertEqual(view.items['']['status'], 'failure')
                self.assertEqual((self.dest / 'good').read_text(), 'observed child')
                if operation == 'readlink_source':
                    self.assertEqual((self.dest / 'link').readlink(), pathlib.Path('good'))
                self.assertEqual(view.items[name.encode().hex()]['status'], 'failure')
                retry = copy_request(self.source, self.dest)
                retry['sources'] = view.retry_selections()
                self.assertEqual(retry['sources'], [{'endpoint': endpoint(self.source), 'mode': 'contents'}])
                _, retried = self.job(retry)
                self.assertEqual(retried['status'], 'success')
                self.assertEqual((self.dest / 'missing-stat').read_text(), 'temporarily unobservable')
                self.assertEqual((self.dest / 'link').readlink(), pathlib.Path('good'))

    def test_receiver_write_and_disk_full_errors_preserve_outputs_and_retry_inventory(self):
        source = self.source / 'file'; source.write_bytes(b'incoming' * 10000)
        target = self.dest / 'file'
        for code, category, status in ((errno.EIO, 'content', 'partial_failure'), (errno.ENOSPC, 'disk_full', 'failure')):
            with self.subTest(code=code):
                target.write_text('old good copy')
                c, result = self.job(copy_request(source, self.dest, mode='entry'),
                                     self.fault_env(self.dest, XSYNC_FAULT_WRITE_ERROR=str(code)))
                self.assertEqual(result['status'], status, c.events)
                error = next(e for e in c.events if e['type'] == 'error' and e['operation'] == 'write')
                self.assertEqual((error['category'], error['native_code'], error['item_id'], error['side'], error['stage']),
                                 (category, str(code), b'file'.hex(), 'destination', 'content'))
                item = inventory(c.events).items[b'file'.hex()]
                self.assertEqual((item['status'], item['content_published'], item['metadata_complete']), ('failure', False, False))
                self.assertEqual(target.read_text(), 'old good copy')
                self.assertEqual([p.name for p in self.dest.iterdir()], ['file'])
                retry = copy_request(source, self.dest, mode='entry'); retry['sources'] = inventory(c.events).retry_selections()
                self.assertEqual(retry['sources'], [{'endpoint': endpoint(source), 'mode': 'entry'}])
                _, retried = self.job(retry)
                self.assertEqual(retried['status'], 'success')
                self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_metadata_failure_is_distinct_from_content_failure(self):
        source = self.source / 'file'
        source.write_text('published data')
        c, result = self.job(copy_request(source, self.dest, mode='entry'),
                             self.fault_env(self.dest, XSYNC_FAULT_FUTIMENS_ERROR=str(errno.EPERM)))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['side'], error['stage'], error['native_code']),
                         ('destination', 'metadata', str(errno.EPERM)))
        self.assertEqual((self.dest / 'file').read_text(), 'published data')
        item = inventory(c.events).items[b'file'.hex()]
        self.assertEqual((item['status'], item['reason'], item['content_published'], item['metadata_complete']),
                         ('failure', 'metadata_error', True, False))
        self.assertEqual(error['item_id'], item['item_id'])

    def test_changed_and_vanished_sources_keep_good_output_and_typed_reason(self):
        for scenario in ('changed', 'vanished', 'vanished_second'):
            with self.subTest(scenario=scenario):
                source = self.source / 'file'
                source.write_bytes(b'a' * 4096)
                target = self.dest / 'file'
                target.write_text('old good copy')
                marker = self.root / (scenario + '-read')
                c = self.client(self.fault_env(source, XSYNC_FAULT_READ_NOTIFY=str(marker),
                                               XSYNC_FAULT_READ_DELAY_US='300000'))
                c.send(copy_request(source, self.dest, mode='entry'))
                for attempt in range(1, 2 if scenario == 'vanished' else 3):
                    deadline = time.monotonic() + 3
                    while not pathlib.Path(str(marker) + f'.{attempt}').exists():
                        self.assertLess(time.monotonic(), deadline, c.events)
                        time.sleep(.005)
                    if scenario == 'vanished' or (scenario == 'vanished_second' and attempt == 2): source.unlink()
                    else:
                        source.write_bytes(bytes([ord('a') + attempt]) * 4096)
                        os.utime(source, ns=(1600000000123456789 + attempt,) * 2)
                result = c.finish()
                self.assertEqual(result['status'], 'partial_failure', c.events)
                error = next(e for e in c.events if e['type'] == 'error')
                self.assertEqual(error['path']['bytes_hex'], os.fsencode(source).hex())
                self.assertEqual(error['side'], 'source')
                if scenario.startswith('vanished'):
                    if scenario == 'vanished_second': self.assertEqual(error['operation'], 'revalidate_source')
                    self.assertEqual((error['category'], error['native_code']), ('vanished_source', str(errno.ENOENT)))
                else:
                    self.assertEqual((error['category'], error['native_code'], error['reason']), ('content', None, 'source_changed'))
                self.assertEqual(target.read_text(), 'old good copy')
                self.assertEqual([p.name for p in self.dest.iterdir()], ['file'])
                summary = next(e for e in c.events if e['type'] == 'summary')
                self.assertEqual((summary['logical_bytes_completed'], summary['files_completed']), ('0', '0'))

    def wait_marker(self, marker, timeout=3):
        deadline = time.monotonic() + timeout
        while not marker.exists():
            self.assertLess(time.monotonic(), deadline, f'missing marker {marker}')
            time.sleep(.005)

    def test_destination_revisions_reject_changed_staged_targets(self):
        source = self.source / 'file'
        source.write_bytes(b'incoming bytes' * 1000)
        target = self.dest / 'file'
        for scenario in ('in_place', 'replaced', 'permissions', 'deleted', 'appeared', 'symlink'):
            with self.subTest(scenario=scenario):
                if target.exists() or target.is_symlink(): target.unlink()
                if scenario != 'appeared': target.write_text('old good copy')
                marker, release = self.root / (scenario + '-metadata'), self.root / (scenario + '-release')
                c = self.client(self.fault_env(self.dest, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker),
                                              XSYNC_FAULT_FUTIMENS_RELEASE=str(release)))
                c.send(copy_request(source, self.dest, mode='entry'))
                self.wait_marker(marker)
                if scenario == 'in_place': target.write_text('external writer')
                elif scenario == 'replaced':
                    target.unlink(); target.write_text('external writer')
                elif scenario == 'permissions': target.chmod(0o444)
                elif scenario == 'deleted': target.unlink()
                elif scenario == 'appeared': target.write_text('external writer')
                else:
                    target.unlink(); target.symlink_to(source)
                release.touch()
                result = c.finish()
                self.assertEqual(result['status'], 'partial_failure', c.events)
                errors = [e for e in c.events if e['type'] == 'error' and e['category'] == 'conflict']
                self.assertEqual(len(errors), 1, c.events)
                error = errors[0]
                self.assertEqual((error['operation'], error['reason'], error['native_code'], error['side']),
                                 ('destination_changed', 'destination_changed', None, 'destination'))
                self.assertEqual(error['item_id'], b'file'.hex())
                self.assertNotEqual(error['expected_revision'], error['observed_revision'])
                self.assertEqual(error['expected_revision']['exists'], scenario != 'appeared')
                self.assertEqual(error['observed_revision']['exists'], scenario != 'deleted')
                item = inventory(c.events).items[b'file'.hex()]
                self.assertEqual((item['status'], item['reason'], item['content_published'], item['metadata_complete']),
                                 ('failure', 'destination_changed', False, False))
                if scenario == 'symlink': self.assertTrue(target.is_symlink())
                elif scenario == 'deleted': self.assertFalse(target.exists())
                else: self.assertEqual(target.read_text(), 'old good copy' if scenario == 'permissions' else 'external writer')
                self.assertEqual(sorted(p.name for p in self.dest.iterdir()), [] if scenario == 'deleted' else ['file'])

    def test_atomic_absent_publication_rejects_file_appearing_after_last_check(self):
        source = self.source / 'file'; source.write_text('incoming')
        marker, release = self.root / 'closed-output', self.root / 'release-close'
        c = self.client(self.fault_env(self.dest, XSYNC_FAULT_CLOSE_NOTIFY=str(marker), XSYNC_FAULT_CLOSE_RELEASE=str(release)))
        c.send(copy_request(source, self.dest, mode='entry'))
        self.wait_marker(marker)
        target = self.dest / 'file'; target.write_text('external writer')
        release.touch()
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['category'], error['operation'], error['native_code']),
                         ('conflict', 'destination_changed', str(errno.EEXIST)))
        self.assertFalse(error['expected_revision']['exists'])
        self.assertTrue(error['observed_revision']['exists'])
        self.assertEqual(target.read_text(), 'external writer')
        self.assertEqual([p.name for p in self.dest.iterdir()], ['file'])
        self.assertFalse(inventory(c.events).items[b'file'.hex()]['content_published'])

    def test_existing_destination_is_rechecked_after_staged_close(self):
        source = self.source / 'file'; source.write_text('incoming')
        target = self.dest / 'file'; target.write_text('old good copy')
        marker, release = self.root / 'closed-output', self.root / 'release-close'
        c = self.client(self.fault_env(self.dest, XSYNC_FAULT_CLOSE_NOTIFY=str(marker), XSYNC_FAULT_CLOSE_RELEASE=str(release)))
        c.send(copy_request(source, self.dest, mode='entry'))
        self.wait_marker(marker)
        target.write_text('external writer during close'); release.touch()
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['category'], error['operation'], error['native_code']), ('conflict', 'destination_changed', None))
        self.assertEqual(target.read_text(), 'external writer during close')
        self.assertEqual([p.name for p in self.dest.iterdir()], ['file'])
        self.assertFalse(inventory(c.events).items[b'file'.hex()]['content_published'])

    def test_replaced_temporary_outputs_are_never_published_or_cleaned_as_owned(self):
        source = self.source / 'file'; source.write_bytes(b'incoming' * 8192)
        protected = self.root / 'protected'; protected.write_text('unrelated good file')
        for cancelled in (False, True):
            for occupant in ('file', 'symlink', 'directory'):
                with self.subTest(cancelled=cancelled, occupant=occupant):
                    destination = self.dest / f'{cancelled}-{occupant}'; destination.mkdir()
                    target = destination / 'file'; target.write_text('old good copy')
                    marker = self.root / f'{cancelled}-{occupant}-metadata'
                    release = self.root / f'{cancelled}-{occupant}-release'
                    c = self.client(self.fault_env(destination, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker),
                                                  XSYNC_FAULT_FUTIMENS_RELEASE=str(release)))
                    c.send(copy_request(source, destination, mode='entry'))
                    self.wait_marker(marker)
                    staged = next(p for p in destination.iterdir() if p.name != 'file')
                    staged.unlink()
                    if occupant == 'file': staged.write_text('external staging occupant')
                    elif occupant == 'symlink': staged.symlink_to(protected)
                    else:
                        staged.mkdir(); (staged / 'keep').write_text('external staging occupant')
                    before = staged.lstat()
                    if cancelled:
                        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
                        while c.read()['type'] != 'cancel_ack': pass
                    release.touch()
                    result = c.finish()
                    self.assertEqual(result['status'], 'cancellation' if cancelled else 'partial_failure', c.events)
                    after = staged.lstat()
                    self.assertEqual((after.st_dev, after.st_ino), (before.st_dev, before.st_ino))
                    if occupant == 'file': self.assertEqual(staged.read_text(), 'external staging occupant')
                    elif occupant == 'symlink': self.assertEqual(staged.readlink(), protected)
                    else: self.assertEqual((staged / 'keep').read_text(), 'external staging occupant')
                    self.assertEqual(protected.read_text(), 'unrelated good file')
                    self.assertEqual(target.read_text(), 'old good copy')
                    if not cancelled:
                        error = next(e for e in c.events if e['type'] == 'error')
                        self.assertEqual((error['category'], error['reason'], error['native_code']),
                                         ('conflict', 'temporary_output_changed', None))
                        self.assertNotEqual(error['expected_revision']['inode'], error['observed_revision']['inode'])
                        item = inventory(c.events).items[b'file'.hex()]
                        self.assertEqual((item['status'], item['reason'], item['content_published']),
                                         ('failure', 'temporary_output_changed', False))

    def test_destination_root_stat_failure_after_anchor_is_not_treated_as_new_directory(self):
        (self.source / 'file').write_text('incoming')
        (self.dest / 'file').write_text('old good copy')
        (self.dest / 'unselected').write_text('protected')
        request = copy_request(self.source, self.dest)
        c, result = self.job(request, self.fault_env(self.dest, XSYNC_FAULT_STAT_NAME='.'))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['operation'], error['category'], error['native_code']), ('stat_destination_root', 'missing', str(errno.ENOENT)))
        view = inventory(c.events)
        self.assertEqual(set(view.items), {'', b'file'.hex()})
        self.assertTrue(all(item['status'] == 'failure' and not item['content_published'] and not item['metadata_complete'] for item in view.items.values()))
        self.assertEqual((self.dest / 'file').read_text(), 'old good copy')
        self.assertEqual((self.dest / 'unselected').read_text(), 'protected')
        _, retried = self.job(view.retry_requests(request)[0])
        self.assertEqual(retried['status'], 'success')
        self.assertEqual((self.dest / 'file').read_text(), 'incoming')
        self.assertEqual((self.dest / 'unselected').read_text(), 'protected')

    def test_missing_destination_root_after_source_scan_is_not_recreated(self):
        (self.source / 'file').write_text('incoming')
        (self.dest / 'unselected').write_text('protected')
        marker, release = self.root / 'scanning', self.root / 'scan-release'
        c = self.client(self.fault_env(self.source, XSYNC_FAULT_SCAN_NOTIFY=str(marker), XSYNC_FAULT_SCAN_RELEASE=str(release)))
        request = copy_request(self.source, self.dest)
        c.send(request)
        self.wait_marker(marker)
        displaced = self.root / 'displaced'; self.dest.rename(displaced)
        release.touch()
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertFalse(self.dest.exists())
        self.assertEqual((displaced / 'unselected').read_text(), 'protected')
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['category'], error['reason'], error['observed_revision']), ('conflict', 'destination_root_changed', {'exists': False}))
        view = inventory(c.events)
        self.assertEqual(set(view.items), {'', b'file'.hex()})
        self.assertTrue(all(item['status'] == 'failure' and not item['metadata_complete'] and not item['content_published'] for item in view.items.values()))
        displaced.rename(self.dest)
        retry = view.retry_requests(request)[0]
        _, retried = self.job(retry)
        self.assertEqual(retried['status'], 'success')
        self.assertEqual((self.dest / 'file').read_text(), 'incoming')
        self.assertEqual((self.dest / 'unselected').read_text(), 'protected')

    def test_replaced_destination_root_and_ancestor_are_conflicts(self):
        source = self.source / 'sub'; source.mkdir(); (source / 'file').write_text('incoming')
        (self.dest / 'sub').mkdir(); (self.dest / 'sub' / 'file').write_text('old good copy')
        for scenario in ('ancestor', 'root'):
            with self.subTest(scenario=scenario):
                marker, release = self.root / (scenario + '-metadata'), self.root / (scenario + '-release')
                c = self.client(self.fault_env(self.dest, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker), XSYNC_FAULT_FUTIMENS_RELEASE=str(release)))
                c.send(copy_request(source, self.dest, mode='entry'))
                self.wait_marker(marker)
                selected = self.dest / 'sub' if scenario == 'ancestor' else self.dest
                parked = self.root / (scenario + '-parked')
                selected.rename(parked); selected.mkdir(); (selected / 'keep').write_text('external writer')
                release.touch(); result = c.finish()
                self.assertEqual(result['status'], 'partial_failure', c.events)
                error = next(e for e in c.events if e['type'] == 'error')
                self.assertEqual(error['operation'], 'destination_ancestor_changed' if scenario == 'ancestor' else 'destination_root_changed')
                self.assertEqual(error['category'], 'conflict')
                self.assertEqual((selected / 'keep').read_text(), 'external writer')
                old_target = parked / 'file' if scenario == 'ancestor' else parked / 'sub' / 'file'
                self.assertEqual(old_target.read_text(), 'old good copy')
                self.assertFalse(any(p.name.startswith('.file.') for p in parked.rglob('*')))
                selected.rename(self.root / (scenario + '-new-directory'))
                parked.rename(selected)

    def test_browse_revision_changes_after_same_size_write(self):
        target = self.source / 'file'; target.write_text('aaaa')
        c, _ = self.job({'id': 'stat', 'op': 'lstat', 'endpoint': endpoint(target)})
        first = next(e['entry']['revision'] for e in c.events if e['type'] == 'entry')
        target.write_text('bbbb')
        c, _ = self.job({'id': 'stat', 'op': 'lstat', 'endpoint': endpoint(target)})
        second = next(e['entry']['revision'] for e in c.events if e['type'] == 'entry')
        self.assertEqual(first['inode'], second['inode'])
        self.assertEqual(first['size'], second['size'])
        self.assertNotEqual(first, second)
        self.assertTrue(first['exists'])
        self.assertNotIn('atime_seconds', first)

    def test_automatic_source_retry_keeps_one_identity_and_final_attempt_counts(self):
        source = self.source / 'file'
        source.write_bytes(b'a' * 4096)
        (self.dest / 'file').write_text('old good copy')
        marker = self.root / 'read-attempt'
        c = self.client(self.fault_env(source, XSYNC_FAULT_READ_NOTIFY=str(marker),
                                      XSYNC_FAULT_READ_DELAY_US='300000'))
        c.send(copy_request(source, self.dest, mode='entry'))
        deadline = time.monotonic() + 3
        while not pathlib.Path(str(marker) + '.1').exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.005)
        source.write_bytes(b'b' * 4096)
        os.utime(source, ns=(1600000000123456789,) * 2)
        result = c.finish()
        self.assertEqual(result['status'], 'success', c.events)
        view = inventory(c.events)
        item = view.items[b'file'.hex()]
        self.assertEqual((item['status'], item['attempt'], item['bytes_processed']), ('success', '1', '4096'))
        retries = [e for e in c.events if e['type'] == 'item_retry']
        self.assertEqual([(e['item_id'], e['attempt'], e['reason']) for e in retries], [(b'file'.hex(), '1', 'source_changed')])
        self.assertEqual(len([e for e in c.events if e['type'] == 'item_result']), 1)
        self.assertEqual((self.dest / 'file').read_bytes(), b'b' * 4096)

    def test_authoritative_inventory_success_skip_and_deferred_directories(self):
        (self.source / 'sub').mkdir()
        name = 'new\n:*?'
        (self.source / 'sub' / name).write_bytes(b'payload' * 10000)
        (self.source / 'empty').mkdir()
        (self.source / 'link').symlink_to('sub/' + name)
        os.mkfifo(self.source / 'fifo')
        (self.dest / 'unselected').write_text('keep')
        c, result = self.job(copy_request(self.source, self.dest, jobs='4'))
        self.assertEqual(result['status'], 'success', c.events)
        view = inventory(c.events)
        expected = {b'', b'sub', os.fsencode('sub/' + name), b'empty', b'link', b'fifo'}
        self.assertEqual(set(view.items), {p.hex() for p in expected})
        for identity, item in view.items.items():
            self.assertEqual(identity, item['path']['bytes_hex'])
            if identity == b'fifo'.hex():
                self.assertEqual((item['status'], item['reason']), ('skipped', 'unsupported_type'))
            else:
                self.assertEqual((item['status'], item['metadata_complete']), ('success', True))
                self.assertEqual(bytes.fromhex(item['source_path']['bytes_hex']),
                                 os.fsencode(self.source) + (b'/' + bytes.fromhex(identity) if identity else b''))
        results = [e for e in c.events if e['type'] == 'item_result']
        positions = {e['item_id']: int(e['seq']) for e in results}
        self.assertGreater(positions[b'sub'.hex()], positions[os.fsencode('sub/' + name).hex()])
        self.assertGreater(positions[''], max(v for k, v in positions.items() if k))
        summary = next(e for e in c.events if e['type'] == 'summary')
        self.assertEqual((summary['items_discovered'], summary['items_results']), ('6', '6'))
        self.assertEqual((self.dest / 'unselected').read_text(), 'keep')
        c, result = self.job(copy_request(self.source, self.dest, policy='skip'))
        self.assertEqual(result['status'], 'success', c.events)
        view = inventory(c.events)
        self.assertEqual(view.items[os.fsencode('sub/' + name).hex()]['status'], 'skipped')
        self.assertEqual(view.items[b'link'.hex()]['status'], 'skipped')
        self.assertEqual(view.retry_selections(), [])

    def test_skip_directory_type_conflict_preserves_existing_file(self):
        (self.source / 'directory').mkdir()
        (self.source / 'directory' / 'child').write_text('incoming')
        (self.dest / 'directory').write_text('keep good file')
        c, result = self.job(copy_request(self.source, self.dest, policy='skip'))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'directory').read_text(), 'keep good file')
        view = inventory(c.events)
        self.assertEqual(view.items[b'directory'.hex()]['status'], 'skipped')
        self.assertFalse(any(item['status'] == 'failure' for item in view.items.values()))

    def test_directory_scan_failure_is_an_item_failure_with_retry_mapping(self):
        (self.source / 'blocked').mkdir()
        (self.source / 'blocked' / 'hidden').write_text('unseen')
        (self.source / 'good').write_text('copied')
        c, result = self.job(copy_request(self.source, self.dest),
                             self.fault_env(self.source / 'blocked', XSYNC_FAULT_OPENDIR_ERROR=str(errno.EACCES)))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        view = inventory(c.events)
        self.assertEqual((view.items[b'blocked'.hex()]['status'], view.items[b'blocked'.hex()]['reason']),
                         ('failure', 'source_error'))
        self.assertEqual(view.items[b'good'.hex()]['status'], 'success')
        self.assertNotIn(b'blocked/hidden'.hex(), view.items)
        error = next(e for e in c.events if e['type'] == 'error' and e['operation'] == 'scan_source')
        self.assertEqual(error['item_id'], b'blocked'.hex())
        self.assertEqual(view.retry_selections(), [{'endpoint': endpoint(self.source / 'blocked'), 'mode': 'entry'}])
        _, retry = self.job(dict(copy_request(self.source, self.dest), sources=view.retry_selections()))
        self.assertEqual(retry['status'], 'success')
        self.assertEqual((self.dest / 'blocked' / 'hidden').read_text(), 'unseen')
        c, result = self.job(copy_request(self.source, self.dest),
                             self.fault_env(self.source, XSYNC_FAULT_OPENDIR_ERROR=str(errno.EACCES)))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        view = inventory(c.events)
        self.assertEqual(view.items['']['status'], 'failure')
        self.assertEqual(view.retry_selections(), [{'endpoint': endpoint(self.source), 'mode': 'contents'}])

    def test_inventory_cancellation_and_interrupted_stream_unknowns(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from app_client import TransferInventory
        source = self.source / 'large'
        source.write_bytes(b'x' * (4*1024*1024))
        c = self.client()
        c.send(copy_request(source, self.dest, mode='entry', bandwidth_bytes_per_second='65536'))
        view = TransferInventory('copy')
        while not view.items:
            view.accept(c.read())
        self.assertFalse(view.accept(dict(c.events[-1], id='old-job')))
        interrupted = TransferInventory('copy')
        for event in c.events: interrupted.accept(event)
        interrupted.finish()
        self.assertEqual(interrupted.items[b'large'.hex()]['status'], 'unknown')
        self.assertEqual(interrupted.retry_selections(), [])
        self.assertEqual(interrupted.retry_selections(include_unknown=True), [{'endpoint': endpoint(source), 'mode': 'entry'}])
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
        result = c.finish()
        for event in c.events:
            if event['type'] != 'item_discovered': view.accept(event)
        self.assertEqual(result['status'], 'cancellation', c.events)
        self.assertIn(view.items[b'large'.hex()]['status'], ('unknown', 'cancellation'))
        self.assertEqual(view.retry_selections(include_unknown=True), [])
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_literal_selections_copy_folder_and_contents(self):
        name = b'new\n:*?-name'
        source = os.fsencode(self.source) + b'/' + name
        with open(source, 'wb') as f:
            f.write(b'payload')
        (self.source / 'not-selected').write_text('sibling')
        c, r = self.job(copy_request(source, self.dest, mode='entry'))
        self.assertEqual(r['status'], 'success', c.events)
        self.assertEqual(os.listdir(os.fsencode(self.dest)), [name])
        with open(os.fsencode(self.dest)+b'/'+name, 'rb') as f:
            self.assertEqual(f.read(), b'payload')
        folder = self.source / 'folder'
        folder.mkdir()
        (folder / 'nested').write_text('nested')
        self.job(copy_request(folder, self.dest, mode='entry'))
        self.assertEqual((self.dest / 'folder/nested').read_text(), 'nested')
        self.job(copy_request(folder, self.dest, mode='contents'))
        self.assertEqual((self.dest / 'nested').read_text(), 'nested')

    def test_batch_skip_policy(self):
        (self.source / 'existing').write_text('new')
        (self.source / 'new').write_text('created')
        (self.dest / 'existing').write_text('old')
        c, r = self.job(copy_request(self.source, self.dest, policy='skip'))
        self.assertEqual(r['status'], 'success', c.events)
        self.assertEqual((self.dest / 'existing').read_text(), 'old')
        self.assertEqual((self.dest / 'new').read_text(), 'created')

    def test_unsupported_operations_paths_options_are_rejected_before_writes(self):
        requests = [
            {'id': 'ssh', 'op': 'list', 'endpoint': endpoint(self.source, 'ssh')},
            {'id': 'delete', 'op': 'delete', 'endpoint': endpoint(self.source)},
            {'id': 'resolve', 'op': 'resolve', 'location': 'home', 'endpoint': {'kind': 'unsupported'}},
            {'id': 'path', 'op': 'list', 'endpoint': {'kind': 'local', 'path': {'bytes_hex': '00'}}},
            {'id': 'path', 'op': 'list', 'endpoint': {'kind': 'local', 'path': {'bytes_hex': 'gg'}}},
            copy_request(self.source, self.dest, on_conflict='interactive'),
            copy_request(self.source, self.dest, jobs='65'),
            copy_request(self.source, self.dest, jobs=2),
            copy_request(self.source, self.dest, bandwidth_bytes_per_second='18446744073709551616')]
        for request in requests:
            with self.subTest(request=request):
                _, r = self.job(request)
                self.assertEqual(r['status'], 'failure')
                self.assertEqual(list(self.dest.iterdir()), [])

    def test_unknown_optional_fields_and_unicode_json(self):
        c, r = self.job({'id': 'optional', 'op': 'list', 'endpoint': endpoint(self.source),
                         'future': {'emoji': '😀', 'number': 1.2e10, 'array': [None, True, False]}})
        self.assertEqual(r['status'], 'success')

    def test_invalid_utf8_bytes_roundtrip_independent_of_filesystem(self):
        home = b'/unusual-home-\xff\n'
        c, r = self.job({'id': 'home', 'op': 'resolve', 'location': 'home'},
                        dict(os.environ, HOME=os.fsdecode(home)))
        path = next(e for e in c.events if e['type'] == 'resolved')['endpoint']['path']
        self.assertEqual(bytes.fromhex(path['bytes_hex']), home)
        self.assertIn('\ufffd', path['display'])

    def test_invalid_utf8_filesystem_names_when_supported(self):
        name = b'invalid-\xff\n:*?'
        source = os.fsencode(self.source) + b'/' + name
        try:
            with open(source, 'wb') as f:
                f.write(b'raw bytes')
        except OSError as e:
            if e.errno in (errno.EILSEQ, getattr(errno, 'EFTYPE', 79)):
                self.skipTest('host filesystem rejects invalid UTF-8 names; byte codec covered separately')
            raise
        c, r = self.job({'id': 'raw', 'op': 'list', 'endpoint': endpoint(self.source)})
        self.assertEqual(next(e for e in c.events if e['type'] == 'entries')['entries'][0]['name']['bytes_hex'], name.hex())
        _, r = self.job(copy_request(source, self.dest, mode='entry'))
        self.assertEqual(r['status'], 'success')
        with open(os.fsencode(self.dest)+b'/'+name, 'rb') as f:
            self.assertEqual(f.read(), b'raw bytes')

    def test_permission_failure_is_typed(self):
        if os.geteuid() == 0:
            self.skipTest('permission fixture requires an unprivileged user')
        self.source.chmod(0)
        self.addCleanup(self.source.chmod, 0o700)
        c, r = self.job({'id': 'denied', 'op': 'list', 'endpoint': endpoint(self.source)})
        self.assertEqual(r['status'], 'failure')
        e = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual(e['category'], 'permission')
        self.assertEqual(e['native_code'], str(errno.EACCES))

    def test_invalid_json_duplicate_ids_and_depth(self):
        for frame in (b'{"id":"x","id":"y","op":"list"}',
                      br'{"id":"x","op":"\ud800"}',
                      b'{"id":"x","future":' + b'['*34+b'0'+b']'*34+b'}',
                      b'{"id":"x","op":"list","future":01}',
                      b'{"id":"hello","op":"list"}',
                      b'{"id":"x","op":"\xff"}'):
            c = self.client()
            c.proc.stdin.write(frame+b'\n')
            c.proc.stdin.flush()
            self.assertEqual(c.finish()['status'], 'failure')

    def slow_copy(self):
        (self.source / 'large').write_bytes(os.urandom(8*1024*1024))
        (self.dest / 'large').write_bytes(b'old good copy')
        c = self.client()
        c.send(copy_request(self.source, self.dest, bandwidth_bytes_per_second='1048576'))
        self.assertEqual(c.read()['type'], 'started')
        while c.read()['type'] != 'progress':
            pass
        return c

    def test_live_progress_cancel_ack_and_atomic_cleanup(self):
        c = self.slow_copy()
        before = time.monotonic()
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
        r = c.finish()
        self.assertEqual(r['status'], 'cancellation')
        self.assertLess(time.monotonic()-before, 5)
        self.assertTrue(any(e['type'] == 'cancel_ack' and e['id'] == 'cancel' for e in c.events))
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        self.assertEqual([p.name for p in self.dest.iterdir()], ['large'])
        self.assertTrue(any(e['type'] == 'progress' and e['logical_bytes_total'] is None for e in c.events))

    def test_overlapping_destinations_rejected_and_browsing_isolated(self):
        c = self.slow_copy()
        browse, r = self.job({'id': 'browse', 'op': 'list', 'endpoint': endpoint(self.source)})
        self.assertEqual(r['status'], 'success')
        (self.dest / 'sub').mkdir()
        alias = self.root / 'alias'
        alias.symlink_to(self.dest, target_is_directory=True)
        for dest in (self.dest, self.dest / 'sub', alias / 'sub'):
            other, r = self.job(copy_request(self.source, dest))
            self.assertEqual(r['status'], 'failure', other.events)
            self.assertTrue(any(e['type'] == 'error' and e['category'] == 'conflict' for e in other.events))
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
        c.finish()

    def test_cancel_one_transfer_preserves_another_jobs_staging_and_options(self):
        first = self.slow_copy()
        source, destination = self.root / 'second-source', self.root / 'second-destination'
        source.mkdir(); destination.mkdir()
        payload = b'second independent payload' * 8192
        (source / 'other').write_bytes(payload)
        (source / 'other').chmod(0o600)
        stamp = 1600000000123456789
        os.utime(source / 'other', ns=(stamp, stamp))
        target = destination / 'other'; target.write_text('second old copy'); target.chmod(0o444)
        sentinel = destination / '.other.ABC123'; sentinel.write_text('unrelated temporary-looking file')
        marker, release = self.root / 'second-metadata', self.root / 'second-release'
        second = self.client(self.fault_env(destination, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker),
                                            XSYNC_FAULT_FUTIMENS_RELEASE=str(release)))
        request = copy_request(source / 'other', destination, mode='entry', jobs='2',
                               bandwidth_bytes_per_second='0', preserve_permissions=False)
        second.send(request)
        self.wait_marker(marker)
        staged = next(p for p in destination.iterdir() if p.name not in ('other', sentinel.name))
        staged_identity = staged.stat()
        before = time.monotonic()
        first.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
        self.assertEqual(first.finish()['status'], 'cancellation', first.events)
        self.assertLess(time.monotonic() - before, 5)
        self.assertIsNone(second.proc.poll())
        self.assertEqual((staged.stat().st_dev, staged.stat().st_ino),
                         (staged_identity.st_dev, staged_identity.st_ino))
        release.touch()
        result = second.finish()
        self.assertEqual(result['status'], 'success', second.events)
        self.assertFalse(any(e['type'] in ('error', 'cancel_ack') for e in second.events))
        self.assertEqual(target.read_bytes(), payload)
        self.assertEqual(target.stat().st_mode & 0o777, 0o444)
        self.assertEqual(target.stat().st_mtime_ns, stamp)
        self.assertEqual(sentinel.read_text(), 'unrelated temporary-looking file')
        self.assertEqual(sorted(p.name for p in destination.iterdir()), [sentinel.name, 'other'])
        items = inventory(second.events).items
        self.assertEqual(set(items), {b'other'.hex()})
        self.assertEqual((items[b'other'.hex()]['status'], items[b'other'.hex()]['bytes_processed']),
                         ('success', str(len(payload))))
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_control_eof_and_signal_cancel(self):
        for action in ('eof', 'signal'):
            c = self.slow_copy()
            if action == 'eof':
                c.proc.stdin.close()
            else:
                c.proc.send_signal(signal.SIGTERM)
            self.assertEqual(c.finish()['status'], 'cancellation')
            self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_closed_event_consumer_cancels_worker(self):
        c = self.slow_copy()
        c.proc.stdout.close()
        c.proc.wait(timeout=6)
        self.assertNotEqual(c.proc.returncode, 0)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_success_is_after_files_and_directory_metadata(self):
        sub = self.source / 'sub'
        sub.mkdir()
        (sub / 'file').write_bytes(os.urandom(1024*1024))
        os.utime(sub, ns=(1600000000123456789,)*2)
        c, r = self.job(copy_request(self.source, self.dest))
        self.assertEqual(r['status'], 'success', c.events)
        self.assertEqual((self.dest / 'sub/file').read_bytes(), (sub / 'file').read_bytes())
        self.assertEqual((self.dest / 'sub').stat().st_mtime_ns, sub.stat().st_mtime_ns)
        self.assertEqual(c.events[-2]['type'], 'summary')
        self.assertEqual(r['durability'], 'filesystem-completion')

    def test_existing_directory_required_and_symlink_destination_rejected(self):
        for path in (self.root / 'absent', self.root / 'link'):
            if path.name == 'link':
                path.symlink_to(self.dest, target_is_directory=True)
            c, r = self.job(copy_request(self.source, path))
            self.assertEqual(r['status'], 'failure')
        self.assertFalse((self.root / 'absent').exists())

    def test_explicit_unsupported_and_missing_sources_fail_before_writes(self):
        pipe = self.source / 'fifo'
        os.mkfifo(pipe)
        for source, category in ((pipe, 'unsupported_feature'), (self.source / 'missing', 'missing')):
            c, r = self.job(copy_request(source, self.dest, mode='entry'))
            self.assertEqual(r['status'], 'failure')
            self.assertEqual(next(e for e in c.events if e['type'] == 'error')['category'], category)
            self.assertEqual(list(self.dest.iterdir()), [])

    def test_failed_preflight_has_complete_selection_outcomes_without_copying_valid_siblings(self):
        good = self.source / 'good'; good.write_text('must not copy before preflight succeeds')
        missing = self.source / 'missing'
        request = copy_request(good, self.dest, mode='entry')
        request['sources'].append({'endpoint': endpoint(missing), 'mode': 'entry'})
        c, result = self.job(request)
        self.assertEqual(result['status'], 'failure', c.events)
        view = inventory(c.events)
        self.assertEqual(set(view.items), {b'good'.hex(), b'missing'.hex()})
        self.assertEqual((view.items[b'good'.hex()]['status'], view.items[b'good'.hex()]['reason']), ('skipped', 'preflight_failed'))
        self.assertEqual(view.items[b'missing'.hex()]['status'], 'failure')
        self.assertIsNone(view.items[b'missing'.hex()]['size'])
        self.assertEqual(list(self.dest.iterdir()), [])
        self.assertEqual(view.retry_selections(), [{'endpoint': endpoint(missing), 'mode': 'entry'}])
        missing.write_text('source now exists')
        retry = copy_request(missing, self.dest, mode='entry'); retry['sources'] = view.retry_selections()
        _, result = self.job(retry)
        self.assertEqual(result['status'], 'success')
        self.assertEqual((self.dest / 'missing').read_text(), 'source now exists')
        self.assertFalse((self.dest / 'good').exists())

    def test_transfer_diagnostics_are_not_limited_to_ten_samples(self):
        for i in range(17):
            name = str(i)
            (self.source / name).write_text('new')
            (self.dest / name).mkdir()
            (self.dest / name / 'keep').write_text('old')
        c, r = self.job(copy_request(self.source, self.dest))
        self.assertEqual(r['status'], 'partial_failure', c.events)
        errors = [e for e in c.events if e['type'] == 'diagnostic']
        self.assertEqual(len(errors), 17)
        self.assertTrue(all((self.dest / str(i) / 'keep').read_text() == 'old' for i in range(17)))

    def test_stalled_event_reader_stops_with_bounded_buffers(self):
        for i in range(3000):
            (self.source / str(i)).touch()
        c = self.client()
        c.send({'id': 'stalled', 'op': 'list', 'endpoint': endpoint(self.source)})
        self.assertEqual(c.read()['type'], 'started')
        c.proc.wait(timeout=8)
        self.assertNotEqual(c.proc.returncode, 0)

    def test_hard_supervisor_death_leaves_no_running_writer(self):
        c = self.slow_copy()
        rows = subprocess.check_output(['ps', '-axo', 'pid=,ppid=']).splitlines()
        children = [int(pid) for pid, parent in (line.split() for line in rows) if int(parent) == c.proc.pid]
        self.assertEqual(len(children), 1)
        c.proc.kill()
        c.proc.wait(timeout=3)
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            states = subprocess.run(['ps', '-o', 'stat=', '-p', str(children[0])], capture_output=True).stdout.strip()
            if not states or states.startswith(b'Z'):
                break
            time.sleep(0.05)
        else:
            self.fail('orphaned job writer remained running')
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_oversized_and_truncated_frames_fail_before_writes(self):
        hello = json.dumps({'id': 'hello', 'op': 'hello', 'schema': '1'}).encode()+b'\n'
        for frame in (b'{"id":"x"', b'{"id":"x","padding":"' + b'a'*(1024*1024)+b'"}\n'):
            p = subprocess.run([str(BINARY), '--app'], input=hello+frame, capture_output=True, timeout=5)
            self.assertNotEqual(p.returncode, 0)
            events = [json.loads(line) for line in p.stdout.splitlines()]
            self.assertEqual(events[-1]['status'], 'failure')
            self.assertEqual(list(self.dest.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
