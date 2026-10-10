"""Roadmap page: a timeline of experiments and features, condensed from ROADMAP.md."""
from docs_content import doc, section, p

EXPERIMENT, FEATURE, HARNESS = 'experiment', 'feature', 'harness'
KIND_LABEL = {EXPERIMENT: 'EXPERIMENT', FEATURE: 'FEATURE', HARNESS: 'MEASUREMENT'}
STATUS_LABEL = {'active': 'IN PROGRESS', 'planned': 'PLANNED', 'ongoing': 'ONGOING'}


def item(ref, kind, title, text, success, prior='', backlog='', status='planned'):
    return {'ref': ref, 'kind': kind, 'title': title, 'text': text, 'success': success,
            'prior': prior, 'backlog': backlog, 'status': status}


def phase(number, horizon, title, goal, exit_criterion, items):
    return {'number': number, 'horizon': horizon, 'title': title, 'goal': goal,
            'exit': exit_criterion, 'items': items}


PHASES = [
    phase(0, 'NOW', 'Baseline', 'Finish a trustworthy before-picture and make knob sweeps cheap enough to run routinely.',
          'Every later change is judged against the completed neo ↔ freya matrix, with cold-cache and quiet-volume evidence.', [
        item('0.1', EXPERIMENT, 'Finish the neo ↔ freya matrix', 'Complete the full Congress corpus (914,106 files) fresh, no-op, checksum and 1% update cases in both directions, three verified runs per tool.', 'Congress and update-1pct medians appear in the published result table.', backlog='F-01', status='active'),
        item('0.2', HARNESS, 'Runtime tuning overrides', 'Every engine constant is fixed at compile time today. A start-up override for block size, queue limits, thread clamp, zstd level and the delta threshold lets a sweep run without rebuilding.', 'Result JSON records the effective values for each sample.'),
        item('0.3', HARNESS, 'Sweeps from one command', 'Expose thread counts, deletion and cold-cache modes through the paired runner, with a load / memory / ARC snapshot before and after each case.', 'A <code>-j</code> sweep and a <code>--delete</code> case run unattended.'),
        item('0.4', HARNESS, 'Time to durable', 'Report the time until data is on disk (<code>syncfs</code>, <code>F_FULLFSYNC</code>) next to the time until exit. The tool that leaves more dirty pages otherwise looks faster.', 'Both timings appear side by side for write-heavy cases.', prior='rsync exited with ~2.4 GB still dirty; v1 with ~2.6 MB.'),
        item('0.5', EXPERIMENT, 'Quiet APFS re-measurement', 'Repeat the 1/2/4/8-thread APFS diagnostic with low load and at least 20% free space, so filesystem defaults are not chosen from a 98%-full volume.', 'Thread table recorded with load under 2 and the volume under 80% full.', backlog='F-07'),
        item('0.6', EXPERIMENT, 'Cold-cache protocol', 'Evict caches on both hosts and prove it: ZFS ARC residency on freya, page cache on the Pi.', 'At least one cold Congress push and pull, with residency evidence attached.', prior='Warm vs cold walks differed 44.6 vs 101.6 s.', backlog='F-01'),
    ]),
    phase(1, 'NEXT', 'Efficiency', 'Reach rsync-class CPU and memory without giving up any safety guarantee.',
          'Across the matrix, CPU ≤ 1.5× and peak memory ≤ 4× rsync’s, with wall time no worse than today.', [
        item('1.1', FEATURE, 'Per-directory destination handles', 'Keep one no-follow handle per destination directory and make child operations relative to it, instead of re-walking from the destination root for every file. This keeps the symlink-race protection and removes repeated path walks.', 'APFS no-op at or below rsync; receiver system time on Congress at least halved.', prior='63% of APFS profile samples sit in repeated <code>openat</code> walks.', backlog='F-07 · F-08'),
        item('1.2', FEATURE, 'Cache name-collision rules', 'Look up case and normalisation rules once per filesystem, on macOS as well as Linux, and run collision checks once per directory.', 'Directory walks drop out of the top of the APFS profile.', backlog='F-08'),
        item('1.3', FEATURE, 'Unserialised file creation', 'Replace the process-wide output lock with per-file state, so creating and publishing files scales with worker threads.', 'Wall time improves up to at least 8 threads on ext4 and ZFS.', backlog='F-07'),
        item('1.4', FEATURE, 'Release finished directories', 'Free directory records once they and their files complete, and bound the local work queue by bytes and files rather than task count.', 'Receiver memory on Congress under 200 MiB; a 5-million-file tree stays under a stated bound.', prior='Receiver peaked near 1 GiB against rsync’s 89 MiB.', backlog='F-09'),
        item('1.5', FEATURE, 'Right-sized compression buffers', 'Compress into per-worker scratch space and queue exactly the bytes produced, so compressed frames stop retaining their worst-case buffer.', '<code>-z</code> push peak memory under 100 MiB with unchanged wall time.', prior='Compressed pushes peaked at 292–298 MiB.'),
        item('1.6', FEATURE, 'Leaner Linux scan', 'Use directory entry types and minimal <code>statx</code> masks, and skip per-entry stats where the listing already answers the question.', 'Congress no-op CPU within 1.5× rsync.', backlog='F-06'),
        item('1.7', HARNESS, 'CPU and memory gates', 'Extend the CI performance gate beyond wall time, so efficiency gains cannot quietly regress.', 'The gate fails on an injected leak or busy loop.', backlog='F-02'),
    ]),
    phase(2, 'THEN', 'Local lead', 'Restore and widen xsync’s lead on local copies, starting with Linux filesystems that support cloning.',
          'Local fresh, no-op and update cases lead rsync on APFS, XFS/btrfs and ext4, with thread defaults chosen per filesystem.', [
        item('2.1', FEATURE, 'Linux reflinks and copy offload', 'Probe clone support once per source/destination pair by cloning a real source file, then clone per file. Otherwise use kernel copy offload before falling back to read/write.', 'XFS/btrfs fresh copy at least 2× rsync; ext4 not slower.', prior='The one-time probe alone gave 2.98× on ext4; a correct probe turned XFS from 1.61× slower to 1.07× faster.', backlog='F-05'),
        item('2.2', EXPERIMENT, 'Whole-file local copies', 'Local updates currently run large changed files through delta matching and re-read them for verification. rsync sends whole files locally because the disk is cheaper than the matcher.', 'A/B on an edited 2 GiB file decides the default; the remote delta path is unchanged.'),
        item('2.3', EXPERIMENT, 'Threads per filesystem', 'Sweep 1–32 threads for fresh, no-op and update on APFS, ext4, ZFS and XFS, then pick defaults from filesystem type, not core count alone.', 'Default within 5% of the measured optimum on each filesystem.', prior='Optima ranged from 4 to 32; core count was a poor predictor.', backlog='F-07'),
        item('2.4', EXPERIMENT, 'APFS creation floor', 'With per-directory handles in place, determine whether ~100 µs per created file is the filesystem itself or contention.', 'Either reach ~4,600 files/s or document the floor with a standalone benchmark.', prior='4,636 files/s at the APFS optimum.', backlog='F-07'),
        item('2.5', EXPERIMENT, 'Bounded subtree clones', 'Clone a small missing subtree in one call, sized from the scan.', 'Crossover measured; threshold set from it.', prior='Directory clones won only below ~4–7 MB of missing data.', backlog='F-10'),
        item('2.6', FEATURE, 'Clones without full archive mode', 'Clone first, then correct mode and ownership, when <code>-rt</code> or <code>-rlt</code> would otherwise fall back to byte copies.', 'Faster than create-and-write on APFS.', backlog='F-11'),
        item('2.7', FEATURE, 'Parallel deletion', 'Remove stale subtrees in parallel during <code>--delete</code>.', 'A 96k-entry stale subtree removed at least 3× faster than <code>rm -rf</code>.', backlog='F-12'),
    ]),
    phase(3, 'THEN', 'Remote throughput', 'Push past the single-stream ceiling only where it pays, after efficiency makes the gains cheap.',
          'Compressed, checksum and delta transfers lead rsync on 1 GbE without extra CPU, with a measured plan for faster links.', [
        item('3.1', FEATURE, 'Adaptive compression', 'Decide from a 64 KiB sample of the data whether compression saves at least 5%, honour <code>--skip-compress</code>, and measure the link-speed crossover.', '<code>-z</code> on incompressible data within 3% of <code>-a</code>; compressible data no worse.', prior='1.66× on congress-100k; incompressible data added 0% to wire bytes.', backlog='F-04'),
        item('3.2', FEATURE, 'Pipelined checksums', 'Hash on the transfer pool, overlapping with listing, and hash receiver candidates in parallel.', 'Large-file <code>-c</code> pull at least matches rsync.', prior='Skipping hashing entirely saved 0 ms once it overlapped.', backlog='F-14'),
        item('3.3', FEATURE, 'Asynchronous delta requests', 'Keep several basis signatures in flight instead of blocking a worker on a round trip per file.', 'Remote update of 100 edited 8 MiB files at least matches rsync.', prior='Removing per-chunk acks took pushes from 62.9 MB/s to line rate.'),
        item('3.4', EXPERIMENT, 'Cipher selection', 'Measure ChaCha20 against AES-GCM on the Pi and the workstation. The current link negotiates ChaCha20 both ways.', 'Decision recorded with the Pi’s own numbers.', prior='Loopback: 845 MB/s ChaCha20 vs 2,374 MB/s AES-GCM; within 4% at 1 GbE.', backlog='F-03'),
        item('3.5', EXPERIMENT, 'Multiple streams for large files', 'Only if one SSH stream proves to be the ceiling: stripe files of 16 MiB or more across connections, never small-file trees.', 'At least 1.4× on a large file over 10 GbE with no small-tree regression.', prior='1.41× at 16 MiB, 1.94× at 64 MiB, 0.90× on small files.', backlog='F-03'),
        item('3.6', EXPERIMENT, 'Receiver worker count', 'Compare the receiver capped at eight workers with today’s sixteen, once creation is unserialised.', 'Default set from the sweep.', prior='Workers 1 → 2 → 8 → 16: 11.45 → 9.23 → 8.75 → 8.80 s.'),
        item('3.7', EXPERIMENT, 'Tiny transfers', 'Break down start-up cost (worker pool, handshake round trip) against rsync.', 'A single small file within 10 ms of rsync in both directions.', backlog='F-13'),
    ]),
    phase(4, 'LATER', 'Scale', 'Hold the lead on the trees, links and hardware you actually use.',
          'No superlinear cost in tree size, depth or width, and documented behaviour on slow links and the Pi.', [
        item('4.1', EXPERIMENT, 'Millions of files', 'A 5-million-file synthetic tree and a 1-million-file real tree, measured for memory and wall time.', 'Stated memory bound met; receiver memory flat in tree size.', backlog='F-09'),
        item('4.2', EXPERIMENT, 'Pathological shapes', 'One directory of 500k entries, trees 64+ levels deep, and long names.', 'No superlinear CPU on APFS, ext4 or ZFS.'),
        item('4.3', EXPERIMENT, 'Metadata-heavy runs', 'Price hard links, xattrs and ACLs on the Congress corpus.', 'Each within 1.2× of the plain archive-mode ratio to rsync.'),
        item('4.4', EXPERIMENT, 'Shaped links', 'No-op, 1% update and delta over emulated 20 ms / 100 Mb/s and 80 ms / 20 Mb/s links.', 'High-latency regressions identified and recorded.'),
        item('4.5', EXPERIMENT, 'Pi soak', 'Repeat the Congress push on the Pi, cooled and uncooled, with a sustained soak.', 'Drift under 5%, or documented.', prior='Pi thermal drift of 18.1 → 27.1 s.'),
    ]),
    phase(5, 'ALWAYS', 'Lock in', 'Turn every verified win into a permanent check.',
          'Each phase closes by advancing the pinned CI reference to the improved build.', [
        item('5.1', HARNESS, 'Advance the reference', 'Move the CI gate’s pinned reference forward after each verified improvement, so later changes protect it.', 'The reference never trails a released performance gain.', backlog='F-02', status='ongoing'),
        item('5.2', HARNESS, 'New CI scenarios', 'Add incompressible <code>-z</code> (memory), deep-tree no-op (walk cost), large <code>--delete</code> and large-file <code>-c</code> fixtures.', 'Each confirmed fix has a scenario that would catch its regression.', backlog='F-02', status='ongoing'),
        item('5.3', HARNESS, 'Generated results', 'Generate the README benchmark table from verified results, keeping historical numbers clearly labelled.', 'No hand-edited performance numbers.', status='ongoing'),
    ]),
]

