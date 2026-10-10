#!/usr/bin/env python3
"""Generate VitePress manuals from curated content and captured executable help.

Pages come from two places: `scripts/docs_content.py` (the original manuals) and
`content/*.md` (Markdown pages with a small frontmatter block). Both may contain
`<!--generated:NAME-->` placeholders, filled from docs-inputs/ by generated.py.
"""
import json
import re
import sys
from html import escape

import derive
import generated
import options_model
from docs_content import PAGES, doc, p, section, table
from lessons_content import FIGURES as LESSON_FIGURES, LESSONS_PAGE
from roadmap_content import ROADMAP_PAGE

ROOT = derive.SITE
INPUTS = ROOT / 'docs-inputs'
HELP = (INPUTS / 'xs-help.txt').read_text()
META = derive.version_meta(HELP)
GROUPS = ['MANUAL', 'WORKFLOWS', 'REFERENCE', 'PROJECT']
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


BADGES = {'xs-only': 'xs only', 'no-op': 'no-op'}


def see_link(target, pages):
    """`page#anchor` → a link labeled with the page and section names; fails if either is missing."""
    slug, _, anchor = target.partition('#')
    page = next((page for page in pages if page['slug'] == slug), None)
    title = next((item['title'] for item in (page or {}).get('sections', []) if item['id'] == anchor), None) if anchor else ''
    if page is None or title is None:
        sys.exit(f'generate-docs: options: link to {target!r} names a missing page or section')
    label = escape(page['name']) + (f' › {escape(title.title())}' if anchor else '')
    return f'<a href="{slug}.html{"#" + anchor if anchor else ""}">{label}</a>'


def option_row(option, pages):
    labels = [label for label in [BADGES.get(option['class']), option['platform'] and option['platform'] + ' only',
                                  option['features'] and 'helper feature'] if label]
    badges = f'<div class="option-badges">{"".join(f"<span class=\"option-badge\">{label}</span>" for label in labels)}</div>' if labels else ''
    aliases = ''.join(f'<span id="{escape(alias)}" class="option-alias"></span>' for alias in option['aliases'])
    facts = []
    if option['detail']:
        facts.append(f'<p>{option["detail"]}</p>')
    if option['implies']:
        facts.append('<p><strong>Implies</strong> ' + ' '.join(f'<code>{escape(item)}</code>' for item in option['implies']) + '</p>')
    if option['features']:
        facts.append('<p><strong>Remote helpers must support</strong> ' + ', '.join(
            f'<a href="protocol.html#{feature.lower().replace("_", "-")}"><code>{feature}</code></a>' for feature in option['features'])
            + '. A helper without it causes fallback, or exit 4 with <code>--no-fallback</code>.</p>')
    if option['see']:
        facts.append('<p><strong>See</strong> ' + ' · '.join(see_link(target, pages) for target in option['see']) + '</p>')
    details = f'<details><summary>Details</summary>{"".join(facts)}</details>' if facts else ''
    search = escape(' '.join([option['spec'], option['help']]).lower())
    # One code span per form, so a long spec wraps between forms, never inside one.
    spec = ', '.join(f'<code class="nowrap">{escape(form.strip())}</code>' for form in option['spec'].split(','))
    return (f'<tr id="{escape(option["id"])}" class="option-row" data-class="{option["class"]}" data-platform="{escape(option["platform"] or "")}" '
            f'data-feature="{"yes" if option["features"] else "no"}" data-search="{search}">'
            f'<td>{aliases}<a class="option-anchor" href="#{escape(option["id"])}">{spec}</a>{badges}</td>'
            f'<td>{escape(option["help"])}{details}</td></tr>')


def options_page(model, pages):
    intro = (p('Captured from <code>' + escape(META['line']) + '</code>. Every option <code>xs --help</code> lists is below, with a stable link: '
               '<code>options.html#delete</code> for a long option, <code>options.html#z</code> for its short form. '
               'Open <em>Details</em> for what each one implies, which remote-helper features it needs, and where it is explained.')
             + p('<a href="xs-help.txt" download>Original help ↓</a> &nbsp; / &nbsp; <a href="xs.1" download>Manpage ↓</a> &nbsp; / &nbsp; '
                 '<a href="options.json" download>Option data (JSON) ↓</a>')
             + '<OptionFilter />')
    body = [section('source', 'SOURCE', intro)]
    for heading in options_model.CLASSES:
        rows = [option_row(option, pages) for option in model['options'] if option['section'] == heading]
        body.append(section(re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-'), heading.upper(),
                            '<div class="manual-table-wrap"><table class="option-table"><thead><tr><th scope="col">Option</th><th scope="col">Description</th></tr></thead><tbody>'
                            + ''.join(rows) + '</tbody></table></div>'))
    body.append(section('also-accepted', 'ALSO ACCEPTED',
                        p('These rsync spellings work natively but are not listed in <code>--help</code>.')
                        + table(['Option', 'Meaning'], [(f'<code>{escape(item["name"])}</code>', escape(item['help'])) for item in model['unlisted']])))
    body.append(section('delegated', 'DELEGATED TO RSYNC',
                        p('xs does not implement these rsync options. A command that uses one runs a real rsync from <code>PATH</code> instead, with a one-line notice on stderr. With <code>--no-fallback</code> it exits 1. The list is read from the option parser in <code>src/main.cpp</code>.')
                        + '<p class="delegated-list">' + ' '.join(f'<code>{escape(item)}</code>' for item in model['delegated']) + '</p>'
                        + p('See <a href="compatibility.html#fallback">compatibility</a> and <a href="troubleshooting.html#fallback">troubleshooting</a>.')))
    return doc('options', 'xs-options(1)', 'Option reference', 'Every option, with stable links, what it implies, and what a remote helper must support.', 'REFERENCE', body)


