#!/usr/bin/env python3
"""Isolate the remote PATH/HOME for lookup tests over actual sshd."""
import json
import os
import shlex
import sys

config = json.loads(os.environ['XSYNC_TEST_LOOKUP'])
prefix = '; '.join('export ' + name + '=' + shlex.quote(value) for name, value in config.items())
host, command = sys.argv[1], ' '.join(sys.argv[2:])
os.execv('/usr/bin/ssh', ['ssh', '-i', '/keys/id test', '-oBatchMode=yes', '-oStrictHostKeyChecking=no',
                         '-oUserKnownHostsFile=/dev/null', '-oLogLevel=ERROR', host, prefix + '; ' + command])
