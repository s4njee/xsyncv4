"""Lessons page: what the first xsync (v1, Rust) learned from its benchmarks, with Holochart figures.

Every number comes from the v1 repository (github.com/s4njee/xsync); each figure names its files.
"""
from html import escape
from docs_content import doc, section, p, table

V1 = 'https://github.com/s4njee/xsync/blob/main/'

# Dark-mode categorical steps validated against the #0e0e0e card surface
# (dataviz validate_palette.js: all checks pass). Gray carries "baseline" or "dropped", never identity alone.
BLUE, ORANGE, AQUA, GRAY = '#3987e5', '#d95926', '#199e70', '#6f6f6f'
INK, MUTED, GRID, SURFACE = '#c8c8c8', '#8d8d8d', '#262626', '#0e0e0e'
FONT = {'family': 'Helvetica Neue, Helvetica, Arial, sans-serif', 'size': 11, 'color': MUTED}


def layout(**extra):
    base = {
        'paper_bgcolor': SURFACE, 'plot_bgcolor': SURFACE, 'font': FONT,
        'margin': {'l': 64, 'r': 24, 't': 16, 'b': 48},
        'showlegend': False,
        'hoverlabel': {'bgcolor': '#1b1b1b', 'bordercolor': '#444', 'font': {'color': '#ededed', 'size': 12}},
        'legend': {'orientation': 'h', 'x': 0, 'y': 1.12, 'font': {'color': INK, 'size': 11}},
    }
    for key, value in extra.items():
        base[key] = value
    return base


def axis(title='', **extra):
    out = {'gridcolor': GRID, 'zerolinecolor': '#3a3a3a', 'linecolor': '#3a3a3a', 'tickfont': {'color': MUTED, 'size': 10},
           'title': {'text': title, 'font': {'color': MUTED, 'size': 11}}}
    out.update(extra)
    return out


def ref_line(axis_name, value, label):
    """A dashed reference line across the plot, labelled in text ink."""
    other = 'y' if axis_name == 'x' else 'x'
    line = {'type': 'line', 'xref': 'x' if axis_name == 'x' else 'paper', 'yref': 'y' if axis_name == 'y' else 'paper',
            f'{axis_name}0': value, f'{axis_name}1': value, f'{other}0': 0, f'{other}1': 1,
            'line': {'color': '#8a8a8a', 'width': 1, 'dash': 'dash'}}
    note = {'xref': 'x' if axis_name == 'x' else 'paper', 'yref': 'y' if axis_name == 'y' else 'paper',
            axis_name: value, other: 1, 'text': label, 'showarrow': False,
            'font': {'color': INK, 'size': 10}, 'xanchor': 'left' if axis_name == 'x' else 'right', 'yanchor': 'bottom',
            'xshift': 4 if axis_name == 'x' else 0}
    return line, note


# ---------------------------------------------------------------- figures and their tables

WINS = [  # (idea in plain English, short label, speed-up ×, kept?, source)
    ('Pack many small files into each network message', 'Bundle small files', 25.5, True, 'benches/results/story-8.1/DECISION.md'),
    ('Clone a whole new folder in one call (macOS)', 'Clone whole folders', 6.27, True, 'benches/results/tuning/T1/hash-and-100k-20260828/README.md'),
    ('Read ahead on the sender, write in parallel on the receiver', 'Read ahead, write in parallel', 3.11, True, 'legacy/BENCHMARKSv3.md'),
    ('Check once whether the disk can clone files', 'Check clone support once', 2.98, True, 'benches/results/tuning/T1/perf-profile-20260828/README.md'),
    ('Compress, but only when a sample shows it helps', 'Compress when it helps', 1.66, True, 'legacy/backlogv4.md'),
    ('Confirm progress every 8 chunks instead of every chunk', 'Fewer progress checks', 1.19, True, 'legacy/backlogv4.md'),
    ('Use a faster, weaker compression level', 'Weaker compression', 1.056, False, 'legacy/backlogv4.md'),
    ('Rewrite file creation with io_uring (best case)', 'io_uring (best case)', 1.045, False, 'benches/results/tuning/T1/io-uring-spike-20260828/README.md'),
    ('Pin work to the thread that found it (best case)', 'Pin work to threads', 1.021, False, 'benches/results/tuning/T7/DECISION.md'),
    ('Hint the kernel to flush data early', 'Early flush hint', 1.007, False, 'legacy/backlogv4.md'),
    ('Skip checksums entirely', 'Skip checksums', 1.001, False, 'benches/results/tuning/T1/hash-and-100k-20260828/README.md'),
    ('Open extra SSH connections for a tree of small files', 'Extra SSH connections', 0.90, False, 'benches/results/story-4.3/stripe-crossover.md'),
]


