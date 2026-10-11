#!/usr/bin/env python3
"""Reference client for xs --app; stdout contains live JSON events."""
import argparse
import copy
import json
import os
import pathlib
import select
import subprocess
import time
import sys
import getpass
import queue
import threading


class ListingView:
    """Minimal pane accumulator: a new navigation invalidates older job events."""
    def __init__(self, request_id, endpoint=None):
        self.begin(request_id, endpoint)

    def begin(self, request_id, endpoint=None):
        self.request_id = request_id
        self.entries, self.errors = [], []
        self.status = None
        self.endpoint = copy.deepcopy(endpoint)
        self.invalidated = False

    def invalidate(self, event, operation_endpoint):
        """Route another job's refresh hint using its original endpoint/profile.

        Endpoint kind alone cannot distinguish two SSH hosts. The caller binds
        the job's event to its saved endpoint; never infer a profile from a path.
        """
        if event.get('type') != 'invalidate' or self.endpoint is None:
            return False
        kind = self.endpoint['kind']
        if event.get('endpoint') != kind or operation_endpoint.get('kind') != kind:
            return False
        if kind == 'ssh':
            profile = self.endpoint.get('connection')
            if not isinstance(profile, dict) or not profile.get('host') or profile != operation_endpoint.get('connection'):
                return False
        pane = bytes.fromhex(self.endpoint['path']['bytes_hex']).rstrip(b'/') or b'/'
        path = bytes.fromhex(event['path']['bytes_hex']).rstrip(b'/') or b'/'
        parent = bytes.fromhex(event['parent_path']['bytes_hex']).rstrip(b'/') or b'/'
        descendant = pane.startswith(path + b'/') if path != b'/' else pane.startswith(b'/')
        if pane != path and pane != parent and not (event.get('recursive', True) is True and descendant):
            return False
        self.entries, self.status, self.invalidated = [], None, True
        return True

    def accept(self, event):
        if event['id'] != self.request_id or self.invalidated:
            return False
        if event['type'] == 'entries':
            self.entries.extend(event['entries'])
        elif event['type'] == 'error':
            self.errors.append(event)
        elif event['type'] == 'result':
            self.status = event['status']
        return True


def action_request(request_id, operation, selected_endpoint, parent_revision, entries,
                   names, *, recursive=False, replace=False, destination_name=None,
                   mode=None, mtime=None):
    """Build a revision-bound action from the pane's observed entries, without I/O."""
    observed = {entry['name']['bytes_hex']: entry for entry in entries}
    request = {'id': request_id, 'op': operation, 'endpoint': copy.deepcopy(selected_endpoint),
               'parent_revision': copy.deepcopy(parent_revision), 'items': []}
    for name in names:
        encoded = os.fsencode(name).hex()
        entry = observed.get(encoded)
        if operation != 'mkdir' and entry is None:
            raise ValueError('selected entry is absent from the pane')
        item = {'name': {'bytes_hex': encoded},
                'expected_revision': copy.deepcopy(entry['revision']) if entry else {'exists': False}}
        if operation == 'rename':
            if len(names) != 1 or destination_name is None:
                raise ValueError('reference rename requires one selection and a new name')
            target = os.fsencode(destination_name).hex()
            item['destination_name'] = {'bytes_hex': target}
            item['destination_revision'] = copy.deepcopy(observed[target]['revision']) if target in observed else {'exists': False}
        request['items'].append(item)
    if operation == 'delete': request['recursive'] = recursive
    if operation == 'rename': request['replace'] = replace
    if mode is not None: request['mode'] = str(mode)
    if mtime is not None: request['mtime'] = copy.deepcopy(mtime)
    return request


