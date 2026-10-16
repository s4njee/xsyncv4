// The 10 GbE view: results from the direct 10 GbE cable between the Mac and mars, and only
// from runs made once it ran at full speed (their preflight required 10 000 Mb/s; earlier runs
// on the same cable topped out near 3 Gb/s). The commentary is in index.html; the charts and
// table here are computed from the runs themselves, so they follow new runs as they arrive.
import { alpha, Plot, type ChartTheme } from './charts';
import { CODEC, CODEC_RUN } from './codec';
import { esc } from './format';
import { fetchRun, forgetRun } from './runs';
import type { RunDetail, RunIndex } from './types';

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const GIGABIT = 0.94; // what gigabit Ethernet carries as TCP payload, Gb/s
const TEN_GIG = 9.41; // raw TCP measured on this cable, each way, Gb/s
const BLUE = '#3b82ff', CYAN = '#22d3ee', GREY = '#94a3b8', AMBER = '#f59e0b';

const ARM_LABEL: Record<string, string> = {
  rsync: 'rsync', 'rsync-z': 'rsync -z', xs: 'xs', 'xs-z': 'xs -z (adaptive)', 'xs-z1': 'xs -z, level 1', 'xs-z3': 'xs -z, level 3',
};
const COMPRESSION_ARMS = ['rsync', 'rsync-z', 'xs', 'xs-z', 'xs-z1', 'xs-z3'];

interface Cell {
  corpus: string;
  scenario: string;
  toMac: boolean;
  arm: string;
  files: number;
  bytes: number;
  gbps: number[];
  fps: number[];
}

const seen = new Map<string, number>(); // run key -> samples when fetched
let spread: Plot | null = null;
let codecs: Plot | null = null;
let ceilings: Plot | null = null;
let drawn = '';

export function tenGigRuns(all: RunIndex[] | undefined): RunIndex[] {
  return (all || []).filter((r) => r.group === 'direct' && (r.link_mbps ?? 0) >= 10000);
}

export async function renderTenGig(all: RunIndex[] | undefined): Promise<void> {
  const runs = tenGigRuns(all);
  const stamp = runs.map((r) => `${r.key}:${r.samples}`).join('|');
  if (stamp === drawn) return;
  drawn = stamp;
  for (const r of runs) {
    if (seen.has(r.key) && seen.get(r.key) !== r.samples) forgetRun(r.key);
    seen.set(r.key, r.samples);
  }
  $('tengig-runs').innerHTML = runs.length
    ? runs.map((r) => `<li><a class="hcss-link" href="#runs/${esc(r.key)}">${esc(r.experiment)}</a> <span class="dash-muted">${esc(r.run.slice(0, 8))} · ${r.valid} samples${r.state === 'running' ? ' · still running' : ''}</span></li>`).join('')
    : '<li class="dash-muted">No 10 GbE runs have reached the dashboard yet.</li>';
  const details = (await Promise.all(runs.map((r) => fetchRun(r.key)))).filter((d): d is RunDetail => !!d);
  if (drawn !== stamp) return;
  const cells = aggregate(details);
  spread ??= new Plot($('tengig-spread'));
  codecs ??= new Plot($('tengig-codecs'));
  drawSpread(cells);
  drawCodecs(cells);
  renderTable(cells);
  drawCeilings(details.filter((d) => d.experiment === CEILING_EXPERIMENT));
}

// --- the most data the link can deliver, by compression level ------------------------------------

const CEILING_EXPERIMENT = 'Z5-10g-zstd-levels';
const LEVELS = [
  { arm: 'xs', level: 0, label: 'no compression' },
  { arm: 'xs-z1', level: 1, label: 'zstd level 1' },
  { arm: 'xs-z2', level: 2, label: 'zstd level 2' },
  { arm: 'xs-z3', level: 3, label: 'zstd level 3' },
] as const;
// xs compresses block by block, which cost level 1 about 6% of zstd's ratio on a whole file
// (2.62 in Z4 against 2.79); until Z5 measures a level, its ratio is estimated the same way.
const BLOCK_RATIO = 2.62 / 2.793;

