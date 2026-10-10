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


def _median(values):
    import statistics
    return statistics.median(values) if values else None


def _host(target):
    """`user@freya.local:/path` → `freya`."""
    if not target:
        return None
    host = target.split(':', 1)[0].rsplit('@', 1)[-1]
    return host.split('.', 1)[0]


def benchmarks(repo=REPO):
    """Every benchmark run in benchmarks/results, grouped by run id.

    A run is identified by a JSON file carrying `run_id` (a run manifest or host
    record). Result files are those starting with the run id that hold `records`.
    Only verified samples (exit 0 on both ends and verified) are summarized;
    incomplete result files are kept and marked incomplete.
    """
    import json
    results = repo / 'benchmarks/results'
    files = {path.name: json.loads(path.read_text()) for path in sorted(results.glob('*.json'))}
    run_ids = sorted({data['run_id'] for data in files.values() if isinstance(data, dict) and 'run_id' in data})
    runs = []
    for run_id in run_ids:
        mine = {name: data for name, data in files.items() if name.startswith(run_id + '-')}
        meta = next((data for data in mine.values() if data.get('run_id') == run_id), {})
        hosts = [{
            'name': data['hostname'],
            'arch': data['uname'][4] if len(data.get('uname', [])) > 4 else None,
            'kernel': ' '.join(data['uname'][:3:2]) if data.get('uname') else None,
            'cpu': (data.get('cpu_model') or [''])[0].split(':', 1)[-1].strip() or None,
            'cpus': data.get('cpus'),
            'memory': data.get('memory', {}).get('MemTotal'),
            'filesystem': data.get('filesystem'),
        } for data in mine.values() if 'hostname' in data]
        if not hosts and 'filesystem' in meta:
            # Local runs record one host summary in the run record instead of host files.
            client = next((data.get('client') for data in mine.values() if 'records' in data), None)
            lines = meta['filesystem'].strip().splitlines()
            hosts = [{'name': client, 'arch': None, 'kernel': None, 'cpu': None, 'cpus': None,
                      'memory': f"{int(meta['memory_bytes']) // 2**30} GiB" if meta.get('memory_bytes') else None,
                      'filesystem': ' '.join(lines[-1].split()) if lines else None}]
        datasets = {data['dataset']: {key: data[key] for key in ('files', 'directories', 'bytes')}
                    for data in mine.values() if 'dataset' in data and 'files' in data}
        if 'corpus' in meta:
            datasets.setdefault('corpus', meta['corpus'])
        entries = []
        for name, data in mine.items():
            if 'records' not in data or data.get('label') == 'smoke':
                continue
            argv = data.get('argv', [])
            threads = next((argv[index + 1] for index, arg in enumerate(argv[:-1]) if arg == '--threads'), None)
            good = [record for record in data['records'] if record.get('verified') and record.get('returncode') == 0
                    and (not record.get('remote') or record['remote'].get('returncode') == 0)]
            client, server = data.get('client'), _host(data.get('target'))
            flow = 'local' if not server else (f'{client} → {server}' if data['direction'] == 'push' else f'{server} → {client}')
            scenarios = []
            for scenario in sorted({record['scenario'] for record in data['records']},
                                   key=lambda s: ['fresh', 'fresh-z', 'noop', 'checksum', 'tiny'].index(s) if s in ['fresh', 'fresh-z', 'noop', 'checksum', 'tiny'] else 99):
                row = {'scenario': scenario, 'samples': {}, 'median': {}, 'cpu_median': {}, 'rss_mib': {}}
                for tool in ('rsync', 'xs'):
                    records = [record for record in good if record['tool'] == tool and record['scenario'] == scenario]
                    row['samples'][tool] = [round(record['wall_seconds'], 4) for record in records]
                    row['median'][tool] = _median([record['wall_seconds'] for record in records])
                    row['cpu_median'][tool] = _median([record['user_seconds'] + record['system_seconds'] +
                                                       ((record['remote'] or {}).get('user_seconds', 0) + (record['remote'] or {}).get('system_seconds', 0))
                                                       for record in records])
                    rss = [max(record['max_rss_bytes'], (record['remote'] or {}).get('max_rss_bytes', 0)) for record in records]
                    row['rss_mib'][tool] = round(max(rss) / 2**20, 1) if rss else None
                medians = row['median']
                row['speedup'] = medians['rsync'] / medians['xs'] if medians['rsync'] and medians['xs'] else None
                scenarios.append(row)
            entries.append({
                'file': name, 'label': data['label'], 'direction': data['direction'], 'flow': flow,
                'cache': data.get('cache'), 'threads': int(threads) if threads else None,
                'complete': bool(data.get('complete')), 'samples': len(data['records']),
                'unverified': len(data['records']) - len(good), 'versions': data.get('versions', {}),
                'scenarios': scenarios,
            })
        entries.sort(key=lambda entry: (entry['label'], entry['direction'], entry['threads'] or 0))
        revision = meta.get('application_git') or next((entry['versions'].get('xs', '').rsplit(' ', 1)[-1] for entry in entries if entry['versions']), None)
        runs.append({'run_id': run_id, 'source_revision': revision, 'cache': meta.get('cache'),
                     'runs_per_tool': meta.get('runs_per_tool'), 'hosts': hosts, 'datasets': datasets,
                     'loadavg': meta.get('loadavg'), 'results': entries})
    return runs


