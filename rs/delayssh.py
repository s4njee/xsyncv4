#!/usr/bin/env python3
"""A stand-in for ssh that adds a round trip: like tests/fakessh.sh it drops the ssh options and the host and runs
the remote command locally, but every byte each way is held for half the round trip before it is passed on.

    xs -e 'rs/delayssh.py 11' SRC/ fake:DST/        # an 11 ms round trip

Only latency is added: data is stamped as it arrives and released when its time comes, so the bandwidth is the
pipe's (about 300 MB/s through the relay), with at most WINDOW bytes in flight each way. Used by rs/race.py --rtt.
"""
import collections
import os
import subprocess
import sys
import threading
import time

OPTIONS_WITH_ARGUMENT = set('BbcDEeFIiJLlmOopQRSWw')
WINDOW = 64 << 20  # bytes held in flight each way, like a transport's window: backpressure still reaches the sender


def remote_command(argv):
    while argv:
        word = argv[0]
        if word == '--':
            argv = argv[1:]
            break
        if len(word) == 2 and word[0] == '-' and word[1] in OPTIONS_WITH_ARGUMENT:
            argv = argv[2:]
        elif word.startswith('-') and len(word) > 1:
            argv = argv[1:]
        else:
            break
    if len(argv) < 2:
        sys.exit('delayssh: need a host and a remote command')
    return ' '.join(argv[1:])


def relay(source, sink, delay):
    """Copy source to sink, each chunk released `delay` seconds after it was read; close sink at the end."""
    held = collections.deque()
    ready = threading.Condition()

    in_flight = [0]

    def read():
        while True:
            chunk = os.read(source, 1 << 20)
            with ready:
                while in_flight[0] > WINDOW:
                    ready.wait()
                held.append((time.monotonic() + delay, chunk))
                in_flight[0] += len(chunk)
                ready.notify_all()
            if not chunk:
                return

    threading.Thread(target=read, daemon=True).start()
    try:
        while True:
            with ready:
                while not held:
                    ready.wait()
                due, chunk = held.popleft()
                in_flight[0] -= len(chunk)
                ready.notify_all()
            wait = due - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            if not chunk:
                return
            view = memoryview(chunk)
            while view:
                view = view[os.write(sink, view):]
    except BrokenPipeError:
        pass
    finally:
        os.close(sink)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    delay = float(sys.argv[1]) / 2000
    child = subprocess.Popen(['/bin/sh', '-c', remote_command(sys.argv[2:])], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)
    up = threading.Thread(target=relay, args=(0, os.dup(child.stdin.fileno()), delay), daemon=True)
    child.stdin.close()
    up.start()
    relay(child.stdout.fileno(), os.dup(1), delay)
    os._exit(child.wait())  # the upstream relay may still be blocked reading the client's side


if __name__ == '__main__':
    main()
