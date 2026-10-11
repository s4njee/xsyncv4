#!/usr/bin/env python3
"""Private local recovery: real interruption, verified reuse and guarded cleanup."""
import copy
import errno
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from app_test import BINARY, ROOT, Client, copy_request, endpoint
from app_refresh_test import assert_scope

MIB = 1024 * 1024


class PrivatePartialsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xs-partials-fault-')
        cls.addClassCleanup(cls.library_tmp.cleanup)
        cls.fault = pathlib.Path(cls.library_tmp.name) / 'fault_io.so'
        command = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                   '-fPIC', str(ROOT / 'tests/fault_io.cpp'), '-o', str(cls.fault)]
        if sys.platform != 'darwin': command += ['-ldl']
        subprocess.run(command, check=True, capture_output=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs private recovery ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        self.dest = self.root / 'destination'; self.dest.mkdir()
        self.payload = os.urandom(4 * MIB)
        (self.source / 'large').write_bytes(self.payload)
        (self.dest / 'large').write_bytes(b'old good copy')
        self.request = copy_request(self.source, self.dest, retain_partials=True,
                                    bandwidth_bytes_per_second=str(MIB), jobs='1')

    def client(self, env=None):
        c = Client(env); self.addCleanup(c.close); return c

    def job(self, request):
        c = self.client(); c.send(request); result = c.finish(); return c, result

    def begin(self):
        c = self.client(); c.send(self.request)
        recovery_id = None
        for _ in range(100):
            event = c.read()
            if event['type'] == 'recovery_created': recovery_id = event['recovery_id']
            if event['type'] == 'progress' and int(event.get('source_bytes_read') or '0') >= 262144:
                self.assertIsNotNone(recovery_id)
                self.recovery_id = recovery_id
                self.store = self.dest / '.xsync-app-partials' / recovery_id
                return c
            self.assertNotEqual(event['type'], 'result', c.events)
        self.fail('no staged prefix observed')

    def interrupted(self):
        c = self.begin(); c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
        self.assertEqual(c.finish()['status'], 'cancellation', c.events)
        assert_scope(self,c.events,self.dest)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        self.part = next(self.store.glob('*.part'))
        self.assertGreater(self.part.stat().st_size, 0)
        self.assertLess(self.part.stat().st_size, len(self.payload))
        return c

    def resume(self, **options):
        request = copy.deepcopy(self.request)
        request.update(id='resume', op='resume', recovery_id=self.recovery_id)
        request['options']['bandwidth_bytes_per_second'] = '0'
        request['options'].update(options)
        c,result = self.job(request)
        assert_scope(self,c.events,self.dest)
        return c,result

    def state(self):
        c, result = self.job({'id': 'state', 'op': 'recovery_state',
                              'endpoint': endpoint(self.dest), 'recovery_id': self.recovery_id})
        self.assertEqual(result['status'], 'success', c.events)
        return next(e for e in c.events if e['type'] == 'recovery_state')

    def cleanup_request(self, revision=None):
        return {'id': 'cleanup', 'op': 'cleanup_partials', 'endpoint': endpoint(self.dest),
                'recovery_id': self.recovery_id,
                'expected_job_revision': revision or self.state()['job_revision']}

    def verify_request(self, state=None):
        state = state or self.state()
        request = copy.deepcopy(self.request)
        request.update(id='verify', op='verify_recovery', recovery_id=self.recovery_id,
                       expected_job_revision=state['job_revision'], expected_inventory_token=state['inventory_token'])
        return request

    def publication_gap(self, before=False, absent=False):
        (self.dest/'large').write_bytes(b'old good copy'); (self.dest/'large').chmod(0o644)
        if absent: (self.dest/'large').unlink()
        marker = self.root/('publication-'+os.urandom(6).hex())
        variable = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
        env = dict(os.environ, **{variable:str(self.fault)}, XSYNC_FAULT_PATH=str(self.dest.resolve()),
                   XSYNC_FAULT_PUBLICATION_NOTIFY=str(marker), XSYNC_FAULT_PUBLICATION_HOLD='1')
        if before: env['XSYNC_FAULT_PUBLICATION_BEFORE'] = '1'
        if absent:
            env.update(XSYNC_FAULT_PUBLICATION_STAT='large',XSYNC_FAULT_PUBLICATION_SIZE=str(len(self.payload)))
        request = copy.deepcopy(self.request); request['options']['bandwidth_bytes_per_second'] = '0'
        c = self.client(env); c.send(request)
        deadline = time.monotonic()+10
        while not marker.exists():
            if c.proc.poll() is not None:
                c.finish(); self.fail('engine ended before publication fixture: '+repr(c.events))
            self.assertLess(time.monotonic(),deadline,'publication fixture never reached rename')
            time.sleep(.01)
        worker = int(marker.read_text()); self.assertNotEqual(worker,c.proc.pid)
        os.kill(worker,signal.SIGKILL)
        self.assertIn(c.finish()['status'],('failure','partial_failure','cancellation'),c.events)
        self.recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
        self.store = self.dest/'.xsync-app-partials'/self.recovery_id
        rows = [(p,json.loads(p.read_text())) for p in self.store.glob('*.json') if not p.name.startswith('.')]
        rows = [(p,row) for p,row in rows if row['entry_type'] == 'regular']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][1]['state'],'publishing')
        self.assertEqual(bool(list(self.store.glob('*.part'))),before)
        self.assertEqual((self.dest/'large').read_bytes(),b'old good copy' if before else self.payload)
        return rows[0]

    def test_publication_gap_verifies_without_writes_and_resume_freezes_full_revision(self):
        record,row = self.publication_gap(); state = self.state()
        before = {p.name:p.read_bytes() for p in self.store.iterdir()}
        revisions = {p.name:p.stat().st_mtime_ns for p in self.store.iterdir()}
        c,result = self.job(self.verify_request(state))
        self.assertEqual(result['status'],'success',c.events)
        proof = next(e for e in c.events if e['type'] == 'recovery_verified')
        self.assertGreaterEqual(int(proof['published_records']),1); self.assertEqual(proof['pending_records'],'0')
        self.assertFalse(proof['operation_completion_proven'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.store.iterdir()})
        self.assertEqual(revisions,{p.name:p.stat().st_mtime_ns for p in self.store.iterdir()})
        c,result = self.resume(); self.assertEqual(result['status'],'success',c.events)
        saved = json.loads(record.read_text()); self.assertIn(saved['state'],('published','entry_published'))
        self.assertEqual((self.dest/'large').read_bytes(),self.payload)
        # Once normalized, even a same-content metadata edit is checked against
        # the full observed ctime rather than the exceptional rename allowance.
        target = self.dest/'large'; mode = target.stat().st_mode & 0o777
        target.chmod(mode ^ 0o100); target.chmod(mode)
        c,result = self.resume(); self.assertIn(result['status'],('failure','partial_failure'),c.events)
        self.assertIn('recovery_destination_changed',[e.get('operation') for e in c.events if e['type'] == 'error'])

    def test_publication_intent_before_rename_retains_guarded_prefix_and_original_destination(self):
        record,row = self.publication_gap(before=True)
        original = record.read_bytes(); c,result = self.job(self.verify_request())
        self.assertEqual(result['status'],'success',c.events)
        proof = next(e for e in c.events if e['type'] == 'recovery_verified')
        self.assertEqual(proof['pending_records'],'1'); self.assertEqual(proof['bytes_retained'],str(len(self.payload)))
        self.assertFalse(proof['operation_completion_proven']); self.assertEqual(record.read_bytes(),original)
        self.assertEqual((self.dest/'large').read_bytes(),b'old good copy')
        c,result = self.resume(); self.assertEqual(result['status'],'success',c.events)
        self.assertEqual(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']),len(self.payload))
        self.assertEqual((self.dest/'large').read_bytes(),self.payload)

    def test_publication_gap_resume_revalidates_changed_source_bytes(self):
        self.publication_gap()
        replacement = b'changed source'*(len(self.payload)//14)+b'z'*(len(self.payload)%14)
        (self.source/'large').write_bytes(replacement)
        c,result = self.job(self.verify_request()); self.assertEqual(result['status'],'success',c.events)
        c,result = self.resume(); self.assertEqual(result['status'],'success',c.events)
        self.assertEqual((self.dest/'large').read_bytes(),replacement)
        self.assertEqual(next(e for e in c.events if e['type'] == 'summary')['reused_bytes'],'0')

    def test_absent_name_publication_gap_recovers_the_exclusively_published_inode(self):
        record,row = self.publication_gap(absent=True)
        self.assertEqual(row['expected_destination'],{'exists':False})
        c,result = self.job(self.verify_request()); self.assertEqual(result['status'],'success',c.events)
        self.assertFalse(next(e for e in c.events if e['type'] == 'recovery_verified')['operation_completion_proven'])
        c,result = self.resume(); self.assertEqual(result['status'],'success',c.events)
        self.assertEqual((self.dest/'large').read_bytes(),self.payload)

    def test_failed_publication_intent_write_does_not_publish_destination(self):
        variable = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
        env = dict(os.environ, **{variable:str(self.fault)}, XSYNC_FAULT_PATH=str(self.dest.resolve()),
                   XSYNC_FAULT_RECOVERY_PUBLICATION_ERROR=str(errno.ENOSPC))
        request = copy.deepcopy(self.request); request['options']['bandwidth_bytes_per_second'] = '0'
        c = self.client(env); c.send(request); result = c.finish()
        self.assertIn(result['status'],('failure','partial_failure'),c.events)
        self.assertEqual((self.dest/'large').read_bytes(),b'old good copy')
        self.assertFalse(any(e['type'] == 'partial_published' for e in c.events))
        self.assertTrue(any(e['type'] == 'error' and e['category'] == 'disk_full' and e['operation'] == 'recovery_write' for e in c.events))

    def test_empty_file_publication_gap_has_a_verified_content_digest(self):
        self.payload = b''; (self.source/'large').write_bytes(self.payload)
        record,row = self.publication_gap()
        self.assertEqual(row['publication_identity']['size'],'0')
        self.assertRegex(row['publication_digest'],r'^[0-9a-f]{32}$')
        c,result = self.job(self.verify_request()); self.assertEqual(result['status'],'success',c.events)
        c,result = self.resume(); self.assertEqual(result['status'],'success',c.events)
        self.assertEqual((self.dest/'large').read_bytes(),b'')

    def test_publication_gap_unknown_private_files_block_direct_resume_before_normalization(self):
        for name in ('e'*32+'.part','.pending-'+ 'e'*32,'unknown'):
            with self.subTest(name=name):
                record,row = self.publication_gap(); before = record.read_bytes()
                extra = self.store/name; extra.write_bytes(b'unrecorded private work'); extra.chmod(0o600)
                (self.source/'large').write_bytes(b'new source must not be published')
                c,result = self.resume(); self.assertIn(result['status'],('failure','partial_failure'),c.events)
                self.assertTrue(any(e.get('operation') in ('recovery_unrecorded_data','recovery_verification_scope') for e in c.events))
                self.assertEqual(record.read_bytes(),before); self.assertEqual((self.dest/'large').read_bytes(),self.payload)
                self.assertEqual(extra.read_bytes(),b'unrecorded private work')
                (self.source/'large').write_bytes(self.payload)

    def test_publication_gap_rejects_changed_content_attributes_identity_and_links(self):
        for mutation in ('content','replacement','mode','link'):
            with self.subTest(mutation=mutation):
                record,row = self.publication_gap(); target = self.dest/'large'; before = target.stat()
                if mutation == 'content':
                    target.write_bytes(b'x'*len(self.payload)); os.utime(target,ns=(before.st_atime_ns,before.st_mtime_ns))
                elif mutation == 'replacement':
                    other = self.dest/'replacement'; other.write_bytes(self.payload)
                    other.chmod(before.st_mode & 0o777); os.utime(other,ns=(before.st_atime_ns,before.st_mtime_ns)); other.replace(target)
                elif mutation == 'mode': target.chmod((before.st_mode & 0o777) ^ 0o100)
                else: os.link(target,self.dest/'foreign-link')
                contents = target.read_bytes(); metadata = record.read_bytes()
                c,result = self.job(self.verify_request())
                self.assertIn(result['status'],('failure','partial_failure'),c.events)
                self.assertFalse(any(e['type'] == 'recovery_verified' for e in c.events))
                self.assertEqual(record.read_bytes(),metadata)
                c,result = self.resume(); self.assertIn(result['status'],('failure','partial_failure'),c.events)
                self.assertEqual(target.read_bytes(),contents)
                if mutation == 'link': (self.dest/'foreign-link').unlink()

    def test_copy_accepts_reserved_identity_and_refuses_an_existing_store_without_writes(self):
        request = copy.deepcopy(self.request); request.update(recovery_id='d'*32)
        request['options']['bandwidth_bytes_per_second'] = '0'
        c, result = self.job(request)
        self.assertEqual(c.capabilities['copy_recovery_identity'], '1')
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual({e['recovery_id'] for e in c.events if e['type'] in ('recovery_preparing', 'recovery_created')}, {'d'*32})
        store = self.dest / '.xsync-app-partials' / ('d'*32)
        before = {p.name:p.read_bytes() for p in store.iterdir()}
        revisions = {p.name:p.stat().st_mtime_ns for p in store.iterdir()}
        original = (self.dest/'large').read_bytes(); (self.source/'large').write_bytes(b'changed source')
        c, result = self.job(request)
        self.assertIn(result['status'], ('failure', 'partial_failure'), c.events)
        self.assertIn('recovery_job_exists', [e.get('operation') for e in c.events if e['type'] == 'error'])
        self.assertEqual((self.dest/'large').read_bytes(), original)
        self.assertEqual({p.name:p.read_bytes() for p in store.iterdir()}, before)
        self.assertEqual({p.name:p.stat().st_mtime_ns for p in store.iterdir()}, revisions)

    def test_invalid_or_nonprivate_copy_recovery_identity_is_rejected_before_mutation(self):
        for identity in ('', 'A'*32, 'a'*31, 'a'*33, '../foreign', False, 1, None):
            with self.subTest(identity=identity):
                request = copy.deepcopy(self.request); request['recovery_id'] = identity
                c, result = self.job(request)
                self.assertEqual(result['status'], 'failure', c.events)
                self.assertFalse((self.dest/'.xsync-app-partials').exists())
                self.assertEqual((self.dest/'large').read_bytes(), b'old good copy')
        request = copy.deepcopy(self.request); request.update(recovery_id='d'*32)
        request['options']['retain_partials'] = False
        c, result = self.job(request); self.assertEqual(result['status'], 'failure', c.events)
        self.assertFalse((self.dest/'.xsync-app-partials').exists())
        self.assertEqual((self.dest/'large').read_bytes(), b'old good copy')

    def test_read_only_recovery_verification_checks_the_bound_inventory(self):
        self.interrupted(); state = self.state()
        before = {p.name:p.read_bytes() for p in self.store.iterdir()}
        revisions = {p.name:p.stat().st_mtime_ns for p in self.store.iterdir()}
        c, result = self.job(self.verify_request(state))
        self.assertEqual(result['status'], 'success', c.events)
        proof = next(e for e in c.events if e['type'] == 'recovery_verified')
        self.assertTrue(proof['destination_guard_verified']); self.assertTrue(proof['source_verification_required'])
        self.assertFalse(proof['operation_completion_proven'])
        self.assertEqual(proof['inventory_token'], state['inventory_token'])
        self.assertGreater(int(proof['bytes_retained']), 0); self.assertGreater(int(proof['pending_records']), 0)
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.store.iterdir()})
        self.assertEqual(revisions, {p.name:p.stat().st_mtime_ns for p in self.store.iterdir()})
        self.assertEqual((self.dest/'large').read_bytes(), b'old good copy')

    def test_verification_of_completed_receipts_cannot_claim_a_lost_result(self):
        self.completed(); c, result = self.job(self.verify_request())
        self.assertEqual(result['status'], 'success', c.events)
        proof = next(e for e in c.events if e['type'] == 'recovery_verified')
        self.assertEqual(proof['state'], 'completed'); self.assertEqual(proof['pending_records'], '0')
        self.assertGreater(int(proof['published_records']), 0); self.assertFalse(proof['operation_completion_proven'])

    def test_verification_rejects_changed_destinations_and_semantic_bindings_without_writes(self):
        self.interrupted(); original = self.part.read_bytes()
        request = self.verify_request(); request['options']['on_conflict'] = 'skip'
        c, result = self.job(request)
        self.assertNotEqual(result['status'], 'success')
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_binding_changed' for e in c.events), c.events)
        request = self.verify_request(); (self.dest/'large').write_bytes(b'independently edited target')
        c, result = self.job(request)
        self.assertNotEqual(result['status'], 'success')
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_destination_changed' for e in c.events), c.events)
        self.assertFalse(any(e['type'] == 'recovery_verified' for e in c.events))
        self.assertEqual(self.part.read_bytes(), original)
        self.assertEqual((self.dest/'large').read_bytes(), b'independently edited target')

    def test_inventory_token_rejects_in_place_metadata_changes_after_inspection(self):
        self.interrupted(); state = self.state(); before_directory = self.store.stat()
        header = self.store/'.job.json'; header.write_bytes(header.read_bytes()+b' ')
        self.assertEqual(self.store.stat().st_mtime_ns, before_directory.st_mtime_ns)
        c, result = self.job(self.verify_request(state))
        self.assertNotEqual(result['status'], 'success')
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_inventory_changed' for e in c.events), c.events)
        self.assertFalse(any(e['type'] == 'recovery_verified' for e in c.events))

    def test_verification_rejects_orphan_data_and_unknown_private_files(self):
        self.interrupted(); original = self.part.read_bytes()
        for name in ('f'*32+'.part', '.pending-unfinished', 'unexpected'):
            with self.subTest(name=name):
                extra = self.store/name; extra.write_bytes(b'foreign bytes'); extra.chmod(0o600)
                c, result = self.job(self.verify_request())
                self.assertNotEqual(result['status'], 'success', c.events)
                self.assertFalse(any(e['type'] == 'recovery_verified' for e in c.events))
                self.assertEqual(extra.read_bytes(), b'foreign bytes'); self.assertEqual(self.part.read_bytes(), original)
                extra.unlink()

    def test_verification_accepts_guarded_private_data_after_output_permissions_were_applied(self):
        self.interrupted(); self.part.chmod(0o640)
        c, result = self.job(self.verify_request())
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(self.part.stat().st_mode & 0o777, 0o640)

    def test_verification_accepts_literal_mapped_entry_selections(self):
        name = 'mapped\nα[*]'
        self.request['sources'] = [{'endpoint':endpoint(self.source/'large'), 'mode':'entry',
                                    'destination_name':{'bytes_hex':os.fsencode(name).hex()}}]
        self.completed(); c, result = self.job(self.verify_request())
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest/name).read_bytes(), self.payload)
        self.assertEqual((self.dest/'large').read_bytes(), b'old good copy')

    def assert_resume_failure(self, operation):
        before = self.part.read_bytes() if hasattr(self, 'part') else None
        c, result = self.resume()
        self.assertNotEqual(result['status'], 'success', c.events)
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == operation for e in c.events), c.events)
        if before is not None: self.assertEqual(self.part.read_bytes(), before)
        return c

    def completed(self):
        self.request['options']['bandwidth_bytes_per_second'] = '0'
        c, result = self.job(self.request)
        self.assertEqual(result['status'], 'success', c.events)
        self.recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
        self.store = self.dest / '.xsync-app-partials' / self.recovery_id
        return c

    def test_completed_symlink_edit_blocks_all_resume_writes(self):
        (self.source / 'link').symlink_to('large')
        self.completed()
        (self.dest / 'link').unlink(); (self.dest / 'link').symlink_to('independent target')
        (self.source / 'large').write_bytes(b'new source')
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual(os.readlink(self.dest / 'link'), 'independent target')
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)

    def test_completed_directory_permission_edit_blocks_all_resume_writes(self):
        (self.source / 'nested').mkdir(); (self.source / 'nested' / 'empty').mkdir()
        self.completed(); (self.dest / 'nested' / 'empty').chmod(0o711)
        (self.source / 'large').write_bytes(b'new source')
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'nested' / 'empty').stat().st_mode & 0o777, 0o711)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)

    def test_completed_directory_timestamp_edit_is_not_accepted_as_child_activity(self):
        (self.source / 'empty').mkdir(); self.completed()
        os.utime(self.dest / 'empty', ns=(123456789, 987654321))
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'empty').stat().st_mtime_ns, 987654321)

    def test_source_type_changes_replace_only_recorded_targets_across_attempts(self):
        self.interrupted()
        source = self.source / 'large'; target = self.dest / 'large'
        source.unlink(); source.symlink_to('literal target')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(os.readlink(target), 'literal target'); self.assertFalse(list(self.store.glob('*.part')))
        source.unlink(); source.mkdir()
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertTrue(target.is_dir())
        source.rmdir(); source.write_bytes(b'new regular data')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(target.read_bytes(), b'new regular data')
        source.unlink(); source.symlink_to('second target')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(os.readlink(target), 'second target')
        source.unlink(); source.mkdir()
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        source.rmdir(); source.symlink_to('directory to link')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(os.readlink(target), 'directory to link')
        source.unlink(); source.write_bytes(b'link to file')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(target.read_bytes(), b'link to file')
        source.unlink(); source.mkdir()
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertTrue(target.is_dir())

    def test_nonempty_directory_type_change_preserves_children(self):
        (self.source / 'large').unlink(); (self.source / 'large').mkdir()
        (self.source / 'large' / 'child').write_bytes(b'preserved child')
        (self.dest / 'large').unlink(); self.completed()
        (self.source / 'large' / 'child').unlink(); (self.source / 'large').rmdir()
        (self.source / 'large').write_bytes(b'replacement')
        c, result = self.resume(); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large' / 'child').read_bytes(), b'preserved child')

    def test_unchanged_links_and_reverified_files_receive_destination_guards(self):
        (self.source / 'link').symlink_to('large')
        initial = copy.deepcopy(self.request); initial['options'].update(retain_partials=False, bandwidth_bytes_per_second='0')
        c, result = self.job(initial); self.assertEqual(result['status'], 'success', c.events)
        self.completed()
        rows = [json.loads(p.read_text()) for p in self.store.glob('*.json') if p.name != '.job.json']
        self.assertEqual({r.get('entry_type') for r in rows}, {'regular', 'symlink', 'directory'})
        self.assertTrue(all(r['state'] in ('entry_published', 'published') for r in rows), rows)
        self.assertTrue(any(r['entry_type'] == 'symlink' and r['state'] == 'entry_published' for r in rows), rows)
        (self.dest / 'large').write_bytes(b'independent edit')
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'large').read_bytes(), b'independent edit')

    def test_pause_nested_directories_freezes_receipts_and_reuses_prefix(self):
        nested = self.source / 'nested'; nested.mkdir(); (nested / 'deep').mkdir()
        (self.source / 'large').rename(nested / 'deep' / 'large')
        c = self.begin(); c.send({'id': 'pause', 'op': 'pause', 'job_id': 'copy'})
        self.assertEqual(c.finish()['status'], 'paused', c.events)
        rows = [json.loads(p.read_text()) for p in self.store.glob('*.json') if p.name != '.job.json']
        self.assertTrue(all(r['state'] in ('entry_published', 'entry_checkpoint') for r in rows if r.get('entry_type') == 'directory'), rows)
        retained = next(self.store.glob('*.part')).stat().st_size
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'nested' / 'deep' / 'large').read_bytes(), self.payload)
        self.assertEqual(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), retained)

    def test_hard_killed_nested_directory_job_revalidates_active_receipts(self):
        nested = self.source / 'nested'; nested.mkdir()
        (self.source / 'large').rename(nested / 'large')
        c = self.begin()
        children = subprocess.check_output(['pgrep', '-P', str(c.proc.pid)], text=True).split()
        self.assertEqual(len(children), 1, children); os.kill(int(children[0]), signal.SIGKILL)
        self.assertNotEqual(c.finish()['status'], 'success', c.events)
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'nested' / 'large').read_bytes(), self.payload)

    def test_active_directory_permission_edit_cannot_be_adopted_by_pause(self):
        nested = self.source / 'nested'; nested.mkdir()
        (self.source / 'large').rename(nested / 'large')
        c = self.begin(); (self.dest / 'nested').chmod(0o711)
        c.send({'id': 'pause', 'op': 'pause', 'job_id': 'copy'})
        self.assertEqual(c.finish()['status'], 'failure', c.events)
        self.assertFalse(any(e['type'] == 'paused' for e in c.events))
        self.assertEqual((self.dest / 'nested').stat().st_mode & 0o777, 0o711)
        self.assert_resume_failure('recovery_destination_changed')

    def test_legacy_regular_file_receipts_remain_resumable(self):
        self.completed()
        for path in self.store.glob('*.json'):
            row = json.loads(path.read_text())
            if row.get('state') == 'published':
                row.pop('entry_type', None); path.write_text(json.dumps(row))
        (self.source / 'large').write_bytes(self.payload + b'new tail')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload + b'new tail')
        self.assertEqual(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), len(self.payload))

    def test_source_named_like_private_vault_cannot_modify_the_current_store(self):
        vault = self.source / '.xsync-app-partials'; vault.mkdir(mode=0o700)
        (vault / '.owner').write_bytes(b'foreign owner')
        (vault / 'foreign child').write_bytes(b'foreign data')
        self.request['options']['bandwidth_bytes_per_second'] = '0'
        c, result = self.job(self.request); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_reserved_destination' for e in c.events), c.events)
        private = self.dest / '.xsync-app-partials'
        self.assertEqual((private / '.owner').read_bytes(), b'xsync app private partials 1\n')
        self.assertFalse((private / 'foreign child').exists())
        self.assertEqual((vault / '.owner').read_bytes(), b'foreign owner')

    def test_explicit_regular_selection_cannot_replace_the_current_vault(self):
        self.request['sources'][0].update(endpoint=endpoint(self.source / 'large'), mode='entry',
                                          destination_name={'bytes_hex': b'.xsync-app-partials'.hex()})
        self.request['options']['bandwidth_bytes_per_second'] = '0'
        c, result = self.job(self.request); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_reserved_destination' for e in c.events), c.events)
        self.assertEqual((self.dest / '.xsync-app-partials' / '.owner').read_bytes(), b'xsync app private partials 1\n')
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def answer_choice(self, c, event, decision='replace', **fields):
        c.send({'id': 'decision-' + event['conflict_id'], 'op': 'conflict_response', 'job_id': 'copy',
                'conflict_id': event['conflict_id'], 'revision_token': event['revision_token'],
                'decision': decision, **fields})

    def interrupt_choice(self, decision, pause=False, **fields):
        self.request['options']['on_conflict'] = 'ask'
        c = self.client(); c.send(self.request)
        for _ in range(1000):
            event = c.read()
            if event['type'] == 'recovery_created':
                self.recovery_id = event['recovery_id']; self.store = self.dest / '.xsync-app-partials' / self.recovery_id
            if event['type'] == 'conflict': self.answer_choice(c, event, decision, **fields)
            if event['type'] == 'progress' and int(event.get('source_bytes_read') or '0') >= 262144:
                c.send({'id': 'stop', 'op': 'pause' if pause else 'cancel', 'job_id': 'copy'})
                self.assertEqual(c.finish()['status'], 'paused' if pause else 'cancellation', c.events)
                self.part = next(self.store.glob('*.part')); return c
            self.assertNotEqual(event['type'], 'result', c.events)
        self.fail('no recoverable interactive progress')

    def test_interactive_keep_both_resume_restores_actual_name_and_reuses_prefix(self):
        c = self.interrupt_choice('keep_both'); size = self.part.stat().st_size
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
        replay = next(e for e in c.events if e['type'] == 'conflict_replayed')
        self.assertEqual(replay['recovery_id'], self.recovery_id); self.assertEqual(replay['decision'], 'keep_both')
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        self.assertEqual((self.dest / 'large (copy 1)').read_bytes(), self.payload)
        self.assertFalse((self.dest / 'large (copy 2)').exists())
        self.assertEqual(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), size)

    def test_interactive_replace_pause_and_resume_does_not_repeat_approval(self):
        self.interrupt_choice('replace', pause=True)
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)

    def test_interactive_skip_survives_resume_and_is_guarded_before_other_writes(self):
        (self.source / 'zzz').write_bytes(self.payload)
        self.interrupt_choice('skip')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        self.assertEqual((self.dest / 'zzz').read_bytes(), self.payload)
        self.assertTrue(any(e['type'] == 'item_result' and e['status'] == 'skipped' and e['reason'] == 'recovery_skip' for e in c.events), c.events)
        (self.dest / 'large').write_bytes(b'external skipped edit')
        (self.source / 'zzz').write_bytes(b'new source')
        del self.part
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'zzz').read_bytes(), self.payload)

    def test_interactive_keep_both_literal_byte_name_survives_resume(self):
        name = 'literal*?\n" café'
        self.interrupt_choice('keep_both', destination_name={'bytes_hex': os.fsencode(name).hex()})
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / name).read_bytes(), self.payload)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_completed_keep_both_choice_does_not_create_another_copy_on_resume(self):
        self.interrupt_choice('keep_both'); c, result = self.resume()
        self.assertEqual(result['status'], 'success', c.events)
        del self.part
        (self.source / 'large').write_bytes(self.payload + b'new tail')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large (copy 1)').read_bytes(), self.payload + b'new tail')
        self.assertFalse((self.dest / 'large (copy 2)').exists())
        self.assertGreater(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), 0)

    def test_edited_completed_keep_both_target_blocks_resume(self):
        self.interrupt_choice('keep_both'); c, result = self.resume()
        self.assertEqual(result['status'], 'success', c.events); del self.part
        (self.dest / 'large (copy 1)').write_bytes(b'external edit')
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'large (copy 1)').read_bytes(), b'external edit')

    def finish_choices(self, c, handler):
        while True:
            event = c.read()
            if event['type'] == 'conflict': handler(event)
            if event['type'] == 'result': c.proc.wait(timeout=6); return event

    def resume_with_choices(self, handler):
        request = copy.deepcopy(self.request); request.update(id='copy', op='resume', recovery_id=self.recovery_id)
        request['options']['bandwidth_bytes_per_second'] = '0'
        c = self.client(); c.send(request); return c, self.finish_choices(c, lambda e: handler(c, e))

    def test_scoped_skip_policy_survives_resume_without_expanding_directory_scope(self):
        (self.source / 'zzz').write_bytes(self.payload)
        (self.source / 'nested').mkdir(); (self.dest / 'nested').mkdir()
        (self.dest / 'nested' / 'file').write_bytes(b'old nested')
        (self.dest / 'future').write_bytes(b'old root')
        self.request['options']['on_conflict'] = 'ask'
        c = self.client(); c.send(self.request)
        while True:
            event = c.read()
            if event['type'] == 'recovery_created':
                self.recovery_id = event['recovery_id']; self.store = self.dest / '.xsync-app-partials' / self.recovery_id
            if event['type'] == 'conflict':
                self.answer_choice(c, event, 'skip' if event['kind'] == 'file_file' else 'replace',
                                   scope='directory' if event['kind'] == 'file_file' else 'item')
            if event['type'] == 'progress' and int(event.get('source_bytes_read') or '0') >= 262144:
                c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'}); c.finish(); break
            self.assertNotEqual(event['type'], 'result', c.events)
        (self.source / 'future').write_bytes(b'new root'); (self.source / 'nested' / 'file').write_bytes(b'new nested')
        prompts = []
        c, result = self.resume_with_choices(lambda client, e: (prompts.append(e), self.answer_choice(client, e)))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(len(prompts), 1, prompts)
        self.assertTrue(os.fsdecode(bytes.fromhex(prompts[0]['path']['bytes_hex'])).endswith('/nested/file'))
        self.assertEqual((self.dest / 'future').read_bytes(), b'old root')
        self.assertEqual((self.dest / 'nested' / 'file').read_bytes(), b'new nested')
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_job_scope_policy_applies_to_new_same_kind_conflicts_after_resume(self):
        (self.source / 'zzz').write_bytes(self.payload); (self.dest / 'future').write_bytes(b'old future')
        self.interrupt_choice('skip', scope='job')
        (self.source / 'future').write_bytes(b'new future')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
        self.assertEqual((self.dest / 'future').read_bytes(), b'old future')

    def test_keep_both_directory_restores_descendant_paths_on_resume(self):
        nested = self.source / 'nested'; nested.mkdir(); (self.source / 'large').rename(nested / 'large')
        old = self.dest / 'nested'; old.mkdir(); (old / 'sentinel').write_bytes(b'old nested')
        self.interrupt_choice('keep_both', pause=True)
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
        self.assertEqual((self.dest / 'nested (copy 1)' / 'large').read_bytes(), self.payload)
        self.assertEqual((old / 'sentinel').read_bytes(), b'old nested')
        self.assertFalse((self.dest / 'nested (copy 2)').exists())

    def test_saved_keep_both_mapping_collision_with_new_selection_reprompts(self):
        self.interrupt_choice('keep_both')
        (self.source / 'large (copy 1)').write_bytes(b'new selected sibling')
        prompts = []
        c, result = self.resume_with_choices(lambda client, e: (prompts.append(e), self.answer_choice(client, e, 'keep_both')))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(len(prompts), 1, prompts)
        self.assertEqual(prompts[0]['reason'], 'recovery_name_collision')
        self.assertNotIn('replace', prompts[0]['allowed_actions'])
        self.assertEqual((self.dest / 'large (copy 1)').read_bytes(), b'new selected sibling')
        self.assertEqual((self.dest / 'large (copy 1) (copy 1)').read_bytes(), self.payload)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_choice_metadata_disk_full_prevents_approval_and_staging(self):
        variable = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
        env = dict(os.environ, **{variable: str(self.fault), 'XSYNC_FAULT_PATH': str(self.dest.resolve()),
                                  'XSYNC_FAULT_RECOVERY_CHOICE_ERROR': str(errno.ENOSPC)})
        self.request['options']['on_conflict'] = 'ask'
        c = self.client(env); c.send(self.request)
        result = self.finish_choices(c, lambda e: self.answer_choice(c, e, 'keep_both'))
        self.assertNotEqual(result['status'], 'success', c.events)
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_write' and e.get('native_code') == str(errno.ENOSPC) for e in c.events), c.events)
        self.assertFalse(any(e['type'] == 'conflict_resolved' for e in c.events))
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        self.assertFalse((self.dest / 'large (copy 1)').exists())
        self.assertFalse(list((self.dest / '.xsync-app-partials').glob('*/*.part')))

    def test_publication_race_rebinds_private_receipt_to_new_keep_both_target(self):
        from app_test import AppTests
        marker, release = self.root / 'closed', self.root / 'release'
        variable = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
        env = dict(os.environ, **{variable: str(self.fault), 'XSYNC_FAULT_PATH': str(self.dest.resolve()),
                                  'XSYNC_FAULT_CLOSE_NOTIFY': str(marker), 'XSYNC_FAULT_CLOSE_RELEASE': str(release),
                                  'XSYNC_FAULT_CLOSE_SUFFIX': '.part'})
        self.request['options'].update(on_conflict='ask', bandwidth_bytes_per_second='0')
        c = self.client(env); c.send(self.request)
        while True:
            event = c.read()
            if event['type'] == 'recovery_created': self.recovery_id = event['recovery_id']
            if event['type'] == 'conflict': self.answer_choice(c, event, 'replace'); break
            self.assertNotEqual(event['type'], 'result', c.events)
        AppTests.wait_marker(self, marker)
        self.store = self.dest / '.xsync-app-partials' / self.recovery_id
        self.assertEqual(next(self.store.glob('*.part')).read_bytes(), self.payload)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        (self.dest / 'large').write_bytes(b'new external edit'); release.touch()
        result = self.finish_choices(c, lambda e: self.answer_choice(c, e, 'keep_both'))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), b'new external edit')
        self.assertEqual((self.dest / 'large (copy 1)').read_bytes(), self.payload)
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse((self.dest / 'large (copy 2)').exists())

    def test_colliding_selections_keep_separate_skip_and_copy_choices(self):
        probe = self.dest / 'CASE-probe'; probe.write_bytes(b'probe')
        equivalent = (self.dest / 'case-probe').exists(); probe.unlink()
        if not equivalent: self.skipTest('destination filesystem is case sensitive')
        second = self.source / 'second'; second.write_bytes(self.payload)
        self.request['sources'] = [{'endpoint': endpoint(path), 'mode': 'entry', 'destination_name': {'bytes_hex': name.hex()}}
                                   for path, name in ((self.source / 'large', b'ALIAS'), (second, b'alias'))]
        self.request['options'].update(on_conflict='ask', bandwidth_bytes_per_second='0')
        c = self.client(); c.send(self.request)
        result = self.finish_choices(c, lambda e: self.answer_choice(c, e, 'skip'))
        self.assertEqual(result['status'], 'success', c.events)
        self.recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
        self.assertEqual((self.dest / 'alias').read_bytes(), self.payload)
        self.assertEqual(sorted(e['decision'] for e in c.events if e['type'] == 'conflict_replayed'), ['copy', 'skip'])

    def test_malformed_saved_choice_cannot_redirect_resume_outside_destination(self):
        self.interrupt_choice('keep_both')
        path = next(self.store.glob('choice-*.json')); row = json.loads(path.read_text())
        outside = self.root / 'outside'; outside.write_bytes(b'outside preserved')
        row['destination_path'] = endpoint(outside)['path']; path.write_text(json.dumps(row))
        self.assert_resume_failure('recovery_record_changed')
        self.assertEqual(outside.read_bytes(), b'outside preserved')

    def test_duplicate_private_data_references_are_rejected_before_resume_writes(self):
        self.payload *= 2; (self.source / 'large').write_bytes(self.payload)
        (self.source / 'second').write_bytes(self.payload)
        self.request['options']['jobs'] = '2'
        c = self.client(); c.send(self.request)
        while True:
            event = c.read()
            if event['type'] == 'recovery_created':
                self.recovery_id = event['recovery_id']; self.store = self.dest / '.xsync-app-partials' / self.recovery_id
            if hasattr(self, 'store') and len(list(self.store.glob('*.part'))) == 2:
                c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'}); c.finish(); break
            self.assertNotEqual(event['type'], 'result', c.events)
        rows = [(p, json.loads(p.read_text())) for p in self.store.glob('*.json') if p.name != '.job.json']
        rows = [(p, r) for p, r in rows if r['state'] in ('active', 'retained')]
        self.assertEqual(len(rows), 2, rows)
        before = {p.name: p.read_bytes() for p in self.store.glob('*.part')}
        path, row = rows[1]; row['data_name'] = rows[0][1]['data_name']; row['data_identity'] = rows[0][1]['data_identity']
        path.write_text(json.dumps(row))
        self.assert_resume_failure('recovery_data_mapping_changed')
        self.assertEqual({p.name: p.read_bytes() for p in self.store.glob('*.part')}, before)

    def test_pause_while_waiting_for_conflict_resumes_with_a_fresh_unapproved_prompt(self):
        self.request['options']['on_conflict'] = 'ask'
        c = self.client(); c.send(self.request)
        while True:
            event = c.read()
            if event['type'] == 'recovery_created': self.recovery_id = event['recovery_id']
            if event['type'] == 'conflict': original = event; break
            self.assertNotEqual(event['type'], 'result', c.events)
        c.send({'id': 'pause', 'op': 'pause', 'job_id': 'copy'})
        self.assertEqual(c.finish()['status'], 'paused', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        prompts = []
        c, result = self.resume_with_choices(lambda client, e: (prompts.append(e), self.answer_choice(client, e, 'replace')))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(len(prompts), 1, prompts)
        self.assertNotEqual(prompts[0]['conflict_id'], original['conflict_id'])
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)

    def test_interrupt_resume_preserves_good_destination_and_reports_reuse(self):
        c = self.interrupted(); size = self.part.stat().st_size
        self.assertEqual(self.store.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.store.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.part.stat().st_mode & 0o777, 0o600)
        self.assertTrue(any(e['type'] == 'partial_retained' for e in c.events))
        c, result = self.resume(jobs='3')
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)
        summary = next(e for e in c.events if e['type'] == 'summary')
        self.assertEqual(int(summary['reused_bytes']), size)
        self.assertEqual(int(summary['logical_bytes_completed']), len(self.payload))
        self.assertFalse(list(self.store.glob('*.part')))
        self.assertEqual(self.state()['state'], 'completed')

    def test_changed_source_prefix_is_copied_fresh(self):
        self.interrupted()
        changed = b'new source' + self.payload[10:]
        (self.source / 'large').write_bytes(changed)
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), changed)
        self.assertEqual(next(e for e in c.events if e['type'] == 'summary')['reused_bytes'], '0')

    def test_changed_source_tail_reuses_only_matching_prefix(self):
        self.interrupted(); size = self.part.stat().st_size
        changed = self.payload[:size] + b'changed tail'
        (self.source / 'large').write_bytes(changed)
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), changed)
        self.assertEqual(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), size)

    def test_shrunken_source_truncates_retained_output(self):
        self.interrupted(); changed = self.payload[:8192]
        (self.source / 'large').write_bytes(changed)
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), changed)

    def test_empty_source_cannot_publish_old_partial_tail(self):
        self.interrupted(); (self.source / 'large').write_bytes(b'')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), b'')

    def test_corrupt_retained_prefix_is_never_trusted(self):
        self.interrupted()
        with self.part.open('r+b') as f: f.write(b'corrupt')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)
        self.assertEqual(next(e for e in c.events if e['type'] == 'summary')['reused_bytes'], '0')

    def test_replaced_destination_is_rejected_before_writes(self):
        self.interrupted(); (self.dest / 'large').write_bytes(b'external replacement')
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'large').read_bytes(), b'external replacement')

    def test_replaced_private_inode_is_rejected_and_preserved(self):
        self.interrupted(); original = self.part.read_bytes()
        replacement = self.store / 'replacement'; replacement.write_bytes(original)
        replacement.replace(self.part)
        self.assert_resume_failure('recovery_data_changed')

    def test_replaced_root_cannot_adopt_another_jobs_data(self):
        self.interrupted(); saved = self.root / 'saved'; self.dest.rename(saved); self.dest.mkdir()
        (self.dest / '.xsync-app-partials').symlink_to(saved / '.xsync-app-partials', target_is_directory=True)
        c, result = self.resume(); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertEqual((saved / 'large').read_bytes(), b'old good copy')
        self.assertFalse((self.dest / 'large').exists())

    def test_changed_selection_binding_is_rejected(self):
        self.interrupted(); alternate = self.root / 'alternate'; alternate.mkdir()
        (alternate / 'large').write_bytes(self.payload)
        self.request['sources'][0]['endpoint'] = endpoint(alternate)
        self.assert_resume_failure('recovery_binding_changed')

    def test_changed_semantic_option_binding_is_rejected(self):
        self.interrupted(); self.request['options']['preserve_times'] = False
        self.assert_resume_failure('recovery_binding_changed')

    def test_completed_destination_receipt_is_revalidated(self):
        self.request['options']['bandwidth_bytes_per_second'] = '0'
        c, result = self.job(self.request); self.assertEqual(result['status'], 'success', c.events)
        self.recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
        (self.dest / 'large').write_bytes(b'new independent edit')
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'large').read_bytes(), b'new independent edit')

    def test_all_destination_receipts_are_checked_before_any_resume_write(self):
        (self.source / 'first').write_bytes(b'first file')
        self.interrupted()
        rows = [json.loads(p.read_text()) for p in self.store.glob('*.json') if p.name != '.job.json']
        self.assertTrue(any(r['state'] == 'published' for r in rows), rows)
        (self.dest / 'first').write_bytes(b'external edit')
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'first').read_bytes(), b'external edit')

    def test_byte_path_selection_and_destination_mapping_survive_resume(self):
        original = self.source / 'large'; source = self.source / 'line\n" café'
        original.rename(source)
        self.request['sources'][0].update(endpoint=endpoint(source), mode='entry',
                                          destination_name={'bytes_hex': os.fsencode('mapped\n☃').hex()})
        c = self.begin(); c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'}); c.finish()
        self.part = next(self.store.glob('*.part'))
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'mapped\n☃').read_bytes(), self.payload)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_malformed_recovery_metadata_is_a_typed_failure(self):
        self.interrupted(); manifest = self.store / '.job.json'
        manifest.write_text('{}')
        self.assert_resume_failure('recovery_metadata_invalid')

    def test_managed_store_is_hidden_from_pane_and_recursive_app_copy(self):
        self.interrupted()
        c, result = self.job({'id': 'list', 'op': 'list', 'endpoint': endpoint(self.dest)})
        self.assertEqual(result['status'], 'success', c.events)
        names = [bytes.fromhex(e['name']['bytes_hex']) for event in c.events if event['type'] == 'entries' for e in event['entries']]
        self.assertNotIn(b'.xsync-app-partials', names)
        other = self.root / 'other'; other.mkdir()
        c, result = self.job(copy_request(self.dest, other))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual([p.name for p in other.iterdir()], ['large'])

    def test_foreign_same_named_directory_stays_visible_and_untouched(self):
        foreign = self.dest / '.xsync-app-partials'; foreign.mkdir(mode=0o700)
        (foreign / 'user-data').write_bytes(b'keep')
        c, result = self.job(self.request); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertEqual([p.name for p in foreign.iterdir()], ['user-data'])
        c, result = self.job({'id': 'list', 'op': 'list', 'endpoint': endpoint(self.dest)})
        names = [bytes.fromhex(e['name']['bytes_hex']) for event in c.events if event['type'] == 'entries' for e in event['entries']]
        self.assertIn(b'.xsync-app-partials', names)

    def test_cleanup_is_explicit_scoped_and_preserves_destination(self):
        self.interrupted(); sibling = self.store.parent / ('a' * 32); sibling.mkdir(mode=0o700)
        (sibling / 'user-data').write_bytes(b'keep')
        c, result = self.job(self.cleanup_request())
        self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(self.store.exists())
        self.assertEqual((sibling / 'user-data').read_bytes(), b'keep')
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_stale_cleanup_revision_removes_nothing(self):
        self.interrupted(); revision = self.state()['job_revision']
        (self.store / 'new-entry').write_bytes(b'keep')
        before = {p.name: p.read_bytes() for p in self.store.iterdir()}
        c, result = self.job(self.cleanup_request(revision)); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertEqual({p.name: p.read_bytes() for p in self.store.iterdir()}, before)

    def test_cleanup_rejects_symlinks_before_removing_any_file(self):
        self.interrupted(); link = self.store / 'foreign'; link.symlink_to(self.dest / 'large')
        before = sorted(p.name for p in self.store.iterdir())
        c, result = self.job(self.cleanup_request()); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertEqual(sorted(p.name for p in self.store.iterdir()), before)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_cleanup_rejects_unexpected_directories_and_hardlinks(self):
        self.interrupted()
        foreign = self.store / 'unexpected'; foreign.mkdir()
        c, result = self.job(self.cleanup_request()); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertTrue(self.part.exists()); foreign.rmdir()
        outside = self.root / 'linked'; os.link(self.part, outside)
        c, result = self.job(self.cleanup_request()); self.assertNotEqual(result['status'], 'success', c.events)
        self.assertTrue(self.part.exists()); self.assertTrue(outside.exists())

    def test_active_job_cannot_be_inspected_or_cleaned(self):
        c = self.begin()
        other, result = self.job({'id': 'state', 'op': 'recovery_state', 'endpoint': endpoint(self.dest), 'recovery_id': self.recovery_id})
        self.assertNotEqual(result['status'], 'success', other.events)
        self.assertTrue(any(e['type'] == 'error' and e['category'] == 'conflict' for e in other.events))
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'}); c.finish()

    def test_hard_killed_worker_data_requires_verification_on_resume(self):
        c = self.begin()
        children = subprocess.check_output(['pgrep', '-P', str(c.proc.pid)], text=True).split()
        self.assertEqual(len(children), 1, children)
        os.kill(int(children[0]), signal.SIGKILL)
        self.assertNotEqual(c.finish()['status'], 'success', c.events)
        self.assertEqual(self.state()['state'], 'active')
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)

    def test_unimplemented_recovery_modes_fail_before_staging(self):
        for options in ({'retain_partials': 'yes'}, {'delete': True}):
            request = copy.deepcopy(self.request); request['options'].update(options)
            c, result = self.job(request); self.assertNotEqual(result['status'], 'success', c.events)
            self.assertFalse((self.dest / '.xsync-app-partials').exists())

    def test_native_recovery_binding_must_match_options_and_destination_before_handoff(self):
        binding = {'sources': [], 'destination': endpoint(self.dest)['path'], 'on_conflict':'replace',
                   'preserve_times':True, 'preserve_permissions':True, 'source_kind':'local', 'destination_kind':'ssh',
                   'peer': {'host':'localhost','user':'','port':'22'}}
        base = {'id':'native','op':'_native_transfer','role':'receiver','idle_timeout_seconds':'30',
                'destination':endpoint(self.dest),'options':self.request['options'],
                'recovery_id':'b'*32,'resume':False,'recovery_binding':binding}
        for change in ('times','destination','credential'):
            with self.subTest(change=change):
                request = copy.deepcopy(base)
                if change == 'times': request['recovery_binding']['preserve_times'] = False
                if change == 'destination': request['recovery_binding']['destination'] = endpoint(self.source)['path']
                if change == 'credential': request['recovery_binding']['peer']['password'] = 'must-not-be-stored'
                c, result = self.job(request); self.assertNotEqual(result['status'],'success',c.events)
                self.assertFalse(any(e['type']=='transfer_ready' for e in c.events))
                self.assertFalse((self.dest/'.xsync-app-partials').exists())

    def test_native_recovery_binding_must_match_sender_selection_before_handoff(self):
        binding = {'sources':[{'path':endpoint(self.source/'different')['path'],'mode':'entry','destination_name':None}],
                   'destination':endpoint(self.dest)['path'],'on_conflict':'replace','preserve_times':True,'preserve_permissions':True,
                   'source_kind':'ssh','destination_kind':'local','peer':{'host':'localhost','user':'','port':'22'}}
        request = {'id':'native','op':'_native_transfer','role':'sender','idle_timeout_seconds':'30',
                   'sources':[{'endpoint':endpoint(self.source/'large'),'mode':'entry'}],
                   'options':self.request['options'],'recovery_id':'b'*32,'resume':False,'recovery_binding':binding}
        c, result = self.job(request); self.assertNotEqual(result['status'],'success',c.events)
        self.assertFalse(any(e['type']=='transfer_ready' for e in c.events))
        self.assertFalse((self.dest/'.xsync-app-partials').exists())

    def test_recovery_metadata_contains_semantics_without_resource_knobs(self):
        self.interrupted(); header = json.loads((self.store / '.job.json').read_text())
        self.assertNotIn('jobs', header['binding'])
        self.assertNotIn('bandwidth_bytes_per_second', header['binding'])
        self.assertEqual(header['binding']['on_conflict'], 'replace')
        self.assertEqual(header['binding']['sources'][0]['path']['bytes_hex'], os.fsencode(self.source).hex() + '2f')

    def test_reference_client_resumes_then_prepares_guarded_cleanup(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from app_client import AppClient, prepare_partial_cleanup, resume_request
        self.interrupted()
        original = copy.deepcopy(self.request)
        request = resume_request('resume', original, self.recovery_id)
        request['options']['bandwidth_bytes_per_second'] = '0'
        self.assertEqual(original, self.request)
        client = AppClient(BINARY)
        try: events = list(client.run(request))
        finally: client.close()
        self.assertEqual(events[-1]['status'], 'success', events)
        request = prepare_partial_cleanup(BINARY, endpoint(self.dest), self.recovery_id)
        c, result = self.job(request); self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(self.store.exists())
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)
        with self.assertRaises(ValueError): resume_request('resume', {'op': 'move'}, self.recovery_id)

    def test_disk_full_during_write_and_partial_trim_finishes_without_recursive_cleanup(self):
        variable = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
        env = dict(os.environ, **{variable: str(self.fault), 'XSYNC_FAULT_PATH': str(self.dest.resolve()),
                                   'XSYNC_FAULT_WRITE_ERROR': str(errno.ENOSPC), 'XSYNC_FAULT_TRUNCATE_ERROR': str(errno.ENOSPC)})
        c = self.client(env); c.send(self.request); result = c.finish(timeout=6)
        self.assertNotEqual(result['status'], 'success', c.events)
        errors = [e for e in c.events if e['type'] == 'error']
        self.assertTrue(any(e.get('operation') == 'trim private partial' and e.get('native_code') == str(errno.ENOSPC) for e in errors), errors)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        self.assertFalse(list((self.dest / '.xsync-app-partials').glob('*/*.part')))
        self.recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
        self.store = self.dest / '.xsync-app-partials' / self.recovery_id
        rows = [json.loads(p.read_text()) for p in self.store.glob('*.json') if p.name != '.job.json']
        self.assertEqual([r['state'] for r in rows if r.get('entry_type') != 'directory'], ['discarded'])
        (self.dest / 'large').write_bytes(b'new independent edit')
        self.assert_resume_failure('recovery_destination_changed')
        self.assertEqual((self.dest / 'large').read_bytes(), b'new independent edit')

    def test_discarded_prefix_is_copied_fresh_with_an_unchanged_destination(self):
        variable = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
        env = dict(os.environ, **{variable: str(self.fault), 'XSYNC_FAULT_PATH': str(self.dest.resolve()),
                                   'XSYNC_FAULT_WRITE_ERROR': str(errno.ENOSPC), 'XSYNC_FAULT_TRUNCATE_ERROR': str(errno.ENOSPC)})
        c = self.client(env); c.send(self.request); self.assertNotEqual(c.finish()['status'], 'success', c.events)
        self.recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)

    def test_prefix_changed_after_snapshot_is_rejected_when_reopened(self):
        self.interrupted()
        marker = self.root / 'source-prefix-check'
        variable = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
        env = dict(os.environ, **{variable: str(self.fault), 'XSYNC_FAULT_PATH': str((self.source / 'large').resolve()),
                                   'XSYNC_FAULT_PREAD_NOTIFY': str(marker), 'XSYNC_FAULT_PREAD_DELAY_US': '2000000'})
        request = copy.deepcopy(self.request)
        request.update(id='resume', op='resume', recovery_id=self.recovery_id)
        request['options']['bandwidth_bytes_per_second'] = '0'
        c = self.client(env); c.send(request)
        deadline = time.monotonic()+6
        while not marker.exists():
            self.assertLess(time.monotonic(), deadline, c.events)
            time.sleep(.01)
        # The destination prefix has been hashed. Change its full revision while
        # the corresponding source hash is held, before out_open/restore.
        with self.part.open('ab') as stream: stream.write(b'external change')
        result = c.finish()
        self.assertNotEqual(result['status'], 'success', c.events)
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_prefix_changed' for e in c.events), c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_pause_confirms_quiescence_and_resumes_the_same_private_job(self):
        c = self.begin(); c.send({'id': 'pause', 'op': 'pause', 'job_id': 'copy'})
        result = c.finish()
        self.assertEqual(result['status'], 'paused', c.events)
        self.assertEqual(result['cleanup'], 'finished')
        self.assertEqual(result['recovery_id'], self.recovery_id)
        self.assertTrue(next(e for e in c.events if e['type'] == 'pause_ack')['accepted'])
        self.assertTrue(next(e for e in c.events if e['type'] == 'paused')['receiver_quiescent'])
        assert_scope(self,c.events,self.dest)
        self.assertEqual(self.state()['state'], 'paused')
        self.part = next(self.store.glob('*.part')); kept = self.part.stat().st_size
        self.assertGreater(kept, 0)
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')
        c, result = self.resume()
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), kept)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)

    def test_pause_of_a_stuck_worker_waits_for_forced_reap_before_checkpoint(self):
        c = self.begin()
        worker = int(subprocess.check_output(['pgrep', '-P', str(c.proc.pid)]).strip())
        os.kill(worker, signal.SIGSTOP)  # Fixture simulates a worker that cannot handle TERM.
        c.send({'id': 'pause', 'op': 'pause', 'job_id': 'copy'})
        self.assertEqual(c.finish()['status'], 'paused', c.events)
        with self.assertRaises(ProcessLookupError): os.kill(worker, 0)
        self.assertEqual(self.state()['state'], 'paused')
        c, result = self.resume(); self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((self.dest / 'large').read_bytes(), self.payload)

    def test_cancel_overrides_an_accepted_pause(self):
        c = self.begin()
        c.send({'id': 'pause', 'op': 'pause', 'job_id': 'copy'})
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
        self.assertEqual(c.finish()['status'], 'cancellation', c.events)
        self.assertFalse(any(e['type'] == 'paused' for e in c.events))
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_pause_checkpoint_failure_never_reports_paused(self):
        c = self.begin(); (self.store / 'unexpected-directory').mkdir()
        c.send({'id': 'pause', 'op': 'pause', 'job_id': 'copy'})
        result = c.finish()
        self.assertEqual(result['status'], 'failure', c.events)
        self.assertEqual(result['cleanup'], 'unknown')
        self.assertFalse(any(e['type'] == 'paused' for e in c.events))
        self.assertEqual((self.dest / 'large').read_bytes(), b'old good copy')

    def test_pause_rejects_nonrecoverable_copy_without_stopping_it(self):
        request = copy.deepcopy(self.request); request['options']['retain_partials'] = False
        c = self.client(); c.send(request)
        while True:
            event = c.read()
            if event['type'] == 'progress' and int(event.get('source_bytes_read') or '0') >= 262144: break
            self.assertNotEqual(event['type'], 'result', c.events)
        c.send({'id': 'pause', 'op': 'pause', 'job_id': 'copy'})
        while (event := c.read())['type'] != 'pause_ack': self.assertNotEqual(event['type'], 'result', c.events)
        self.assertFalse(event['accepted'])
        self.assertEqual(event['reason'], 'unsupported_job')
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'copy'})
        self.assertEqual(c.finish()['status'], 'cancellation', c.events)

    def test_pause_rejects_a_changed_recorded_destination(self):
        c = self.begin(); (self.dest/'large').write_bytes(b'independent destination edit')
        c.send({'id':'pause','op':'pause','job_id':'copy'})
        self.assertEqual(c.finish()['status'],'failure',c.events)
        self.assertFalse(any(e['type']=='paused' for e in c.events))
        self.assertEqual((self.dest/'large').read_bytes(),b'independent destination edit')

    def test_pause_checkpoint_disk_full_never_reports_paused(self):
        variable = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
        env = dict(os.environ, **{variable: str(self.fault), 'XSYNC_FAULT_PATH': str(self.dest.resolve()),
                                  'XSYNC_FAULT_RECOVERY_PAUSE_ERROR': str(errno.ENOSPC)})
        c=self.client(env); c.send(self.request)
        while True:
            event=c.read()
            if event['type']=='progress' and int(event.get('source_bytes_read') or '0')>=262144: break
            self.assertNotEqual(event['type'],'result',c.events)
        c.send({'id':'pause','op':'pause','job_id':'copy'})
        result=c.finish(); self.assertEqual(result['status'],'failure',c.events)
        self.assertEqual(result['cleanup'],'unknown')
        self.assertTrue(any(e['type']=='error' and e.get('operation')=='recovery_write' and e['native_code']==str(errno.ENOSPC) for e in c.events),c.events)
        self.assertFalse(any(e['type']=='paused' for e in c.events))
        self.assertEqual((self.dest/'large').read_bytes(),b'old good copy')

    def test_frontend_eof_during_pause_check_is_cancellation(self):
        c=self.begin(); c.send({'id':'pause','op':'pause','job_id':'copy'})
        while (event:=c.read())['type']!='pause_pending': self.assertNotEqual(event['type'],'result',c.events)
        c.proc.stdin.close()
        self.assertEqual(c.finish()['status'],'cancellation',c.events)
        self.assertFalse(any(e['type']=='paused' for e in c.events))

    def test_reference_client_can_pause_from_live_progress_and_resume(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from app_client import AppClient,pause_request
        client=AppClient(BINARY); events=[]; sent=False
        try:
            for event in client.run(self.request):
                events.append(event)
                if not sent and event['type']=='progress' and int(event.get('source_bytes_read') or '0')>=262144:
                    client.send(pause_request('pause',self.request['id'])); sent=True
        finally: client.close()
        self.assertEqual(events[-1]['status'],'paused',events)
        self.recovery_id=events[-1]['recovery_id']
        _,result=self.resume(); self.assertEqual(result['status'],'success')
        self.assertEqual((self.dest/'large').read_bytes(),self.payload)

    def native_actor(self):
        c = self.client()
        source = self.source / 'large'
        binding = {'sources': [{'path': endpoint(source)['path'], 'mode': 'entry', 'destination_name': None}],
                   'destination': endpoint(self.dest)['path'], 'source_kind': 'ssh', 'destination_kind': 'local',
                   'peer': {'host': 'fixture', 'user': '', 'port': '0'}, 'on_conflict': 'replace',
                   'preserve_times': True, 'preserve_permissions': True}
        c.send({'id': 'actor', 'op': '_native_transfer', 'role': 'sender',
                'sources': [{'endpoint': endpoint(source), 'mode': 'entry'}], 'idle_timeout_seconds': '2',
                'options': {'on_conflict': 'replace', 'retain_partials': True, 'preserve_times': True, 'preserve_permissions': True},
                'recovery_id': '1'*32, 'attempt_id': '2'*32, 'resume': False, 'recovery_binding': binding})
        while True:
            event = c.read()
            if event['type'] == 'recovery_actor': return c, event
            self.assertNotEqual(event['type'], 'result', c.events)

    def actor_request(self, event, cleanup=False):
        sys.path.insert(0,str(ROOT/'tools'))
        from app_client import recovery_actor_request
        return recovery_actor_request('check',{'kind':'local','path':event['actor_path']},event,cleanup)

    def test_actor_cleanup_rejects_an_unexpected_child_before_removing_the_lease(self):
        c,actor=self.native_actor(); self.stop_actor(c,actor)
        folder=pathlib.Path(os.fsdecode(bytes.fromhex(actor['actor_path']['bytes_hex'])))
        (folder/'unexpected').symlink_to(self.source/'large')
        check,result=self.job(self.actor_request(actor,cleanup=True))
        self.assertNotEqual(result['status'],'success',check.events)
        self.assertTrue((folder/'lease').exists()); self.assertTrue((folder/'unexpected').is_symlink())
        self.assertFalse(any(e['type']=='recovery_quiescent' for e in check.events))
        (folder/'unexpected').unlink()
        check,result=self.job(self.actor_request(actor,cleanup=True)); self.assertEqual(result['status'],'success',check.events)

    def stop_actor(self, c, event):
        c.proc.kill(); c.proc.wait(timeout=3)
        deadline = time.monotonic()+6
        while True:
            check, result = self.job(self.actor_request(event))
            if result['status'] == 'success': return
            self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_actor_busy' for e in check.events), check.events)
            self.assertLess(time.monotonic(), deadline); time.sleep(.1)

    def test_actor_lease_proves_parent_and_worker_release_without_trusting_pids(self):
        c, actor = self.native_actor()
        check, result = self.job(self.actor_request(actor, cleanup=True))
        self.assertNotEqual(result['status'], 'success', check.events)
        self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_actor_busy' for e in check.events), check.events)
        self.stop_actor(c, actor)
        check, result = self.job(self.actor_request(actor, cleanup=True))
        self.assertEqual(result['status'], 'success', check.events)
        self.assertTrue(next(e for e in check.events if e['type'] == 'recovery_quiescent')['actor_cleaned'])
        self.assertFalse(pathlib.Path(os.fsdecode(bytes.fromhex(actor['actor_path']['bytes_hex']))).exists())

    def test_actor_lease_stays_busy_when_only_the_helper_parent_remains(self):
        c,actor=self.native_actor()
        worker=int(subprocess.check_output(['pgrep','-P',str(c.proc.pid)]).strip())
        os.kill(c.proc.pid,signal.SIGSTOP)
        try:
            os.kill(worker,signal.SIGKILL)
            check,result=self.job(self.actor_request(actor))
            self.assertNotEqual(result['status'],'success',check.events)
            self.assertTrue(any(e['type']=='error' and e.get('operation')=='recovery_actor_busy' for e in check.events),check.events)
        finally: os.kill(c.proc.pid,signal.SIGCONT)
        self.stop_actor(c,actor)
        check,result=self.job(self.actor_request(actor,cleanup=True))
        self.assertEqual(result['status'],'success',check.events)

    def test_actor_lease_replacement_and_stale_revision_do_not_prove_quiescence(self):
        c, actor = self.native_actor(); self.stop_actor(c, actor)
        folder = pathlib.Path(os.fsdecode(bytes.fromhex(actor['actor_path']['bytes_hex'])))
        request = self.actor_request(actor, cleanup=True)
        request['expected_actor_revision'] = dict(actor['actor_revision'], inode=str(int(actor['actor_revision']['inode'])+1))
        check, result = self.job(request); self.assertNotEqual(result['status'], 'success', check.events)
        self.assertTrue((folder/'lease').exists())
        (folder/'lease').rename(folder/'original')
        (folder/'lease').write_bytes((folder/'original').read_bytes()); (folder/'lease').chmod(0o600)
        check, result = self.job(self.actor_request(actor, cleanup=True))
        self.assertNotEqual(result['status'], 'success', check.events)
        self.assertFalse(any(e['type'] == 'recovery_quiescent' for e in check.events))
        (folder/'lease').unlink(); (folder/'original').rename(folder/'lease')
        # Rename changes ctime; deliberately refresh only the test's exact receipt.
        actor['actor_revision']['ctime_seconds'] = str((folder/'lease').stat().st_ctime_ns//1000000000)
        actor['actor_revision']['ctime_nanoseconds'] = str((folder/'lease').stat().st_ctime_ns%1000000000)
        check, result = self.job(self.actor_request(actor, cleanup=True)); self.assertEqual(result['status'], 'success', check.events)


if __name__ == '__main__': unittest.main()
