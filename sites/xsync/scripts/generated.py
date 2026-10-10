"""HTML for `<!--generated:NAME-->` placeholders, built from docs-inputs/.

Every renderer reads committed inputs only, so the Site builds without the C++
checkout. check-docs.py proves those inputs still match the sources.
"""
import json
import re
import sys
from html import escape

import derive
from docs_content import EXIT_CODES, REPO_URL, p, table

INPUTS = derive.SITE / 'docs-inputs'


def load(name):
    return json.loads((INPUTS / name).read_text())


def fail(message):
    sys.exit('generate-docs: ' + message)


def inline_code(text):
    """Escape Markdown text, keeping its `code` spans."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', escape(text))


def evidence(path):
    """Link to a file in the source repository."""
    return f'<a href="{REPO_URL}/blob/main/{escape(path)}">{escape(path.rsplit("/", 1)[-1])} ↗</a>'


def exit_codes():
    derived = load('exit-codes.json')
    codes = [0] + [entry['code'] for entry in derived]
    missing = [code for code in codes if code not in EXIT_CODES]
    if missing:
        fail(f'exit codes {missing} are defined in the source but have no meaning in EXIT_CODES')
    unknown = sorted(set(EXIT_CODES) - set(codes))
    if unknown:
        fail(f'EXIT_CODES documents {unknown}, which the source no longer defines')
    kinds = {entry['code']: entry['summary'] for entry in derived}
    rows = [(f'<code class="nowrap">{code}</code>', EXIT_CODES[code][0], escape(kinds.get(code) or '—')) for code in codes if EXIT_CODES[code][1]]
    unused = [code for code in codes if not EXIT_CODES[code][1]]
    body = table(['Code', 'Meaning', 'Error-summary kind'], rows)
    if unused:
        body += p('Code ' + ', '.join(f'<code>{code}</code>' for code in unused) + ' is defined for rsync compatibility but xs does not currently return it.')
    return body


DONE = {'done'}
CLOSED = {'skipped — user request'}


def backlog_tiers():
    summary = []
    for tier in load('backlog-status.json'):
        items = tier['items']
        done = sum(item['status'] in DONE for item in items)
        closed = sum(item['status'] in CLOSED for item in items)
        summary.append((f'{tier["tier"]} · {escape(tier["title"])}', str(len(items)), str(done), str(closed), str(len(items) - done - closed)))
    return table(['Tier', 'Items', 'Done', 'Closed', 'Open'], summary) + p('“Closed” items were set aside without completion, for example at the user’s request. Statuses use the backlog’s own vocabulary: <code>partial</code>, <code>new</code>, <code>code</code>, <code>confirmed</code> and <code>unverified</code>.')


def backlog_open():
    rows = [(tier['tier'], f'<code>{item["id"]}</code>', inline_code(item['title']), escape(item['status']))
            for tier in load('backlog-status.json') for item in tier['items'] if item['status'] not in DONE | CLOSED]
    return table(['Tier', 'ID', 'Item', 'Status'], rows)


def _seconds(value):
    return '—' if value is None else f'{value:.3f}'


def _spread(samples):
    return '' if len(samples) < 2 else f'<br><small>{min(samples):.3f}–{max(samples):.3f}</small>'


def _bytes(count):
    return f'{count:,}' + (f' <small>({count / 1e9:.2f} GB)</small>' if count >= 1e9 else f' <small>({count / 1e6:.1f} MB)</small>' if count >= 1e6 else '')


def benchmarks():
    """One block per run: hosts, datasets, verified results with spread, then incomplete work."""
    out = ''
    for run in sorted(derive_runs(), key=lambda run: run['run_id'], reverse=True):
        out += f'<h3 id="run-{escape(run["run_id"])}">Run <code>{escape(run["run_id"])}</code></h3>\n\n'
        facts = [f'source revision <code>{escape(run["source_revision"] or "unknown")}</code>']
        if run.get('cache'):
            facts.append('cache policy: ' + escape(run['cache']))
        if run.get('runs_per_tool'):
            facts.append(f'{run["runs_per_tool"]} samples per tool, alternating order')
        if run.get('loadavg'):
            facts.append('starting load average ' + ' / '.join(f'{value:.2f}' for value in run['loadavg']))
        sentence = '; '.join(facts)
        out += p(sentence[0].upper() + sentence[1:] + '.')
        if run['hosts']:
            out += table(['Host', 'CPU', 'Memory', 'Filesystem'], [
                (f'<strong>{escape(host["name"] or "—")}</strong>' + (f'<br><small>{escape(host["kernel"])} · {escape(host["arch"])}</small>' if host.get('kernel') else ''),
                 escape(host['cpu'] or '—') + (f' <small>({host["cpus"]} CPUs)</small>' if host.get('cpus') else ''),
                 escape(host['memory'] or '—'), f'<code>{escape(host["filesystem"] or "—")}</code>') for host in run['hosts']])
        if run['datasets']:
            out += table(['Dataset', 'Files', 'Directories', 'Logical bytes'], [
                (f'<code>{escape(name)}</code>', f'{data["files"]:,}', f'{data["directories"]:,}', _bytes(data['bytes']))
                for name, data in sorted(run['datasets'].items())])
        rows, pending = [], []
        for result in run['results']:
            for row in result['scenarios']:
                median, samples = row['median'], row['samples']
                if not result['complete']:
                    pending.append(f'<code>{escape(result["label"])}</code> {escape(result["flow"])} <code>{escape(row["scenario"])}</code>: '
                                   f'{len(samples["rsync"])} rsync and {len(samples["xs"])} xs verified samples so far'
                                   + (f' (medians {median["rsync"]:.1f} s and {median["xs"]:.1f} s)' if median['rsync'] and median['xs'] else ''))
                    continue
                speedup = row['speedup']
                verdict = '—' if speedup is None else (f'<strong>{speedup:.2f}×</strong>' if speedup >= 1 else f'{speedup:.2f}× <small>(slower)</small>')
                cpu, rss = row['cpu_median'], row['rss_mib']
                rows.append((
                    f'<code>{escape(result["label"])}</code>', escape(result['flow']) + (f'<br><small>-j {result["threads"]}</small>' if result['threads'] else ''),
                    f'<code>{escape(row["scenario"])}</code>', str(len(samples['xs'])),
                    _seconds(median['rsync']) + _spread(samples['rsync']), _seconds(median['xs']) + _spread(samples['xs']), verdict,
                    f'{_seconds(cpu["rsync"])} / {_seconds(cpu["xs"])}', f'{rss["rsync"]} / {rss["xs"]}',
                    evidence('benchmarks/results/' + result['file'])))
        if rows:
            out += table(['Dataset', 'Flow', 'Scenario', 'Samples', 'rsync s', 'xs s', 'xs speedup', 'CPU s rsync / xs', 'Peak MiB rsync / xs', 'Evidence'], rows)
        if pending:
            out += '<aside class="manual-note"><span>IN PROGRESS</span><p>Incomplete measurements, not included above: ' + '; '.join(pending) + '.</p></aside>'
        out += '\n\n'
    return out


def derive_runs():
    return load('benchmarks.json')


_examples = None


def example(name):
    """A captured example: the command a reader runs, then its real output."""
    global _examples
    if _examples is None:
        _examples = load('examples.json')
    if name not in _examples['examples']:
        fail(f'unknown example {name!r}; add it to scripts/capture-examples.py and capture it')
    item = _examples['examples'][name]
    status = item['exit_code']
    tail = item['command'].rsplit('\n', 1)[-1]
    # Examples that print their own status end with `echo "exit status: $?"`.
    label = 'ACTUAL OUTPUT' if 'exit status:' in tail else f'ACTUAL OUTPUT · EXIT {status}'
    out = f'\n\n<div class="example-caption">{escape(item["caption"])}</div>\n\n```sh\n{item["command"]}\n```\n\n'
    # One HTML line: a blank line inside <pre> would end Markdown's HTML block early.
    # v-pre keeps Vue from reading {{ }} in real program output.
    block = lambda text: '<pre><code>' + escape(text.strip('\n')).replace('\n', '&#10;') + '</code></pre>'
    out += f'<div class="captured-doc-output example-output" v-pre><span class="micro">{label}</span>'
    if item['stdout'].strip():
        out += block(item['stdout'])
    if item['stderr'].strip():
        out += '<span class="micro stream-label">STDERR</span>' + block(item['stderr'])
    if not item['stdout'].strip() and not item['stderr'].strip():
        out += '<p class="example-empty">No output.</p>'
    if item['remote']:
        out += ('<p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine'
                + ('' if item['remote_helper'] else ', with no <code>xs</code> on the remote PATH') + '.</p>')
    return out + '</div>\n\n'


def json_schema():
    """Field tables for each --progress=json record type, from the published schema."""
    schema = json.loads((derive.SITE / 'docs/public/progress.schema.json').read_text())
    out = ''
    for record in schema['oneOf']:
        rows = []
        for name, field in record['properties'].items():
            kind = field.get('type', 'string')  # const and enum fields here are all strings
            kind = ' or '.join(kind) if isinstance(kind, list) else kind
            detail = field.get('description', '')
            if 'const' in field:
                detail = (detail + ' ' if detail else '') + f'Always <code>{escape(json.dumps(field["const"]))}</code>.'
            if 'enum' in field:
                detail += ' One of ' + ', '.join(f'<code>{escape(value)}</code>' for value in field['enum']) + '.'
            rows.append((f'<code>{escape(name)}</code>', escape(kind), detail.replace('-c ', '<code>-c</code> ').replace('-n;', '<code>-n</code>;').replace('-i.', '<code>-i</code>.')))
        out += f'<h3 id="record-{record["title"]}"><code>{record["title"]}</code> records</h3>\n\n' + p(escape(record['description'])) + table(['Field', 'Type', 'Meaning'], rows)
    return out


def _protocol():
    import protocol_notes
    data = load('protocol.json')
    for kind, notes, items in [('feature bit', protocol_notes.FEATURES, data['bits']), ('frame', protocol_notes.FRAMES, data['frames']),
                               ('data record', protocol_notes.RECORDS, data['records'])]:
        names = {item['name'] for item in items}
        if names - set(notes):
            fail(f'{kind}s {sorted(names - set(notes))} are defined in the source but missing from scripts/protocol_notes.py')
        if set(notes) - names:
            fail(f'scripts/protocol_notes.py describes {kind}s {sorted(set(notes) - names)} that the source no longer defines')
    return data, protocol_notes


def protocol_features():
    data, notes = _protocol()
    platform = {name: system for system, names in data['not_advertised'].items() for name in names}
    rows = []
    for bit in data['bits']:
        requested, missing = notes.FEATURES[bit['name']]
        flag = f'<br><small>not advertised on {platform[bit["name"]]}</small>' if bit['name'] in platform else ''
        anchor = bit['name'].lower().replace('_', '-')
        rows.append(f'<tr id="{anchor}"><td><a class="option-anchor" href="#{anchor}"><code>{bit["name"]}</code></a>{flag}</td>'
                    f'<td><code>{bit["value"]}</code><br><small>bit {bit["value"].bit_length() - 1}</small></td><td>{requested}</td><td>{missing}</td></tr>')
    return ('<div class="manual-table-wrap"><table><thead><tr><th scope="col">Feature</th><th scope="col">Value</th>'
            '<th scope="col">Requested when</th><th scope="col">Without it</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def protocol_frames():
    data, notes = _protocol()
    frames = table(['Type', 'Frame', 'Purpose'], [(f'<code>{frame["value"]}</code>', f'<code>{frame["name"]}</code>', notes.FRAMES[frame['name']]) for frame in data['frames']])
    records = table(['Flag', 'Record', 'Meaning'], [(f'<code>{record["value"]}</code>', f'<code>{record["name"]}</code>', notes.RECORDS[record['name']]) for record in data['records']])
    return frames + p('Inside a <code>F_DATA</code> block, each file’s data is a sequence of records:') + records


def protocol_constants():
    data, _ = _protocol()
    legacy = [bit['name'] for bit in data['bits'] if data['legacy_v3_features'] & bit['value']]
    rows = [('Current version', f'<code>{data["version"]}</code>'), ('Oldest supported peer', f'<code>{data["min_version"]}</code>'),
            ('Magic', f'<code>{escape(data["magic"])}</code>'), ('Frame header', f'{data["header_bytes"]} bytes: a 4-byte payload length and a 1-byte type'),
            ('DATA block target', f'{data["block_target"] // 2**20} MiB of file data'), ('Small-file limit', f'{data["small_max"] // 2**10} KiB; smaller files are packed together into shared blocks'),
            ('Features assumed for a protocol-3 peer', ', '.join(f'<code>{name}</code>' for name in legacy))]
    return table(['Constant', 'Value'], rows)


def protocol_v3_options():
    data, _ = _protocol()
    return (p(f'{len(data["v3_bool_options"])} flags, one byte each, in this order:') + '<p class="delegated-list">' + ' '.join(f'<code>{name}</code>' for name in data['v3_bool_options']) + '</p>'
            + p(f'Then {len(data["v3_int_options"])} integers as zigzag varints:') + '<p class="delegated-list">' + ' '.join(f'<code>{name}</code>' for name in data['v3_int_options']) + '</p>'
            + p('Then a count and the plain include/exclude rules. Nothing may be added to, removed from or reordered in this layout.'))


def changelog():
    """CHANGELOG.md as Markdown under a manual section: headings demoted, repository links absolute."""
    text = (INPUTS / 'changelog.md').read_text()
    text = re.sub(r'^# .*\n+', '', text, count=1)
    text = re.sub(r'^(#{2,4}) ', lambda match: '#' * (len(match[1]) + 1) + ' ', text, flags=re.M)
    return re.sub(r'\]\((?!https?:|#)([^)]+)\)', lambda match: f']({REPO_URL}/blob/main/{match[1]})', text)


RENDERERS = {
    'exit-codes': exit_codes,
    'backlog-tiers': backlog_tiers,
    'backlog-open': backlog_open,
    'benchmarks': benchmarks,
    'json-schema': json_schema,
    'changelog': changelog,
    'protocol-features': protocol_features,
    'protocol-frames': protocol_frames,
    'protocol-constants': protocol_constants,
    'protocol-v3-options': protocol_v3_options,
}


def render(name, extra):
    if name in extra:
        return extra[name]
    if name not in RENDERERS:
        fail(f'unknown generated section {name!r}')
    return RENDERERS[name]()
