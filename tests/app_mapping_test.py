#!/usr/bin/env python3
"""Explicit literal selection mappings and destination-preserving retry."""
import copy
import os
import unittest
import app_test as api
from app_test import endpoint, copy_request, inventory


class AppMappingTests(unittest.TestCase):
    setUpClass = classmethod(api.AppTests.setUpClass.__func__)
    setUp = api.AppTests.setUp
    fault_env = api.AppTests.fault_env
    client = api.AppTests.client
    job = api.AppTests.job

    def selection(self, path, name):
        return {'endpoint': endpoint(path), 'mode': 'entry', 'destination_name': {'bytes_hex': os.fsencode(name).hex()}}

    def test_literal_mapped_files_directories_and_symlinks_keep_actual_sources(self):
        (self.source / 'a').mkdir(); (self.source / 'b').mkdir()
        first = self.source / 'a' / 'file'; first.write_text('first object')
        second = self.source / 'b' / 'file'; second.write_text('second object')
        folder = self.source / 'folder'; folder.mkdir(); (folder / 'nested').write_text('inside folder')
        link = self.source / 'link'; link.symlink_to('literal target')
        (self.source / 'unselected').write_text('source sentinel')
        (self.dest / 'file').write_text('destination sentinel')
        request = copy_request(self.source, self.dest)
        request['sources'] = [self.selection(first, 'colon:name'), self.selection(second, '*?\nline'),
                              self.selection(folder, '-renamed folder'), self.selection(link, 'renamed link')]
        c, result = self.job(request)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['*?\nline', '-renamed folder', 'colon:name', 'file', 'renamed link'])
        self.assertEqual((self.dest / 'colon:name').read_text(), 'first object')
        self.assertEqual((self.dest / '*?\nline').read_text(), 'second object')
        self.assertEqual((self.dest / '-renamed folder' / 'nested').read_text(), 'inside folder')
        self.assertEqual((self.dest / 'renamed link').readlink(), link.readlink())
        self.assertEqual((self.dest / 'file').read_text(), 'destination sentinel')
        view = inventory(c.events)
        for selection in request['sources']:
            identity = selection['destination_name']['bytes_hex']
            self.assertEqual(view.items[identity]['source_path'], dict(selection['endpoint']['path'], display=view.items[identity]['source_path']['display']))
        self.assertIn(b'-renamed folder/nested'.hex(), view.items)
        self.assertTrue(c.capabilities['selection_mappings'])

    def test_mapped_name_uses_explicit_skip_replace_and_retry_mapping(self):
        source = self.source / 'original'; source.write_text('incoming bytes')
        (self.dest / 'original').write_text('unselected sibling')
        target = self.dest / 'renamed'; target.write_text('old good copy')
        request = copy_request(source, self.dest, mode='entry', policy='skip')
        request['sources'] = [self.selection(source, 'renamed')]
        c, result = self.job(request)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(inventory(c.events).items[b'renamed'.hex()]['status'], 'skipped')
        self.assertEqual(target.read_text(), 'old good copy')
        request['options']['on_conflict'] = 'replace'
        c, result = self.job(request, self.fault_env(source, XSYNC_FAULT_READ_ERROR='1'))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        view = inventory(c.events)
        self.assertEqual(view.retry_selections(), request['sources'])
        retries = view.retry_requests(request)
        self.assertEqual(retries[0]['sources'], request['sources'])
        _, result = self.job(retries[0])
        self.assertEqual(result['status'], 'success')
        self.assertEqual(target.read_text(), 'incoming bytes')
        self.assertEqual((self.dest / 'original').read_text(), 'unselected sibling')

    def test_mapping_validation_and_failed_preflight_do_not_mutate_destination(self):
        source = self.source / 'file'; source.write_text('incoming')
        request = copy_request(source, self.dest, mode='entry')
        request['sources'] = [self.selection(source, 'mapped')]
        for name in (b'', b'.', b'..', b'/absolute', b'one/two', b'has\0nul', b'x'*256):
            candidate = copy.deepcopy(request); candidate['sources'][0]['destination_name']['bytes_hex'] = name.hex()
            _, result = self.job(candidate)
            self.assertEqual(result['status'], 'failure')
            self.assertEqual(list(self.dest.iterdir()), [])
        candidate = copy.deepcopy(request); candidate['sources'][0]['mode'] = 'contents'
        _, result = self.job(candidate); self.assertEqual(result['status'], 'failure')
        candidate = copy.deepcopy(request); candidate['sources'].append(self.selection(self.source / 'absent', 'mapped'))
        _, result = self.job(candidate); self.assertEqual(result['status'], 'failure')
        candidate = copy.deepcopy(request); candidate['sources'].append(self.selection(self.source / 'absent', 'missing mapped'))
        c, result = self.job(candidate)
        self.assertEqual(result['status'], 'failure', c.events)
        view = inventory(c.events)
        self.assertEqual(view.items[b'missing mapped'.hex()]['status'], 'failure')
        self.assertEqual(view.items[b'mapped'.hex()]['status'], 'skipped')
        self.assertEqual(view.retry_requests(candidate)[0]['sources'], [candidate['sources'][1]])
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_mapped_invalid_utf8_name_when_filesystem_supports_it(self):
        source = self.source / 'file'; source.write_text('incoming')
        target = os.fsencode(self.dest) + b'/mapped-\xff'
        try:
            with open(target, 'wb') as f: f.write(b'old')
        except OSError:
            self.skipTest('filesystem rejects invalid UTF-8 names')
        request = copy_request(source, self.dest, mode='entry')
        request['sources'] = [self.selection(source, b'mapped-\xff')]
        c, result = self.job(request)
        self.assertEqual(result['status'], 'success', c.events)
        with open(target, 'rb') as f: self.assertEqual(f.read(), b'incoming')
        self.assertEqual(inventory(c.events).items[b'mapped-\xff'.hex()]['status'], 'success')


if __name__ == '__main__': unittest.main()
