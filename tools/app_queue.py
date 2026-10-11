#!/usr/bin/env python3
"""Persistent copy queue foundation for the schema-1 reference client.

Keep this object open for the manager's lifetime. Each claim must be committed
before launching its one-job AppClient; record recovery IDs before consuming
more events. SSH profiles are resolved separately, never written to this file.
"""
import copy
import fcntl
import json
import math
import os
import re
import stat
import tempfile
import threading
import time
import uuid


LIMIT = 16 * 1024 * 1024
STATES = {'queued', 'retry_waiting', 'active', 'reconciling', 'paused', 'success', 'failure', 'partial_failure',
          'cancellation', 'needs_reconciliation', 'recoverable'}
RESULTS = {'paused', 'success', 'failure', 'partial_failure', 'cancellation'}
ITEM_FIELDS = {'item_id', 'path', 'source_path', 'destination_path', 'source_endpoint',
               'destination_endpoint', 'entry_type', 'status', 'reason',
               'content_published', 'metadata_complete'}


def _delays(value):
    if not isinstance(value, (tuple, list)) or len(value) > 8 or any(type(d) not in (int, float) or not 0 <= d <= 5 for d in value):
        raise ValueError('backoff requires at most eight delays of zero to five seconds')
    return [math.ceil(d * 1000) for d in value]


def _reconnect(value, attempt):
    _fields(value, {'delays_ms', 'retries', 'not_before_ms', 'engine_support', 'not_submitted', 'network_errors', 'disqualified', 'history'}, {'recovery'})
    delays = value['delays_ms']
    if not isinstance(delays, list) or not 1 <= len(delays) <= 8 or any(type(d) is not int or not 0 <= d <= 5000 for d in delays):
        raise ValueError('invalid reconnect delays')
    retries = value['retries']
    if type(retries) is not int or not 0 <= retries <= len(delays): raise ValueError('invalid reconnect budget')
    deadline = value['not_before_ms']
    if deadline is not None and (type(deadline) is not int or not 0 <= deadline <= 2**63-1): raise ValueError('invalid reconnect deadline')
    for field in ('engine_support', 'not_submitted', 'disqualified'):
        if type(value[field]) is not bool: raise ValueError('invalid reconnect evidence')
    if type(value['network_errors']) is not int or not 0 <= value['network_errors'] <= 64: raise ValueError('invalid reconnect errors')
    history = value['history']
    if not isinstance(history, list) or len(history) != retries: raise ValueError('invalid reconnect history')
    previous, previous_kind = 0, None
    for row in history:
        _fields(row, {'attempt', 'status'}, {'code', 'cleanup', 'durability', 'kind'})
        kind = row.get('kind')
        duplicate = kind == previous_kind == 'reconciliation' and row['attempt'] == previous
        if kind not in (None, 'reconciliation') or type(row['attempt']) is not int or not (previous < row['attempt'] <= attempt or duplicate) or row['status'] not in (('failure',) if kind is None else ('failure', 'partial_failure', 'unknown')):
            raise ValueError('invalid reconnect attempt history')
        if 'code' in row and (not isinstance(row['code'], str) or not re.fullmatch(r'[0-9]{1,3}', row['code'])):
            raise ValueError('invalid reconnect result code')
        for field in ('cleanup', 'durability'):
            if field in row and (kind != 'reconciliation' or not isinstance(row[field], str) or len(row[field]) > 128): raise ValueError('invalid recovery history')
        previous, previous_kind = row['attempt'], kind
    if 'recovery' in value:
        recovery = value['recovery']
        _fields(recovery, {'enabled', 'disqualified', 'network_errors', 'pending', 'claim'})
        if recovery['enabled'] is not True or any(type(recovery[f]) is not bool for f in ('disqualified', 'pending')):
            raise ValueError('invalid automatic recovery policy')
        if type(recovery['network_errors']) is not int or not 0 <= recovery['network_errors'] <= 64: raise ValueError('invalid recovery network evidence')
        if recovery['claim'] is not None: _hex_identity(recovery['claim'])


def _can_reconnect(job):
    policy = job.get('reconnect')
    return (policy is not None and policy['engine_support'] and policy['not_submitted'] and
            policy['network_errors'] > 0 and not policy['disqualified'] and job.get('stop_requested') is None and
            not job['items'] and job['state'] in ('failure', 'retry_waiting') and job['result'] is not None and
            job['result']['status'] == 'failure' and
            any(ep['kind'] == 'ssh' for ep in [job['request']['destination']] + [s['endpoint'] for s in job['request']['sources']]))


def _new_reconnect(delays, recover_disconnected=False):
    policy = {'delays_ms':delays, 'retries':0, 'not_before_ms':None, 'engine_support':False,
            'not_submitted':False, 'network_errors':0, 'disqualified':False, 'history':[]}
    if recover_disconnected:
        policy['recovery'] = {'enabled':True, 'disqualified':False, 'network_errors':0, 'pending':False, 'claim':None}
    return policy


def _can_recover(job):
    recovery = job.get('reconnect', {}).get('recovery')
    return (recovery is not None and not recovery['disqualified'] and job.get('stop_requested') is None and
            job['recovery_id'] is not None and job['request']['options'].get('retain_partials') is True and
            any(ep['kind'] == 'ssh' for ep in [job['request']['destination']] + [s['endpoint'] for s in job['request']['sources']]))


def _schedule_recovery(job, outcome=None):
    if not _can_recover(job): return False
    policy = job['reconnect']
    if policy['retries'] == len(policy['delays_ms']):
        job['reason'] = 'automatic_recovery_budget_exhausted'; return False
    delay = policy['delays_ms'][policy['retries']]
    policy['history'].append({'attempt':job['attempt'], 'kind':'reconciliation', **(outcome or {'status':'unknown'})})
    policy.update(retries=policy['retries']+1, not_before_ms=time.time_ns()//1000000+delay)
    policy['recovery'].update(pending=True, claim=None)
    job['reason'] = 'automatic_recovery_waiting'
    return True


def _recovery_request_id(job, prefix, claim):
    recovery = job.get('reconnect', {}).get('recovery')
    if claim is None:
        if job['state'] != 'needs_reconciliation' or (recovery is not None and recovery['pending']):
            raise ValueError('manual reconciliation requires unclaimed unknown work')
    elif job['state'] != 'reconciling' or recovery is None or recovery['claim'] != claim or not recovery['pending']:
        raise ValueError('reconciliation claim is no longer active')
    return f'{prefix}-{claim}' if claim is not None else f"{prefix}-{job['id']}-{job['attempt']}"


class RecoveryUnavailable(RuntimeError):
    def __init__(self, message, *, retryable=False, cancelled=False):
        super().__init__(message)
        self.retryable, self.cancelled = retryable, cancelled


def _waiting(job):
    recovery = job.get('reconnect', {}).get('recovery')
    return job['state'] in ('queued', 'retry_waiting') or (job['state'] == 'needs_reconciliation' and recovery is not None and recovery['pending'])


def _busy(job):
    recovery = job.get('reconnect', {}).get('recovery')
    return job['state'] in ('active', 'reconciling') or (job['state'] == 'recoverable' and recovery is not None and recovery['claim'] is not None)


def _clamp_deadlines(data, now):
    for job in data['jobs']:
        if not _waiting(job) or job['state'] == 'queued': continue
        policy = job['reconnect']
        policy['not_before_ms'] = min(policy['not_before_ms'], now + policy['delays_ms'][policy['retries']-1])


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError('invalid queue fields')


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,96}', value):
        raise ValueError('invalid queue identity')