def option_source(repo=REPO):
    """Option names the parser in src/main.cpp accepts or refuses.

    `recognized` are long names it handles natively (flags also accept --no-NAME);
    `unsupported` are long names it refuses, which therefore delegate to rsync;
    `unsupported_short` maps refused short letters to the long name in their message.
    """
    main = (repo / 'src/main.cpp').read_text()
    table = main[main.index('static const char* unsupported[]'):]
    table = table[:table.index('};')]
    unsupported = sorted(set(re.findall(r'"([a-z0-9-]+)"', table)))
    short = dict(sorted(re.findall(r"case '(.)': usage_error\(\"--([a-z0-9-]+) is not supported by xs\"\)", main)))
    flags = sorted(set(re.findall(r'flag\(o\.\w+, "([a-z0-9-]+)"\)', main)))
    named = set(re.findall(r'name == "([a-z0-9-]+)"', main)) | set(flags)
    named |= {'no-' + flag for flag in flags}
    return {'recognized': sorted(named - set(unsupported)), 'negatable': flags,
            'unsupported': unsupported, 'unsupported_short': short}


def _enum(text, first):
    """Names of the `enum : u8 { FIRST = 1, NEXT, ... }` that starts with FIRST."""
    body = text[text.index('{ ' + first):]
    body = body[2:body.index('}')]
    values, current = [], 0
    for item in (part.strip() for part in body.split(',') if part.strip()):
        name, _, value = (piece.strip() for piece in item.partition('='))
        current = int(value) if value else current + 1
        values.append({'name': name, 'value': current})
    return values


def protocol(repo=REPO):
    """Protocol constants: versions, feature bits, frame and record types, the frozen v3 options."""
    common = (repo / 'src/common.h').read_text()
    remote = (repo / 'src/remote.cpp').read_text()
    bits = [{'name': name, 'value': int(value)} for name, value in re.findall(r'(PF_[A-Z0-9_]+) = (\d+)(?:ULL)?\b', common)]
    apple, other = common.split('#ifdef __APPLE__', 1)[1].split('#else', 1)
    other = other.split('#endif', 1)[0]
    unsupported = lambda block: re.search(r'PF_UNSUPPORTED_NATIVE = ([^;]+);', block)[1].replace(' ', '').split('|')

    def names(macro):
        block = common[common.index('#define ' + macro):]
        block = block[:block.index('\n#define', 1)]
        return re.findall(r'X\((\w+)\)', block)
    version = int(re.search(r'PROTO_VERSION = (\d+);', common)[1])
    return {
        'version': version,
        'min_version': version - int(re.search(r'PROTO_MIN_VERSION = PROTO_VERSION - (\d+);', common)[1]),
        'default_features': int(re.search(r'#define XSYNC_PROTOCOL_FEATURES (\d+)', common)[1]),
        'legacy_v3_features': int(re.search(r'LEGACY_V3_FEATURES = (\d+);', common)[1]),
        'bits': bits,
        'not_advertised': {'macOS': unsupported(apple), 'Linux': unsupported(other)},
        'v3_bool_options': names('WIRE_V3_BOOL_OPTS'),
        'v3_int_options': names('WIRE_V3_INT_OPTS'),
        'frames': _enum(remote, 'F_HELLO'),
        'dir_flags': [dict(name=name, value=int(value)) for name, value in re.findall(r'(DF_\w+) = (\d+)', remote)],
        'records': [dict(name=name, value=int(value)) for name, value in re.findall(r'\b(R_[A-Z_]+) = (\d+)', remote)],
        'header_bytes': int(re.search(r'constexpr size_t HDR = (\d+);', remote)[1]),
        'block_target': 1 << int(re.search(r'BLOCK_TARGET = 1 << (\d+);', remote)[1]),
        'small_max': int(re.search(r'SMALL_MAX = (\d+) << 10;', remote)[1]) << 10,
        'magic': re.search(r'const char MAGIC\[\] = "([^"]+)";', remote)[1],
    }