def prepare_action(binary, operation, selected_endpoint, names, prompt_handler=None, **options):
    """Refresh the pane before an action; failed/incomplete navigation cannot delete."""
    snapshots = {}
    for op in ('lstat', 'list'):
        client = AppClient(binary)
        try:
            events = list(client.run({'id': 'pane', 'op': op, 'endpoint': selected_endpoint},
                                     prompt_handler=prompt_handler))
        finally:
            client.close()
        if not events or events[-1]['type'] != 'result' or events[-1]['status'] != 'success':
            raise RuntimeError('cannot prepare action from an incomplete pane')
        snapshots[op] = events
    parent = next(event['entry'] for event in snapshots['lstat'] if event['type'] == 'entry')
    entries = [entry for event in snapshots['list'] if event['type'] == 'entries' for entry in event['entries']]
    return action_request('job', operation, selected_endpoint, parent['revision'], entries, names, **options)


def prepare_move(binary, request, prompt_handler=None):
    """Bind a move to fresh selected source and destination-directory revisions."""
    request = copy.deepcopy(request)
    request['op'] = 'move'
    def revision(selected):
        client = AppClient(binary)
        try:
            if client.capabilities.get('safe_move') != '1':
                raise RuntimeError('engine does not support safe moves')
            events = list(client.run({'id':'move-preflight', 'op':'lstat', 'endpoint':selected}, prompt_handler=prompt_handler))
        finally:
            client.close()
        if not events or events[-1]['type'] != 'result' or events[-1]['status'] != 'success':
            raise RuntimeError('cannot prepare a move from an incomplete source or destination observation')
        return next(event['entry']['revision'] for event in events if event['type'] == 'entry')
    request['destination_parent_revision'] = revision(request['destination'])
    for selected in request['sources']:
        selected['expected_revision'] = revision(selected['endpoint'])
    return request


def pause_request(request_id, job_id):
    """Stopping is accepted separately from the authoritative paused result."""
    for value in (request_id, job_id):
        if not isinstance(value, str) or not 1 <= len(value) <= 128 or any(not 33 <= ord(c) <= 126 for c in value):
            raise ValueError('pause requires valid request and job IDs')
    return {'id': request_id, 'op': 'pause', 'job_id': job_id}


def recovery_actor_request(request_id, endpoint, actor, cleanup=False):
    """Inspect or explicitly clean one exact helper lifetime receipt."""
    if actor.get('type') != 'recovery_actor' or actor.get('role') not in ('sender', 'receiver'):
        raise ValueError('actor cleanup requires an engine lifetime receipt')
    target = copy.deepcopy(endpoint)
    if target.get('kind') != actor.get('endpoint'):
        raise ValueError('actor endpoint differs from its receipt')
    target['path'] = copy.deepcopy(actor['actor_path'])
    return {'id': request_id, 'op': 'recovery_quiescence', 'endpoint': target,
            'recovery_id': actor['recovery_id'], 'attempt_id': actor['attempt_id'], 'role': actor['role'],
            'expected_actor_revision': copy.deepcopy(actor['actor_revision']), 'cleanup': bool(cleanup)}


def resume_request(request_id, original_copy, recovery_id):
    """Build an explicit copy resume; never infer recovery for a move or delete."""
    if original_copy.get('op') != 'copy':
        raise ValueError('only a copy can be resumed with private partials')
    if len(recovery_id) != 32 or any(c not in '0123456789abcdef' for c in recovery_id):
        raise ValueError('invalid recovery ID')
    request = copy.deepcopy(original_copy)
    request.update(id=request_id, op='resume', recovery_id=recovery_id)
    request['options']['retain_partials'] = True
    return request


def prepare_partial_cleanup(binary, selected_endpoint, recovery_id, prompt_handler=None):
    """Inspect an inactive job before explicitly removing its private scope."""
    client = AppClient(binary)
    try:
        events = list(client.run({'id': 'recovery-inspect', 'op': 'recovery_state',
                                  'endpoint': selected_endpoint, 'recovery_id': recovery_id}, prompt_handler=prompt_handler))
    finally:
        client.close()
    if not events or events[-1]['type'] != 'result' or events[-1]['status'] != 'success':
        raise RuntimeError('cannot clean an active, stale or incomplete recovery observation')
    state = next(event for event in events if event['type'] == 'recovery_state')
    return {'id': 'job', 'op': 'cleanup_partials', 'endpoint': copy.deepcopy(selected_endpoint),
            'recovery_id': recovery_id, 'expected_job_revision': copy.deepcopy(state['job_revision'])}


