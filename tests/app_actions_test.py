#!/usr/bin/env python3
"""Revision-bound independent filesystem actions through the public contract."""
import copy
import errno
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

import app_test
from app_test import BINARY, ROOT, Client, endpoint
sys.path.insert(0, str(ROOT / 'tools'))
from app_client import action_request, prepare_action


class AppActionsTests(unittest.TestCase):
    setUpClass = classmethod(app_test.AppTests.setUpClass.__func__)
    fault_env = app_test.AppTests.fault_env
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.parent = self.root / 'pane'
        self.parent.mkdir()

    def client(self, env=None):
        c = Client(env)
        self.addCleanup(c.close)
        return c

    def request(self, operation, names, **options):
        return prepare_action(BINARY, operation, endpoint(self.parent), names, **options)

    def run_request(self, request, env=None):
        c = self.client(env)
        c.send(request)
        result = c.finish()
        return result, c.events

    def actions(self, events):
        return [e for e in events if e['type'] == 'action_result']

    def test_capabilities_distinguish_permanent_delete_and_trash(self):
        caps = self.client().capabilities
        self.assertEqual(caps['filesystem_actions'], '1')
        self.assertTrue(caps['permanent_delete'])
        self.assertFalse(caps['trash'])
        self.assertFalse(caps['undo_delete'])
        for op in ('mkdir', 'rename', 'delete', 'metadata'):
            self.assertIn(op, caps['operations'])

    def test_mkdir_batch_literal_names_and_modes(self):
        names = [b'*?\n-leading', b'colon:name']
        result, events = self.run_request(self.request('mkdir', names, mode=0o750))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(self.actions(events)), 2)
        for name in names:
            st = os.lstat(os.fsencode(self.parent) + b'/' + name)
            self.assertEqual(st.st_mode & 0o777, 0o750)
        self.assertEqual(len([e for e in events if e['type'] == 'invalidate']), 2)

    def test_invalid_utf8_name(self):
        try:
            os.mkdir(os.fsencode(self.parent) + b'/existing-\xff')
        except OSError as error:
            if sys.platform == 'darwin' and error.errno == 92:
                self.skipTest('macOS filesystem rejects invalid UTF-8')
            raise
        result, _ = self.run_request(self.request('rename', [b'existing-\xff'], destination_name=b'new-\xfe'))
        self.assertEqual(result['status'], 'success')
        self.assertTrue(os.path.isdir(os.fsencode(self.parent) + b'/new-\xfe'))

    def test_rename_no_replace_and_replace(self):
        (self.parent / 'a').write_text('first')
        result, events = self.run_request(self.request('rename', ['a'], destination_name='b'))
        self.assertEqual(result['status'], 'success')
        self.assertFalse((self.parent / 'a').exists())
        self.assertEqual((self.parent / 'b').read_text(), 'first')
        (self.parent / 'a').write_text('second')
        result, _ = self.run_request(self.request('rename', ['a'], destination_name='b', replace=True))
        self.assertEqual(result['status'], 'success')
        self.assertEqual((self.parent / 'b').read_text(), 'second')
        self.assertEqual(self.actions(events)[0]['destination_path']['bytes_hex'], os.fsencode(self.parent / 'b').hex())

    def test_replace_nonempty_directory_is_not_recursive(self):
        (self.parent / 'a').mkdir()
        (self.parent / 'b').mkdir()
        (self.parent / 'b' / 'keep').write_text('only copy')
        result, events = self.run_request(self.request('rename', ['a'], destination_name='b', replace=True))
        self.assertNotEqual(result['status'], 'success')
        self.assertTrue((self.parent / 'a').is_dir())
        self.assertEqual((self.parent / 'b' / 'keep').read_text(), 'only copy')
        self.assertFalse(self.actions(events)[0]['changed'])

    def test_replace_empty_directory(self):
        (self.parent / 'a').mkdir()
        (self.parent / 'a' / 'child').write_text('data')
        (self.parent / 'b').mkdir()
        result, _ = self.run_request(self.request('rename', ['a'], destination_name='b', replace=True))
        self.assertEqual(result['status'], 'success')
        self.assertEqual((self.parent / 'b' / 'child').read_text(), 'data')

    def test_stale_leaf_keeps_replacement_and_other_items_continue(self):
        (self.parent / 'a').write_text('old')
        (self.parent / 'b').write_text('delete me')
        request = self.request('delete', ['a', 'b'])
        # Editing the file preserves the parent revision; the leaf is stale.
        (self.parent / 'a').write_text('new only copy')
        result, events = self.run_request(request)
        self.assertEqual(result['status'], 'partial_failure')
        self.assertEqual((self.parent / 'a').read_text(), 'new only copy')
        self.assertFalse((self.parent / 'b').exists())
        self.assertEqual([e['status'] for e in self.actions(events)], ['failure', 'success'])
        self.assertIn('stale_entry', [e.get('reason') for e in events if e['type'] == 'error'])

    def test_stale_parent_prevents_all_writes(self):
        request = self.request('mkdir', ['new'])
        (self.parent / 'external').write_text('external')
        result, events = self.run_request(request)
        self.assertNotEqual(result['status'], 'success')
        self.assertFalse((self.parent / 'new').exists())
        self.assertEqual(len(self.actions(events)), 1)

    def test_replaced_root_is_not_modified(self):
        (self.parent / 'a').write_text('old')
        request = self.request('delete', ['a'])
        displaced = self.root / 'displaced'
        self.parent.rename(displaced)
        self.parent.mkdir()
        (self.parent / 'a').write_text('replacement')
        result, _ = self.run_request(request)
        self.assertNotEqual(result['status'], 'success')
        self.assertEqual((self.parent / 'a').read_text(), 'replacement')
        self.assertEqual((displaced / 'a').read_text(), 'old')

    def test_missing_root_returns_each_selected_outcome(self):
        request = self.request('mkdir', ['a', 'b'])
        self.parent.rmdir()
        result, events = self.run_request(request)
        self.assertNotEqual(result['status'], 'success')
        self.assertEqual(len(self.actions(events)), 2)

    def test_recursive_delete_never_follows_directory_symlinks(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'keep').write_text('only copy')
        selected = self.parent / 'tree'
        selected.mkdir()
        (selected / 'sub').mkdir()
        (selected / 'sub' / 'a').write_text('a')
        (selected / 'link').symlink_to(outside, target_is_directory=True)
        result, events = self.run_request(self.request('delete', ['tree'], recursive=True))
        self.assertEqual(result['status'], 'success')
        self.assertFalse(selected.exists())
        self.assertEqual((outside / 'keep').read_text(), 'only copy')
        actions = self.actions(events)
        self.assertEqual(len(actions), 4)
        self.assertTrue(all(e['removed'] and not e['undoable'] for e in actions))
        self.assertTrue(all('outside' not in e['path']['display'] for e in actions))

    def test_nonrecursive_delete_keeps_directory_children(self):
        (self.parent / 'tree').mkdir()
        (self.parent / 'tree' / 'keep').write_text('keep')
        result, events = self.run_request(self.request('delete', ['tree']))
        self.assertNotEqual(result['status'], 'success')
        self.assertEqual((self.parent / 'tree' / 'keep').read_text(), 'keep')
        self.assertFalse(self.actions(events)[0]['removed'])

    def test_delete_selected_symlink_does_not_touch_target(self):
        outside = self.root / 'target'
        outside.write_text('keep')
        (self.parent / 'link').symlink_to(outside)
        result, _ = self.run_request(self.request('delete', ['link'], recursive=True))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(outside.read_text(), 'keep')

    def test_metadata_mode_and_time_independent_of_copy(self):
        file = self.parent / 'a'
        file.write_text('content')
        result, events = self.run_request(self.request('metadata', ['a'], mode=0o640,
            mtime={'seconds': '1600000000', 'nanoseconds': '123456789'}))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(file.stat().st_mode & 0o777, 0o640)
        self.assertEqual(file.stat().st_mtime_ns, 1600000000123456789)
        self.assertEqual(file.read_text(), 'content')
        self.assertTrue(self.actions(events)[0]['changed'])

    def test_symlink_metadata_is_explicitly_unsupported(self):
        outside = self.root / 'target'
        outside.write_text('keep')
        before = outside.stat().st_mode
        (self.parent / 'link').symlink_to(outside)
        result, events = self.run_request(self.request('metadata', ['link'], mode=0o600))
        self.assertNotEqual(result['status'], 'success')
        self.assertEqual(outside.stat().st_mode, before)
        self.assertIn('unsupported_feature', [e['category'] for e in events if e['type'] == 'error'])

    def test_invalid_scope_names_revisions_and_fields_fail_before_writes(self):
        (self.parent / 'a').write_text('keep')
        base = self.request('delete', ['a'])
        mutations = []
        missing_scope = copy.deepcopy(base); del missing_scope['recursive']; mutations.append(missing_scope)
        trash = copy.deepcopy(base); trash['trash'] = True; mutations.append(trash)
        missing_revision = copy.deepcopy(base); del missing_revision['items'][0]['expected_revision']; mutations.append(missing_revision)
        for name in ('../outside', '.', '/', 'bad\0name'):
            invalid = copy.deepcopy(base); invalid['items'][0]['name']['bytes_hex'] = os.fsencode(name).hex(); mutations.append(invalid)
        for request in mutations:
            with self.subTest(request=request):
                result, _ = self.run_request(request)
                self.assertEqual(result['status'], 'failure')
                self.assertEqual((self.parent / 'a').read_text(), 'keep')

    def test_reference_cli_actions(self):
        for args in (['mkdir', str(self.parent), 'new', '--mode', '750'],
                     ['rename', str(self.parent), 'new', 'renamed'],
                     ['metadata', str(self.parent), 'renamed', '--mode', '700'],
                     ['delete', str(self.parent), 'renamed']):
            result = subprocess.run([sys.executable, str(ROOT / 'tools/app_client.py'), '--binary', str(BINARY), *args],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.parent / 'renamed').exists())

    def test_recursive_scan_failure_never_authorizes_removal(self):
        tree = self.parent / 'tree'; tree.mkdir()
        for n in range(4): (tree / str(n)).write_text('keep')
        request = self.request('delete', ['tree'], recursive=True)
        result, events = self.run_request(request, self.fault_env(tree, XSYNC_FAULT_LIST_AFTER='1'))
        self.assertNotEqual(result['status'], 'success')
        self.assertEqual(len(list(tree.iterdir())), 4)
        self.assertFalse(any(e['changed'] for e in self.actions(events)))
        self.assertIn(str(errno.EIO), [e.get('native_code') for e in events if e['type'] == 'error'])

    def test_recursive_delete_reports_failed_and_removed_children(self):
        tree = self.parent / 'tree'; tree.mkdir()
        (tree / 'keep').write_text('keep'); (tree / 'remove').write_text('remove')
        request = self.request('delete', ['tree'], recursive=True)
        result, events = self.run_request(request, self.fault_env(tree, XSYNC_FAULT_UNLINK_NAME='keep'))
        self.assertEqual(result['status'], 'partial_failure')
        self.assertEqual((tree / 'keep').read_text(), 'keep')
        self.assertFalse((tree / 'remove').exists())
        outcomes = {e['item_id']: e for e in self.actions(events)}
        self.assertTrue(outcomes[b'tree/remove'.hex()]['removed'])
        self.assertFalse(outcomes[b'tree/keep'.hex()]['removed'])
        self.assertEqual(outcomes[b'tree'.hex()]['status'], 'failure')

    def test_metadata_partial_application_is_truthful(self):
        file = self.parent / 'a'; file.write_text('keep')
        request = self.request('metadata', ['a'], mode=0o640, mtime={'seconds':'1', 'nanoseconds':'0'})
        result, events = self.run_request(request, self.fault_env(file, XSYNC_FAULT_FUTIMENS_ERROR=str(errno.EPERM)))
        self.assertEqual(result['status'], 'partial_failure')
        action = self.actions(events)[0]
        self.assertEqual(action['status'], 'partial_failure')
        self.assertTrue(action['changed'])
        self.assertFalse(action['metadata_complete'])
        self.assertEqual(file.stat().st_mode & 0o777, 0o640)
        self.assertEqual(file.read_text(), 'keep')

    def test_mkdir_concurrent_name_creation_keeps_foreign_entry(self):
        request = self.request('mkdir', ['new'])
        marker = self.root / 'notified'
        c = self.client(self.fault_env(self.parent, XSYNC_FAULT_AT_OP='mkdir', XSYNC_FAULT_AT_NAME='new', XSYNC_FAULT_AT_NOTIFY=str(marker)))
        c.send(request)
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline: time.sleep(.01)
        self.assertTrue(marker.exists())
        (self.parent / 'new').mkdir(); (self.parent / 'new' / 'keep').write_text('foreign')
        result = c.finish()
        self.assertNotEqual(result['status'], 'success')
        self.assertEqual((self.parent / 'new' / 'keep').read_text(), 'foreign')
        self.assertFalse(self.actions(c.events)[0]['changed'])

    def test_cancellation_during_recursive_inventory_leaves_tree_intact(self):
        tree = self.parent / 'tree'; tree.mkdir()
        for n in range(100): (tree / str(n)).write_text('keep')
        request = self.request('delete', ['tree'], recursive=True)
        c = self.client(self.fault_env(tree, XSYNC_FAULT_LIST_DELAY_US='20000'))
        c.send(request)
        while True:
            event = c.read()
            if event['type'] == 'phase' and event['phase'] == 'scanning_delete': break
        c.send({'id':'stop', 'op':'cancel', 'job_id':'job'})
        result = c.finish()
        self.assertEqual(result['status'], 'cancellation')
        self.assertEqual(len(list(tree.iterdir())), 100)

    def test_metadata_pins_old_inode_and_reports_replaced_name(self):
        file = self.parent / 'a'; file.write_text('old')
        request = self.request('metadata', ['a'], mtime={'seconds':'1', 'nanoseconds':'0'})
        marker, release = self.root / 'notified', self.root / 'release'
        c = self.client(self.fault_env(file, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker), XSYNC_FAULT_FUTIMENS_RELEASE=str(release)))
        c.send(request)
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline: time.sleep(.01)
        self.assertTrue(marker.exists())
        displaced = self.root / 'displaced'
        file.rename(displaced); file.write_text('new only copy')
        before = file.stat().st_mtime_ns
        release.touch()
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure')
        self.assertEqual(file.read_text(), 'new only copy')
        self.assertEqual(file.stat().st_mtime_ns, before)
        self.assertEqual(displaced.stat().st_mtime_ns, 1000000000)
        self.assertEqual(self.actions(c.events)[0]['status'], 'partial_failure')

    def test_batch_rename_cannot_overwrite_an_alias_of_a_selected_source(self):
        (self.parent / 'a').write_text('first')
        (self.parent / 'b').write_text('second only copy')
        os.link(self.parent / 'b', self.parent / 'alias')
        first = self.request('rename', ['a'], destination_name='alias', replace=True)
        second = self.request('rename', ['b'], destination_name='c', replace=True)
        first['items'].extend(second['items'])
        result, _ = self.run_request(first)
        self.assertEqual(result['status'], 'failure')
        self.assertEqual((self.parent / 'a').read_text(), 'first')
        self.assertEqual((self.parent / 'b').read_text(), 'second only copy')
        self.assertEqual((self.parent / 'alias').read_text(), 'second only copy')

    def test_rename_same_inode_hardlink_is_an_explicit_conflict(self):
        (self.parent / 'a').write_text('keep')
        os.link(self.parent / 'a', self.parent / 'b')
        result, events = self.run_request(self.request('rename', ['a'], destination_name='b', replace=True))
        self.assertNotEqual(result['status'], 'success')
        self.assertFalse(self.actions(events)[0]['changed'])
        self.assertEqual((self.parent / 'a').read_text(), 'keep')
        self.assertIn('same_object_target', [e.get('reason') for e in events if e['type'] == 'error'])


if __name__ == '__main__':
    unittest.main()