interface Ceiling {
  toMac: boolean; level: number; label: string;
  ratio: number; ratioMeasured: boolean;
  data: number; wire: number; samples: number;
  full: number; compressor: number; max: number; limit: string;
}

function ceilingRows(details: RunDetail[]): Ceiling[] {
  const rows: Ceiling[] = [];
  for (const toMac of [true, false]) {
    const sender = CODEC[toMac ? 'mars' : 'mac'];
    for (const step of LEVELS) {
      const data: number[] = [], wire: number[] = [], ratios: number[] = [];
      for (const d of details) {
        const c = d.columns;
        for (let i = 0; i < c.cell.length; i++) {
          const cell = d.cells[c.cell[i]];
          if (!c.valid[i] || d.arms[c.arm[i]].name !== step.arm || (cell.receiver === 'mac') !== toMac || !cell.bytes) continue;
          const t = c.durable_s[i], w = c.wire_bytes[i], wall = c.wall_s[i];
          if (t) data.push((cell.bytes * 8) / t / 1e9);
          if (w && wall) { wire.push((w * 8) / wall / 1e9); ratios.push(cell.bytes / w); }
        }
      }
      const measured = ratios.length > 0;
      const ratio = step.level === 0 ? 1 : measured ? median(ratios) : sender.levels[step.level as 1 | 2 | 3].ratio * BLOCK_RATIO;
      const full = TEN_GIG * Math.max(1, ratio);
      const compressor = step.level === 0 ? Infinity : (sender.levels[step.level as 1 | 2 | 3].compress8 * 8) / 1000;
      rows.push({
        toMac, level: step.level, label: step.label, ratio, ratioMeasured: measured || step.level === 0,
        data: median(data), wire: median(wire), samples: data.length,
        full, compressor, max: Math.min(full, compressor),
        limit: compressor < full ? `${sender.name}'s compressor` : 'the link',
      });
    }
  }
  return rows;
}

function drawCeilings(details: RunDetail[]): void {
  const rows = ceilingRows(details);
  ceilings ??= new Plot($('tengig-ceiling-chart'));
  const directions = [
    { toMac: true, name: 'mars → Mac', color: BLUE },
    { toMac: false, name: 'Mac → mars', color: CYAN },
  ];
  ceilings.show((theme) => {
    const { muted, layout } = base(theme);
    return {
      data: directions.flatMap((dir) => {
        const mine = rows.filter((r) => r.toMac === dir.toMac);
        return [
          { type: 'bar', name: `${dir.name}, theoretical max`, x: mine.map((r) => r.label), y: mine.map((r) => r.max),
            marker: { color: alpha(dir.color, 0.22), line: { color: dir.color, width: 1.5 } },
            hovertemplate: `${dir.name}<br>%{x}: up to %{y:.1f} Gb/s of data<extra></extra>` },
          { type: 'bar', name: `${dir.name}, measured`, x: mine.map((r) => r.label), y: mine.map((r) => (isFinite(r.data) ? r.data : null)),
            marker: { color: dir.color },
            hovertemplate: `${dir.name}<br>%{x}: %{y:.1f} Gb/s of data, measured<extra></extra>` },
        ];
      }),
      layout: {
        ...layout,
        barmode: 'group',
        margin: { l: 56, r: 16, t: 12, b: 84 },
        legend: { orientation: 'h', x: 0, y: -0.2, yanchor: 'top' },
        xaxis: { tickfont: { color: muted } },
        yaxis: { title: { text: 'Gb/s of data delivered' }, rangemode: 'tozero', tickfont: { color: muted } },
        shapes: [{ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: TEN_GIG, y1: TEN_GIG, line: { color: muted, width: 1, dash: 'dash' } }],
        annotations: [{ xref: 'paper', x: 1, xanchor: 'right', y: TEN_GIG, yanchor: 'bottom', text: 'the link, 9.41', showarrow: false,
          font: { size: 10, color: muted } }],
      },
    };
  });
  const g = (v: number) => (isFinite(v) ? v.toFixed(1) : '—');
  $('tengig-ceiling-table').innerHTML = `<thead><tr><th>Direction</th><th>Compression</th><th data-numeric>Ratio in xs</th>
      <th data-numeric>Link full</th><th data-numeric>Sender's compressor</th><th data-numeric>Theoretical max</th>
      <th data-numeric>Measured</th><th data-numeric>On the wire</th><th data-numeric>Of max</th></tr></thead><tbody>${rows.map((r) =>
    `<tr><th scope="row">${r.toMac ? 'mars → Mac' : 'Mac → mars'}</th><td>${esc(r.label)}</td>
      <td data-numeric>${r.level ? `${r.ratio.toFixed(2)}×${r.ratioMeasured ? '' : ' (est.)'}` : '1×'}</td>
      <td data-numeric>${g(r.full)}</td><td data-numeric>${g(r.compressor)}</td>
      <td data-numeric><strong>${g(r.max)}</strong> <span class="dash-muted">${esc(r.limit)}</span></td>
      <td data-numeric>${g(r.data)}${r.samples ? ` <span class="dash-muted">n=${r.samples}</span>` : ''}</td><td data-numeric>${g(r.wire)}</td>
      <td data-numeric>${isFinite(r.data) ? `${Math.round((100 * r.data) / r.max)}%` : '—'}</td></tr>`).join('')}</tbody>`;
  const measuredRuns = details.length;
  $('tengig-ceiling-note').textContent = measuredRuns
    ? `Measured: ${CEILING_EXPERIMENT}, median of the valid samples so far. Compressor speeds: the ${CODEC_RUN.job} job, ${CODEC_RUN.date}, ${CODEC_RUN.file}, eight threads (mars ${CODEC.mars.note}; ${CODEC.mac.name} ${CODEC.mac.note}, so its figures vary).`
    : `${CEILING_EXPERIMENT} has not reported yet: ratios are estimated from zstd's own and the measured columns fill in as its samples arrive. Compressor speeds: the ${CODEC_RUN.job} job, ${CODEC_RUN.date}.`;
}