class MoveInventory:
    """Keep copied, removed and retained outcomes distinct; never blindly retry."""
    def __init__(self, request):
        self.request_id = request['id']
        self.items, self.errors, self.summary = {}, [], None
        self.status = None
        for selected in request['sources']:
            raw = bytes.fromhex(selected['endpoint']['path']['bytes_hex']).rstrip(b'/')
            identity = '' if selected['mode'] == 'contents' else selected.get('destination_name', {}).get('bytes_hex', raw.rsplit(b'/', 1)[-1].hex())
            self.items[identity] = {'status':'unknown', 'source_path':selected['endpoint']['path'],
                                    'copied':None, 'removed':None, 'remaining':None}

    def accept(self, event):
        if event['id'] != self.request_id: return False
        if event['type'] == 'move_discovered':
            self.items[event['item_id']] = dict(copy.deepcopy(event), status='unknown', copied=None, removed=None, remaining=None)
        elif event['type'] == 'move_result': self.items[event['item_id']] = copy.deepcopy(event)
        elif event['type'] == 'move_summary': self.summary = copy.deepcopy(event)
        elif event['type'] == 'error': self.errors.append(copy.deepcopy(event))
        elif event['type'] == 'result':
            self.status = event['status']
            if self.status == 'success' and (self.summary is None or
                    int(self.summary['items_total']) != len(self.items) or
                    any(item['status'] != 'success' for item in self.items.values())):
                raise RuntimeError('move claimed success without complete successful item outcomes')
        return True


