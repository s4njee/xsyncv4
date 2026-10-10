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
    changelog = derive.REPO / 'CHANGELOG.md'
    if (SITE / 'docs-inputs/changelog.md').read_text() != changelog.read_text():
        fail('derived: docs-inputs/changelog.md is stale; run `npm run docs:refresh`')
    else:
        ok('derived: docs-inputs/changelog.md matches CHANGELOG.md')
    for name, value in [('exit-codes.json', derive.exit_codes()), ('backlog-status.json', derive.backlog_status()), ('benchmarks.json', derive.benchmarks()),
                        ('option-source.json', derive.option_source()), ('protocol.json', derive.protocol())]:
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
    examples = json.loads((SITE / 'docs-inputs/examples.json').read_text())
    if examples['binary_version'] != meta['line']:
        fail(f'examples: captured from "{examples["binary_version"]}" but help is "{meta["line"]}"; run scripts/capture-examples.py')
    else:
        ok('examples: captured from the same binary as the help')
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


def schema_errors(value, schema, path='$'):
    """Validate VALUE against the subset of JSON Schema that progress.schema.json uses."""
    if 'oneOf' in schema:
        results = [schema_errors(value, option, path) for option in schema['oneOf']]
        matches = [errors for errors in results if not errors]
        if len(matches) == 1:
            return []
        if not matches:
            # Report the closest alternative: the one whose `type` const matches, if any.
            chosen = next((errors for option, errors in zip(schema['oneOf'], results)
                           if isinstance(value, dict) and option.get('properties', {}).get('type', {}).get('const') == value.get('type')), results[0])
            return chosen
        return [f'{path}: matches {len(matches)} alternatives']
    errors = []
    types = schema.get('type')
    if types is not None:
        types = [types] if isinstance(types, str) else types
        checks = {'object': lambda v: isinstance(v, dict), 'string': lambda v: isinstance(v, str), 'boolean': lambda v: isinstance(v, bool),
                  'integer': lambda v: isinstance(v, int) and not isinstance(v, bool), 'null': lambda v: v is None}
        if not any(checks[name](value) for name in types):
            return [f'{path}: expected {"/".join(types)}, got {json.dumps(value)}']
    if 'const' in schema and value != schema['const']:
        errors.append(f'{path}: expected {json.dumps(schema["const"])}, got {json.dumps(value)}')
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: {json.dumps(value)} is not one of {schema["enum"]}')
    if 'minimum' in schema and isinstance(value, int) and value < schema['minimum']:
        errors.append(f'{path}: {value} is below {schema["minimum"]}')
    if 'pattern' in schema and isinstance(value, str):
        import re
        if not re.search(schema['pattern'], value):
            errors.append(f'{path}: {json.dumps(value)} does not match {schema["pattern"]}')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            if key not in value:
                errors.append(f'{path}: missing {key}')
        properties = schema.get('properties', {})
        for key, item in value.items():
            if key in properties:
                errors += schema_errors(item, properties[key], f'{path}.{key}')
            elif schema.get('additionalProperties') is False:
                errors.append(f'{path}: undocumented field {key}')
    return errors


def check_json_schema(binary):
    schema = json.loads((SITE / 'docs/public/progress.schema.json').read_text())
    streams = {'dist/recordings/progress.ndjson': (SITE / 'dist/recordings/progress.ndjson').read_text()}
    if binary.exists():
        with tempfile.TemporaryDirectory(prefix='xsync-site-json-') as temporary:
            root = Path(temporary)
            source = root / 'src'
            (source / 'sub').mkdir(parents=True)
            for index in range(40):
                (source / 'sub' / f'file-{index}.txt').write_text(f'line {index}\n' * (index + 1))
            (source / 'big.bin').write_bytes(bytes(range(256)) * 8192)
            (source / 'odd\tname\x01.txt').write_text('control bytes in the name\n')
            env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FALLBACK='0', XSYNC_RSH=str(derive.REPO / 'tests/fakessh.sh'),
                       PATH=f'{binary.parent}:{os.environ["PATH"]}')
            fresh = [('local copy', ['-a', 'src/', 'dst/']),
                     ('dry run with deletions', ['-an', '--delete', 'src/', 'stale/']),
                     ('checksum re-sync', ['-ac', 'src/', 'dst/']),
                     ('push', ['-az', '--rsync-path=' + str(binary), 'src/', 'host:remote/'])]
            (root / 'stale').mkdir()
            (root / 'stale' / 'old.txt').write_text('old\n')
            for label, argv in fresh:
                result = subprocess.run([str(binary), '--progress=json', *argv], cwd=root, env=env, capture_output=True, text=True)
                if result.returncode:
                    fail(f'json schema: `xs --progress=json {" ".join(argv)}` exited {result.returncode}: {result.stderr.strip()[:200]}')
                streams[f'fresh {label}'] = result.stderr
    else:
        skip(f'json schema: {binary} not built; validating the committed recording only')
    for label, text in streams.items():
        events = [line for line in text.splitlines() if line.startswith('{')]
        problems = [f'line {number}: {error}' for number, line in enumerate(events, 1) for error in schema_errors(json.loads(line), schema)]
        kinds = {json.loads(line)['type'] for line in events}
        if not events or json.loads(events[-1])['type'] != 'complete':
            problems.append('the last event is not a complete record')
        for problem in problems[:5]:
            fail(f'json schema ({label}): {problem}')
        if not problems:
            ok(f'json schema: {len(events)} events from {label} validate ({", ".join(sorted(kinds))})')


def git_changes(*paths):
    result = subprocess.run(['git', 'status', '--porcelain', '--', *paths], cwd=SITE, capture_output=True, text=True)
    return None if result.returncode else result.stdout.strip()


def git_ignored():
    """Build output that .gitignore hides: it would silently never be committed."""
    result = subprocess.run(['git', 'ls-files', '--others', '--ignored', '--exclude-standard', '--', 'dist', 'docs-inputs', 'docs/public', 'docs/*.md'],
                            cwd=SITE, capture_output=True, text=True)
    return result.stdout.strip()


def check_rebuild():
    hidden = git_ignored()
    if hidden:
        fail('rebuild: committed Site output is ignored by git and would never be committed:\n' + hidden)
    before = git_changes('docs', 'dist', 'docs-inputs')
    if before is None:
        return skip('rebuild: not a git checkout')
    if before:
        return skip('rebuild: Site files have uncommitted changes; commit them, then rerun to prove the build reproduces them')
    subprocess.run(['npm', 'run', '--silent', 'build'], cwd=SITE, check=True)
    after = git_changes('docs', 'dist', 'docs-inputs') + git_ignored()
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
check_json_schema(args.binary.resolve())
if not args.no_build:
    check_rebuild()
check_links() if not args.no_build else skip('links: --no-build')
if failures:
    sys.exit(f'\n{len(failures)} check(s) failed.')
print('\nAll Site checks passed.')