def wins_figure(short=False):
    ordered = list(reversed(WINS))  # largest at the top of a horizontal bar chart
    label = 1 if short else 0
    traces = []
    for kept, name, color in [(True, 'Kept in v1', BLUE), (False, 'Measured, then dropped', GRAY)]:
        rows = [r for r in ordered if r[3] == kept]
        traces.append({'type': 'bar', 'orientation': 'h', 'name': name, 'marker': {'color': color},
                       'y': [r[label] for r in rows], 'x': [r[2] for r in rows], 'customdata': [r[0] for r in rows],
                       'text': [f'{r[2]:g}×' for r in rows], 'textposition': 'outside',
                       'textfont': {'color': INK, 'size': 10}, 'cliponaxis': False,
                       'hovertemplate': '%{customdata}<br><b>%{x:.3g}× as fast</b><extra></extra>'})
    line, note = ref_line('x', 1, 'no change')
    return {'data': traces, 'layout': layout(
        showlegend=True, barmode='overlay', bargap=0.35,
        margin={'l': 150 if short else 330, 'r': 48, 't': 44, 'b': 48},
        xaxis=axis('Times as fast as before (log scale)', type='log', range=[-0.12, 1.85 if short else 1.62], tickangle=0,
                   tickvals=[1, 2, 5, 10, 25], ticktext=['1×', '2×', '5×', '10×', '25×']),
        yaxis=axis('', categoryorder='array', categoryarray=[r[label] for r in ordered], tickfont={'color': INK, 'size': 10 if short else 11}, gridcolor='rgba(0,0,0,0)'),
        shapes=[line], annotations=[note])}


THREADS = {  # workers -> median seconds, congress-10k (T7)
    'Linux ext4 (24 cores)': ([1, 2, 4, 6, 8, 12, 16, 24], [0.468, 0.317, 0.241, 0.221, 0.209, 0.201, 0.196, 0.193], BLUE),
    'macOS APFS, government data': ([2, 3, 4, 5, 6, 10], [2.856, 2.609, 2.520, 2.500, 2.554, 2.717], ORANGE),
    'macOS APFS, node_modules': ([2, 4, 5, 8, 10, 16], [4.893, 3.834, 3.872, 4.534, 4.418, 4.474], AQUA),
}


def threads_figure():
    traces = []
    for name, (workers, seconds, color) in THREADS.items():
        best = min(seconds)
        slower = [round((s / best - 1) * 100, 1) for s in seconds]
        traces.append({'type': 'scatter', 'mode': 'lines+markers', 'name': name, 'x': workers, 'y': slower,
                       'line': {'color': color, 'width': 2}, 'marker': {'color': color, 'size': 8, 'line': {'color': SURFACE, 'width': 2}},
                       'customdata': seconds,
                       'hovertemplate': name + '<br>%{x} workers: %{customdata:.3f} s<br><b>%{y:.0f}% slower than its best</b><extra></extra>'})
    return {'data': traces, 'layout': layout(
        showlegend=True, margin={'l': 64, 'r': 24, 't': 44, 'b': 52},
        xaxis=axis('Worker threads (log scale)', type='log', tickvals=[1, 2, 4, 8, 16, 24], ticktext=['1', '2', '4', '8', '16', '24']),
        yaxis=axis('% slower than the best setting', rangemode='tozero', ticksuffix='%'))}


CLONE = ([4, 8, 12, 16], [0.502, 0.863, 1.130, 1.448])