class TransferInventory:
    """Reference per-item view; retain final outcomes, not the event history."""
    def __init__(self, request_id):
        self.request_id = request_id
        self.items, self.errors = {}, []
        self.status = None

    def accept(self, event):
        if event['id'] != self.request_id:
            return False
        kind = event['type']
        if kind == 'error':
            self.errors.append(event)
        elif kind == 'item_discovered':
            identity = event['item_id']
            if identity in self.items:
                raise ValueError('duplicate item discovery')
            self.items[identity] = dict(event, status='pending')
        elif kind in ('item_stage', 'item_progress', 'item_retry', 'item_result', 'item_mapping'):
            item = self.items.get(event['item_id'])
            # Source observations can precede receiver discovery. Discovery
            # and results are authoritative; a late source stage cannot undo one.
            if item is None:
                if kind == 'item_result':
                    raise ValueError('item result without discovery')
                return True
            if kind == 'item_result' and item['status'] != 'pending':
                raise ValueError('duplicate item result')
            if kind == 'item_mapping' and item['status'] == 'pending':
                item['destination_path'] = event['destination_path']
            if item['status'] == 'pending':
                # Source-side observations have no destination mapping.
                item.update({key: value for key, value in event.items()
                             if key not in ('destination_path', 'source_path', 'side')})
        elif kind == 'result':
            self.finish(event['status'])
        return True

    def finish(self, status='interrupted'):
        pending = [item for item in self.items.values() if item['status'] == 'pending']
        if status == 'success' and pending:
            raise ValueError('successful job with incomplete item outcomes')
        self.status = status
        for item in pending:
            item.update(status='unknown', reason='outcome_not_reported',
                        content_published=None, metadata_complete=None)

    def _retry_items(self, include_unknown=False):
        if self.status == 'cancellation': return []
        statuses = {'failure'} | ({'unknown'} if include_unknown else set())
        failed = sorted((item for item in self.items.values() if item['status'] in statuses),
                        key=lambda item: len(bytes.fromhex(item['path']['bytes_hex'])))
        selected, parents = [], []
        for item in failed:
            path = bytes.fromhex(item['path']['bytes_hex'])
            if any(path == parent or path.startswith(parent + b'/') or parent == b''
                   for parent in parents):
                continue
            selected.append(item)
            if item['entry_type'] == 'directory':
                parents.append(path)
        return selected

    @staticmethod
    def _retry_selection(item, templates):
        path = bytes.fromhex(item['path']['bytes_hex'])
        ep = copy.deepcopy(templates[item['source_endpoint']])
        ep['path'] = {'bytes_hex': item['source_path']['bytes_hex']}
        selection = {'endpoint': ep, 'mode': 'contents' if path == b'' else 'entry'}
        if path:
            destination = item.get('destination_path')
            name = bytes.fromhex(destination['bytes_hex']).rpartition(b'/')[2] if destination else path.rpartition(b'/')[2]
            if name != bytes.fromhex(item['source_path']['bytes_hex']).rpartition(b'/')[2]:
                selection['destination_name'] = {'bytes_hex': name.hex()}
        return selection

    def retry_selections(self, endpoint_templates=None, include_unknown=False):
        """Selections for root-level failures; nested failures need retry_requests."""
        templates = endpoint_templates or {'local': {'kind': 'local'}}
        items = self._retry_items(include_unknown)
        if any(b'/' in bytes.fromhex(item['path']['bytes_hex']) for item in items):
            raise ValueError('nested failures require retry_requests to preserve destination paths')
        return [self._retry_selection(item, templates) for item in items]

    def retry_requests(self, original_request, include_unknown=False, id_prefix='retry'):
        """Group explicit retries by destination parent; profiles stay client-owned."""
        if original_request['op'] != 'copy' or original_request['id'] != self.request_id:
            raise ValueError('retry requires the original copy request for this inventory')
        templates = {}
        for source in original_request['sources']:
            ep = source['endpoint']
            templates[ep['kind']] = ep
        original_destination = original_request['destination']
        root = bytes.fromhex(original_destination['path']['bytes_hex']).rstrip(b'/') or b'/'
        groups = {}
        for item in self._retry_items(include_unknown):
            relative = bytes.fromhex(item['path']['bytes_hex'])
            mapped = item.get('destination_path')
            target = bytes.fromhex(mapped['bytes_hex']) if mapped else root.rstrip(b'/') + (b'/' + relative if relative else b'')
            if not relative:
                if (target or b'/') != root:
                    raise ValueError('contents retry must retain the original destination root')
                parent = target or b'/'
            else:
                parent, _, name = target.rpartition(b'/')
                parent = parent or b'/'
                suffix = target[len(root.rstrip(b'/'))+1:] if target.startswith(root.rstrip(b'/') + b'/') else b''
                if not suffix or any(part in (b'', b'.', b'..') for part in suffix.split(b'/')):
                    raise ValueError('item destination is outside the original destination scope')
            selection = self._retry_selection(item, templates)
            # Root contents owns its children; directory ancestor pruning above
            # prevents mixing contents and entry selections in the same request.
            groups.setdefault(parent, []).append(selection)
        requests = []
        for index, (parent, sources) in enumerate(groups.items(), 1):
            destination = copy.deepcopy(original_destination)
            destination['path'] = {'bytes_hex': parent.hex()}
            requests.append({'id': f'{id_prefix}-{index}', 'op': 'copy', 'sources': sources,
                             'destination': destination, 'options': copy.deepcopy(original_request['options'])})
        return requests


