#!/usr/bin/env python3
"""Run documented xs examples in disposable sandboxes and record their real output.

Each example has hidden setup (`prelude`) and the commands a reader sees (`shown`).
Only the shown commands are captured; stdout, stderr and the exit status are stored
verbatim in docs-inputs/examples.json, apart from the sandbox path. Remote examples
use tests/fakessh.sh, an ssh stand-in that runs the helper on this machine, so
`host:backup/` is a directory inside the sandbox.

    python3 scripts/capture-examples.py [--binary ../../build/xs] [--only NAME...]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parents[1]

# Hidden helpers available to every prelude and shown block.
COMMON = r'''
stamp() { find "$@" -exec touch -h -d '2026-10-10 12:00:00' {} + ; }
mktree() {
  mkdir -p "$1/docs/images" "$1/scripts" "$1/archive"
  printf 'Meeting notes\n' > "$1/notes.txt"
  printf '# Guide\n\nHow to use the archive.\n' > "$1/docs/guide.md"
  printf '<svg xmlns="http://www.w3.org/2000/svg"/>\n' > "$1/docs/images/diagram.svg"
  printf '#!/bin/sh\necho build\n' > "$1/scripts/build.sh"; chmod 755 "$1/scripts/build.sh"
  seq 1 200000 > "$1/archive/2026-q3.log"
  ln -s notes.txt "$1/latest"
  stamp "$1"
}
quiet() { xs "$@" >/dev/null 2>&1; }
'''

EXAMPLES = [
    # --- itemization -------------------------------------------------------
    dict(name='itemize-new', caption='Itemize a fresh copy',
         prelude='mktree src',
         shown='xs -ai src/ dst/'),
    dict(name='itemize-changes', caption='Itemize every kind of change: content, time, mode, owner, group, access time, ACL, xattr, symlink target, new device and FIFO, deletion',
         prelude='''mktree src
mkfifo src/pipe; stamp src/pipe
quiet -aXAUD src/ dst/
printf 'Action items\\n' >> src/notes.txt; stamp src/notes.txt
touch -d '2026-10-11 09:30:00' src/docs/guide.md
chmod 700 src/scripts/build.sh
chown nobody src/archive/2026-q3.log
chgrp nogroup src/notes.txt
mkfifo src/queue; mknod src/null c 1 3; stamp src/queue src/null
setfacl -m u:nobody:r src/docs/images/diagram.svg
python3 -c "import os; os.setxattr('src/docs/images', 'user.origin', b'scanner')"
touch -a -d '2026-10-12 08:00:00' src/docs/guide.md
printf 'New page\\n' > src/docs/faq.md; stamp src/docs/faq.md
ln -sfn docs/guide.md src/latest; stamp src/latest
printf 'old\\n' > dst/stale.txt''',
         shown='xs -aiXAUD --delete src/ dst/'),
    dict(name='itemize-unchanged', caption='Repeat -i to list unchanged entries too',
         prelude='mktree src\nquiet -a src/ dst/',
         shown='xs -aii src/ dst/'),
    dict(name='itemize-hardlinks', caption='Hard-link groups with -H',
         prelude='mktree src\nln src/notes.txt src/docs/notes-link.txt\nln -s guide.md src/docs/readme.md; ln src/docs/readme.md src/docs/readme-link.md; stamp src',
         shown='xs -aiH src/ dst/'),
    dict(name='itemize-checksum', caption='Same size and time, different content: only -c notices',
         prelude='mktree src\nquiet -a src/ dst/\nprintf "Meeting nodes\\n" > src/notes.txt; stamp src/notes.txt\ntouch -d "2026-10-11 07:00:00" src/docs/guide.md',
         shown='xs -aci src/ dst/'),
    dict(name='itemize-no-times', caption='Without -t, updated files get the transfer time (T)',
         prelude='mktree src\nquiet -a src/ dst/\nprintf "Action items\\n" >> src/notes.txt',
         shown='xs -rli src/ dst/'),
    # --- planning and output ----------------------------------------------
    dict(name='dry-run-mirror', caption='Preview a mirror',
         prelude='mktree src\nquiet -a src/ dst/\nprintf "Draft\\n" > src/docs/draft.md\nrm src/docs/images/diagram.svg\nmkdir dst/old; printf "x\\n" > dst/old/a.txt; printf "y\\n" > dst/old/b.txt',
         shown='xs -ani --delete src/ dst/'),
    dict(name='out-format', caption='Choose the fields of each file line',
         prelude='mktree src',
         shown="xs -a --out-format='%o %i %-24n %10l %b' src/ dst/"),
    dict(name='stats', caption='Transfer statistics',
         prelude='mktree src',
         shown='xs -a --stats src/ dst/'),
    dict(name='list', caption='List a directory’s entries',
         prelude='mktree src',
         shown='xs src/'),
    dict(name='list-recursive', caption='List recursively, with symlink targets',
         prelude='mktree src',
         shown='xs -r src/docs'),
    # --- selection --------------------------------------------------------
    dict(name='files-from', caption='Copy a list of names relative to the source',
         prelude='mktree src',
         shown="printf 'notes.txt\\ndocs/guide.md\\n' | xs -ai --files-from=- src/ dst/"),
    dict(name='relative', caption='Keep the path after /./',
         prelude='mktree src',
         shown='xs -aiR src/./docs/guide.md dst/'),
    dict(name='filter-include', caption='Copy only Markdown files, keeping their directories',
         prelude='mktree src',
         shown="xs -ai -m --include='*/' --include='*.md' --exclude='*' src/ dst/"),
    dict(name='max-delete', caption='Stop when a mirror would delete too much',
         prelude='mktree src\nquiet -a src/ dst/\nfor n in 1 2 3; do printf "x\\n" > dst/extra-$n.txt; done',
         shown='xs -a --delete --max-delete=1 src/ dst/; echo "exit status: $?"'),
    # --- snapshots --------------------------------------------------------
    dict(name='link-dest', caption='A dated snapshot that hard-links unchanged files',
         prelude='mktree src\nmkdir snapshots\nquiet -a src/ snapshots/2026-10-09/\nprintf "Action items\\n" >> src/notes.txt',
         shown='xs -ai --link-dest=../2026-10-09 src/ snapshots/2026-10-10/\nstat -c "%h links  %n" snapshots/2026-10-10/notes.txt snapshots/2026-10-10/docs/guide.md'),
    # --- remote -----------------------------------------------------------
    dict(name='push', caption='Push over SSH', remote=True,
         prelude='mktree src',
         shown='xs -azi src/ host:backup/'),
    dict(name='pull', caption='Pull over SSH', remote=True,
         prelude='mktree backup',
         shown='xs -azi host:backup/ restore/'),
    dict(name='push-stats', caption='Wire and compression totals for a push', remote=True,
         prelude='mktree src',
         shown='xs -az --stats src/ host:backup/'),
    # --- fallback and errors ---------------------------------------------
    dict(name='fallback-option', caption='An option xs does not implement runs rsync instead',
         prelude='mktree src\nquiet -a src/ dst/\nprintf "Action items\\n" >> src/notes.txt',
         shown='xs -a --backup src/ dst/\nls dst/notes.txt*'),
    dict(name='strict-option', caption='The same request with fallback disabled',
         prelude='mktree src',
         shown='xs --no-fallback -a --backup src/ dst/; echo "exit status: $?"'),
    dict(name='fallback-helper', caption='No xs on the remote host: rsync carries the transfer', remote=True, helper=False,
         prelude='mktree src',
         shown='xs -az src/ host:backup/; echo "exit status: $?"'),
    dict(name='strict-helper', caption='No xs on the remote host, fallback disabled', remote=True, helper=False,
         prelude='mktree src',
         shown='xs --no-fallback -az src/ host:backup/; echo "exit status: $?"'),
    dict(name='usage-error', caption='A malformed value',
         prelude='mktree src',
         shown='xs --no-fallback -a --bwlimit=fast src/ dst/; echo "exit status: $?"'),
    dict(name='missing-source', caption='A source that does not exist',
         prelude='',
         shown='xs -a missing/ dst/; echo "exit status: $?"'),
    dict(name='strict-feature', caption='A helper without hard-link support, fallback disabled', remote=True, helper='old',
         prelude='mktree src\nln src/notes.txt src/notes-link.txt',
         shown='xs --no-fallback -aH src/ host:backup/; echo "exit status: $?"'),
    dict(name='fallback-feature', caption='The same helper with fallback enabled', remote=True, helper='old',
         prelude='mktree src\nln src/notes.txt src/notes-link.txt',
         shown='xs -aH src/ host:backup/; echo "exit status: $?"\nstat -c "%h links  %n" backup/notes.txt'),
    # --- recipes ----------------------------------------------------------
    dict(name='recipe-snapshots', caption='Dated snapshots that share unchanged files',
         prelude='mktree src\nmkdir snapshots',
         shown="""snapshot() {
  previous=$(ls -1 snapshots | tail -n 1)
  xs -a ${previous:+--link-dest=../$previous} src/ "snapshots/$1/"
}
snapshot 2026-10-09
printf 'Action items\\n' >> src/notes.txt
snapshot 2026-10-10
ls snapshots
stat -c '%h links  %n' snapshots/*/notes.txt snapshots/*/docs/guide.md"""),
    dict(name='mirror-execute', caption='Run the reviewed mirror with a deletion limit',
         prelude='mktree src\nquiet -a src/ dst/\nprintf "Draft\\n" > src/docs/draft.md\nrm src/docs/images/diagram.svg\nmkdir dst/old; printf "x\\n" > dst/old/a.txt; printf "y\\n" > dst/old/b.txt',
         shown='xs -ai --delete --max-delete=10 src/ dst/'),
    dict(name='recipe-install', caption='Install xs on a host that does not have it, then push natively', remote=True, helper=False,
         prelude='mktree src\nmkdir releases\nfor target in linux-amd64 linux-arm64; do cp "$XS_BIN" "releases/xs-$target"; done',
         shown='export XSYNC_RELEASE_DIR=releases\nxs --install user@pi\nxs -azi --no-fallback src/ user@pi:backup/ | tail -n 3'),
    dict(name='recipe-find', caption='Copy the files find selects, with NUL delimiters',
         prelude='mktree src\nprintf "two\\nlines\\n" > "src/docs/odd\nname.md"; stamp src',
         shown="(cd src && find . -name '*.md' -print0) | xs -ai0 --files-from=- src/ dst/"),
    dict(name='recipe-cron', caption='A scheduled backup that logs and keeps the exit status',
         prelude='mktree src',
         shown="""cat > backup.sh <<'SH'