STANDING = [
    ('FRESH COPIES', '1.00–1.28×', 'rsync’s speed over 1 GbE SSH. Parity without <code>-z</code>, where the link is the ceiling.'),
    ('CPU', '1.6–1.9×', 'rsync’s CPU on fresh copies, and up to 8× on no-op and checksum runs.'),
    ('PEAK MEMORY', '6–22×', 'rsync’s on fresh copies. Near 1 GiB on the 914,106-file corpus.'),
    ('APFS NO-OP', '1.8–3.2×', 'slower than rsync on a loaded machine, against 1.9× faster in the earlier baseline.'),
]

WON = [
    ('One-time reflink probe', '2.98× on ext4'),
    ('Native whole-directory clones', '6.3× over per-file clones'),
    ('Small-file batching and pipelining', '25.5× over SSH'),
    ('Sampled adaptive compression', '1.66× on congress-100k'),
    ('No per-chunk acknowledgements', '62.9 MB/s → line rate'),
    ('Striping large files only', '1.41–1.94× at 16–64 MiB'),
]

PARKED = [
    ('io_uring create/write path', '4% ceiling'),
    ('Dedicated writer threads, fsync tuning', 'flat'),
    ('Hash caching, cheaper hashes', 'within noise'),
    ('Extra connections for small-file trees', '0.90×'),
    ('zstd level 1 or 9', '5% faster / 2× slower'),
    ('Persistent destination index', '1.09 GB at 1M files'),
]

