#!/usr/bin/env python3
"""Durable admission/outcome boundaries for the app-owned reference copy queue."""
import copy
import errno
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import app_test as api
from app_test import ROOT, BINARY, Client, copy_request
sys.path.insert(0, str(ROOT / 'tools'))
from app_queue import PersistentQueue, execute_next, execute_queue, reconcile_job, RecoveryUnavailable


class AppQueueTests(unittest.TestCase):
    setUpClass = classmethod(api.AppTests.setUpClass.__func__)
    fault_env = api.AppTests.fault_env

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs queue ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        self.dest = self.root / 'destination'; self.dest.mkdir()
        self.path = self.root / 'queue.json'
        self.request = copy_request(self.source, self.dest)

    def queue(self, **options):
        q = PersistentQueue(self.path, **options); self.addCleanup(q.close)
        return q

    def event(self, claim, kind, **fields):
        return dict(id=claim['request']['id'], type=kind, **fields)

    def test_private_identity_reservation_requires_exact_capability_and_survives_receipt_loss(self):
        for capability in (None, False, 1, '2', '1'):
            with self.subTest(capability=capability):
                q = self.queue(); request = self.reconnect_request(); request['options']['retain_partials'] = True
                q.enqueue(request, 'job', reconnect_delays=(0,), recover_disconnected=True); claim = q.claim()
                recovery = q.record_engine_capabilities('job', claim['request']['id'], {'copy_recovery_identity':capability})
                if capability == '1' and type(capability) is str:
                    self.assertRegex(recovery, r'^[0-9a-f]{32}$')
                    self.assertEqual(json.loads(self.path.read_text())['jobs'][0]['recovery_id'], recovery)
                    self.assertEqual(q.record_engine_capabilities('job', claim['request']['id'], {'copy_recovery_identity':'1'}), recovery)
                    with self.assertRaises(ValueError): q.accept('job', self.event(claim, 'recovery_created', recovery_id='f'*32))
                else: self.assertIsNone(recovery)
                q.close(); q = self.queue(); row = q.snapshot()[0]
                self.assertEqual(row['state'], 'needs_reconciliation'); self.assertEqual(row['recovery_id'], recovery)
                self.assertEqual(row['reconnect']['recovery']['pending'], recovery is not None)
                self.assertIsNone(q.claim()); q.close(); self.path.unlink()

    def test_worker_saves_reserved_identity_before_operation_and_old_engines_keep_receipts(self):
        for capable in (True, False):
            with self.subTest(capable=capable):
                q = self.queue(); request = copy.deepcopy(self.request); request['options']['retain_partials'] = True
                q.enqueue(request, 'job'); submitted = []
                class LostClient:
                    capabilities = {'copy_recovery_identity':'1'} if capable else {}
                    def __init__(self, _): pass
                    def run(inner, request, **_):
                        submitted.append(request)
                        persisted = json.loads(self.path.read_text())['jobs'][0]
                        self.assertEqual(request.get('recovery_id'), persisted['recovery_id'])
                        self.assertEqual('recovery_id' in request, capable)
                        raise RuntimeError('lost before first receipt')
                    def close(inner): pass
                with patch('app_client.AppClient', LostClient), self.assertRaisesRegex(RuntimeError, 'lost before first receipt'):
                    execute_next(q, BINARY)
                self.assertEqual(len(submitted), 1); self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')
                q.close(); self.path.unlink()

    def test_identity_reservation_commit_failure_prevents_operation_submission(self):
        q = self.queue(); request = copy.deepcopy(self.request); request['options']['retain_partials'] = True
        q.enqueue(request, 'job'); q.claim()
        with patch('app_queue.os.fsync', side_effect=OSError(errno.EIO, 'sync fault')):
            with self.assertRaises(OSError): q.record_engine_capabilities('job', 'job-1', {'copy_recovery_identity':'1'})
        self.assertIsNone(q.snapshot()[0]['recovery_id'])

    def unsubmitted_failure(self, q, claim, *, category='network', operation='ssh_connect', retryable=True, proof=True, capability='1'):
        q.record_engine_capabilities(claim['job_id'], claim['request']['id'], {'copy_reconnect':capability})
        q.accept(claim['job_id'], self.event(claim, 'error', category=category, operation=operation, retryable=retryable))
        if proof:
            q.accept(claim['job_id'], self.event(claim, 'copy_not_submitted', operation='copy', endpoint='ssh', remote_request_submitted=False, transfer_started=False))
        q.accept(claim['job_id'], self.event(claim, 'result', status='failure', code='12', cleanup='unknown'))

    def reconnect_request(self):
        request = copy.deepcopy(self.request); request['destination'].update(kind='ssh', profile_id='saved-host')
        return request

    def auto_recovery(self, delays=(0,0,0), *, outcome=False):
        q = self.queue(); request = self.reconnect_request(); request['options']['retain_partials'] = True
        q.enqueue(request, 'job', reconnect_delays=delays, recover_disconnected=True); claim = q.claim()
        q.accept('job', self.event(claim, 'recovery_created', recovery_id='a'*32))
        q.accept('job', self.event(claim, 'item_discovered', item_id='61', path={'bytes_hex':'61'}, entry_type='file'))
        if outcome:
            q.accept('job', self.event(claim, 'error', category='network', operation='transfer', retryable=True))
            q.accept('job', self.event(claim, 'result', status='partial_failure', code='23', cleanup='unknown', durability='filesystem-completion'))
        else: q.interrupted('job')
        return q

    def verify_auto_recovery(self, q, reserved):
        claim = reserved['claim']
        revision = {k:'1' for k in ('device','inode','links','mode','uid','gid','flags','size','mtime_seconds','mtime_nanoseconds','ctime_seconds','ctime_nanoseconds')}
        revision.update(exists=True, mode=str(0o40700))
        actor = {'type':'recovery_actor', 'endpoint':'ssh', 'role':'receiver', 'recovery_id':'a'*32,
                 'attempt_id':'b'*32, 'actor_path':{'bytes_hex':b'/tmp/xsync-app-actor-ABC123'.hex()},
                 'actor_revision':dict(revision,mode=str(0o100600))}
        request = q.reconciliation_request('job', claim)
        q.record_reconciliation('job', [dict(id=request['id'], type='recovery_state', recovery_id='a'*32,
            state='active', files_total='3', job_revision=revision, inventory_token='c'*32, actors=[actor]),
            dict(id=request['id'], type='result', status='success')], claim)
        request = q.verification_request('job', claim)
        q.record_verification('job', [dict(id=request['id'], type='recovery_verified', recovery_id='a'*32,
            inventory_token='c'*32, job_revision=revision, destination_guard_verified=True, pending_records='1',
            published_records='0', prepared_records='0', records_total='1', choices_total='0', bytes_retained='262144',
            source_verification_required=True, operation_completion_proven=False), dict(id=request['id'],type='result',status='success')],
            [dict(actor,type='recovery_quiescent',actor_cleaned=False)], claim)

    def test_auto_recovery_retains_known_network_result_and_requires_verified_resume_admission(self):
        q = self.auto_recovery(outcome=True)
        row = q.snapshot()[0]; self.assertEqual(row['state'], 'needs_reconciliation'); self.assertIsNone(row['result'])
        self.assertEqual(row['items']['61']['status'], 'unknown')
        self.assertEqual(row['reconnect']['history'][0]['status'], 'partial_failure')
        self.assertEqual(row['reconnect']['history'][0]['code'], '23')
        reserved = q.claim_recovery(); self.assertIsNone(q.claim()); self.assertIsNone(q.claim_recovery())
        with self.assertRaises(ValueError): q.finish_recovery('job', reserved['claim'])
        with self.assertRaises(ValueError): q.reconciliation_request('job')
        self.verify_auto_recovery(q, reserved)
        self.assertEqual(q.snapshot()[0]['state'], 'recoverable'); self.assertIsNone(q.claim())
        q.finish_recovery('job', reserved['claim']); claim = q.claim()
        self.assertEqual(claim['request']['op'], 'resume'); self.assertEqual(claim['request']['recovery_id'], 'a'*32)

    def test_auto_recovery_restart_retires_stale_claim_and_does_not_trust_a_saved_verification(self):
        q = self.auto_recovery(); first = q.claim_recovery(); self.verify_auto_recovery(q, first)
        q.close(); q = self.queue(); row = q.snapshot()[0]
        self.assertEqual(row['state'], 'needs_reconciliation'); self.assertNotIn('verification', row)
        self.assertEqual(row['reconnect']['retries'], 2); self.assertIsNone(q.claim())
        second = q.claim_recovery(); self.assertNotEqual(first['claim'], second['claim'])
        for callback in (lambda:q.reconciliation_request('job', first['claim']), lambda:q.finish_recovery('job',first['claim'])):
            with self.assertRaises(ValueError): callback()
        self.verify_auto_recovery(q, second); q.finish_recovery('job',second['claim']); self.assertEqual(q.claim()['request']['op'],'resume')

    def test_auto_recovery_budget_is_shared_with_unsubmitted_reconnects_and_read_only_failures(self):
        q = self.queue(); request = self.reconnect_request(); request['options']['retain_partials'] = True
        q.enqueue(request,'job',reconnect_delays=(0,0,0),recover_disconnected=True)
        claim = q.claim(); self.unsubmitted_failure(q,claim); claim = q.claim()
        q.accept('job',self.event(claim,'recovery_created',recovery_id='a'*32)); q.interrupted('job')
        reserved = q.claim_recovery(); q.finish_recovery('job',reserved['claim'],RecoveryUnavailable('busy',retryable=True))
        reserved = q.claim_recovery(); q.finish_recovery('job',reserved['claim'],RecoveryUnavailable('busy',retryable=True))
        row = q.snapshot()[0]; self.assertEqual(row['reconnect']['retries'],3)
        self.assertEqual([r['attempt'] for r in row['reconnect']['history']],[1,2,2])
        self.assertEqual(row['reason'],'automatic_recovery_budget_exhausted'); self.assertIsNone(q.claim_recovery())

    def test_auto_recovery_cancel_during_inspection_rejects_late_proofs_and_never_resumes(self):
        q = self.auto_recovery(); reserved = q.claim_recovery(); q.cancel_recovery('job')
        with self.assertRaises(ValueError): self.verify_auto_recovery(q,reserved)
        with self.assertRaises(ValueError): q.finish_recovery('job',reserved['claim'])
        q.close(); q = self.queue(); self.assertIsNone(q.claim_recovery()); self.assertIsNone(q.claim())
        self.assertEqual(q.snapshot()[0]['stop_requested'],'cancel'); self.assertIsNone(q.snapshot()[0]['result'])

    def test_auto_recovery_permanent_errors_and_prompt_cancellation_stop_rescheduling(self):
        for cancelled in (False,True):
            with self.subTest(cancelled=cancelled):
                q = self.auto_recovery(); reserved = q.claim_recovery()
                q.finish_recovery('job',reserved['claim'],RecoveryUnavailable('auth',cancelled=cancelled))
                self.assertIsNone(q.claim_recovery()); self.assertIsNone(q.next_reconnect_delay())
                row = q.snapshot()[0]; self.assertFalse(row['reconnect']['recovery']['pending'])
                self.assertEqual(row.get('stop_requested'), 'cancel' if cancelled else None)
                q.close(); self.path.unlink()

    def test_auto_recovery_policy_requires_private_ssh_scope_and_known_nonnetwork_errors_block_it(self):
        q = self.queue()
        for request, delays in ((self.request,(0,)), (self.reconnect_request(),(0,)), (self.reconnect_request(),())):
            with self.assertRaises(ValueError): q.enqueue(request,reconnect_delays=delays,recover_disconnected=True)
        request = self.reconnect_request(); request['options']['retain_partials'] = True
        q.enqueue(request,'job',reconnect_delays=(0,),recover_disconnected=True); claim = q.claim()
        q.accept('job',self.event(claim,'recovery_created',recovery_id='a'*32))
        q.accept('job',self.event(claim,'error',category='authentication',operation='ssh_connect',retryable=True)); q.interrupted('job')
        self.assertFalse(q.snapshot()[0]['reconnect']['recovery']['pending']); self.assertIsNone(q.claim_recovery())

    def test_auto_recovery_worker_inspects_and_reaps_before_resuming_and_blocks_changed_guards(self):
        q = self.auto_recovery(); phases = []
        def reconcile(queue, identity, _binary, **options):
            phases.append('inspect'); self.verify_auto_recovery(queue,{'job_id':identity,'claim':options['claim']})
        class Client:
            capabilities = {'copy_reconnect':'1'}
            def __init__(self,_): pass
            def run(self,request,**_):
                phases.append(request['op']); self_request = request['op']
                if self_request != 'resume': raise AssertionError('fresh copy after uncertain submission')
                yield dict(id=request['id'],type='result',status='success',code='0')
            def close(self): phases.append('reaped')
        with patch('app_queue.reconcile_job',reconcile),patch('app_client.AppClient',Client):
            results = list(execute_queue(q,BINARY,profile_resolver=lambda _:{'host':'runtime-only'}))
        self.assertEqual([r['status'] for r in results],['success']); self.assertEqual(phases,['inspect','resume','reaped'])
        q.close(); self.path.unlink(); q = self.auto_recovery()
        with patch('app_queue.reconcile_job',side_effect=ValueError('destination changed')),patch('app_client.AppClient',side_effect=AssertionError('must not launch')):
            self.assertEqual(list(execute_queue(q,BINARY)),[])
        self.assertEqual(q.snapshot()[0]['state'],'needs_reconciliation'); self.assertIsNone(q.claim())

    def test_auto_recovery_long_job_ids_and_forged_claim_state_cannot_bypass_admission(self):
        q = self.auto_recovery(); data = copy.deepcopy(q.data); identity = 'j'*96
        data['jobs'][0]['id'] = identity; q._commit(data)
        reserved = q.claim_recovery(); request = q.reconciliation_request(identity,reserved['claim'])
        self.assertLessEqual(len(request['id']),128)
        valid = copy.deepcopy(q.data)
        for mutation in ('queued','missing-claim','cancelled','no-private','no-history'):
            broken = copy.deepcopy(valid); row = broken['jobs'][0]
            if mutation == 'queued': row['state'] = 'queued'
            elif mutation == 'missing-claim': row['reconnect']['recovery']['claim'] = None
            elif mutation == 'cancelled': row['stop_requested'] = 'cancel'
            elif mutation == 'no-private': row['request']['options']['retain_partials'] = False
            else: row['reconnect']['history'][-1].pop('kind')
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): q._commit(broken)
        q.close(); self.path.write_text(json.dumps(broken)); before = self.path.read_bytes()
        with self.assertRaises(ValueError): PersistentQueue(self.path)
        self.assertEqual(self.path.read_bytes(),before)

    def test_auto_recovery_restart_with_exhausted_budget_does_not_reuse_an_unfinished_claim(self):
        q = self.auto_recovery(delays=(0,)); claim = q.claim_recovery()
        q.close(); q = self.queue()
        row = q.snapshot()[0]; self.assertEqual(row['state'],'needs_reconciliation')
        self.assertEqual(row['reason'],'automatic_recovery_budget_exhausted'); self.assertIsNone(q.claim_recovery())
        self.assertFalse(row['reconnect']['recovery']['pending'])
        with self.assertRaises(ValueError): q.finish_recovery('job',claim['claim'])

    def test_reconnect_deadline_budget_and_reorder_survive_restart_without_holding_active_slot(self):
        q = self.queue(); request = self.reconnect_request()
        q.enqueue(request, 'network', reconnect_delays=(.25, .5))
        q.enqueue(self.request, 'ready')
        with patch('app_queue.time.time_ns', return_value=1000000000):
            first = q.claim(); self.unsubmitted_failure(q, first)
            self.assertEqual(q.snapshot()[0]['state'], 'retry_waiting')
            self.assertEqual(q.next_reconnect_delay(), .25)
            self.assertEqual(q.claim()['job_id'], 'ready')
            q.accept('ready', {'id':'ready-1', 'type':'result', 'status':'success'})
            self.assertIsNone(q.claim())
        q.close(); q = self.queue(); q.reorder(['network'])
        with patch('app_queue.time.time_ns', return_value=1249000000): self.assertIsNone(q.claim())
        with patch('app_queue.time.time_ns', return_value=1250000000):
            second = q.claim(); self.assertEqual(second['request']['id'], 'network-2')
            self.unsubmitted_failure(q, second); self.assertEqual(q.next_reconnect_delay(), .5)
        with patch('app_queue.time.time_ns', return_value=1750000000):
            third = q.claim(); self.unsubmitted_failure(q, third)
        row = q.snapshot()[0]
        self.assertEqual(row['state'], 'failure'); self.assertEqual(row['attempt'], 3)
        self.assertEqual([h['attempt'] for h in row['reconnect']['history']], [1, 2])
        self.assertIsNone(q.claim()); self.assertIsNone(q.next_reconnect_delay())

    def test_reconnect_requires_exact_capability_receipt_network_error_and_complete_result(self):
        request = self.reconnect_request()
        for name, options in (('absent-proof', {'proof':False}), ('old-engine', {'capability':None}),
                              ('bool-capability', {'capability':True}), ('auth', {'category':'authentication'}),
                              ('host-key', {'category':'host_key'}), ('protocol', {'category':'protocol'}),
                              ('source-stream', {'operation':'transfer'}), ('not-retryable', {'retryable':False})):
            with self.subTest(name=name):
                path = self.root/(name+'.json'); q = PersistentQueue(path); self.addCleanup(q.close)
                q.enqueue(request, name, reconnect_delays=(0,)); claim = q.claim()
                self.unsubmitted_failure(q, claim, **options)
                self.assertEqual(q.snapshot()[0]['state'], 'failure'); self.assertIsNone(q.claim())
        q = self.queue(); q.enqueue(request, 'lost', reconnect_delays=(0,)); claim = q.claim()
        q.record_engine_capabilities('lost', claim['request']['id'], {'copy_reconnect':'1'})
        q.accept('lost', self.event(claim, 'error', category='network', operation='ssh_connect', retryable=True))
        q.accept('lost', self.event(claim, 'copy_not_submitted', operation='copy', endpoint='ssh', remote_request_submitted=False, transfer_started=False))
        q.close(); q = self.queue()
        self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation'); self.assertIsNone(q.claim())

    def test_reconnect_activity_conflicting_errors_and_stop_intent_disqualify_retry(self):
        for kind in ('item_discovered', 'recovery_created', 'phase', 'error', 'pause_ack', 'cancel_ack'):
            with self.subTest(kind=kind):
                q = PersistentQueue(self.root/(kind+'.json')); self.addCleanup(q.close)
                q.enqueue(self.reconnect_request(), 'job', reconnect_delays=(0,)); claim = q.claim()
                fields = {'item_discovered':{'item_id':'61', 'path':{'bytes_hex':'61'}, 'entry_type':'file'},
                          'recovery_created':{'recovery_id':'a'*32}, 'phase':{'phase':'scanning'},
                          'error':{'category':'authentication', 'operation':'ssh_connect', 'retryable':True},
                          'pause_ack':{'job_id':claim['request']['id'], 'accepted':True},
                          'cancel_ack':{'job_id':claim['request']['id'], 'accepted':True}}[kind]
                q.accept('job', self.event(claim, kind, **fields)); self.unsubmitted_failure(q, claim)
                self.assertEqual(q.snapshot()[0]['state'], 'failure'); self.assertIsNone(q.claim())

    def test_waiting_reconnect_can_be_cancelled_and_malformed_waiting_record_is_rejected(self):
        q = self.queue(); q.enqueue(self.reconnect_request(), 'job', reconnect_delays=(.1,)); claim = q.claim()
        self.unsubmitted_failure(q, claim); valid = copy.deepcopy(q.data)
        for field, value in (('not_submitted', False), ('engine_support', False), ('not_before_ms', None),
                             ('network_errors', 0), ('history', []), ('disqualified', True)):
            broken = copy.deepcopy(valid); broken['jobs'][0]['reconnect'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): q._commit(broken)
        q.cancel_queued('job'); q.close(); q = self.queue()
        self.assertEqual(q.snapshot()[0]['state'], 'cancellation'); self.assertIsNone(q.claim())

    def test_reconnect_claim_preserves_resume_identity_but_discards_unstarted_copy_identity(self):
        for operation in ('copy', 'resume'):
            with self.subTest(operation=operation):
                q = PersistentQueue(self.root/(operation+'.json')); self.addCleanup(q.close)
                request = self.reconnect_request(); request['options']['retain_partials'] = True
                q.enqueue(request, operation, reconnect_delays=(0,))
                data = copy.deepcopy(q.data); data['jobs'][0].update(next_operation=operation, recovery_id='a'*32); q._commit(data)
                claim = q.claim(); self.unsubmitted_failure(q, claim); claim = q.claim()
                row = q.snapshot()[0]
                if operation == 'resume': self.assertEqual(claim['request']['recovery_id'], 'a'*32)
                else: self.assertNotIn('recovery_id', claim['request']); self.assertIsNone(row['recovery_id'])

    def test_reconnect_policy_is_bounded_and_only_configurable_before_launch(self):
        q = self.queue()
        for delays in ((-1,), (6,), (True,), (float('nan'),), (0,)*9, '0'):
            with self.assertRaises(ValueError): q.enqueue(self.reconnect_request(), reconnect_delays=delays)
        q.enqueue(self.reconnect_request(), 'job'); q.set_reconnect('job', (.0001,))
        self.assertEqual(q.snapshot()[0]['reconnect']['delays_ms'], [1]); claim = q.claim()
        with self.assertRaises(ValueError): q.set_reconnect('job', ())
        with self.assertRaises(ValueError): q.record_engine_capabilities('job', 'stale-claim', {'copy_reconnect':'1'})
        self.unsubmitted_failure(q, claim); q.cancel_queued('job')

    def test_reconnect_clock_rollback_keeps_wait_bounded_and_persists_adjusted_deadline(self):
        q = self.queue(); q.enqueue(self.reconnect_request(), 'job', reconnect_delays=(.25,))
        with patch('app_queue.time.time_ns', return_value=10000000000):
            claim = q.claim(); self.unsubmitted_failure(q, claim)
        with patch('app_queue.time.time_ns', return_value=1000000000):
            self.assertEqual(q.next_reconnect_delay(), .25); self.assertIsNone(q.claim())
            self.assertEqual(q.snapshot()[0]['reconnect']['not_before_ms'], 1250)
        q.close(); q = self.queue()
        with patch('app_queue.time.time_ns', return_value=1250000000):
            self.assertEqual(q.claim()['request']['id'], 'job-2')

    def test_reconnect_result_commit_failure_requires_authoritative_disk_state_before_dispatch(self):
        for after_replace in (False, True):
            with self.subTest(after_replace=after_replace):
                path = self.root/('commit-'+str(after_replace)+'.json')
                q = PersistentQueue(path); self.addCleanup(q.close)
                q.enqueue(self.reconnect_request(), 'job', reconnect_delays=(0,)); claim = q.claim()
                q.record_engine_capabilities('job', claim['request']['id'], {'copy_reconnect':'1'})
                q.accept('job', self.event(claim, 'error', category='network', operation='ssh_connect', retryable=True))
                q.accept('job', self.event(claim, 'copy_not_submitted', operation='copy', endpoint='ssh', remote_request_submitted=False, transfer_started=False))
                sync = os.fsync; calls = []
                def failed_sync(fd):
                    calls.append(fd)
                    if len(calls) == 2: raise OSError(errno.EIO, 'directory sync')
                    return sync(fd)
                target, failure = ('app_queue.os.fsync', failed_sync) if after_replace else ('app_queue.os.replace', OSError(errno.EIO, 'replace'))
                with patch(target, side_effect=failure), self.assertRaises(OSError):
                    q.accept('job', self.event(claim, 'result', status='failure', code='12'))
                if after_replace:
                    with self.assertRaises(RuntimeError): q.claim()
                q.close(); q = PersistentQueue(path); self.addCleanup(q.close)
                if after_replace:
                    self.assertEqual(q.snapshot()[0]['state'], 'retry_waiting'); self.assertEqual(q.claim()['request']['id'], 'job-2')
                else:
                    self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation'); self.assertIsNone(q.claim())

    def test_reconnect_worker_reaps_each_attempt_resolves_profiles_again_and_stops_during_backoff(self):
        q = self.queue(); q.enqueue(self.reconnect_request(), 'job', reconnect_delays=(.01,))
        clients, profiles = [], []
        class FakeClient:
            def __init__(self, _):
                self.capabilities = {'copy_reconnect':'1'}; self.closed = False; clients.append(self)
            def run(self, request, **_):
                self_profile = request['destination']['connection']['host']
                if self_profile == 'offline':
                    yield dict(id=request['id'], type='error', category='network', operation='ssh_connect', retryable=True)
                    yield dict(id=request['id'], type='copy_not_submitted', operation='copy', endpoint='ssh', remote_request_submitted=False, transfer_started=False)
                    yield dict(id=request['id'], type='result', status='failure', code='12')
                else: yield dict(id=request['id'], type='result', status='success', code='0')
            def close(self): self.closed = True
        def profile(_): profiles.append(1); return {'host':'offline' if len(profiles) == 1 else 'online'}
        with patch('app_client.AppClient', FakeClient):
            results = list(execute_queue(q, BINARY, profile_resolver=profile))
        self.assertEqual([r['status'] for r in results], ['failure', 'success'])
        self.assertEqual(len(profiles), 2); self.assertTrue(all(c.closed for c in clients)); self.assertIsNone(q.claim())
        self.assertNotIn('offline', self.path.read_text()); self.assertNotIn('online', self.path.read_text())
        stopped = __import__('threading').Event()
        q.enqueue(self.reconnect_request(), 'stopped', reconnect_delays=(5,))
        with patch('app_client.AppClient', FakeClient):
            worker = execute_queue(q, BINARY, profile_resolver=lambda _: {'host':'offline'}, stop_event=stopped)
            self.assertEqual(next(worker)['status'], 'failure'); stopped.set()
            self.assertEqual(list(worker), [])
        self.assertEqual(q.snapshot()[-1]['state'], 'retry_waiting')

    def failed_inventory(self, q, outcomes, request=None, identity='original'):
        q.enqueue(request or self.request, identity); claim = q.claim()
        for relative, status, entry_type, destination in outcomes:
            raw = os.fsencode(relative); source = os.fsencode(self.source) + b'/' + raw
            q.accept(identity, self.event(claim, 'item_discovered', item_id=raw.hex(), path={'bytes_hex':raw.hex()},
                     source_path={'bytes_hex':source.hex()}, destination_path={'bytes_hex':os.fsencode(destination or self.dest / relative).hex()},
                     source_endpoint=(request or self.request)['sources'][0]['endpoint']['kind'],
                     destination_endpoint=(request or self.request)['destination']['kind'], entry_type=entry_type))
            if status != 'pending': q.accept(identity, self.event(claim, 'item_result', item_id=raw.hex(), status=status))
        q.accept(identity, self.event(claim, 'result', status='partial_failure', code='23'))
        return claim

    def test_retry_failed_maps_nested_leaves_and_preserves_original_outcomes_across_restart(self):
        q = self.queue()
        request = copy.deepcopy(self.request); request['options']['retain_partials'] = True
        self.failed_inventory(q, [('outer/file', 'failure', 'file', self.dest/'kept outer'/'renamed file'),
                                 ('outer/link', 'failure', 'symlink', self.dest/'kept outer'/'link'),
                                 ('good', 'success', 'file', None), ('cancelled', 'cancellation', 'file', None),
                                 ('unknown', 'pending', 'file', None)], request)
        parent = q.snapshot()[0]
        children = q.retry_failed('original'); self.assertEqual(len(children), 1)
        row = q.snapshot()[1]
        self.assertEqual(q.snapshot()[0], parent)
        self.assertEqual(row['request']['destination']['path']['bytes_hex'], os.fsencode(self.dest/'kept outer').hex())
        self.assertEqual(row['request']['sources'][0]['destination_name']['bytes_hex'], b'renamed file'.hex())
        self.assertEqual(row['request']['options']['on_conflict'], 'ask')
        self.assertTrue(row['request']['options']['retain_partials'])
        self.assertIsNone(row['recovery_id'])
        self.assertEqual(row['retry_of']['item_ids'], [b'outer/file'.hex(), b'outer/link'.hex()])
        q.close(); q = self.queue()
        with self.assertRaisesRegex(ValueError, 'already'): q.retry_failed('original')
        self.assertEqual(q.claim()['job_id'], children[0])

    def test_retry_failed_rejects_cancel_unknown_success_and_directory_broadening(self):
        q = self.queue()
        self.failed_inventory(q, [('dir', 'failure', 'directory', None), ('dir/failed', 'failure', 'file', None),
                                 ('dir/good', 'success', 'file', None), ('cancelled', 'cancellation', 'file', None),
                                 ('unknown', 'pending', 'file', None)])
        before = self.path.read_bytes()
        for items in (None, [b'dir/good'.hex()], [b'cancelled'.hex()], [b'unknown'.hex()], []):
            with self.assertRaises(ValueError): q.retry_failed('original', items)
            self.assertEqual(self.path.read_bytes(), before)
        children = q.retry_failed('original', [b'dir/failed'.hex()])
        self.assertEqual(len(children), 1)
        self.assertEqual(len(q.snapshot()[1]['request']['sources']), 1)

    def test_retry_failed_requires_authoritative_result_and_respects_saved_cancel_intent(self):
        q = self.queue(); self.failed_inventory(q, [('file', 'failure', 'file', None)])
        cancelled = copy.deepcopy(q.data); cancelled['jobs'][0]['stop_requested'] = 'cancel'; q._commit(cancelled)
        with self.assertRaisesRegex(ValueError, 'cancel intent'): q.retry_failed('original')
        q.enqueue(self.request, 'lost'); claim = q.claim()
        q.accept('lost', self.event(claim, 'item_discovered', item_id=b'file'.hex(), path={'bytes_hex':b'file'.hex()}, entry_type='file'))
        q.accept('lost', self.event(claim, 'item_result', item_id=b'file'.hex(), status='failure'))
        q.interrupted('lost')
        with self.assertRaisesRegex(ValueError, 'authoritative'): q.retry_failed('lost')

    def test_retry_failed_admission_is_atomic_and_keeps_runtime_profiles_outside_journal(self):
        q = self.queue(); request = copy.deepcopy(self.request)
        request['destination'].update(kind='ssh', profile_id='saved-host')
        self.failed_inventory(q, [('a/file', 'failure', 'file', None), ('b/file', 'failure', 'file', None)], request)
        before = self.path.read_bytes()
        with patch('app_queue.os.replace', side_effect=OSError(errno.EIO, 'injected')):
            with self.assertRaises(OSError): q.retry_failed('original')
        self.assertEqual(self.path.read_bytes(), before); self.assertEqual(len(q.snapshot()), 1)
        children = q.retry_failed('original'); self.assertEqual(len(children), 2)
        q.close(); q = self.queue()
        claim = q.claim()
        runtime = q.resolve_request(claim, lambda _: {'host':'example.test', 'password':'runtime-only-secret'})
        self.assertEqual(runtime['destination']['connection']['password'], 'runtime-only-secret')
        self.assertNotIn('runtime-only-secret', self.path.read_text())
        self.assertEqual(q.snapshot()[1]['request']['destination']['profile_id'], 'saved-host')

    def test_retry_failed_rejects_forged_mapping_and_malformed_saved_lineage(self):
        q = self.queue(); self.failed_inventory(q, [('file', 'failure', 'file', None)])
        for field, value in (('source_path', {'bytes_hex':os.fsencode(self.root/'unselected').hex()}),
                             ('destination_path', {'bytes_hex':os.fsencode(self.root/'outside').hex()}),
                             ('source_endpoint', 'ssh'), ('destination_endpoint', 'ssh')):
            with self.subTest(field=field):
                forged = copy.deepcopy(q.data); forged['jobs'][0]['items'][b'file'.hex()][field] = value
                q._commit(forged)
                with self.assertRaises(ValueError): q.retry_failed('original')
                restored = copy.deepcopy(q.data)
                restored['jobs'][0]['items'][b'file'.hex()] = {'item_id':b'file'.hex(), 'status':'failure', 'entry_type':'file',
                    'path':{'bytes_hex':b'file'.hex()}, 'source_path':{'bytes_hex':os.fsencode(self.source/'file').hex()},
                    'destination_path':{'bytes_hex':os.fsencode(self.dest/'file').hex()}, 'source_endpoint':'local', 'destination_endpoint':'local'}
                q._commit(restored)
        q.retry_failed('original'); valid = copy.deepcopy(q.data)
        for mutation in ('request', 'attempt', 'duplicate'):
            broken = copy.deepcopy(valid)
            if mutation == 'request': broken['jobs'][1]['request']['options']['on_conflict'] = 'replace'
            elif mutation == 'attempt': broken['jobs'][1]['retry_of']['attempt'] += 1
            else:
                duplicate = copy.deepcopy(broken['jobs'][1]); duplicate['id'] = 'duplicate'; broken['jobs'].append(duplicate)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): q._commit(broken)

    def test_real_retry_failed_preserves_keep_both_parent_and_completed_siblings(self):
        (self.source/'outer').mkdir(); leaf = self.source/'outer'/'file'
        leaf.write_bytes(b'incoming nested payload'*1000)
        (self.source/'good').write_text('completed sibling')
        (self.dest/'outer').mkdir(); (self.dest/'outer'/'file').write_text('original preserved')
        request = copy_request(self.source, self.dest, policy='ask', retain_partials=True, jobs='1')
        q = self.queue(); q.enqueue(request, 'original'); claim = q.claim()
        client = Client(self.fault_env(leaf, XSYNC_FAULT_READ_ERROR='1')); self.addCleanup(client.close)
        client.send(claim['request'])
        while True:
            event = client.read(); q.accept('original', event)
            if event['type'] == 'conflict':
                client.send({'id':'decision-'+event['conflict_id'], 'op':'conflict_response', 'job_id':claim['request']['id'],
                             'conflict_id':event['conflict_id'], 'revision_token':event['revision_token'], 'decision':'keep_both'})
            if event['type'] == 'result': break
        self.assertEqual(event['status'], 'partial_failure', client.events); client.close()
        parent = q.snapshot()[0]
        failed = parent['items'][b'outer/file'.hex()]
        self.assertEqual(failed['status'], 'failure')
        target = pathlib.Path(os.fsdecode(bytes.fromhex(failed['destination_path']['bytes_hex'])))
        self.assertEqual(target, self.dest/'outer (copy 1)'/'file')
        # New source bytes for a completed sibling must not enter this retry.
        (self.source/'good').write_text('changed completed source')
        target.write_text('external edit since failure')
        children = q.retry_failed('original'); q.close(); q = self.queue()
        conflicts = []
        def answer(event): conflicts.append(event); return 'replace'
        result = execute_next(q, BINARY, conflict_handler=answer)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(target.read_bytes(), leaf.read_bytes())
        self.assertEqual((self.dest/'outer'/'file').read_text(), 'original preserved')
        self.assertEqual((self.dest/'good').read_text(), 'completed sibling')
        self.assertEqual(q.snapshot()[0], parent)
        child = next(j for j in q.snapshot() if j['id'] == children[0])
        self.assertEqual(child['state'], 'success'); self.assertNotEqual(child['recovery_id'], parent['recovery_id'])

    def test_retry_lineage_supports_failed_children_and_preserves_cancelled_admission(self):
        q = self.queue(); self.failed_inventory(q, [('outer/file', 'failure', 'file', None)])
        first = q.retry_failed('original')[0]; claim = q.claim()
        selected = claim['request']['sources'][0]
        q.accept(first, self.event(claim, 'item_discovered', item_id=b'file'.hex(), path={'bytes_hex':b'file'.hex()},
                 source_path=selected['endpoint']['path'], destination_path={'bytes_hex':os.fsencode(self.dest/'outer'/'file').hex()},
                 source_endpoint='local', destination_endpoint='local', entry_type='file'))
        q.accept(first, self.event(claim, 'item_result', item_id=b'file'.hex(), status='failure'))
        q.accept(first, self.event(claim, 'result', status='failure'))
        second = q.retry_failed(first)[0]; q.cancel_queued(second); q.close(); q = self.queue()
        for identity in ('original', first):
            with self.assertRaisesRegex(ValueError, 'already'): q.retry_failed(identity)
        with self.assertRaises(ValueError): q.retry_failed(second)
        self.assertIsNone(q.claim())

    def test_reorder_and_active_admission_are_independent_of_worker_counts(self):
        q = self.queue(max_active=2)
        for name, workers in (('first', '64'), ('second', '1'), ('third', '0')):
            request = copy.deepcopy(self.request); request['options']['jobs'] = workers
            q.enqueue(request, name)
        q.reorder(['third', 'first', 'second'])
        with self.assertRaises(ValueError): q.reorder(['first', 'first', 'third'])
        one = q.claim(); two = q.claim()
        self.assertEqual((one['job_id'], two['job_id']), ('third', 'first'))
        self.assertIsNone(q.claim())
        q.accept(one['job_id'], self.event(one, 'result', status='success'))
        self.assertEqual(q.claim()['job_id'], 'second')
        self.assertEqual(two['request']['options']['jobs'], '64')

    def test_only_one_manager_and_private_regular_journal(self):
        q = self.queue()
        with self.assertRaises(BlockingIOError): PersistentQueue(self.path)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(pathlib.Path(str(self.path) + '.lock').stat().st_mode & 0o777, 0o600)
        q.close()
        q = self.queue(); q.close()
        self.path.chmod(0o644)
        with self.assertRaises(ValueError): PersistentQueue(self.path)
        self.path.unlink(); target = self.root / 'foreign'; target.write_text('preserve')
        self.path.symlink_to(target)
        with self.assertRaises(OSError): PersistentQueue(self.path)
        self.assertEqual(target.read_text(), 'preserve')

    def test_claim_is_committed_before_a_crash_and_never_dispatched_again(self):
        q = self.queue(); q.enqueue(self.request, 'started'); q.enqueue(self.request, 'waiting'); q.close()
        code = "from app_queue import PersistentQueue; import os; q=PersistentQueue(os.environ['QUEUE_PATH']); q.claim(); os._exit(17)"
        completed = subprocess.run([sys.executable, '-c', code], env=dict(os.environ, PYTHONPATH=str(ROOT/'tools'), QUEUE_PATH=str(self.path)), capture_output=True)
        self.assertEqual(completed.returncode, 17, completed.stderr)
        q = self.queue()
        jobs = q.snapshot()
        self.assertEqual((jobs[0]['state'], jobs[0]['reason']), ('needs_reconciliation', 'manager_restart'))
        self.assertEqual(q.claim()['job_id'], 'waiting')

    def test_lost_result_retains_reported_outcomes_and_marks_pending_unknown(self):
        q = self.queue(); q.enqueue(self.request, 'job'); claim = q.claim()
        for name in ('done', 'pending'):
            q.accept('job', self.event(claim, 'item_discovered', item_id=name.encode().hex(), path={'bytes_hex':name.encode().hex(), 'display':name}, entry_type='file'))
        q.accept('job', self.event(claim, 'item_result', item_id=b'done'.hex(), status='success', content_published=True, metadata_complete=True))
        q.close(); q = self.queue(); row = q.snapshot()[0]
        self.assertEqual(row['items'][b'done'.hex()]['status'], 'success')
        self.assertEqual(row['items'][b'pending'.hex()]['status'], 'unknown')
        self.assertIsNone(row['items'][b'pending'.hex()]['content_published'])
        self.assertIsNone(q.claim())
        with self.assertRaises(ValueError): q.request_resume('job')

    def test_ssh_profiles_and_prompt_secrets_never_enter_the_journal(self):
        q = self.queue(); request = copy.deepcopy(self.request)
        request['destination'].update(kind='ssh', profile_id='saved-host')
        q.enqueue(request, 'ssh'); claim = q.claim()
        calls = []
        def resolve(profile):
            calls.append(profile)
            return {'host':'example.test', 'identity_file':'/private/runtime-key', 'password':'runtime-secret'}
        runtime = q.resolve_request(claim, resolve)
        self.assertEqual(calls, ['saved-host'])
        self.assertEqual(runtime['destination']['connection']['password'], 'runtime-secret')
        for kind in ('auth_prompt', 'auth_response', 'conflict_response'):
            self.assertFalse(q.accept('ssh', self.event(claim, kind, answer='prompt-secret')))
        raw = self.path.read_text()
        self.assertNotIn('runtime-secret', raw); self.assertNotIn('runtime-key', raw); self.assertNotIn('prompt-secret', raw)
        request['destination']['connection'] = runtime['destination']['connection']
        with self.assertRaises(ValueError): q.enqueue(request)
        request = copy.deepcopy(self.request); request['options']['password'] = 'secret'
        with self.assertRaises(ValueError): q.enqueue(request)

    def test_authoritative_results_survive_restart_and_cancelled_work_does_not_retry(self):
        q = self.queue()
        for identity in ('completed', 'cancelled', 'waiting'): q.enqueue(self.request, identity)
        claim = q.claim(); q.accept('completed', self.event(claim, 'result', status='success', code='0', cleanup='finished'))
        q.cancel_queued('cancelled'); q.close(); q = self.queue()
        self.assertEqual([j['state'] for j in q.snapshot()], ['success', 'cancellation', 'queued'])
        with self.assertRaises(ValueError): q.request_resume('cancelled')
        self.assertEqual(q.claim()['job_id'], 'waiting')

    def test_stale_events_cannot_finish_a_new_attempt(self):
        q = self.queue(); request = copy.deepcopy(self.request); request['options']['retain_partials'] = True
        q.enqueue(request, 'job'); original = q.claim()
        q.accept('job', self.event(original, 'recovery_created', recovery_id='a'*32))
        q.accept('job', self.event(original, 'result', status='paused'))
        q.request_resume('job'); claim = q.claim()
        self.assertEqual(claim['request']['op'], 'resume')
        self.assertEqual(claim['request']['recovery_id'], 'a'*32)
        self.assertFalse(q.accept('job', self.event(original, 'result', status='success')))
        self.assertEqual(q.snapshot()[0]['state'], 'active')

    def test_metadata_write_failure_does_not_admit_work(self):
        q = self.queue(); q.enqueue(self.request, 'job'); before = self.path.read_bytes()
        with patch('app_queue.os.fsync', side_effect=OSError(errno.ENOSPC, 'full')):
            with self.assertRaises(OSError): q.claim()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(q.snapshot()[0]['state'], 'queued')
        self.assertFalse(list(self.root.glob('.xsync-queue-*')))
        self.assertEqual(q.claim()['job_id'], 'job')

    def test_directory_sync_failure_blocks_dispatch_until_reopened(self):
        q = self.queue(); q.enqueue(self.request, 'job')
        sync = os.fsync; calls = []
        def fail_directory(fd):
            calls.append(fd)
            if len(calls) == 2: raise OSError(errno.EIO, 'directory sync')
            return sync(fd)
        with patch('app_queue.os.fsync', side_effect=fail_directory):
            with self.assertRaises(OSError): q.claim()
        with self.assertRaises(RuntimeError): q.claim()
        q.close(); q = self.queue()
        self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')
        self.assertIsNone(q.claim())

    def test_bad_journal_is_preserved_and_never_reset_to_empty(self):
        q = self.queue(); q.enqueue(self.request, 'job'); q.close()
        for raw in (b'{"format":"1","format":"1","jobs":[]}', b'{broken', b'{"format":"99","jobs":[]}'):
            self.path.write_bytes(raw)
            with self.assertRaises(ValueError): PersistentQueue(self.path)
            self.assertEqual(self.path.read_bytes(), raw)

    def test_destructive_operations_and_unknown_request_fields_are_rejected(self):
        q = self.queue()
        for operation in ('move', 'delete', 'rename', 'resume'):
            request = copy.deepcopy(self.request); request['op'] = operation
            with self.assertRaises(ValueError): q.enqueue(request)
        request = copy.deepcopy(self.request); request['credentials'] = {'secret':'bad'}
        with self.assertRaises(ValueError): q.enqueue(request)
        self.assertFalse(q.snapshot())

    def test_incomplete_or_failed_items_cannot_be_acknowledged_as_success(self):
        q = self.queue(); q.enqueue(self.request, 'job'); claim = q.claim()
        q.accept('job', self.event(claim, 'item_discovered', item_id='61', path={'bytes_hex':'61'}))
        with self.assertRaises(ValueError): q.accept('job', self.event(claim, 'result', status='success'))
        q.accept('job', self.event(claim, 'item_result', item_id='61', status='failure'))
        with self.assertRaises(ValueError): q.accept('job', self.event(claim, 'result', status='success'))
        self.assertEqual(q.snapshot()[0]['state'], 'active')

    def test_inspection_is_an_observation_and_cannot_invent_job_completion(self):
        q = self.queue(); request = copy.deepcopy(self.request); request['options']['retain_partials'] = True
        q.enqueue(request, 'job'); claim = q.claim()
        q.accept('job', self.event(claim, 'recovery_preparing', recovery_id='b'*32))
        q.interrupted('job'); inspect = q.reconciliation_request('job')
        events = [dict(id=inspect['id'], type='recovery_state', recovery_id='b'*32, state='completed', files_total='7'),
                  dict(id=inspect['id'], type='result', status='success')]
        with self.assertRaises(ValueError): q.record_reconciliation('job', events[:-1])
        q.record_reconciliation('job', events)
        row = q.snapshot()[0]
        self.assertEqual(row['observation']['state'], 'completed')
        self.assertEqual(row['state'], 'needs_reconciliation')
        self.assertIsNone(row['result']); self.assertIsNone(q.claim())
        with self.assertRaises(ValueError): q.request_resume('job')

    def test_real_byte_mapping_copy_persists_outcomes_and_completed_queue(self):
        name = 'literal \n α[*]'; (self.source / name).write_bytes(b'copy payload')
        request = copy_request(self.source / name, self.dest, mode='entry')
        request['sources'][0]['destination_name'] = {'bytes_hex':os.fsencode('renamed\nΩ').hex()}
        q = self.queue(); q.enqueue(request, 'literal'); claim = q.claim()
        c = Client(); self.addCleanup(c.close); c.send(claim['request'])
        while True:
            event = c.read(); q.accept('literal', event)
            if event['type'] == 'result': break
        self.assertEqual(event['status'], 'success', c.events)
        self.assertEqual((self.dest / 'renamed\nΩ').read_bytes(), b'copy payload')
        q.close(); q = self.queue(); row = q.snapshot()[0]
        self.assertEqual(row['state'], 'success')
        self.assertEqual(row['request']['sources'][0]['destination_name'], request['sources'][0]['destination_name'])
        self.assertTrue(all(i['status'] == 'success' for i in row['items'].values()))
        self.assertIsNone(q.claim())

    def test_real_pause_restart_and_explicit_resume_reuses_private_prefix(self):
        payload = os.urandom(4*1024*1024); (self.source / 'large').write_bytes(payload)
        (self.dest / 'large').write_bytes(b'old good target')
        request = copy_request(self.source, self.dest, retain_partials=True, bandwidth_bytes_per_second='1048576', jobs='1')
        q = self.queue(); q.enqueue(request, 'copy'); claim = q.claim()
        c = Client(); self.addCleanup(c.close); c.send(claim['request']); stopping = False
        while True:
            event = c.read(); q.accept('copy', event)
            if not stopping and event['type'] == 'progress' and int(event.get('source_bytes_read') or '0') >= 262144:
                c.send({'id':'pause', 'op':'pause', 'job_id':claim['request']['id']}); stopping = True
            if event['type'] == 'result': break
        self.assertEqual(event['status'], 'paused', c.events)
        self.assertEqual((self.dest/'large').read_bytes(), b'old good target')
        recovery = q.snapshot()[0]['recovery_id']; self.assertIsNotNone(recovery)
        q.close(); q = self.queue(); self.assertIsNone(q.claim())
        q.request_resume('copy'); resumed = q.claim()
        self.assertEqual(resumed['request']['recovery_id'], recovery)
        c = Client(); self.addCleanup(c.close); c.send(resumed['request']); reused = 0
        while True:
            event = c.read(); q.accept('copy', event)
            if event['type'] == 'progress': reused = max(reused, int(event.get('reused_bytes') or '0'))
            if event['type'] == 'result': break
        self.assertEqual(event['status'], 'success', c.events)
        self.assertGreater(reused, 0); self.assertEqual((self.dest/'large').read_bytes(), payload)
        q.close(); q = self.queue(); self.assertEqual(q.snapshot()[0]['state'], 'success')

    def test_reference_worker_records_before_callbacks_and_does_not_repeat_success(self):
        (self.source/'file').write_bytes(b'worker payload')
        q = self.queue(); q.enqueue(self.request, 'job')
        def observe(event, client):
            if event['type'] == 'result': self.assertEqual(q.snapshot()[0]['state'], 'success')
        result = execute_next(q, BINARY, event_handler=observe)
        self.assertEqual(result['status'], 'success')
        self.assertEqual((self.dest/'file').read_bytes(), b'worker payload')
        self.assertIsNone(execute_next(q, BINARY))

    def test_worker_callback_failure_reaps_the_engine_and_keeps_unknown_work_out_of_dispatch(self):
        (self.source/'file').write_bytes(os.urandom(4*1024*1024))
        request = copy.deepcopy(self.request); request['options'].update(retain_partials=True, bandwidth_bytes_per_second='1048576')
        q = self.queue(); q.enqueue(request, 'job'); processes = []
        def observe(event, client):
            processes.append(client.process)
            if event['type'] == 'recovery_created': raise RuntimeError('UI disconnected')
        with self.assertRaisesRegex(RuntimeError, 'UI disconnected'): execute_next(q, BINARY, event_handler=observe)
        self.assertTrue(processes); self.assertTrue(all(p.poll() is not None for p in processes))
        self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')
        self.assertIsNotNone(q.snapshot()[0]['recovery_id'])
        self.assertIsNone(execute_next(q, BINARY))

    def interrupted_copy(self, *, completed=False):
        payload = os.urandom(4*1024*1024); (self.source/'large').write_bytes(payload)
        (self.dest/'large').write_bytes(b'old good target')
        request = copy.deepcopy(self.request); request['options'].update(retain_partials=True, bandwidth_bytes_per_second='1048576')
        if completed: request['options']['bandwidth_bytes_per_second'] = '0'
        q = self.queue(); q.enqueue(request, 'copy'); claim = q.claim()
        c = Client(); self.addCleanup(c.close); c.send(claim['request'])
        while True:
            event = c.read()
            if event['type'] == 'result':
                self.assertTrue(completed); self.assertEqual(event['status'], 'success', c.events)
                break  # Deliberately lose this authoritative result from the journal.
            q.accept('copy', event)
            if not completed and event['type'] == 'progress' and int(event.get('source_bytes_read') or '0') >= 262144:
                # Simulate an abrupt client/process loss, without user cancel intent.
                c.proc.kill(); c.proc.wait(timeout=5)
                # App supervision reaps its worker when its parent disappears.
                break
        c.close(); q.close(); q = self.queue()
        self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')
        return q, payload

    def test_unknown_partial_reconciles_then_explicit_resume_revalidates_source_bytes(self):
        q, payload = self.interrupted_copy()
        proof = reconcile_job(q, 'copy', BINARY)
        self.assertTrue(proof['actors_quiescent']); self.assertFalse(proof['operation_completion_proven'])
        self.assertGreater(int(proof['bytes_retained']), 0)
        self.assertEqual(q.snapshot()[0]['state'], 'recoverable'); self.assertIsNone(q.claim())
        # Reconciliation is a destination observation. Resume must hash against
        # the current source instead of assuming the original staged bytes match.
        replacement = b'changed source\n' * 1000
        (self.source/'large').write_bytes(replacement)
        q.request_resume('copy'); result = execute_next(q, BINARY)
        self.assertEqual(result['status'], 'success')
        self.assertEqual((self.dest/'large').read_bytes(), replacement)

    def test_lost_completed_result_reconciles_as_recoverable_without_inventing_success(self):
        q, payload = self.interrupted_copy(completed=True)
        proof = reconcile_job(q, 'copy', BINARY)
        self.assertEqual(proof['pending_records'], '0'); self.assertGreater(int(proof['published_records']), 0)
        row = q.snapshot()[0]; self.assertEqual(row['state'], 'recoverable'); self.assertIsNone(row['result'])
        self.assertEqual((self.dest/'large').read_bytes(), payload)
        q.close(); q = self.queue(); self.assertEqual(q.snapshot()[0]['state'], 'recoverable')
        q.request_resume('copy'); self.assertEqual(execute_next(q, BINARY)['status'], 'success')

    def test_changed_destination_stays_unknown_and_cannot_resume_after_reconciliation_failure(self):
        q, _ = self.interrupted_copy()
        (self.dest/'large').write_bytes(b'external target edit')
        with self.assertRaises(RuntimeError): reconcile_job(q, 'copy', BINARY)
        self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')
        self.assertIsNone(q.claim())
        with self.assertRaises(ValueError): q.request_resume('copy')
        self.assertEqual((self.dest/'large').read_bytes(), b'external target edit')

    def test_cancel_intent_is_persisted_before_send_and_lost_ack_cannot_enable_retry(self):
        q = self.queue(); request = copy.deepcopy(self.request); request['options']['retain_partials'] = True
        q.enqueue(request, 'job'); claim = q.claim()
        class Disconnected:
            def send(self, request): raise BrokenPipeError('lost control pipe')
        with self.assertRaises(BrokenPipeError): q.stop_active('job', Disconnected())
        q.close(); q = self.queue(); row = q.snapshot()[0]
        self.assertEqual(row['stop_requested'], 'cancel')
        self.assertEqual(row['reason'], 'cancel_requested_outcome_unknown')
        self.assertIsNone(q.claim())
        with self.assertRaises(ValueError): q.request_resume('job')

    def test_cancel_ack_matches_the_attempt_and_survives_missing_terminal_result(self):
        q = self.queue(); q.enqueue(self.request, 'job'); claim = q.claim()
        self.assertFalse(q.accept('job', {'id':'cancel', 'type':'cancel_ack', 'job_id':'job-0', 'accepted':True}))
        self.assertTrue(q.accept('job', {'id':'cancel', 'type':'cancel_ack', 'job_id':claim['request']['id'], 'accepted':True}))
        q.close(); q = self.queue()
        self.assertEqual(q.snapshot()[0]['stop_requested'], 'cancel')
        self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')

    def synthetic_verification(self, *, ssh=False, cleaned=False, save_close=False, cancelled=False):
        q = self.queue(); request = copy.deepcopy(self.request); request['options']['retain_partials'] = True
        if ssh: request['destination'].update(kind='ssh', profile_id='saved-host')
        q.enqueue(request, 'job'); claim = q.claim(); recovery = 'a'*32
        q.accept('job', self.event(claim, 'recovery_created', recovery_id=recovery))
        revision = {k:'1' for k in ('device', 'inode', 'links', 'mode', 'uid', 'gid', 'flags', 'size', 'mtime_seconds', 'mtime_nanoseconds', 'ctime_seconds', 'ctime_nanoseconds')}
        revision['exists'] = True
        revision['mode'] = str(0o40700)
        lease_revision = dict(revision, mode=str(0o100600))
        actor = {'type':'recovery_actor', 'endpoint':'ssh', 'role':'receiver', 'recovery_id':recovery,
                 'attempt_id':'b'*32, 'actor_path':{'bytes_hex':b'/tmp/xsync-app-actor-ABC123'.hex()}, 'actor_revision':lease_revision}
        if save_close:
            q.accept('job', dict(actor, id=claim['request']['id']))
            q.accept('job', dict(actor, type='recovery_quiescent', id=claim['request']['id'], actor_cleaned=True))
        if cancelled:
            q.accept('job', {'id':'cancel', 'type':'cancel_ack', 'job_id':claim['request']['id'], 'accepted':True})
        q.interrupted('job'); inspect = q.reconciliation_request('job')
        actors = [dict(actor, cleaned=True)] if cleaned else [actor] if ssh else []
        q.record_reconciliation('job', [dict(id=inspect['id'], type='recovery_state', recovery_id=recovery, state='active', files_total='3', job_revision=revision, inventory_token='c'*32, actors=actors),
                                        dict(id=inspect['id'], type='result', status='success')])
        verify = q.verification_request('job')
        events = [dict(id=verify['id'], type='recovery_verified', recovery_id=recovery, inventory_token='c'*32, job_revision=revision, destination_guard_verified=True,
                       pending_records='1', published_records='1', prepared_records='0', records_total='2', choices_total='0', bytes_retained='262144', source_verification_required=True, operation_completion_proven=False),
                  dict(id=verify['id'], type='result', status='success')]
        proof = dict(actor, type='recovery_quiescent', actor_cleaned=False)
        return q, events, proof

    def test_actor_quiescence_must_match_the_inspected_lifetime_receipt(self):
        q, events, proof = self.synthetic_verification(ssh=True)
        for proofs in ([], [dict(proof, attempt_id='d'*32)], [dict(proof, role='sender')], [dict(proof, endpoint='local')]):
            with self.assertRaises(ValueError): q.record_verification('job', events, proofs)
        self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')
        q.record_verification('job', events, [proof]); self.assertEqual(q.snapshot()[0]['state'], 'recoverable')

    def test_cleaned_marker_does_not_replace_an_authoritative_saved_close_proof(self):
        q, events, _ = self.synthetic_verification(ssh=True, cleaned=True)
        with self.assertRaises(ValueError): q.record_verification('job', events)
        self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')

    def test_saved_close_proof_survives_restart_and_verifies_the_exact_actor(self):
        q, events, _ = self.synthetic_verification(ssh=True, cleaned=True, save_close=True)
        q.close(); q = self.queue(); q.record_verification('job', events)
        self.assertEqual(q.snapshot()[0]['state'], 'recoverable')
        self.assertEqual(q.snapshot()[0]['closed_actors'][0]['attempt_id'], 'b'*32)

    def test_verified_work_still_cannot_retry_a_lost_cancel_intent(self):
        q, events, _ = self.synthetic_verification(cancelled=True)
        q.record_verification('job', events)
        row = q.snapshot()[0]
        self.assertEqual(row['state'], 'needs_reconciliation')
        self.assertEqual(row['reason'], 'cancel_requested_work_verified')
        self.assertTrue(row['verification']['actors_quiescent'])
        self.assertIsNone(q.claim())
        with self.assertRaises(ValueError): q.request_resume('job')

    def test_read_only_reconciliation_backoff_is_bounded_and_excludes_auth_changes_and_cancel(self):
        q = self.queue(); request = copy.deepcopy(self.request); request['options']['retain_partials'] = True
        q.enqueue(request, 'job'); claim = q.claim()
        q.accept('job', self.event(claim, 'recovery_created', recovery_id='a'*32)); q.interrupted('job')
        for category, operation, status, expected in (
            ('conflict', 'destination_lock', 'failure', 3),
            ('network', 'ssh_connect', 'failure', 3),
            ('authentication', 'ssh_connect', 'failure', 1),
            ('conflict', 'recovery_inventory_changed', 'failure', 1),
            ('network', 'ssh_connect', 'cancellation', 1),
        ):
            with self.subTest(operation=operation, category=category, status=status):
                clients = []
                class FakeClient:
                    def __init__(self, _):
                        self.capabilities = {'recovery_verification':'1'}; self.closed = False; clients.append(self)
                    def run(self, request, **_):
                        yield dict(id=request['id'], type='error', category=category, operation=operation, retryable=True)
                        yield dict(id=request['id'], type='result', status=status)
                    def close(self): self.closed = True
                with patch('app_client.AppClient', FakeClient), patch('app_queue.time.sleep') as sleep:
                    with self.assertRaises(RuntimeError): reconcile_job(q, 'job', BINARY, retry_delays=(0,0))
                self.assertEqual(len(clients), expected); self.assertTrue(all(c.closed for c in clients))
                self.assertEqual(sleep.call_count, expected-1)
                self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')

    def test_cancel_intent_cannot_be_loaded_as_ready_work(self):
        q = self.queue(); q.enqueue(self.request, 'job'); claim = q.claim()
        q.accept('job', {'id':'cancel', 'type':'cancel_ack', 'job_id':claim['request']['id'], 'accepted':True})
        q.interrupted('job'); q.close()
        data = json.loads(self.path.read_text()); data['jobs'][0]['state'] = 'queued'
        self.path.write_text(json.dumps(data)); before = self.path.read_bytes()
        with self.assertRaises(ValueError): PersistentQueue(self.path)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__': unittest.main()
