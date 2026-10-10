#!/usr/bin/env python3
"""Capture real xs output against disposable fixture trees. No SSH is used."""
import argparse
import datetime
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time

parser = argparse.ArgumentParser()
parser.add_argument('--binary', type=Path, default=Path(__file__).resolve().parents[3] / 'build/xs')
args = parser.parse_args()
binary = args.binary.resolve()
destination = Path(__file__).resolve().parents[1] / 'dist' / 'recordings'
destination.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_PROGRESS='1', NO_COLOR='1', TERM='xterm-256color', LC_ALL='en_US.UTF-8' if sys.platform == 'darwin' else 'C.UTF-8')
ansi = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]')
frame_pattern = re.compile(rb'\x1b\[\?2026h(.*?)\x1b\[\?2026l', re.S)

def clean(data):
    return ansi.sub(b'', data).decode('utf-8').replace('\r', '').strip('\n')

def capture(cwd, flags, name, interrupt_after=None):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 120, 0, 0))
    process = subprocess.Popen([str(binary), *flags], cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=slave, stderr=slave, start_new_session=True)
    os.close(slave)
    started = time.monotonic()
    raw = bytearray()
    frames = []
    parsed = 0
    interrupted = False
    try:
        while True:
            elapsed = time.monotonic() - started
            if elapsed > 30:
                raise TimeoutError(name)
            if interrupt_after and elapsed >= interrupt_after and not interrupted:
                process.send_signal(signal.SIGINT)
                interrupted = True
            if select.select([master], [], [], .02)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                raw.extend(chunk)
                for match in frame_pattern.finditer(raw, parsed):
                    frames.append({'at_ms':round((time.monotonic() - started) * 1000), 'text':clean(match.group(1))})
                    parsed = match.end()
        code = process.wait(timeout=2)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
    tail_start = list(frame_pattern.finditer(raw))[-1].end() if frames else 0
    tail = clean(raw[tail_start:])
    if tail:
        frames.append({'at_ms':round((time.monotonic() - started) * 1000), 'text':tail})
    if not frames:
        raise RuntimeError('No output captured: ' + name)
    (destination / f'{name}.ansi').write_bytes(raw)
    transcript = '\n\n'.join(f'[{frame["at_ms"] / 1000:.3f}s]\n{frame["text"]}' for frame in frames)
    (destination / f'{name}.txt').write_text('xs ' + ' '.join(flags) + '\n\n' + transcript + f'\n\nProcess exit code: {code}\n')
    return {'command':'xs ' + ' '.join(flags), 'exit_code':code, 'frames':frames, 'raw':f'recordings/{name}.ansi', 'transcript':f'recordings/{name}.txt'}

with tempfile.TemporaryDirectory(prefix='xsync-page-recording-') as temporary:
    work = Path(temporary)
    source = work / 'demo-data'
    source.mkdir()
    (source / 'archive.tar').write_bytes(b'archive-data\n' * (256 * 1024))
    (source / 'dataset.bin').write_bytes(b'dataset-record\n' * (192 * 1024))
    (source / 'documents').mkdir()
    for number in range(128):
        (source / 'documents' / f'note-{number:03}.txt').write_text(f'Example document {number}\n' * 40)
    flags = ['-aP', '--no-clone', '--jobs=2', '--bwlimit=1M', './demo-data/', './backup/']
    transfer = capture(work, flags, 'transfer')
    if transfer['exit_code'] != 0:
        raise RuntimeError('Transfer failed')
    for file in source.rglob('*'):
        if file.is_file():
            original = hashlib.sha256(file.read_bytes()).digest()
            copied = hashlib.sha256((work / 'backup' / file.relative_to(source)).read_bytes()).digest()
            if original != copied:
                raise RuntimeError('Content mismatch')
    interrupted = capture(work, [*flags[:-1], './interrupted-backup/'], 'interrupted', interrupt_after=1.8)
    if interrupted['exit_code'] != 20:
        raise RuntimeError('Unexpected interrupt exit code')
    failed = capture(work, ['-aP', './missing-source/', './unused-backup/'], 'error')
    if failed['exit_code'] == 0:
        raise RuntimeError('Missing source unexpectedly succeeded')
    checks = work / 'checks-data'
    checks.mkdir()
    block = b'checksum fixture\n' * 65536
    for number in range(3):
        with (checks / f'volume-{number}.dat').open('wb') as file:
            for repeat in range(96):
                file.write(block)
    shutil.copytree(checks, work / 'checks-backup', copy_function=shutil.copy2)
    for number in range(12):
        original = f'volume-{number % 3}.dat'
        alias = f'part-{number:02}.dat'
        os.link(checks / original, checks / alias)
        os.link(work / 'checks-backup' / original, work / 'checks-backup' / alias)
    verification = capture(work, ['-acP', '--no-clone', './checks-data/', './checks-backup/'], 'verification')
    if verification['exit_code'] != 0:
        raise RuntimeError('Verification failed')
    json_flags = ['-a', '--no-clone', '--jobs=2', '--bwlimit=2M', '--progress=json', './demo-data/', './json-backup/']
    json_run = subprocess.run([str(binary), *json_flags], cwd=work, env=env, capture_output=True, text=True, check=True)
    json_events = [json.loads(line) for line in json_run.stderr.splitlines() if line.startswith('{')]
    if not json_events or json_events[-1].get('success') is not True:
        raise RuntimeError('JSON transfer did not complete')
    (destination / 'progress.ndjson').write_text(json_run.stderr)
    version = subprocess.check_output([str(binary), '--version'], text=True).splitlines()[0]
    recording = {'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'binary_version':version, 'terminal_columns':120, 'transport':'Local filesystem', 'fixture_files':130, 'transfer':transfer, 'verification':verification, 'interrupted':interrupted, 'error':failed, 'json':{'command':'xs ' + ' '.join(json_flags), 'events':json_events, 'download':'recordings/progress.ndjson'}}
    (destination / 'sessions.json').write_text(json.dumps(recording, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'version':version, 'frames':{name:len(recording[name]['frames']) for name in ['transfer','verification','interrupted','error']}, 'has_scanning':any('scanning' in frame['text'] for frame in transfer['frames'] + verification['frames']), 'has_verifying':any('verifying' in frame['text'] for frame in verification['frames']), 'json_events':len(json_events), 'verified_files':130, 'exit_codes':{name:recording[name]['exit_code'] for name in ['transfer','verification','interrupted','error']}}))