def _path(value, component=False):
    _fields(value, {'bytes_hex'})
    encoded = value['bytes_hex']
    if not isinstance(encoded, str) or not re.fullmatch(r'(?:[0-9a-f]{2})+', encoded):
        raise ValueError('invalid queue byte path')
    raw = bytes.fromhex(encoded)
    if b'\0' in raw or len(raw) > 4096:
        raise ValueError('invalid queue byte path')
    if component:
        if raw in (b'.', b'..') or b'/' in raw or len(raw) > 255:
            raise ValueError('invalid destination component')
    elif not raw.startswith(b'/') or any(p in (b'.', b'..') for p in raw.split(b'/')):
        raise ValueError('queue requires absolute endpoint paths')
    return raw


def _endpoint(value):
    _fields(value, {'kind', 'path'}, {'profile_id'})
    _path(value['path'])
    if value['kind'] == 'ssh':
        _identifier(value.get('profile_id'))
    elif value['kind'] != 'local' or 'profile_id' in value:
        raise ValueError('invalid queue endpoint')


def _request(value):
    # Destructive actions need their own restart/revision contract. This first
    # queue implementation accepts copies only, with no arbitrary saved fields.
    _fields(value, {'op', 'sources', 'destination', 'options'})
    if value['op'] != 'copy':
        raise ValueError('persistent queue currently accepts copies only')
    _endpoint(value['destination'])
    sources = value['sources']
    if not isinstance(sources, list) or not 1 <= len(sources) <= 1024:
        raise ValueError('invalid queue selection')
    kinds, profiles, paths, names = set(), set(), set(), set()
    for selected in sources:
        _fields(selected, {'endpoint', 'mode'}, {'destination_name'})
        ep = selected['endpoint']; _endpoint(ep)
        raw = _path(ep['path']); kinds.add(ep['kind'])
        if raw in paths: raise ValueError('duplicate source selection')
        paths.add(raw)
        if ep['kind'] == 'ssh': profiles.add(ep['profile_id'])
        if selected['mode'] == 'contents':
            if len(sources) != 1 or 'destination_name' in selected:
                raise ValueError('contents must be the only selection')
        elif selected['mode'] == 'entry':
            name = _path(selected['destination_name'], True) if 'destination_name' in selected else raw.rsplit(b'/', 1)[-1]
            if not name or name in names: raise ValueError('duplicate or empty destination name')
            names.add(name)
        else: raise ValueError('invalid queue selection mode')
    if len(kinds) != 1 or len(profiles) > 1 or ('ssh' in kinds and value['destination']['kind'] == 'ssh'):
        raise ValueError('unsupported endpoint combination')
    options = value['options']
    _fields(options, {'on_conflict', 'preserve_times', 'preserve_permissions'},
            {'retain_partials', 'jobs', 'bandwidth_bytes_per_second', 'conflict_timeout_seconds'})
    if options['on_conflict'] not in ('ask', 'replace', 'skip'): raise ValueError('invalid conflict policy')
    for field in ('preserve_times', 'preserve_permissions', 'retain_partials'):
        if field in options and type(options[field]) is not bool: raise ValueError('invalid boolean option')
    for field, maximum, minimum in (('jobs', 64, 0), ('bandwidth_bytes_per_second', 2**63-1, 0), ('conflict_timeout_seconds', 3600, 1)):
        if field in options:
            number = options[field]
            if not isinstance(number, str) or not re.fullmatch(r'[0-9]{1,20}', number) or not minimum <= int(number) <= maximum:
                raise ValueError('invalid numeric queue option')


def _private_file(fd):
    s = os.fstat(fd)
    if not stat.S_ISREG(s.st_mode) or s.st_uid != os.geteuid() or s.st_nlink != 1 or s.st_mode & 0o077:
        raise ValueError('queue files must be private owned regular files')


def _retry_plan(job, identities):
    """Fresh leaf copies: never broaden a failed directory into completed children."""
    if job['state'] not in ('failure', 'partial_failure') or job.get('stop_requested') == 'cancel' or job['result'] is None:
        raise ValueError('retry-failed requires an authoritative failed copy without cancel intent')
    if not isinstance(identities, list) or not identities or any(not isinstance(i, str) for i in identities) or len(identities) != len(set(identities)):
        raise ValueError('retry-failed requires distinct failed item identities')
    original = job['request']
    root = _path(original['destination']['path']).rstrip(b'/')
    groups, targets = {}, set()
    for identity in sorted(identities):
        item = job['items'].get(identity)
        if item is None or item['status'] != 'failure':
            raise ValueError('only reported failures qualify for retry-failed')
        if item.get('entry_type') not in ('file', 'symlink'):
            raise ValueError('directory retries need selective engine support; select failed leaves explicitly')
        relative = bytes.fromhex(item.get('path', {}).get('bytes_hex', ''))
        if not relative or b'\0' in relative or any(p in (b'', b'.', b'..') for p in relative.split(b'/')):
            raise ValueError('retry item lacks a safe relative path')
        if identity != relative.hex(): raise ValueError('retry item identity differs from its path')
        source = _path(item.get('source_path'))
        target = _path(item.get('destination_path'))
        if item.get('destination_endpoint') != original['destination']['kind'] or not target.startswith(root + b'/'):
            raise ValueError('retry destination is outside its original endpoint scope')
        suffix = target[len(root) + 1:]
        if any(p in (b'', b'.', b'..') for p in suffix.split(b'/')) or target in targets:
            raise ValueError('retry destination is ambiguous')
        targets.add(target)
        templates = []
        for selected in original['sources']:
            ep = selected['endpoint']; base = _path(ep['path']).rstrip(b'/')
            if ep['kind'] != item.get('source_endpoint'): continue
            if selected['mode'] == 'contents': expected = base + b'/' + relative
            else:
                name = _path(selected['destination_name'], True) if 'destination_name' in selected else base.rsplit(b'/', 1)[-1]
                if relative == name: expected = base
                elif relative.startswith(name + b'/'): expected = base + relative[len(name):]
                else: continue
            if expected == source: templates.append(ep)
        if len(templates) != 1: raise ValueError('retry source differs from its original selection')
        ep = copy.deepcopy(templates[0]); ep['path'] = {'bytes_hex':source.hex()}
        parent, _, name = target.rpartition(b'/')
        selection = {'endpoint':ep, 'mode':'entry'}
        if name != source.rsplit(b'/', 1)[-1]: selection['destination_name'] = {'bytes_hex':name.hex()}
        selections, items = groups.setdefault(parent or b'/', ([], []))
        selections.append(selection); items.append(identity)
    plans = []
    for parent, (sources, items) in groups.items():
        destination = copy.deepcopy(original['destination']); destination['path'] = {'bytes_hex':parent.hex()}
        options = copy.deepcopy(original['options'])
        # A previous replace choice cannot authorize replacing today's target.
        if options['on_conflict'] == 'replace': options['on_conflict'] = 'ask'
        request = {'op':'copy', 'sources':sources, 'destination':destination, 'options':options}
        _request(request)
        plans.append((request, items))
    return plans


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('duplicate queue JSON field')
        result[key] = value
    return result


def _revision(value):
    fields = {'device', 'inode', 'links', 'mode', 'uid', 'gid', 'flags', 'size',
              'mtime_seconds', 'mtime_nanoseconds', 'ctime_seconds', 'ctime_nanoseconds'}
    _fields(value, {'exists'} | fields)
    if value['exists'] is not True: raise ValueError('recovery observation requires an existing revision')
    for field in fields:
        pattern = r'-?[0-9]{1,20}' if field in ('mtime_seconds', 'ctime_seconds') else r'[0-9]{1,20}'
        if not isinstance(value[field], str) or not re.fullmatch(pattern, value[field]): raise ValueError('invalid recovery revision')