METHOD = [
    'Run xsync and rsync paired, in rotated order, and judge ratios rather than absolute times.',
    'Verify every sample independently; a wrong tree fails the run even when the tool exits 0.',
    'Report wall time, CPU split by endpoint, peak memory and context switches.',
    'Label the source revision, binary hash, filesystem, free space, load, cache state and cipher.',
    'Take five or more samples; spread above 15% of the median is inconclusive.',
    'Decide with a timed A/B on the target, never with a profile alone.',
]

DECISIONS = [
    ('Local delta', 'Keep rsync-style whole-file copies for local updates? Recommended, pending experiment 2.2.'),
    ('Thread default', 'A per-filesystem table, or one conservative default with documentation?'),
    ('Cipher', 'Should xsync ever choose an SSH cipher on the user’s behalf, or only document the choice?'),
    ('Performance budget', 'Adopt CPU ≤ 1.5× and memory ≤ 4× rsync as standing CI gates?'),
]

SHIPPED = 'P0 trust 15/15 · P1 reach 21/22 · P2 progress closed'


def render_item(entry):
    facts = '<div><dt>Done when</dt><dd>' + entry['success'] + '</dd></div>'
    if entry['prior']:
        facts += '<div><dt>Evidence</dt><dd>' + entry['prior'] + '</dd></div>'
    backlog = '<span class="rm-backlog">' + entry['backlog'] + '</span>' if entry['backlog'] else ''
    return ('<li class="rm-item rm-' + entry['kind'] + '" id="item-' + entry['ref'].replace('.', '-') + '">'
            '<div class="rm-item-head"><span class="rm-kind">' + KIND_LABEL[entry['kind']] + '</span>'
            '<span class="rm-ref">' + entry['ref'] + '</span>' + backlog +
            '<span class="rm-status rm-status-' + entry['status'] + '">' + STATUS_LABEL[entry['status']] + '</span></div>'
            '<h3>' + entry['title'] + '</h3><p>' + entry['text'] + '</p><dl class="rm-facts">' + facts + '</dl></li>')


