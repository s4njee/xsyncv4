#!/usr/bin/env python3
"""Reference retries retain nested destinations instead of flattening them."""
import unittest

import app_test as api
from app_test import copy_request, inventory, endpoint


class AppRetryTests(unittest.TestCase):
    setUpClass = classmethod(api.AppTests.setUpClass.__func__)
    setUp = api.AppTests.setUp
    fault_env = api.AppTests.fault_env
    client = api.AppTests.client
    job = api.AppTests.job

    def test_nested_failed_item_retries_only_its_original_destination(self):
        (self.source / 'outer').mkdir()
        leaf = self.source / 'outer' / 'file'; leaf.write_text('incoming nested bytes')
        (self.source / 'good').write_text('completed sibling')
        (self.dest / 'outer').mkdir()
        target = self.dest / 'outer' / 'file'; target.write_text('old nested copy')
        (self.dest / 'file').write_text('unselected root sibling')
        request = copy_request(self.source, self.dest)
        c, result = self.job(request, self.fault_env(leaf, XSYNC_FAULT_READ_ERROR='1'))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        view = inventory(c.events)
        self.assertEqual(view.items[b'outer'.hex()]['status'], 'success')
        self.assertEqual(view.items[b'outer/file'.hex()]['status'], 'failure')
        with self.assertRaises(ValueError): view.retry_selections()
        retries = view.retry_requests(request)
        self.assertEqual(len(retries), 1)
        self.assertEqual(retries[0]['destination'], endpoint(self.dest / 'outer'))
        self.assertEqual(retries[0]['sources'], [{'endpoint': endpoint(leaf), 'mode': 'entry'}])
        _, retried = self.job(retries[0])
        self.assertEqual(retried['status'], 'success')
        self.assertEqual(target.read_text(), 'incoming nested bytes')
        self.assertEqual((self.dest / 'file').read_text(), 'unselected root sibling')
        self.assertEqual((self.dest / 'good').read_text(), 'completed sibling')

    def test_retry_groups_byte_paths_and_keeps_profiles_options_and_unknown_opt_in(self):
        from app_client import TransferInventory
        request = copy_request(self.source, self.dest)
        view = TransferInventory(request['id'])
        for name, status in ((b'a/new\nline', 'failure'), (b'b/colon:name', 'failure'), (b'c/file', 'pending')):
            source = bytes(str(self.source), 'utf8') + b'/' + name
            target = bytes(str(self.dest), 'utf8') + b'/' + name
            view.accept({'id': request['id'], 'type': 'item_discovered', 'item_id': name.hex(),
                         'path': {'bytes_hex': name.hex()}, 'source_path': {'bytes_hex': source.hex()},
                         'destination_path': {'bytes_hex': target.hex()}, 'source_endpoint': 'local',
                         'destination_endpoint': 'local', 'entry_type': 'file'})
            if status == 'failure':
                view.accept({'id': request['id'], 'type': 'item_result', 'item_id': name.hex(), 'status': status})
        view.finish('interrupted')
        self.assertEqual(len(view.retry_requests(request)), 2)
        retries = view.retry_requests(request, include_unknown=True)
        self.assertEqual(len(retries), 3)
        self.assertEqual([r['destination']['path']['bytes_hex'] for r in retries],
                         [bytes(str(self.dest / x), 'utf8').hex() for x in ('c', 'a', 'b')])
        retries[0]['options']['on_conflict'] = 'skip'
        self.assertEqual(request['options']['on_conflict'], 'replace')
        with self.assertRaises(ValueError): view.retry_requests(dict(request, id='another'))

    def test_cancelled_items_never_enter_retry_failed_even_with_unknown_opt_in(self):
        from app_client import TransferInventory
        request = copy_request(self.source, self.dest)
        view = TransferInventory(request['id'])
        for name, status in (('failed', 'failure'), ('cancelled', 'cancellation')):
            view.accept({'id':request['id'], 'type':'item_discovered', 'item_id':name,
                         'path':{'bytes_hex':name.encode().hex()}, 'source_path':{'bytes_hex':bytes(str(self.source / name), 'utf8').hex()},
                         'destination_path':{'bytes_hex':bytes(str(self.dest / name), 'utf8').hex()},
                         'source_endpoint':'local', 'destination_endpoint':'local', 'entry_type':'file'})
            view.accept({'id':request['id'], 'type':'item_result', 'item_id':name, 'status':status})
        for include_unknown in (False, True):
            retries = view.retry_requests(request, include_unknown=include_unknown)
            self.assertEqual(len(retries), 1)
            self.assertEqual(retries[0]['sources'][0]['endpoint'], endpoint(self.source / 'failed'))
        view.finish('cancellation')
        self.assertEqual(view.retry_requests(request, include_unknown=True), [])


if __name__ == '__main__': unittest.main()