def clone_figure():
    sizes, speed = CLONE
    line, note = ref_line('y', 1, 'clone and copy take the same time')
    return {'data': [{'type': 'scatter', 'mode': 'lines+markers+text', 'name': 'Clone vs copy', 'x': sizes, 'y': speed,
                      'text': [f'{v:g}×' for v in speed], 'textposition': 'top left', 'textfont': {'color': INK, 'size': 10},
                      'line': {'color': BLUE, 'width': 2}, 'marker': {'color': BLUE, 'size': 9, 'line': {'color': SURFACE, 'width': 2}},
                      'hovertemplate': '%{x} MiB file<br><b>cloning is %{y:.2f}× as fast as copying</b><extra></extra>'}],
            'layout': layout(
                margin={'l': 64, 'r': 24, 't': 24, 'b': 52},
                xaxis=axis('File size (MiB)', tickvals=sizes, range=[2.5, 17.5]),
                yaxis=axis('Clone speed vs plain copy', range=[0.3, 1.65], ticksuffix='×'),
                shapes=[line, {'type': 'rect', 'xref': 'x', 'yref': 'paper', 'x0': 12, 'x1': 17.5, 'y0': 0, 'y1': 1,
                               'fillcolor': 'rgba(57,135,229,0.07)', 'line': {'width': 0}}],
                annotations=[note, {'xref': 'x', 'yref': 'paper', 'x': 12.2, 'y': 0.06, 'xanchor': 'left', 'showarrow': False,
                                    'text': 'v1 clones files from 12 MiB up', 'font': {'color': INK, 'size': 10}}])}


COMPRESSION = [('Off', 12.52), ('Level 1', 7.14), ('Level 3 (default)', 7.54), ('Level 9', 15.23)]


def compression_figure():
    colors = [GRAY, BLUE, BLUE, ORANGE]
    return {'data': [{'type': 'bar', 'name': 'Transfer time', 'x': [c[0] for c in COMPRESSION], 'y': [c[1] for c in COMPRESSION],
                      'marker': {'color': colors}, 'text': [f'{c[1]:.2f} s' for c in COMPRESSION], 'textposition': 'outside',
                      'textfont': {'color': INK, 'size': 10}, 'cliponaxis': False,
                      'hovertemplate': 'Compression %{x}<br><b>%{y:.2f} s</b><extra></extra>'}],
            'layout': layout(bargap=0.45, margin={'l': 64, 'r': 24, 't': 28, 'b': 48},
                             xaxis=axis('zstd compression level'), yaxis=axis('Seconds to copy (lower is better)', rangemode='tozero', range=[0, 17.5]))}


STRIPES = [('4 MiB file', 0.98), ('16 MiB file', 1.41), ('64 MiB file', 1.94), ('Many small files', 0.90)]


def stripes_figure():
    line, note = ref_line('y', 1, 'one connection')
    return {'data': [{'type': 'bar', 'name': 'Four connections', 'x': [s[0] for s in STRIPES], 'y': [s[1] for s in STRIPES],
                      'marker': {'color': [GRAY if s[1] < 1.05 else BLUE for s in STRIPES]},
                      'text': [f'{s[1]:g}×' for s in STRIPES], 'textposition': 'inside', 'insidetextanchor': 'end', 'textfont': {'color': '#f2f2f2', 'size': 11},
                      'hovertemplate': '%{x}<br><b>%{y:.2f}× as fast with four connections</b><extra></extra>'}],
            'layout': layout(bargap=0.45, margin={'l': 64, 'r': 24, 't': 28, 'b': 48},
                             xaxis=axis(''), yaxis=axis('Speed with 4 connections vs 1', range=[0, 2.25], ticksuffix='×'),
                             shapes=[line], annotations=[note])}


CIPHERS = [('ChaCha20 (OpenSSH default)', 845.5), ('AES-128-GCM', 2374.5)]


