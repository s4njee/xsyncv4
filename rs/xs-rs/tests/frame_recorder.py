#!/usr/bin/env python3
"""Run a remote program and log DATA (4) and COMPRESS_CONFIG (37) frame flags."""
import os
import struct
import subprocess
import sys
import threading

log = sys.argv[1]
command = sys.argv[2:]
child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
records = []
lock = threading.Lock()


def exact(stream, length):
    pieces = bytearray()
    while len(pieces) < length:
        data = os.read(stream.fileno(), length - len(pieces))
        if not data:
            return bytes(pieces)
        pieces.extend(data)
    return bytes(pieces)


def forward(source, destination, direction):
    while True:
        header = exact(source, 5)
        if len(header) != 5:
            break
        length, kind = struct.unpack('<IB', header)
        payload = exact(source, length)
        if len(payload) != length:
            break
        if kind in (4, 37):
            with lock:
                records.append((direction, kind, length, payload[0] if payload else -1))
        remaining = memoryview(header + payload)
        while remaining:
            count = os.write(destination.fileno(), remaining)
            remaining = remaining[count:]
    if direction == 'client':
        destination.close()


incoming = threading.Thread(target=forward, args=(sys.stdin.buffer, child.stdin, 'client'), daemon=True)
incoming.start()
forward(child.stdout, sys.stdout.buffer, 'server')
code = child.wait()
with open(log, 'w') as out:
    for record in records:
        out.write('{} {} {} {}\n'.format(*record))
sys.exit(code)
