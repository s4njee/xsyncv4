"""The option data model: `xs --help` joined with curated notes and the parser's own tables.

build() fails the docs build on any gap: a --help option without notes, notes for an
option --help no longer lists, a long name the parser does not accept, an unknown
feature bit, or a duplicate anchor.
"""
import re
import sys

from option_notes import NOTES, UNLISTED

CLASSES = {
    'Options (same meaning as rsync)': 'native',
    'Documented compatibility no-ops': 'no-op',
    'xs extensions': 'xs-only',
}


def fail(message):
    sys.exit('generate-docs: options: ' + message)


def _name(form):
    """`--rsh=COMMAND` → `--rsh`; `--progress[=json]` → `--progress`."""
    return re.split(r'[=\[]', form, 1)[0]


def build(sections, source, protocol):
    recognized = set(source['recognized'])
    bits = {bit['name']: bit['value'] for bit in protocol['bits']}
    options, used, anchors = [], set(), set()
    for heading, rows in sections:
        if heading not in CLASSES:
            fail(f'unknown --help section {heading!r}; add it to CLASSES')
        for spec, text in rows:
            forms = [form.strip() for form in spec.split(',')]
            names = [_name(form) for form in forms]
            longs = [name for name in names if name.startswith('--')]
            shorts = [name for name in names if not name.startswith('--')]
            key = longs[0] if longs else shorts[0]
            if key not in NOTES:
                fail(f'{spec!r} is in --help but has no entry in scripts/option_notes.py')
            used.add(key)
            for name in longs:
                if name[2:] not in recognized:
                    fail(f'{name} is in --help but src/main.cpp does not parse it')
            note = NOTES[key]
            for feature in note.get('features', []):
                if feature not in bits:
                    fail(f'{key} names unknown feature bit {feature}')
            argument = next((re.split(r'[=\[]', form, 1)[1].strip('[]=') for form in forms if re.search(r'[=\[]', form)), None)
            anchor = key.lstrip('-')
            aliases = [short.lstrip('-') for short in shorts if short.lstrip('-') != anchor]
            for item in [anchor, *aliases]:
                if item in anchors:
                    fail(f'anchor {item!r} is used twice')
                anchors.add(item)
            options.append({
                'id': anchor, 'aliases': aliases, 'spec': spec, 'long': longs, 'short': shorts, 'argument': argument,
                'help': text, 'class': CLASSES[heading], 'section': heading,
                'implies': note.get('implies', []), 'features': note.get('features', []),
                'platform': note.get('platform'), 'see': note.get('see', []), 'detail': note.get('detail'),
            })
    stale = sorted(set(NOTES) - used)
    if stale:
        fail(f'scripts/option_notes.py documents {stale}, which --help no longer lists')
    unlisted = []
    for name, text in UNLISTED.items():
        if name != '--no-OPTION' and name[2:] not in recognized:
            fail(f'{name} is listed as accepted, but src/main.cpp does not parse it')
        unlisted.append({'name': name, 'help': text})
    delegated = sorted({'--' + name for name in source['unsupported']} |
                       {f'-{letter}, --{name}' for letter, name in source['unsupported_short'].items()},
                       key=lambda item: item.split('--')[-1])
    # A short refusal duplicates its long name; keep the combined form only.
    combined = {item.split('--')[-1] for item in delegated if ',' in item}
    delegated = [item for item in delegated if ',' in item or item[2:] not in combined]
    return {'options': options, 'unlisted': unlisted, 'delegated': delegated}
