#!/usr/bin/env python3
"""Fail when the Site has drifted from its sources or does not rebuild exactly.

    npm run check                 # every check; run before committing Site changes
    npm run docs:review           # after re-reading curated pages: record new fingerprints

Checks that need the parent repository or a built xs are skipped, with a notice,
when they are unavailable.
"""
import argparse
import datetime
import html.parser
import json
import os
import posixpath
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import derive

SITE = derive.SITE
SOURCES = SITE / 'docs/public/sources.json'
failures = []


def fail(message):
    failures.append(message)
    print('FAIL ' + message)


def ok(message):
    print('ok   ' + message)


def skip(message):
    print('skip ' + message)


def review():
    manifest = json.loads(SOURCES.read_text())
    if not derive.repo_available():
        sys.exit('docs:review needs the parent xsync repository')
    for source in manifest['sources']:
        if not source.get('external'):
            source['sha256'] = derive.sha256(derive.REPO / source['path'])
    manifest['reviewed_at'] = datetime.date.today().isoformat()
    SOURCES.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f'Recorded fingerprints reviewed on {manifest["reviewed_at"]}. Run `npm run build` to update the pages.')


def check_fingerprints():
    stale = derive.stale_sources()
    if stale is None:
        return skip('fingerprints: parent repository not available')
    for source in stale:
        fail(f'fingerprint: {source["path"]} changed since review; re-read {", ".join(source["pages"])}, then `npm run docs:review`')
    if not stale:
        ok('fingerprints: curated sources unchanged since review')


def check_derived():
    if not derive.repo_available():
        return skip('derived inputs: parent repository not available')
    for name, value in [('exit-codes.json', derive.exit_codes()), ('backlog-status.json', derive.backlog_status())]:
        if json.loads((SITE / 'docs-inputs' / name).read_text()) != value:
            fail(f'derived: docs-inputs/{name} is stale; run `npm run docs:refresh`')
        else:
            ok(f'derived: docs-inputs/{name} matches the source')


def check_help(binary):
    captured = (SITE / 'docs-inputs/xs-help.txt').read_text()
    meta = derive.version_meta(captured)
    recordings = json.loads((SITE / 'dist/recordings/sessions.json').read_text())
    if recordings['binary_version'] != meta['line']:
        fail(f'recordings: captured from "{recordings["binary_version"]}" but help is "{meta["line"]}"; recapture both from one binary')
    else:
        ok('recordings: captured from the same binary as the help')
    if not binary.exists():
        return skip(f'help: {binary} not built')
    current = subprocess.check_output([str(binary), '--help'], text=True)
    live = derive.version_meta(current)
    # The git revision changes with every commit; compare everything else.
    if (live['program'], live['version'], live['protocol']) != (meta['program'], meta['version'], meta['protocol']) \
            or current.splitlines()[1:] != captured.splitlines()[1:]:
        fail(f'help: docs-inputs/xs-help.txt differs from `{binary} --help`; run `npm run docs:refresh`')
    else:
        ok(f'help: matches {binary}')


def git_changes(*paths):
    result = subprocess.run(['git', 'status', '--porcelain', '--', *paths], cwd=SITE, capture_output=True, text=True)
    return None if result.returncode else result.stdout.strip()


def check_rebuild():
    before = git_changes('docs', 'dist', 'docs-inputs')
    if before is None:
        return skip('rebuild: not a git checkout')
    if before:
        return skip('rebuild: Site files have uncommitted changes; commit them, then rerun to prove the build reproduces them')
    subprocess.run(['npm', 'run', '--silent', 'build'], cwd=SITE, check=True)
    after = git_changes('docs', 'dist', 'docs-inputs')
    if after:
        fail('rebuild: `npm run build` changed committed output:\n' + after)
    else:
        ok('rebuild: `npm run build` reproduces the committed docs and dist exactly')


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ('href', 'src') and value:
                self.links.append(value)


def broken_links(root, base):
    """Internal href/src targets in ROOT's HTML that do not resolve, served at BASE."""
    broken = []
    for page in sorted(root.rglob('*.html')):
        page_rel = page.relative_to(root).as_posix()
        parser = Links()
        parser.feed(page.read_text())
        for link in parser.links:
            if link.startswith(('http:', 'https:', 'mailto:', '#', 'data:', 'javascript:')):
                continue
            path = link.split('#', 1)[0].split('?', 1)[0]
            if not path:
                continue
            if path.startswith('/'):
                if not path.startswith(base):
                    broken.append(f'{page_rel}: {link} is outside the site base {base}')
                    continue
                rel = path[len(base):]
            else:
                rel = posixpath.normpath(posixpath.join(posixpath.dirname(page_rel), path))
            if rel.startswith('..'):
                broken.append(f'{page_rel}: {link} leaves the site')
                continue
            target = root / rel
            if path.endswith('/') or target.is_dir():
                target = target / 'index.html'
            if not target.exists():
                broken.append(f'{page_rel}: {link} does not exist')
    return broken


def check_links():
    problems = broken_links(SITE / 'dist', '/')
    for problem in problems:
        fail('links (base /): ' + problem)
    if not problems:
        ok('links: every internal link resolves at base /')
    base = '/xsyncv4/'
    with tempfile.TemporaryDirectory(prefix='xsync-site-base-') as temporary:
        root = Path(temporary) / 'site'
        shutil.copytree(SITE / 'dist', root, ignore=lambda directory, names: ['docs'] if Path(directory) == SITE / 'dist' else [])
        subprocess.run(['npx', '--no-install', 'vitepress', 'build', 'docs', '--outDir', str(root / 'docs')],
                       cwd=SITE, check=True, env=dict(os.environ, SITE_BASE=base), stdout=subprocess.DEVNULL)
        problems = broken_links(root, base)
    for problem in problems:
        fail(f'links (base {base}): ' + problem)
    if not problems:
        ok(f'links: every internal link resolves when served at {base}')


parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--review', action='store_true', help='record current fingerprints of the curated sources')
parser.add_argument('--binary', type=Path, default=derive.REPO / 'build/xs')
parser.add_argument('--no-build', action='store_true', help='skip the rebuild and subpath build checks')
args = parser.parse_args()
if args.review:
    review()
    sys.exit()
check_fingerprints()
check_derived()
check_help(args.binary.resolve())
if not args.no_build:
    check_rebuild()
check_links() if not args.no_build else skip('links: --no-build')
if failures:
    sys.exit(f'\n{len(failures)} check(s) failed.')
print('\nAll Site checks passed.')