def render_phase(entry):
    counts = {kind: sum(1 for i in entry['items'] if i['kind'] == kind) for kind in KIND_LABEL}
    summary = ' · '.join(f'{n} {KIND_LABEL[k].lower()}{"s" if n != 1 else ""}' for k, n in counts.items() if n)
    return ('<div class="rm-phase rm-horizon-' + entry['horizon'].lower() + '">'
            '<div class="rm-phase-meta"><span class="rm-horizon">' + entry['horizon'] + '</span><span>' + summary + '</span></div>'
            '<p class="rm-goal">' + entry['goal'] + '</p>'
            '<p class="rm-exit"><span>EXIT</span>' + entry['exit'] + '</p>'
            '<ol class="rm-items">' + ''.join(render_item(i) for i in entry['items']) + '</ol></div>')


def overview():
    columns = [('SHIPPED', 'rm-stop-done', '<a href="https://github.com/s4njee/xsyncv4/blob/main/backlog.md" target="_blank" rel="noopener noreferrer"><strong>Daily-driver CLI</strong><span class="rm-stop-text">' + SHIPPED + '</span></a>')]
    for horizon in ['NOW', 'NEXT', 'THEN', 'LATER']:
        phases = [e for e in PHASES if e['horizon'] == horizon or (horizon == 'LATER' and e['horizon'] == 'ALWAYS')]
        links = ''.join('<a href="#phase-' + str(e['number']) + '"><strong>Phase ' + str(e['number']) + ' · ' + e['title'] + '</strong>'
                        '<span class="rm-stop-text">' + str(len(e['items'])) + ' items' + (' · ongoing' if e['horizon'] == 'ALWAYS' else '') + '</span></a>' for e in phases)
        columns.append((horizon, 'rm-stop-now' if horizon == 'NOW' else '', links))
    nodes = ''.join('<li class="rm-stop ' + cls + '"><span class="rm-stop-when">' + when + '</span>' + body + '</li>' for when, cls, body in columns)
    filters = ''.join('<input type="radio" name="rm-filter" id="rm-filter-' + key + '" value="' + key + '"' + (' checked' if key == 'all' else '') + '>'
                      '<label for="rm-filter-' + key + '">' + label + '</label>'
                      for key, label in [('all', 'Everything'), (EXPERIMENT, 'Experiments'), (FEATURE, 'Features'), (HARNESS, 'Measurement')])
    return ('<ol class="rm-track">' + nodes + '</ol>'
            '<fieldset class="rm-filter"><legend>Show on the timeline</legend>' + filters + '</fieldset>')