// Every valid sample's delivered rate (corpus bytes over the run's primary time), grouped by
// corpus, scenario, direction and arm. Cold and warm caches are pooled.
function aggregate(details: RunDetail[]): Map<string, Cell> {
  const cells = new Map<string, Cell>();
  for (const d of details) {
    const c = d.columns;
    const time = (c[d.primary as keyof typeof c] ?? c.wall_s) as (number | null)[];
    for (let i = 0; i < c.cell.length; i++) {
      if (!c.valid[i]) continue;
      const cell = d.cells[c.cell[i]];
      const t = time[i];
      if (!t || !cell.bytes || !cell.files) continue;
      const arm = d.arms[c.arm[i]].name;
      const toMac = cell.receiver === 'mac';
      const key = `${cell.corpus}|${cell.scenario}|${toMac}|${arm}`;
      let entry = cells.get(key);
      if (!entry) cells.set(key, (entry = { corpus: cell.corpus, scenario: cell.scenario, toMac, arm, files: cell.files, bytes: cell.bytes, gbps: [], fps: [] }));
      entry.gbps.push((cell.bytes * 8) / t / 1e9);
      entry.fps.push(cell.files / t);
    }
  }
  return cells;
}

function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  if (!s.length) return NaN;
  const m = (s.length - 1) / 2;
  return (s[Math.floor(m)] + s[Math.ceil(m)]) / 2;
}

const size = (bytes: number) => (bytes >= 2 ** 30 ? `${(bytes / 2 ** 30).toFixed(1)} GiB` : bytes >= 2 ** 20 ? `${(bytes / 2 ** 20).toFixed(1)} MiB` : `${(bytes / 1024).toFixed(1)} KiB`);
const rateText = (v: number) => (!isFinite(v) ? '—' : v >= 1 ? v.toFixed(2) : v.toFixed(3));

function base(theme: ChartTheme) {
  const muted = theme.colors?.muted ?? '#888';
  return {
    muted,
    layout: { paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { size: 11 } },
  };
}

function referenceLines(muted: string) {
  return [
    { type: 'line', xref: 'paper', x0: 0, x1: 1, y0: TEN_GIG, y1: TEN_GIG, line: { color: BLUE, width: 1, dash: 'dash' } },
    { type: 'line', xref: 'paper', x0: 0, x1: 1, y0: GIGABIT, y1: GIGABIT, line: { color: muted, width: 1, dash: 'dash' } },
  ];
}

