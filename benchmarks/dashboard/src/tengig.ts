// The 10 GbE view: results from the direct 10 GbE cable between the Mac and mars, and only
// from runs made once it ran at full speed (their preflight required 10 000 Mb/s; earlier runs
// on the same cable topped out near 3 Gb/s). The commentary is in index.html; the charts and
// table here are computed from the runs themselves, so they follow new runs as they arrive.
import { alpha, Plot, type ChartTheme } from './charts';
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