def content_pages():
    """Markdown pages in content/. Frontmatter keys: slug, title, name, summary, group, after."""
    pages = []
    for path in sorted((ROOT / 'content').glob('*.md')):
        text = path.read_text()
        match = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
        if not match:
            sys.exit(f'generate-docs: {path.name} has no frontmatter')
        front = dict(re.findall(r'^(\w+):\s*(.*)$', match[1], re.M))
        missing = {'slug', 'title', 'name', 'summary', 'group'} - set(front)
        if missing or front['group'] not in GROUPS:
            sys.exit(f'generate-docs: {path.name} frontmatter needs {sorted(missing) or "a known group"}')
        sections = []
        for heading, ident, body in re.findall(r'^## (.+?) \{#([a-z0-9-]+)\}\n(.*?)(?=^## |\Z)', match[2], re.M | re.S):
            sections.append(section(ident, heading, body.strip() + '\n'))
        page = doc(front['slug'], front['title'], front['name'], front['summary'], front['group'], sections)
        page['after'] = front.get('after')
        pages.append(page)
    return pages


pages = [*PAGES, LESSONS_PAGE, ROADMAP_PAGE]
(ROOT / 'docs/public/charts').mkdir(parents=True, exist_ok=True)
(ROOT / 'docs/public/charts/lessons.json').write_text(json.dumps(LESSON_FIGURES, ensure_ascii=False, separators=(',', ':')) + '\n')
# Place content pages after the page each names, resolving chains such as
# performance → architecture → changelog in whatever order the files sort.
pending = content_pages()
while pending:
    placed = False
    for page in list(pending):
        if any(existing['slug'] == page['slug'] for existing in pages):
            sys.exit(f'generate-docs: duplicate page slug {page["slug"]!r}')
        if page.get('after') == 'options':  # the options page is added later, at a fixed position
            sys.exit('generate-docs: content pages cannot be placed after options')
        anchor = next((index for index, existing in enumerate(pages) if existing['slug'] == page.get('after')), None)
        if page.get('after') and anchor is None:
            continue
        pages.insert(anchor + 1 if anchor is not None else len(pages), page)
        pending.remove(page)
        placed = True
    if not placed:
        sys.exit('generate-docs: cannot place ' + ', '.join(f'{page["slug"]} (after {page["after"]!r})' for page in pending))

MODEL = options_model.build(help_sections(HELP), json.loads((INPUTS / 'option-source.json').read_text()),
                            json.loads((INPUTS / 'protocol.json').read_text()))
pages.insert(8, options_page(MODEL, pages))
(ROOT / 'docs/public/options.json').write_text(json.dumps({'help_version': META['line'], **MODEL}, indent=2, ensure_ascii=False) + '\n')
EXTRA = {'reviewed-at': escape(sources['reviewed_at'])}
for page in pages:
    front = {'title': page['title'], 'description': page['summary'], 'manual': page['title'], 'manualName': page['name'], 'sectionNumber': re.search(r'\((\d)\)', page['title'])[1], **page.get('front', {})}
    text = '---\n' + '\n'.join(f'{k}: {json.dumps(v)}' for k, v in front.items()) + '\n---\n\n'
    deck = page.get('deck') or f'<div class="manual-deck"><strong>{escape(page["name"])}</strong><p>{escape(page["summary"])}</p></div>'
    text += f'# {page["title"]}\n\n{deck}\n\n'
    for item in page['sections']:
        body = item['html']
        # Leave links to the separate product view to the browser, not the docs router.
        body = body.replace('href="../index.html#demo"', 'href="../index.html#demo" target="_self"')
        body = body.replace('Loading captured event…', escape(json.dumps(progress, indent=2)))
        body = body.replace('Loading captured diagnostic…', escape(recordings['error']['frames'][-1]['text']))
        body = re.sub(r'<!--generated:([a-z0-9-]+)-->', lambda match: generated.render(match[1], EXTRA), body)
        body = re.sub(r'<!--example:([a-z0-9-]+)-->', lambda match: generated.example(match[1]), body)
        text += f'## {item["title"]} {{#{item["id"]}}}\n\n{body}\n\n'
    (ROOT / 'docs' / (page['slug'] + '.md')).write_text(text)
sidebar = [{'text': group, 'items': [{'text': page['name'], 'link': '/' if page['slug'] == 'index' else '/' + page['slug']}
                                    for page in pages if page['group'] == group]} for group in GROUPS]
(ROOT / 'docs/.vitepress/sidebar.json').write_text(json.dumps(sidebar, indent=2) + '\n')
(ROOT / 'docs/.vitepress/site-meta.json').write_text(json.dumps({k: META[k] for k in ('program', 'version', 'protocol', 'git')}, indent=2) + '\n')
(ROOT / 'docs/public/xs-help.txt').write_text(HELP)
print(f'Generated {len(pages)} VitePress manuals from executable help and captured output.')

stale = derive.stale_sources()
if stale:
    for source in stale:
        print(f'warning: {source["path"]} changed since review on {sources["reviewed_at"]}; re-read pages: {", ".join(source["pages"])}', file=sys.stderr)
    print('warning: after reviewing, run `npm run docs:review`; `npm run check` fails until then.', file=sys.stderr)
