#!/usr/bin/env python3
"""Generate the installed manual from the executable's authoritative --help."""
import argparse
import datetime
import os
import pathlib
import subprocess


def generate(binary, output):
    text = subprocess.check_output([str(binary), '--help'], text=True)
    version = text.splitlines()[0].split('version ', 1)[1].split()[0]
    body = text[text.index('Usage:'):].strip()
    escaped = []
    for line in body.splitlines():
        line = line.replace('\\', r'\e').replace('-', r'\-')
        if line.startswith(('.', "'")): line = r'\&' + line
        escaped.append(line)
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH', '0'))
    date = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime('%Y-%m-%d') if epoch else datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    page = f'.TH XS 1 "{date}" "xs {version}" "User Commands"\n'
    page += '.SH NAME\nxs \\- parallel rsync work-alike\n.SH SYNOPSIS AND OPTIONS\n.nf\n'
    page += '\n'.join(escaped) + '\n.fi\n'
    page += '''.SH ENVIRONMENT
.TP
XSYNC_FALLBACK
Set to 0 to disable automatic rsync fallback. The --fallback flag overrides it.
.TP
XSYNC_OPTS
Shell-quoted default options. Command-line flags override these defaults.
.TP
XSYNC_CONFIG
Optional defaults file; an empty value disables config. Otherwise the default
is $XDG_CONFIG_HOME/xsync/config or ~/.config/xsync/config. Config options are
lower priority than environment defaults. Blank lines and full-line comments
are allowed. Transfer paths and control actions are not defaults.
.TP
XSYNC_RSH
Remote shell command, overriding RSYNC_RSH and default options; --rsh wins.
.TP
RSYNC_RSH
Remote shell command when --rsh and XSYNC_RSH are absent.
.TP
XSYNC_REMOTE_PATH
Additional remote executable path, after PATH and ~/.local/bin/xs.
.TP
XSYNC_RELEASE_DIR
Directory containing release artifacts for the explicit --install command.
.SH COMPATIBILITY
Native peers support the current protocol and its predecessor. Missing remote
helpers, unsupported protocol versions and unsupported options use real rsync
from PATH unless fallback is disabled. Transfers never upload an executable.
.SH SEE ALSO
rsync(1), ssh(1)
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    generate(args.binary, args.output)
