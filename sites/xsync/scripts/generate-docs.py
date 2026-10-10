#!/usr/bin/env python3
"""Generate VitePress manuals from curated content and captured executable help."""
import json
import re
import sys
from html import escape

import derive
from docs_content import EXIT_CODES, PAGES, doc, p, section, table

ROOT = derive.SITE
INPUTS = ROOT / 'docs-inputs'
HELP = (INPUTS / 'xs-help.txt').read_text()
META = derive.version_meta(HELP)
recordings = json.loads((ROOT / 'dist/recordings/sessions.json').read_text())
events = [json.loads(line) for line in (ROOT / 'dist/recordings/progress.ndjson').read_text().splitlines() if line.startswith('{')]
progress = next(event for event in events if event['type'] == 'progress' and event.get('phase') == 'transferring')
sources = json.loads((ROOT / 'docs/public/sources.json').read_text())

# Rows the help prints without a description of their own.
HELP_DESCRIPTIONS = {'--version, --help': 'print the version, or this help, and exit'}


def help_sections(text):
    """Option tables from --help. An option spec is comma-separated forms such as
    `-v, --verbose` or `--rsync-path=PROGRAM`; its description follows the first
    space that is not part of the spec, however many spaces separate them."""
    result = []
    for heading, body in re.findall(r'^([^\n]+):\n(.*?)(?=^\S[^\n]+:\n|\Z)', text, re.M | re.S):
        if heading.startswith('Usage'):
            continue
        rows = []
        for line in body.splitlines():
            match = re.match(r'^\s+(-[^\s,]+(?:,\s+-[^\s,]+)*)(?:\s+(.*))?$', line)
            if match:
                rows.append([match[1], (match[2] or '').strip()])
            elif rows and line.strip():
                rows[-1][1] = (rows[-1][1] + ' ' + line.strip()).strip()
        for row in rows:
            row[1] = row[1] or HELP_DESCRIPTIONS.get(row[0], '')
            if not row[1]:
                sys.exit(f'generate-docs: option {row[0]!r} has no description in --help')
        if rows:
            result.append((heading, rows))
    return result


def exit_code_table():
    derived = json.loads((INPUTS / 'exit-codes.json').read_text())
    codes = [0] + [entry['code'] for entry in derived]
    missing = [code for code in codes if code not in EXIT_CODES]
    if missing:
        sys.exit(f'generate-docs: exit codes {missing} are defined in the source but have no meaning in EXIT_CODES')
    unknown = sorted(set(EXIT_CODES) - set(codes))
    if unknown:
        sys.exit(f'generate-docs: EXIT_CODES documents {unknown}, which the source no longer defines')
    kinds = {entry['code']: entry['summary'] for entry in derived}
    rows = [(f'<code class="nowrap">{code}</code>', EXIT_CODES[code][0], escape(kinds.get(code) or '—')) for code in codes if EXIT_CODES[code][1]]
    unused = [code for code in codes if not EXIT_CODES[code][1]]
    body = table(['Code', 'Meaning', 'Error-summary kind'], rows)
    if unused:
        body += p('Code ' + ', '.join(f'<code>{code}</code>' for code in unused) + ' is defined for rsync compatibility but xs does not currently return it.')
    return body


