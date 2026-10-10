#!/usr/bin/env python3
"""Generate VitePress manuals from curated content and captured executable help."""
import json
import re
from pathlib import Path
from html import escape
from docs_content import PAGES, doc, section, p, table

ROOT = Path(__file__).resolve().parents[1]
HELP = (ROOT / 'docs-inputs/xsync-help.txt').read_text()
recordings = json.loads((ROOT / 'dist/recordings/sessions.json').read_text())
events = [json.loads(line) for line in (ROOT / 'dist/recordings/progress.ndjson').read_text().splitlines() if line.startswith('{')]
progress = next(event for event in events if event['type'] == 'progress' and event.get('phase') == 'transferring')
sections = []
for heading, body in re.findall(r'^([^\n]+):\n(.*?)(?=^\S[^\n]+:\n|\Z)', HELP, re.M | re.S):
    if heading.startswith('Usage'):
        continue
    rows = []
    for line in body.splitlines():
        match = re.match(r'^\s+(-\S.*?)(?:\s{2,}(.*))?$', line)
        if match:
            rows.append([f'<code>{escape(match[1].strip())}</code>', escape(match[2] or '')])
        elif rows and line.strip():
            rows[-1][1] += ' ' + escape(line.strip())
    if rows:
        sections.append(section(re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-'), heading.upper(), table(['OPTION', 'DESCRIPTION'], rows)))
options = doc('options', 'xsync-options(1)', 'Option reference', 'The complete option list, generated from the executable’s own help.', 'REFERENCE', [section('source', 'SOURCE', p('Captured from <code>' + escape(HELP.splitlines()[0]) + '</code>. This is the current native help; delegated options and platform limits are covered in <a href="compatibility.html">compatibility</a>.') + p('<a href="xsync-help.txt" download>Download original help ↗</a> &nbsp; / &nbsp; <a href="xs.1" download>Download generated manpage ↗</a>')), *sections])
pages = [*PAGES]
pages.insert(8, options)
for page in pages:
    front = {'title': page['title'], 'description': page['summary'], 'manual': page['title'], 'manualName': page['name'], 'sectionNumber': re.search(r'\((\d)\)', page['title'])[1]}
    text = '---\n' + '\n'.join(f'{k}: {json.dumps(v)}' for k,v in front.items()) + '\n---\n\n'
    text += f'# {page["title"]}\n\n<div class="manual-deck"><strong>{escape(page["name"])}</strong><p>{escape(page["summary"])}</p></div>\n\n'
    for item in page['sections']:
        body = item['html']
        # Leave links to the separate product view to the browser, not the docs router.
        body = body.replace('href="../index.html#demo"', 'href="../index.html#demo" target="_self"')
        body = body.replace('Loading captured event…', escape(json.dumps(progress, indent=2)))
        body = body.replace('Loading captured diagnostic…', escape(recordings['error']['frames'][-1]['text']))
        text += f'## {item["title"]} {{#{item["id"]}}}\n\n{body}\n\n'
    (ROOT / 'docs' / (page['slug'] + '.md')).write_text(text)
sidebar = []
for group in ['MANUAL','WORKFLOWS','REFERENCE','PROJECT']:
    sidebar.append({'text':group,'items':[{'text':page['name'], 'link':'/' if page['slug']=='index' else '/'+page['slug']} for page in pages if page['group']==group]})
(ROOT / 'docs/.vitepress/sidebar.json').write_text(json.dumps(sidebar, indent=2) + '\n')
(ROOT / 'docs/public/xsync-help.txt').write_text(HELP)
print(f'Generated {len(pages)} VitePress manuals from executable help and captured output.')