def cipher_figure(short=False):
    line, note = ref_line('x', 125, 'gigabit Ethernet')
    names = ['ChaCha20', 'AES-GCM'] if short else [c[0] for c in CIPHERS]
    return {'data': [{'type': 'bar', 'orientation': 'h', 'name': 'Encryption speed', 'y': names, 'x': [c[1] for c in CIPHERS],
                      'marker': {'color': [ORANGE, BLUE]}, 'text': [f'{c[1]:,.0f} MB/s' for c in CIPHERS], 'textposition': 'outside',
                      'textfont': {'color': INK, 'size': 10}, 'cliponaxis': False,
                      'hovertemplate': '%{y}<br><b>%{x:,.1f} MB/s</b><extra></extra>'}],
            'layout': layout(bargap=0.5, margin={'l': 80 if short else 190, 'r': 24, 't': 24, 'b': 48},
                             xaxis=axis('MB/s through one SSH connection' if short else 'MB/s through one SSH connection on one machine', range=[0, 3100]),
                             yaxis=axis('', tickfont={'color': INK, 'size': 11}, gridcolor='rgba(0,0,0,0)'),
                             shapes=[line], annotations=[note])}


NOISE = [('Same transfer, first three runs', [23.2, 21.8, 21.0], ORANGE),
         ('Same transfer, after warming up', [11.6, 11.9, 11.4], BLUE)]


def noise_figure():
    traces = [{'type': 'scatter', 'mode': 'lines+markers', 'name': name, 'x': [1, 2, 3], 'y': runs,
               'line': {'color': color, 'width': 2}, 'marker': {'color': color, 'size': 9, 'line': {'color': SURFACE, 'width': 2}},
               'hovertemplate': name + '<br>run %{x}: <b>%{y:.1f} s</b><extra></extra>'} for name, runs, color in NOISE]
    return {'data': traces, 'layout': layout(showlegend=True, margin={'l': 64, 'r': 24, 't': 44, 'b': 52},
                                             xaxis=axis('Run', tickvals=[1, 2, 3]), yaxis=axis('Seconds', rangemode='tozero', range=[0, 26]))}


FIGURES = {'wins': wins_figure(), 'threads': threads_figure(), 'clone': clone_figure(), 'compression': compression_figure(),
           'stripes': stripes_figure(), 'cipher': cipher_figure(), 'noise': noise_figure()}
# Phone-width variants: the component swaps these in when its container is narrower than 560 px.
FIGURES['wins']['narrow'] = wins_figure(short=True)
FIGURES['cipher']['narrow'] = cipher_figure(short=True)


def source_links(*paths):
    return ' · '.join(f'<a href="{V1}{path}" target="_blank" rel="noopener noreferrer"><code>{escape(path)}</code></a>' for path in paths)


def figure(chart, title, takeaway, headers, rows, sources, height=340, label=''):
    return ('<figure class="lesson-figure"><figcaption><span>' + title + '</span><p>' + takeaway + '</p></figcaption>'
            f'<HoloChart set="lessons" chart="{chart}" :height="{height}" label="{escape(label or title)}" />'
            '<details class="lesson-data"><summary>Show the numbers</summary>' + table(headers, rows) +
            '<p class="lesson-source">Source: ' + source_links(*sources) + '</p></details></figure>')


def wins_table():
    return [(name, f'{speed:g}×', 'Kept' if kept else 'Dropped') for name, _, speed, kept, _ in WINS]


def thread_rows():
    rows = []
    for name, (workers, seconds, _) in THREADS.items():
        rows.append((name, ', '.join(f'{w}: {s:.3f} s' for w, s in zip(workers, seconds))))
    return rows