#!/bin/sh
log=backup.log
xs -a --delete --log-file="$log" --out-format='%t %i %n' src/ dst/ > /dev/null
status=$?
echo "$(date -u '+%Y/%m/%d %H:%M:%S') finished with exit status $status" >> "$log"
exit $status
SH
sh backup.sh; echo "exit status: $?"
head -n 3 backup.log; tail -n 1 backup.log"""),
    dict(name='recipe-overnight', caption='A bandwidth-limited push that gives up on a stalled link', remote=True,
         prelude='mktree src',
         shown='xs -az --bwlimit=2M --timeout=60 --stats src/ host:backup/ | tail -n 4'),
    dict(name='recipe-preserve', caption='Preserve hard links, ACLs and extended attributes (Linux)',
         prelude='mktree src\nln src/notes.txt src/notes-link.txt\nsetfacl -m u:nobody:r src/notes.txt\npython3 -c "import os; os.setxattr(\'src/docs/guide.md\', \'user.origin\', b\'scanner\')"',
         shown="xs -aHAXi src/ dst/ | head -n 6\ngetfacl -c dst/notes.txt | grep nobody; getfattr -d dst/docs/guide.md 2>/dev/null | grep origin || python3 -c \"import os; print(os.getxattr('dst/docs/guide.md', 'user.origin'))\""),
    # --- machine-readable progress ----------------------------------------
    dict(name='json-complete', caption='The final JSON record of a transfer',
         prelude='mktree src',
         shown="xs -a --progress=json src/ dst/ 2>&1 >/dev/null | jq -c 'select(.type == \"complete\")'"),
    dict(name='json-files', caption='Transferred files from JSON events',
         prelude='mktree src',
         shown="xs -a --progress=json src/ dst/ 2>&1 >/dev/null | jq -r 'select(.type == \"file\") | [.code, .size, .path] | @tsv' | sort -k3"),
    dict(name='json-python', caption='A Python consumer that ignores diagnostics and reports the outcome',
         prelude='mktree src\nmkdir dst; printf "old\\n" > dst/stale.txt',
         shown="""xs -a --delete --progress=json src/ dst/ 2> events.ndjson