def hero():
    stats = ''.join('<div class="rm-stat"><span>' + label + '</span><strong>' + value + '</strong><p>' + text + '</p></div>'
                    for label, value, text in STANDING)
    return ('<div class="rm-hero"><span class="rm-eyebrow"><i aria-hidden="true"></i>ROADMAP · REVIEWED 10 OCTOBER 2026</span>'
            '<p class="rm-headline">Faster where you sync.<br><span>Lighter while it does.</span></p>'
            '<p class="rm-lede">xsync already matches rsync on real links and leads it with compression. The next stretch makes every transfer cheaper in CPU and memory, wins back the local lead, and then pushes remote throughput only where measurements show it pays.</p>'
            '<div class="rm-stats" aria-label="Where xsync stands today">' + stats + '</div>'
            '<p class="rm-stats-note">Measured 10 October 2026 between a Raspberry Pi 5 (ext4) and a Ryzen 7950X (ZFS) over 1 GbE, warm caches, three verified runs per tool. APFS figures come from a loaded M1 Max.</p></div>')


def lessons():
    def column(title, rows):
        return ('<div class="rm-lesson"><span>' + title + '</span><ul>' +
                ''.join('<li><strong>' + name + '</strong><em>' + effect + '</em></li>' for name, effect in rows) + '</ul></div>')
    return (p('xsync v1, an earlier Rust implementation, ran a long tuning programme across APFS, ext4, XFS, ZFS, Windows and a Raspberry Pi. Its winners shape the plan above; its losers are parked until new evidence contradicts them.') +
            '<div class="rm-lessons">' + column('WHAT WON', WON) + column('PARKED', PARKED) + '</div>')


def numbered(rows):
    return '<ol class="rm-method">' + ''.join('<li>' + row + '</li>' for row in rows) + '</ol>'


def decisions():
    return '<div class="rm-decisions">' + ''.join('<div><span>' + name + '</span><p>' + question + '</p></div>' for name, question in DECISIONS) + '</div>'


ROADMAP_PAGE = doc('roadmap', 'xsync-roadmap(7)', 'Roadmap', 'Experiments and features planned for xsync’s performance, in the order they unlock each other.', 'PROJECT', [
    section('timeline', 'TIMELINE', p('Each phase makes the next one’s measurements meaningful. Efficiency comes before throughput: a faster transfer that costs four times the CPU is not faster on a Raspberry Pi.') + overview()),
    *[section(f'phase-{entry["number"]}', f'PHASE {entry["number"]} · {entry["title"].upper()}', render_phase(entry)) for entry in PHASES],
    section('lessons', 'LESSONS FROM XSYNC V1', lessons()),
    section('method', 'HOW WE MEASURE', p('Environment changes impersonated code changes three times in v1. Every experiment on this page follows these rules:') + numbered(METHOD)),
    section('decisions', 'OPEN DECISIONS', decisions()),
    section('sources', 'SOURCES', p('Condensed from <code>ROADMAP.md</code> in the <a href="https://github.com/s4njee/xsyncv4" target="_blank" rel="noopener noreferrer">source repository</a>, which cites every figure. It links the verified benchmark results and the xsync v1 tuning records. Planned work here is not part of the command reference; see <a href="development.html">development status</a> for what ships today.')),
])
ROADMAP_PAGE['deck'] = hero()
ROADMAP_PAGE['front'] = {'pageClass': 'roadmap-page'}