function referenceNotes(muted: string) {
  return [
    { xref: 'paper', x: 0.01, xanchor: 'left', y: Math.log10(TEN_GIG), yanchor: 'bottom', text: '10 GbE, raw TCP 9.41', showarrow: false, font: { size: 10, color: BLUE } },
    { xref: 'paper', x: 0.01, xanchor: 'left', y: Math.log10(GIGABIT), yanchor: 'bottom', text: 'what gigabit carries, 0.94', showarrow: false, font: { size: 10, color: muted } },
  ];
}

// Fresh copies only: delivered rate against the corpus's average file size, per tool and direction.
function drawSpread(cells: Map<string, Cell>): void {
  const fresh = [...cells.values()].filter((c) => c.scenario === 'fresh' && (c.arm === 'xs' || c.arm === 'rsync') && c.bytes / c.files >= 1024);
  const series = [
    { arm: 'xs', toMac: false, name: 'xs, onto mars (NVMe)', color: BLUE, symbol: 'circle' },
    { arm: 'xs', toMac: true, name: 'xs, onto the Mac (APFS)', color: CYAN, symbol: 'diamond' },
    { arm: 'rsync', toMac: false, name: 'rsync, onto mars', color: GREY, symbol: 'circle-open' },
    { arm: 'rsync', toMac: true, name: 'rsync, onto the Mac', color: GREY, symbol: 'diamond-open' },
  ];
  spread!.show((theme) => {
    const { muted, layout } = base(theme);
    return {
      data: series.map((s) => {
        const mine = fresh.filter((c) => c.arm === s.arm && c.toMac === s.toMac).sort((a, b) => a.bytes / a.files - b.bytes / b.files);
        return {
          type: 'scatter', mode: 'markers', name: s.name,
          x: mine.map((c) => c.bytes / c.files), y: mine.map((c) => median(c.gbps)),
          marker: { color: s.color, size: s.arm === 'xs' ? 10 : 8, symbol: s.symbol, line: { color: s.color, width: 1.5 } },
          customdata: mine.map((c) => [c.corpus, c.files.toLocaleString(), size(c.bytes / c.files), Math.round(median(c.fps)).toLocaleString(), c.gbps.length]),
          hovertemplate: `%{customdata[0]}<br>${s.name}<br>%{y:.2f} Gb/s, %{customdata[3]} files/s<br>%{customdata[1]} files, %{customdata[2]} on average · %{customdata[4]} samples<extra></extra>`,
        };
      }),
      layout: {
        ...layout,
        margin: { l: 56, r: 16, t: 12, b: 96 },
        legend: { orientation: 'h', x: 0, y: -0.3, yanchor: 'top' },
        xaxis: { type: 'log', title: { text: 'average file size (bytes)' }, tickvals: [1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9], ticktext: ['1 KB', '10 KB', '100 KB', '1 MB', '10 MB', '100 MB', '1 GB'], tickfont: { color: muted } },
        yaxis: { type: 'log', title: { text: 'delivered Gb/s' }, range: [Math.log10(0.03), Math.log10(14)], tickvals: [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10], ticktext: ['0.05', '0.1', '0.25', '0.5', '1', '2.5', '5', '10'], tickfont: { color: muted } },
        shapes: [
          { type: 'rect', xref: 'paper', x0: 0, x1: 1, y0: 0.03, y1: GIGABIT, fillcolor: alpha(muted, 0.07), line: { width: 0 }, layer: 'below' },
          ...referenceLines(muted),
        ],
        // Where the corpora fall, named once rather than per point (hover names each point).
        annotations: [
          ...referenceNotes(muted),
          ...[[3e3, 'small files'], [2.5e5, 'mixed trees'], [4e8, 'large files']].map(([x, text]) => ({
            x: Math.log10(x as number), y: Math.log10(0.035), yanchor: 'bottom', text, showarrow: false, font: { size: 11, color: muted },
          })),
        ],
      },
    };
  });
}

