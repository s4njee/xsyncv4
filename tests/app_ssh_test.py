#!/usr/bin/env python3
"""Real SSH, without a TTY: machine browsing, host keys and askpass controls."""
import json
import hashlib
import errno
import os
import pathlib
import re
import select
import signal
import socket
import shlex
import subprocess
import sys
import tempfile
import time
import unittest

from app_test import BINARY, ROOT, Client, inventory, endpoint as local_endpoint
from app_refresh_test import assert_scope
import ssh_test
from ssh_test import HOST, SSH, remote_code, remote_json

PASSPHRASE = 'app-fixture-passphrase'
PASSWORD = 'app-fixture-password'
LOCAL_TMP = os.environ.get('XSYNC_APP_SSH_TEST_TMP', '/rig')
IDENTITY = os.environ.get('XSYNC_APP_SSH_TEST_IDENTITY', '/keys/id test')
PORT = os.environ.get('XSYNC_APP_SSH_TEST_PORT')
AUTH_PORT = os.environ.get('XSYNC_APP_SSH_TEST_AUTH_PORT', '2223')


@unittest.skipUnless(HOST, 'run via tests/ssh-rig.sh app_ssh_test.py')
class AppSSHTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ssh_test.SSHTests.setUpClass()
        cls.scratch = tempfile.TemporaryDirectory(dir=LOCAL_TMP, prefix='app ssh ')
        cls.root = pathlib.Path(cls.scratch.name)
        cls.key = cls.root / 'encrypted key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', PASSPHRASE, '-f', str(cls.key)], check=True)
        remote_code("import pathlib,sys; p=pathlib.Path('/root/.ssh/authorized_keys'); p.write_text(p.read_text()+sys.argv[1]); p.chmod(0o600)", cls.key.with_suffix('.pub').read_text())
        cls.daemon = int(remote_code(r'''import pathlib,subprocess,sys
subprocess.run(['chpasswd'],input='root:'+sys.argv[1]+'\n',text=True,check=True)
p=pathlib.Path('/rig/app_auth_sshd.conf')
p.write_text('Port 2223\nListenAddress 0.0.0.0\nHostKey /etc/ssh/ssh_host_ed25519_key\nPidFile /rig/app_auth_sshd.pid\nUsePAM no\nPermitRootLogin yes\nPasswordAuthentication yes\nKbdInteractiveAuthentication no\nStrictModes yes\n')
child=subprocess.Popen(['/usr/sbin/sshd','-D','-f',str(p)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
print(child.pid)
''', PASSWORD))
        remote_code(r'''import os,pathlib,sys
root=pathlib.Path(sys.argv[1]); root.mkdir(parents=True)
for name in [b'colon:name',b'*?',b'new\nline',b'-leading',b'invalid-\xff']:
 p=os.fsencode(root)+b'/'+name
 with open(p,'wb') as f: f.write(b'hello')
 os.utime(p,ns=(1600000000123456789,)*2)
os.symlink(b'new\nline',os.fsencode(root)+b'/link')
(root/'sub').mkdir(); (root/'sub'/'nested').write_text('nested')
''', cls.root / 'remote source')

    @classmethod
    def tearDownClass(cls):
        remote_code('import os,signal,sys,shutil; os.kill(int(sys.argv[1]),signal.SIGTERM); shutil.rmtree(sys.argv[2])', cls.daemon, cls.root)
        cls.scratch.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=LOCAL_TMP, prefix='app-profile-')
        self.addCleanup(self.tmp.cleanup)
        self.local = pathlib.Path(self.tmp.name)
        self.known = self.local / 'known hosts'
        self.config = self.local / 'config'
        self.config.write_text('Host *\n  IdentitiesOnly yes\n  PreferredAuthentications publickey\n')
        self.counter = 0

    def endpoint(self, path=None, **connection):
        profile = {'host': HOST, 'user': 'root', 'identity_file': IDENTITY,
                   'known_hosts_file': str(self.known), 'config_file': str(self.config),
                   'helper_path': '/usr/local/bin/xs', 'host_key_policy': 'ask', **connection}
        if PORT and 'port' not in profile:
            profile['port'] = PORT
        return {'kind': 'ssh', 'connection': profile,
                'path': {'bytes_hex': os.fsencode(path or self.root / 'remote source').hex()}}

    def client(self, env=None):
        c = Client(env)
        self.addCleanup(c.close)
        return c

    def response(self, c, prompt, answer=None, cancel=False, prompt_id=None):
        self.counter += 1
        request = {'id': 'answer-' + str(self.counter), 'op': 'auth_response',
                   'job_id': 'ssh', 'prompt_id': prompt_id or prompt['prompt_id']}
        if cancel:
            request['cancelled'] = True
        else:
            request['answer'] = answer
        c.send(request)

    def run_job(self, op='list', endpoint=None, answer=None, env=None, **fields):
        c = self.client(env)
        request = {'id':'ssh', 'op':op, **fields}
        if op not in ('move', 'copy', 'resume', 'verify_recovery', 'preview'): request['endpoint'] = endpoint or self.endpoint()
        c.send(request)
        while True:
            event = c.read(15)
            if event['type'] == 'auth_prompt':
                if event['kind'] == 'host_key':
                    self.response(c, event, 'yes')
                elif answer is not None:
                    self.response(c, event, answer)
                else:
                    self.fail('unexpected credential prompt')
            if event['type'] == 'result':
                c.proc.wait(timeout=6)
                return c, event

    def errors(self, c):
        return [e['category'] for e in c.events if e['type'] == 'error']

    def copy_job(self, sources, destination, policy='replace', answer=None, **options):
        return self.run_job('copy', answer=answer, sources=sources, destination=destination,
                            options={'on_conflict': policy, 'preserve_times': True,
                                     'preserve_permissions': True, **options})

    def private_recovery_fixture(self, push, suffix=''):
        folder = self.local / (('push' if push else 'pull')+suffix); folder.mkdir()
        remote = self.root / (self.local.name + ('-push' if push else '-pull')+suffix)
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        source = folder / 'source'; source.write_bytes(os.urandom(4*1024*1024))
        name = 'line\n" café'
        if push:
            remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/sys.argv[2]).write_bytes(b"old good")', remote, name)
            sources, destination = [{'endpoint': local_endpoint(source), 'mode': 'entry',
                                      'destination_name': {'bytes_hex': os.fsencode(name).hex()}}], self.endpoint(remote)
        else:
            command = shlex.join(['python3','-c','import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())',str(remote/'source')])
            subprocess.run([*SSH,HOST,command],input=source.read_bytes(),check=True,capture_output=True,timeout=10)
            target = folder / 'destination'; target.mkdir(); (target / name).write_bytes(b'old good')
            sources, destination = [{'endpoint': self.endpoint(remote / 'source'), 'mode': 'entry',
                                      'destination_name': {'bytes_hex': os.fsencode(name).hex()}}], local_endpoint(target)
        return {'id': 'ssh', 'op': 'copy', 'sources': sources, 'destination': destination,
                'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True,
                            'retain_partials': True, 'jobs': '1', 'bandwidth_bytes_per_second': '524288'}}, source, name

    def interrupt_private_copy(self, request):
        c = self.client(); c.send(request); recovery_id = None
        while True:
            event = c.read(15)
            if event['type'] == 'auth_prompt': self.response(c,event,'yes')
            if event['type'] == 'recovery_created': recovery_id = event['recovery_id']
            if event['type'] == 'item_progress' and event.get('side') == 'destination' and int(event['bytes_processed']) >= 262144:
                self.assertIsNotNone(recovery_id, c.events); break
            self.assertNotEqual(event['type'], 'result', c.events)
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'ssh'})
        self.assertEqual(c.finish()['status'], 'cancellation', c.events)
        return recovery_id

    def test_persistent_queue_pause_restart_and_keep_both_resume_push_and_pull(self):
        sys.path.insert(0, str(ROOT/'tools'))
        from app_queue import PersistentQueue, execute_next, execute_queue
        for push in (True, False):
            with self.subTest(push=push):
                request, source, original_name = self.private_recovery_fixture(push, '-queue')
                request['options']['on_conflict'] = 'ask'
                profile = None
                for ep in [request['destination']] + [s['endpoint'] for s in request['sources']]:
                    if ep['kind'] == 'ssh':
                        profile = ep.pop('connection'); ep['profile_id'] = 'saved-host'
                path = self.local / ('push-queue.json' if push else 'pull-queue.json')
                q = PersistentQueue(path); self.addCleanup(q.close)
                q.enqueue(request, 'transfer', reconnect_delays=(.05, .1)); paused = False; choices = []
                def choose(event):
                    choices.append(event)
                    return 'keep_both'
                def observe(event, client):
                    nonlocal paused
                    if not paused and event['type'] == 'item_progress' and event.get('side') == 'destination' and int(event['bytes_processed']) >= 262144:
                        self.assertIsNotNone(q.snapshot()[0]['recovery_id'])
                        client.send({'id':'pause', 'op':'pause', 'job_id':event['id']}); paused = True
                result = execute_next(q, BINARY, profile_resolver=lambda _: profile,
                                      prompt_handler=lambda _: 'yes', conflict_handler=choose, event_handler=observe)
                self.assertEqual(result['status'], 'paused'); self.assertEqual(len(choices), 1)
                recovery = q.snapshot()[0]['recovery_id']; q.close()
                q = PersistentQueue(path); self.addCleanup(q.close)
                self.assertEqual(q.snapshot()[0]['state'], 'paused')
                self.assertIsNone(execute_next(q, BINARY))
                q.request_resume('transfer'); unexpected = []; reused = []
                def no_new_choice(event): unexpected.append(event); return 'cancel'
                def resumed(event, _):
                    if event['type'] == 'progress': reused.append(int(event.get('reused_bytes') or '0'))
                with socket.socket() as refused:
                    refused.bind(('127.0.0.1', 0)); calls = []
                    def reconnect(_):
                        calls.append(1)
                        return dict(profile, port=str(refused.getsockname()[1])) if len(calls) == 1 else profile
                    outcomes = list(execute_queue(q, BINARY, profile_resolver=reconnect,
                                    prompt_handler=lambda _: 'yes', conflict_handler=no_new_choice, event_handler=resumed))
                self.assertEqual([r['status'] for r in outcomes], ['failure', 'success'])
                result = outcomes[-1]
                self.assertEqual(result['status'], 'success'); self.assertFalse(unexpected)
                self.assertGreater(max(reused or [0]), 0)
                row = q.snapshot()[0]; self.assertEqual(row['recovery_id'], recovery)
                self.assertEqual(row['attempt'], 3); self.assertEqual(row['reconnect']['retries'], 1)
                item = next(i for i in row['items'].values() if i['entry_type'] == 'file')
                actual = os.fsdecode(bytes.fromhex(item['destination_path']['bytes_hex']))
                parent = os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex']))
                if push:
                    observed = remote_json('import hashlib,json,pathlib,sys; print(json.dumps([hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(),(pathlib.Path(sys.argv[2])/sys.argv[3]).read_text()]))', actual, parent, original_name)
                    self.assertEqual(observed, [hashlib.sha256(source.read_bytes()).hexdigest(), 'old good'])
                else:
                    self.assertEqual(pathlib.Path(actual).read_bytes(), source.read_bytes())
                    self.assertEqual((pathlib.Path(parent)/original_name).read_text(), 'old good')
                raw = path.read_text()
                for field in ('identity_file', 'known_hosts_file', 'config_file', 'helper_path', 'connection', 'auth_prompt'):
                    self.assertNotIn(field, raw)
                q.close(); q = PersistentQueue(path); self.addCleanup(q.close)
                self.assertEqual(q.snapshot()[0]['state'], 'success'); self.assertIsNone(q.claim())

    def test_queue_reconnect_unsubmitted_copy_restart_and_profile_refresh_push_and_pull(self):
        sys.path.insert(0, str(ROOT/'tools'))
        from app_queue import PersistentQueue, execute_queue
        with socket.socket() as refused:
            refused.bind(('127.0.0.1', 0)); port = str(refused.getsockname()[1])
            for push in (True, False):
                with self.subTest(push=push):
                    request, source, name = self.private_recovery_fixture(push, '-reconnect')
                    request['options']['bandwidth_bytes_per_second'] = '0'
                    profile = None
                    for ep in [request['destination']] + [s['endpoint'] for s in request['sources']]:
                        if ep['kind'] == 'ssh': profile = ep.pop('connection'); ep['profile_id'] = 'saved-host'
                    calls = []
                    def resolve(_):
                        calls.append(1)
                        return dict(profile, port=port) if len(calls) == 1 else profile
                    path = self.local / ('reconnect-'+str(push)+'.json')
                    q = PersistentQueue(path); self.addCleanup(q.close)
                    q.enqueue(request, 'transfer', reconnect_delays=(.1, .2)); events = []
                    worker = execute_queue(q, BINARY, profile_resolver=resolve, prompt_handler=lambda _:'yes',
                                           event_handler=lambda event,_:events.append(event))
                    first = next(worker)
                    self.assertEqual(first['status'], 'failure', events)
                    self.assertEqual(q.snapshot()[0]['state'], 'retry_waiting')
                    self.assertEqual(len([e for e in events if e['type'] == 'copy_not_submitted']), 1)
                    self.assertFalse(any(e['type'] in ('item_discovered', 'recovery_created', 'recovery_actor') for e in events))
                    first_identity = q.snapshot()[0]['recovery_id']
                    destination = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                    code = 'import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([(p/sys.argv[2]).read_bytes().decode(),(p/".xsync-app-partials").exists()]))'
                    untouched = remote_json(code, destination, name) if push else json.loads(subprocess.check_output([sys.executable,'-c',code,str(destination),name],text=True))
                    self.assertEqual(untouched, ['old good', False])
                    worker.close(); q.close(); q = PersistentQueue(path); self.addCleanup(q.close)
                    remaining = list(execute_queue(q, BINARY, profile_resolver=resolve, prompt_handler=lambda _:'yes'))
                    self.assertEqual([r['status'] for r in remaining], ['success'])
                    row = q.snapshot()[0]
                    self.assertEqual(row['state'], 'success'); self.assertEqual(row['attempt'], 2)
                    self.assertEqual(row['reconnect']['retries'], 1); self.assertEqual(len(calls), 2)
                    self.assertNotEqual(row['recovery_id'], first_identity)
                    self.assertNotIn(IDENTITY, path.read_text())
                    target = destination/name
                    actual = bytes.fromhex(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).read_bytes().hex()))', target)) if push else target.read_bytes()
                    self.assertEqual(actual, source.read_bytes()); self.assertIsNone(q.claim())

    def test_queue_does_not_reconnect_after_remote_copy_request_was_submitted(self):
        sys.path.insert(0, str(ROOT/'tools'))
        from app_queue import PersistentQueue, execute_queue
        for push in (True, False):
            with self.subTest(push=push):
                request, source, name = self.private_recovery_fixture(push, '-submitted')
                marker = self.root/(self.local.name+'-submitted-'+str(push))
                helper = self.root/(self.local.name+'-drop-helper-'+str(push))
                script = '''#!/usr/bin/python3
import json,pathlib,subprocess,sys
child=subprocess.Popen(['/usr/local/bin/xs','--app'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
child.stdin.write(sys.stdin.buffer.readline()); child.stdin.flush()
sys.stdout.buffer.write(child.stdout.readline()); sys.stdout.buffer.flush()
request=sys.stdin.buffer.readline()
pathlib.Path(MARKER).write_bytes(request)
child.stdin.close(); child.wait()
'''.replace('MARKER', repr(str(marker)))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o700)', helper, script)
                profile = None
                for ep in [request['destination']] + [s['endpoint'] for s in request['sources']]:
                    if ep['kind'] == 'ssh':
                        profile = ep.pop('connection'); profile['helper_path'] = str(helper); ep['profile_id'] = 'saved-host'
                q = PersistentQueue(self.local/('submitted-'+str(push)+'.json')); self.addCleanup(q.close)
                q.enqueue(request, 'transfer', reconnect_delays=(0,0)); events = []
                results = list(execute_queue(q, BINARY, profile_resolver=lambda _:profile, prompt_handler=lambda _:'yes',
                                             event_handler=lambda event,_:events.append(event)))
                self.assertEqual(len(results), 1); self.assertEqual(results[0]['status'], 'failure')
                self.assertFalse(any(e['type'] == 'copy_not_submitted' for e in events), events)
                submitted = remote_json('import pathlib,sys,json; print(json.dumps(json.loads(pathlib.Path(sys.argv[1]).read_bytes())))', marker)
                self.assertEqual(submitted['op'], '_native_transfer')
                self.assertEqual(submitted['role'], 'receiver' if push else 'sender')
                row = q.snapshot()[0]; self.assertEqual(row['attempt'], 1)
                self.assertEqual(row['reconnect']['retries'], 0); self.assertIsNone(q.claim())

    def test_unknown_queue_copy_reconciles_helper_and_destination_guards_before_resume_push_and_pull(self):
        sys.path.insert(0, str(ROOT/'tools'))
        from app_queue import PersistentQueue, execute_next, reconcile_job
        for push in (True, False):
            with self.subTest(push=push):
                request, source, name = self.private_recovery_fixture(push, '-reconcile')
                request['options']['on_conflict'] = 'ask'; profile = None
                for ep in [request['destination']] + [s['endpoint'] for s in request['sources']]:
                    if ep['kind'] == 'ssh': profile = ep.pop('connection'); ep['profile_id'] = 'saved-host'
                path = self.local / ('push-reconcile.json' if push else 'pull-reconcile.json')
                q = PersistentQueue(path); self.addCleanup(q.close); q.enqueue(request, 'transfer')
                def lost_ui(event, _):
                    if event['type'] == 'item_progress' and event.get('side') == 'destination' and int(event['bytes_processed']) >= 262144:
                        raise RuntimeError('UI event consumer disappeared')
                with self.assertRaisesRegex(RuntimeError, 'UI event consumer disappeared'):
                    execute_next(q, BINARY, profile_resolver=lambda _:profile, prompt_handler=lambda _:'yes', conflict_handler=lambda _:'keep_both', event_handler=lost_ui)
                self.assertEqual(q.snapshot()[0]['state'], 'needs_reconciliation')
                self.assertIsNone(q.snapshot()[0].get('stop_requested'))
                q.close(); q = PersistentQueue(path); self.addCleanup(q.close)
                observed = []
                proof = reconcile_job(q, 'transfer', BINARY, profile_resolver=lambda _:profile,
                                      prompt_handler=lambda _:'yes', event_handler=lambda event,_:observed.append(event))
                self.assertTrue(proof['actors_quiescent']); self.assertGreater(int(proof['bytes_retained']), 0)
                self.assertFalse(proof['operation_completion_proven']); self.assertEqual(q.snapshot()[0]['state'], 'recoverable')
                self.assertTrue(any(e['type'] == 'recovery_quiescent' and e['endpoint'] == 'ssh' for e in observed), observed)
                self.assertTrue(any(e['type'] == 'recovery_verified' and e['endpoint'] == ('ssh' if push else 'local') for e in observed), observed)
                self.assertIsNone(q.claim()); q.request_resume('transfer'); prompts = []; reused = []
                def unexpected(event): prompts.append(event); return 'cancel'
                def progress(event, _):
                    if event['type'] == 'progress': reused.append(int(event.get('reused_bytes') or '0'))
                result = execute_next(q, BINARY, profile_resolver=lambda _:profile, prompt_handler=lambda _:'yes', conflict_handler=unexpected, event_handler=progress)
                self.assertEqual(result['status'], 'success'); self.assertFalse(prompts); self.assertGreater(max(reused or [0]), 0)
                item = next(i for i in q.snapshot()[0]['items'].values() if i['entry_type'] == 'file')
                actual = os.fsdecode(bytes.fromhex(item['destination_path']['bytes_hex']))
                parent = os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex']))
                if push:
                    values = remote_json('import hashlib,json,pathlib,sys; print(json.dumps([hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(),(pathlib.Path(sys.argv[2])/sys.argv[3]).read_text()]))', actual,parent,name)
                    self.assertEqual(values, [hashlib.sha256(source.read_bytes()).hexdigest(), 'old good'])
                else:
                    self.assertEqual(pathlib.Path(actual).read_bytes(), source.read_bytes())
                    self.assertEqual((pathlib.Path(parent)/name).read_text(), 'old good')

    def test_automatic_disconnect_recovery_preserves_private_mapping_or_blocks_races_push_and_pull(self):
        sys.path.insert(0, str(ROOT/'tools'))
        from app_queue import PersistentQueue, execute_next, execute_queue
        for push in (True,False):
            for stop in ('resume','changed','cancel'):
                with self.subTest(push=push, stop=stop):
                    request,source,name = self.private_recovery_fixture(push,'-auto-'+stop)
                    request['options']['on_conflict'] = 'ask'; profile = None
                    for ep in [request['destination']] + [s['endpoint'] for s in request['sources']]:
                        if ep['kind'] == 'ssh': profile = ep.pop('connection'); ep['profile_id'] = 'saved-host'
                    path = self.local/('auto-'+str(push)+'-'+stop+'.json')
                    q = PersistentQueue(path); self.addCleanup(q.close)
                    q.enqueue(request,'transfer',reconnect_delays=(.1,.25,.5,1,2),recover_disconnected=True)
                    def lost(event,_):
                        if event['type'] == 'item_progress' and event.get('side') == 'destination' and int(event['bytes_processed']) >= 262144:
                            raise RuntimeError('lost transfer consumer')
                    with self.assertRaisesRegex(RuntimeError,'lost transfer consumer'):
                        execute_next(q,BINARY,profile_resolver=lambda _:profile,prompt_handler=lambda _:'yes',
                                     conflict_handler=lambda _:'keep_both',event_handler=lost)
                    row = q.snapshot()[0]; recovery_id = row['recovery_id']
                    item = next(i for i in row['items'].values() if i['entry_type'] == 'file')
                    actual = pathlib.Path(os.fsdecode(bytes.fromhex(item['destination_path']['bytes_hex'])))
                    self.assertEqual(row['state'],'needs_reconciliation'); self.assertTrue(row['reconnect']['recovery']['pending'])
                    if stop == 'changed':
                        if push: remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(b"foreign edit")',actual)
                        else: actual.write_bytes(b'foreign edit')
                    elif stop == 'cancel': q.cancel_recovery('transfer')
                    q.close(); q = PersistentQueue(path); self.addCleanup(q.close)
                    events,prompts = [],[]
                    def no_new_choice(event): prompts.append(event); return 'cancel'
                    results = list(execute_queue(q,BINARY,profile_resolver=lambda _:profile,prompt_handler=lambda _:'yes',
                                   conflict_handler=no_new_choice,event_handler=lambda event,_:events.append(event)))
                    row = q.snapshot()[0]
                    self.assertEqual(row['recovery_id'],recovery_id); self.assertFalse(prompts)
                    if stop == 'resume':
                        self.assertEqual([r['status'] for r in results],['success'],events)
                        self.assertEqual(row['state'],'success'); self.assertEqual(row['attempt'],2)
                        self.assertTrue(any(e['type'] == 'recovery_quiescent' for e in events))
                        self.assertTrue(any(e['type'] == 'recovery_verified' for e in events))
                        self.assertGreater(max([int(e.get('reused_bytes') or '0') for e in events if e['type'] == 'progress'] or [0]),0)
                        data = bytes.fromhex(remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_bytes().hex())',actual).strip()) if push else actual.read_bytes()
                        self.assertEqual(data,source.read_bytes())
                    else:
                        self.assertEqual(results,[],events); self.assertEqual(row['state'],'needs_reconciliation')
                        self.assertEqual(row['attempt'],1); self.assertIsNone(row['result'])
                        self.assertFalse(row['reconnect']['recovery']['pending'])
                        if stop == 'changed':
                            data = bytes.fromhex(remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_bytes().hex())',actual).strip()) if push else actual.read_bytes()
                            self.assertEqual(data,b'foreign edit')
                        else:
                            self.assertEqual(row['stop_requested'],'cancel'); self.assertFalse(events)
                    self.assertIsNone(q.claim()); self.assertNotIn(IDENTITY,path.read_text())

    def test_automatic_recovery_reconciles_after_killed_ssh_transport_push_and_pull(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from app_queue import PersistentQueue, execute_next, execute_queue
        for push in (True,False):
            with self.subTest(push=push):
                request,source,name = self.private_recovery_fixture(push,'-wire-loss')
                request['options']['on_conflict'] = 'ask'; profile = None
                for ep in [request['destination']] + [s['endpoint'] for s in request['sources']]:
                    if ep['kind'] == 'ssh': profile = ep.pop('connection'); ep['profile_id'] = 'saved-host'
                q = PersistentQueue(self.local/('wire-loss-'+str(push)+'.json')); self.addCleanup(q.close)
                q.enqueue(request,'transfer',reconnect_delays=(.1,.25,.5,1,2),recover_disconnected=True)
                killed = []; initial = []
                def disconnect(event,client):
                    initial.append(event)
                    if not killed and event['type'] == 'item_progress' and event.get('side') == 'destination' and int(event['bytes_processed']) >= 262144:
                        rows = [row.split(None,2) for row in subprocess.check_output(['ps','-axo','pid=,ppid=,comm='],text=True).splitlines()]
                        descendants = {client.process.pid}
                        while True:
                            added = {int(pid) for pid,parent,_ in rows if int(parent) in descendants} - descendants
                            if not added: break
                            descendants.update(added)
                        candidates = [int(pid) for pid,_,comm in rows if int(pid) in descendants and pathlib.Path(comm).name == 'ssh']
                        self.assertEqual(len(candidates),1,rows)
                        os.kill(candidates[0],signal.SIGKILL); killed.extend(candidates)
                first = execute_next(q,BINARY,profile_resolver=lambda _:profile,prompt_handler=lambda _:'yes',
                                     conflict_handler=lambda _:'keep_both',event_handler=disconnect)
                self.assertTrue(killed); self.assertIn(first['status'],('failure','partial_failure'),initial)
                row = q.snapshot()[0]; self.assertEqual(row['state'],'needs_reconciliation',initial)
                self.assertTrue(row['reconnect']['recovery']['pending'],initial)
                self.assertEqual(row['reconnect']['history'][0]['status'],first['status'])
                events = []
                results = list(execute_queue(q,BINARY,profile_resolver=lambda _:profile,prompt_handler=lambda _:'yes',
                               conflict_handler=lambda _:'cancel',event_handler=lambda event,_:events.append(event)))
                self.assertEqual([r['status'] for r in results],['success'],events)
                self.assertTrue(any(e['type'] == 'recovery_verified' for e in events))
                self.assertGreater(max([int(e.get('reused_bytes') or '0') for e in events if e['type'] == 'progress'] or [0]),0)
                item = next(i for i in q.snapshot()[0]['items'].values() if i['entry_type'] == 'file')
                actual = pathlib.Path(os.fsdecode(bytes.fromhex(item['destination_path']['bytes_hex'])))
                data = bytes.fromhex(remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_bytes().hex())',actual).strip()) if push else actual.read_bytes()
                self.assertEqual(data,source.read_bytes()); self.assertEqual(q.snapshot()[0]['state'],'success')

    def test_reserved_identity_recovers_when_every_initial_receipt_is_lost_push_and_pull(self):
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'tools'))
        from app_client import AppClient
        from app_queue import PersistentQueue, execute_next, execute_queue
        for push in (True,False):
            with self.subTest(push=push):
                request,source,name = self.private_recovery_fixture(push,'-receipt-loss')
                request['options']['on_conflict'] = 'ask'; profile = None
                for ep in [request['destination']] + [s['endpoint'] for s in request['sources']]:
                    if ep['kind'] == 'ssh': profile = ep.pop('connection'); ep['profile_id'] = 'saved-host'
                path = self.local/('receipt-loss-'+str(push)+'.json')
                q = PersistentQueue(path); self.addCleanup(q.close)
                q.enqueue(request,'transfer',reconnect_delays=(.1,.25,.5,1,2),recover_disconnected=True)
                sent,hidden = [],[]
                class LostReceipts(AppClient):
                    def run(inner, request, **options):
                        sent.append(request)
                        persisted = json.loads(path.read_text())['jobs'][0]
                        self.assertEqual(persisted['recovery_id'],request['recovery_id'])
                        for event in super().run(request, **options):
                            hidden.append(event)
                            if event['type'] == 'item_progress' and event.get('side') == 'destination' and int(event['bytes_processed']) >= 262144:
                                raise RuntimeError('all initial receipts lost')
                        self.fail('no receiver prefix before receipt loss')
                        yield  # Keep the SDK generator interface while suppressing receipts.
                with patch('app_client.AppClient',LostReceipts), self.assertRaisesRegex(RuntimeError,'all initial receipts lost'):
                    execute_next(q,BINARY,profile_resolver=lambda _:profile,prompt_handler=lambda _:'yes',conflict_handler=lambda _:'keep_both')
                row = q.snapshot()[0]; recovery = row['recovery_id']
                self.assertEqual(row['items'],{}); self.assertFalse(row.get('actors'))
                self.assertEqual(row['state'],'needs_reconciliation'); self.assertTrue(row['reconnect']['recovery']['pending'])
                self.assertEqual(sent[0]['recovery_id'],recovery)
                self.assertTrue(any(e['type'] == 'recovery_created' and e['recovery_id'] == recovery for e in hidden))
                q.close(); q = PersistentQueue(path); self.addCleanup(q.close)
                events = []
                results = list(execute_queue(q,BINARY,profile_resolver=lambda _:profile,prompt_handler=lambda _:'yes',
                               conflict_handler=lambda _:'cancel',event_handler=lambda event,_:events.append(event)))
                self.assertEqual([r['status'] for r in results],['success'],events)
                self.assertTrue(any(e['type'] == 'recovery_quiescent' for e in events))
                self.assertTrue(any(e['type'] == 'recovery_verified' for e in events))
                self.assertGreater(max([int(e.get('reused_bytes') or '0') for e in events if e['type'] == 'progress'] or [0]),0)
                row = q.snapshot()[0]; self.assertEqual(row['recovery_id'],recovery)
                item = next(i for i in row['items'].values() if i['entry_type'] == 'file')
                actual = pathlib.Path(os.fsdecode(bytes.fromhex(item['destination_path']['bytes_hex'])))
                data = bytes.fromhex(remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_bytes().hex())',actual).strip()) if push else actual.read_bytes()
                self.assertEqual(data,source.read_bytes()); self.assertEqual(row['state'],'success')

    def test_queue_reconciles_crash_after_publication_and_blocks_foreign_edits_push_and_pull(self):
        from concurrent.futures import ThreadPoolExecutor
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'tools'))
        from app_client import AppClient
        from app_queue import PersistentQueue, execute_next, execute_queue
        for push in (True,False):
            for changed in (False,True):
                with self.subTest(push=push,changed=changed):
                    suffix = '-publication-'+str(changed)
                    request,source,name = self.private_recovery_fixture(push,suffix)
                    request['options']['bandwidth_bytes_per_second'] = '0'
                    destination = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                    marker = (self.root if push else self.local)/(self.local.name+'-published-'+str(push)+'-'+str(changed))
                    settings = dict(XSYNC_FAULT_PUBLICATION_NOTIFY=str(marker),XSYNC_FAULT_PUBLICATION_HOLD='1')
                    env = None; helper = None
                    if push:
                        helper = self.fault_helper(destination,**settings)
                        request['destination']['connection']['helper_path'] = helper
                    else:
                        env = self.local_fault_env(destination,**settings)
                        launcher = self.local/('publication-engine-'+str(changed))
                        selected_env = {k:v for k,v in env.items() if k.startswith('XSYNC_FAULT_') or k in ('DYLD_INSERT_LIBRARIES','LD_PRELOAD')}
                        launcher.write_text('#!/bin/sh\nexec env '+shlex.join([k+'='+v for k,v in selected_env.items()])+' '+shlex.quote(str(BINARY))+' "$@"\n')
                        launcher.chmod(0o700)
                    profile = None
                    for ep in [request['destination']] + [s['endpoint'] for s in request['sources']]:
                        if ep['kind'] == 'ssh': profile = ep.pop('connection'); ep['profile_id'] = 'saved-host'
                    path = self.local/('publication-'+str(push)+'-'+str(changed)+'.json')
                    q = PersistentQueue(path); self.addCleanup(q.close)
                    q.enqueue(request,'transfer',reconnect_delays=(.1,.25,.5,1,2),recover_disconnected=True)
                    launched = []
                    def capture(binary):
                        client = AppClient(binary if env is None else launcher); launched.append(client); return client
                    with patch('app_client.AppClient',capture), ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(execute_next,q,BINARY,profile_resolver=lambda _:profile,prompt_handler=lambda _:'yes')
                        deadline = time.monotonic()+15
                        while not (remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))',marker) if push else marker.exists()):
                            if future.done(): self.fail('copy ended before publication checkpoint: '+repr(future.result()))
                            self.assertLess(time.monotonic(),deadline); time.sleep(.01)
                        self.assertEqual(len(launched),1)
                        os.killpg(launched[0].process.pid,signal.SIGKILL)
                        if push: remote_code('import pathlib,sys,os,signal; os.kill(int(pathlib.Path(sys.argv[1]).read_text()),signal.SIGKILL)',marker)
                        with self.assertRaises(RuntimeError): future.result(timeout=10)
                    recovery = q.snapshot()[0]['recovery_id']; store = destination/'.xsync-app-partials'/recovery
                    if push:
                        rows = remote_json('import pathlib,sys,json; print(json.dumps([json.loads(p.read_text()) for p in pathlib.Path(sys.argv[1]).glob("*.json") if not p.name.startswith(".")]))',store)
                        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])',helper,'#!/bin/sh\nexec /usr/local/bin/xs "$@"\n')
                    else: rows = [json.loads(p.read_text()) for p in store.glob('*.json') if not p.name.startswith('.')]
                    self.assertTrue(any(row['state'] == 'publishing' for row in rows),rows)
                    actual = destination/name
                    if changed:
                        if push: remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(b"foreign edit")',actual)
                        else: actual.write_bytes(b'foreign edit')
                    q.close(); q = PersistentQueue(path); self.addCleanup(q.close)
                    events = []
                    results = list(execute_queue(q,BINARY,profile_resolver=lambda _:profile,prompt_handler=lambda _:'yes',event_handler=lambda event,_:events.append(event)))
                    row = q.snapshot()[0]; self.assertEqual(row['recovery_id'],recovery)
                    if changed:
                        self.assertEqual(results,[],events); self.assertEqual(row['state'],'needs_reconciliation')
                        self.assertEqual(row['attempt'],1); self.assertFalse(row['reconnect']['recovery']['pending'])
                    else:
                        self.assertEqual([r['status'] for r in results],['success'],events)
                        self.assertEqual(row['state'],'success'); self.assertTrue(any(e['type'] == 'recovery_verified' for e in events))
                    data = bytes.fromhex(remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_bytes().hex())',actual).strip()) if push else actual.read_bytes()
                    self.assertEqual(data,b'foreign edit' if changed else source.read_bytes())

    def private_recovery_state(self, destination, recovery_id):
        deadline = time.monotonic() + 8
        while True:
            c, result = self.run_job('recovery_state', endpoint=destination, recovery_id=recovery_id)
            if result['status'] == 'success': return c, next(e for e in c.events if e['type'] == 'recovery_state')
            # A cancelled SSH helper may still be completing bounded teardown.
            self.assertIn('conflict', self.errors(c), c.events)
            self.assertLess(time.monotonic(), deadline, c.events); time.sleep(.2)

    def resume_private_copy(self, request, recovery_id):
        import copy
        request = copy.deepcopy(request); request.update(op='resume', recovery_id=recovery_id)
        request['options'].update(jobs='2', bandwidth_bytes_per_second='0')
        return self.run_job('resume', sources=request['sources'], destination=request['destination'],
                            options=request['options'], recovery_id=recovery_id)

    def private_target_bytes(self, destination, name):
        root = pathlib.Path(os.fsdecode(bytes.fromhex(destination['path']['bytes_hex'])))
        if destination['kind'] == 'local': return (root / name).read_bytes()
        return bytes.fromhex(remote_code('import pathlib,sys; print((pathlib.Path(sys.argv[1])/sys.argv[2]).read_bytes().hex())',root,name).strip())

    def test_private_recovery_cancel_resume_push_and_pull(self):
        for push in (True,False):
            with self.subTest(push=push):
                request, source, name = self.private_recovery_fixture(push)
                recovery_id = self.interrupt_private_copy(request)
                self.assertEqual(self.private_target_bytes(request['destination'],name), b'old good')
                c, state = self.private_recovery_state(request['destination'],recovery_id)
                entries = [e for e in c.events if e['type'] == 'recovery_entry']
                parts = [e for e in entries if bytes.fromhex(e['name']['bytes_hex']).endswith(b'.part')]
                self.assertEqual(len(parts),1,c.events); kept = int(parts[0]['revision']['size'])
                self.assertGreater(kept,0); self.assertLess(kept,source.stat().st_size)
                serialized = json.dumps(state['binding'])
                for credential in (str(self.key),str(self.known),str(self.config),PASSPHRASE,PASSWORD): self.assertNotIn(credential,serialized)
                c, result = self.resume_private_copy(request,recovery_id)
                self.assertEqual(result['status'],'success',c.events)
                destination_root = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                assert_scope(self,c.events,destination_root,'ssh' if push else 'local')
                item = next(e for e in c.events if e['type'] == 'item_result' and e['entry_type'] == 'file')
                hint = next(e for e in c.events if e['type'] == 'invalidate' and e.get('reason') == 'transfer_item' and e['item_id'] == item['item_id'])
                self.assertEqual(hint['path'],item['destination_path']); self.assertEqual(hint['endpoint'],'ssh' if push else 'local')
                self.assertEqual(self.private_target_bytes(request['destination'],name),source.read_bytes())
                self.assertEqual(int(next(e for e in c.events if e['type']=='summary')['reused_bytes']),kept)
                _, state = self.private_recovery_state(request['destination'],recovery_id)
                self.assertEqual(state['state'],'completed')
                c, result = self.run_job('cleanup_partials',endpoint=request['destination'],recovery_id=recovery_id,
                                         expected_job_revision=state['job_revision'])
                self.assertEqual(result['status'],'success',c.events)
                self.assertEqual(self.private_target_bytes(request['destination'],name),source.read_bytes())

    def directory_recovery_fixture(self, push, suffix=''):
        local = self.local / ('tree-' + str(push) + suffix); local.mkdir()
        remote = self.root / (self.local.name + '-tree-' + str(push) + suffix)
        payload = b'nested recovery data' * 209716
        if push:
            (local / 'nested' / 'deep').mkdir(parents=True)
            (local / 'nested' / 'deep' / 'large').write_bytes(payload)
            (local / 'nested' / 'link').symlink_to('deep/large')
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
            sources = [{'endpoint': local_endpoint(local), 'mode': 'contents'}]
            destination = self.endpoint(remote)
        else:
            remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/"nested"/"deep").mkdir(parents=True); '
                        '(p/"nested"/"deep"/"large").write_bytes(b"nested recovery data"*209716); '
                        '(p/"nested"/"link").symlink_to("deep/large")', remote)
            sources = [{'endpoint': self.endpoint(remote), 'mode': 'contents'}]
            destination = local_endpoint(local)
        return {'id': 'ssh', 'op': 'copy', 'sources': sources, 'destination': destination,
                'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True,
                            'retain_partials': True, 'jobs': '1', 'bandwidth_bytes_per_second': '524288'}}, payload

    def test_private_nested_pause_receipts_and_prefix_reuse_push_and_pull(self):
        for push in (True, False):
            with self.subTest(push=push):
                request, payload = self.directory_recovery_fixture(push)
                c, result, recovery_id, _ = self.pause_private_copy(request)
                self.assertEqual(result['status'], 'paused', c.events)
                c, _ = self.private_recovery_state(request['destination'], recovery_id)
                rows = [e['record'] for e in c.events if e['type'] == 'recovery_entry' and e['record']]
                directories = [r for r in rows if r.get('entry_type') == 'directory']
                self.assertEqual(len(directories), 3, rows)
                self.assertTrue(all(r['state'] in ('entry_published', 'entry_checkpoint') for r in directories), rows)
                c, result = self.resume_private_copy(request, recovery_id)
                self.assertEqual(result['status'], 'success', c.events)
                self.assertGreater(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), 0)
                self.assertEqual(self.private_target_bytes(request['destination'], 'nested/deep/large'), payload)

    def test_private_store_collision_is_rejected_before_remote_or_local_vault_mutation(self):
        for push in (True, False):
            with self.subTest(push=push):
                request, _ = self.directory_recovery_fixture(push)
                source = pathlib.Path(os.fsdecode(bytes.fromhex(request['sources'][0]['endpoint']['path']['bytes_hex'])))
                target = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                code = ('import pathlib,sys; p=pathlib.Path(sys.argv[1])/".xsync-app-partials"; p.mkdir(mode=0o700); '
                        '(p/".owner").write_bytes(b"foreign owner"); (p/"foreign child").write_bytes(b"foreign data")')
                if push: subprocess.run([sys.executable, '-c', code, str(source)], check=True)
                else: remote_code(code, source)
                request['options']['bandwidth_bytes_per_second'] = '0'
                c, result = self.run_job('copy', sources=request['sources'], destination=request['destination'], options=request['options'])
                self.assertNotEqual(result['status'], 'success', c.events)
                self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_reserved_destination' for e in c.events), c.events)
                code = ('import pathlib,sys,json; p=pathlib.Path(sys.argv[1])/".xsync-app-partials"; '
                        'print(json.dumps([(p/".owner").read_text(), (p/"foreign child").exists()]))')
                actual = remote_json(code, target) if push else json.loads(subprocess.check_output([sys.executable, '-c', code, str(target)], text=True))
                self.assertEqual(actual, ['xsync app private partials 1\n', False])

    def test_private_completed_directory_and_link_edits_block_ssh_resume(self):
        for push in (True, False):
            for kind in ('directory', 'symlink'):
                with self.subTest(push=push, kind=kind):
                    request, payload = self.directory_recovery_fixture(push, kind)
                    request['options']['bandwidth_bytes_per_second'] = '0'
                    c, result = self.run_job('copy', sources=request['sources'], destination=request['destination'], options=request['options'])
                    self.assertEqual(result['status'], 'success', c.events)
                    recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
                    target = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                    code = ('import pathlib,sys; p=pathlib.Path(sys.argv[1]); '
                            'p.chmod(0o711)' if kind == 'directory' else
                            'import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.unlink(); p.symlink_to("independent target")')
                    path = target / 'nested' / ('deep' if kind == 'directory' else 'link')
                    if push: remote_code(code, path)
                    else: subprocess.run([sys.executable, '-c', code, str(path)], check=True)
                    c, result = self.resume_private_copy(request, recovery_id)
                    self.assertNotEqual(result['status'], 'success', c.events)
                    self.assertTrue(any(e['type'] == 'error' and e.get('operation') == 'recovery_destination_changed' for e in c.events), c.events)
                    self.assertEqual(self.private_target_bytes(request['destination'], 'nested/deep/large'), payload)
                    if not push:
                        if kind == 'directory': self.assertEqual(path.stat().st_mode & 0o777, 0o711)
                        else: self.assertEqual(os.readlink(path), 'independent target')

    def test_private_mapped_selection_type_changes_push_and_pull(self):
        for push in (True, False):
            with self.subTest(push=push):
                request, source, name = self.private_recovery_fixture(push)
                recovery_id = self.interrupt_private_copy(request)
                self.private_recovery_state(request['destination'], recovery_id)
                source_path = pathlib.Path(os.fsdecode(bytes.fromhex(request['sources'][0]['endpoint']['path']['bytes_hex'])))
                target = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex']))) / name
                for transition in ('link', 'directory', 'file'):
                    code = ('import pathlib,sys; p=pathlib.Path(sys.argv[1]); '
                            '(p.rmdir() if p.is_dir() and not p.is_symlink() else p.unlink()); ' +
                            {'link': 'p.symlink_to("literal target")', 'directory': 'p.mkdir()', 'file': 'p.write_bytes(b"new regular data")'}[transition])
                    if push: subprocess.run([sys.executable, '-c', code, str(source_path)], check=True)
                    else: remote_code(code, source_path)
                    c, result = self.resume_private_copy(request, recovery_id)
                    self.assertEqual(result['status'], 'success', c.events)
                    code = ('import pathlib,sys,json,os; p=pathlib.Path(sys.argv[1]); print(json.dumps(' +
                            {'link': 'os.readlink(p)', 'directory': 'p.is_dir()', 'file': 'p.read_bytes().decode()'}[transition] + '))')
                    actual = remote_json(code, target) if push else json.loads(subprocess.check_output([sys.executable, '-c', code, str(target)], text=True))
                    self.assertEqual(actual, {'link': 'literal target', 'directory': True, 'file': 'new regular data'}[transition])

    def pause_private_copy(self, request, mutate_actor=None, conflict=None):
        c = self.client(); c.send(request); recovery_id = None; actor = None
        while True:
            event = c.read(15)
            if event['type'] == 'auth_prompt': self.response(c,event,'yes')
            if event['type'] == 'conflict' and conflict: conflict(c,event)
            if event['type'] == 'recovery_created': recovery_id = event['recovery_id']
            if event['type'] == 'recovery_actor': actor = event
            if event['type'] == 'item_progress' and event.get('side') == 'destination' and int(event['bytes_processed']) >= 262144: break
            self.assertNotEqual(event['type'],'result',c.events)
        self.assertIsNotNone(recovery_id,c.events); self.assertIsNotNone(actor,c.events)
        if mutate_actor: mutate_actor(actor)
        c.send({'id': 'pause', 'op': 'pause', 'job_id': 'ssh'})
        return c, c.finish(35), recovery_id, actor

    def test_private_interactive_keep_both_pause_resume_and_completed_reuse_push_and_pull(self):
        for push in (True, False):
            with self.subTest(push=push):
                request, source, name = self.private_recovery_fixture(push)
                request['options']['on_conflict'] = 'ask'
                c, result, recovery_id, _ = self.pause_private_copy(request, conflict=lambda client, e: self.conflict_reply(client, e, 'keep_both'))
                self.assertEqual(result['status'], 'paused', c.events)
                c, result = self.resume_private_copy(request, recovery_id)
                self.assertEqual(result['status'], 'success', c.events)
                self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
                replay = next(e for e in c.events if e['type'] == 'conflict_replayed')
                self.assertEqual(replay['endpoint'], 'ssh' if push else 'local')
                self.assertEqual(replay['recovery_id'], recovery_id)
                self.assertEqual(self.private_target_bytes(request['destination'], name), b'old good')
                self.assertEqual(self.private_target_bytes(request['destination'], name + ' (copy 1)'), source.read_bytes())
                destination_root = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                assert_scope(self,c.events,destination_root,'ssh' if push else 'local')
                hints = [e for e in c.events if e['type'] == 'invalidate' and e.get('reason') == 'transfer_item']
                self.assertTrue(any(e['path']['bytes_hex'] == os.fsencode(destination_root/(name+' (copy 1)')).hex() for e in hints),c.events)
                self.assertGreater(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), 0)
                source.write_bytes(source.read_bytes() + b'changed tail')
                if not push:
                    actual = pathlib.Path(os.fsdecode(bytes.fromhex(request['sources'][0]['endpoint']['path']['bytes_hex'])))
                    remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_bytes(p.read_bytes()+b"changed tail")', actual)
                c, result = self.resume_private_copy(request, recovery_id)
                self.assertEqual(result['status'], 'success', c.events)
                self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
                self.assertEqual(self.private_target_bytes(request['destination'], name + ' (copy 1)'), source.read_bytes())

    def test_private_interactive_directory_mapping_and_scoped_policy_survive_ssh_resume(self):
        for push in (True, False):
            with self.subTest(push=push):
                request, payload = self.directory_recovery_fixture(push)
                target = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                code = ('import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/"nested").mkdir(); '
                        '(p/"nested"/"sentinel").write_bytes(b"old nested"); '
                        '(p/"future").mkdir(); (p/"future"/"sentinel").write_bytes(b"old future")')
                if push: remote_code(code, target)
                else: subprocess.run([sys.executable, '-c', code, str(target)], check=True)
                request['options']['on_conflict'] = 'ask'
                c, result, recovery_id, _ = self.pause_private_copy(request, conflict=lambda client, e: self.conflict_reply(client, e, 'keep_both', scope='job'))
                self.assertEqual(result['status'], 'paused', c.events)
                source = pathlib.Path(os.fsdecode(bytes.fromhex(request['sources'][0]['endpoint']['path']['bytes_hex'])))
                code = ('import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/"future").mkdir(); '
                        '(p/"future"/"child").write_bytes(b"new future")')
                if push: subprocess.run([sys.executable, '-c', code, str(source)], check=True)
                else: remote_code(code, source)
                c, result = self.resume_private_copy(request, recovery_id)
                self.assertEqual(result['status'], 'success', c.events)
                self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
                self.assertEqual(self.private_target_bytes(request['destination'], 'nested/sentinel'), b'old nested')
                self.assertEqual(self.private_target_bytes(request['destination'], 'nested (copy 1)/deep/large'), payload)
                self.assertEqual(self.private_target_bytes(request['destination'], 'future/sentinel'), b'old future')
                self.assertEqual(self.private_target_bytes(request['destination'], 'future (copy 1)/child'), b'new future')
                state_client, state = self.private_recovery_state(request['destination'], recovery_id)
                self.assertEqual(state['conflict_policies'][0]['action'], 'keep_both')
                choices = [e['record'] for e in state_client.events if e['type'] == 'recovery_entry' and e.get('record', {}).get('record_kind') == 'conflict_choice']
                self.assertTrue(any(r['decision'] == 'keep_both' for r in choices), state_client.events)

    def test_private_interactive_recovery_requires_exact_peer_choice_capability(self):
        for capability in (None, True, 'old'):
            for push in (True, False):
                with self.subTest(capability=capability, push=push):
                    request, _, _ = self.private_recovery_fixture(push, str(capability))
                    request['options']['on_conflict'] = 'ask'
                    remote_endpoint = request['destination'] if push else request['sources'][0]['endpoint']
                    root = pathlib.Path(os.fsdecode(bytes.fromhex(remote_endpoint['path']['bytes_hex']))).parent if not push else pathlib.Path(os.fsdecode(bytes.fromhex(remote_endpoint['path']['bytes_hex'])))
                    helper, marker = root / 'old-choice-helper', root / 'unexpected-choice-request'
                    change = 'caps.pop("recovery_conflicts",None)' if capability is None else 'caps["recovery_conflicts"]='+repr(capability)
                    script = '\n'.join(['#!/usr/bin/python3','import json,sys,pathlib,subprocess',
                        'p=subprocess.Popen(["/usr/local/bin/xs","--app"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)',
                        'p.stdin.write(sys.stdin.buffer.readline()); p.stdin.flush()',
                        'caps=json.loads(p.stdout.readline()); '+change, 'print(json.dumps(caps),flush=True)',
                        'request=sys.stdin.buffer.readline()', 'if request: pathlib.Path('+repr(str(marker))+').touch()',
                        'p.stdin.close(); p.wait()', ''])
                    remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o700)', helper, script)
                    remote_endpoint['connection']['helper_path'] = str(helper)
                    c, result = self.run_job('copy', sources=request['sources'], destination=request['destination'], options=request['options'])
                    self.assertNotEqual(result['status'], 'success', c.events); self.assertIn('unsupported_feature', self.errors(c))
                    self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker))

    def test_recovery_verification_requires_exact_receiver_capability_before_request(self):
        for capability in (None, True, 'old', 'missing-bridge'):
            with self.subTest(capability=capability):
                request, _, _ = self.private_recovery_fixture(True, '-verify-'+str(capability))
                request['options']['bandwidth_bytes_per_second'] = '0'
                c, result = self.run_job('copy', sources=request['sources'], destination=request['destination'], options=request['options'])
                self.assertEqual(result['status'], 'success', c.events)
                recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
                _, state = self.private_recovery_state(request['destination'], recovery_id)
                root = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                helper, marker = root/'old-verify-helper', root/'unexpected-verification-request'
                change = 'caps.pop("recovery_verification",None)' if capability is None else 'caps["recovery_verification"]='+repr(capability)
                if capability == 'missing-bridge': change = 'caps["transfer_bridge"]=None'
                script = '\n'.join(['#!/usr/bin/python3','import json,sys,pathlib,subprocess',
                    'p=subprocess.Popen(["/usr/local/bin/xs","--app"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)',
                    'p.stdin.write(sys.stdin.buffer.readline()); p.stdin.flush()',
                    'caps=json.loads(p.stdout.readline()); '+change, 'print(json.dumps(caps),flush=True)',
                    'request=sys.stdin.buffer.readline()', 'if request: pathlib.Path('+repr(str(marker))+').touch()',
                    'p.stdin.close(); p.wait()', ''])
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o700)', helper, script)
                request['destination']['connection']['helper_path'] = str(helper)
                c, result = self.run_job('verify_recovery', sources=request['sources'], destination=request['destination'], options=request['options'],
                                         recovery_id=recovery_id, expected_job_revision=state['job_revision'], expected_inventory_token=state['inventory_token'])
                self.assertNotEqual(result['status'], 'success', c.events); self.assertIn('unsupported_feature', self.errors(c), c.events)
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker))

    def test_private_interactive_scoped_skip_is_restored_for_new_ssh_conflicts(self):
        for push in (True, False):
            with self.subTest(push=push):
                request, payload = self.directory_recovery_fixture(push)
                source = pathlib.Path(os.fsdecode(bytes.fromhex(request['sources'][0]['endpoint']['path']['bytes_hex'])))
                target = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                code = 'import pathlib,sys; (pathlib.Path(sys.argv[1])/"aaa").write_bytes(b"new aaa")'
                if push: subprocess.run([sys.executable, '-c', code, str(source)], check=True)
                else: remote_code(code, source)
                code = ('import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/"aaa").write_bytes(b"old aaa"); '
                        '(p/"future").write_bytes(b"old future")')
                if push: remote_code(code, target)
                else: subprocess.run([sys.executable, '-c', code, str(target)], check=True)
                request['options']['on_conflict'] = 'ask'
                c, result, recovery_id, _ = self.pause_private_copy(request, conflict=lambda client, e: self.conflict_reply(client, e, 'skip', scope='job'))
                self.assertEqual(result['status'], 'paused', c.events)
                code = 'import pathlib,sys; (pathlib.Path(sys.argv[1])/"future").write_bytes(b"new future")'
                if push: subprocess.run([sys.executable, '-c', code, str(source)], check=True)
                else: remote_code(code, source)
                c, result = self.resume_private_copy(request, recovery_id)
                self.assertEqual(result['status'], 'success', c.events)
                self.assertFalse(any(e['type'] == 'conflict' for e in c.events), c.events)
                self.assertEqual(self.private_target_bytes(request['destination'], 'aaa'), b'old aaa')
                self.assertEqual(self.private_target_bytes(request['destination'], 'future'), b'old future')
                self.assertEqual(self.private_target_bytes(request['destination'], 'nested/deep/large'), payload)

    def test_private_interactive_pause_of_unapproved_ssh_conflict_requires_new_prompt(self):
        for push in (True, False):
            with self.subTest(push=push):
                request, source, name = self.private_recovery_fixture(push)
                request['options']['on_conflict'] = 'ask'
                c = self.client(); c.send(request)
                while True:
                    event = c.read(15)
                    if event['type'] == 'auth_prompt': self.response(c, event, 'yes')
                    if event['type'] == 'recovery_created': recovery_id = event['recovery_id']
                    if event['type'] == 'conflict': original = event; break
                    self.assertNotEqual(event['type'], 'result', c.events)
                c.send({'id': 'pause', 'op': 'pause', 'job_id': 'ssh'})
                self.assertEqual(c.finish(35)['status'], 'paused', c.events)
                self.assertEqual(self.private_target_bytes(request['destination'], name), b'old good')
                resumed = dict(request, op='resume', recovery_id=recovery_id,
                               options=dict(request['options'], bandwidth_bytes_per_second='0'))
                c = self.client(); c.send(resumed); prompts = []
                result = self.finish_conflicts(c, lambda e: (prompts.append(e), self.conflict_reply(c, e, 'replace')))
                self.assertEqual(result['status'], 'success', c.events)
                self.assertEqual(len(prompts), 1, prompts); self.assertNotEqual(prompts[0]['conflict_id'], original['conflict_id'])
                self.assertEqual(self.private_target_bytes(request['destination'], name), source.read_bytes())

    def test_private_pause_and_resume_prove_both_ssh_actors_stopped(self):
        for push in (True,False):
            with self.subTest(push=push):
                request, source, name = self.private_recovery_fixture(push)
                c, result, recovery_id, actor = self.pause_private_copy(request)
                self.assertEqual(result['status'],'paused',c.events)
                self.assertEqual(result['cleanup'],'finished')
                paused = next(e for e in c.events if e['type']=='paused')
                self.assertTrue(paused['receiver_quiescent']); self.assertTrue(paused['peer_quiescent'])
                self.assertEqual(self.private_target_bytes(request['destination'],name),b'old good')
                _, state = self.private_recovery_state(request['destination'],recovery_id)
                self.assertEqual(state['state'],'paused')
                self.assertEqual(len(state['actors']),1)
                self.assertEqual(state['actors'][0]['attempt_id'],actor['attempt_id'])
                self.assertEqual(state['actors'][0]['endpoint'],'ssh')
                self.assertTrue(state['actors'][0]['cleaned'])
                path = os.fsdecode(bytes.fromhex(actor['actor_path']['bytes_hex']))
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))',path))
                c, result = self.resume_private_copy(request,recovery_id)
                self.assertEqual(result['status'],'success',c.events)
                self.assertGreater(int(next(e for e in c.events if e['type']=='summary')['reused_bytes']),0)
                self.assertEqual(self.private_target_bytes(request['destination'],name),source.read_bytes())
                _,state=self.private_recovery_state(request['destination'],recovery_id)
                self.assertEqual(len(state['actors']),2)
                self.assertTrue(state['actors'][0]['cleaned'])
                latest=state['actors'][1]
                self.assertNotEqual(latest['attempt_id'],actor['attempt_id'])
                self.assertNotIn('cleaned',latest)
                sys.path.insert(0,str(ROOT/'tools'))
                from app_client import recovery_actor_request
                endpoint=request['destination'] if push else request['sources'][0]['endpoint']
                cleanup=recovery_actor_request('cleanup',endpoint,latest,cleanup=True)
                cleanup.pop('id'); cleanup.pop('op')
                check,result=self.run_job('recovery_quiescence',**cleanup)
                self.assertEqual(result['status'],'success',check.events)
                self.assertTrue(next(e for e in check.events if e['type']=='recovery_quiescent')['actor_cleaned'])

    def test_private_pause_rejects_missing_or_replaced_remote_actor_evidence(self):
        for replace in (True,False):
            with self.subTest(replace=replace):
                request, _, name = self.private_recovery_fixture(True,str(replace))
                def mutate(actor):
                    path = os.fsdecode(bytes.fromhex(actor['actor_path']['bytes_hex']))
                    remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/"lease").rename(p/"old"); '
                                'q=p/"lease"; q.write_bytes((p/"old").read_bytes()) if sys.argv[2]=="True" else None; '
                                'q.chmod(0o600) if q.exists() else None',path,replace)
                c, result, recovery_id, actor = self.pause_private_copy(request,mutate)
                self.assertEqual(result['status'],'failure',c.events)
                self.assertEqual(result['cleanup'],'unknown')
                self.assertFalse(any(e['type']=='paused' for e in c.events))
                self.assertEqual(self.private_target_bytes(request['destination'],name),b'old good')
                self.assertTrue(any(e['type']=='error' and e['endpoint']=='ssh' and e.get('operation') in ('recovery_actor_changed','recovery_actor_open') for e in c.events),c.events)
                # Test-owned hostile runtime scopes are removed after the helper's
                # bounded teardown; the production failure preserves them.
                self.private_recovery_state(request['destination'],recovery_id)
                remote_code('import shutil,sys; shutil.rmtree(sys.argv[1])',os.fsdecode(bytes.fromhex(actor['actor_path']['bytes_hex'])))

    def test_private_pause_requires_exact_peer_capability_and_leaves_copy_running(self):
        for capability in (None,True,'old'):
            with self.subTest(capability=capability):
                request, _, _ = self.private_recovery_fixture(True,str(capability))
                remote = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
                helper = remote/'old-pause-helper'
                script = '\n'.join(['#!/usr/bin/python3','import json,sys,subprocess,os,threading',
                  'p=subprocess.Popen(["/usr/local/bin/xs","--app"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)',
                  'p.stdin.write(sys.stdin.buffer.readline()); p.stdin.flush()',
                  'caps=json.loads(p.stdout.readline()); caps["pause_bridge"]='+repr(capability),
                  'print(json.dumps(caps),flush=True)',
                  'request=json.loads(sys.stdin.buffer.readline()); assert "attempt_id" not in request',
                  'p.stdin.write(json.dumps(request).encode()+b"\\n"); p.stdin.flush()',
                  'def send():',
                  ' while True:',
                  '  data=os.read(sys.stdin.fileno(),65536)',
                  '  if not data: p.stdin.close(); return',
                  '  p.stdin.write(data); p.stdin.flush()',
                  'threading.Thread(target=send,daemon=True).start()',
                  'while True:',
                  ' data=os.read(p.stdout.fileno(),65536)',
                  ' if not data: break',
                  ' sys.stdout.buffer.write(data); sys.stdout.buffer.flush()',
                  'p.wait()', ''])
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o700)',helper,script)
                request['destination']['connection']['helper_path'] = str(helper)
                c=self.client(); c.send(request)
                while True:
                    event=c.read(15)
                    if event['type']=='auth_prompt': self.response(c,event,'yes')
                    if event['type']=='item_progress' and event.get('side')=='destination' and int(event['bytes_processed'])>=262144: break
                    self.assertNotEqual(event['type'],'result',c.events)
                c.send({'id':'pause','op':'pause','job_id':'ssh'})
                while (event:=c.read())['type']!='pause_ack': self.assertNotEqual(event['type'],'result',c.events)
                self.assertFalse(event['accepted']); self.assertEqual(event['reason'],'peer_pause_unavailable')
                self.assertFalse(any(e['type']=='recovery_actor' for e in c.events))
                c.send({'id':'cancel','op':'cancel','job_id':'ssh'})
                self.assertEqual(c.finish()['status'],'cancellation',c.events)

    def test_private_recovery_bulk_resume_uses_bounded_file_descriptors(self):
        remote = self.root / (self.local.name + '-bulk')
        count = 600
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); '
                    '[(p/str(i)).write_bytes(f"{i:016d}".encode()*32769) for i in range(int(sys.argv[2]))]', remote, count)
        target = self.local / 'bulk'; target.mkdir()
        request = {'sources': [{'endpoint': self.endpoint(remote), 'mode': 'contents'}],
                   'destination': local_endpoint(target),
                   'options': {'on_conflict': 'replace', 'retain_partials': True, 'jobs': '1',
                               'preserve_times': True, 'preserve_permissions': True}}
        c, result = self.run_job('copy', **request)
        self.assertEqual(result['status'], 'success', c.events)
        recovery_id = next(e['recovery_id'] for e in c.events if e['type'] == 'recovery_created')
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); '
                    '[(p/str(i)).write_bytes(f"{i:016d}".encode()*32769+b"tail") for i in range(int(sys.argv[2]))]', remote, count)
        wrapper = ('import os,resource,sys; '
                   'resource.setrlimit(resource.RLIMIT_NOFILE,(128,resource.getrlimit(resource.RLIMIT_NOFILE)[1])); '
                   'os.execv(sys.argv[1],sys.argv[1:])')
        c = Client(prefix=(sys.executable, '-c', wrapper)); self.addCleanup(c.close)
        c.send({'id': 'ssh', 'op': 'resume', 'recovery_id': recovery_id, **request})
        result = c.finish(30)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual({p.name for p in target.iterdir() if p.name != '.xsync-app-partials'},
                         {str(i) for i in range(count)})
        for i in range(count): self.assertEqual((target/str(i)).read_bytes(), f'{i:016d}'.encode()*32769+b'tail')
        self.assertEqual(int(next(e for e in c.events if e['type'] == 'summary')['reused_bytes']), count*16*32769)

    def test_private_recovery_changed_destination_is_preserved_on_ssh_resume(self):
        request, source, name = self.private_recovery_fixture(True)
        recovery_id = self.interrupt_private_copy(request)
        self.private_recovery_state(request['destination'],recovery_id)
        root = os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex']))
        remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/sys.argv[2]).write_bytes(b"external edit")',root,name)
        c, result = self.resume_private_copy(request,recovery_id)
        self.assertNotEqual(result['status'],'success',c.events)
        self.assertTrue(any(e['type']=='error' and e.get('operation')=='recovery_destination_changed' and e['endpoint']=='ssh' for e in c.events),c.events)
        self.assertEqual(self.private_target_bytes(request['destination'],name),b'external edit')

    def test_private_recovery_corrupt_prefix_is_copied_fresh_over_ssh(self):
        request, source, name = self.private_recovery_fixture(True)
        recovery_id = self.interrupt_private_copy(request)
        self.private_recovery_state(request['destination'],recovery_id)
        root = os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex']))
        remote_code('import pathlib,sys; p=next((pathlib.Path(sys.argv[1])/".xsync-app-partials"/sys.argv[2]).glob("*.part")); f=p.open("r+b"); f.write(b"corrupt"); f.close()',root,recovery_id)
        c, result = self.resume_private_copy(request,recovery_id)
        self.assertEqual(result['status'],'success',c.events)
        self.assertEqual(self.private_target_bytes(request['destination'],name),source.read_bytes())
        self.assertEqual(next(e for e in c.events if e['type']=='summary')['reused_bytes'],'0')

    def test_private_recovery_shrunken_source_cannot_publish_old_remote_tail(self):
        request, source, name = self.private_recovery_fixture(True)
        recovery_id = self.interrupt_private_copy(request)
        self.private_recovery_state(request['destination'],recovery_id)
        source.write_bytes(source.read_bytes()[:8192])
        c, result = self.resume_private_copy(request,recovery_id)
        self.assertEqual(result['status'],'success',c.events)
        self.assertEqual(self.private_target_bytes(request['destination'],name),source.read_bytes())

    def test_private_recovery_corrupt_local_prefix_on_ssh_pull_is_copied_fresh(self):
        request, source, name = self.private_recovery_fixture(False)
        recovery_id = self.interrupt_private_copy(request)
        self.private_recovery_state(request['destination'],recovery_id)
        root = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
        part = next((root/'.xsync-app-partials'/recovery_id).glob('*.part'))
        with part.open('r+b') as f: f.write(b'corrupt')
        c, result = self.resume_private_copy(request,recovery_id)
        self.assertEqual(result['status'],'success',c.events)
        self.assertEqual(self.private_target_bytes(request['destination'],name),source.read_bytes())
        self.assertEqual(next(e for e in c.events if e['type']=='summary')['reused_bytes'],'0')

    def test_private_recovery_cleanup_over_ssh_rejects_stale_and_symlink_scopes(self):
        request, source, name = self.private_recovery_fixture(True)
        recovery_id = self.interrupt_private_copy(request)
        _, state = self.private_recovery_state(request['destination'],recovery_id)
        root = os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex']))
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1])/".xsync-app-partials"/sys.argv[2]; (p/"foreign").symlink_to(pathlib.Path(sys.argv[1])/sys.argv[3])',root,recovery_id,name)
        c, result = self.run_job('cleanup_partials',endpoint=request['destination'],recovery_id=recovery_id,expected_job_revision=state['job_revision'])
        self.assertNotEqual(result['status'],'success',c.events)
        self.assertTrue(any(e['type']=='error' and e.get('operation')=='recovery_cleanup_stale' for e in c.events),c.events)
        _, state = self.private_recovery_state(request['destination'],recovery_id)
        c, result = self.run_job('cleanup_partials',endpoint=request['destination'],recovery_id=recovery_id,expected_job_revision=state['job_revision'])
        self.assertNotEqual(result['status'],'success',c.events)
        self.assertTrue(any(e['type']=='error' and e.get('operation')=='recovery_cleanup_unexpected_entry' for e in c.events),c.events)
        self.assertEqual(self.private_target_bytes(request['destination'],name),b'old good')

    def test_private_recovery_metadata_finalization_failure_precedes_native_completion(self):
        request, source, name = self.private_recovery_fixture(True)
        root = pathlib.Path(os.fsdecode(bytes.fromhex(request['destination']['path']['bytes_hex'])))
        helper = self.fault_helper(root,XSYNC_FAULT_RECOVERY_FINALIZE_ERROR=str(errno.ENOSPC))
        request['destination']['connection']['helper_path'] = helper
        request['options']['bandwidth_bytes_per_second'] = '0'
        c, result = self.copy_job(request['sources'],request['destination'],**request['options'])
        self.assertEqual(result['status'],'partial_failure',c.events)
        self.assertTrue(any(e['type']=='error' and e.get('operation')=='recovery_write' and e.get('native_code')==str(errno.ENOSPC) and e['endpoint']=='ssh' for e in c.events),c.events)
        self.assertEqual(self.private_target_bytes(request['destination'],name),source.read_bytes())
        recovery_id = next(e['recovery_id'] for e in c.events if e['type']=='recovery_created')
        _, state = self.private_recovery_state(request['destination'],recovery_id)
        self.assertNotEqual(state['state'],'completed')

    def test_private_recovery_requires_exact_remote_capability_before_any_staging(self):
        remote = self.root / (self.local.name + '-unsupported'); remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()',remote)
        source = self.local / 'source'; source.write_bytes(b'incoming')
        remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/"source").write_bytes(b"incoming")',remote)
        helper, marker = remote / 'helper', remote / 'unexpected-request'
        for field, capability in ((field, value) for field in ('recovery_bridge', 'recovery_entries') for value in (None, True, 'old')):
            script = '\n'.join(['#!/usr/bin/python3','import json,sys,pathlib,subprocess',
              'p=subprocess.Popen(["/usr/local/bin/xs","--app"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)',
              'p.stdin.write(sys.stdin.buffer.readline()); p.stdin.flush()',
              'caps=json.loads(p.stdout.readline()); caps['+repr(field)+']='+repr(capability),
              'print(json.dumps(caps),flush=True)',
              'request=sys.stdin.buffer.readline()',
              'if request: pathlib.Path('+repr(str(marker))+').touch()',
              'p.stdin.close(); p.wait()', ''])
            remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)',helper,script)
            for push in (True,False):
                with self.subTest(field=field,capability=capability,push=push):
                    target = self.local / ('target-'+field+'-'+str(capability)+'-'+str(push)); target.mkdir()
                    sources = [{'endpoint': local_endpoint(source) if push else self.endpoint(remote/'source',helper_path=str(helper)), 'mode':'entry'}]
                    destination = self.endpoint(remote,helper_path=str(helper)) if push else local_endpoint(target)
                    c, result = self.copy_job(sources,destination,retain_partials=True)
                    self.assertNotEqual(result['status'],'success',c.events); self.assertIn('unsupported_feature',self.errors(c))
                    self.assertEqual(list(target.iterdir()),[])
                    self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/".xsync-app-partials").exists() or pathlib.Path(sys.argv[2]).exists()))',remote,marker))

    def local_fault_env(self, path, **settings):
        library = self.local / 'local-fault.so'
        if not library.exists():
            args = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                    '-fPIC', str(ROOT / 'tests/fault_io.cpp'), '-o', str(library)]
            if sys.platform != 'darwin': args += ['-ldl']
            subprocess.run(args, check=True, capture_output=True)
        return dict(os.environ, **{'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD': str(library),
                                  'XSYNC_FAULT_PATH': str(path.resolve()), **settings})

    def conflict_reply(self, c, e, decision='replace', **fields):
        c.send({'id': 'decision-' + e['conflict_id'], 'op': 'conflict_response', 'job_id': 'ssh',
                'conflict_id': e['conflict_id'], 'revision_token': e['revision_token'], 'decision': decision, **fields})

    def finish_conflicts(self, c, handler):
        while True:
            e = c.read(15)
            if e['type'] == 'auth_prompt': self.response(c, e, 'yes')
            if e['type'] == 'conflict': handler(e)
            if e['type'] == 'result':
                c.proc.wait(timeout=6)
                return e

    def test_interactive_keep_both_directory_file_and_symlink_in_both_directions(self):
        for push in (True, False):
            with self.subTest(push=push):
                source = self.local / ('interactive-source-' + str(push)); source.mkdir()
                dest = self.local / ('interactive-dest-' + str(push)); dest.mkdir()
                (source/'file').write_text('incoming'); (source/'folder').mkdir(); (source/'folder'/'child').write_text('nested'); (source/'link').symlink_to('literal:target')
                (dest/'file').write_text('old'); (dest/'folder').mkdir(); (dest/'folder'/'sentinel').write_text('keep'); (dest/'link').write_text('old link')
                remote = self.root / (self.local.name + '-interactive-' + str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text(sys.argv[2]); (p/"folder").mkdir(); (p/"folder"/sys.argv[3]).write_text(sys.argv[4]); (p/"link").write_text("old link") if sys.argv[5]=="dest" else (p/"link").symlink_to("literal:target")', remote, 'old' if push else 'incoming', 'sentinel' if push else 'child', 'keep' if push else 'nested', 'dest' if push else 'source')
                selection = {'endpoint': local_endpoint(source) if push else self.endpoint(remote, idle_timeout_seconds='1'), 'mode': 'contents'}
                destination = self.endpoint(remote, idle_timeout_seconds='1') if push else local_endpoint(dest)
                c = self.client(); c.send({'id': 'ssh', 'op': 'copy', 'sources': [selection], 'destination': destination,
                                          'options': {'on_conflict': 'ask', 'preserve_times': True, 'preserve_permissions': True}})
                waited = []
                def answer(e):
                    if not waited: time.sleep(1.5); waited.append(True)
                    self.assertEqual(e['endpoint'], 'ssh' if push else 'local')
                    self.conflict_reply(c, e, 'keep_both')
                self.assertEqual(self.finish_conflicts(c, answer)['status'], 'success', c.events)
                self.assertEqual({e['kind'] for e in c.events if e['type']=='conflict'}, {'file_file','directory_merge','symlink'})
                view = inventory(c.events, 'ssh')
                self.assertTrue(os.fsdecode(bytes.fromhex(view.items[b'folder/child'.hex()]['destination_path']['bytes_hex'])).endswith('/folder (copy 1)/child'))
                if push:
                    actual = remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([(p/"file").read_text(),(p/"file (copy 1)").read_text(),(p/"folder"/"sentinel").read_text(),(p/"folder (copy 1)"/"child").read_text(),str((p/"link (copy 1)").readlink())]))', remote)
                else: actual = [(dest/'file').read_text(),(dest/'file (copy 1)').read_text(),(dest/'folder'/'sentinel').read_text(),(dest/'folder (copy 1)'/'child').read_text(),str((dest/'link (copy 1)').readlink())]
                self.assertEqual(actual, ['old','incoming','keep','nested','literal:target'])

    def test_interactive_changed_revision_reprompts_on_push_and_pull(self):
        for push in (True, False):
            with self.subTest(push=push):
                source = self.local / ('interactive-file-' + str(push)); source.write_text('incoming')
                dest = self.local / ('interactive-target-' + str(push)); dest.mkdir(); (dest/source.name).write_text('old')
                remote = self.root / (self.local.name + '-changed-' + str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/sys.argv[2]).write_text(sys.argv[3])', remote, source.name, 'old' if push else 'incoming')
                selection = {'endpoint': local_endpoint(source) if push else self.endpoint(remote/source.name), 'mode': 'entry'}
                c = self.client(); c.send({'id':'ssh','op':'copy','sources':[selection], 'destination':self.endpoint(remote) if push else local_endpoint(dest),
                                          'options':{'on_conflict':'ask','preserve_times':True,'preserve_permissions':True}})
                seen=[]
                def answer(e):
                    seen.append(e)
                    if len(seen)==1:
                        if push: remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("foreign changed")', remote/source.name)
                        else: (dest/source.name).write_text('foreign changed')
                        self.conflict_reply(c,e)
                    else:
                        self.assertEqual(e['reason'],'destination_changed'); self.conflict_reply(c,e,'skip')
                self.assertEqual(self.finish_conflicts(c,answer)['status'],'success',c.events)
                self.assertEqual(len(seen),2)
                actual=remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).read_text()))',remote/source.name) if push else (dest/source.name).read_text()
                self.assertEqual(actual,'foreign changed')

    def test_interactive_cancel_and_scoped_skip_do_not_write_existing_entries(self):
        for cancel in (True, False):
            source=self.local/('conflicts-'+str(cancel)); source.mkdir()
            for i in range(4): (source/str(i)).write_text('incoming')
            remote=self.root/(self.local.name+'-scope-'+str(cancel))
            remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); [(p/str(i)).write_text("old") for i in range(4)]',remote)
            c=self.client(); c.send({'id':'ssh','op':'copy','sources':[{'endpoint':local_endpoint(source),'mode':'contents'}], 'destination':self.endpoint(remote),
                                    'options':{'on_conflict':'ask','preserve_times':True,'preserve_permissions':True}})
            r=self.finish_conflicts(c,lambda e:self.conflict_reply(c,e,'cancel' if cancel else 'skip',scope='job'))
            self.assertEqual(r['status'],'cancellation' if cancel else 'success',c.events)
            self.assertEqual(sum(e['type']=='conflict' for e in c.events),1)
            self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps([p.read_text() for p in pathlib.Path(sys.argv[1]).iterdir()]))',remote),['old']*4)

    def test_interactive_deadline_is_typed_and_retains_known_outcomes_in_both_directions(self):
        for push in (True,False):
            with self.subTest(push=push):
                source=self.local/('deadline-'+str(push)); source.write_text('incoming')
                dest=self.local/('deadline-target-'+str(push)); dest.mkdir(); (dest/source.name).write_text('old')
                remote=self.root/(self.local.name+'-deadline-'+str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/sys.argv[2]).write_text(sys.argv[3])',remote,source.name,'old' if push else 'incoming')
                c=self.client(); c.send({'id':'ssh','op':'copy','sources':[{'endpoint':local_endpoint(source) if push else self.endpoint(remote/source.name,idle_timeout_seconds='1'),'mode':'entry'}],
                                        'destination':self.endpoint(remote,idle_timeout_seconds='1') if push else local_endpoint(dest),
                                        'options':{'on_conflict':'ask','preserve_times':True,'preserve_permissions':True,'conflict_timeout_seconds':'1'}})
                self.assertEqual(self.finish_conflicts(c,lambda e:None)['status'],'partial_failure',c.events)
                error=next(e for e in c.events if e['type']=='error' and e['category']=='conflict_timeout')
                self.assertEqual((error['endpoint'],error['side'],error['stage'],error['native_code']),('ssh' if push else 'local','destination','waiting_conflict',None))
                item=inventory(c.events,'ssh').items[source.name.encode().hex()]
                self.assertEqual((item['status'],item['reason'],item['content_published']),('failure','conflict_timeout',False))
                actual=remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).read_text()))',remote/source.name) if push else (dest/source.name).read_text()
                self.assertEqual(actual,'old')

    def test_interactive_early_stale_control_is_rejected_without_interrupting_transfer(self):
        source=self.local/'file'; source.write_text('incoming')
        remote=self.root/(self.local.name+'-early-control')
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("old")',remote)
        c=self.client(); c.send({'id':'ssh','op':'copy','sources':[{'endpoint':local_endpoint(source),'mode':'entry'}],
                                'destination':self.endpoint(remote),'options':{'on_conflict':'ask','preserve_times':True,'preserve_permissions':True}})
        sent=False
        while True:
            e=c.read(15)
            if e['type']=='auth_prompt': self.response(c,e,'yes')
            if e['type']=='phase' and e['phase']=='scanning' and not sent:
                c.send({'id':'decision-unissued','op':'conflict_response','job_id':'ssh','conflict_id':'unissued','revision_token':'unissued','decision':'cancel'})
                sent=True
            if e['type']=='conflict': self.conflict_reply(c,e,'replace')
            if e['type']=='result':
                self.assertEqual(e['status'],'success',c.events); c.proc.wait(timeout=6); break
        self.assertTrue(sent,c.events)
        self.assertTrue(any(e['type']=='conflict_response_rejected' and e['reason']=='stale_conflict' for e in c.events),c.events)
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).read_text()))',remote/'file'),'incoming')

    def test_interactive_copy_requires_verified_conflict_bridge_before_operation(self):
        source=self.local/'file'; source.write_text('incoming')
        remote=self.root/(self.local.name+'-old-conflicts')
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()',remote)
        helper,marker=remote/'helper',remote/'unexpected-operation'
        for capability in ({}, {'interactive_conflicts':False,'conflict_bridge':'1'},
                           {'interactive_conflicts':'true','conflict_bridge':'1'}, {'interactive_conflicts':True,'conflict_bridge':'old'}):
            with self.subTest(capability=capability):
                caps={'schema':'1','id':'remote-hello','seq':'1','type':'capabilities','version':'old','operations':['copy'],
                      'transfer_bridge':'3','typed_transfer_errors':True,**capability}
                script='#!/usr/bin/python3\nimport sys,pathlib\nsys.stdin.readline()\nprint('+repr(json.dumps(caps))+',flush=True)\nif sys.stdin.readline(): pathlib.Path('+repr(str(marker))+').touch()\n'
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)',helper,script)
                c,result=self.copy_job([{'endpoint':local_endpoint(source),'mode':'entry'}],self.endpoint(remote,helper_path=str(helper)),policy='ask')
                self.assertEqual(result['status'],'failure',c.events)
                self.assertIn('unsupported_feature',self.errors(c))
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))',marker))

    def test_delta_hashing_and_reused_bytes_precede_publication_on_push_and_pull(self):
        basis = os.urandom(2 * 1024 * 1024)
        payload = basis[:800000] + b'changed block' * 200 + basis[802600:]
        source = self.local / 'file'; source.write_bytes(basis)
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        _, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'entry'}], self.endpoint(remote))
        self.assertEqual(result['status'], 'success')
        source.write_bytes(payload)
        for push in (True, False):
            with self.subTest(push=push):
                marker = (self.root if push else self.local) / (self.local.name + f'-delta-{push}')
                release = marker.with_name(marker.name + '-release')
                settings = {'XSYNC_FAULT_PREAD_NOTIFY': str(marker.with_name(marker.name + '-hash')),
                            'XSYNC_FAULT_PREAD_DELAY_US': '500000', 'XSYNC_FAULT_FUTIMENS_NOTIFY': str(marker),
                            'XSYNC_FAULT_FUTIMENS_RELEASE': str(release)}
                if push:
                    helper = self.fault_helper(remote, **settings)
                    sources, destination, env = local_endpoint(source), self.endpoint(remote, helper_path=helper), None
                else:
                    target = self.local / 'destination'; target.mkdir(); (target / 'file').write_bytes(basis)
                    sources, destination, env = self.endpoint(remote / 'file'), local_endpoint(target), self.local_fault_env(target, **settings)
                c = self.client(env)
                c.send({'id': 'ssh', 'op': 'copy', 'sources': [{'endpoint': sources, 'mode': 'entry'}],
                        'destination': destination, 'options': {'on_conflict': 'replace', 'preserve_times': True,
                                                               'preserve_permissions': True}})
                hashing = metadata = False
                while True:
                    event = c.read(15)
                    if event['type'] == 'auth_prompt': self.response(c, event, 'yes')
                    if event['type'] == 'progress' and event['phase'] == 'hashing':
                        hashing = True
                        self.assertEqual((event['logical_bytes_completed'], event['files_completed']), ('0', '0'))
                    if event['type'] == 'progress' and event['phase'] == 'applying_metadata' and not metadata:
                        present = remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker) if push else marker.exists()
                        if present:
                            metadata = True
                            self.assertEqual((event['logical_bytes_completed'], event['files_completed']), ('0', '0'))
                            self.assertFalse(any(e['type'] == 'item_result' for e in c.events))
                            if push: remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).touch()', release)
                            else: release.touch()
                    if event['type'] == 'result':
                        self.assertEqual(event['status'], 'success', c.events); c.proc.wait(timeout=5); break
                self.assertTrue(hashing and metadata, c.events)
                item = inventory(c.events, 'ssh').items[b'file'.hex()]
                self.assertEqual((item['status'], item['bytes_processed']), ('success', str(len(payload))))
                self.assertGreater(int(item['reused_bytes']), len(payload) // 2)
                self.assertLess(int(item['reused_bytes']), len(payload))
                stages = [e['stage'] for e in c.events if e['type'] == 'item_stage' and e['side'] == 'destination']
                self.assertEqual(stages.count('hashing'), 2)
                summary = next(e for e in c.events if e['type'] == 'summary')
                self.assertEqual((summary['logical_bytes_completed'], summary['reused_bytes']),
                                 (str(len(payload)), item['reused_bytes']))
                wire_bytes = max(int(e['wire_bytes']) for e in c.events if e['type'] == 'progress')
                self.assertGreater(wire_bytes, 0)
                self.assertLess(wire_bytes, len(payload) // 2)
                if push:
                    self.assertEqual(remote_json('import pathlib,sys,hashlib,json; print(json.dumps(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()))', remote / 'file'), hashlib.sha256(payload).hexdigest())
                else: self.assertEqual((target / 'file').read_bytes(), payload)

    def test_delta_receiver_checksum_failures_preserve_outputs_in_both_directions(self):
        basis = os.urandom(2 * 1024 * 1024)
        source = self.local / 'file'; source.write_bytes(basis)
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        _, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'entry'}], self.endpoint(remote))
        self.assertEqual(result['status'], 'success')
        source.write_bytes(basis[:10000] + b'new' + basis[10003:])
        for push in (True, False):
            with self.subTest(push=push):
                if push:
                    helper = self.fault_helper(remote, XSYNC_FAULT_PREAD_WRITABLE_ERROR='5')
                    c, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'entry'}], self.endpoint(remote, helper_path=helper))
                else:
                    target = self.local / 'destination'; target.mkdir(); (target / 'file').write_bytes(basis)
                    c, result = self.run_job('copy', env=self.local_fault_env(target, XSYNC_FAULT_PREAD_WRITABLE_ERROR='5'),
                                            sources=[{'endpoint': self.endpoint(remote / 'file'), 'mode': 'entry'}],
                                            destination=local_endpoint(target), options={'on_conflict': 'replace',
                                            'preserve_times': True, 'preserve_permissions': True})
                self.assertEqual(result['status'], 'partial_failure', c.events)
                error = next(e for e in c.events if e['type'] == 'error' and e['operation'] == 'verify reconstructed delta')
                self.assertEqual((error['category'], error['native_code'], error['endpoint'], error['item_id']),
                                 ('content', '5', 'ssh' if push else 'local', b'file'.hex()))
                item = inventory(c.events, 'ssh').items[b'file'.hex()]
                self.assertEqual((item['status'], item['content_published'], item['metadata_complete']), ('failure', False, False))
                summary = next(e for e in c.events if e['type'] == 'summary')
                self.assertEqual((summary['logical_bytes_completed'], summary['files_completed']), ('0', '0'))
                if push:
                    self.assertEqual(remote_json('import pathlib,sys,hashlib,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([hashlib.sha256((p/"file").read_bytes()).hexdigest(),sorted(q.name for q in p.iterdir())]))', remote), [hashlib.sha256(basis).hexdigest(), ['file']])
                else:
                    self.assertEqual((target / 'file').read_bytes(), basis)
                    self.assertEqual([p.name for p in target.iterdir()], ['file'])

    def test_receiver_io_and_disk_full_failures_have_retryable_item_inventory(self):
        source = self.local / 'file'; source.write_bytes(b'incoming' * 10000)
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        for push in (True, False):
            for code, category, status in ((errno.EIO, 'content', 'partial_failure'), (errno.ENOSPC, 'disk_full', 'failure')):
                with self.subTest(push=push, code=code):
                    if push:
                        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("old good copy")', remote / 'file')
                        helper = self.fault_helper(remote, XSYNC_FAULT_WRITE_ERROR=str(code))
                        c, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'entry'}], self.endpoint(remote, helper_path=helper))
                    else:
                        target = self.local / ('destination-' + str(code)); target.mkdir(); (target / 'file').write_text('old good copy')
                        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(b"incoming"*10000)', remote / 'file')
                        c, result = self.run_job('copy', env=self.local_fault_env(target, XSYNC_FAULT_WRITE_ERROR=str(code)),
                            sources=[{'endpoint': self.endpoint(remote / 'file'), 'mode': 'entry'}], destination=local_endpoint(target),
                            options={'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True})
                    self.assertEqual(result['status'], status, c.events)
                    error = next(e for e in c.events if e['type'] == 'error' and e['operation'] == 'write')
                    self.assertEqual((error['category'], error['native_code'], error['side'], error['stage'], error['endpoint']),
                                     (category, str(code), 'destination', 'content', 'ssh' if push else 'local'))
                    view = inventory(c.events, 'ssh')
                    item = view.items[b'file'.hex()]
                    self.assertEqual((item['status'], item['content_published'], item['metadata_complete']), ('failure', False, False))
                    if push:
                        self.assertEqual(remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([(p/"file").read_text(),sorted(q.name for q in p.iterdir())]))', remote), ['old good copy', ['file']])
                    else:
                        self.assertEqual((target / 'file').read_text(), 'old good copy')
                        self.assertEqual([p.name for p in target.iterdir()], ['file'])
                    selections = view.retry_selections({'local': local_endpoint(source), 'ssh': self.endpoint(remote)})
                    _, result = self.copy_job(selections, self.endpoint(remote) if push else local_endpoint(target))
                    self.assertEqual(result['status'], 'success')

    def test_failed_remote_source_preflight_keeps_native_status_and_selection_results(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"good").write_text("unselected after failed preflight")', remote)
        target = self.local / 'destination'; target.mkdir()
        c, result = self.copy_job([{'endpoint': self.endpoint(remote / name), 'mode': 'entry'} for name in ('good', 'missing')], local_endpoint(target))
        self.assertEqual((result['status'], result['code']), ('failure', '3'), c.events)
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['category'], error['operation'], error['native_code'], error['endpoint']), ('missing', 'source_preflight', '2', 'ssh'))
        self.assertNotIn('network', self.errors(c))
        view = inventory(c.events, 'ssh')
        self.assertEqual(view.items[b'good'.hex()]['status'], 'skipped')
        self.assertEqual(view.items[b'missing'.hex()]['status'], 'failure')
        self.assertEqual(list(target.iterdir()), [])
        selections = view.retry_selections({'ssh': self.endpoint(remote)})
        self.assertEqual(selections, [{'endpoint': self.endpoint(remote / 'missing'), 'mode': 'entry'}])
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("recovered")', remote / 'missing')
        _, result = self.copy_job(selections, local_endpoint(target))
        self.assertEqual(result['status'], 'success')
        self.assertEqual([p.name for p in target.iterdir()], ['missing'])

    def test_remote_scan_child_errors_preserve_old_links_and_explicit_retry(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"good").write_text("observed child"); (p/"link").symlink_to("good")', remote)
        target = self.local / 'destination'; target.mkdir(); (target / 'link').symlink_to('protected old target')
        helper = self.fault_helper(remote, XSYNC_FAULT_READLINK_NAME='link')
        c, result = self.copy_job([{'endpoint': self.endpoint(remote, helper_path=helper), 'mode': 'contents'}], local_endpoint(target))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error' and e['operation'] == 'readlink_source')
        self.assertEqual((error['side'], error['native_code'], error['endpoint'], error['item_id']), ('source', '5', 'ssh', b'link'.hex()))
        self.assertEqual(error['path']['bytes_hex'], os.fsencode(remote / 'link').hex())
        view = inventory(c.events, 'ssh')
        self.assertEqual((view.items['']['status'], view.items[b'link'.hex()]['status']), ('failure', 'failure'))
        self.assertEqual((target / 'link').readlink(), pathlib.Path('protected old target'))
        self.assertEqual((target / 'good').read_text(), 'observed child')
        selections = view.retry_selections({'ssh': self.endpoint(remote)})
        self.assertEqual(selections, [{'endpoint': self.endpoint(remote), 'mode': 'contents'}])
        _, result = self.copy_job(selections, local_endpoint(target))
        self.assertEqual(result['status'], 'success')
        self.assertEqual((target / 'link').readlink(), pathlib.Path('good'))

    def test_push_pull_literal_selection_and_receiver_completion(self):
        source = self.local / 'source *?'
        source.mkdir()
        for name in ('*?', 'colon:name', 'new\nline', '-leading'):
            (source / name).write_bytes(name.encode()*100)
        (source / 'sub').mkdir()
        (source / 'sub' / 'file').write_bytes(b'nested')
        (source / 'link').symlink_to('sub/file')
        stamp = 1600000000123456789
        os.chmod(source / 'sub', 0o750)
        os.utime(source / 'sub', ns=(stamp, stamp))
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        c, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'contents'}], self.endpoint(remote))
        self.assertEqual(result['status'], 'success', c.events)
        snapshot = remote_json('import os,pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps({"names":sorted(x.name for x in p.iterdir()),"mode":(p/"sub").stat().st_mode&511,"time":(p/"sub").stat().st_mtime_ns,"file":(p/"sub"/"file").read_text(),"link":os.readlink(p/"link")}))', remote)
        assert_scope(self,c.events,remote,'ssh')
        hints = [e for e in c.events if e['type'] == 'invalidate' and e.get('reason') == 'transfer_item']
        self.assertTrue(all(e['endpoint'] == 'ssh' for e in hints)); self.assertGreaterEqual(len(hints),7)
        self.assertTrue(any(e['path']['bytes_hex'] == os.fsencode(remote/'sub'/'file').hex() for e in hints))
        self.assertEqual(snapshot['names'], sorted(x.name for x in source.iterdir()))
        self.assertEqual(snapshot['mode'], 0o750)
        self.assertEqual(snapshot['time'], stamp)
        self.assertEqual(snapshot['file'], 'nested')
        self.assertEqual(snapshot['link'], 'sub/file')
        self.assertTrue(any(e['type'] == 'summary' for e in c.events))
        dest = self.local / 'destination'
        dest.mkdir()
        (dest / 'unselected').write_text('keep')
        c, result = self.copy_job([{'endpoint': self.endpoint(remote / '*?'), 'mode': 'entry'},
                                   {'endpoint': self.endpoint(remote / 'sub'), 'mode': 'entry'}], local_endpoint(dest))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(sorted(x.name for x in dest.iterdir()), ['*?', 'sub', 'unselected'])
        assert_scope(self,c.events,dest)
        hints = [e for e in c.events if e['type'] == 'invalidate' and e.get('reason') == 'transfer_item']
        self.assertTrue(all(e['endpoint'] == 'local' for e in hints)); self.assertGreaterEqual(len(hints),3)
        self.assertEqual((dest / '*?').read_bytes(), (source / '*?').read_bytes())
        self.assertEqual((dest / 'sub').stat().st_mtime_ns, stamp)
        self.assertEqual((dest / 'sub' / 'file').read_bytes(), b'nested')

    def test_remote_destination_preflight_is_read_only_and_keeps_exact_advisory_budget(self):
        remote = self.root/(self.local.name+'-preflight')
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"existing").write_bytes(b"unchanged")',remote)
        before = remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); s=p.stat(); print(json.dumps([s.st_mtime_ns,s.st_ctime_ns]))',remote)
        c,result = self.run_job('preflight',endpoint=self.endpoint(remote),space={'regular_file_sizes':['9007199254740993','1'],'jobs':'1','retained_logical_bytes':'37'})
        self.assertEqual(result['status'],'success',c.events)
        row = next(e for e in c.events if e['type'] == 'destination_preflight')
        self.assertEqual(row['endpoint'],'ssh'); self.assertEqual(row['path']['bytes_hex'],os.fsencode(remote).hex())
        self.assertEqual(row['space']['copy_logical_bytes'],'9007199254740994')
        self.assertEqual(row['space']['atomic_staging_peak_logical_bytes'],'9007199254740993')
        self.assertFalse(row['space']['inputs_verified']); self.assertFalse(row['copy_authorized']); self.assertFalse(row['write_probe_performed'])
        after = remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); s=p.stat(); print(json.dumps([s.st_mtime_ns,s.st_ctime_ns]))',remote)
        self.assertEqual(before,after)
        self.assertEqual(remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([(f.name,f.read_text()) for f in p.iterdir()]))',remote),[['existing','unchanged']])
        peer = next(e for e in c.events if e['type'] == 'capabilities' and e.get('backend') == 'native-ssh')
        self.assertEqual(peer['destination_preflight'],'1'); self.assertIn('preflight',peer['operations'])

    def test_read_only_preview_guarded_copy_and_stale_remote_revision_push_and_pull(self):
        from app_client import TransferPreview
        for push in (True,False):
            with self.subTest(push=push):
                local=self.local/('preview-'+str(push)); local.mkdir()
                remote=self.root/(self.local.name+'-preview-'+str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_bytes(sys.argv[2].encode()); (p/"extra").write_bytes(b"keep")',remote,'old' if push else 'incoming')
                (local/'file').write_bytes(b'incoming' if push else b'old'); (local/'extra').write_bytes(b'keep')
                sources=[{'endpoint':local_endpoint(local) if push else self.endpoint(remote),'mode':'contents'}]
                destination=self.endpoint(remote) if push else local_endpoint(local)
                options={'on_conflict':'replace','preserve_times':True,'preserve_permissions':True,'jobs':'1'}
                request={'id':'ssh','op':'preview','mode':'selected_copy','sources':sources,'destination':destination,'options':options}
                before=remote_json('import pathlib,json,sys; p=pathlib.Path(sys.argv[1]); print(json.dumps({q.name:[q.stat().st_mtime_ns,q.stat().st_ctime_ns,q.read_bytes().hex()] for q in p.iterdir()}))',remote)
                c,result=self.run_job('preview',mode=request['mode'],sources=sources,destination=destination,options=options)
                self.assertEqual(result['status'],'success',c.events)
                view=TransferPreview(request)
                for event in c.events: view.accept(event)
                self.assertEqual(view.summary['direction'],'push' if push else 'pull'); self.assertTrue(view.summary['complete'])
                after=remote_json('import pathlib,json,sys; p=pathlib.Path(sys.argv[1]); print(json.dumps({q.name:[q.stat().st_mtime_ns,q.stat().st_ctime_ns,q.read_bytes().hex()] for q in p.iterdir()}))',remote)
                self.assertEqual(before,after)
                self.assertEqual((local/'file').read_bytes(),b'incoming' if push else b'old')
                guarded=view.execution_request('ssh')
                c,result=self.run_job('copy',sources=sources,destination=destination,options=options,expected_preview=guarded['expected_preview'])
                self.assertEqual(result['status'],'success',c.events)
                self.assertEqual(sum(e['type']=='preview_revalidated' for e in c.events),1)
                self.assertEqual(self.private_target_bytes(destination,'file'),b'incoming')
                c,result=self.run_job('preview',mode='selected_copy',sources=sources,destination=destination,options=options)
                self.assertEqual(result['status'],'success',c.events)
                view=TransferPreview(request)
                for event in c.events: view.accept(event)
                remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/"file").write_bytes(b"external revision")',remote)
                c,result=self.run_job('copy',sources=sources,destination=destination,options=options,expected_preview=view.execution_request('ssh')['expected_preview'])
                self.assertNotEqual(result['status'],'success',c.events)
                self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' for e in c.events),c.events)
                self.assertFalse(any(e['type']=='item_discovered' for e in c.events))

    def test_preview_source_and_destination_revisions_remain_bound_while_waiting_for_conflict(self):
        from app_client import TransferPreview
        for push in (True,False):
            for changed in ('source','destination','source_symlink'):
                with self.subTest(push=push,changed=changed):
                    name='bound-'+str(push)+'-'+changed
                    local=self.local/name; local.mkdir(); remote=self.root/(self.local.name+'-'+name)
                    remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()',remote)
                    if changed=='source_symlink':
                        if push:
                            (local/'file').symlink_to('incoming')
                            remote_code('import os,sys; os.symlink("good",sys.argv[1]+"/file")',remote)
                        else:
                            remote_code('import os,sys; os.symlink("incoming",sys.argv[1]+"/file")',remote)
                            (local/'file').symlink_to('good')
                    else:
                        (local/'file').write_bytes(b'incoming' if push else b'good')
                        remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/"file").write_bytes(sys.argv[2].encode())',remote,'good' if push else 'incoming')
                    sources=[{'endpoint':local_endpoint(local) if push else self.endpoint(remote),'mode':'contents'}]
                    destination=self.endpoint(remote) if push else local_endpoint(local)
                    options={'on_conflict':'ask','preserve_times':True,'preserve_permissions':True,'jobs':'1'}
                    request={'id':'ssh','op':'preview','mode':'selected_copy','sources':sources,'destination':destination,'options':options}
                    c,result=self.run_job('preview',mode='selected_copy',sources=sources,destination=destination,options=options)
                    self.assertEqual(result['status'],'success',c.events)
                    view=TransferPreview(request)
                    for event in c.events: view.accept(event)
                    c=self.client(); c.send(view.execution_request('ssh'))
                    while True:
                        event=c.read(15)
                        if event['type']=='auth_prompt': self.response(c,event,'yes')
                        if event['type']=='conflict': break
                        self.assertNotEqual(event['type'],'result',c.events)
                    changed_remote=not push if changed.startswith('source') else push
                    if changed_remote:
                        remote_code('import pathlib,sys,os; p=pathlib.Path(sys.argv[1])/"file"; p.unlink() if p.is_symlink() else None; os.symlink("changed",p) if sys.argv[2]=="source_symlink" else p.write_bytes(b"external revision")',remote,changed)
                    else:
                        p=local/'file'
                        if p.is_symlink(): p.unlink(); p.symlink_to('changed')
                        else: p.write_bytes(b'external revision')
                    c.send({'id':'decision-'+event['conflict_id'],'op':'conflict_response','job_id':'ssh',
                            'conflict_id':event['conflict_id'],'revision_token':event['revision_token'],'decision':'replace'})
                    result=c.finish(15); self.assertEqual(result['status'],'partial_failure',c.events)
                    self.assertEqual(sum(e['type']=='conflict' for e in c.events),1)
                    self.assertTrue(any(e['type']=='error' and e.get('reason')=='stale_preview' for e in c.events),c.events)
                    if changed=='source_symlink':
                        observed=remote_json('import os,json,sys; print(json.dumps(os.readlink(sys.argv[1]+"/file")))',remote) if push else os.readlink(local/'file')
                        self.assertEqual(observed,'good')
                    else: self.assertEqual(self.private_target_bytes(destination,'file'),b'external revision' if changed=='destination' else b'good')
                    self.assertFalse(any(e['type'].startswith('_preview_') for e in c.events))

    def test_remote_mirror_preview_proposes_deletes_without_writing_or_copy_guard(self):
        source=self.local/'preview-source'; source.mkdir(); (source/'file').write_bytes(b'incoming')
        remote=self.root/(self.local.name+'-mirror-preview')
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"old").write_bytes(b"only copy")',remote)
        c,result=self.run_job('preview',mode='mirror',sources=[{'endpoint':local_endpoint(source),'mode':'contents'}],destination=self.endpoint(remote),
                              options={'on_conflict':'replace','preserve_times':True,'preserve_permissions':True})
        self.assertEqual(result['status'],'success',c.events)
        summary=next(e for e in c.events if e['type']=='preview_summary')
        self.assertEqual(summary['counts']['delete'],'1'); self.assertFalse(summary['execution_supported']); self.assertIsNone(summary['execution_guard'])
        self.assertEqual(remote_json('import pathlib,json,sys; p=pathlib.Path(sys.argv[1]); print(json.dumps({q.name:q.read_bytes().hex() for q in p.iterdir()}))',remote),{'old':b'only copy'.hex()})

    def test_preflight_requires_exact_remote_capability_and_operation_before_submission(self):
        remote = self.root/(self.local.name+'-preflight-unsupported')
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()',remote)
        helper,marker = remote/'helper',remote/'unexpected-request'
        for feature,operations in [(None,['preflight']),(False,['preflight']),(1,['preflight']),('2',['preflight']),('1',[])]:
            with self.subTest(feature=feature,operations=operations):
                caps = {'schema':'1','id':'remote-hello','seq':'1','type':'capabilities','version':'old','operations':operations}
                if feature is not None: caps['destination_preflight'] = feature
                script = '#!/usr/bin/python3\nimport sys,json,pathlib\nsys.stdin.readline()\nprint('+repr(json.dumps(caps))+',flush=True)\nif sys.stdin.readline(): pathlib.Path('+repr(str(marker))+').touch()\n'
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o700)',helper,script)
                c,result = self.run_job('preflight',endpoint=self.endpoint(remote,helper_path=str(helper)))
                self.assertEqual(result['status'],'failure',c.events); self.assertIn('unsupported_feature',self.errors(c))
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))',marker))

    def fault_helper(self, path, **settings):
        helper = self.root / (self.local.name + '-fault-helper')
        values = {'LD_PRELOAD': '/work/build/fault_io.so', 'XSYNC_FAULT_PATH': str(path), **settings}
        script = '#!/bin/sh\nexec env ' + ' '.join(shlex.quote(k+'='+v) for k, v in values.items())
        script += ' /usr/local/bin/xs "$@"\n'
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o700)', helper, script)
        return str(helper)

    def test_partial_remote_listing_and_cancelled_stale_pane(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from app_client import ListingView
        source = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); '
                    '[(p/f"entry-{i}").touch() for i in range(300)]', source)
        empty = self.root / (self.local.name + '-empty')
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', empty)
        for settings, count, code in (({'XSYNC_FAULT_LIST_AFTER': '140'}, 140, '5'),
                                      ({'XSYNC_FAULT_STAT_NAME': 'entry-137'}, 299, '2')):
            helper = self.fault_helper(source, **settings)
            c, result = self.run_job(endpoint=self.endpoint(source, helper_path=helper))
            self.assertEqual(result['status'], 'partial_failure', c.events)
            entries = [entry for e in c.events if e['type'] == 'entries' for entry in e['entries']]
            self.assertEqual(len(entries), count)
            self.assertEqual(len({e['name']['bytes_hex'] for e in entries}), count)
            error = next(e for e in c.events if e['type'] == 'error')
            self.assertEqual((error['native_code'], error['endpoint']), (code, 'ssh'))
        helper = self.fault_helper(source, XSYNC_FAULT_OPENDIR_ERROR='13')
        c, result = self.run_job(endpoint=self.endpoint(source, helper_path=helper))
        self.assertEqual(result['status'], 'failure', c.events)
        self.assertFalse(any(e['type'] == 'entries' for e in c.events))
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['category'], error['native_code'], error['endpoint']), ('permission', '13', 'ssh'))
        helper = self.fault_helper(source, XSYNC_FAULT_LIST_DELAY_US='5000')
        old = self.client()
        old.send({'id': 'old-pane', 'op': 'list', 'endpoint': self.endpoint(source, helper_path=helper)})
        view = ListingView('old-pane')
        while True:
            event = old.read(15)
            view.accept(event)
            if event['type'] == 'entries': break
        self.assertEqual(len(view.entries), 128)
        view.begin('ssh')
        fresh, result = self.run_job(endpoint=self.endpoint(empty))
        for e in fresh.events: view.accept(e)
        old.send({'id': 'cancel-old', 'op': 'cancel', 'job_id': 'old-pane'})
        self.assertEqual(old.finish()['status'], 'cancellation')
        for event in old.events: self.assertFalse(view.accept(event))
        self.assertEqual((view.status, view.entries, view.errors), ('success', [], []))

    def test_receiver_metadata_phase_and_published_bytes(self):
        source = self.local / 'file'
        source.write_bytes(b'x' * (1024 * 1024))
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("good old copy")', remote)
        helper = self.fault_helper(remote, XSYNC_FAULT_FUTIMENS_DELAY_US='800000')
        c, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'entry'}],
                                  self.endpoint(remote, helper_path=helper), bandwidth_bytes_per_second='1048576')
        self.assertEqual(result['status'], 'success', c.events)
        progress = [e for e in c.events if e['type'] == 'progress' and e['phase'] == 'applying_metadata']
        self.assertTrue(progress, c.events)
        published = next(i for i, e in enumerate(c.events) if e['type'] == 'item_result' and e.get('content_published'))
        before_publish = [e for e in c.events[:published] if e['type'] == 'progress' and e['phase'] == 'applying_metadata']
        self.assertTrue(before_publish, c.events)
        self.assertTrue(all(e['logical_bytes_completed'] == '0' and e['files_completed'] == '0' for e in before_publish))
        # Root directory metadata can follow publication of its completed file.
        self.assertTrue(all(int(e['logical_bytes_completed']) <= source.stat().st_size for e in progress))
        summary = next(e for e in c.events if e['type'] == 'summary')
        self.assertEqual(summary['logical_bytes_completed'], str(source.stat().st_size))
        # This empty directory has no file worker to keep phase sampling alive.
        directory = self.local / 'directory'
        directory.mkdir()
        os.utime(directory, ns=(1600000000123456789,) * 2)
        c, result = self.copy_job([{'endpoint': local_endpoint(directory), 'mode': 'entry'}],
                                  self.endpoint(remote, helper_path=helper))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertTrue(any(e['type'] == 'progress' and e['phase'] == 'applying_metadata' for e in c.events), c.events)
        timestamp = remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).stat().st_mtime_ns))', remote / 'directory')
        self.assertEqual(timestamp, 1600000000123456789)

    def test_late_root_stat_failure_retains_native_error_and_no_write_outcomes(self):
        for push in (True, False):
            with self.subTest(push=push):
                source = self.local / ('root-stat-source-' + str(push)); source.mkdir(); (source / 'file').write_text('incoming')
                remote = self.root / (self.local.name + '-root-stat-' + str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text(sys.argv[2])', remote, 'old good copy' if push else 'incoming')
                env = None
                if push:
                    remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/"unselected").write_text("protected")', remote)
                    helper = self.fault_helper(remote, XSYNC_FAULT_STAT_NAME='.')
                    selection, destination = {'endpoint': local_endpoint(source), 'mode': 'contents'}, self.endpoint(remote, helper_path=helper)
                else:
                    dest = self.local / 'root-stat-destination'; dest.mkdir(); (dest / 'file').write_text('old good copy'); (dest / 'unselected').write_text('protected')
                    env = self.local_fault_env(dest, XSYNC_FAULT_STAT_NAME='.')
                    selection, destination = {'endpoint': self.endpoint(remote), 'mode': 'contents'}, local_endpoint(dest)
                original = {'id': 'ssh', 'op': 'copy', 'sources': [selection], 'destination': destination,
                            'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}}
                c, result = self.run_job('copy', sources=[selection], destination=destination, options=original['options'], env=env)
                self.assertEqual(result['status'], 'partial_failure', c.events)
                error = next(e for e in c.events if e['type'] == 'error')
                self.assertEqual((error['operation'], error['native_code'], error['endpoint']), ('stat_destination_root', '2', 'ssh' if push else 'local'))
                view = inventory(c.events, 'ssh')
                self.assertEqual(set(view.items), {'', b'file'.hex()})
                self.assertTrue(all(item['status'] == 'failure' and not item['content_published'] and not item['metadata_complete'] for item in view.items.values()), c.events)
                if push:
                    old = remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"file").read_text()))', remote)
                    remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', helper, '#!/bin/sh\nexec /usr/local/bin/xs "$@"\n')
                else: old = (dest / 'file').read_text()
                self.assertEqual(old, 'old good copy')
                retry = view.retry_requests(original)[0]
                _, retried = self.copy_job(retry['sources'], retry['destination'])
                self.assertEqual(retried['status'], 'success')
                if push:
                    kept = remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"unselected").read_text()))', remote)
                else: kept = (dest / 'unselected').read_text()
                self.assertEqual(kept, 'protected')

    def test_missing_destination_root_before_setup_is_preserved_in_both_directions(self):
        _, probe = self.run_job('probe')
        self.assertEqual(probe['status'], 'success')
        for push in (True, False):
            with self.subTest(push=push):
                source = self.local / ('guard-source-' + str(push)); source.mkdir(); (source / 'file').write_text('incoming')
                remote = self.root / (self.local.name + '-guard-' + str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("incoming"); (p/"unselected").write_text("protected")', remote)
                marker, release = self.local / ('scanning-' + str(push)), self.local / ('scan-release-' + str(push))
                if push:
                    c = self.client(self.local_fault_env(source, XSYNC_FAULT_SCAN_NOTIFY=str(marker), XSYNC_FAULT_SCAN_RELEASE=str(release)))
                    selection, destination = {'endpoint': local_endpoint(source), 'mode': 'contents'}, self.endpoint(remote)
                    displaced = remote.with_name(remote.name + '-displaced')
                else:
                    destination_path = self.local / 'guard-destination'; destination_path.mkdir(); (destination_path / 'unselected').write_text('protected')
                    marker, release = self.root / (self.local.name + '-scanning'), self.root / (self.local.name + '-scan-release')
                    helper = self.fault_helper(remote, XSYNC_FAULT_SCAN_NOTIFY=str(marker), XSYNC_FAULT_SCAN_RELEASE=str(release))
                    c = self.client()
                    selection, destination = {'endpoint': self.endpoint(remote, helper_path=helper), 'mode': 'contents'}, local_endpoint(destination_path)
                    displaced = self.local / 'displaced'
                original = {'id': 'ssh', 'op': 'copy', 'sources': [selection], 'destination': destination,
                            'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}}
                c.send(original)
                deadline = time.monotonic() + 8
                while not (marker.exists() if push else remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker)):
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(.01)
                if push:
                    remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).rename(sys.argv[2])', remote, displaced)
                    release.touch()
                else:
                    destination_path.rename(displaced)
                    remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).touch()', release)
                result = c.finish()
                self.assertEqual(result['status'], 'partial_failure', c.events)
                if push:
                    exists = remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', remote)
                else: exists = destination_path.exists()
                self.assertFalse(exists)
                error = next(e for e in c.events if e['type'] == 'error' and e.get('reason') == 'destination_root_changed')
                self.assertEqual((error['endpoint'], error['observed_revision']), ('ssh' if push else 'local', {'exists': False}))
                view = inventory(c.events, 'ssh')
                self.assertTrue(view.items, c.events)
                self.assertTrue(all(item['status'] == 'failure' and not item['metadata_complete'] for item in view.items.values()), c.events)
                if push:
                    remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).rename(sys.argv[2])', displaced, remote)
                else:
                    displaced.rename(destination_path)
                retry = view.retry_requests(original)[0]
                _, retried = self.copy_job(retry['sources'], retry['destination'])
                self.assertEqual(retried['status'], 'success')
                if push:
                    kept = remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"unselected").read_text()))', remote)
                else: kept = (destination_path / 'unselected').read_text()
                self.assertEqual(kept, 'protected')

    def test_explicit_selection_mappings_keep_names_and_actual_sources_in_both_directions(self):
        for push in (True, False):
            with self.subTest(push=push):
                source = self.local / ('mapped-source-' + str(push)); source.mkdir()
                for directory, text in (('a', 'first'), ('b', 'second')):
                    (source / directory).mkdir(); (source / directory / 'file').write_text(text)
                (source / 'folder').mkdir(); (source / 'folder' / 'child').write_text('nested')
                (source / 'link').symlink_to('literal target')
                remote = self.root / (self.local.name + '-mapped-' + str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("unselected sibling")', remote)
                if not push:
                    remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/"a").mkdir(); (p/"a"/"file").write_text("first"); (p/"b").mkdir(); (p/"b"/"file").write_text("second"); (p/"folder").mkdir(); (p/"folder"/"child").write_text("nested"); (p/"link").symlink_to("literal target")', remote)
                    destination_path = self.local / 'mapped-destination'; destination_path.mkdir()
                    (destination_path / 'file').write_text('unselected sibling')
                pairs = [('a/file', 'colon:name'), ('b/file', '*?\nline'), ('folder', '-renamed folder'), ('link', 'renamed link')]
                selections = [{'endpoint': local_endpoint(source / name) if push else self.endpoint(remote / name),
                               'mode': 'entry', 'destination_name': {'bytes_hex': os.fsencode(mapped).hex()}} for name, mapped in pairs]
                destination = self.endpoint(remote) if push else local_endpoint(destination_path)
                c, result = self.copy_job(selections, destination)
                self.assertEqual(result['status'], 'success', c.events)
                view = inventory(c.events, 'ssh')
                for selection in selections:
                    item = view.items[selection['destination_name']['bytes_hex']]
                    self.assertEqual(item['source_path']['bytes_hex'], selection['endpoint']['path']['bytes_hex'])
                    self.assertEqual(item['status'], 'success')
                self.assertIn(b'-renamed folder/child'.hex(), view.items)
                if push:
                    found = remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([(p/"colon:name").read_text(),(p/sys.argv[2]).read_text(),(p/"-renamed folder"/"child").read_text(),str((p/"renamed link").readlink()),(p/"file").read_text()]))', remote, '*?\nline')
                else:
                    found = [(destination_path / 'colon:name').read_text(), (destination_path / '*?\nline').read_text(),
                             (destination_path / '-renamed folder' / 'child').read_text(), str((destination_path / 'renamed link').readlink()), (destination_path / 'file').read_text()]
                self.assertEqual(found, ['first', 'second', 'nested', 'literal target', 'unselected sibling'])

    def test_mapped_io_failures_and_retry_requests_keep_destination_names(self):
        sys.path.insert(0, str(ROOT/'tools'))
        from app_queue import PersistentQueue, execute_next
        for push in (True, False):
            with self.subTest(push=push):
                source = self.local / ('mapping-retry-' + str(push)); source.write_text('incoming mapped bytes')
                remote = self.root / (self.local.name + '-mapping-retry-' + str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text(sys.argv[2]); (p/"mapped name").write_text("old good copy")', remote,
                            'unselected sibling' if push else 'incoming mapped bytes')
                if push:
                    helper = self.fault_helper(remote, XSYNC_FAULT_WRITE_ERROR='5')
                    selected = local_endpoint(source)
                    destination = self.endpoint(remote, helper_path=helper)
                else:
                    destination_path = self.local / 'mapped-retry-destination'; destination_path.mkdir()
                    (destination_path / 'mapped name').write_text('old good copy'); (destination_path / 'file').write_text('unselected sibling')
                    helper = self.fault_helper(remote / 'file', XSYNC_FAULT_READ_ERROR='1')
                    selected = self.endpoint(remote / 'file', helper_path=helper)
                    destination = local_endpoint(destination_path)
                selection = {'endpoint': selected, 'mode': 'entry', 'destination_name': {'bytes_hex': b'mapped name'.hex()}}
                original = {'id': 'ssh', 'op': 'copy', 'sources': [selection], 'destination': destination,
                            'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}}
                c, result = self.copy_job([selection], destination)
                self.assertEqual(result['status'], 'partial_failure', c.events)
                view = inventory(c.events, 'ssh')
                self.assertEqual(view.items[b'mapped name'.hex()]['status'], 'failure')
                self.assertEqual(view.items[b'mapped name'.hex()]['source_path']['bytes_hex'], selected['path']['bytes_hex'])
                requests = view.retry_requests(original)
                self.assertEqual(requests[0]['sources'], [selection])
                # Persist real reported outcomes with external profile references,
                # then exercise the manager's fresh retry across its restart.
                saved = json.loads(json.dumps(original)); profile = None
                for ep in [saved['destination']] + [s['endpoint'] for s in saved['sources']]:
                    if ep['kind'] == 'ssh': profile = ep.pop('connection'); ep['profile_id'] = 'saved-host'
                queue_path = self.local / ('mapped-retry-'+str(push)+'.json')
                q = PersistentQueue(queue_path); self.addCleanup(q.close); q.enqueue(saved, 'original'); claim = q.claim()
                for event in c.events: q.accept('original', dict(event, id=claim['request']['id']))
                parent = q.snapshot()[0]; children = q.retry_failed('original'); q.close()
                q = PersistentQueue(queue_path); self.addCleanup(q.close)
                remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', helper, '#!/bin/sh\nexec /usr/local/bin/xs "$@"\n')
                conflicts = []
                def choose(event): conflicts.append(event); return 'replace'
                retried = execute_next(q, BINARY, profile_resolver=lambda _:profile, prompt_handler=lambda _:'yes', conflict_handler=choose)
                self.assertEqual(retried['status'], 'success')
                self.assertEqual(len(conflicts), 1); self.assertEqual(q.snapshot()[0], parent)
                self.assertEqual(q.snapshot()[1]['id'], children[0]); self.assertEqual(q.snapshot()[1]['state'], 'success')
                self.assertNotIn(IDENTITY, queue_path.read_text())
                if push:
                    contents = remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([(p/"mapped name").read_text(),(p/"file").read_text()]))', remote)
                else:
                    contents = [(destination_path / 'mapped name').read_text(), (destination_path / 'file').read_text()]
                self.assertEqual(contents, ['incoming mapped bytes', 'unselected sibling'])

    def filesystem_action(self, operation, remote, names, connection=None, **options):
        sys.path.insert(0, str(ROOT / 'tools'))
        from app_client import action_request
        parent_client, parent_result = self.run_job('lstat', self.endpoint(remote))
        listing_client, listing_result = self.run_job('list', self.endpoint(remote))
        self.assertEqual(parent_result['status'], 'success')
        self.assertEqual(listing_result['status'], 'success')
        parent = next(e['entry']['revision'] for e in parent_client.events if e['type'] == 'entry')
        entries = [entry for e in listing_client.events if e['type'] == 'entries' for entry in e['entries']]
        request = action_request('ssh', operation, self.endpoint(remote), parent, entries, names, **options)
        fields = {k:v for k,v in request.items() if k not in ('id', 'op', 'endpoint')}
        return self.run_job(operation, self.endpoint(remote, **(connection or {})), **fields)

    def move_request(self, sources, destination, policy='replace'):
        def revision(selected):
            if selected['kind'] == 'ssh':
                c, result = self.run_job('lstat', selected)
            else:
                c = self.client(); c.send({'id':'stat','op':'lstat','endpoint':selected}); result = c.finish()
            self.assertEqual(result['status'], 'success', c.events)
            return next(e['entry']['revision'] for e in c.events if e['type']=='entry')
        parent = revision(destination)
        sources = [dict(selected, expected_revision=revision(selected['endpoint'])) for selected in sources]
        return {'id':'ssh', 'op':'move', 'sources':sources, 'destination':destination, 'destination_parent_revision':parent,
                'options':{'on_conflict':policy, 'preserve_times':True, 'preserve_permissions':True}}

    def move_job(self, sources, destination, policy='replace', env=None):
        request = self.move_request(sources, destination, policy)
        return self.run_job('move', env=env, **{k:v for k,v in request.items() if k not in ('id','op')})

    def wait_move_verification(self, c):
        while True:
            event = c.read(20)
            if event['type'] == 'auth_prompt': self.response(c, event, 'yes')
            if event['type'] == 'result': self.fail('move ended before verification: ' + repr(c.events))
            if event['type'] == 'phase' and event['phase'] == 'verifying_move': return

    def test_move_remote_lock_covers_verification_in_both_directions(self):
        for push in (True, False):
            with self.subTest(push=push):
                remote = self.root / (self.local.name + '-move-lock-' + str(push))
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_bytes(b"a"*(20*1024*1024)) if sys.argv[2]=="pull" else None', remote, 'push' if push else 'pull')
                folder = self.local/str(push); folder.mkdir()
                if push: (folder/'file').write_bytes(b'a'*(20*1024*1024))
                source = local_endpoint(folder/'file') if push else self.endpoint(remote/'file')
                destination = self.endpoint(remote) if push else local_endpoint(folder)
                request = self.move_request([{'endpoint':source, 'mode':'entry'}], destination)
                c = self.client(self.local_fault_env(folder/'file', XSYNC_FAULT_EACH_READ_DELAY_US='100000'))
                c.send(request); self.wait_move_verification(c)
                contender = self.local/'contender'; contender.write_text('another job')
                blocked, result = self.copy_job([{'endpoint':local_endpoint(contender),'mode':'entry'}], self.endpoint(remote))
                self.assertNotEqual(result['status'], 'success', blocked.events)
                self.assertTrue(any(e['type']=='error' and e.get('operation')=='destination_lock' and e.get('endpoint')=='ssh' for e in blocked.events), blocked.events)
                self.assertEqual(c.finish()['status'], 'success', c.events)
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"contender").exists()))', remote))
                # A completed session releases its remote locks.
                after, result = self.copy_job([{'endpoint':local_endpoint(contender),'mode':'entry'}], self.endpoint(remote))
                self.assertEqual(result['status'], 'success', after.events)

    def test_move_remote_cancel_and_helper_loss_keep_source(self):
        for crash in (False, True):
            with self.subTest(crash=crash):
                remote = self.root/(self.local.name + '-move-stop-' + str(crash))
                remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
                source = self.local/('source-'+str(crash)); source.write_bytes(b'a'*(20*1024*1024))
                request = self.move_request([{'endpoint':local_endpoint(source),'mode':'entry'}], self.endpoint(remote))
                c = self.client(self.local_fault_env(source, XSYNC_FAULT_EACH_READ_DELAY_US='100000'))
                c.send(request); self.wait_move_verification(c)
                if crash:
                    # Kill only the helper owning this test's destination lock.
                    remote_code('import pathlib,os,signal,sys; root=os.path.realpath(sys.argv[1]); victims=[]\nfor p in pathlib.Path("/proc").iterdir():\n if not p.name.isdigit(): continue\n try:\n  cmd=(p/"cmdline").read_bytes(); fds=p/"fd"\n  if b"--app" in cmd and any(os.path.realpath(f)==root for f in fds.iterdir()): victims.append(int(p.name))\n except (OSError,PermissionError): pass\nfor pid in victims: os.kill(pid,signal.SIGKILL)\nprint(len(victims))', remote)
                else: c.send({'id':'cancel', 'op':'cancel', 'job_id':'ssh'})
                result = c.finish()
                self.assertNotEqual(result['status'], 'success', c.events)
                self.assertTrue(source.exists())
                self.assertTrue(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/sys.argv[2]).stat().st_size==20*1024*1024))', remote, source.name))
                contender = self.local/'after-stop'; contender.write_text('released')
                after, result = self.copy_job([{'endpoint':local_endpoint(contender),'mode':'entry'}], self.endpoint(remote))
                self.assertEqual(result['status'], 'success', after.events)

    def test_move_remote_contents_and_hardlinks(self):
        remote = self.root/(self.local.name+'-move-contents')
        remote_code('import pathlib,sys,os; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"a").write_text("only copy"); os.link(p/"a",p/"b")', remote)
        destination = self.local/'contents'; destination.mkdir()
        c, result = self.move_job([{'endpoint':self.endpoint(remote),'mode':'contents'}], local_endpoint(destination))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((destination/'a').read_text(), 'only copy')
        self.assertEqual((destination/'b').read_text(), 'only copy')
        self.assertEqual(remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([p.is_dir(),len(list(p.iterdir()))]))', remote), [True,0])

    def test_move_rejects_missing_old_and_malformed_remote_lease_versions(self):
        remote = self.root/(self.local.name+'-move-version')
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        source = self.local/'file'; source.write_text('only copy')
        helper, marker = remote/'helper', remote/'unexpected-mutation'
        for version in (None, 'old', True):
            with self.subTest(version=version):
                # Relay the actual browse protocol, changing only negotiation.
                script = '\n'.join([
                    '#!/usr/bin/python3', 'import json,sys,os,threading,subprocess,pathlib',
                    'p=subprocess.Popen(["/usr/local/bin/xs","--app"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)',
                    'p.stdin.write(sys.stdin.buffer.readline()); p.stdin.flush()',
                    'caps=json.loads(p.stdout.readline()); caps["move_lease"]='+repr(version),
                    'print(json.dumps(caps),flush=True)',
                    'request=sys.stdin.buffer.readline()',
                    'if request and json.loads(request).get("op")=="_native_transfer": pathlib.Path('+repr(str(marker))+').touch()',
                    'p.stdin.write(request); p.stdin.flush()',
                    'def feed():',
                    ' while True:',
                    '  data=os.read(0,65536)',
                    '  if not data: p.stdin.close(); return',
                    '  p.stdin.write(data); p.stdin.flush()',
                    'threading.Thread(target=feed,daemon=True).start()',
                    'while True:',
                    ' data=os.read(p.stdout.fileno(),65536)',
                    ' if not data: break',
                    ' sys.stdout.buffer.write(data); sys.stdout.buffer.flush()',
                    'sys.exit(p.wait())', ''])
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)', helper, script)
                c, result = self.move_job([{'endpoint':local_endpoint(source),'mode':'entry'}], self.endpoint(remote,helper_path=str(helper)))
                self.assertNotEqual(result['status'], 'success', c.events)
                self.assertIn('unsupported_feature', self.errors(c))
                self.assertEqual(source.read_text(), 'only copy')
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(any((pathlib.Path(sys.argv[1])/n).exists() for n in ("unexpected-mutation","file"))))', remote))

    def test_move_interactive_keep_both_and_cancel_in_both_directions(self):
        for push in (True,False):
            for decision in ('keep_both','cancel'):
                with self.subTest(push=push,decision=decision):
                    remote = self.root/(self.local.name+'-move-conflict-'+str(push)+decision)
                    local = self.local/(str(push)+decision); local.mkdir()
                    remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"tree").mkdir(); (p/"tree"/sys.argv[2]).write_text(sys.argv[3]); (p/"tree"/"link").symlink_to("literal:target") if sys.argv[2]=="file" else None', remote, 'sentinel' if push else 'file', 'good existing' if push else 'incoming')
                    (local/'tree').mkdir(); (local/'tree'/('file' if push else 'sentinel')).write_text('incoming' if push else 'good existing')
                    if push:
                        (local/'tree'/'link').symlink_to('literal:target')
                        if sys.platform=='darwin': os.chmod(local/'tree'/'link',0o777,follow_symlinks=False)
                    source = local_endpoint(local/'tree') if push else self.endpoint(remote/'tree')
                    destination = self.endpoint(remote) if push else local_endpoint(local)
                    c = self.client(); c.send(self.move_request([{'endpoint':source,'mode':'entry'}], destination, 'ask'))
                    kept = 'kept\n*?:tree'
                    result = self.finish_conflicts(c, lambda e:self.conflict_reply(c,e,decision,**({'destination_name':{'bytes_hex':os.fsencode(kept).hex()}} if decision=='keep_both' else {})))
                    if decision=='keep_both':
                        self.assertEqual(result['status'], 'success', [e for e in c.events if e['type'] in ('move_result','error')])
                        moves = [e for e in c.events if e['type']=='move_result']
                        self.assertEqual(len(moves),3); self.assertTrue(all(e['removed'] for e in moves))
                        if push:
                            self.assertFalse((local/'tree').exists())
                            self.assertEqual(remote_json('import pathlib,sys,json,os; p=pathlib.Path(sys.argv[1]); print(json.dumps([(p/"tree"/"sentinel").read_text(),(p/sys.argv[2]/"file").read_text(),os.readlink(p/sys.argv[2]/"link")]))',remote,kept),['good existing','incoming','literal:target'])
                        else:
                            self.assertEqual((local/'tree'/'sentinel').read_text(),'good existing')
                            self.assertEqual((local/kept/'file').read_text(),'incoming')
                            self.assertEqual(os.readlink(local/kept/'link'),'literal:target')
                            self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"tree").exists()))',remote))
                    else:
                        self.assertEqual(result['status'],'cancellation',c.events)
                        if push: self.assertEqual((local/'tree'/'file').read_text(),'incoming')
                        else: self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"tree"/"file").read_text()))',remote),'incoming')

    def test_move_remote_disk_full_recovers_unknown_outcomes_without_source_removal(self):
        remote = self.root/(self.local.name+'-move-full')
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("good existing")', remote)
        source = self.local/'file'; source.write_bytes(b'incoming'*65536)
        helper = self.fault_helper(remote,XSYNC_FAULT_WRITE_ERROR=str(errno.ENOSPC))
        c,result = self.move_job([{'endpoint':local_endpoint(source),'mode':'entry'}],self.endpoint(remote,helper_path=helper))
        self.assertNotEqual(result['status'],'success',c.events)
        self.assertEqual(source.read_bytes(),b'incoming'*65536)
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"file").read_text()))',remote),'good existing')
        outcomes = [e for e in c.events if e['type']=='move_result']
        self.assertEqual(len(outcomes),1,c.events)
        self.assertFalse(outcomes[0]['removed'])
        self.assertIn('disk_full',self.errors(c))

    def test_move_real_ssh_both_directions_and_literal_paths(self):
        remote = self.root/self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        source = self.local/'tree\n*?'; source.mkdir(); (source/'nested').mkdir(); (source/'nested'/'file').write_text('only copy')
        c, result = self.move_job([{'endpoint':local_endpoint(source),'mode':'entry'}], self.endpoint(remote))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(source.exists())
        moves = [e for e in c.events if e['type']=='move_result']
        self.assertEqual(len(moves), 3)
        self.assertTrue(all(e['copied'] and e['removed'] and not e['remaining'] for e in moves))
        target = self.local/'returned'; target.mkdir()
        c, result = self.move_job([{'endpoint':self.endpoint(remote/source.name),'mode':'entry', 'destination_name':{'bytes_hex':b'mapped-\ncolon:name'.hex()}}], local_endpoint(target))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((target/'mapped-\ncolon:name'/'nested'/'file').read_text(), 'only copy')
        self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', remote/source.name))
        self.assertTrue(all(e['source_endpoint']=='ssh' and e['removed'] for e in c.events if e['type']=='move_result'))

    def test_move_remote_metadata_failure_preserves_only_source_copy(self):
        remote = self.root/self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        source = self.local/'file'; source.write_text('only copy')
        helper = self.fault_helper(remote, XSYNC_FAULT_FUTIMENS_ERROR=str(errno.EPERM))
        c, result = self.move_job([{'endpoint':local_endpoint(source),'mode':'entry'}], self.endpoint(remote, helper_path=helper))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertEqual(source.read_text(), 'only copy')
        move = next(e for e in c.events if e['type']=='move_result')
        self.assertFalse(move['removed'] or move['destination_completed'])
        self.assertTrue(move['remaining'])

    def test_move_remote_source_removal_failure_reports_retained_copy(self):
        remote = self.root/self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("only copy")', remote)
        helper = self.fault_helper(remote, XSYNC_FAULT_UNLINK_NAME='file')
        destination = self.local/'destination'; destination.mkdir()
        c, result = self.move_job([{'endpoint':self.endpoint(remote/'file', helper_path=helper),'mode':'entry'}], local_endpoint(destination))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertEqual((destination/'file').read_text(), 'only copy')
        self.assertTrue(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"file").exists()))', remote))
        move = next(e for e in c.events if e['type']=='move_result')
        self.assertTrue(move['copied'] and move['remaining'])
        self.assertFalse(move['removed'])

    def test_reference_cli_remote_move_without_tty(self):
        remote = self.root/self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        _, result = self.run_job('probe', self.endpoint(remote)); self.assertEqual(result['status'], 'success')
        profile_file = self.local/'move-profile.json'; profile_file.write_text(json.dumps(self.endpoint(remote, host_key_policy='strict')['connection']))
        source = self.local/'file'; source.write_text('only copy')
        for args in (['move', str(source), str(remote), '--on-conflict', 'replace'],
                     ['move', str(remote/'file'), str(self.local), '--direction', 'pull', '--on-conflict', 'replace']):
            completed = subprocess.run([sys.executable, str(ROOT/'tools/app_client.py'), '--binary', str(BINARY),
                '--ssh-profile', str(profile_file), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            events = [json.loads(line) for line in completed.stdout.splitlines()]
            self.assertTrue(any(e['type']=='move_result' and e['removed'] for e in events))
        self.assertEqual(source.read_text(), 'only copy')
        self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"file").exists()))', remote))

    def test_remote_action_scan_and_metadata_failures_are_truthful(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"tree").mkdir(); [(p/"tree"/str(n)).write_text("keep") for n in range(4)]; (p/"file").write_text("keep")', remote)
        helper = self.fault_helper(remote / 'tree', XSYNC_FAULT_LIST_AFTER='1')
        c, result = self.filesystem_action('delete', remote, ['tree'], recursive=True, connection={'helper_path':helper})
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps(len(list((pathlib.Path(sys.argv[1])/"tree").iterdir()))))', remote), 4)
        self.assertFalse(any(e['changed'] for e in c.events if e['type'] == 'action_result'))
        helper = self.fault_helper(remote / 'file', XSYNC_FAULT_FUTIMENS_ERROR=str(errno.EPERM))
        c, result = self.filesystem_action('metadata', remote, ['file'], mode=0o640,
            mtime={'seconds':'1','nanoseconds':'0'}, connection={'helper_path':helper})
        self.assertEqual(result['status'], 'partial_failure', c.events)
        action = next(e for e in c.events if e['type'] == 'action_result')
        self.assertEqual(action['status'], 'partial_failure')
        self.assertTrue(action['changed'])
        self.assertFalse(action['metadata_complete'])
        self.assertEqual(action['endpoint'], 'ssh')
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"file").stat().st_mode & 511))', remote), 0o640)

    def test_filesystem_actions_remote_workflow_and_refresh(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        c, result = self.filesystem_action('mkdir', remote, [b'raw-\xff\n*?'], mode=0o750)
        self.assertEqual(result['status'], 'success', c.events)
        c, result = self.filesystem_action('rename', remote, [b'raw-\xff\n*?'], destination_name=b'renamed-\xfe')
        self.assertEqual(result['status'], 'success', c.events)
        c, result = self.filesystem_action('metadata', remote, [b'renamed-\xfe'], mode=0o700,
            mtime={'seconds':'1600000000', 'nanoseconds':'123456789'})
        self.assertEqual(result['status'], 'success', c.events)
        self.assertTrue(all(e['endpoint'] == 'ssh' for e in c.events if e['type'] in ('action_result', 'invalidate')))
        remote_code('import os,sys; p=os.fsencode(sys.argv[1]); os.mkdir(p+b"/renamed-\\xfe/sub"); open(p+b"/renamed-\\xfe/sub/data","w").write("delete"); os.symlink(p, p+b"/renamed-\\xfe/outside-link")', remote)
        c, result = self.filesystem_action('delete', remote, [b'renamed-\xfe'], recursive=True)
        self.assertEqual(result['status'], 'success', c.events)
        outcomes = [e for e in c.events if e['type'] == 'action_result']
        self.assertEqual(len(outcomes), 4)
        self.assertTrue(all(e['removed'] and not e['undoable'] for e in outcomes))
        c, result = self.run_job('list', self.endpoint(remote))
        self.assertEqual(result['status'], 'success')
        self.assertEqual([entry for e in c.events if e['type'] == 'entries' for entry in e['entries']], [])

    def test_reference_cli_remote_actions_without_tty(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        _, result = self.run_job('probe', self.endpoint(remote))
        self.assertEqual(result['status'], 'success')
        profile = self.endpoint(remote, host_key_policy='strict')['connection']
        profile_file = self.local / 'profile.json'
        profile_file.write_text(json.dumps(profile))
        for args in (['mkdir', str(remote), 'new', '--mode', '750'],
                     ['rename', str(remote), 'new', 'renamed'],
                     ['metadata', str(remote), 'renamed', '--mode', '700'],
                     ['delete', str(remote), 'renamed']):
            completed = subprocess.run([sys.executable, str(ROOT/'tools/app_client.py'), '--binary', str(BINARY),
                '--ssh-profile', str(profile_file), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            events = [json.loads(line) for line in completed.stdout.splitlines()]
            self.assertEqual(events[-1]['status'], 'success')
            self.assertTrue(any(e['type'] == 'action_result' and e['endpoint'] == 'ssh' for e in events))
        self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"renamed").exists()))', remote))

    def test_filesystem_actions_remote_stale_leaf_and_replace(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"a").write_text("first"); (p/"b").write_text("second")', remote)
        c, result = self.filesystem_action('rename', remote, ['a'], destination_name='b', replace=True)
        self.assertEqual(result['status'], 'success', c.events)
        c, result = self.run_job('lstat', self.endpoint(remote))
        parent = next(e['entry']['revision'] for e in c.events if e['type'] == 'entry')
        c, result = self.run_job('list', self.endpoint(remote))
        entry = next(entry for e in c.events if e['type'] == 'entries' for entry in e['entries'])
        remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/"b").write_text("changed only copy")', remote)
        c, result = self.run_job('delete', self.endpoint(remote), parent_revision=parent, recursive=False,
            items=[{'name':entry['name'], 'expected_revision':entry['revision']}])
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertIn('stale_entry', [e.get('reason') for e in c.events if e['type'] == 'error'])
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/"b").read_text()))', remote), 'changed only copy')
        self.assertEqual([e['status'] for e in c.events if e['type'] == 'action_result'], ['failure'])

    def test_filesystem_action_capability_required_before_mutation(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        c, result = self.run_job('lstat', self.endpoint(remote))
        parent = next(e['entry']['revision'] for e in c.events if e['type'] == 'entry')
        helper, marker = remote / 'helper', remote / 'unexpected-operation'
        for feature in (None, False, 1, '2'):
            with self.subTest(feature=feature):
                caps = {'schema':'1','id':'remote-hello','seq':'1','type':'capabilities','version':'old','operations':['mkdir']}
                if feature is not None: caps['filesystem_actions'] = feature
                script = '#!/usr/bin/python3\nimport sys,json,pathlib\nsys.stdin.readline()\nprint('+repr(json.dumps(caps))+',flush=True)\nif sys.stdin.readline(): pathlib.Path('+repr(str(marker))+').touch()\n'
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)', helper, script)
                c, result = self.run_job('mkdir', self.endpoint(remote, helper_path=str(helper)), parent_revision=parent,
                    items=[{'name':{'bytes_hex':b'new'.hex()},'expected_revision':{'exists':False}}])
                self.assertEqual(result['status'], 'failure', c.events)
                self.assertIn('unsupported_feature', self.errors(c))
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker))

    def test_mapping_capability_required_before_remote_mutation(self):
        source = self.local / 'file'; source.write_text('incoming')
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        helper, marker = remote / 'helper', remote / 'unexpected-operation'
        for feature in (None, False, 'true'):
            with self.subTest(feature=feature):
                capabilities = {'schema': '1', 'id': 'remote-hello', 'seq': '1', 'type': 'capabilities',
                                'version': 'old', 'operations': ['copy'], 'transfer_bridge': '3', 'typed_transfer_errors': True}
                if feature is not None: capabilities['selection_mappings'] = feature
                script = '#!/usr/bin/python3\nimport sys,json,pathlib\nsys.stdin.readline()\nprint('+repr(json.dumps(capabilities))+',flush=True)\nif sys.stdin.readline(): pathlib.Path('+repr(str(marker))+').touch()\n'
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)', helper, script)
                selection = {'endpoint': local_endpoint(source), 'mode': 'entry', 'destination_name': {'bytes_hex': b'renamed'.hex()}}
                c, result = self.copy_job([selection], self.endpoint(remote, helper_path=str(helper)))
                self.assertEqual(result['status'], 'failure', c.events)
                self.assertIn('unsupported_feature', self.errors(c))
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker))

    def test_nested_failure_retry_requests_preserve_destination_in_both_directions(self):
        for push in (True, False):
            with self.subTest(push=push):
                source = self.local / ('source-' + str(push)); source.mkdir()
                (source / 'outer').mkdir(); (source / 'outer' / 'file').write_text('nested incoming bytes')
                (source / 'good').write_text('completed sibling')
                remote = self.root / (self.local.name + '-retry-' + str(push))
                if push:
                    remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"outer").mkdir(); (p/"outer"/"file").write_text("old nested copy"); (p/"file").write_text("unselected root sibling")', remote)
                    helper = self.fault_helper(remote / 'outer', XSYNC_FAULT_WRITE_ERROR='5')
                    selection = {'endpoint': local_endpoint(source), 'mode': 'contents'}
                    destination = self.endpoint(remote, helper_path=helper)
                else:
                    remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"outer").mkdir(); (p/"outer"/"file").write_text("nested incoming bytes"); (p/"good").write_text("completed sibling")', remote)
                    helper = self.fault_helper(remote / 'outer' / 'file', XSYNC_FAULT_READ_ERROR='1')
                    destination_path = self.local / 'destination'; destination_path.mkdir()
                    (destination_path / 'outer').mkdir(); (destination_path / 'outer' / 'file').write_text('old nested copy')
                    (destination_path / 'file').write_text('unselected root sibling')
                    selection = {'endpoint': self.endpoint(remote, helper_path=helper), 'mode': 'contents'}
                    destination = local_endpoint(destination_path)
                options = {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}
                original = {'id': 'ssh', 'op': 'copy', 'sources': [selection], 'destination': destination, 'options': options}
                c, result = self.copy_job(original['sources'], destination)
                self.assertEqual(result['status'], 'partial_failure', c.events)
                view = inventory(c.events, 'ssh')
                self.assertEqual(view.items[b'outer'.hex()]['status'], 'success')
                self.assertEqual(view.items[b'outer/file'.hex()]['status'], 'failure')
                with self.assertRaises(ValueError): view.retry_selections({'local': local_endpoint(source), 'ssh': self.endpoint(remote)})
                retries = view.retry_requests(original)
                self.assertEqual(len(retries), 1)
                self.assertEqual(retries[0]['destination']['path']['bytes_hex'], os.fsencode((remote if push else destination_path) / 'outer').hex())
                remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', helper, '#!/bin/sh\nexec /usr/local/bin/xs "$@"\n')
                _, retried = self.copy_job(retries[0]['sources'], retries[0]['destination'])
                self.assertEqual(retried['status'], 'success')
                if push:
                    contents = remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([(p/"outer"/"file").read_text(),(p/"file").read_text(),(p/"good").read_text()]))', remote)
                else:
                    contents = [(destination_path / 'outer' / 'file').read_text(), (destination_path / 'file').read_text(), (destination_path / 'good').read_text()]
                self.assertEqual(contents, ['nested incoming bytes', 'unselected root sibling', 'completed sibling'])

    def test_source_revalidation_keeps_native_vanished_error_after_retry(self):
        remote = self.root / self.local.name
        source, marker = remote / 'file', remote / 'reading'
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_bytes(b"a"*4096)', remote)
        dest = self.local / 'destination'; dest.mkdir()
        (dest / 'file').write_text('old good copy')
        helper = self.fault_helper(source, XSYNC_FAULT_READ_NOTIFY=str(marker), XSYNC_FAULT_READ_DELAY_US='1000000')
        c = self.client()
        _, probe = self.run_job('probe')
        self.assertEqual(probe['status'], 'success')
        c.send({'id': 'ssh', 'op': 'copy', 'sources': [{'endpoint': self.endpoint(source, helper_path=helper), 'mode': 'entry'}],
                'destination': local_endpoint(dest), 'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}})
        for attempt in (1, 2):
            deadline = time.monotonic() + 8
            while not remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', str(marker)+f'.{attempt}'):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            if attempt == 1:
                remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(b"b"*4096)', source)
            else:
                remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).unlink()', source)
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error' and e['operation'] == 'revalidate_source')
        self.assertEqual((error['category'], error['native_code'], error['endpoint'], error['side']), ('vanished_source', '2', 'ssh', 'source'))
        self.assertEqual(error['path']['bytes_hex'], os.fsencode(source).hex())
        self.assertEqual((dest / 'file').read_text(), 'old good copy')
        self.assertEqual(list(dest.iterdir()), [dest / 'file'])
        self.assertEqual(next(e for e in c.events if e['type'] == 'item_result')['status'], 'failure')

    def test_remote_source_errors_support_explicit_retry_without_logs(self):
        source = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); '
                    '[(p/f"file-{i:02}").write_bytes(b"incoming bytes"*100) for i in range(24)]', source)
        dest = self.local / 'destination'
        dest.mkdir()
        for i in range(24): (dest / f'file-{i:02}').write_text('old good copy')
        helper = self.fault_helper(source, XSYNC_FAULT_READ_ERROR='1')
        c, result = self.copy_job([{'endpoint': self.endpoint(source, helper_path=helper), 'mode': 'contents'}], local_endpoint(dest), jobs='8')
        self.assertEqual(result['status'], 'partial_failure', c.events)
        errors = [e for e in c.events if e['type'] == 'error' and e['operation'] == 'read_source']
        failed_paths = {bytes.fromhex(e['path']['bytes_hex']) for e in errors}
        self.assertEqual(failed_paths, {os.fsencode(source / f'file-{i:02}') for i in range(24)})
        self.assertTrue(all(e['category'] == 'content' and e['side'] == 'source' and
                            e['endpoint'] == 'ssh' and e['native_code'] == '5' for e in errors))
        self.assertTrue(all(p.read_text() == 'old good copy' for p in dest.iterdir()))
        view = inventory(c.events, 'ssh')
        self.assertEqual(sum(item['status'] == 'failure' for item in view.items.values()), 24)
        self.assertTrue(all(e['item_id'] in view.items for e in errors))
        retry_sources = view.retry_selections({'ssh': self.endpoint(source)})
        self.assertEqual({bytes.fromhex(s['endpoint']['path']['bytes_hex']) for s in retry_sources}, failed_paths)
        _, retry = self.copy_job(retry_sources, local_endpoint(dest))
        self.assertEqual(retry['status'], 'success')
        self.assertTrue(all(p.read_bytes() == b'incoming bytes'*100 for p in dest.iterdir()))

    def test_remote_inventory_covers_success_skip_and_directory_scan_failure(self):
        source = self.root / self.local.name
        remote_code('import pathlib,sys,os; p=pathlib.Path(sys.argv[1]); p.mkdir(); '
                    '(p/"blocked").mkdir(); (p/"blocked"/"hidden").write_text("unseen"); '
                    '(p/"good").write_text("copied"); (p/"link").symlink_to("good"); os.mkfifo(p/"fifo")', source)
        dest = self.local / 'destination'
        dest.mkdir()
        helper = self.fault_helper(source / 'blocked', XSYNC_FAULT_OPENDIR_ERROR='13')
        c, result = self.copy_job([{'endpoint': self.endpoint(source, helper_path=helper), 'mode': 'contents'}], local_endpoint(dest))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        view = inventory(c.events, 'ssh')
        self.assertEqual(set(view.items), {p.hex() for p in (b'', b'blocked', b'good', b'link', b'fifo')})
        blocked = view.items[b'blocked'.hex()]
        self.assertEqual((blocked['status'], blocked['reason'], blocked['source_endpoint'], blocked['destination_endpoint']),
                         ('failure', 'source_error', 'ssh', 'local'))
        self.assertEqual(view.items[b'good'.hex()]['status'], 'success')
        self.assertEqual(view.items[b'fifo'.hex()]['status'], 'skipped')
        error = next(e for e in c.events if e['type'] == 'error' and e['operation'] == 'scan_source')
        self.assertEqual(error['item_id'], b'blocked'.hex())
        retry = view.retry_selections({'ssh': self.endpoint(source)})
        self.assertEqual(retry, [{'endpoint': self.endpoint(source / 'blocked'), 'mode': 'entry'}])
        c, result = self.copy_job(retry, local_endpoint(dest))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((dest / 'blocked' / 'hidden').read_text(), 'unseen')
        c, result = self.copy_job([{'endpoint': self.endpoint(source), 'mode': 'contents'}], local_endpoint(dest), policy='skip')
        self.assertEqual(result['status'], 'success', c.events)
        view = inventory(c.events, 'ssh')
        self.assertEqual(view.items[b'good'.hex()]['status'], 'skipped')
        self.assertEqual(view.items[b'link'.hex()]['status'], 'skipped')
        helper = self.fault_helper(source, XSYNC_FAULT_OPENDIR_ERROR='13')
        c, result = self.copy_job([{'endpoint': self.endpoint(source, helper_path=helper), 'mode': 'contents'}], local_endpoint(dest))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertEqual(inventory(c.events, 'ssh').items['']['status'], 'failure')

    def test_skip_directory_type_conflict_preserves_file_in_both_directions(self):
        source = self.local / 'directory'
        source.mkdir(); (source / 'child').write_text('incoming')
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"directory").write_text("keep good file")', remote)
        c, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'entry'}], self.endpoint(remote), policy='skip')
        self.assertEqual(result['status'], 'success', c.events)
        view = inventory(c.events, 'ssh')
        self.assertEqual(view.items[b'directory'.hex()]['status'], 'skipped')
        self.assertFalse(any(item['status'] == 'failure' for item in view.items.values()))
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).read_text()))', remote / 'directory'), 'keep good file')
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/"directory").unlink(); (p/"directory").mkdir(); (p/"directory"/"child").write_text("incoming")', remote)
        dest = self.local / 'destination'; dest.mkdir(); (dest / 'directory').write_text('keep good file')
        c, result = self.copy_job([{'endpoint': self.endpoint(remote / 'directory'), 'mode': 'entry'}], local_endpoint(dest), policy='skip')
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual((dest / 'directory').read_text(), 'keep good file')
        self.assertEqual(inventory(c.events, 'ssh').items[b'directory'.hex()]['status'], 'skipped')

    def test_fast_no_write_pulls_keep_authoritative_success_during_teardown(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("incoming")', remote)
        dest = self.local / 'destination'; dest.mkdir(); (dest / 'file').write_text('keep good file')
        for iteration in range(16):
            with self.subTest(iteration=iteration):
                c, result = self.copy_job([{'endpoint': self.endpoint(remote / 'file'), 'mode': 'entry'}], local_endpoint(dest), policy='skip')
                self.assertEqual(result['status'], 'success', c.events)
                self.assertFalse(self.errors(c), c.events)
                self.assertEqual(inventory(c.events, 'ssh').items[b'file'.hex()]['status'], 'skipped')
                self.assertEqual((dest / 'file').read_text(), 'keep good file')

    def test_remote_metadata_error_retains_published_item_outcome(self):
        source = self.local / 'file'
        source.write_text('published bytes')
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        helper = self.fault_helper(remote, XSYNC_FAULT_FUTIMENS_ERROR='1')
        c, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'entry'}], self.endpoint(remote, helper_path=helper))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        item = inventory(c.events, 'ssh').items[b'file'.hex()]
        self.assertEqual((item['status'], item['reason'], item['content_published'], item['metadata_complete']),
                         ('failure', 'metadata_error', True, False))
        self.assertEqual((item['source_endpoint'], item['destination_endpoint']), ('local', 'ssh'))
        self.assertEqual(item['source_path']['bytes_hex'], os.fsencode(source).hex())
        self.assertEqual(item['destination_path']['bytes_hex'], os.fsencode(remote / 'file').hex())
        self.assertTrue(any(e['type'] == 'error' and e['item_id'] == item['item_id'] and e['endpoint'] == 'ssh' for e in c.events))
        data = remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).read_text()))', remote / 'file')
        self.assertEqual(data, 'published bytes')
        assert_scope(self,c.events,remote,'ssh')
        self.assertTrue(any(e['type'] == 'invalidate' and e['path'] == item['destination_path'] and e['endpoint'] == 'ssh' for e in c.events))

    def test_destination_revision_races_preserve_external_files_on_push_and_pull(self):
        source = self.local / 'file'; source.write_text('incoming')
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("old good copy")', remote)
        marker, release = self.root / (self.local.name + '-metadata'), self.root / (self.local.name + '-release')
        helper = self.fault_helper(remote, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker), XSYNC_FAULT_FUTIMENS_RELEASE=str(release))
        c = self.client()
        c.send({'id': 'ssh', 'op': 'copy', 'sources': [{'endpoint': local_endpoint(source), 'mode': 'entry'}],
                'destination': self.endpoint(remote, helper_path=helper),
                'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}})
        while True:
            event = c.read(15)
            if event['type'] == 'auth_prompt': self.response(c, event, 'yes')
            if event['type'] == 'item_stage' and event['stage'] == 'applying_metadata': break
        deadline = time.monotonic() + 3
        while not remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker):
            self.assertLess(time.monotonic(), deadline)
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.unlink(); p.write_text("external writer"); pathlib.Path(sys.argv[2]).touch()', remote / 'file', release)
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error' and e['category'] == 'conflict')
        self.assertEqual((error['operation'], error['native_code'], error['endpoint'], error['side']),
                         ('destination_changed', None, 'ssh', 'destination'))
        self.assertNotEqual(error['expected_revision'], error['observed_revision'])
        self.assertEqual(inventory(c.events, 'ssh').items[b'file'.hex()]['reason'], 'destination_changed')
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).read_text()))', remote / 'file'), 'external writer')
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps(sorted(p.name for p in pathlib.Path(sys.argv[1]).iterdir())))', remote), ['file'])
        # Pause after the local receiver's last revision check to exercise the
        # atomic absent-name publication boundary on an SSH pull too.
        dest = self.local / 'destination'; dest.mkdir()
        marker, release = self.local / 'closed-output', self.local / 'release-close'
        library = self.local / 'fault_io.so'
        args = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared', '-fPIC', str(ROOT / 'tests/fault_io.cpp'), '-o', str(library)]
        if sys.platform != 'darwin': args += ['-ldl']
        subprocess.run(args, check=True, capture_output=True)
        env = dict(os.environ, **{'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD': str(library),
                                  'XSYNC_FAULT_PATH': str(dest.resolve()), 'XSYNC_FAULT_CLOSE_NOTIFY': str(marker),
                                  'XSYNC_FAULT_CLOSE_RELEASE': str(release)})
        c = self.client(env)
        c.send({'id': 'ssh', 'op': 'copy', 'sources': [{'endpoint': self.endpoint(remote / 'file'), 'mode': 'entry'}],
                'destination': local_endpoint(dest),
                'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}})
        deadline = time.monotonic() + 4
        while not marker.exists():
            event = c.read(10)
            if event['type'] == 'auth_prompt': self.response(c, event, 'yes')
            self.assertLess(time.monotonic(), deadline, c.events)
        (dest / 'file').write_text('local external writer'); release.touch()
        result = c.finish()
        self.assertEqual(result['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error' and e['category'] == 'conflict')
        self.assertEqual((error['operation'], error['native_code'], error['endpoint']), ('destination_changed', '17', 'local'))
        self.assertEqual((dest / 'file').read_text(), 'local external writer')
        self.assertEqual([p.name for p in dest.iterdir()], ['file'])
        self.assertFalse(inventory(c.events, 'ssh').items[b'file'.hex()]['content_published'])

    def test_copy_does_not_report_scanning_during_authentication(self):
        self.run_job('probe')
        source = self.local / 'file'
        source.write_text('incoming')
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        c = self.client()
        c.send({'id': 'ssh', 'op': 'copy', 'sources': [{'endpoint': local_endpoint(source), 'mode': 'entry'}],
                'destination': self.endpoint(remote, identity_file=str(self.key),
                                             authentication_timeout_seconds='1', prompt_timeout_seconds='5'),
                'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}})
        while True:
            prompt = c.read(15)
            if prompt['type'] == 'auth_prompt': break
        deadline = time.monotonic() + 1.2
        while time.monotonic() < deadline:
            if b'\n' in c.pending or select.select([c.proc.stdout], [], [], .05)[0]:
                c.read()
        self.assertIsNone(c.proc.poll())
        self.assertFalse(any(e['type'] == 'progress' or (e['type'] == 'phase' and e['phase'] == 'scanning') for e in c.events))
        self.response(c, prompt, PASSPHRASE)
        self.assertEqual(c.finish()['status'], 'success', c.events)
        self.assertEqual(remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text())', remote / 'file').strip(), 'incoming')

    def test_copy_authentication_and_batch_skip_replace(self):
        source = self.local / 'file'
        source.write_text('new')
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("old")', remote)
        selection = [{'endpoint': local_endpoint(source), 'mode': 'entry'}]
        c, result = self.copy_job(selection, self.endpoint(remote, identity_file=str(self.key)), policy='skip', answer=PASSPHRASE)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(remote_code('import pathlib,sys; print((pathlib.Path(sys.argv[1])/"file").read_text())', remote).strip(), 'old')
        self.config.write_text('Host *\n  PreferredAuthentications password\n  PubkeyAuthentication no\n')
        c, result = self.copy_job(selection, self.endpoint(remote, port=AUTH_PORT), answer=PASSWORD)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertEqual(remote_code('import pathlib,sys; print((pathlib.Path(sys.argv[1])/"file").read_text())', remote).strip(), 'new')
        self.assertNotIn(PASSWORD, json.dumps(c.events))

    def test_copy_preflight_errors_and_old_bridge_before_writes(self):
        source = self.local / 'file'
        source.write_text('data')
        selection = [{'endpoint': local_endpoint(source), 'mode': 'entry'}]
        remote = self.root / self.local.name
        c, result = self.copy_job(selection, self.endpoint(remote))
        self.assertEqual(result['status'], 'failure', c.events)
        self.assertIn('missing', self.errors(c))
        self.assertEqual(next(e for e in c.events if e['type'] == 'error')['endpoint'], 'ssh')
        self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', remote))
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"alias").symlink_to(p,target_is_directory=True)', remote)
        c, result = self.copy_job(selection, self.endpoint(remote / 'alias'))
        self.assertEqual(result['status'], 'failure', c.events)
        self.assertIn('not_directory', self.errors(c))
        dest = self.local / 'destination'
        dest.mkdir()
        c, result = self.copy_job([{'endpoint': self.endpoint(remote / 'absent'), 'mode': 'entry'}], local_endpoint(dest))
        self.assertEqual(result['status'], 'failure', c.events)
        self.assertIn('missing', self.errors(c))
        self.assertEqual(list(dest.iterdir()), [])
        helper, marker = remote / 'old-helper', remote / 'unexpected-operation'
        for bridge in ('1', '2', '3'):
            with self.subTest(bridge=bridge):
                capabilities = {'schema': '1', 'id': 'remote-hello', 'seq': '1', 'type': 'capabilities',
                                'version': 'old', 'operations': ['copy'], 'transfer_bridge': bridge}
                script = '#!/usr/bin/python3\nimport sys,json,pathlib\nsys.stdin.readline()\nprint('+repr(json.dumps(capabilities))+',flush=True)\nif sys.stdin.readline(): pathlib.Path('+repr(str(marker))+').touch()\n'
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)', helper, script)
                c, result = self.copy_job(selection, self.endpoint(remote, helper_path=str(helper)))
                self.assertEqual(result['status'], 'failure', c.events)
                self.assertIn('unsupported_feature', self.errors(c))
                self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker))

    def test_copy_local_receiver_partial_failure_retains_native_status(self):
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"blocked").write_text("incoming"); (p/"good").write_text("copied")', remote)
        destination = self.local / 'destination'
        destination.mkdir()
        (destination / 'blocked').mkdir()
        (destination / 'blocked' / 'keep').write_text('protected')
        c, result = self.copy_job([{'endpoint': self.endpoint(remote), 'mode': 'contents'}], local_endpoint(destination))
        self.assertEqual(result['status'], 'partial_failure', c.events)
        self.assertEqual(result['code'], '23')
        self.assertEqual((destination / 'good').read_text(), 'copied')
        self.assertEqual((destination / 'blocked' / 'keep').read_text(), 'protected')
        self.assertNotIn('interrupted', self.errors(c))

    def start_slow_copy(self, push=True):
        self.run_job('probe')
        local = self.local / ('upload' if push else 'download')
        local.mkdir()
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        if push:
            (local / 'blob').write_bytes(b'z'*(8*1024*1024))
            remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/"blob").write_text("old")', remote)
            source, destination = local_endpoint(local / 'blob'), self.endpoint(remote)
        else:
            (local / 'blob').write_text('old')
            remote_code('import pathlib,sys; (pathlib.Path(sys.argv[1])/"blob").write_bytes(b"z"*(8*1024*1024))', remote)
            source, destination = self.endpoint(remote / 'blob'), local_endpoint(local)
        c = self.client()
        c.send({'id': 'ssh', 'op': 'copy', 'sources': [{'endpoint': source, 'mode': 'entry'}],
                'destination': destination, 'options': {'on_conflict': 'replace',
                'preserve_times': True, 'preserve_permissions': True, 'bandwidth_bytes_per_second': '125000'}})
        while True:
            event = c.read()
            if event['type'] == 'result':
                self.fail('slow copy ended before cancellation: '+repr(c.events))
            if event['type'] == 'progress' and int(event['wire_bytes']) > 131072:
                if push:
                    self.assertEqual(event['logical_bytes_completed'], '0')
                    self.assertEqual(event['files_completed'], '0')
                return c, local, remote

    def assert_remote_copy_stopped(self, remote):
        deadline = time.monotonic()+6
        while time.monotonic() < deadline:
            active = remote_json('import pathlib,json\nactive=[]\nfor p in pathlib.Path("/proc").iterdir():\n try:\n  if p.name.isdigit() and (p/"cmdline").read_bytes().startswith(b"/usr/local/bin/xs\\0--app"): active.append(int(p.name))\n except FileNotFoundError: pass\nprint(json.dumps(active))')
            if not active:
                break
            time.sleep(0.1)
        else:
            self.fail('remote app writer survived connection loss: '+repr(active))
        self.assertEqual(remote_code('import pathlib,sys; print((pathlib.Path(sys.argv[1])/"blob").read_text())', remote).strip(), 'old')
        self.assertEqual(remote_json('import pathlib,sys,json; print(json.dumps(sorted(p.name for p in pathlib.Path(sys.argv[1]).iterdir())))', remote), ['blob'])

    def test_copy_cancel_and_control_loss_preserve_atomic_outputs(self):
        for push in (True, False):
            with self.subTest(push=push):
                # Use a separate test-directory for each direction.
                if not push:
                    self.tmp = tempfile.TemporaryDirectory(dir=LOCAL_TMP, prefix='app-profile-')
                    self.addCleanup(self.tmp.cleanup)
                    self.local = pathlib.Path(self.tmp.name)
                c, local, remote = self.start_slow_copy(push)
                if push:
                    c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'ssh'})
                else:
                    c.proc.stdin.close()
                result = c.finish()
                self.assertEqual(result['status'], 'cancellation', c.events)
                self.assertEqual(result['cleanup'], 'unknown')
                if push:
                    self.assertTrue(any(e['type'] == 'cancel_ack' and e['accepted'] for e in c.events))
                    self.assert_remote_copy_stopped(remote)
                else:
                    self.assertEqual((local / 'blob').read_text(), 'old')
                    self.assertEqual(sorted(p.name for p in local.iterdir()), ['blob'])

    def test_copy_overlap_rejected_browsing_independent_and_parent_loss(self):
        c, _, remote = self.start_slow_copy()
        source = self.local / 'extra'
        source.write_text('extra')
        other, result = self.copy_job([{'endpoint': local_endpoint(source), 'mode': 'entry'}], self.endpoint(remote))
        self.assertEqual(result['status'], 'failure', other.events)
        self.assertIn('conflict', self.errors(other))
        listing, result = self.run_job('list', self.endpoint(remote))
        self.assertEqual(result['status'], 'success', listing.events)
        c.proc.kill()
        c.proc.wait(timeout=5)
        self.assert_remote_copy_stopped(remote)

    def test_cancel_one_ssh_copy_preserves_another_remote_writer_and_options(self):
        first, _, remote_first = self.start_slow_copy()
        source = self.local / 'independent'; source.write_bytes(b'independent bytes' * 8192)
        source.chmod(0o600)
        stamp = 1600000000123456789; os.utime(source, ns=(stamp, stamp))
        destination = self.root / (self.local.name + '-second')
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"independent").write_text("old"); (p/"independent").chmod(0o444); (p/".independent.ABC123").write_text("unrelated temporary-looking file")', destination)
        marker, release = self.root / (self.local.name + '-second-metadata'), self.root / (self.local.name + '-second-release')
        helper = self.fault_helper(destination, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker), XSYNC_FAULT_FUTIMENS_RELEASE=str(release))
        second = self.client()
        second.send({'id': 'ssh', 'op': 'copy', 'sources': [{'endpoint': local_endpoint(source), 'mode': 'entry'}],
                     'destination': self.endpoint(destination, helper_path=helper),
                     'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': False,
                                 'jobs': '2', 'bandwidth_bytes_per_second': '0'}})
        while True:
            event = second.read(15)
            if event['type'] == 'auth_prompt': self.response(second, event, 'yes')
            if event['type'] == 'item_stage' and event['stage'] == 'applying_metadata': break
        deadline = time.monotonic() + 3
        while not remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker):
            self.assertLess(time.monotonic(), deadline)
        staged = remote_json('import pathlib,sys,json; p=next(p for p in pathlib.Path(sys.argv[1]).iterdir() if p.name not in ("independent",".independent.ABC123")); s=p.stat(); print(json.dumps([p.name,s.st_dev,s.st_ino]))', destination)
        before = time.monotonic()
        first.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'ssh'})
        self.assertEqual(first.finish()['status'], 'cancellation', first.events)
        self.assertLess(time.monotonic() - before, 5)
        self.assertIsNone(second.proc.poll())
        after = remote_json('import pathlib,sys,json; s=pathlib.Path(sys.argv[1]).stat(); print(json.dumps([s.st_dev,s.st_ino]))', destination / staged[0])
        self.assertEqual(after, staged[1:])
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).touch()', release)
        self.assertEqual(second.finish()['status'], 'success', second.events)
        self.assertFalse(any(e['type'] in ('error', 'cancel_ack') for e in second.events))
        actual = remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); f=p/"independent"; s=f.stat(); print(json.dumps([f.read_bytes().hex(),s.st_mode&0o777,s.st_mtime_ns,(p/".independent.ABC123").read_text(),sorted(q.name for q in p.iterdir())]))', destination)
        self.assertEqual(actual, [source.read_bytes().hex(), 0o444, stamp, 'unrelated temporary-looking file',
                                  ['.independent.ABC123', 'independent']])
        items = inventory(second.events, 'ssh').items
        self.assertEqual(set(items), {b'independent'.hex()})
        self.assertEqual((items[b'independent'.hex()]['status'], items[b'independent'.hex()]['bytes_processed']),
                         ('success', str(source.stat().st_size)))
        self.assert_remote_copy_stopped(remote_first)

    def test_replaced_remote_staging_entry_is_preserved_and_not_published(self):
        source = self.local / 'file'; source.write_text('incoming')
        destination = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"file").write_text("old good copy")', destination)
        marker, release = self.root / (self.local.name + '-metadata'), self.root / (self.local.name + '-release')
        helper = self.fault_helper(destination, XSYNC_FAULT_FUTIMENS_NOTIFY=str(marker), XSYNC_FAULT_FUTIMENS_RELEASE=str(release))
        c = self.client()
        c.send({'id': 'ssh', 'op': 'copy', 'sources': [{'endpoint': local_endpoint(source), 'mode': 'entry'}],
                'destination': self.endpoint(destination, helper_path=helper),
                'options': {'on_conflict': 'replace', 'preserve_times': True, 'preserve_permissions': True}})
        while True:
            event = c.read(15)
            if event['type'] == 'auth_prompt': self.response(c, event, 'yes')
            if event['type'] == 'item_stage' and event['stage'] == 'applying_metadata': break
        deadline = time.monotonic() + 3
        while not remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker):
            self.assertLess(time.monotonic(), deadline)
        staged = remote_json('import pathlib,sys,json; p=next(p for p in pathlib.Path(sys.argv[1]).iterdir() if p.name!="file"); p.unlink(); p.write_text("external staging occupant"); s=p.stat(); pathlib.Path(sys.argv[2]).touch(); print(json.dumps([p.name,s.st_dev,s.st_ino]))', destination, release)
        self.assertEqual(c.finish()['status'], 'partial_failure', c.events)
        error = next(e for e in c.events if e['type'] == 'error')
        self.assertEqual((error['category'], error['reason'], error['endpoint'], error['native_code']),
                         ('conflict', 'temporary_output_changed', 'ssh', None))
        item = inventory(c.events, 'ssh').items[b'file'.hex()]
        self.assertEqual((item['status'], item['reason'], item['content_published']),
                         ('failure', 'temporary_output_changed', False))
        actual = remote_json('import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); s=(p/sys.argv[2]).stat(); print(json.dumps([(p/"file").read_text(),(p/sys.argv[2]).read_text(),s.st_dev,s.st_ino,sorted(q.name for q in p.iterdir())]))', destination, staged[0])
        self.assertEqual(actual, ['old good copy', 'external staging occupant', *staged[1:], sorted(['file', staged[0]])])

    def test_copy_connection_loss_is_typed_and_preserves_good_output(self):
        c, _, remote = self.start_slow_copy()
        table = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,command=']).decode()
        rows = [line.strip().split(None, 2) for line in table.splitlines()]
        worker = next(int(row[0]) for row in rows if int(row[1]) == c.proc.pid)
        ssh = next(int(row[0]) for row in rows if int(row[1]) == worker and row[2].startswith('/usr/bin/ssh '))
        os.kill(ssh, signal.SIGKILL)
        result = c.finish()
        self.assertEqual(result['status'], 'failure', c.events)
        self.assertIn('network', self.errors(c))
        self.assertEqual(result['cleanup'], 'unknown')
        self.assert_remote_copy_stopped(remote)

    def test_copy_closed_event_consumer_stops_remote_writer(self):
        c, _, remote = self.start_slow_copy()
        c.proc.stdout.close()
        c.proc.wait(timeout=6)
        self.assertNotEqual(c.proc.returncode, 0)
        self.assert_remote_copy_stopped(remote)

    def test_reference_cli_copy_push_pull(self):
        self.run_job('probe')
        profile = self.local / 'profile.json'
        connection = self.endpoint()['connection']
        connection['host_key_policy'] = 'strict'
        profile.write_text(json.dumps(connection))
        source = self.local / 'one'
        source.write_text('reference-copy')
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        destination = self.local / 'download'
        destination.mkdir()
        for direction, src, dst in (('push', source, remote), ('pull', remote / 'one', destination)):
            result = subprocess.run([sys.executable, str(ROOT/'tools/app_client.py'), '--binary', str(BINARY),
                                     '--ssh-profile', str(profile), 'copy', '--direction', direction,
                                     '--on-conflict', 'replace', str(src), str(dst)],
                                    capture_output=True, text=True, timeout=15, start_new_session=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            events = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(events[-1]['status'], 'success')
            self.assertFalse(any(e['type'] == 'transfer_ready' for e in events))
        self.assertEqual((destination / 'one').read_text(), 'reference-copy')

    def test_copy_invalid_utf8_identities_when_filesystem_supports_them(self):
        import errno
        name = b'invalid-\xff'
        destination = self.local / 'raw download'
        destination.mkdir()
        raw = os.fsencode(destination) + b'/' + name
        try:
            with open(raw, 'wb'): pass
            os.unlink(raw)
        except OSError as error:
            if error.errno in (errno.EILSEQ, getattr(errno, 'EFTYPE', 79)):
                self.skipTest('host filesystem rejects invalid UTF-8 names')
            raise
        source = os.fsencode(self.root / 'remote source') + b'/' + name
        c, result = self.copy_job([{'endpoint': self.endpoint(source), 'mode': 'entry'}], local_endpoint(destination))
        self.assertEqual(result['status'], 'success', c.events)
        with open(raw, 'rb') as file: self.assertEqual(file.read(), b'hello')
        self.assertTrue(any(e['type'] == 'item_update' and bytes.fromhex(e['path']['bytes_hex']).endswith(name) for e in c.events))
        remote = self.root / self.local.name
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', remote)
        c, result = self.copy_job([{'endpoint': local_endpoint(raw), 'mode': 'entry'}], self.endpoint(remote))
        self.assertEqual(result['status'], 'success', c.events)
        value = remote_json('import os,sys,json; root=os.fsencode(sys.argv[1]); print(json.dumps({n.hex():open(root+b"/"+n,"rb").read().hex() for n in os.listdir(root)}))', remote)
        self.assertEqual(value, {name.hex(): b'hello'.hex()})

    def test_first_connection_and_raw_byte_listing(self):
        c, result = self.run_job()
        self.assertEqual(result['status'], 'success', c.events)
        self.assertTrue(self.known.exists())
        self.assertTrue(any(e['type'] == 'auth_prompt' and e['kind'] == 'host_key' for e in c.events))
        capabilities = next(e for e in c.events[1:] if e['type'] == 'capabilities')
        self.assertEqual(capabilities['backend'], 'native-ssh')
        self.assertEqual(capabilities['peer_version'], '0.1.0')
        self.assertIn('copy', capabilities['operations'])
        self.assertIn('copy', capabilities['peer_operations'])
        self.assertEqual(capabilities['transfer_bridge'], '3')
        self.assertTrue(capabilities['typed_transfer_errors'])
        self.assertEqual(capabilities['copy_endpoint_kinds'], ['local', 'ssh'])
        entries = [item for e in c.events if e['type'] == 'entries' for item in e['entries']]
        by_name = {bytes.fromhex(item['name']['bytes_hex']): item for item in entries}
        self.assertIn(b'invalid-\xff', by_name)
        self.assertEqual(by_name[b'new\nline']['mtime_nanoseconds'], '123456789')
        self.assertEqual(by_name[b'link']['link_target']['bytes_hex'], b'new\nline'.hex())
        self.assertNotIn(b'nested', by_name)
        sequence = [int(e['seq']) for e in c.events]
        self.assertEqual(sequence, list(range(1, len(sequence)+1)))
        self.assertEqual(c.proc.stderr.read(), b'')

    def test_probe_stat_lstat_and_home_root(self):
        c, result = self.run_job('probe')
        self.assertEqual(result['status'], 'success', c.events)
        for op, kind in (('stat', 'file'), ('lstat', 'symlink')):
            c, result = self.run_job(op, self.endpoint(self.root / 'remote source' / 'link'))
            self.assertEqual(result['status'], 'success', c.events)
            self.assertEqual(next(e for e in c.events if e['type'] == 'entry')['entry']['type'], kind)
            self.assertFalse(any(e['type'] == 'auth_prompt' for e in c.events))
        for location in ('home', 'root'):
            c, result = self.run_job('resolve', location=location)
            self.assertEqual(result['status'], 'success', c.events)
            ep = next(e for e in c.events if e['type'] == 'resolved')['endpoint']
            self.assertEqual(ep['kind'], 'ssh')
            self.assertTrue(bytes.fromhex(ep['path']['bytes_hex']).startswith(b'/'))

    def test_remote_literal_stat_missing_and_empty(self):
        for name in (b'*?', b'colon:name', b'invalid-\xff', b'new\nline', b'-leading'):
            c, result = self.run_job('lstat', self.endpoint(os.fsencode(self.root / 'remote source')+b'/'+name))
            self.assertEqual(result['status'], 'success', c.events)
            self.assertEqual(next(e for e in c.events if e['type'] == 'entry')['entry']['size'], '5')
        c, result = self.run_job('list', self.endpoint(self.root / 'missing'))
        self.assertEqual(result['status'], 'failure')
        self.assertIn('missing', self.errors(c))
        self.assertEqual(next(e for e in c.events if e['type'] == 'error')['endpoint'], 'ssh')
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', self.root / self.local.name)
        c, result = self.run_job('list', self.endpoint(self.root / self.local.name))
        self.assertEqual(result['status'], 'success')
        self.assertFalse(any(e['type'] == 'entries' for e in c.events))

    def test_encrypted_key_and_no_secret_in_events_or_arguments(self):
        endpoint = self.endpoint(identity_file=str(self.key))
        c, result = self.run_job(endpoint=endpoint, answer=PASSPHRASE)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertTrue(any(e['type'] == 'auth_prompt' and e['kind'] == 'credential' for e in c.events))
        self.assertNotIn(PASSPHRASE, json.dumps(c.events))
        self.assertNotIn(PASSPHRASE.encode(), c.proc.stderr.read())

    def test_reference_client_typed_prompt_callback(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from app_client import AppClient
        c = AppClient(BINARY)
        self.addCleanup(c.close)
        prompts = []
        def answer(event):
            prompts.append(event['kind'])
            return 'yes' if event['kind'] == 'host_key' else PASSPHRASE
        events = list(c.run({'id': 'ssh', 'op': 'list',
                             'endpoint': self.endpoint(identity_file=str(self.key))},
                            prompt_handler=answer))
        self.assertEqual(events[-1]['status'], 'success', events)
        self.assertEqual(c.process.returncode, 0)
        self.assertEqual(prompts, ['host_key', 'credential'])
        self.assertTrue(any(e['type'] == 'entries' for e in events))
        self.assertNotIn(PASSPHRASE, json.dumps(events))

    def test_password_and_rejected_credentials(self):
        self.config.write_text('Host *\n  PreferredAuthentications password\n  PubkeyAuthentication no\n')
        endpoint = self.endpoint(port=AUTH_PORT)
        c, result = self.run_job(endpoint=endpoint, answer=PASSWORD)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertNotIn(PASSWORD, json.dumps(c.events))
        c, result = self.run_job(endpoint=endpoint, answer='wrong-password')
        self.assertEqual(result['status'], 'failure', c.events)
        self.assertIn('authentication', self.errors(c))
        self.assertNotIn('wrong-password', json.dumps(c.events))

    def credential_prompt(self, **connection):
        # Preseed trust using an ordinary successful app-mode probe.
        self.run_job('probe')
        c = self.client()
        c.send({'id': 'ssh', 'op': 'probe', 'endpoint': self.endpoint(identity_file=str(self.key), **connection)})
        while True:
            event = c.read(10)
            if event['type'] == 'auth_prompt':
                self.assertEqual(event['kind'], 'credential')
                return c, event

    def test_cancelled_prompt_and_explicit_job_cancel(self):
        c, prompt = self.credential_prompt()
        self.response(c, prompt, cancel=True)
        self.assertEqual(c.finish()['status'], 'cancellation')
        self.assertIn('authentication_cancelled', self.errors(c))
        c, _ = self.credential_prompt()
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'ssh'})
        self.assertEqual(c.finish()['status'], 'cancellation')
        self.assertTrue(any(e['type'] == 'cancel_ack' for e in c.events))

    def test_open_prompt_has_its_own_deadline(self):
        c, prompt = self.credential_prompt(authentication_timeout_seconds='1', prompt_timeout_seconds='5')
        time.sleep(1.2)
        self.assertIsNone(c.proc.poll())
        self.response(c, prompt, PASSPHRASE)
        self.assertEqual(c.finish()['status'], 'success')
        c, _ = self.credential_prompt(authentication_timeout_seconds='5', prompt_timeout_seconds='1')
        self.assertEqual(c.finish()['status'], 'failure')
        self.assertIn('authentication_timeout', self.errors(c))

    def test_stale_answer_is_rejected_without_disclosing_secret(self):
        c, prompt = self.credential_prompt()
        self.response(c, prompt, 'stale-secret', prompt_id='old-prompt')
        while True:
            event = c.read()
            if event['type'] == 'auth_response_rejected':
                break
        self.response(c, prompt, PASSPHRASE)
        self.assertEqual(c.finish()['status'], 'success')
        self.assertNotIn('stale-secret', json.dumps(c.events))

    def test_changed_host_key_and_unknown_key_strict_policy(self):
        self.run_job('probe')
        wrong = self.local / 'wrong-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(wrong)], check=True)
        known_name = '['+HOST+']:'+PORT if PORT else HOST
        self.known.write_text(known_name + ' ' + wrong.with_suffix('.pub').read_text())
        c, result = self.run_job('probe')
        self.assertEqual(result['status'], 'failure')
        self.assertIn('host_key', self.errors(c))
        self.assertFalse(any(e['type'] == 'auth_prompt' for e in c.events))
        self.known.unlink()
        c, result = self.run_job('probe', self.endpoint(host_key_policy='strict'))
        self.assertEqual(result['status'], 'failure')
        self.assertIn('host_key', self.errors(c))

    def test_missing_old_and_noisy_helpers_fail_before_operations(self):
        self.run_job('probe')
        for helper, category in (('/rig/no-helper-here', 'helper_missing'), ('/usr/bin/rsync', 'incompatible_schema')):
            c, result = self.run_job('probe', self.endpoint(helper_path=helper))
            self.assertEqual(result['status'], 'failure')
            self.assertIn(category, self.errors(c))
        script = self.root / self.local.name
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text("#!/bin/sh\\nprintf banner\\\\n\\nexec /usr/local/bin/xs \\\"$@\\\"\\n"); p.chmod(0o755)', script)
        c, result = self.run_job('probe', self.endpoint(helper_path=str(script)))
        self.assertEqual(result['status'], 'failure')
        self.assertIn('protocol', self.errors(c))
        # A peer's valid bounded frame must not grow past the public limit when
        # the adapter adds negotiated endpoint fields and the local envelope.
        code = '#!/usr/bin/python3\nimport json,sys\nsys.stdin.readline()\ne={"schema":"1","id":"remote-hello","seq":"1","type":"capabilities","version":"0.1.0","operations":["probe"],"padding":""}\ne["padding"]="x"*(1048576-len(json.dumps(e,separators=(",",":"))))\nprint(json.dumps(e,separators=(",",":")),flush=True)\n'
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)', script, code)
        c, result = self.run_job('probe', self.endpoint(helper_path=str(script)))
        self.assertEqual(result['status'], 'failure', c.events)
        self.assertTrue(all(len(json.dumps(e).encode()) <= 1048576 for e in c.events))

    def test_unreachable_host_and_invalid_profile(self):
        c, result = self.run_job('probe', self.endpoint(host='127.0.0.1', port='1', connect_timeout_seconds='1', authentication_timeout_seconds='2'))
        self.assertEqual(result['status'], 'failure')
        self.assertIn('network', self.errors(c))
        for changes in ({'host': '-oProxyCommand=oops'}, {'host_key_policy': 'no'}, {'helper_path': 'xs; touch /rig/unwanted'}, {'port': '65536'}):
            c = self.client()
            c.send({'id': 'ssh', 'op': 'probe', 'endpoint': self.endpoint(**changes)})
            self.assertEqual(c.finish()['status'], 'failure')
            self.assertFalse(any(e['type'] == 'started' for e in c.events))

    def test_control_pipe_loss_and_private_broker_cleanup(self):
        before = set(pathlib.Path('/tmp').glob('xsync-auth-*'))
        c, _ = self.credential_prompt()
        live = set(pathlib.Path('/tmp').glob('xsync-auth-*')) - before
        self.assertEqual(len(live), 1)
        directory = live.pop()
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((directory / 'socket').stat().st_mode & 0o777, 0o600)
        commands = subprocess.check_output(['ps', '-axo', 'command=']).decode()
        self.assertNotIn(PASSPHRASE, commands)
        c.proc.stdin.close()
        self.assertEqual(c.finish()['status'], 'cancellation')
        self.assertFalse(directory.exists())

    def test_agent_authentication(self):
        agent = subprocess.check_output(['ssh-agent', '-s']).decode()
        sock = re.search(r'SSH_AUTH_SOCK=([^;]+)', agent)[1]
        pid = int(re.search(r'SSH_AGENT_PID=(\d+)', agent)[1])
        self.addCleanup(os.kill, pid, signal.SIGTERM)
        env = dict(os.environ, SSH_AUTH_SOCK=sock)
        subprocess.run(['ssh-add', IDENTITY], env=env, check=True, capture_output=True)
        self.config.write_text('Host *\n  PreferredAuthentications publickey\n  IdentityFile none\n')
        endpoint = self.endpoint()
        endpoint['connection'].pop('identity_file')
        c, result = self.run_job('probe', endpoint, env=env)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(any(e['type'] == 'auth_prompt' and e['kind'] == 'credential' for e in c.events))

    def test_jump_host_and_profile_alias(self):
        self.run_job('probe')  # Preseed the jump host's verified host key.
        self.config.write_text('Host app-jump\n  HostName ' + HOST + '\n  Port ' + (PORT or '22') +
                               '\nHost app-alias\n  HostName 127.0.0.1\n  Port 22\nHost app-jump app-alias\n  User root\n  IdentityFile "' + IDENTITY +
                               '"\n  UserKnownHostsFile "' + str(self.known) + '"\n  StrictHostKeyChecking yes\n  IdentitiesOnly yes\n  PreferredAuthentications publickey\n')
        endpoint = self.endpoint(host='app-alias', jump_host='app-jump')
        endpoint['connection'].pop('port', None)  # The inner target is server-local port 22.
        c, result = self.run_job('list', endpoint)
        self.assertEqual(result['status'], 'success', c.events)
        self.assertTrue(any(e['type'] == 'entries' for e in c.events))

    def test_existing_controlmaster_survives_cancelled_job(self):
        self.run_job('probe')
        control = self.local / 'control'
        subprocess.run([*SSH, '-M', '-N', '-f', '-oControlPersist=30', '-oControlPath='+str(control), HOST], check=True, capture_output=True)
        self.addCleanup(subprocess.run, [*SSH, '-S', str(control), '-O', 'exit', HOST], capture_output=True)
        self.config.write_text('Host *\n  ControlPath '+str(control)+'\n  IdentitiesOnly yes\n  PreferredAuthentications publickey\n')
        c, result = self.run_job('probe', self.endpoint(identity_file=str(self.key)))
        self.assertEqual(result['status'], 'success', c.events)
        self.assertFalse(any(e['type'] == 'auth_prompt' for e in c.events))
        c = self.client()
        c.send({'id': 'ssh', 'op': 'list', 'endpoint': self.endpoint()})
        self.assertEqual(c.read()['type'], 'started')
        c.send({'id': 'cancel', 'op': 'cancel', 'job_id': 'ssh'})
        self.assertEqual(c.finish()['status'], 'cancellation')
        check = subprocess.run([*SSH, '-S', str(control), '-O', 'check', HOST], capture_output=True)
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_hard_supervisor_loss_stops_ssh_and_removes_private_broker(self):
        before = set(pathlib.Path('/tmp').glob('xsync-auth-*'))
        c, _ = self.credential_prompt()
        directories = set(pathlib.Path('/tmp').glob('xsync-auth-*')) - before
        self.assertEqual(len(directories), 1)
        c.proc.kill()
        c.proc.wait(timeout=5)
        deadline = time.monotonic()+6
        while time.monotonic() < deadline:
            if not any(path.exists() for path in directories):
                break
            time.sleep(0.05)
        else:
            self.fail('private authentication broker survived supervisor death')

    def test_operation_idle_timeout_is_independent_of_authentication(self):
        self.run_job('probe')
        helper = self.root / self.local.name
        script = '#!/usr/bin/python3\nimport sys,json,time\njson.loads(sys.stdin.readline())\nprint(json.dumps({"schema":"1","id":"remote-hello","seq":"1","type":"capabilities","version":"0.1.0","operations":["probe","list"]}),flush=True)\nsys.stdin.readline()\ntime.sleep(30)\n'
        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)', helper, script)
        c, result = self.run_job('list', self.endpoint(helper_path=str(helper), authentication_timeout_seconds='10', idle_timeout_seconds='1'))
        self.assertEqual(result['status'], 'failure')
        self.assertIn('network_timeout', self.errors(c))


if __name__ == '__main__':
    unittest.main()
