#!/usr/bin/env python3
"""Copy/resume refresh hints, missing receipts and independent pane generations."""
import copy
import errno
import os
import pathlib
import signal
import sys
import time
import unittest

import app_test as api
from app_test import Client, copy_request, endpoint
sys.path.insert(0,str(api.ROOT/'tools'))
from app_client import ListingView


def assert_scope(test, events, path, kind='local'):
    hints = [e for e in events if e['type'] == 'invalidate' and e.get('reason') == 'transfer_attempt']
    test.assertEqual(len(hints),1,events)
    hint = hints[0]
    test.assertEqual(hint['endpoint'],kind)
    test.assertEqual(hint['path']['bytes_hex'],os.fsencode(path).hex())
    test.assertEqual(hint['parent_path']['bytes_hex'],os.fsencode(path.parent).hex())
    test.assertTrue(hint['recursive']); test.assertIsNone(hint['item_id'])
    test.assertLess(events.index(hint),next(i for i,e in enumerate(events) if e['type'] == 'result'))
    return hint


class CopyRefreshTests(unittest.TestCase):
    setUpClass = classmethod(api.AppTests.setUpClass.__func__)
    setUp = api.AppTests.setUp
    client = api.AppTests.client
    job = api.AppTests.job
    fault_env = api.AppTests.fault_env

    def test_mapped_files_directories_and_symlinks_invalidate_actual_destinations(self):
        (self.source/'file').write_bytes(b'copied')
        (self.source/'directory').mkdir(); (self.source/'directory'/'new\nchild').write_bytes(b'nested')
        (self.source/'link').symlink_to('mapped:file')
        request = copy_request(self.source,self.dest)
        request['sources'] = [{'endpoint':endpoint(self.source/name),'mode':'entry',
                               'destination_name':{'bytes_hex':os.fsencode(mapped).hex()}}
                              for name,mapped in [('file','mapped:file'),('directory','mapped *?'),('link','mapped link')]]
        c,result = self.job(request); self.assertEqual(result['status'],'success',c.events)
        self.assertEqual(c.capabilities['copy_invalidation'],'1'); assert_scope(self,c.events,self.dest)
        items = [e for e in c.events if e['type'] == 'item_result' and e['status'] == 'success']
        hints = [e for e in c.events if e['type'] == 'invalidate' and e.get('reason') == 'transfer_item']
        self.assertGreaterEqual(len(items),4); self.assertEqual(len(items),len(hints))
        for item in items:
            hint = next(e for e in hints if e['item_id'] == item['item_id'])
            self.assertEqual(hint['path'],item['destination_path'])
            self.assertEqual(hint['endpoint'],'local')
            self.assertEqual(hint['recursive'],item['entry_type'] == 'directory')
            self.assertGreater(c.events.index(hint),c.events.index(item))
        self.assertEqual((self.dest/'mapped:file').read_bytes(),b'copied')
        self.assertEqual((self.dest/'mapped *?'/'new\nchild').read_bytes(),b'nested')
        self.assertEqual(os.readlink(self.dest/'mapped link'),'mapped:file')

    def test_metadata_failure_still_invalidates_published_content(self):
        (self.source/'file').write_text('published data')
        c,result = self.job(copy_request(self.source,self.dest),self.fault_env(self.dest,XSYNC_FAULT_FUTIMENS_ERROR=str(errno.EPERM)))
        self.assertEqual(result['status'],'partial_failure',c.events)
        item = next(e for e in c.events if e['type'] == 'item_result' and e['entry_type'] == 'file')
        self.assertTrue(item['content_published']); self.assertFalse(item['metadata_complete'])
        self.assertTrue(any(e['type'] == 'invalidate' and e['path'] == item['destination_path'] for e in c.events))
        assert_scope(self,c.events,self.dest)
        self.assertEqual((self.dest/'file').read_text(),'published data')

    def test_ancestor_alias_keeps_the_requested_destination_spelling(self):
        (self.source/'file').write_text('through alias')
        (self.root/'alias').symlink_to(self.root,target_is_directory=True)
        selected = self.root/'alias'/'destination'
        c,result = self.job(copy_request(self.source,selected)); self.assertEqual(result['status'],'success',c.events)
        assert_scope(self,c.events,selected)
        hints = [e for e in c.events if e['type'] == 'invalidate' and e.get('reason') == 'transfer_item']
        self.assertTrue(any(e['path']['bytes_hex'] == os.fsencode(selected/'file').hex() for e in hints),c.events)
        self.assertEqual((self.dest/'file').read_text(),'through alias')

    def test_invalid_utf8_mapped_names_remain_literal_in_refresh_hints(self):
        source = os.fsencode(self.source)+b'/source-\xff'
        try:
            with open(source,'wb') as f: f.write(b'literal bytes')
        except OSError as error:
            if sys.platform == 'darwin' and error.errno in (errno.EINVAL,errno.EILSEQ):
                self.skipTest('host filesystem rejects invalid UTF-8')
            raise
        target = b'mapped-\xfe\n'
        request = copy_request(source,self.dest,mode='entry')
        request['sources'][0]['destination_name'] = {'bytes_hex':target.hex()}
        c,result = self.job(request); self.assertEqual(result['status'],'success',c.events)
        expected = os.fsencode(self.dest)+b'/'+target
        self.assertTrue(any(e['type'] == 'invalidate' and e['path']['bytes_hex'] == expected.hex() for e in c.events),c.events)
        with open(expected,'rb') as f: self.assertEqual(f.read(),b'literal bytes')
        assert_scope(self,c.events,self.dest)

    def test_failed_staging_and_skips_are_conservative_hints_without_success_claims(self):
        (self.source/'file').write_bytes(os.urandom(256*1024)); (self.dest/'file').write_bytes(b'old good copy')
        c,result = self.job(copy_request(self.source,self.dest),self.fault_env(self.dest,XSYNC_FAULT_WRITE_ERROR=str(errno.ENOSPC)))
        self.assertEqual(result['status'],'failure',c.events); assert_scope(self,c.events,self.dest)
        self.assertEqual((self.dest/'file').read_bytes(),b'old good copy')
        c,result = self.job(copy_request(self.source,self.dest,policy='skip'))
        self.assertEqual(result['status'],'success',c.events); assert_scope(self,c.events,self.dest)
        skipped = {e['item_id'] for e in c.events if e['type'] == 'item_result' and e['status'] == 'skipped'}
        self.assertIn(b'file'.hex(),skipped)
        self.assertFalse(any(e['type'] == 'invalidate' and e.get('reason') == 'transfer_item' and e['item_id'] in skipped for e in c.events))
        self.assertEqual((self.dest/'file').read_bytes(),b'old good copy')

    def hold_publication(self):
        (self.source/'file').write_bytes(os.urandom(256*1024)); (self.dest/'file').write_bytes(b'old good copy')
        marker = self.root/'published'
        env = self.fault_env(self.dest,XSYNC_FAULT_PUBLICATION_NOTIFY=str(marker),XSYNC_FAULT_PUBLICATION_HOLD='1')
        c = self.client(env); c.send(copy_request(self.source/'file',self.dest,mode='entry',retain_partials=True))
        deadline = time.monotonic()+10
        while not marker.exists() or not marker.stat().st_size:
            self.assertLess(time.monotonic(),deadline,'publication hold not reached'); time.sleep(.01)
        worker = int(marker.read_text()); self.assertNotEqual(worker,c.proc.pid)
        return c,worker

    def test_fatal_worker_after_publication_invalidates_scope_without_item_receipt(self):
        c,worker = self.hold_publication(); os.kill(worker,signal.SIGKILL)
        result = c.finish(); self.assertEqual(result['status'],'failure',c.events)
        self.assertFalse(any(e['type'] == 'item_result' for e in c.events)); assert_scope(self,c.events,self.dest)
        self.assertEqual((self.dest/'file').read_bytes(),(self.source/'file').read_bytes())

    def test_invalid_active_control_preserves_refresh_after_forced_worker_cleanup(self):
        c,worker = self.hold_publication()
        c.send({'id':'invalid-control','op':'unsupported-control','job_id':'copy'})
        result = c.finish(); self.assertEqual(result['status'],'failure',c.events)
        assert_scope(self,c.events,self.dest)
        self.assertTrue(any(e['type'] == 'error' and e['category'] == 'invalid_request' for e in c.events),c.events)
        self.assertEqual((self.dest/'file').read_bytes(),(self.source/'file').read_bytes())
        with self.assertRaises(ProcessLookupError): os.kill(worker,0)

    def test_pane_refresh_rejects_old_navigation_events_and_reloads_final_tree(self):
        pane = ListingView('list-before',endpoint(self.dest))
        c,result = self.job({'id':'list-before','op':'list','endpoint':endpoint(self.dest)})
        for event in c.events: pane.accept(event)
        self.assertEqual(pane.status,'success'); self.assertEqual(pane.entries,[])
        (self.source/'file').write_text('new pane entry')
        transfer,result = self.job(copy_request(self.source,self.dest)); self.assertEqual(result['status'],'success')
        for event in transfer.events: pane.invalidate(event,endpoint(self.dest))
        self.assertTrue(pane.invalidated); self.assertIsNone(pane.status)
        self.assertFalse(pane.accept({'id':'list-before','type':'entries','entries':[{'stale':True}]}))
        self.assertFalse(pane.accept({'id':'list-before','type':'result','status':'success'}))
        pane.begin('list-after',endpoint(self.dest))
        refreshed,result = self.job({'id':'list-after','op':'list','endpoint':endpoint(self.dest)})
        for event in refreshed.events: pane.accept(event)
        self.assertFalse(pane.invalidated); self.assertEqual(pane.status,'success')
        self.assertEqual([e['name']['bytes_hex'] for e in pane.entries],[b'file'.hex()])

    def test_pane_hints_bind_byte_paths_and_ssh_profiles_without_cross_job_navigation(self):
        target = endpoint(self.dest/'sub'); target.update(kind='ssh',connection={'host':'first','user':'alice'})
        hint = {'id':'another-job','type':'invalidate','endpoint':'ssh','path':endpoint(self.dest)['path'],
                'parent_path':endpoint(self.root)['path'],'recursive':True}
        pane = ListingView('browse',target)
        foreign = copy.deepcopy(target); foreign['connection']['host'] = 'second'
        self.assertFalse(pane.invalidate(hint,foreign)); self.assertFalse(pane.invalidated)
        unknown = copy.deepcopy(target); unknown.pop('connection')
        self.assertFalse(pane.invalidate(hint,unknown)); self.assertFalse(ListingView('unknown',unknown).invalidate(hint,unknown))
        shallow = dict(hint,recursive=False); self.assertFalse(pane.invalidate(shallow,target))
        self.assertTrue(pane.invalidate(hint,target)); self.assertTrue(pane.invalidated)
        pane.begin('new-pane',dict(target,path=endpoint(self.root/'destination-extra')['path']))
        self.assertFalse(pane.invalidate(hint,target)); self.assertFalse(pane.invalidated)
        pane.begin('root',dict(target,path=endpoint('/')['path']))
        root_hint = dict(hint,path=endpoint('/')['path'],parent_path=endpoint('/')['path'])
        self.assertTrue(pane.invalidate(root_hint,target))

    def test_read_only_jobs_and_invalid_copy_requests_emit_no_transfer_hints(self):
        for op in ('list','lstat','preflight'):
            c,result = self.job({'id':'observation','op':op,'endpoint':endpoint(self.dest)})
            self.assertEqual(result['status'],'success',c.events)
            self.assertFalse(any(e['type'] == 'invalidate' for e in c.events))
        request = copy_request(self.source,self.dest); request['options']['jobs'] = False
        c,result = self.job(request); self.assertEqual(result['status'],'failure',c.events)
        self.assertFalse(any(e['type'] == 'invalidate' for e in c.events))


if __name__ == '__main__': unittest.main()