// Compression on data that compresses: delivered data rate per arm, per corpus and direction.
function drawCodecs(cells: Map<string, Cell>): void {
  const groups = [
    { corpus: 'large-text', toMac: true, name: 'large-text, mars → Mac', color: BLUE },
    { corpus: 'large-text', toMac: false, name: 'large-text, Mac → mars', color: CYAN },
    { corpus: 'large-half', toMac: true, name: 'large-half, mars → Mac', color: AMBER },
    { corpus: 'large-half', toMac: false, name: 'large-half, Mac → mars', color: '#ec4899' },
  ];
  const present = groups.filter((g) => COMPRESSION_ARMS.some((a) => cells.has(`${g.corpus}|fresh|${g.toMac}|${a}`)));
  $('tengig-codecs-figure').hidden = present.length === 0;
  if (!present.length) return;
  const arms = COMPRESSION_ARMS.filter((a) => present.some((g) => cells.has(`${g.corpus}|fresh|${g.toMac}|${a}`)));
  codecs!.show((theme) => {
    const { muted, layout } = base(theme);
    return {
      data: present.map((g) => {
        const values = arms.map((a) => cells.get(`${g.corpus}|fresh|${g.toMac}|${a}`));
        return {
          type: 'bar', name: g.name, x: arms.map((a) => ARM_LABEL[a] ?? a), y: values.map((v) => (v ? median(v.gbps) : null)),
          marker: { color: g.color },
          customdata: values.map((v) => [v?.gbps.length ?? 0]),
          hovertemplate: `${g.name}<br>%{x}: %{y:.2f} Gb/s of data<br>%{customdata[0]} samples<extra></extra>`,
        };
      }),
      layout: {
        ...layout,
        barmode: 'group',
        margin: { l: 56, r: 16, t: 12, b: 84 },
        legend: { orientation: 'h', x: 0, y: -0.2, yanchor: 'top' },
        xaxis: { tickfont: { color: muted } },
        yaxis: { title: { text: 'delivered Gb/s of data' }, range: [0, 10.5], tickfont: { color: muted } },
        shapes: referenceLines(muted).map((s) => ({ ...s })),
      },
    };
  });
}

function renderTable(cells: Map<string, Cell>): void {
  const corpora = [...new Set([...cells.values()].filter((c) => c.scenario === 'fresh' && c.bytes / c.files >= 1024).map((c) => c.corpus))];
  const info = (corpus: string) => [...cells.values()].find((c) => c.corpus === corpus)!;
  corpora.sort((a, b) => info(b).bytes / info(b).files - info(a).bytes / info(a).files);
  const get = (corpus: string, toMac: boolean, arm: string) => {
    const c = cells.get(`${corpus}|fresh|${toMac}|${arm}`);
    return c ? median(c.gbps) : NaN;
  };
  const rows = corpora.map((corpus) => {
    const c = info(corpus);
    const xs = [get(corpus, false, 'xs'), get(corpus, true, 'xs')];
    const best = Math.max(...xs.filter(isFinite));
    const [label, status] = best >= 2 ? ['Uses 10 GbE', 'success'] : best >= GIGABIT ? ['Some gain over gigabit', 'warning'] : ['Gigabit is enough', 'neutral'];
    const cell = (v: number) => `<td data-numeric>${rateText(v)}</td>`;
    return `<tr><th scope="row">${esc(corpus)}</th><td data-numeric>${c.files.toLocaleString()}</td><td data-numeric>${esc(size(c.bytes / c.files))}</td>
      ${cell(xs[0])}${cell(xs[1])}${cell(get(corpus, false, 'rsync'))}${cell(get(corpus, true, 'rsync'))}
      <td>${isFinite(best) ? `<span class="hcss-badge" data-status="${status}">${label}</span>` : '—'}</td></tr>`;
  });
  $('tengig-table').innerHTML = `<thead><tr><th>Corpus</th><th data-numeric>Files</th><th data-numeric>Average file</th>
      <th data-numeric>xs onto mars</th><th data-numeric>xs onto Mac</th><th data-numeric>rsync onto mars</th><th data-numeric>rsync onto Mac</th><th>Verdict</th></tr></thead>
    <tbody>${rows.join('') || '<tr><td colspan="8" class="dash-muted">No fresh copies yet.</td></tr>'}</tbody>`;
}

