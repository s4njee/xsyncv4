"""Derive documentation inputs from the parent xsync repository.

refresh-inputs.py writes these results into docs-inputs/; check-docs.py
re-derives them and fails when the committed copies are stale.
"""
import re
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parents[1]


def repo_available(repo=REPO):
    return (repo / 'src/common.h').exists() and (repo / 'backlog.md').exists()


def _switch_strings(text, function):
    """Map RERR_* names to the strings returned by a `switch` in FUNCTION."""
    start = text.index(function)
    body = text[start:text.index('\n}', start)]
    return dict(re.findall(r'case (RERR_\w+|\d+): return "([^"]*)";', body))


def exit_codes(repo=REPO):
    """Exit codes from the RERR_* enum, with the final-line and summary wording."""
    common = (repo / 'src/common.h').read_text()
    enum = common[common.index('// rsync exit codes'):]
    enum = enum[enum.index('enum {'):enum.index('};')]
    values = {name: int(value) for name, value in re.findall(r'(RERR_\w+)\s*=\s*(\d+)', enum)}
    final = _switch_strings((repo / 'src/main.cpp').read_text(), 'const char* rerr_name(int c)')
    summary = _switch_strings((repo / 'src/util.cpp').read_text(), 'const char* error_kind(size_t code)')
    codes = [{'code': value, 'name': name, 'final': final.get(name), 'summary': summary.get(name)}
             for name, value in sorted(values.items(), key=lambda item: item[1])]
    # 255 is not an enum value: it is the remote shell's own failure status, passed through.
    if '255' in summary:
        codes.append({'code': 255, 'name': None, 'final': None, 'summary': summary['255']})
    return codes


def _cells(row):
    return [cell.strip().replace('\\|', '|') for cell in re.split(r'(?<!\\)\|', row.strip().strip('|'))]


def backlog_status(repo=REPO):
    """Tier tables from backlog.md: ID, title and status of every item."""
    tiers = []
    tier = None
    for line in (repo / 'backlog.md').read_text().splitlines():
        heading = re.match(r'^## (P\d) — (.+)$', line)
        if heading:
            tier = {'tier': heading[1], 'title': heading[2], 'items': []}
            tiers.append(tier)
            continue
        if line.startswith('## '):
            tier = None
            continue
        if tier is None or not re.match(r'^\| [A-Z]-\d+ \|', line):
            continue
        cells = _cells(line)
        title = re.match(r'\*\*(.+?)\*\*', cells[1])
        tier['items'].append({
            'id': cells[0],
            'title': (title[1] if title else cells[1]).rstrip('.'),
            'status': cells[2].replace('**', '').strip(),
            'size': cells[4] if len(cells) > 4 else None,
        })
    return [tier for tier in tiers if tier['items']]


def sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stale_sources(repo=REPO):
    """Fingerprinted sources whose content changed since the curated pages were reviewed.

    Returns None when the parent repository is not available (a standalone Site build).
    """
    import json
    manifest = json.loads((SITE / 'docs/public/sources.json').read_text())
    if not repo_available(repo):
        return None
    stale = []
    for source in manifest['sources']:
        if source.get('external'):
            continue
        path = repo / source['path']
        current = sha256(path) if path.exists() else None
        if current != source['sha256']:
            stale.append({**source, 'current': current})
    return stale


def version_meta(help_text):
    """Version, protocol and revision from the first line of `xs --help`."""
    first = help_text.splitlines()[0]
    match = re.match(r'^(\S+)\s+version (\S+)\s+protocol version (\d+)\s+git (\S+)', first)
    if not match:
        raise ValueError('unrecognized --help version line: ' + first)
    return {'program': match[1], 'version': match[2], 'protocol': int(match[3]), 'git': match[4], 'line': first}
