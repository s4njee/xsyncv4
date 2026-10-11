#!/usr/bin/env python3
"""Read-only comparison, explicit mirror proposals and stale-copy guards."""
import copy
import errno
import json
import os
import pathlib
import subprocess
import sys
import time
import unittest

import app_test as api
from app_test import copy_request, endpoint
sys.path.insert(0,str(api.ROOT/'tools'))
from app_client import AppClient, TransferPreview


class PreviewTests(unittest.TestCase):
    setUpClass=classmethod(api.AppTests.setUpClass.__func__)
    setUp=api.AppTests.setUp
    client=api.AppTests.client
    job=api.AppTests.job
    fault_env=api.AppTests.fault_env

    def request(self, mode='selected_copy',policy='replace'):
        request=copy_request(self.source,self.dest,policy=policy)
        request.update(id='preview',op='preview',mode=mode)
        return request

    def plan(self,request=None,env=None):
        request=request or self.request(); c,result=self.job(request,env)
        view=TransferPreview(request)
        for event in c.events: view.accept(event)
        return c,result,view

    def snapshot(self):
        result={}
        for folder in (self.source,self.dest):
            for p in [folder,*folder.rglob('*')]:
                st=p.lstat()
                result[str(p)]=(st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns,
                    os.readlink(p) if p.is_symlink() else p.read_bytes() if p.is_file() else None)
        return result

    def test_selected_copy_and_mirror_proposals_never_write_or_authorize_deletion(self):
        (self.source/'new\nfile').write_bytes(b'new data'); (self.source/'folder').mkdir()
        (self.dest/'extra').mkdir(); (self.dest/'extra'/'old').write_bytes(b'keep')
        before=self.snapshot()
        c,result,selected=self.plan(env=self.fault_env(self.root,XSYNC_FAULT_WRITE_ERROR=str(errno.ENOSPC)))
        self.assertEqual(result['status'],'success',c.events); self.assertEqual(before,self.snapshot())
        self.assertFalse(any(e['type']=='invalidate' for e in c.events))
        self.assertEqual(c.capabilities['transfer_preview'],'1'); self.assertIn('preview',c.capabilities['operations'])
        self.assertEqual(c.capabilities['preview_revision_binding'],'1')
        self.assertEqual(c.capabilities['preview_revision_binding_endpoint_kinds'],['local','ssh'])
        self.assertFalse(any(i['action']=='delete' for i in selected.items))
        self.assertTrue(any(i['action']=='copy' and bytes.fromhex(i['path']['bytes_hex'])==b'new\nfile' for i in selected.items))
        self.assertEqual(selected.summary['direction'],'local'); self.assertTrue(selected.summary['complete'])
        _,result,mirror=self.plan(self.request('mirror')); self.assertEqual(result['status'],'success')
        self.assertEqual(before,self.snapshot()); self.assertEqual(mirror.summary['counts']['delete'],'2')
        self.assertFalse(mirror.summary['deletion_authorized']); self.assertFalse(mirror.summary['execution_supported'])
        with self.assertRaises(ValueError): mirror.execution_request('copy')

    def test_source_budget_is_verified_from_metadata_with_explicit_physical_unknowns(self):
        (self.source/'a').write_bytes(b'a'*9000); (self.source/'b').write_bytes(b'b'*2000)
        (self.source/'link').symlink_to('a'); (self.dest/'old').write_bytes(b'old')
        request=self.request(); request['options']['jobs']='1'
        c,result,view=self.plan(request); self.assertEqual(result['status'],'success',c.events)
        budget=next(e['space'] for e in c.events if e['type']=='destination_preflight')
        self.assertTrue(budget['inputs_verified']); self.assertFalse(budget['source_content_verified'])
        self.assertEqual(budget['copy_logical_bytes'],'11000'); self.assertEqual(budget['atomic_staging_peak_logical_bytes'],'9000')
        self.assertEqual(view.summary['regular_data_upper_bound_bytes'],'11000')
        for key in ('retained_logical_bytes','coexisting_data_logical_bytes','physical_requirement_bytes','quota_remaining_bytes'):
            self.assertIsNone(budget[key])
        self.assertFalse(budget['retained_data_inventory_complete'])

    def test_guarded_execution_revalidates_and_preserves_unselected_entries(self):
        (self.source/'file').write_bytes(b'new data'); (self.dest/'other').write_bytes(b'unselected')
        _,result,view=self.plan(); self.assertEqual(result['status'],'success')
        _,result,repeated=self.plan(); self.assertEqual(result['status'],'success')
        self.assertEqual(view.summary['token'],repeated.summary['token'])
        c,result=self.job(view.execution_request('copy')); self.assertEqual(result['status'],'success',c.events)
        self.assertEqual(sum(e['type']=='preview_revalidated' for e in c.events),1)
        self.assertLess(next(i for i,e in enumerate(c.events) if e['type']=='preview_revalidated'),
                        next(i for i,e in enumerate(c.events) if e['type']=='item_discovered'))
        self.assertEqual((self.dest/'file').read_bytes(),b'new data'); self.assertEqual((self.dest/'other').read_bytes(),b'unselected')

    def test_changed_sources_destinations_and_options_block_all_staging(self):
        (self.source/'file').write_bytes(b'new data'); (self.dest/'file').write_bytes(b'old good')
        for change in ('source','destination','extra','options'):
            with self.subTest(change=change):
                _,result,view=self.plan(); self.assertEqual(result['status'],'success')
                request=view.execution_request('copy')
                if change=='source': (self.source/'file').write_bytes(b'source changed')
                elif change=='destination': (self.dest/'file').write_bytes(b'external copy')
                elif change=='extra': (self.dest/'new child').write_bytes(b'external child')
                else: request['options']['preserve_times']=False
                before=self.snapshot(); c,result=self.job(request)
                self.assertNotEqual(result['status'],'success',c.events); self.assertEqual(before,self.snapshot())
                self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' for e in c.events),c.events)
                self.assertFalse(any(e['type']=='item_discovered' or e['type']=='preview_revalidated' for e in c.events))
                self.assertFalse((self.dest/'.xsync-app-partials').exists())

    def wait_marker(self,marker,client):
        deadline=time.monotonic()+5
        while not marker.exists() and time.monotonic()<deadline and client.proc.poll() is None: time.sleep(.01)
        self.assertTrue(marker.exists(),'native copy never reached the fault barrier')

    def reply(self,client,event,decision):
        client.send({'id':'decision-'+event['conflict_id'],'op':'conflict_response','conflict_id':event['conflict_id'],
                     'job_id':'copy','revision_token':event['revision_token'],'decision':decision})

    def test_guard_rejects_destination_changed_while_waiting_for_decision(self):
        (self.source/'file').write_bytes(b'incoming'); target=self.dest/'file'; target.write_bytes(b'old')
        _,result,view=self.plan(self.request(policy='ask')); self.assertEqual(result['status'],'success')
        c=self.client(); c.send(view.execution_request('copy'))
        while True:
            event=c.read()
            if event['type']=='conflict': break
        target.write_bytes(b'external replacement'); self.reply(c,event,'replace')
        result=c.finish(); self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertEqual(target.read_bytes(),b'external replacement')
        self.assertEqual(sum(e['type']=='conflict' for e in c.events),1)
        self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' for e in c.events))

    def test_guard_rejects_source_changed_during_read_instead_of_retrying_new_content(self):
        source=self.source/'file'; source.write_bytes(b'a'*(2<<20)); target=self.dest/'file'; target.write_bytes(b'good')
        _,result,view=self.plan(); self.assertEqual(result['status'],'success')
        marker=self.root/'read'; c=self.client(self.fault_env(source,XSYNC_FAULT_READ_NOTIFY=str(marker),XSYNC_FAULT_READ_DELAY_US='400000'))
        c.send(view.execution_request('copy')); self.wait_marker(pathlib.Path(str(marker)+'.1'),c)
        source.write_bytes(b'b'*(2<<20))
        result=c.finish(); self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertEqual(target.read_bytes(),b'good')
        self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' and e.get('side')=='source' for e in c.events))

    def test_guard_rejects_destination_changed_after_staging_before_publication(self):
        (self.source/'file').write_bytes(b'incoming'*2000); target=self.dest/'file'; target.write_bytes(b'old')
        _,result,view=self.plan(); self.assertEqual(result['status'],'success')
        marker=self.root/'writing'; c=self.client(self.fault_env(self.dest,XSYNC_FAULT_WRITE_NOTIFY=str(marker),XSYNC_FAULT_WRITE_DELAY_US='400000'))
        c.send(view.execution_request('copy')); self.wait_marker(marker,c)
        target.write_bytes(b'external replacement')
        result=c.finish(); self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertEqual(target.read_bytes(),b'external replacement')
        self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' and e.get('side')=='destination' for e in c.events))
        self.assertEqual([p.name for p in self.dest.iterdir()],['file'])

    def test_guard_rejects_changed_symlink_source_after_conflict_decision(self):
        source=self.source/'link'; source.symlink_to('old source target'); target=self.dest/'link'; target.symlink_to('good target')
        _,result,view=self.plan(self.request(policy='ask')); self.assertEqual(result['status'],'success')
        c=self.client(); c.send(view.execution_request('copy'))
        while True:
            event=c.read()
            if event['type']=='conflict': break
        source.unlink(); source.symlink_to('changed source target'); self.reply(c,event,'replace')
        result=c.finish(); self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertEqual(os.readlink(target),'good target')
        self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' and e.get('side')=='source' for e in c.events))

    def test_guard_binds_directory_source_before_final_metadata_restoration(self):
        source=self.source/'folder'; source.mkdir(); (source/'file').write_bytes(b'incoming'*2000)
        _,result,view=self.plan(); self.assertEqual(result['status'],'success')
        marker=self.root/'writing'; c=self.client(self.fault_env(self.dest,XSYNC_FAULT_WRITE_NOTIFY=str(marker),XSYNC_FAULT_WRITE_DELAY_US='400000'))
        c.send(view.execution_request('copy')); self.wait_marker(marker,c); source.chmod(0o750)
        result=c.finish(); self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertTrue(any(e['type']=='item_result' and e['entry_type']=='directory' and e['status']=='failure' and e.get('reason')=='stale_preview' for e in c.events))
        self.assertNotEqual((self.dest/'folder').stat().st_mode&0o777,0o750)

    def test_guard_rechecks_source_ancestors_before_publication(self):
        folder=self.source/'folder'; folder.mkdir(); (folder/'file').write_bytes(b'incoming'*2000)
        target=self.dest/'folder'; target.mkdir(); (target/'file').write_bytes(b'good')
        _,result,view=self.plan(); self.assertEqual(result['status'],'success')
        marker=self.root/'writing'; c=self.client(self.fault_env(self.dest,XSYNC_FAULT_WRITE_NOTIFY=str(marker),XSYNC_FAULT_WRITE_DELAY_US='400000'))
        c.send(view.execution_request('copy')); self.wait_marker(marker,c)
        (folder/'unexpected').write_bytes(b'changed source inventory')
        result=c.finish(); self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertEqual((target/'file').read_bytes(),b'good')
        self.assertFalse((target/'unexpected').exists())
        self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' and e.get('side')=='source' and e['path']['bytes_hex']==os.fsencode(folder).hex() for e in c.events))

    def test_guard_binds_virtual_destination_root_for_entry_selections(self):
        source=self.source/'file'; source.write_bytes(b'incoming'*2000); target=self.dest/'file'; target.write_bytes(b'good')
        request=self.request(); request['sources']=[{'endpoint':endpoint(source),'mode':'entry'}]
        _,result,view=self.plan(request); self.assertEqual(result['status'],'success')
        marker=self.root/'writing'; c=self.client(self.fault_env(self.dest,XSYNC_FAULT_WRITE_NOTIFY=str(marker),XSYNC_FAULT_WRITE_DELAY_US='400000'))
        c.send(view.execution_request('copy')); self.wait_marker(marker,c); self.dest.chmod(0o750)
        result=c.finish(); self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertEqual(target.read_bytes(),b'good')
        self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' and e['path']['bytes_hex']==os.fsencode(self.dest).hex() for e in c.events))

    def test_guard_preserves_changed_destination_ancestor_and_marks_affected_leaf(self):
        source=self.source/'folder'; source.mkdir(); (source/'file').write_bytes(b'incoming'*2000)
        folder=self.dest/'folder'; folder.mkdir(); (folder/'file').write_bytes(b'good')
        _,result,view=self.plan(); self.assertEqual(result['status'],'success')
        marker=self.root/'writing'; c=self.client(self.fault_env(self.dest,XSYNC_FAULT_WRITE_NOTIFY=str(marker),XSYNC_FAULT_WRITE_DELAY_US='400000'))
        c.send(view.execution_request('copy')); self.wait_marker(marker,c); folder.chmod(0o750)
        result=c.finish(); self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertEqual((folder/'file').read_bytes(),b'good'); self.assertEqual(folder.stat().st_mode&0o777,0o750)
        self.assertTrue(any(e['type']=='item_result' and e['entry_type']=='file' and e['status']=='failure' and e.get('reason')=='stale_preview' for e in c.events))

    def test_guard_accepts_root_permission_changes_owned_by_copy(self):
        (self.source/'file').write_bytes(b'incoming'); self.dest.chmod(0o500)
        try:
            _,result,view=self.plan(); self.assertEqual(result['status'],'success')
            c,result=self.job(view.execution_request('copy')); self.assertEqual(result['status'],'success',c.events)
            self.assertEqual((self.dest/'file').read_bytes(),b'incoming')
            self.assertEqual(self.dest.stat().st_mode&0o777,self.source.stat().st_mode&0o777)
        finally: self.dest.chmod(0o700)

    def test_guard_preserves_contents_selection_through_dot_path_alias(self):
        (self.source/'file').write_bytes(b'incoming')
        request=self.request(); request['sources'][0]['endpoint']=endpoint(str(self.source)+'/.')
        _,result,view=self.plan(request); self.assertEqual(result['status'],'success')
        c,result=self.job(view.execution_request('copy')); self.assertEqual(result['status'],'success',c.events)
        self.assertEqual((self.dest/'file').read_bytes(),b'incoming')

    def test_guard_allows_owned_directory_mutations_and_explicit_keep_both_mapping(self):
        for retain in (False,True):
            with self.subTest(retain=retain):
                source=self.source/str(retain); source.mkdir(); (source/'child').mkdir()
                (source/'child'/'file').write_bytes(b'incoming'); (source/'link').symlink_to('child/file')
                target=self.dest/str(retain); target.mkdir(); (target/'old').write_bytes(b'keep')
                request=self.request(policy='ask'); request['sources']=[{'endpoint':endpoint(source),'mode':'entry'}]
                request['options']['retain_partials']=retain
                _,result,view=self.plan(request); self.assertEqual(result['status'],'success')
                c=self.client(); c.send(view.execution_request('copy'))
                while True:
                    event=c.read()
                    if event['type']=='conflict': self.reply(c,event,'keep_both')
                    if event['type']=='result': break
                self.assertEqual(event['status'],'success',c.events); c.proc.wait(timeout=5)
                self.assertEqual((target/'old').read_bytes(),b'keep')
                copied=self.dest/(str(retain)+' (copy 1)')
                self.assertEqual((copied/'child'/'file').read_bytes(),b'incoming')
                self.assertEqual(os.readlink(copied/'link'),'child/file')

    def test_conflicts_skips_and_metadata_updates_have_reasons_and_conditional_bounds(self):
        (self.source/'file').write_bytes(b'incoming'); (self.dest/'file').write_bytes(b'old')
        (self.source/'folder').mkdir(); (self.dest/'folder').mkdir()
        (self.source/'folder').chmod(0o750); (self.dest/'folder').chmod(0o700)
        c,result,view=self.plan(self.request(policy='ask')); self.assertEqual(result['status'],'success',c.events)
        file=next(i for i in view.items if bytes.fromhex(i['path']['bytes_hex'])==b'file')
        self.assertEqual(file['action'],'conflict'); self.assertTrue(file['conditional'])
        self.assertEqual(view.summary['regular_data_upper_bound_bytes'],'8')
        self.assertTrue(any(i['action']=='metadata_update' and i['reason']=='directory_merge' for i in view.items))
        _,result,view=self.plan(self.request(policy='skip')); self.assertEqual(result['status'],'success')
        self.assertEqual(view.summary['regular_data_upper_bound_bytes'],'0')
        self.assertTrue(any(i['action']=='skip' and i['reason']=='existing_destination' for i in view.items))

    def test_incomplete_scan_cannot_return_guard_or_delete_anything(self):
        (self.source/'file').write_bytes(b'incoming'); (self.dest/'old').write_bytes(b'keep')
        before=self.snapshot()
        c,result,view=self.plan(self.request('mirror'),self.fault_env(self.source,XSYNC_FAULT_LIST_AFTER='0'))
        self.assertNotEqual(result['status'],'success',c.events); self.assertFalse(view.summary['complete'])
        self.assertIsNone(view.summary['token']); self.assertIsNone(view.summary['execution_guard'])
        self.assertFalse(view.summary['deletion_authorized']); self.assertEqual(before,self.snapshot())
        with self.assertRaises(ValueError): view.execution_request('copy')

    def test_invalid_preview_fields_and_guards_fail_before_filesystem_changes(self):
        before=self.snapshot()
        for change in ({'mode':'two_way'},{'mode':False},{'extra':True}):
            request=self.request(); request.update(change)
            c,result=self.job(request); self.assertEqual(result['status'],'failure',c.events)
            self.assertFalse(any(e['type']=='preview_item' for e in c.events))
        request=self.request(); request['options']['delete']=True
        self.assertEqual(self.job(request)[1]['status'],'failure')
        request=self.request(); request['sources'][0]['delete']=True
        self.assertEqual(self.job(request)[1]['status'],'failure')
        request=copy_request(self.source,self.dest); request['expected_preview']={'version':'1','mode':'mirror','token':'a'*32}
        self.assertEqual(self.job(request)[1]['status'],'failure'); self.assertEqual(before,self.snapshot())

    def test_unsupported_source_is_blocked_without_a_usable_execution_guard(self):
        os.mkfifo(self.source/'fifo'); before=self.snapshot()
        c,result,view=self.plan(); self.assertNotEqual(result['status'],'success',c.events)
        self.assertFalse(view.summary['complete']); self.assertIsNone(view.summary['execution_guard'])
        self.assertTrue(any(i['action']=='blocked' and i['reason']=='unsupported_source' for i in view.items))
        self.assertEqual(before,self.snapshot())

    def test_depth_limit_returns_only_an_incomplete_nonexecutable_proposal(self):
        folder=self.source
        for i in range(256): folder=folder/'d'; folder.mkdir()
        c,result,view=self.plan(); self.assertNotEqual(result['status'],'success',c.events)
        self.assertEqual(c.capabilities['preview_max_depth'],'256')
        self.assertFalse(view.summary['complete']); self.assertIsNone(view.summary['execution_guard'])
        self.assertTrue(any(e['type']=='error' and e.get('reason')=='preview_inventory_limit' for e in c.events),c.events)

    def test_child_copy_plans_directory_time_restoration_and_does_not_follow_links(self):
        (self.source/'file').write_bytes(b'new'); (self.source/'link').symlink_to(self.dest,target_is_directory=True)
        stamp=1600000000123456789
        for p in (self.source,self.dest): os.utime(p,ns=(stamp,stamp))
        before=self.snapshot(); c,result,view=self.plan(); self.assertEqual(result['status'],'success',c.events)
        root=next(i for i in view.items if i['item_id']=='')
        self.assertEqual(root['action'],'metadata_update'); self.assertEqual(root['reason'],'directory_children_may_change_times')
        self.assertTrue(any(i['entry_type']=='symlink' for i in view.items)); self.assertEqual(before,self.snapshot())

    def test_existing_case_alias_is_reported_at_its_actual_destination_name(self):
        (self.source/'Case').write_bytes(b'new'); (self.dest/'case').write_bytes(b'old')
        c,result,view=self.plan(); self.assertEqual(result['status'],'success',c.events)
        rules=next(e['names'] for e in c.events if e['type']=='destination_preflight')
        if rules['case_sensitive'] is not False: self.skipTest('requires detected case-insensitive destination')
        row=next(i for i in view.items if i['entry_type']=='file' and i['source_path'] is not None)
        self.assertEqual(row['destination_path']['bytes_hex'],os.fsencode(self.dest/'case').hex())
        self.assertEqual(row['action'],'copy'); self.assertEqual(row['reason'],'replace_regular_file')

    def test_planned_case_collisions_mark_both_source_items(self):
        (self.source/'one').write_bytes(b'one'); (self.source/'two').write_bytes(b'two')
        request=self.request(); request['sources']=[{'endpoint':endpoint(self.source/n),'mode':'entry','destination_name':{'bytes_hex':mapped.hex()}}
                                                   for n,mapped in [('one',b'Alias'),('two',b'alias')]]
        c,result,view=self.plan(request); self.assertEqual(result['status'],'success',c.events)
        rules=next(e['names'] for e in c.events if e['type']=='destination_preflight')
        if rules['case_sensitive'] is not False: self.skipTest('requires detected case-insensitive destination')
        self.assertEqual(view.summary['counts']['conflict'],'2')
        self.assertTrue(all(i['conditional'] and i['reason']=='planned_name_collision' for i in view.items if i['source_path'] is not None))
        self.assertEqual(view.summary['regular_data_upper_bound_bytes'],'6')

    def test_cancellation_during_inventory_never_writes_or_returns_a_guard(self):
        for i in range(40): (self.source/str(i)).write_bytes(b'new')
        (self.dest/'old').write_bytes(b'keep'); before=self.snapshot()
        c=self.client(self.fault_env(self.source,XSYNC_FAULT_LIST_DELAY_US='50000')); c.send(self.request('mirror'))
        while c.read()['type']!='phase': pass
        time.sleep(.3); c.send({'id':'cancel','op':'cancel','job_id':'preview'})
        result=c.finish(); self.assertEqual(result['status'],'cancellation',c.events); self.assertEqual(before,self.snapshot())
        self.assertFalse(any(e['type']=='preview_summary' and e['execution_guard'] is not None for e in c.events))

    def test_reference_client_requires_exact_engine_capability_before_guard_submission(self):
        request=copy_request(self.source,self.dest); request['expected_preview']={'version':'1','mode':'selected_copy','token':'a'*32}
        for capability in (None,False,1,'2'):
            client=AppClient(api.BINARY)
            try:
                client.capabilities['transfer_preview']=capability
                with self.assertRaises(RuntimeError): list(client.run(request))
            finally: client.close()
        self.assertEqual(list(self.dest.iterdir()),[])

    def test_reference_cli_preview_has_no_tty_and_no_destination_writes(self):
        (self.source/'file').write_bytes(b'new'); (self.dest/'old').write_bytes(b'old')
        before=self.snapshot()
        done=subprocess.run([sys.executable,str(api.ROOT/'tools/app_client.py'),'--binary',str(api.BINARY),
            'preview',str(self.source),str(self.dest),'--contents','--on-conflict','replace','--mode','mirror'],
            stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=10)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr); self.assertEqual(before,self.snapshot())
        events=[json.loads(line) for line in done.stdout.splitlines()]
        self.assertFalse(next(e for e in events if e['type']=='preview_summary')['execution_supported'])
        self.assertEqual(events[-1]['status'],'success')


if __name__=='__main__': unittest.main()
