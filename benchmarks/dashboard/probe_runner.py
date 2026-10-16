#!/usr/bin/env python3
"""One JSON snapshot of a driver host's runner, for the dashboard. Read-only.

Run on the driver as `python3 - ROOT < probe_runner.py`: it reads the files
runner.py and agent.py write under ROOT/runs and changes nothing.
"""
import json
import os
import pathlib
import shutil
import socket
import sys
import time

SAMPLE_TAIL = 40   # most recent samples sent in full
BACKLOG_SHOWN = 40  # pending runs listed in order


def read_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError):
        return default


def read_lines(path):
    try:
        return [line.strip() for line in pathlib.Path(path).read_text().splitlines() if line.strip()]
    except OSError:
        return []


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def plan_summary(directory):
    plan = read_json(directory / 'plan.json')
    if plan is None:
        job = read_json(directory / 'job.json')
        return {'kind': 'job', 'experiment': (job or {}).get('name', directory.name), 'steps': len((job or {}).get('steps', []))}
    arms = plan.get('arms', [])
    return {'experiment': plan.get('experiment'), 'kind': plan.get('kind'), 'hypothesis': plan.get('hypothesis'),
            'primary': plan.get('primary'), 'control': plan.get('control'), 'hours': plan.get('hours'),
            'link': next(iter(plan.get('links', {})), None), 'arms': [arm['name'] for arm in arms],
            'cells': len(plan.get('cells', [])), 'blocks': len(plan.get('blocks', [])),
            'samples': len(plan.get('blocks', [])) * len(arms), 'writes': plan.get('writes', {}),
            'hosts': sorted(plan.get('hosts', {}))}


def slim(record):
    """The fields of a sample record the dashboard shows."""
    seconds = record.get(record.get('_primary') or 'durable_s') or record.get('durable_s') or record.get('wall_s')
    size = record.get('corpus_bytes')
    return {'utc': record.get('utc_start'), 'cell': record.get('cell_id'), 'arm': record.get('arm'),
            'block': record.get('block'), 'attempt': record.get('attempt'), 'position': record.get('position'),
            'valid': record.get('valid'), 'void': record.get('void_reason'), 'wall_s': record.get('wall_s'),
            'durable_s': record.get('durable_s'), 'seconds': seconds, 'bytes': size,
            'gbps': (size * 8 / seconds / 1e9) if size and seconds else None,
            'control': record.get('control'), 'client_cpu': _cpu(record.get('client')), 'peer_cpu': _cpu(record.get('peer'))}


def _cpu(measure):
    if not measure:
        return None
    return (measure.get('user_seconds') or 0) + (measure.get('system_seconds') or 0)


def progress(records, control, primary):
    """Per cell: each arm's median time and its ratio to the control over the blocks where both are valid."""
    cells = {}
    for record in records:
        if not record.get('valid'):
            continue
        value = record.get(primary) or record.get('durable_s')
        if not value:
            continue
        cell = cells.setdefault(record['cell_id'], {})
        cell.setdefault(record['arm'], {})[(record.get('block'), record.get('attempt'))] = value
    out = []
    for cell_id, arms in sorted(cells.items()):
        base = arms.get(control, {})
        entry = {'cell': cell_id, 'arms': {}}
        for arm, values in sorted(arms.items()):
            times = sorted(values.values())
            median = times[len(times) // 2]
            ratios = [values[key] / base[key] for key in values if key in base and base[key] > 0]
            geo = None
            if ratios and arm != control:
                logs = sum(__import__('math').log(r) for r in ratios) / len(ratios)
                geo = __import__('math').exp(logs)
            entry['arms'][arm] = {'n': len(times), 'median_s': median, 'ratio': geo, 'pairs': len(ratios)}
        out.append(entry)
    return out


def host_health(root):
    load = os.getloadavg() if hasattr(os, 'getloadavg') else None
    disk = shutil.disk_usage(root) if os.path.exists(root) else None
    return {'load': list(load) if load else None, 'cpus': os.cpu_count(),
            'disk_free': disk.free if disk else None, 'disk_total': disk.total if disk else None}


def main():
    root = pathlib.Path(sys.argv[1])
    runs = root / 'runs'
    snapshot = {'host': socket.gethostname(), 'utc': time.time(), 'root': str(root), 'health': host_health(str(root))}
    status = read_json(runs / 'runner-status.json')
    if status is None:
        snapshot['runner'] = None
        print(json.dumps(snapshot))
        return
    status['alive'] = alive(status.get('pid'))
    status['paused'] = (runs / '.pause').exists()
    snapshot['runner'] = status
    current = status.get('current') or {}
    if current.get('run'):
        directory = runs / current['run']
        summary = plan_summary(directory)
        records = []
        try:
            with open(directory / 'samples.jsonl') as stream:
                records = [json.loads(line) for line in stream if line.strip()]
        except (OSError, ValueError):
            pass
        snapshot['current'] = {'run': current['run'], 'lane': current.get('lane'), 'started_utc': current.get('started_utc'),
                               'plan': summary, 'status': read_json(directory / 'status.json'),
                               'samples': [slim(r) for r in records[-SAMPLE_TAIL:]],
                               'progress': progress(records, summary.get('control'), summary.get('primary') or 'durable_s'),
                               'valid': sum(1 for r in records if r.get('valid')), 'voided': sum(1 for r in records if not r.get('valid'))}
    for name, key in (('backlog.txt', 'backlog'), ('standing.txt', 'standing')):
        pending, done = [], 0
        for run_id in read_lines(runs / name):
            directory = runs / run_id
            if (directory / 'status.json').exists():
                done += 1
                continue
            if not ((directory / 'plan.json').exists() or (directory / 'job.json').exists()):
                continue
            if len(pending) < BACKLOG_SHOWN:
                pending.append(dict(plan_summary(directory), run=run_id))
            else:
                pending.append({'run': run_id})
        snapshot[key] = {'pending': pending[:BACKLOG_SHOWN], 'pending_count': len(pending), 'done_count': done}
    print(json.dumps(snapshot))


if __name__ == '__main__':
    main()
