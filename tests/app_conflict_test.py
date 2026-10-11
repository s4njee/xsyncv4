#!/usr/bin/env python3
"""Interactive decisions bind to native destination revisions and preserve siblings."""
import os
import json
import subprocess
import sys
import threading
import time
import unittest
import app_test as api
from app_test import copy_request, inventory


class AppConflictTests(unittest.TestCase):
    setUpClass = classmethod(api.AppTests.setUpClass.__func__)
    setUp = api.AppTests.setUp
    fault_env = api.AppTests.fault_env
    client = api.AppTests.client
    wait_marker = api.AppTests.wait_marker

    def reply(self, c, event, decision='replace', **fields):
        c.send({'id': 'decision-' + event['conflict_id'], 'op': 'conflict_response', 'job_id': 'copy',
                'conflict_id': event['conflict_id'], 'revision_token': event['revision_token'],
                'decision': decision, **fields})

    def finish(self, c, handler):
        while True:
            e = c.read()
            if e['type'] == 'conflict': handler(e)
            if e['type'] == 'result':
                c.proc.wait(timeout=6)
                return e

    def fixture(self):
        source = self.source / 'file'; source.write_text('incoming')
        target = self.dest / 'file'; target.write_text('old copy')
        return source, target

    def test_replace_skip_and_keep_both_are_explicit_and_inventory_maps_actual_output(self):
        source, target = self.fixture()
        for action in ('skip', 'keep_both', 'replace'):
            c = self.client(); c.send(copy_request(source, self.dest, mode='entry', policy='ask'))
            r = self.finish(c, lambda e: self.reply(c, e, action))
            self.assertEqual(r['status'], 'success', c.events)
            item = inventory(c.events).items[b'file'.hex()]
            self.assertEqual(item['status'], 'skipped' if action == 'skip' else 'success')
            if action == 'keep_both':
                self.assertEqual(target.read_text(), 'old copy')
                mapped = self.dest / 'file (copy 1)'
                self.assertEqual(mapped.read_text(), 'incoming')
                self.assertEqual(os.fsdecode(bytes.fromhex(item['destination_path']['bytes_hex'])), str(mapped))
            elif action == 'skip': self.assertEqual(target.read_text(), 'old copy')
            else: self.assertEqual(target.read_text(), 'incoming')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['file', 'file (copy 1)'])

    def test_changed_revision_reprompts_and_invalid_or_stale_tokens_do_not_mutate(self):
        source, target = self.fixture()
        c = self.client(); c.send(copy_request(source, self.dest, mode='entry', policy='ask'))
        conflicts = []
        def answer(e):
            conflicts.append(e)
            if len(conflicts) == 1:
                self.reply(c, e, revision_token='wrong')
                while c.read()['type'] != 'conflict_response_rejected': pass
                self.assertEqual(target.read_text(), 'old copy')
                target.write_text('external changed destination')
                self.reply(c, e)
            else:
                self.assertEqual(e['reason'], 'destination_changed')
                self.assertNotEqual(e['conflict_id'], conflicts[0]['conflict_id'])
                self.reply(c, conflicts[0])
                while c.read()['type'] != 'conflict_response_rejected': pass
                self.reply(c, e, 'skip')
        self.assertEqual(self.finish(c, answer)['status'], 'success', c.events)
        self.assertEqual(len(conflicts), 2)
        self.assertEqual(target.read_text(), 'external changed destination')
        self.assertEqual([e['decision'] for e in c.events if e['type'] == 'conflict_resolved'], ['skip'])

    def test_job_scope_applies_only_to_same_conflict_kind(self):
        for name in ('a', 'b'):
            (self.source / name).write_text('new ' + name); (self.dest / name).write_text('old ' + name)
        (self.source / 'folder').mkdir(); (self.source / 'folder' / 'nested').write_text('inside')
        (self.dest / 'folder').mkdir(); (self.dest / 'folder' / 'sentinel').write_text('unselected')
        c = self.client(); c.send(copy_request(self.source, self.dest, policy='ask'))
        def answer(e):
            self.reply(c, e, 'skip' if e['kind'] == 'file_file' else 'replace', scope='job')
        self.assertEqual(self.finish(c, answer)['status'], 'success', c.events)
        self.assertEqual([e['kind'] for e in c.events if e['type'] == 'conflict'], ['file_file', 'directory_merge'])
        self.assertEqual((self.dest / 'a').read_text(), 'old a')
        self.assertEqual((self.dest / 'b').read_text(), 'old b')
        self.assertEqual((self.dest / 'folder' / 'sentinel').read_text(), 'unselected')
        self.assertEqual((self.dest / 'folder' / 'nested').read_text(), 'inside')

    def test_keep_both_directory_and_symlink_preserve_existing_descendants(self):
        folder = self.source / 'folder'; folder.mkdir(); (folder / 'child').write_text('nested source')
        (self.source / 'link').symlink_to('literal:target')
        old = self.dest / 'folder'; old.mkdir(); (old / 'sentinel').write_text('keep me')
        (self.dest / 'link').write_text('old link target entry')
        (self.dest / 'folder (copy 1)').mkdir()
        c = self.client(); c.send(copy_request(self.source, self.dest, policy='ask'))
        self.assertEqual(self.finish(c, lambda e: self.reply(c, e, 'keep_both'))['status'], 'success', c.events)
        self.assertEqual((self.dest / 'folder (copy 2)' / 'child').read_text(), 'nested source')
        self.assertEqual((old / 'sentinel').read_text(), 'keep me')
        self.assertEqual((self.dest / 'link (copy 1)').readlink(), (self.source / 'link').readlink())
        self.assertEqual((self.dest / 'link').read_text(), 'old link target entry')
        item = inventory(c.events).items[b'folder/child'.hex()]
        self.assertTrue(os.fsdecode(bytes.fromhex(item['destination_path']['bytes_hex'])).endswith('/folder (copy 2)/child'))

    def test_nonempty_directory_replacement_is_not_offered_and_explicit_names_are_literal(self):
        (self.source / 'file').write_text('incoming')
        old = self.dest / 'file'; old.mkdir(); (old / 'sentinel').write_text('keep')
        c = self.client(); c.send(copy_request(self.source, self.dest, policy='ask'))
        def answer(e):
            self.assertNotIn('replace', e['allowed_actions'])
            self.reply(c, e, 'replace')
            while c.read()['type'] != 'conflict_response_rejected': pass
            self.reply(c, e, 'keep_both', destination_name={'bytes_hex': b'*?\n:name'.hex()})
        self.assertEqual(self.finish(c, answer)['status'], 'success', c.events)
        self.assertEqual((self.dest / '*?\n:name').read_text(), 'incoming')
        self.assertEqual((old / 'sentinel').read_text(), 'keep')

    def test_absent_publication_race_reprompts_after_close_and_keeps_foreign_entry(self):
        source = self.source / 'file'; source.write_text('incoming')
        marker, release = self.root / 'closed', self.root / 'release'
        c = self.client(self.fault_env(self.dest, XSYNC_FAULT_CLOSE_NOTIFY=str(marker), XSYNC_FAULT_CLOSE_RELEASE=str(release)))
        c.send(copy_request(source, self.dest, mode='entry', policy='ask'))
        self.wait_marker(marker)
        target = self.dest / 'file'; target.write_text('foreign')
        release.touch()
        self.assertEqual(self.finish(c, lambda e: self.reply(c, e, 'keep_both'))['status'], 'success', c.events)
        self.assertEqual(target.read_text(), 'foreign')
        self.assertEqual((self.dest / 'file (copy 1)').read_text(), 'incoming')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['file', 'file (copy 1)'])

    def test_cancel_and_deadline_while_waiting_preserve_destinations(self):
        source, target = self.fixture()
        for timeout in (False, True):
            c = self.client(); c.send(copy_request(source, self.dest, mode='entry', policy='ask', conflict_timeout_seconds='1'))
            def answer(e):
                self.assertEqual(target.read_text(), 'old copy')
                if not timeout: c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
            r = self.finish(c, answer)
            self.assertEqual(r['status'], 'partial_failure' if timeout else 'cancellation', c.events)
            self.assertEqual(target.read_text(), 'old copy')
            self.assertEqual([p.name for p in self.dest.iterdir()], ['file'])

    def test_directory_and_symlink_creation_races_require_fresh_decisions(self):
        for kind in ('mkdir','symlink'):
            with self.subTest(kind=kind):
                source=self.source/kind
                if kind=='mkdir': source.mkdir(); (source/'child').write_text('incoming child')
                else: source.symlink_to('literal target')
                marker=self.root/('notify-'+kind)
                c=self.client(self.fault_env(self.dest,XSYNC_FAULT_AT_OP=kind,XSYNC_FAULT_AT_NAME=kind,XSYNC_FAULT_AT_NOTIFY=str(marker)))
                c.send(copy_request(source,self.dest,mode='entry',policy='ask'))
                self.wait_marker(marker)
                target=self.dest/kind
                if kind=='mkdir': target.mkdir(); (target/'sentinel').write_text('foreign child')
                else: target.write_text('foreign entry')
                def answer(e):
                    self.assertEqual(e['reason'],'destination_changed'); self.reply(c,e,'keep_both')
                self.assertEqual(self.finish(c,answer)['status'],'success',c.events)
                if kind=='mkdir':
                    self.assertEqual((target/'sentinel').read_text(),'foreign child')
                    self.assertEqual((self.dest/(kind+' (copy 1)')/'child').read_text(),'incoming child')
                    self.assertFalse((target/'child').exists())
                else:
                    self.assertEqual(target.read_text(),'foreign entry')
                    self.assertEqual((self.dest/(kind+' (copy 1)')).readlink(),source.readlink())

    def test_staged_file_can_replace_new_empty_directory_and_keeps_source_default_mode(self):
        source,target=self.fixture(); source.chmod(0o640); target.chmod(0o600)
        marker,release=self.root/'closed-directory-race',self.root/'release-directory-race'
        c=self.client(self.fault_env(self.dest,XSYNC_FAULT_CLOSE_NOTIFY=str(marker),XSYNC_FAULT_CLOSE_RELEASE=str(release)))
        c.send(copy_request(source,self.dest,mode='entry',policy='ask',preserve_permissions=False))
        while True:
            first=c.read()
            if first['type']=='conflict': break
        self.reply(c,first,'replace')
        self.wait_marker(marker)
        target.unlink(); target.mkdir(); release.touch()
        def answer(e):
            self.assertEqual(e['kind'],'type_mismatch'); self.assertEqual(e['reason'],'destination_changed')
            self.assertIn('replace',e['allowed_actions']); self.reply(c,e,'replace')
        self.assertEqual(self.finish(c,answer)['status'],'success',c.events)
        self.assertEqual(target.read_text(),'incoming')
        self.assertEqual(target.stat().st_mode&0o777,0o640)
        self.assertEqual([p.name for p in self.dest.iterdir()],['file'])

    def test_directory_scope_does_not_apply_to_other_directories(self):
        for folder in ('one', 'two'):
            (self.source/folder).mkdir(); (self.dest/folder).mkdir()
            for name in ('a','b'):
                (self.source/folder/name).write_text('incoming'); (self.dest/folder/name).write_text('old')
        c=self.client(); c.send(copy_request(self.source,self.dest,policy='ask'))
        def answer(e):
            self.reply(c,e,'replace' if e['kind']=='directory_merge' else 'skip',scope='directory')
        self.assertEqual(self.finish(c,answer)['status'],'success',c.events)
        conflicts=[e for e in c.events if e['type']=='conflict']
        self.assertEqual(sum(e['kind']=='directory_merge' for e in conflicts),1)
        self.assertEqual(sum(e['kind']=='file_file' for e in conflicts),2)
        self.assertTrue(all((self.dest/folder/name).read_text()=='old' for folder in ('one','two') for name in ('a','b')))

    def test_planned_case_aliases_prompt_before_writes_and_keep_both_preserves_both_selections(self):
        probe=self.dest/'CASE-probe'; probe.write_text('probe')
        equivalent=(self.dest/'case-probe').exists(); probe.unlink()
        if not equivalent: self.skipTest('destination filesystem is case sensitive')
        first=self.source/'first'; first.write_text('first incoming')
        second=self.source/'second'; second.write_text('second incoming')
        request=copy_request(self.source,self.dest,policy='ask')
        request['sources']=[{'endpoint':api.endpoint(first),'mode':'entry','destination_name':{'bytes_hex':b'ALIAS'.hex()}},
                            {'endpoint':api.endpoint(second),'mode':'entry','destination_name':{'bytes_hex':b'alias'.hex()}}]
        c=self.client(); c.send(request)
        def answer(e):
            self.assertEqual(e['kind'],'name_collision'); self.assertNotIn('replace',e['allowed_actions'])
            self.reply(c,e,'keep_both')
        self.assertEqual(self.finish(c,answer)['status'],'success',c.events)
        self.assertEqual((self.dest/'ALIAS (copy 1)').read_text(),'first incoming')
        self.assertEqual((self.dest/'alias').read_text(),'second incoming')
        self.assertEqual(sum(e['type']=='conflict' for e in c.events),1)

    def test_concurrent_keep_both_jobs_are_exclusive_and_do_not_share_names(self):
        source,target=self.fixture()
        first=self.client(); first.send(copy_request(source,self.dest,mode='entry',policy='ask'))
        while True:
            conflict=first.read()
            if conflict['type']=='conflict': break
        second=self.client(); second.send(copy_request(source,self.dest,mode='entry',policy='ask'))
        result=second.finish()
        self.assertEqual(result['status'],'failure',second.events)
        self.assertTrue(any(e['type']=='error' and e['operation']=='destination_lock' for e in second.events))
        self.reply(first,conflict,'keep_both')
        self.assertEqual(first.finish()['status'],'success')
        third=self.client(); third.send(copy_request(source,self.dest,mode='entry',policy='ask'))
        self.assertEqual(self.finish(third,lambda e:self.reply(third,e,'keep_both'))['status'],'success')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()),['file','file (copy 1)','file (copy 2)'])
        self.assertEqual(target.read_text(),'old copy')

    def test_unicode_aliases_and_long_utf8_keep_both_names(self):
        first=self.source/'first'; first.write_text('first')
        second=self.source/'second'; second.write_text('second')
        probe=self.dest/'é'; probe.write_text('probe')
        normalizes=(self.dest/'e\u0301').exists(); probe.unlink()
        if normalizes:
            request=copy_request(self.source,self.dest,policy='ask')
            request['sources']=[{'endpoint':api.endpoint(first),'mode':'entry','destination_name':{'bytes_hex':'é'.encode().hex()}},
                                {'endpoint':api.endpoint(second),'mode':'entry','destination_name':{'bytes_hex':'e\u0301'.encode().hex()}}]
            c=self.client(); c.send(request)
            self.assertEqual(self.finish(c,lambda e:self.reply(c,e,'keep_both'))['status'],'success',c.events)
            self.assertEqual([e['kind'] for e in c.events if e['type']=='conflict'],['name_collision'])
            self.assertEqual((self.dest/'é (copy 1)').read_text(),'second')
            self.assertEqual((self.dest/'é').read_text(),'first')
        long='é'*125
        source=self.source/long; source.write_text('long incoming')
        target=self.dest/long; target.write_text('old')
        c=self.client(); c.send(copy_request(source,self.dest,mode='entry',policy='ask'))
        self.assertEqual(self.finish(c,lambda e:self.reply(c,e,'keep_both'))['status'],'success',c.events)
        mapped=bytes.fromhex(inventory(c.events).items[long.encode().hex()]['destination_path']['bytes_hex'])
        self.assertLessEqual(len(mapped.rpartition(b'/')[2]),255)
        self.assertEqual(os.fsdecode(mapped).encode('utf8'),mapped)
        self.assertEqual(target.read_text(),'old')
        with open(mapped) as copied: self.assertEqual(copied.read(),'long incoming')

    def test_existing_case_alias_reports_the_actual_name(self):
        original=self.dest/'lower'; original.write_text('old')
        if not (self.dest/'LOWER').exists(): self.skipTest('destination filesystem is case sensitive')
        source=self.source/'source'; source.write_text('incoming')
        request=copy_request(source,self.dest,mode='entry',policy='ask')
        request['sources'][0]['destination_name']={'bytes_hex':b'LOWER'.hex()}
        c=self.client(); c.send(request)
        def answer(e):
            self.assertEqual(e['kind'],'name_collision')
            self.assertEqual(e['existing_name']['bytes_hex'],b'lower'.hex())
            self.reply(c,e,'keep_both')
        self.assertEqual(self.finish(c,answer)['status'],'success',c.events)
        self.assertEqual(original.read_text(),'old')
        self.assertEqual((self.dest/'LOWER (copy 1)').read_text(),'incoming')

    def test_reference_callback_and_cli_conflict_ui_keep_stdout_json(self):
        sys.path.insert(0,str(api.ROOT/'tools'))
        from app_client import AppClient
        source,target=self.fixture()
        c=AppClient(api.BINARY); self.addCleanup(c.close)
        seen=[]
        def choose(e): seen.append(e); return {'decision':'keep_both','destination_name':{'bytes_hex':b':literal?'.hex()}}
        events=list(c.run(copy_request(source,self.dest,mode='entry',policy='ask'),conflict_handler=choose))
        self.assertEqual(events[-1]['status'],'success',events)
        self.assertEqual(len(seen),1)
        self.assertEqual((self.dest/':literal?').read_text(),'incoming')
        self.assertEqual(target.read_text(),'old copy')
        cli=subprocess.run([sys.executable,str(api.ROOT/'tools/app_client.py'),'--binary',str(api.BINARY),'--interactive-conflicts',
                            'copy','--on-conflict','ask',str(source),str(self.dest)],input='invalid action\nskip\n',text=True,capture_output=True,timeout=8)
        self.assertEqual(cli.returncode,0,cli.stderr)
        self.assertEqual(json.loads(cli.stdout.splitlines()[-1])['status'],'success')
        self.assertTrue(all(isinstance(json.loads(line),dict) for line in cli.stdout.splitlines()))
        self.assertIn('Conflict at',cli.stderr)
        self.assertEqual(target.read_text(),'old copy')

    def test_reference_client_drains_progress_while_conflict_callback_waits(self):
        sys.path.insert(0,str(api.ROOT/'tools'))
        from app_client import AppClient
        source,target=self.fixture()
        entered,released=threading.Event(),threading.Event()
        def choose(e):
            entered.set()
            if not released.wait(3): raise AssertionError('client stopped reading while waiting for input')
            return 'skip'
        c=AppClient(api.BINARY); self.addCleanup(c.close)
        events=[]; waiting=False
        for e in c.run(copy_request(source,self.dest,mode='entry',policy='ask'),conflict_handler=choose):
            events.append(e)
            if e['type']=='progress' and e['phase']=='waiting_conflict' and entered.is_set():
                waiting=True; released.set()
        self.assertTrue(waiting,events)
        self.assertEqual(events[-1]['status'],'success',events)
        self.assertEqual(target.read_text(),'old copy')

    def test_reference_client_cancels_and_observes_deadline_during_pending_callback(self):
        sys.path.insert(0,str(api.ROOT/'tools'))
        from app_client import AppClient
        source,target=self.fixture()
        for cancel in (True,False):
            with self.subTest(cancel=cancel):
                released=threading.Event()
                self.addCleanup(released.set)
                def choose(e): released.wait(3); return 'replace'
                c=AppClient(api.BINARY); self.addCleanup(c.close)
                request=copy_request(source,self.dest,mode='entry',policy='ask',conflict_timeout_seconds='1')
                events=list(c.run(request,cancel_after=.3 if cancel else None,conflict_handler=choose))
                released.set()
                self.assertEqual(events[-1]['status'],'cancellation' if cancel else 'partial_failure',events)
                self.assertEqual(target.read_text(),'old copy')

    def test_more_than_32_decisions_have_bounded_control_ids(self):
        for i in range(40):
            (self.source / str(i)).write_text('incoming'); (self.dest / str(i)).write_text('old')
        c = self.client(); c.send(copy_request(self.source, self.dest, policy='ask'))
        self.assertEqual(self.finish(c, lambda e: self.reply(c, e, 'skip'))['status'], 'success', c.events)
        self.assertEqual(sum(e['type'] == 'conflict' for e in c.events), 40)


if __name__ == '__main__': unittest.main()
