#!/usr/bin/env python3
"""Moves preserve source data until required destination completion is verified."""
import errno
import os
import pathlib
import sys
import subprocess
import tempfile
import time
import unittest

import app_test
from app_test import BINARY, ROOT, Client, endpoint
sys.path.insert(0, str(ROOT / 'tools'))


class AppMoveTests(unittest.TestCase):
    setUpClass = classmethod(app_test.AppTests.setUpClass.__func__)
    fault_env = app_test.AppTests.fault_env

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        self.destination = self.root / 'destination'; self.destination.mkdir()

    def client(self, env=None):
        c = Client(env); self.addCleanup(c.close); return c

    def revision(self, path):
        c = self.client(); c.send({'id':'stat', 'op':'lstat', 'endpoint':endpoint(path)}); result = c.finish()
        self.assertEqual(result['status'], 'success')
        return next(e['entry']['revision'] for e in c.events if e['type'] == 'entry')

    def request(self, names, policy='replace', contents=False, mapped=None):
        sources = []
        for name in names:
            p = self.source if contents else self.source / name
            selected = {'endpoint':endpoint(p), 'mode':'contents' if contents else 'entry', 'expected_revision':self.revision(p)}
            if mapped: selected['destination_name'] = {'bytes_hex':os.fsencode(mapped).hex()}
            sources.append(selected)
        return {'id':'move', 'op':'move', 'sources':sources, 'destination':endpoint(self.destination),
                'destination_parent_revision':self.revision(self.destination),
                'options':{'on_conflict':policy, 'preserve_times':True, 'preserve_permissions':True}}

    def run_request(self, request, env=None):
        c = self.client(env); c.send(request); result = c.finish(); return result, c.events

    def moves(self, events):
        return [e for e in events if e['type'] == 'move_result']

    def test_native_same_filesystem_rename_preserves_inode(self):
        file = self.source / 'a'; file.write_text('only copy'); before = file.stat().st_ino
        result, events = self.run_request(self.request(['a']))
        self.assertEqual(result['status'], 'success', events)
        self.assertFalse(file.exists())
        self.assertEqual((self.destination/'a').stat().st_ino, before)
        move = self.moves(events)[0]
        self.assertTrue(move['renamed'] and move['removed'])
        self.assertFalse(move['copied'] or move['remaining'])

    def test_native_directory_rename_reports_descendants(self):
        tree = self.source / 'tree'; tree.mkdir(); (tree/'sub').mkdir(); (tree/'sub'/'file').write_text('data')
        before = tree.stat().st_ino
        result, events = self.run_request(self.request(['tree'], mapped='mapped\n*?'))
        self.assertEqual(result['status'], 'success', events)
        self.assertFalse(tree.exists())
        self.assertEqual((self.destination/'mapped\n*?').stat().st_ino, before)
        self.assertEqual((self.destination/'mapped\n*?'/'sub'/'file').read_text(), 'data')
        self.assertEqual(len(self.moves(events)), 3)
        self.assertTrue(all(e['renamed'] and e['removed'] for e in self.moves(events)))

    def test_copy_remove_waits_for_completion_and_preserves_attributes(self):
        file = self.source/'a'; file.write_text('data'); file.chmod(0o640); os.utime(file, ns=(1600000000123456789,)*2)
        before = file.stat().st_ino
        result, events = self.run_request(self.request(['a'], policy='ask'))
        self.assertEqual(result['status'], 'success', events)
        self.assertFalse(file.exists())
        target = self.destination/'a'
        self.assertNotEqual(target.stat().st_ino, before)
        self.assertEqual(target.read_text(), 'data')
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertEqual(target.stat().st_mtime_ns, 1600000000123456789)
        move = self.moves(events)[0]
        self.assertTrue(move['copied'] and move['removed'] and move['destination_completed'])
        item_index = next(i for i,e in enumerate(events) if e['type']=='item_result')
        move_index = next(i for i,e in enumerate(events) if e['type']=='move_result')
        self.assertLess(item_index, move_index)

    def test_contents_move_keeps_selected_root_and_removes_empty_children(self):
        (self.source/'dir').mkdir(); (self.source/'dir'/'file').write_text('data')
        result, events = self.run_request(self.request(['ignored'], policy='ask', contents=True))
        self.assertEqual(result['status'], 'success', events)
        self.assertEqual(list(self.source.iterdir()), [])
        self.assertEqual((self.destination/'dir'/'file').read_text(), 'data')
        root = next(e for e in self.moves(events) if e['scope_root'])
        self.assertFalse(root['removed'] or root['remaining'])

    def test_existing_directory_merges_without_removing_unselected_destination(self):
        (self.source/'tree').mkdir(); (self.source/'tree'/'file').write_text('incoming')
        (self.destination/'tree').mkdir(); (self.destination/'tree'/'keep').write_text('unselected')
        result, events = self.run_request(self.request(['tree']))
        self.assertEqual(result['status'], 'success', events)
        self.assertFalse((self.source/'tree').exists())
        self.assertEqual((self.destination/'tree'/'keep').read_text(), 'unselected')
        self.assertEqual((self.destination/'tree'/'file').read_text(), 'incoming')
        self.assertTrue(all(e['copied'] for e in self.moves(events)))

    def test_skip_keeps_source_and_reports_remaining(self):
        (self.source/'a').write_text('source'); (self.destination/'a').write_text('existing')
        result, events = self.run_request(self.request(['a'], policy='skip'))
        self.assertEqual(result['status'], 'partial_failure', events)
        self.assertEqual((self.source/'a').read_text(), 'source')
        self.assertEqual((self.destination/'a').read_text(), 'existing')
        move = self.moves(events)[0]; self.assertTrue(move['remaining']); self.assertFalse(move['removed'] or move['copied'])

    def test_metadata_failure_never_removes_source(self):
        (self.source/'a').write_text('only copy')
        request = self.request(['a'], policy='ask')
        result, events = self.run_request(request, self.fault_env(self.destination, XSYNC_FAULT_FUTIMENS_ERROR=str(errno.EPERM)))
        self.assertEqual(result['status'], 'partial_failure', events)
        self.assertEqual((self.source/'a').read_text(), 'only copy')
        move = self.moves(events)[0]
        self.assertFalse(move['removed'] or move['destination_completed'])
        self.assertTrue(move['remaining'])

    def test_source_removal_failure_reports_copied_and_remaining(self):
        (self.source/'a').write_text('only copy')
        request = self.request(['a'], policy='ask')
        result, events = self.run_request(request, self.fault_env(self.source, XSYNC_FAULT_UNLINK_NAME='a'))
        self.assertEqual(result['status'], 'partial_failure', events)
        self.assertEqual((self.source/'a').read_text(), 'only copy')
        self.assertEqual((self.destination/'a').read_text(), 'only copy')
        move = self.moves(events)[0]
        self.assertTrue(move['copied'] and move['remaining'])
        self.assertFalse(move['removed'])
        self.assertIn(str(errno.EPERM), [e.get('native_code') for e in events if e['type']=='error'])

    def test_stale_selected_revision_fails_before_any_move(self):
        (self.source/'a').write_text('old'); request = self.request(['a']); (self.source/'a').write_text('new only copy')
        result, events = self.run_request(request)
        self.assertEqual(result['status'], 'failure', events)
        self.assertEqual((self.source/'a').read_text(), 'new only copy')
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertTrue(self.moves(events)[0]['remaining'])

    def test_source_changed_after_copy_is_retained(self):
        file = self.source/'a'; file.write_bytes(b'old data'*(3*1024*1024))
        request = self.request(['a'], policy='ask')
        c = self.client(self.fault_env(file, XSYNC_FAULT_EACH_READ_DELAY_US='20000'))
        c.send(request)
        while True:
            event = c.read()
            if event['type']=='phase' and event['phase']=='verifying_move': break
        file.write_bytes(b'new only copy')
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertEqual(file.read_bytes(), b'new only copy')
        self.assertFalse(self.moves(c.events)[0]['removed'])

    def test_cancel_after_copy_during_verification_keeps_source(self):
        file = self.source/'a'; file.write_bytes(b'only copy'*(2*1024*1024))
        request = self.request(['a'], policy='ask')
        c = self.client(self.fault_env(file, XSYNC_FAULT_EACH_READ_DELAY_US='20000'))
        c.send(request)
        while True:
            event = c.read()
            if event['type']=='phase' and event['phase']=='verifying_move': break
        c.send({'id':'stop', 'op':'cancel', 'job_id':'move'})
        result = c.finish()
        self.assertEqual(result['status'], 'cancellation', c.events)
        self.assertEqual(file.read_bytes(), b'only copy'*(2*1024*1024))
        self.assertFalse(any(e['removed'] for e in self.moves(c.events)))

    def test_symlink_move_never_follows_external_directory(self):
        outside = self.root/'outside'; outside.mkdir(); (outside/'keep').write_text('keep')
        (self.source/'link').symlink_to(outside, target_is_directory=True)
        result, events = self.run_request(self.request(['link'], policy='ask'))
        self.assertEqual(result['status'], 'success', events)
        self.assertFalse((self.source/'link').is_symlink())
        self.assertTrue((self.destination/'link').is_symlink())
        self.assertEqual((outside/'keep').read_text(), 'keep')

    def test_fingerprint_file_and_symlink_bytes_are_distinct(self):
        (self.source/'a').write_bytes(b'data'); (self.source/'b').write_bytes(b'data'); (self.source/'link').symlink_to('a')
        digests = []
        for name in ('a','b','link'):
            c = self.client(); c.send({'id':'hash','op':'fingerprint','endpoint':endpoint(self.source/name)})
            self.assertEqual(c.finish()['status'], 'success')
            digests.append(next(e['entry']['fingerprint']['hex'] for e in c.events if e['type']=='entry'))
        self.assertEqual(digests[0], digests[1]); self.assertNotEqual(digests[0], digests[2])

    def test_cross_filesystem_move_copies_then_removes(self):
        if sys.platform == 'darwin':
            import mount_test
            mount_test.MountTests.setUpClass()
            self.addCleanup(mount_test.MountTests.tearDownClass)
            other = tempfile.TemporaryDirectory(dir=mount_test.MountTests.mount)
        elif pathlib.Path('/dev/shm').is_dir():
            other = tempfile.TemporaryDirectory(dir='/dev/shm')
        else:
            self.skipTest('no second filesystem available')
        self.addCleanup(other.cleanup)
        self.destination = pathlib.Path(other.name)
        self.assertNotEqual(self.source.stat().st_dev, self.destination.stat().st_dev)
        (self.source/'tree').mkdir(); (self.source/'tree'/'file').write_text('only copy')
        result, events = self.run_request(self.request(['tree']))
        self.assertEqual(result['status'], 'success', events)
        self.assertFalse((self.source/'tree').exists())
        self.assertEqual((self.destination/'tree'/'file').read_text(), 'only copy')
        self.assertTrue(all(e['copied'] and e['removed'] and not e['renamed'] for e in self.moves(events)))

    def test_reference_client_moves_and_retains_unknown_outcomes(self):
        from app_client import MoveInventory
        (self.source/'a').write_text('data'); request = self.request(['a'])
        inventory = MoveInventory(request)
        self.assertIsNone(inventory.items[b'a'.hex()]['removed'])
        result, events = self.run_request(request)
        for event in events: inventory.accept(event)
        self.assertEqual(inventory.status, 'success')
        self.assertTrue(inventory.items[b'a'.hex()]['removed'])
        (self.source/'a').write_text('second')
        completed = subprocess.run([sys.executable, str(ROOT/'tools/app_client.py'), '--binary', str(BINARY),
            'move', str(self.source/'a'), str(self.destination), '--on-conflict', 'replace'], capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertFalse((self.source/'a').exists())
        self.assertEqual((self.destination/'a').read_text(), 'second')

    def test_move_holds_local_destination_lock_through_verification(self):
        file = self.source/'a'; file.write_bytes(b'only copy'*(2*1024*1024))
        request = self.request(['a'], policy='ask')
        c = self.client(self.fault_env(file, XSYNC_FAULT_EACH_READ_DELAY_US='20000'))
        c.send(request)
        while True:
            event = c.read()
            if event['type']=='phase' and event['phase']=='verifying_move': break
        contender = self.client()
        contender.send(app_test.copy_request(self.source, self.destination))
        result = contender.finish()
        self.assertNotEqual(result['status'], 'success', contender.events)
        self.assertIn('destination_lock', [e.get('operation') for e in contender.events if e['type']=='error'])
        self.assertEqual(c.finish()['status'], 'success', c.events)

    def finish_deciding(self, c, decision, **extra):
        while True:
            event = c.read()
            if event['type'] == 'conflict':
                c.send({'id':'decision-'+event['conflict_id'], 'op':'conflict_response', 'job_id':'move',
                        'conflict_id':event['conflict_id'], 'revision_token':event['revision_token'], 'decision':decision, **extra})
            if event['type'] == 'result':
                c.proc.wait(timeout=6); return event

    def test_interactive_keep_both_replace_skip_and_cancel(self):
        for decision in ('keep_both', 'replace', 'skip', 'cancel'):
            with self.subTest(decision=decision):
                source = self.source/'a'; target = self.destination/'a'
                source.write_text('incoming'); target.write_text('good existing')
                c = self.client(); c.send(self.request(['a'], policy='ask'))
                result = self.finish_deciding(c, decision)
                if decision in ('keep_both','replace'):
                    self.assertEqual(result['status'], 'success', c.events)
                    self.assertFalse(source.exists())
                    moved = self.moves(c.events)[0]
                    actual = pathlib.Path(os.fsdecode(bytes.fromhex(moved['destination_path']['bytes_hex'])))
                    self.assertEqual(actual.read_text(), 'incoming')
                    if decision == 'keep_both': self.assertEqual(target.read_text(), 'good existing')
                else:
                    self.assertNotEqual(result['status'], 'success', c.events)
                    self.assertEqual(source.read_text(), 'incoming')
                    self.assertEqual(target.read_text(), 'good existing')
                for file in self.destination.iterdir(): file.unlink()

    def test_disk_full_keeps_only_source_and_existing_destination(self):
        (self.source/'a').write_bytes(b'incoming'*65536); (self.destination/'a').write_text('good existing')
        c = self.client(self.fault_env(self.destination, XSYNC_FAULT_WRITE_ERROR=str(errno.ENOSPC)))
        c.send(self.request(['a'], policy='ask'))
        result = self.finish_deciding(c, 'replace')
        self.assertNotEqual(result['status'], 'success', c.events)
        self.assertEqual((self.source/'a').read_bytes(), b'incoming'*65536)
        self.assertEqual((self.destination/'a').read_text(), 'good existing')
        self.assertFalse(self.moves(c.events)[0]['removed'])
        self.assertIn('disk_full', [e.get('category') for e in c.events if e['type']=='error'])

    def test_new_directory_child_is_not_removed_after_inventory(self):
        tree = self.source/'tree'; tree.mkdir(); (tree/'a').write_bytes(b'a'*(4*1024*1024))
        c = self.client(self.fault_env(tree/'a', XSYNC_FAULT_EACH_READ_DELAY_US='50000'))
        c.send(self.request(['tree'], policy='ask'))
        while True:
            event = c.read()
            if event['type']=='phase' and event['phase']=='verifying_move': break
        (tree/'new-child').write_text('retain')
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertEqual((tree/'new-child').read_text(), 'retain')
        self.assertFalse((tree/'a').exists())
        self.assertEqual((self.destination/'tree'/'a').stat().st_size, 4*1024*1024)
        root = next(e for e in self.moves(c.events) if e['item_id']==b'tree'.hex())
        self.assertTrue(root['copied'] and root['remaining']); self.assertFalse(root['removed'])

    def test_overlapping_plan_rejected_before_first_native_rename(self):
        for name in ('a','b','c'): (self.source/name).write_text(name)
        os.link(self.source/'c', self.destination/'b')
        result, events = self.run_request(self.request(['a','b','c']))
        self.assertNotEqual(result['status'], 'success', events)
        self.assertTrue(all((self.source/name).read_text()==name for name in ('a','b','c')))
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()), ['b'])
        self.assertFalse(any(e['removed'] for e in self.moves(events)))

    def test_destination_inside_selected_directory_rejected(self):
        tree = self.source/'tree'; tree.mkdir(); (tree/'a').write_text('only copy'); (tree/'nested').mkdir()
        request = self.request(['tree']); request['destination'] = endpoint(tree/'nested')
        request['destination_parent_revision'] = self.revision(tree/'nested')
        result, events = self.run_request(request)
        self.assertNotEqual(result['status'], 'success', events)
        self.assertEqual((tree/'a').read_text(), 'only copy')
        self.assertEqual(list((tree/'nested').iterdir()), [])

    def test_busy_move_reports_unknown_selection_without_claiming_retention(self):
        import fcntl
        (self.source/'a').write_text('only copy'); request = self.request(['a'])
        fd = os.open(self.destination, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result, events = self.run_request(request)
        finally: os.close(fd)
        self.assertNotEqual(result['status'], 'success', events)
        moved = self.moves(events)[0]
        self.assertIsNone(moved['remaining']); self.assertFalse(moved['removed'] or moved['copied'])
        summary = next(e for e in events if e['type']=='move_summary')
        self.assertEqual(summary['items_unknown'], '1')
        self.assertEqual((self.source/'a').read_text(), 'only copy')

    def test_frontend_crash_during_verification_keeps_source_and_releases_locks(self):
        import fcntl
        import signal
        source = self.source/'a'; data = b'a'*(8*1024*1024); source.write_bytes(data)
        c = self.client(self.fault_env(source, XSYNC_FAULT_EACH_READ_DELAY_US='100000'))
        c.send(self.request(['a'],policy='ask'))
        while True:
            event = c.read()
            if event['type']=='phase' and event['phase']=='verifying_move': break
        c.proc.send_signal(signal.SIGKILL); c.proc.wait(timeout=6)
        fd = os.open(self.destination,os.O_RDONLY)
        try:
            deadline = time.monotonic()+6
            while True:
                try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); break
                except BlockingIOError:
                    if time.monotonic()>deadline: self.fail('orphan move retained destination lock')
                    time.sleep(0.02)
        finally: os.close(fd)
        self.assertEqual(source.read_bytes(),data)
        self.assertEqual((self.destination/'a').read_bytes(),data)

    def test_reference_inventory_rejects_missing_descendant_results(self):
        from app_client import MoveInventory
        (self.source/'a').write_text('only copy'); request = self.request(['a'])
        result, events = self.run_request(request)
        view = MoveInventory(request)
        for event in events:
            if event['type'] == 'move_summary': event = dict(event, items_total='2')
            if event['type'] == 'result':
                with self.assertRaises(RuntimeError): view.accept(event)
            else: view.accept(event)

    def test_hardlinked_selections_account_for_own_revision_changes(self):
        for policy in ('replace', 'ask'):
            with self.subTest(policy=policy):
                first, second = self.source/'a', self.source/'b'
                first.write_text('only copy'); os.link(first, second)
                result, events = self.run_request(self.request(['a','b'], policy=policy))
                self.assertEqual(result['status'], 'success', events)
                self.assertFalse(first.exists() or second.exists())
                self.assertEqual((self.destination/'a').read_text(), 'only copy')
                self.assertEqual((self.destination/'b').read_text(), 'only copy')
                self.assertTrue(all(e['removed'] for e in self.moves(events)))
                for file in self.destination.iterdir(): file.unlink()


if __name__ == '__main__': unittest.main()