class TransferPreview:
    """A partial/read-only mirror proposal cannot be submitted as a guarded copy."""
    def __init__(self, request):
        self.request = copy.deepcopy(request)
        self.items, self.summary, self.status = [], None, None

    def accept(self, event):
        if event.get('id') != self.request['id']: return False
        if event['type'] == 'preview_item': self.items.append(copy.deepcopy(event))
        elif event['type'] == 'preview_summary': self.summary = copy.deepcopy(event)
        elif event['type'] == 'result': self.status = event['status']
        return True

    def execution_request(self, request_id):
        summary = self.summary or {}
        guard = summary.get('execution_guard')
        if (self.status != 'success' or summary.get('complete') is not True or
            self.request.get('mode') != 'selected_copy' or summary.get('mode') != 'selected_copy' or
            summary.get('execution_supported') is not True or not isinstance(guard, dict) or
            set(guard) != {'version','mode','token'} or guard.get('token') != summary.get('token') or
            guard.get('version') != '1' or guard.get('mode') != 'selected_copy' or
            not isinstance(guard.get('token'), str) or len(guard['token']) != 32 or
            any(c not in '0123456789abcdef' for c in guard['token'])):
            raise ValueError('preview does not permit a guarded selected copy')
        request = copy.deepcopy(self.request)
        request.update(id=request_id, op='copy', expected_preview=copy.deepcopy(guard))
        request.pop('mode', None)
        return request


class AppClient:
    def __init__(self, binary):
        self.process = subprocess.Popen([str(binary), '--app'], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        start_new_session=True)
        self.pending = b''
        self.send({'id': 'hello', 'op': 'hello', 'schema': '1'})
        self.capabilities = self.receive()
        if self.capabilities['type'] != 'capabilities':
            self.close()
            raise RuntimeError('engine did not negotiate schema 1')

    def send(self, request):
        self.process.stdin.write(json.dumps(request).encode() + b'\n')
        self.process.stdin.flush()

    def receive(self, timeout=None):
        while b'\n' not in self.pending:
            if not select.select([self.process.stdout], [], [], timeout)[0]:
                return None
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                # A missing result is never interpreted as successful completion.
                raise RuntimeError('engine interrupted before an authoritative result')
            self.pending += chunk
            if len(self.pending) > 2*1024*1024:
                raise RuntimeError('engine exceeded its framing limit')
        line, self.pending = self.pending.split(b'\n', 1)
        return json.loads(line)

    def run(self, request, cancel_after=None, prompt_handler=None, conflict_handler=None):
        if ('expected_preview' in request or request.get('op') == 'preview') and self.capabilities.get('transfer_preview') != '1':
            raise RuntimeError('engine does not support the required transfer preview contract')
        self.send(request)
        deadline = None if cancel_after is None else time.monotonic() + cancel_after
        prompts, answers = queue.Queue(maxsize=64), queue.SimpleQueue()
        stopped, worker, cancelling = threading.Event(), None, False
        def reply(event, answer):
            response = {'id': 'decision-' + event['conflict_id'], 'op': 'conflict_response',
                        'job_id': request['id'], 'conflict_id': event['conflict_id'],
                        'revision_token': event['revision_token'], 'decision': 'cancel'}
            if isinstance(answer, str): response['decision'] = answer
            elif answer is not None: response.update(answer)
            try: self.send(response)
            except BrokenPipeError: pass  # Drain a queued terminal result after a late answer.
        def choose():
            while not stopped.is_set():
                try: event = prompts.get(timeout=.1)
                except queue.Empty: continue
                if stopped.is_set(): return
                try: answer = conflict_handler(event)
                except Exception: answer = None
                if not stopped.is_set(): answers.put((event, answer))
        try:
            while True:
                if deadline is not None and time.monotonic() >= deadline:
                    self.send({'id': 'cancel', 'op': 'cancel', 'job_id': request['id']})
                    cancelling = True; stopped.set()
                    deadline = None
                while not answers.empty():
                    prompt, answer = answers.get_nowait()
                    if not cancelling: reply(prompt, answer)
                wait = None if deadline is None else max(0, deadline-time.monotonic())
                if worker is not None: wait = .05 if wait is None else min(wait, .05)
                event = self.receive(wait)
                if event is None:
                    continue
                yield event
                if event['type'] in ('cancel_ack', 'pause_ack') and event.get('accepted'):
                    cancelling = True; stopped.set()
                if event['type'] == 'conflict' and not cancelling:
                    if conflict_handler is None:
                        reply(event, None)
                    else:
                        if worker is None:
                            worker = threading.Thread(target=choose, daemon=True)
                            worker.start()
                        try: prompts.put_nowait(event)
                        except queue.Full: reply(event, None)
                if event['type'] == 'auth_prompt':
                    answer = None if prompt_handler is None else prompt_handler(event)
                    response = {'id': 'answer-' + event['prompt_id'], 'op': 'auth_response',
                                'job_id': request['id'], 'prompt_id': event['prompt_id']}
                    if answer is None:
                        response['cancelled'] = True
                    else:
                        response['answer'] = answer
                    self.send(response)
                if event['type'] == 'result':
                    self.process.wait(timeout=5)
                    return
        finally:
            stopped.set()

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdout.close()
        self.process.stderr.close()