LESSONS_PAGE = doc('lessons', 'xsync-lessons(7)', 'Lessons', 'What the first xsync learned from its benchmarks, and what xsync does with it.', 'PROJECT', [
    section('summary', 'IN SHORT', p('Before this C++ version, xsync was written in Rust. That first version ran a long series of measured experiments across a MacBook, two Ryzen workstations, a Raspberry Pi and Windows. Most of its speed came from <strong>a handful of big ideas</strong>. Most clever-sounding tweaks <strong>did almost nothing</strong>. And the test machine itself caused fake results more than once.') +
            '<div class="lesson-points"><div><strong>Do less work per file</strong><p>Bundling, cloning and checking things once beat every low-level trick.</p></div><div><strong>Measure the machine you sync with</strong><p>The best thread count changed from 4 to 24 depending on the disk.</p></div><div><strong>Don’t trust one run</strong><p>The same transfer took 23 s cold and 11 s warm, with no code change.</p></div></div>'),
    section('big-ideas', 'A FEW BIG IDEAS DID MOST OF THE WORK', p('Each bar is one change v1 tried, measured against the version without it. The blue changes stayed. The gray ones were measured and dropped: even at their best they were within a few percent of doing nothing.') +
            figure('wins', 'Measured speed-up of each idea', 'The winners cut the work done per file. The losers made the same work slightly cheaper.',
                   ['Change', 'Speed-up', 'Outcome'], wins_table(),
                   [w[4] for w in WINS[:1]] + ['benches/results/tuning/T1/DECISION.md', 'legacy/backlogv4.md', 'legacy/BENCHMARKSv3.md'], height=470) +
            p('One example: v1 once asked the operating system 3.9 times as often as rsync did, about 25 calls per file instead of 6. Cutting those calls by 44% made it only 13% faster, because creating the files on disk was the real limit. <strong>Fewer steps only helps when those steps are what you’re waiting for.</strong>')),
    section('threads', 'MORE THREADS ISN’T ALWAYS FASTER', p('Copying 10,000 small files locally, Linux kept getting faster all the way to 24 threads. macOS peaked at four or five and then got slower, because its file system handles changes to a folder one at a time. v1’s default of one thread per core was 8–15% slower than the best setting on the Mac.') +
            figure('threads', 'How much slower than its best setting each disk is', 'Lower is better. The Linux line keeps falling; both Mac lines turn back up after 4–5 threads.',
                   ['Disk and data', 'Median time by worker threads'], thread_rows(), ['benches/results/tuning/T7/DECISION.md']) +
            p('<strong>What xsync does with this:</strong> choose the thread count from the kind of disk, not the number of cores. See <a href="roadmap.html#item-2-3">roadmap item 2.3</a>.')),
    section('clone', 'CLONE BIG FILES, COPY SMALL ONES', p('A clone makes a new file that shares storage with the original until either one changes. It sounds free, but on macOS each clone carries a fixed cost. For small files a plain copy is quicker. Past about 12 MiB, cloning wins and keeps winning.') +
            figure('clone', 'Clone vs plain copy on macOS, by file size', 'Below the dashed line copying is faster; above it cloning is faster.',
                   ['File size', 'Clone speed vs copy'], [(f'{s} MiB', f'{v:g}×') for s, v in zip(*CLONE)], ['benches/results/tuning/T1/DECISION.md']) +
            p('The same idea applies to whole folders: cloning a new folder in one call was 6.3 times faster than cloning its files one by one. On Linux, v1 found the biggest local win by <em>checking once</em> whether the disk supports clones, instead of trying and failing for every file (2.98× faster).')),
    section('compression', 'COMPRESSION: SAMPLE FIRST, THEN KEEP IT SIMPLE', p('Compressing data before sending it made a 100,000-file transfer 1.66 times as fast. But data that is already compressed, like photos or archives, only gets slower. v1 compresses a small sample first and sends the rest raw if the sample doesn’t shrink. Going from the default level 3 down to level 1 saved just 5%. Level 9 doubled the time.') +
            figure('compression', 'One 100,000-file transfer at different compression levels', 'Level 3 is within 5% of the fastest setting and shrinks data more.',
                   ['Setting', 'Seconds'], [(c[0], f'{c[1]:.2f}') for c in COMPRESSION], ['legacy/backlogv4.md'], height=320) +
            p('Level 3 measured 7.53–7.54 s in the two sessions these numbers come from.')),
    section('connections', 'EXTRA CONNECTIONS ONLY HELP BIG FILES', p('Splitting a file across several SSH connections lets more processor cores encrypt at once. That helped for files of 16 MiB and up. For trees of small files it made things slower, and on Windows extra connections cost 1.4–1.5 times the time. Too many connections also run into SSH server limits.') +
            figure('stripes', 'Four SSH connections compared with one', 'Big files gain; small files and a 4 MiB file do not.',
                   ['Data', 'Speed with 4 connections'], [(s[0], f'{s[1]:g}×') for s in STRIPES], ['benches/results/story-4.3/stripe-crossover.md'], height=320)),
    section('network', 'THE NETWORK IS USUALLY THE LIMIT, NOT ENCRYPTION', p('On a gigabit network, which carries about 125 MB/s at most, every SSH cipher v1 tried was within 4% of the others, and SSH matched a raw unencrypted socket. Encryption speed only matters on faster links. There, the default ChaCha20 cipher is much slower than AES on processors with AES hardware.') +
            figure('cipher', 'How fast one SSH connection can encrypt', 'Both ciphers are far faster than a gigabit network can carry.',
                   ['Cipher', 'MB/s'], [(c[0], f'{c[1]:,.1f}') for c in CIPHERS], ['legacy/exotic.md'], height=240) +
            p('Measured on one Ryzen 7950X talking to itself, so no network limit applied. The Raspberry Pi 5’s processor has AES instructions too, and on v1’s gigabit link to a Pi the two ciphers tied; <a href="roadmap.html#item-3-4">roadmap item 3.4</a> measures it.')),
    section('honest', 'THE TEST MACHINE CAN FAKE A RESULT', p('The same transfer to the same server took twice as long on its first runs as it did once the machine had warmed up. Nothing in the code changed.') +
            figure('noise', 'One transfer, timed again and again', 'The first runs look like a 2× slowdown that doesn’t exist.',
                   ['Runs', 'Seconds'], [(n, ', '.join(f'{v:.1f}' for v in r)) for n, r, _ in NOISE], ['legacy/BENCHMARKSv3.md'], height=300) +
            p('v1 recorded other ways the environment pretended to be the code:') +
            '<ul class="lesson-list"><li><strong>Old binary.</strong> One whole experiment measured a stale build and had to be thrown away.</li><li><strong>Heat.</strong> A Raspberry Pi drifted from 18.1 s to 27.1 s over one session, most likely because it slowed itself down as it got hot.</li><li><strong>Tired disks.</strong> On a drive whose fast write cache kept filling up, one setting took anywhere from 61 to 94 seconds.</li><li><strong>A busy computer.</strong> One measurement ran while the machine’s load average was 265.</li><li><strong>Leftover writes.</strong> rsync can exit with 2.4 GB still waiting to reach the disk, so “finished” isn’t the same as “saved”.</li><li><strong>The network itself.</strong> A slow link and a stale IP address both produced fake regressions.</li></ul>' +
            p('<strong>What xsync does with this:</strong> every benchmark alternates xsync and rsync, checks every copy byte for byte, records the machine’s state, and repeats each case. See <a href="roadmap.html#method">how we measure</a>.')),
    section('carried', 'WHAT CARRIES OVER TO XSYNC TODAY', table(['Lesson from v1', 'In xsync now'], [
        ('Bundle small files and keep the pipe full', 'Done: 1 MiB blocks hold many small files, and listing, reading, sending and writing overlap'),
        ('Clone whole new folders on macOS', 'Done for new folders of files and links, up to 4,096 entries'),
        ('Check once whether a Linux disk can clone', 'Planned: <a href="roadmap.html#item-2-1">roadmap 2.1</a>'),
        ('Choose threads by disk, not cores', 'Planned: <a href="roadmap.html#item-2-3">roadmap 2.3</a>'),
        ('Compress only what shrinks', 'Planned: <a href="roadmap.html#item-3-1">roadmap 3.1</a>'),
        ('Use extra connections for big files only', 'Planned, only if measurements call for it: <a href="roadmap.html#item-3-5">roadmap 3.5</a>'),
        ('Don’t trust a single run', 'Done: paired, verified benchmarks and a CI speed check'),
    ])),
    section('sources', 'SOURCES', p('Every figure links to the v1 files its numbers come from, in the <a href="https://github.com/s4njee/xsync" target="_blank" rel="noopener noreferrer">s4njee/xsync</a> repository. Speed-ups are relative to the version without each change on the same machine and data. Charts are drawn with <a href="https://github.com/holochart/holochart" target="_blank" rel="noopener noreferrer">Holochart</a>. The full analysis, with a citation for every number, is in <code>ROADMAP.md</code>.')),
])
LESSONS_PAGE['front'] = {'pageClass': 'lessons-page'}