python3 - events.ndjson <<'PY'
import json, sys
events = [json.loads(line) for line in open(sys.argv[1]) if line.startswith('{')]
files = [e for e in events if e['type'] == 'file']
done = events[-1]
print(f"{len(files)} files, {sum(e['bytes'] for e in files):,} bytes sent")
print(f"deleted {done['deleted']}, exit {done['exit_code']}, success {done['success']}")
PY"""),
    dict(name='progress2', caption='rsync-shaped progress lines on a pipe',
         prelude='mktree src',
         shown='xs -a --info=progress2 src/ dst/ 2>&1 | tail -1'),
]


def run(example, binary, old_helper, fakessh, root):
    sandbox = root / example['name']
    sandbox.mkdir()
    (sandbox / 'home').mkdir()
    bin_dir = sandbox / '.bin'
    bin_dir.mkdir()
    helper = example.get('helper', True)
    # The remote lookup searches PATH for xs. Leave it out to simulate a host without xs,
    # or point it at a feature-subset build to simulate an older helper.
    (bin_dir / 'xs').symlink_to(old_helper if helper == 'old' else binary)
    path = (f'{bin_dir}:' if helper else '') + '/usr/local/bin:/usr/bin:/bin'
    env = {'PATH': path, 'HOME': str(sandbox / 'home'), 'TZ': 'UTC', 'LC_ALL': 'C.UTF-8', 'NO_COLOR': '1',
           'XSYNC_CONFIG': '', 'XSYNC_OPTS': '', 'XSYNC_RSH': str(fakessh), 'XS_BIN': str(binary)}
    header = COMMON + 'xs() { "$XS_BIN" "$@"; }\n'
    setup = subprocess.run(['bash', '-c', 'set -e\n' + header + example['prelude']], cwd=sandbox, env=env, capture_output=True, text=True)
    if setup.returncode:
        sys.exit(f'capture-examples: setup for {example["name"]} failed:\n{setup.stderr}')
    shown = subprocess.run(['bash', '-c', header + example['shown']], cwd=sandbox, env=env, capture_output=True, text=True, timeout=60)

    def clean(text):
        return text.replace(str(sandbox) + '/', '').replace(str(sandbox), '.')
    return {'caption': example['caption'], 'command': example['shown'], 'exit_code': shown.returncode,
            'stdout': clean(shown.stdout), 'stderr': clean(shown.stderr), 'remote': bool(example.get('remote')),
            'remote_helper': {True: 'current', False: 'none', 'old': 'feature subset'}[helper]}


parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--binary', type=Path, default=REPO / 'build/xs')
parser.add_argument('--only', nargs='*')
parser.add_argument('--old-helper', type=Path, help='an xs built with -DCMAKE_CXX_FLAGS=-DXSYNC_PROTOCOL_FEATURES=127; '
                    'examples that need it keep their previous capture when it is not given')
args = parser.parse_args()
binary = args.binary.resolve()
fakessh = (REPO / 'tests/fakessh.sh').resolve()
for tool in ('setfacl', 'jq', 'rsync'):
    if not shutil.which(tool):
        sys.exit(f'capture-examples: {tool} is required')
output = SITE / 'docs-inputs/examples.json'
previous = json.loads(output.read_text()) if output.exists() else {}
captured = dict(previous.get('examples', {}))
if not args.only:
    captured = {name: item for name, item in captured.items() if not args.old_helper and item.get('remote_helper') == 'feature subset'}
with tempfile.TemporaryDirectory(prefix='xs-examples-') as temporary:
    for example in EXAMPLES:
        if args.only and example['name'] not in args.only:
            continue
        if example.get('helper') == 'old' and not args.old_helper:
            print(f'{example["name"]}: kept previous capture (no --old-helper)')
            continue
        captured[example['name']] = run(example, binary, args.old_helper and args.old_helper.resolve(), fakessh, Path(temporary))
        print(f'{example["name"]}: exit {captured[example["name"]]["exit_code"]}')
version = subprocess.check_output([str(binary), '--version'], text=True).splitlines()[0]
rsync = subprocess.check_output(['rsync', '--version'], text=True).splitlines()[0]
names = [example['name'] for example in EXAMPLES]
output.write_text(json.dumps({'binary_version': version, 'rsync_version': rsync, 'platform': os.uname().sysname,
                              'examples': {name: captured[name] for name in names if name in captured}},
                             indent=2, ensure_ascii=False) + '\n')
