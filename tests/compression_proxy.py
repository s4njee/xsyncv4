#!/usr/bin/env python3
"""Test-only transparent native frame recorder around a real remote helper."""
import argparse
import json
import os
import struct
import subprocess
import sys
import threading
import time


def exact(stream, length):
    chunks = bytearray()
    while len(chunks) < length:
        data = os.read(stream.fileno(), length - len(chunks))
        if not data: return bytes(chunks)
        chunks.extend(data)
    return bytes(chunks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True)
    parser.add_argument('--rate', type=float, default=0, help='bytes per second the client may send: a slow link')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    child = subprocess.Popen(args.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
    records, lock = [], threading.Lock()
    def forward(source, destination, direction):
        while True:
            header = exact(source, 5)
            if len(header) != 5: break
            length, kind = struct.unpack('<IB', header)
            payload = exact(source, length)
            if len(payload) != length: break
            if kind in (4, 37):
                with lock:
                    records.append({'direction': direction, 'kind': kind, 'bytes': length,
                                    'flag': payload[0] if payload else None})
            if args.rate and direction == 'client': time.sleep((5 + length) / args.rate)
            remaining = memoryview(header + payload)
            while remaining:
                count = os.write(destination.fileno(), remaining)
                remaining = remaining[count:]
        if direction == 'client': destination.close()
    incoming = threading.Thread(target=forward, args=(sys.stdin.buffer, child.stdin, 'client'), daemon=True)
    incoming.start()
    forward(child.stdout, sys.stdout.buffer, 'server')
    code = child.wait()
    with lock:
        with open(args.log, 'w') as out: json.dump(records, out)
    return code


if __name__ == '__main__': sys.exit(main())