def _hex_identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{32}', value): raise ValueError('invalid recovery identity')


def _actor(value, recovery_id):
    _fields(value, {'type', 'endpoint', 'role', 'recovery_id', 'attempt_id', 'actor_path', 'actor_revision'}, {'cleaned'})
    if value['type'] != 'recovery_actor' or value['endpoint'] not in ('local', 'ssh') or value['role'] not in ('sender', 'receiver') or value['recovery_id'] != recovery_id:
        raise ValueError('invalid recovery actor receipt')
    _hex_identity(value['attempt_id']); _revision(value['actor_revision'])
    if not stat.S_ISREG(int(value['actor_revision']['mode'])): raise ValueError('actor receipt requires a regular lease revision')
    # Engine path objects include a display hint. Save/use only authoritative bytes.
    _path({'bytes_hex':value['actor_path']['bytes_hex']})
    if 'cleaned' in value and type(value['cleaned']) is not bool: raise ValueError('invalid actor cleanup receipt')


def _same_actor(a, b):
    return all(a.get(k) == b.get(k) for k in ('endpoint', 'role', 'recovery_id', 'attempt_id')) and a.get('actor_path', {}).get('bytes_hex') == b.get('actor_path', {}).get('bytes_hex')


VERIFICATION_COUNTS = {'records_total', 'pending_records', 'published_records', 'prepared_records', 'choices_total', 'bytes_retained'}


def _verification(value):
    _fields(value, VERIFICATION_COUNTS | {'inventory_token', 'actors_quiescent', 'source_verification_required', 'operation_completion_proven'})
    _hex_identity(value['inventory_token'])
    for field in VERIFICATION_COUNTS:
        if not isinstance(value[field], str) or not re.fullmatch(r'[0-9]{1,20}', value[field]): raise ValueError('invalid verification counts')
    if value['actors_quiescent'] is not True or value['source_verification_required'] is not True or value['operation_completion_proven'] is not False:
        raise ValueError('invalid recovery verification meaning')
    if sum(int(value[k]) for k in ('pending_records', 'published_records', 'prepared_records')) != int(value['records_total']):
        raise ValueError('inconsistent recovery verification counts')