def inline_code(text):
    """Escape backlog Markdown text, keeping its `code` spans."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', escape(text))


DONE = {'done'}
CLOSED = {'skipped — user request'}


def backlog_tables():
    tiers = json.loads((INPUTS / 'backlog-status.json').read_text())
    summary, open_rows = [], []
    for tier in tiers:
        items = tier['items']
        done = [item for item in items if item['status'] in DONE]
        closed = [item for item in items if item['status'] in CLOSED]
        rest = [item for item in items if item['status'] not in DONE | CLOSED]
        summary.append((f'{tier["tier"]} · {escape(tier["title"])}', str(len(items)), str(len(done)), str(len(closed)), str(len(rest))))
        open_rows += [(tier['tier'], f'<code>{item["id"]}</code>', inline_code(item['title']), escape(item['status'])) for item in rest]
    tiers_html = table(['Tier', 'Items', 'Done', 'Closed', 'Open'], summary)
    tiers_html += p('“Closed” items were set aside without completion, for example at the user’s request. Statuses use the backlog’s own vocabulary: <code>partial</code>, <code>new</code>, <code>code</code>, <code>confirmed</code> and <code>unverified</code>.')
    return tiers_html, table(['Tier', 'ID', 'Item', 'Status'], open_rows)


tiers_html, open_html = backlog_tables()
GENERATED = {
    'exit-codes': exit_code_table(),
    'backlog-tiers': tiers_html,
    'backlog-open': open_html,
    'reviewed-at': escape(sources['reviewed_at']),
}

sections = [section(re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-'), heading.upper(),
                    table(['OPTION', 'DESCRIPTION'], [(f'<code>{escape(spec)}</code>', escape(text)) for spec, text in rows]))
            for heading, rows in help_sections(HELP)]
options = doc('options', 'xs-options(1)', 'Option reference', 'The complete option list, generated from the executable’s own help.', 'REFERENCE', [section('source', 'SOURCE', p('Captured from <code>' + escape(META['line']) + '</code>. This is the current native help; delegated options and platform limits are covered in <a href="compatibility.html">compatibility</a>.') + p('<a href="xs-help.txt" download>Download original help ↗</a> &nbsp; / &nbsp; <a href="xs.1" download>Download generated manpage ↗</a>')), *sections])
pages = [*PAGES]
pages.insert(8, options)
for page in pages:
    front = {'title': page['title'], 'description': page['summary'], 'manual': page['title'], 'manualName': page['name'], 'sectionNumber': re.search(r'\((\d)\)', page['title'])[1]}
    text = '---\n' + '\n'.join(f'{k}: {json.dumps(v)}' for k, v in front.items()) + '\n---\n\n'
    text += f'# {page["title"]}\n\n<div class="manual-deck"><strong>{escape(page["name"])}</strong><p>{escape(page["summary"])}</p></div>\n\n'
    for item in page['sections']:
        body = item['html']
        # Leave links to the separate product view to the browser, not the docs router.
        body = body.replace('href="../index.html#demo"', 'href="../index.html#demo" target="_self"')
        body = body.replace('Loading captured event…', escape(json.dumps(progress, indent=2)))
        body = body.replace('Loading captured diagnostic…', escape(recordings['error']['frames'][-1]['text']))
        body = re.sub(r'<!--generated:([a-z-]+)-->', lambda match: GENERATED[match[1]], body)
        text += f'## {item["title"]} {{#{item["id"]}}}\n\n{body}\n\n'
    (ROOT / 'docs' / (page['slug'] + '.md')).write_text(text)
sidebar = []
for group in ['MANUAL', 'WORKFLOWS', 'REFERENCE', 'PROJECT']:
    sidebar.append({'text': group, 'items': [{'text': page['name'], 'link': '/' if page['slug'] == 'index' else '/' + page['slug']} for page in pages if page['group'] == group]})
(ROOT / 'docs/.vitepress/sidebar.json').write_text(json.dumps(sidebar, indent=2) + '\n')
(ROOT / 'docs/.vitepress/site-meta.json').write_text(json.dumps({k: META[k] for k in ('program', 'version', 'protocol', 'git')}, indent=2) + '\n')
(ROOT / 'docs/public/xs-help.txt').write_text(HELP)
print(f'Generated {len(pages)} VitePress manuals from executable help and captured output.')

stale = derive.stale_sources()
if stale:
    for source in stale:
        print(f'warning: {source["path"]} changed since review on {sources["reviewed_at"]}; re-read pages: {", ".join(source["pages"])}', file=sys.stderr)
    print('warning: after reviewing, run `npm run docs:review`; `npm run check` fails until then.', file=sys.stderr)