def endpoint(path):
    return {'kind': 'local', 'path': {'bytes_hex': os.fsencode(os.path.abspath(path)).hex()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', default=str(pathlib.Path(__file__).resolve().parents[1] / 'build/xs'))
    parser.add_argument('--cancel-after', type=float)
    parser.add_argument('--ssh-profile', help='JSON file containing the public SSH connection profile')
    parser.add_argument('--interactive-conflicts', action='store_true', help='answer conflict prompts in this client')
    parser.add_argument('--interactive-auth', action='store_true', help='answer SSH prompts in this client; the engine stays headless')
    commands = parser.add_subparsers(dest='op', required=True)
    commands.add_parser('probe')
    for op in ('list', 'stat', 'lstat'):
        commands.add_parser(op).add_argument('path')
    preflight = commands.add_parser('preflight')
    preflight.add_argument('path')
    preflight.add_argument('--regular-file-size', action='append', default=None)
    preflight.add_argument('--jobs', default=None)
    preflight.add_argument('--retained-logical-bytes', default=None)
    commands.add_parser('resolve').add_argument('location', choices=('home', 'root'))
    for operation in ('copy', 'move', 'preview'):
        copy = commands.add_parser(operation)
        copy.add_argument('sources', nargs='+')
        copy.add_argument('destination')
        copy.add_argument('--contents', action='store_true')
        copy.add_argument('--direction', choices=('push', 'pull'), default='push',
                      help='with --ssh-profile, transfer to SSH (push) or from SSH (pull)')
        copy.add_argument('--on-conflict', choices=('replace', 'skip', 'ask'), required=True)
        copy.add_argument('--preserve-times', action='store_true', default=operation == 'move')
        copy.add_argument('--preserve-permissions', action='store_true', default=operation == 'move')
        copy.add_argument('--bandwidth', default='0', help='bytes per second as an exact decimal integer')
        if operation == 'preview': copy.add_argument('--mode', choices=('selected_copy','mirror'), default='selected_copy')
    for operation in ('mkdir', 'delete', 'metadata'):
        action = commands.add_parser(operation)
        action.add_argument('path', help='existing parent directory')
        action.add_argument('names', nargs='+', help='literal selected entry names')
        if operation == 'delete':
            action.add_argument('--recursive', action='store_true', help='explicitly include directory descendants')
        else:
            action.add_argument('--mode', type=lambda text: int(text, 8), help='permission bits in octal')
        if operation == 'metadata':
            action.add_argument('--mtime-seconds')
            action.add_argument('--mtime-nanoseconds', default='0')
    rename = commands.add_parser('rename')
    rename.add_argument('path', help='existing parent directory')
    rename.add_argument('name')
    rename.add_argument('destination_name')
    rename.add_argument('--replace', action='store_true', help='replace the observed target; directories must be empty')
    args = parser.parse_args()
    def conflict_handler(event):
        if not args.interactive_conflicts: return 'cancel'
        actions = ', '.join(event['allowed_actions'])
        try:
            while True:
                print('Conflict at ' + event['path']['display'] + ' [' + actions + ']: ', end='', file=sys.stderr, flush=True)
                answer = input().strip()
                if answer in event['allowed_actions']: return answer
        except EOFError: return 'cancel'
    profile = None
    if args.ssh_profile:
        profile = json.loads(pathlib.Path(args.ssh_profile).read_text())
    if args.op in ('copy', 'move', 'preview') and args.direction == 'pull' and profile is None:
        parser.error('--direction pull requires --ssh-profile')
    def selected_endpoint(path='/'):
        if profile is None:
            return endpoint(path)
        if not os.path.isabs(path):
            parser.error('SSH paths must be absolute; use resolve to discover home/root')
        return {'kind': 'ssh', 'connection': profile, 'path': {'bytes_hex': os.fsencode(path).hex()}}
    def prompt_handler(event):
        if not args.interactive_auth:
            return None
        if event['kind'] in ('host_key', 'confirmation'):
            return input(event['message'])
        return getpass.getpass(event['message'])
    client = AppClient(args.binary)
    try:
        if args.op == 'probe' and profile is None:
            print(json.dumps(client.capabilities), flush=True)
            events = client.run({'id': 'shutdown', 'op': 'shutdown'})
        else:
            request = {'id': 'job', 'op': args.op}
            if args.op == 'probe':
                request['endpoint'] = selected_endpoint()
            if args.op == 'resolve':
                request['location'] = args.location
                if profile is not None:
                    request['endpoint'] = selected_endpoint()
            elif args.op in ('copy', 'move', 'preview'):
                source_endpoint = selected_endpoint if profile is not None and args.direction == 'pull' else endpoint
                destination_endpoint = selected_endpoint if profile is not None and args.direction == 'push' else endpoint
                request['sources'] = [{'endpoint': source_endpoint(s), 'mode': 'contents' if args.contents else 'entry'} for s in args.sources]
                request['destination'] = destination_endpoint(args.destination)
                request['options'] = {'on_conflict': args.on_conflict, 'preserve_times': args.preserve_times,
                                      'preserve_permissions': args.preserve_permissions,
                                      'bandwidth_bytes_per_second': args.bandwidth}
                if args.op == 'move': request = prepare_move(args.binary, request, prompt_handler)
                if args.op == 'preview': request['mode'] = args.mode
            elif args.op in ('mkdir', 'rename', 'delete', 'metadata'):
                options = {}
                if args.op == 'rename':
                    names = [args.name]
                    options.update(destination_name=args.destination_name, replace=args.replace)
                else:
                    names = args.names
                if args.op == 'delete': options['recursive'] = args.recursive
                if args.op in ('mkdir', 'metadata') and args.mode is not None: options['mode'] = args.mode
                if args.op == 'metadata' and args.mtime_seconds is not None:
                    options['mtime'] = {'seconds': args.mtime_seconds, 'nanoseconds': args.mtime_nanoseconds}
                request = prepare_action(args.binary, args.op, selected_endpoint(args.path), names,
                                         prompt_handler, **options)
            elif args.op != 'probe':
                request['endpoint'] = selected_endpoint(args.path)
                if args.op == 'preflight' and any(v is not None for v in (args.regular_file_size,args.jobs,args.retained_logical_bytes)):
                    request['space'] = {'regular_file_sizes':args.regular_file_size or [],'jobs':args.jobs if args.jobs is not None else '64',
                                        'retained_logical_bytes':args.retained_logical_bytes if args.retained_logical_bytes is not None else '0'}
            events = client.run(request, args.cancel_after, prompt_handler, conflict_handler)
        result = None
        for event in events:
            print(json.dumps(event, ensure_ascii=True), flush=True)
            if event['type'] == 'result':
                result = event
        return 0 if result and result['status'] == 'success' else 1
    finally:
        client.close()


if __name__ == '__main__':
    raise SystemExit(main())
