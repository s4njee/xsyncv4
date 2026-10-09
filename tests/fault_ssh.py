#!/usr/bin/env python3
"""Direct fake SSH for fault tests; avoids macOS SIP shells stripping DYLD env."""
import os
import sys

args = sys.argv[1:]
while args and args[0].startswith("-"):
    args = args[2:] if args[0] in ("-l", "-p", "-i", "-o") else args[1:]
if len(args) < 2:
    sys.exit(255)
if marker := os.environ.get("XSYNC_FAULT_SERVER_PID"):
    with open(marker, "w") as stream:
        stream.write(str(os.getpid()))
os.execvp(args[1], args[1:])
