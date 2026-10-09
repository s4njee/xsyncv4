#!/usr/bin/env python3
"""Test-only remote wrapper: fault settings and PID marker, then exec xsync."""
import json
import os
import sys

with open("/rig/config.json") as stream:
    config = json.load(stream)
with open(config["pid"], "w") as stream:
    stream.write(str(os.getpid()))
env = dict(os.environ)
env.update(config.get("env", {}))
os.execve("/usr/local/bin/xsync", ["xsync", *sys.argv[1:]], env)
