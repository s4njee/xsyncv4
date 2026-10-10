#!/usr/bin/env python3
"""Refresh docs-inputs/ and the manpage from the parent repository and a built xs.

The Site builds from these committed copies, so it does not need the C++ checkout.
Run this after changing the CLI, exit codes or backlog status, then `npm run build`.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import derive

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--binary', type=Path, default=derive.REPO / 'build/xs')
parser.add_argument('--repo', type=Path, default=derive.REPO)
args = parser.parse_args()
binary = args.binary.resolve()
if not binary.exists():
    sys.exit(f'refresh-inputs: {binary} does not exist; build xs first (cmake --build build)')
if not derive.repo_available(args.repo):
    sys.exit(f'refresh-inputs: {args.repo} is not an xsync checkout')

inputs = derive.SITE / 'docs-inputs'
inputs.mkdir(exist_ok=True)
(inputs / 'xs-help.txt').write_text(subprocess.check_output([str(binary), '--help'], text=True))
# Date the manpage by the source commit, so regenerating it is reproducible.
epoch = subprocess.check_output(['git', '-C', str(args.repo), 'log', '-1', '--format=%ct'], text=True).strip()
subprocess.run([sys.executable, str(args.repo / 'tools/help_to_man.py'), str(binary), str(derive.SITE / 'docs/public/xs.1')],
               check=True, env=dict(os.environ, SOURCE_DATE_EPOCH=epoch))
(inputs / 'exit-codes.json').write_text(json.dumps(derive.exit_codes(args.repo), indent=2) + '\n')
(inputs / 'backlog-status.json').write_text(json.dumps(derive.backlog_status(args.repo), indent=2, ensure_ascii=False) + '\n')
print(f'Refreshed docs inputs from {binary} and {args.repo}.')