class PersistentQueue:
    """One manager, bounded durable records, independent active-job admission.

    Missing terminal results require inspection and explicit recovery. Opt-in
    bounded reconnects require proof that no copy operation was submitted.
    """
    def __init__(self, path, max_active=1):
        if type(max_active) is not int or not 1 <= max_active <= 64:
            raise ValueError('invalid active-job limit')
        self.path = os.path.abspath(os.fspath(path))
        self.max_active = max_active
        self.mutex = threading.RLock()
        self.lock_fd = os.open(self.path + '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        self.closed = False
        self.poisoned = False
        try:
            _private_file(self.lock_fd)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            except FileNotFoundError:
                self.data = {'format': '1', 'jobs': []}
                self._commit(copy.deepcopy(self.data))
            else:
                try:
                    _private_file(fd)
                    with os.fdopen(fd, 'rb', closefd=False) as stream:
                        raw = stream.read(LIMIT + 1)
                    if len(raw) > LIMIT: raise ValueError('queue exceeds size limit')
                    self.data = json.loads(raw, object_pairs_hook=_unique_json)
                    self._validate(self.data)
                finally: os.close(fd)
            restarted = copy.deepcopy(self.data)
            for job in restarted['jobs']:
                recovery = job.get('reconnect', {}).get('recovery')
                if job['state'] in ('active', 'reconciling') or (job['state'] == 'recoverable' and recovery is not None and recovery['claim'] is not None):
                    self._unknown(job, 'manager_restart')
            if restarted != self.data: self._commit(restarted)
        except BaseException:
            os.close(self.lock_fd); self.closed = True
            raise

    @staticmethod
    def _validate(data):
        _fields(data, {'format', 'jobs'})
        if data['format'] != '1' or not isinstance(data['jobs'], list) or len(data['jobs']) > 1024:
            raise ValueError('invalid queue format or job count')
        ids = set()
        for job in data['jobs']:
            _fields(job, {'id', 'request', 'state', 'attempt', 'recovery_id', 'items', 'result', 'reason', 'next_operation', 'observation'}, {'verification', 'stop_requested', 'actors', 'closed_actors', 'retry_of', 'reconnect'})
            if job.get('stop_requested') not in (None, 'cancel', 'pause'): raise ValueError('invalid queued stop intent')
            if job.get('stop_requested') == 'cancel' and job['state'] in ('queued', 'retry_waiting', 'recoverable'):
                raise ValueError('cancelled intent cannot be ready for dispatch')
            _identifier(job['id']); _request(job['request'])
            if job['id'] in ids: raise ValueError('duplicate queue job')
            ids.add(job['id'])
            if job['state'] not in STATES or type(job['attempt']) is not int or not 0 <= job['attempt'] <= 1000000:
                raise ValueError('invalid queue state')
            if job['next_operation'] not in ('copy', 'resume'): raise ValueError('invalid queued operation')
            if job['recovery_id'] is not None and (not isinstance(job['recovery_id'], str) or not re.fullmatch(r'[0-9a-f]{32}', job['recovery_id'])):
                raise ValueError('invalid recovery ID')
            if job['next_operation'] == 'resume' and (not job['recovery_id'] or not job['request']['options'].get('retain_partials')):
                raise ValueError('resume lacks private recovery binding')
            if not isinstance(job['reason'], str) or len(job['reason']) > 128 or not isinstance(job['items'], dict) or len(job['items']) > 100000:
                raise ValueError('invalid queue outcome inventory')
            for identity, item in job['items'].items():
                if not isinstance(identity, str) or len(identity) > 8192: raise ValueError('invalid item identity')
                _fields(item, {'item_id', 'status'}, ITEM_FIELDS - {'item_id', 'status'})
                if item['item_id'] != identity or item['status'] not in ('pending', 'success', 'failure', 'skipped', 'cancellation', 'unknown'):
                    raise ValueError('invalid item outcome')
                for field in ('path', 'source_path', 'destination_path'):
                    if field in item:
                        _fields(item[field], {'bytes_hex'})
                        encoded = item[field]['bytes_hex']
                        if not isinstance(encoded, str) or not re.fullmatch(r'(?:[0-9a-f]{2})*', encoded) or len(encoded) > 8192:
                            raise ValueError('invalid item byte path')
                for field in ITEM_FIELDS - {'item_id', 'status', 'path', 'source_path', 'destination_path', 'content_published', 'metadata_complete'}:
                    if field == 'reason' and item.get(field) is None: continue
                    if field in item and (not isinstance(item[field], str) or len(item[field]) > 128): raise ValueError('invalid item attribute')
                for field in ('content_published', 'metadata_complete'):
                    if field in item and item[field] is not None and type(item[field]) is not bool: raise ValueError('invalid item completion')
            if job['result'] is not None:
                _fields(job['result'], {'status'}, {'code', 'cleanup', 'durability'})
                if job['result']['status'] not in RESULTS or any(not isinstance(v, str) or len(v) > 128 for v in job['result'].values()):
                    raise ValueError('invalid authoritative result')
                if job['state'] in RESULTS and job['result']['status'] != job['state']:
                    raise ValueError('queue result and state disagree')
            elif job['state'] in RESULTS: raise ValueError('terminal state lacks authoritative result')
            if job['state'] in ('active', 'reconciling', 'needs_reconciliation', 'recoverable') and job['result'] is not None:
                raise ValueError('unfinished attempt has a terminal result')
            if job['state'] == 'success' and any(i['status'] not in ('success', 'skipped') for i in job['items'].values()):
                raise ValueError('successful queue job has incomplete item outcomes')
            if job['observation'] is not None:
                _fields(job['observation'], {'state', 'files_total'}, {'job_revision', 'inventory_token', 'actors'})
                if not isinstance(job['observation']['state'], str) or len(job['observation']['state']) > 32 or not re.fullmatch(r'[0-9]{1,20}', job['observation']['files_total']):
                    raise ValueError('invalid recovery observation')
                if 'job_revision' in job['observation']: _revision(job['observation']['job_revision'])
                if 'job_revision' in job['observation'] and not stat.S_ISDIR(int(job['observation']['job_revision']['mode'])):
                    raise ValueError('recovery observation requires a job directory revision')
                if 'inventory_token' in job['observation']: _hex_identity(job['observation']['inventory_token'])
                actors = job['observation'].get('actors', [])
                if not isinstance(actors, list) or len(actors) > 256: raise ValueError('invalid recovery actor inventory')
                for actor in actors: _actor(actor, job['recovery_id'])
            if job.get('verification') is not None:
                _verification(job['verification'])
                if job['observation'] is None or job['verification']['inventory_token'] != job['observation'].get('inventory_token'):
                    raise ValueError('verification differs from inspected inventory')
            if job['state'] == 'recoverable' and (job.get('verification') is None or not job['recovery_id'] or not job['request']['options'].get('retain_partials')):
                raise ValueError('recoverable queue job lacks validated private work')
            for field in ('actors', 'closed_actors'):
                actors = job.get(field, [])
                if not isinstance(actors, list) or len(actors) > 256: raise ValueError('invalid saved actor inventory')
                for actor in actors:
                    _actor(actor, job['recovery_id'])
                    if field == 'closed_actors' and actor.get('cleaned') is not True: raise ValueError('saved close proof is incomplete')
            if 'reconnect' in job:
                _reconnect(job['reconnect'], job['attempt'])
                deadline = job['reconnect']['not_before_ms']
                recovery = job['reconnect'].get('recovery')
                if recovery is not None and (not job['request']['options'].get('retain_partials') or not any(ep['kind'] == 'ssh' for ep in [job['request']['destination']] + [s['endpoint'] for s in job['request']['sources']])):
                    raise ValueError('automatic recovery requires a private SSH copy')
                if job['state'] == 'retry_waiting':
                    if not _can_reconnect(job) or deadline is None or job['reconnect']['retries'] == 0 or job['reconnect']['history'][-1]['attempt'] != job['attempt']:
                        raise ValueError('waiting reconnect lacks a complete unsubmitted failure')
                elif recovery is not None and recovery['pending']:
                    history = job['reconnect']['history']
                    if not _can_recover(job) or not history or history[-1].get('kind') != 'reconciliation' or history[-1]['attempt'] != job['attempt']:
                        raise ValueError('automatic recovery lacks its interrupted attempt')
                    if recovery['claim'] is None:
                        if job['state'] != 'needs_reconciliation' or deadline is None: raise ValueError('invalid pending recovery state')
                    elif job['state'] not in ('reconciling', 'recoverable') or deadline is not None:
                        raise ValueError('invalid claimed recovery state')
                elif deadline is not None or (recovery is not None and recovery['claim'] is not None):
                    raise ValueError('reconnect deadline/claim outside waiting state')
                if job['state'] == 'reconciling' and (recovery is None or not recovery['pending']): raise ValueError('unreserved reconciliation')
            elif job['state'] in ('retry_waiting', 'reconciling'): raise ValueError('waiting reconnect lacks its policy')
        by_id = {job['id']:job for job in data['jobs']}
        consumed = set()
        for job in data['jobs']:
            if 'retry_of' not in job: continue
            origin = job['retry_of']
            _fields(origin, {'job_id', 'attempt', 'item_ids'})
            _identifier(origin['job_id'])
            parent = by_id.get(origin['job_id'])
            if parent is None or parent is job or type(origin['attempt']) is not int or origin['attempt'] != parent['attempt']:
                raise ValueError('retry lineage lacks its original attempt')
            items = origin['item_ids']
            if not isinstance(items, list) or any(not isinstance(i, str) for i in items): raise ValueError('invalid retry item identities')
            plans = _retry_plan(parent, items)
            if len(plans) != 1 or plans[0][0] != job['request']:
                raise ValueError('retry request differs from its recorded failed items')
            for item in items:
                key = (parent['id'], parent['attempt'], item)
                if key in consumed: raise ValueError('failed item was admitted for retry more than once')
                consumed.add(key)
        for job in data['jobs']:
            ancestors = {job['id']}
            while 'retry_of' in job:
                job = by_id[job['retry_of']['job_id']]
                if job['id'] in ancestors: raise ValueError('cyclic retry lineage')
                ancestors.add(job['id'])

    def _commit(self, data):
        if self.closed: raise RuntimeError('queue is closed')
        if self.poisoned: raise RuntimeError('queue persistence is uncertain; close and reopen before dispatch')
        self._validate(data)
        raw = json.dumps(data, ensure_ascii=True, separators=(',', ':')).encode() + b'\n'
        if len(raw) > LIMIT: raise ValueError('queue exceeds size limit')
        parent = os.path.dirname(self.path)
        fd, temporary = tempfile.mkstemp(prefix='.xsync-queue-', dir=parent)
        replaced = False
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            replaced = True
            directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try: os.fsync(directory)
            finally: os.close(directory)
        except BaseException:
            if replaced: self.poisoned = True
            raise
        finally:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
        # An error after replace remains a failed acknowledgement. The caller
        # must stop dispatch; reopening reconciles the authoritative disk state.
        self.data = data

    def _change(self, callback):
        with self.mutex:
            if self.closed: raise RuntimeError('queue is closed')
            if self.poisoned: raise RuntimeError('queue persistence is uncertain; close and reopen before dispatch')
            data = copy.deepcopy(self.data)
            result = callback(data)
            if data != self.data: self._commit(data)
            return copy.deepcopy(result)

    @staticmethod
    def _job(data, identity):
        return next(job for job in data['jobs'] if job['id'] == identity)

    @staticmethod
    def _unknown(job, reason, outcome=None):
        if job.get('stop_requested') == 'cancel': reason = 'cancel_requested_outcome_unknown'
        job.update(state='needs_reconciliation', reason=reason, result=None, observation=None)
        job.pop('verification', None)
        if 'reconnect' in job:
            job['reconnect'].update(not_before_ms=None, not_submitted=False, disqualified=True)
            if 'recovery' in job['reconnect']:
                job['reconnect']['recovery'].update(pending=False, claim=None)
        for item in job['items'].values():
            if item['status'] == 'pending':
                item.update(status='unknown', reason='outcome_not_reported', content_published=None, metadata_complete=None)
        _schedule_recovery(job, outcome)

    def snapshot(self):
        with self.mutex: return copy.deepcopy(self.data['jobs'])

    def enqueue(self, request, identity=None, *, reconnect_delays=(), recover_disconnected=False):
        request = copy.deepcopy(request)
        request.pop('id', None)
        _request(request)
        identity = identity or uuid.uuid4().hex; _identifier(identity)
        delays = _delays(reconnect_delays)
        if type(recover_disconnected) is not bool or (recover_disconnected and not delays): raise ValueError('automatic recovery requires an explicit bounded reconnect policy')
        def add(data):
            if any(j['id'] == identity for j in data['jobs']): raise ValueError('duplicate queue job')
            data['jobs'].append({'id': identity, 'request': request, 'state': 'queued', 'attempt': 0,
                                 'recovery_id': None, 'items': {}, 'result': None, 'reason': '',
                                 'next_operation': 'copy', 'observation': None})
            if delays: data['jobs'][-1]['reconnect'] = _new_reconnect(delays, recover_disconnected)
            return identity
        return self._change(add)

    def set_reconnect(self, identity, retry_delays, *, recover_disconnected=False):
        """Choose a bounded policy before the first claim, including retry children."""
        delays = _delays(retry_delays)
        if type(recover_disconnected) is not bool or (recover_disconnected and not delays): raise ValueError('automatic recovery requires an explicit bounded reconnect policy')
        def configure(data):
            job = self._job(data, identity)
            if job['state'] != 'queued' or job['attempt'] != 0: raise ValueError('reconnect policy must be selected before launch')
            if delays: job['reconnect'] = _new_reconnect(delays, recover_disconnected)
            else: job.pop('reconnect', None)
        self._change(configure)

    def reorder(self, identities):
        def order(data):
            waiting = {j['id']: j for j in data['jobs'] if _waiting(j)}
            if len(identities) != len(waiting) or set(identities) != waiting.keys(): raise ValueError('reorder must include every queued job once')
            sequence = iter(identities)
            data['jobs'] = [waiting[next(sequence)] if _waiting(j) else j for j in data['jobs']]
        self._change(order)

    def retry_failed(self, identity, item_ids=None):
        """Atomically admit explicit fresh leaf retries; preserve original outcomes/vaults.

        Default selects all failures, so a failed directory requires the caller
        to select supported failed leaves explicitly instead of silently omitting it.
        Newly admitted jobs have independent recovery identities and ask again
        before replacing a present target. Their lineage survives manager restart.
        """
        def retry(data):
            parent = self._job(data, identity)
            if item_ids is not None and not isinstance(item_ids, (list, tuple)):
                raise ValueError('retry item identities must be a list or tuple')
            items = list(item_ids) if item_ids is not None else [i for i, item in parent['items'].items() if item['status'] == 'failure']
            if any(not isinstance(i, str) for i in items): raise ValueError('invalid retry item identity')
            admitted = {i for job in data['jobs'] for i in job.get('retry_of', {}).get('item_ids', [])
                        if job.get('retry_of', {}).get('job_id') == identity and job['retry_of']['attempt'] == parent['attempt']}
            if any(i in admitted for i in items): raise ValueError('failed item already has an admitted retry; use that job')
            plans = _retry_plan(parent, items)
            identities = []
            for request, selected in plans:
                child = uuid.uuid4().hex
                data['jobs'].append({'id':child, 'request':request, 'state':'queued', 'attempt':0,
                                     'recovery_id':None, 'items':{}, 'result':None, 'reason':'explicit_retry_failed',
                                     'next_operation':'copy', 'observation':None,
                                     'retry_of':{'job_id':identity, 'attempt':parent['attempt'], 'item_ids':selected}})
                identities.append(child)
            return identities
        return self._change(retry)

    def claim(self):
        def take(data):
            if sum(_busy(j) for j in data['jobs']) >= self.max_active: return None
            now = time.time_ns() // 1000000
            # Wall-clock deadlines survive manager restart. A clock rollback
            # must not turn a bounded delay into an unbounded wait.
            _clamp_deadlines(data, now)
            job = next((j for j in data['jobs'] if j['state'] == 'queued' or
                        (j['state'] == 'retry_waiting' and j['reconnect']['not_before_ms'] <= now)), None)
            if job is None: return None
            reconnect = job['state'] == 'retry_waiting'
            if reconnect and job['next_operation'] == 'copy': job['recovery_id'] = None
            job.update(state='active', attempt=job['attempt'] + 1, items={}, result=None, reason='', observation=None)
            job['stop_requested'] = None
            job.pop('verification', None)
            if 'reconnect' in job:
                job['reconnect'].update(not_before_ms=None, engine_support=False, not_submitted=False, network_errors=0, disqualified=False)
                if 'recovery' in job['reconnect']:
                    job['reconnect']['recovery'].update(disqualified=False, network_errors=0, pending=False, claim=None)
            request = copy.deepcopy(job['request'])
            request.update(id=f"{job['id']}-{job['attempt']}", op=job['next_operation'])
            if request['op'] == 'resume': request['recovery_id'] = job['recovery_id']
            return {'job_id': job['id'], 'request': request}
        return self._change(take)

    def next_reconnect_delay(self):
        """Seconds until a waiting copy is ready; no wait while active slots are full."""
        with self.mutex:
            if sum(_busy(j) for j in self.data['jobs']) >= self.max_active: return None
            now = time.time_ns() // 1000000
            delays = [min(max(0, j['reconnect']['not_before_ms'] - now), j['reconnect']['delays_ms'][j['reconnect']['retries']-1])/1000
                      for j in self.data['jobs'] if _waiting(j) and j['state'] != 'queued']
            return min(delays) if delays else None

    def claim_recovery(self):
        """Reserve one read-only reconciliation cycle under the active-job limit."""
        def take(data):
            if sum(_busy(j) for j in data['jobs']) >= self.max_active: return None
            now = time.time_ns()//1000000; _clamp_deadlines(data, now)
            job = next((j for j in data['jobs'] if j['state'] == 'needs_reconciliation' and
                        j.get('reconnect', {}).get('recovery', {}).get('pending') and j['reconnect']['not_before_ms'] <= now), None)
            if job is None: return None
            claim = uuid.uuid4().hex
            job['reconnect']['not_before_ms'] = None
            job['reconnect']['recovery']['claim'] = claim
            job.update(state='reconciling', reason='automatic_recovery_checking')
            return {'job_id':job['id'], 'claim':claim}
        return self._change(take)

    def finish_recovery(self, identity, claim, error=None):
        """Reaped inspection clients precede durable resume admission or failure."""
        def finish(data):
            job = self._job(data, identity); policy = job.get('reconnect', {})
            recovery = policy.get('recovery')
            if recovery is None or recovery['claim'] != claim or job['state'] not in ('reconciling', 'recoverable'):
                raise ValueError('reconciliation claim is no longer active')
            recovery.update(pending=False, claim=None); policy['not_before_ms'] = None
            if error is None:
                if job['state'] != 'recoverable' or job.get('verification') is None or job.get('stop_requested') is not None:
                    raise ValueError('automatic resume requires verified uncancelled recovery')
                job.update(state='queued', next_operation='resume', reason='policy_verified_resume')
            else:
                job.update(state='needs_reconciliation', reason='automatic_recovery_unavailable')
                job.pop('verification', None)
                if isinstance(error, RecoveryUnavailable) and error.cancelled:
                    job.update(stop_requested='cancel', reason='cancel_requested_outcome_unknown')
                elif isinstance(error, RecoveryUnavailable) and error.retryable:
                    _schedule_recovery(job)
        self._change(finish)

    def cancel_recovery(self, identity):
        """Save cancellation of uncertain work; do not invent a completed cancellation."""
        def cancel(data):
            job = self._job(data, identity)
            if job['state'] not in ('needs_reconciliation', 'reconciling', 'recoverable'):
                raise ValueError('job is not awaiting recovery')
            job.update(state='needs_reconciliation', result=None, stop_requested='cancel', reason='cancel_requested_outcome_unknown')
            if 'reconnect' in job:
                job['reconnect']['not_before_ms'] = None
                if 'recovery' in job['reconnect']: job['reconnect']['recovery'].update(pending=False, claim=None)
        self._change(cancel)

    def record_engine_capabilities(self, identity, request_id, capabilities):
        """Save hello evidence; return an optional copy ID to attach before run()."""
        def record(data):
            job = self._job(data, identity)
            if job['state'] != 'active' or request_id != f"{identity}-{job['attempt']}": raise ValueError('engine capability evidence belongs to another attempt')
            if 'reconnect' in job: job['reconnect']['engine_support'] = capabilities.get('copy_reconnect') == '1'
            # AppClient has negotiated hello, but no operation has been sent.
            # Save our identity before submission can create destination work.
            # Old engines continue to allocate and announce their own identity.
            if (job['next_operation'] == 'copy' and job['request']['options'].get('retain_partials') is True and
                    capabilities.get('copy_recovery_identity') == '1'):
                if job['recovery_id'] is None: job['recovery_id'] = uuid.uuid4().hex
                return job['recovery_id']
            return None
        return self._change(record)

    @staticmethod
    def resolve_request(claim, profile_resolver):
        request = copy.deepcopy(claim['request'])
        cache = {}
        endpoints = [request['endpoint']] if 'endpoint' in request else [request['destination']] + [s['endpoint'] for s in request['sources']]
        for ep in endpoints:
            if ep['kind'] == 'ssh':
                profile = ep.pop('profile_id')
                if profile not in cache: cache[profile] = copy.deepcopy(profile_resolver(profile))
                if not isinstance(cache[profile], dict): raise ValueError('profile resolver must return a connection object')
                ep['connection'] = copy.deepcopy(cache[profile])
        return request

    def accept(self, identity, event):
        if event.get('type') not in ('recovery_preparing', 'recovery_created', 'recovery_resuming', 'item_discovered', 'item_mapping', 'item_result', 'result', 'cancel_ack', 'pause_ack', 'recovery_actor', 'recovery_quiescent', 'copy_not_submitted', 'error', 'phase'):
            return False
        def observe(data):
            job = self._job(data, identity)
            if event.get('type') in ('cancel_ack', 'pause_ack'):
                if job['state'] != 'active' or event.get('job_id') != f"{identity}-{job['attempt']}" or event.get('accepted') is not True: return False
                if event['type'] == 'cancel_ack': job['stop_requested'] = 'cancel'
                elif job.get('stop_requested') != 'cancel': job['stop_requested'] = 'pause'
                return True
            if job['state'] != 'active' or event.get('id') != f"{identity}-{job['attempt']}": return False
            kind = event.get('type')
            policy = job.get('reconnect')
            recovery = policy.get('recovery') if policy is not None else None
            if policy is not None and (kind in ('recovery_actor', 'recovery_created', 'recovery_resuming', 'item_discovered') or
                                       (kind == 'phase' and event.get('phase') == 'scanning')):
                policy['disqualified'] = True
            if kind == 'error':
                if policy is None: return False
                if event.get('operation') == 'ssh_connect' and event.get('category') in ('network', 'network_timeout') and event.get('retryable') is True:
                    policy['network_errors'] = min(64, policy['network_errors'] + 1)
                else: policy['disqualified'] = True
                if recovery is not None:
                    if event.get('category') in ('network', 'network_timeout') and event.get('retryable') is True and event.get('operation') in ('ssh_connect', 'transfer', 'read_transport'):
                        recovery['network_errors'] = min(64, recovery['network_errors'] + 1)
                    else: recovery['disqualified'] = True
            elif kind == 'phase': return policy is not None
            elif kind == 'copy_not_submitted':
                if policy is None: return False
                if event.get('operation') != 'copy' or event.get('endpoint') != 'ssh' or event.get('remote_request_submitted') is not False or event.get('transfer_started') is not False or policy['not_submitted']:
                    raise ValueError('invalid unsubmitted-copy receipt')
                policy['not_submitted'] = True
            elif kind == 'recovery_resuming': return policy is not None
            elif kind == 'recovery_actor':
                recovery = event['recovery_id']; _hex_identity(recovery)
                if job['recovery_id'] is not None and job['recovery_id'] != recovery: raise ValueError('engine changed recovery identity')
                actor = {k:copy.deepcopy(event[k]) for k in ('type', 'endpoint', 'role', 'recovery_id', 'attempt_id', 'actor_path', 'actor_revision')}
                actor['actor_path'] = {'bytes_hex':actor['actor_path']['bytes_hex']}
                _actor(actor, recovery); job['recovery_id'] = recovery
                actors = job.setdefault('actors', [])
                if any(a['attempt_id'] == actor['attempt_id'] and a['role'] == actor['role'] for a in actors): raise ValueError('duplicate actor receipt')
                actors.append(actor)
            elif kind == 'recovery_quiescent':
                if event.get('actor_cleaned') is not True: return False
                matches = [a for a in job.get('actors', []) if _same_actor(a, event)]
                if len(matches) != 1: raise ValueError('close proof lacks its original actor receipt')
                actor = copy.deepcopy(matches[0]); actor['cleaned'] = True
                closed = job.setdefault('closed_actors', [])
                if not any(_same_actor(a, actor) for a in closed): closed.append(actor)
            elif kind in ('recovery_preparing', 'recovery_created'):
                recovery = event['recovery_id']
                if job['recovery_id'] is not None and job['recovery_id'] != recovery: raise ValueError('engine changed recovery identity')
                job['recovery_id'] = recovery
            elif kind == 'item_discovered':
                item_id = event['item_id']
                if item_id in job['items']: raise ValueError('duplicate item discovery')
                item = {k: copy.deepcopy(v) for k, v in event.items() if k in ITEM_FIELDS}
                for field in ('path', 'source_path', 'destination_path'):
                    if field in item: item[field] = {'bytes_hex': item[field]['bytes_hex']}
                item['status'] = 'pending'; job['items'][item_id] = item
            elif kind in ('item_mapping', 'item_result'):
                item = job['items'].get(event['item_id'])
                if item is None or item['status'] != 'pending': raise ValueError('outcome without pending discovery')
                if kind == 'item_mapping': item['destination_path'] = {'bytes_hex': event['destination_path']['bytes_hex']}
                else: item.update({k: copy.deepcopy(v) for k, v in event.items() if k in ITEM_FIELDS - {'path', 'source_path', 'destination_path'}})
            elif kind == 'result':
                status = event['status']
                if status not in RESULTS: raise ValueError('unknown engine result')
                pending = [i for i in job['items'].values() if i['status'] == 'pending']
                if status == 'success' and pending: raise ValueError('success with incomplete item outcomes')
                if status == 'success' and any(i['status'] not in ('success', 'skipped') for i in job['items'].values()):
                    raise ValueError('success with failed or unknown item outcomes')
                for item in pending:
                    item.update(status='unknown', reason='outcome_not_reported', content_published=None, metadata_complete=None)
                job.update(state=status, result={k: event[k] for k in ('status', 'code', 'cleanup', 'durability') if k in event})
                if _can_reconnect(job) and policy['retries'] < len(policy['delays_ms']):
                    delay = policy['delays_ms'][policy['retries']]
                    policy['history'].append({'attempt':job['attempt'], **{k:job['result'][k] for k in ('status', 'code') if k in job['result']}})
                    policy.update(retries=policy['retries']+1, not_before_ms=time.time_ns()//1000000+delay)
                    job.update(state='retry_waiting', reason='unsubmitted_copy_reconnect')
                elif not _can_reconnect(job) and status in ('failure', 'partial_failure') and recovery is not None and recovery['network_errors'] and _can_recover(job):
                    self._unknown(job, 'network_result_requires_reconciliation', copy.deepcopy(job['result']))
            else: return False  # Never save authentication or conflict responses.
            return True
        return self._change(observe)

    def interrupted(self, identity, reason='event_stream_lost'):
        def stop(data):
            job = self._job(data, identity)
            if job['state'] != 'active': raise ValueError('job is not active')
            self._unknown(job, reason)
        self._change(stop)

    def cancel_queued(self, identity):
        def cancel(data):
            job = self._job(data, identity)
            if job['state'] not in ('queued', 'retry_waiting'): raise ValueError('active jobs require engine cancellation')
            job.update(state='cancellation', result={'status': 'cancellation'}, reason='cancelled_before_launch', stop_requested='cancel')
            if 'reconnect' in job: job['reconnect']['not_before_ms'] = None
        self._change(cancel)

    def stop_active(self, identity, client, operation='cancel'):
        """Save user intent before sending a pause/cancel, including lost acknowledgements."""
        if operation not in ('pause', 'cancel'): raise ValueError('invalid stop operation')
        def stop(data):
            job = self._job(data, identity)
            if job['state'] != 'active': raise ValueError('job is not active')
            if job.get('stop_requested') == 'cancel' or job.get('stop_requested') == operation: return None
            job['stop_requested'] = operation
            attempt = f"{identity}-{job['attempt']}"
            return {'id':operation+'-'+attempt, 'op':operation, 'job_id':attempt}
        request = self._change(stop)
        if request is not None: client.send(request)
        return request is not None

    def request_resume(self, identity):
        """Explicit continuation of a paused or reconciled recoverable copy."""
        def resume(data):
            job = self._job(data, identity)
            if job.get('reconnect', {}).get('recovery', {}).get('pending'):
                raise ValueError('automatic recovery still owns this job')
            if job.get('stop_requested') == 'cancel' or job['state'] not in ('paused', 'recoverable') or not job['recovery_id'] or not job['request']['options'].get('retain_partials'):
                raise ValueError('resume requires a confirmed pause or verified recoverable copy')
            job.update(state='queued', next_operation='resume', reason='explicit_resume', stop_requested=None)
        self._change(resume)

    def reconciliation_request(self, identity, claim=None):
        with self.mutex:
            job = self._job(self.data, identity)
            request_id = _recovery_request_id(job, 'inspect', claim)
            if not job['recovery_id']:
                raise ValueError('job has no inspectable recovery identity')
            return {'id': request_id, 'op': 'recovery_state',
                    'endpoint': copy.deepcopy(job['request']['destination']), 'recovery_id': job['recovery_id']}

    def record_reconciliation(self, identity, events, claim=None):
        """Record observations, never turn receipt state into operation success."""
        def inspect(data):
            job = self._job(data, identity)
            expected_id = _recovery_request_id(job, 'inspect', claim)
            observed = [e for e in events if e.get('id') == expected_id]
            if not observed or observed[-1].get('type') != 'result' or observed[-1].get('status') != 'success':
                raise ValueError('reconciliation requires a complete successful inspection')
            states = [e for e in observed if e.get('type') == 'recovery_state']
            if len(states) != 1 or states[0].get('recovery_id') != job['recovery_id']:
                raise ValueError('inspection belongs to another recovery job')
            job['observation'] = {k: states[0][k] for k in ('state', 'files_total')}
            for field in ('job_revision', 'inventory_token'):
                if field in states[0]: job['observation'][field] = copy.deepcopy(states[0][field])
            actors = states[0].get('actors', [])
            if not isinstance(actors, list) or len(actors) > 256: raise ValueError('invalid recovery actor inventory')
            saved = []
            for actor in actors:
                _actor(actor, job['recovery_id'])
                row = copy.deepcopy(actor); row['actor_path'] = {'bytes_hex':actor['actor_path']['bytes_hex']}
                saved.append(row)
            job['observation']['actors'] = saved
            job['reason'] = 'recovery_observed_requires_verification'
            job.pop('verification', None)
            return job['observation']
        return self._change(inspect)

    def verification_request(self, identity, claim=None):
        with self.mutex:
            job = self._job(self.data, identity); observation = job['observation']
            request_id = _recovery_request_id(job, 'verify', claim)
            if not job['recovery_id'] or not job['request']['options'].get('retain_partials') or observation is None or 'job_revision' not in observation or 'inventory_token' not in observation:
                raise ValueError('verification requires a fresh complete recovery inventory')
            request = copy.deepcopy(job['request'])
            request.update(id=request_id, op='verify_recovery', recovery_id=job['recovery_id'],
                           expected_job_revision=copy.deepcopy(observation['job_revision']), expected_inventory_token=observation['inventory_token'])
            return request

    def record_verification(self, identity, events, proofs=(), claim=None):
        """Guards and helper proofs make work resumable, never retroactively successful."""
        def verified(data):
            job = self._job(data, identity); observation = job['observation']
            expected_id = _recovery_request_id(job, 'verify', claim)
            if observation is None: raise ValueError('job is not awaiting verification')
            observed = [e for e in events if e.get('id') == expected_id]
            rows = [e for e in observed if e.get('type') == 'recovery_verified']
            if len(rows) != 1 or not observed or observed[-1].get('type') != 'result' or observed[-1].get('status') != 'success':
                raise ValueError('verification lacks an authoritative successful result')
            row = rows[0]
            if row.get('recovery_id') != job['recovery_id'] or row.get('inventory_token') != observation.get('inventory_token') or row.get('job_revision') != observation.get('job_revision') or row.get('destination_guard_verified') is not True:
                raise ValueError('verification differs from inspected recovery work')
            actors = observation.get('actors', [])
            if any(ep['kind'] == 'ssh' for ep in [job['request']['destination']] + [s['endpoint'] for s in job['request']['sources']]) and not actors:
                raise ValueError('SSH recovery lacks helper lifetime receipts')
            seen = set()
            for actor in actors:
                _actor(actor, job['recovery_id'])
                key = (actor['attempt_id'], actor['role'])
                if key in seen: raise ValueError('duplicate recovery actor')
                seen.add(key)
                if actor.get('cleaned') is True:
                    if not any(_same_actor(saved, actor) and saved['actor_revision'] == actor['actor_revision'] for saved in job.get('closed_actors', [])):
                        raise ValueError('cleaned helper lacks the saved authoritative close proof')
                    continue
                matches = [p for p in proofs if p.get('type') == 'recovery_quiescent' and p.get('recovery_id') == job['recovery_id'] and p.get('attempt_id') == actor['attempt_id'] and p.get('role') == actor['role'] and p.get('endpoint') == actor['endpoint'] and p.get('actor_path', {}).get('bytes_hex') == actor['actor_path']['bytes_hex']]
                if len(matches) != 1: raise ValueError('actor quiescence is unproven')
            proof = {k:row[k] for k in VERIFICATION_COUNTS | {'inventory_token', 'source_verification_required', 'operation_completion_proven'}}
            proof['actors_quiescent'] = True; _verification(proof)
            if job.get('stop_requested') == 'cancel':
                job.update(reason='cancel_requested_work_verified', verification=proof)
            else: job.update(state='recoverable', reason='verified_work_requires_resume', verification=proof)
            return proof
        return self._change(verified)

    def close(self):
        with self.mutex:
            if not self.closed:
                os.close(self.lock_fd); self.closed = True

    def __enter__(self): return self
    def __exit__(self, *_): self.close()


def reconcile_job(queue, identity, binary, *, profile_resolver=None, prompt_handler=None, event_handler=None,
                  retry_delays=(0.1, 0.25, 0.5), claim=None):
    """Inspect, prove helper release, and verify destination/store guards.

    No automatic resume, source removal or cleanup. Resume will freshly scan the
    source and hash candidate bytes before reuse; this operation cannot claim a
    missing transfer result or matching source contents.
    """
    if __package__:
        from .app_client import AppClient, recovery_actor_request
    else:
        from app_client import AppClient, recovery_actor_request
    if not isinstance(retry_delays, (tuple, list)) or len(retry_delays) > 8 or any(type(d) not in (int, float) or not 0 <= d <= 5 for d in retry_delays):
        raise ValueError('invalid bounded reconciliation backoff')
    def run(request, required=None):
        for attempt in range(len(retry_delays)+1):
            client = AppClient(binary)
            try:
                if required is not None and client.capabilities.get(required) != '1': raise RuntimeError('engine lacks recovery verification support')
                def missing_profile(_): raise ValueError('SSH reconciliation requires a runtime profile resolver')
                resolved = queue.resolve_request({'request':request}, profile_resolver or missing_profile)
                # Retain bounded summaries/proofs, not the entire streamed file inventory.
                observed, errors = [], []
                for event in client.run(resolved, prompt_handler=prompt_handler):
                    if event.get('type') in ('recovery_state', 'recovery_verified', 'recovery_quiescent', 'result'):
                        if len(observed) >= 260: raise ValueError('too many recovery proof events')
                        observed.append(event)
                    if event.get('type') == 'error':
                        if len(errors) >= 64: raise ValueError('too many reconciliation errors')
                        errors.append({k:event.get(k) for k in ('category', 'operation', 'retryable')})
                    if event_handler is not None: event_handler(event, client)
                if observed and observed[-1].get('type') == 'result' and observed[-1].get('status') == 'success': return observed
                retryable = bool(errors) and all(e['retryable'] is True and
                    (e['operation'] in ('destination_lock', 'recovery_actor_busy') or e['category'] in ('network', 'network_timeout')) for e in errors)
                cancelled = observed and observed[-1].get('type') == 'result' and observed[-1].get('status') == 'cancellation'
            finally: client.close()
            if not retryable or cancelled or attempt == len(retry_delays):
                raise RecoveryUnavailable('recovery operation did not produce a successful result', retryable=retryable and not cancelled, cancelled=bool(cancelled))
            # Only repeat read-only requests after reaping the previous process.
            # Missing/stale leases, credentials, changed guards and user cancels
            # cannot become automatic retries under a broad retryable flag.
            time.sleep(retry_delays[attempt])
    inspected = run(queue.reconciliation_request(identity, claim))
    queue.record_reconciliation(identity, inspected, claim)
    state = next(e for e in inspected if e['type'] == 'recovery_state')
    actors = state.get('actors', [])
    if not isinstance(actors, list) or len(actors) > 256: raise ValueError('invalid recovery actor inventory')
    job = next(j for j in queue.snapshot() if j['id'] == identity)
    endpoints = [job['request']['destination']] + [s['endpoint'] for s in job['request']['sources']]
    proofs = []
    for index, actor in enumerate(actors):
        _actor(actor, job['recovery_id'])
        if actor.get('cleaned') is True:
            if not any(_same_actor(saved, actor) and saved['actor_revision'] == actor['actor_revision'] for saved in job.get('closed_actors', [])):
                raise ValueError('cleaned helper lacks the saved authoritative close proof')
            continue
        selected = next((ep for ep in endpoints if ep['kind'] == actor['endpoint']), None)
        if selected is None: raise ValueError('recovery actor is outside the queued endpoints')
        request = recovery_actor_request(f'quiet-{claim}-{index}' if claim is not None else f"quiet-{identity}-{job['attempt']}-{index}", selected, actor)
        events = run(request)
        proofs.extend(e for e in events if e['type'] == 'recovery_quiescent')
    verified = run(queue.verification_request(identity, claim), 'recovery_verification')
    return queue.record_verification(identity, verified, proofs, claim)


def execute_next(queue, binary, *, profile_resolver=None, prompt_handler=None,
                 conflict_handler=None, event_handler=None, cancel_after=None):
    """Launch one durably admitted AppClient and persist before notifying the UI.

    Concurrent callers share the journal's active-job limit. Keep the queue open
    until every caller returns. An exception stops this attempt; it never retries
    or advances unknown/cancelled work. event_handler(event, client) may send an
    explicit pause/cancel control while events continue to be consumed.
    """
    if __package__:
        from .app_client import AppClient
    else:
        from app_client import AppClient
    claim = queue.claim()
    if claim is None: return None
    client = None
    try:
        def missing_profile(_): raise ValueError('SSH queue requires a runtime profile resolver')
        request = queue.resolve_request(claim, profile_resolver or missing_profile)
        client = AppClient(binary)
        recovery = queue.record_engine_capabilities(claim['job_id'], request['id'], client.capabilities)
        if recovery is not None: request['recovery_id'] = recovery
        result = None
        for event in client.run(request, cancel_after=cancel_after, prompt_handler=prompt_handler,
                                conflict_handler=conflict_handler):
            queue.accept(claim['job_id'], event)
            if event_handler is not None: event_handler(event, client)
            if event['type'] == 'result': result = event
        if result is None: raise RuntimeError('queued engine lost its authoritative result')
        return result
    finally:
        try:
            if client is not None: client.close()
        finally:
            # A persistence error after rename poisons admission. Leave the disk
            # attempt active for reconciliation when the manager reopens it.
            if not queue.closed and not queue.poisoned:
                row = next(j for j in queue.snapshot() if j['id'] == claim['job_id'])
                if row['state'] == 'active': queue.interrupted(claim['job_id'])


def execute_queue(queue, binary, *, stop_event=None, **options):
    """Yield each authoritative attempt result, waiting for bounded reconnects.

    This is one app-owned worker; other workers share max_active admission. A
    stop_event ends waiting/future dispatch. Active engine jobs still use their
    explicit pause/cancel controls. Exceptions leave unknown work for inspection.
    """
    stopped = stop_event if stop_event is not None else threading.Event()
    while not stopped.is_set():
        result = execute_next(queue, binary, **options)
        if result is not None:
            yield result
            continue
        recovery = queue.claim_recovery()
        if recovery is not None:
            error = None
            try:
                reconcile_job(queue, recovery['job_id'], binary, claim=recovery['claim'], retry_delays=(),
                              **{k:v for k,v in options.items() if k in ('profile_resolver', 'prompt_handler', 'event_handler')})
            except Exception as failure:
                error = failure
            try: queue.finish_recovery(recovery['job_id'], recovery['claim'], error)
            except ValueError:
                # A UI cancellation can retire this read-only claim while its
                # events are draining. No late proof may resurrect that work.
                row = next(j for j in queue.snapshot() if j['id'] == recovery['job_id'])
                if row.get('stop_requested') != 'cancel': raise
            continue
        delay = queue.next_reconnect_delay()
        if delay is None: return
        # An app may cancel/reorder jobs or stop this worker during backoff.
        stopped.wait(min(delay, 0.1))
