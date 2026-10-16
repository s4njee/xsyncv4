// The Runs view: every past run's samples, for anyone to explore. Pick a run, then a
// measure, a cell and a scale; the charts show the spread per arm and the samples over
// time, the table the medians and their ratio to the control, and the run downloads as
// CSV or JSON. Links to a run (#runs/<group>/<experiment>/<run>) can be shared.
import { alpha, Plot, type ChartTheme } from './charts';
import { cellLabel, duration, esc, runName } from './format';
import type { RunDetail, RunIndex } from './types';

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

interface Metric {
  label: string;
  unit: string;
  higher: boolean; // is a larger value better?
  value(detail: RunDetail, i: number): number | null;
}

const seconds = (field: keyof RunDetail['columns']) => (d: RunDetail, i: number) => d.columns[field][i] as number | null;
const MiB = (field: 'client_rss' | 'peer_rss') => (d: RunDetail, i: number) => {
  const v = d.columns[field][i];
  return v == null ? null : v / 2 ** 20;
};

const METRICS: Record<string, Metric> = {
  gbps: {
    label: 'Corpus rate', unit: 'Gb/s', higher: true,
    value(d, i) {
      const bytes = d.cells[d.columns.cell[i]]?.bytes;
      const t = d.columns[(d.primary in d.columns ? d.primary : 'wall_s') as 'wall_s'][i];
      return bytes != null && t ? (bytes * 8) / t / 1e9 : null;
    },
  },
  durable_s: { label: 'Time to durable', unit: 's', higher: false, value: seconds('durable_s') },
  wall_s: { label: 'Wall time', unit: 's', higher: false, value: seconds('wall_s') },
  sync_s: { label: 'Sync time', unit: 's', higher: false, value: seconds('sync_s') },
  client_cpu_s: { label: 'Client CPU', unit: 'CPU s', higher: false, value: seconds('client_cpu_s') },
  peer_cpu_s: { label: 'Peer CPU', unit: 'CPU s', higher: false, value: seconds('peer_cpu_s') },
  client_rss: { label: 'Client peak memory', unit: 'MiB', higher: false, value: MiB('client_rss') },
  peer_rss: { label: 'Peer peak memory', unit: 'MiB', higher: false, value: MiB('peer_rss') },
  wire: {
    label: 'Bytes on the wire per corpus byte', unit: '×', higher: false,
    value(d, i) {
      const bytes = d.cells[d.columns.cell[i]]?.bytes, wire = d.columns.wire_bytes[i];
      return bytes && wire != null ? wire / bytes : null;
    },
  },
};

const PALETTE = ['#3b82ff', '#22d3ee', '#f59e0b', '#ec4899', '#22c55e', '#a855f7', '#f97316', '#84cc16', '#14b8a6', '#e11d48'];
const CONTROL_COLOR = '#94a3b8';

const view = {
  key: '' as string,
  metric: 'gbps',
  cell: '' as string, // '' = every cell
  // Cells differ by orders of magnitude, so the default compares each arm with the control.
  scale: 'relative' as 'absolute' | 'relative',
  voided: false,
};
const details = new Map<string, Promise<RunDetail | null>>();
let runs: RunIndex[] = [];
let spread: Plot | null = null;
let timeline: Plot | null = null;
let shown: RunDetail | null = null;
let downloads: string[] = [];

// --- the list --------------------------------------------------------------------------

export function renderRunList(all: RunIndex[] | undefined): void {
  runs = all || [];
  const filter = ($<HTMLInputElement>('runs-filter').value || '').toLowerCase().trim();
  const groupSelect = $<HTMLSelectElement>('runs-group');
  const group = groupSelect.value;
  const groups = [...new Set(runs.map((r) => r.group))].sort();
  if (groupSelect.options.length - 1 !== groups.length)
    groupSelect.innerHTML = `<option value="">All links</option>${groups.map((g) => `<option value="${esc(g)}">${esc(g)}</option>`).join('')}`;
  groupSelect.value = group;
  const words = filter.split(/\s+/).filter(Boolean);
  const list = runs.filter((r) => (!group || r.group === group)
    && words.every((w) => [r.experiment, r.run, r.kind, ...r.arms, ...r.corpora, ...r.links].join(' ').toLowerCase().includes(w)));
  $('runs-count').textContent = `${list.length} of ${runs.length} runs`;
  $('runs-list').innerHTML = list.map((r) => {
    const when = r.started ? new Date(r.started * 1000) : null;
    const status = r.state === 'complete' ? 'success' : r.state === 'running' ? 'info' : 'warning';
    return `<li><button class="hcss-button dash-exp" data-variant="ghost" type="button" data-run="${esc(r.key)}" ${r.key === view.key ? 'aria-current="true"' : ''}>
      <span class="dash-exp-name">${esc(r.experiment)}</span>
      <span class="dash-muted">${when ? esc(when.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })) : '—'} · ${esc(r.group)} · ${r.valid} samples${r.voided ? `, ${r.voided} void` : ''}</span>
      <span class="hcss-cluster dash-tight"><span class="hcss-badge" data-status="neutral">${esc(r.kind || 'run')}</span>${r.state ? `<span class="hcss-badge" data-status="${status}">${esc(r.state)}</span>` : ''}</span>
    </button></li>`;
  }).join('') || '<li class="dash-muted">No runs match.</li>';
}

// --- one run ---------------------------------------------------------------------------

function fetchRun(key: string): Promise<RunDetail | null> {
  let pending = details.get(key);
  if (!pending) {
    pending = fetch(`/api/run?key=${encodeURIComponent(key)}`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
    details.set(key, pending);
    void pending.then((d) => { if (!d) details.delete(key); });
  }
  return pending;
}

export async function openRun(key: string): Promise<void> {
  if (!key) return;
  const changed = key !== view.key;
  view.key = key;
  for (const b of document.querySelectorAll<HTMLElement>('#runs-list [data-run]')) b.toggleAttribute('aria-current', b.dataset.run === key);
  const host = $('run');
  if (changed) host.setAttribute('aria-busy', 'true');
  const detail = await fetchRun(key);
  if (view.key !== key) return;
  host.removeAttribute('aria-busy');
  if (!detail) {
    host.innerHTML = '<div class="hcss-empty-state"><p>This run is not available yet. Its samples reach the dashboard a minute or two after they are collected.</p></div>';
    shown = null;
    return;
  }
  if (changed || shown !== detail) {
    if (!detail.cells.some((c) => c.id === view.cell)) view.cell = '';
    renderRun(detail);
  }
}

function renderRun(detail: RunDetail): void {
  shown = detail;
  spread?.destroy();
  timeline?.destroy();
  for (const url of downloads) URL.revokeObjectURL(url);
  downloads = [];
  const span = detail.started && detail.ended ? duration(detail.ended - detail.started) : '—';
  const started = detail.started ? new Date(detail.started * 1000).toLocaleString() : '—';
  const metricOptions = Object.entries(METRICS)
    .filter(([name]) => name !== 'wire' || detail.columns.wire_bytes.some((v) => v != null))
    .map(([name, m]) => `<option value="${name}">${esc(m.label)} (${esc(m.unit)})</option>`).join('');
  const cellOptions = `<option value="">Every cell (${detail.cells.length})</option>`
    + detail.cells.map((c) => `<option value="${esc(c.id)}">${esc(cellLabel(c.id))}</option>`).join('');
  const csv = URL.createObjectURL(new Blob([toCsv(detail)], { type: 'text/csv' }));
  const json = URL.createObjectURL(new Blob([JSON.stringify(detail)], { type: 'application/json' }));
  downloads.push(csv, json);
  const base = `${detail.experiment}-${detail.run.slice(0, 16)}`;
  $('run').innerHTML = `
    <header class="hcss-stack dash-tight">
      <p class="hcss-eyebrow">${esc(detail.group)} · ${esc(detail.kind || 'run')}${detail.driver ? ` · driven from ${esc(detail.driver)}` : ''}</p>
      <h2>${esc(detail.experiment)} <span class="dash-muted dash-run-id">${esc(detail.run.slice(0, 16))}</span></h2>
      ${detail.hypothesis ? `<p class="dash-muted dash-hypothesis">${esc(detail.hypothesis)}</p>` : ''}
    </header>
    <div class="hcss-stat-row dash-stats">
      <dl class="hcss-stat"><dt>Samples</dt><dd>${detail.valid}${detail.planned ? ` / ${detail.planned}` : ''}</dd></dl>
      <dl class="hcss-stat"><dt>Voided</dt><dd>${detail.voided}</dd></dl>
      <dl class="hcss-stat"><dt>Ran for</dt><dd>${esc(span)}</dd></dl>
      <dl class="hcss-stat"><dt>Cells × arms</dt><dd>${detail.cells.length} × ${detail.arms.length}</dd></dl>
    </div>
    <p class="dash-muted">Started ${esc(started)}. Arms: ${detail.arms.map((a) => `<code>${esc(a.name)}</code>${a.name === detail.control ? ' (control)' : ''}`).join(', ')}.
      Primary measure: <code>${esc(detail.primary)}</code>${detail.revs.length ? `; engine ${detail.revs.map((r) => `<code>${esc(r)}</code>`).join(', ')}` : ''}.</p>
    <div class="hcss-cluster dash-run-controls">
      <label class="dash-control"><span>Measure</span><select class="hcss-select" id="run-metric">${metricOptions}</select></label>
      <label class="dash-control"><span>Cell</span><select class="hcss-select" id="run-cell">${cellOptions}</select></label>
      <fieldset class="hcss-segmented" aria-label="Scale">
        <label><input type="radio" name="run-scale" value="absolute"> Absolute</label>
        <label><input type="radio" name="run-scale" value="relative"> ÷ control</label>
      </fieldset>
      <label class="hcss-choice"><input class="hcss-checkbox" type="checkbox" id="run-voided"> Show voided</label>
    </div>
    <figure class="dash-run-figure"><figcaption class="dash-muted" id="run-spread-caption"></figcaption><div class="dash-run-chart" id="run-spread"></div></figure>
    <figure class="dash-run-figure"><figcaption class="dash-muted">Each sample in the order it ran, so drift and noise show</figcaption><div class="dash-run-chart dash-run-chart-short" id="run-timeline"></div></figure>
    <div class="hcss-table-scroll" role="region" tabindex="0" aria-label="Medians by cell and arm"><table class="hcss-table dash-table" id="run-table"></table></div>
    <p class="hcss-cluster dash-tight">
      <a class="hcss-button" data-variant="outline" data-size="sm" href="${csv}" download="${esc(base)}.csv">Download CSV</a>
      <a class="hcss-button" data-variant="outline" data-size="sm" href="${json}" download="${esc(base)}.json">Download JSON</a>
      <a class="hcss-button" data-variant="ghost" data-size="sm" href="#runs/${esc(detail.key)}" id="run-link">Link to this run</a>
    </p>`;
  if (!METRICS[view.metric] || !$<HTMLSelectElement>('run-metric').querySelector(`option[value="${view.metric}"]`)) view.metric = 'gbps';
  $<HTMLSelectElement>('run-metric').value = view.metric;
  $<HTMLSelectElement>('run-cell').value = view.cell;
  $<HTMLInputElement>('run-voided').checked = view.voided;
  for (const radio of document.querySelectorAll<HTMLInputElement>('input[name="run-scale"]')) radio.checked = radio.value === view.scale;
  spread = new Plot($('run-spread'));
  timeline = new Plot($('run-timeline'));
  drawRun(false);
}

function controlsChanged(): void {
  view.metric = $<HTMLSelectElement>('run-metric').value;
  view.cell = $<HTMLSelectElement>('run-cell').value;
  view.voided = $<HTMLInputElement>('run-voided').checked;
  view.scale = (document.querySelector<HTMLInputElement>('input[name="run-scale"]:checked')?.value as 'absolute' | 'relative') || 'absolute';
  drawRun(true);
}

interface Point { i: number; cell: number; arm: number; value: number; valid: boolean }

const median = (values: number[]) => quantile(values, 0.5);
function quantile(values: number[], q: number): number {
  const sorted = [...values].sort((a, b) => a - b);
  if (!sorted.length) return NaN;
  const at = (sorted.length - 1) * q, lo = Math.floor(at), hi = Math.ceil(at);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (at - lo);
}

function points(detail: RunDetail, metric: Metric): Point[] {
  const out: Point[] = [];
  const cellFilter = view.cell ? detail.cells.findIndex((c) => c.id === view.cell) : -1;
  for (let i = 0; i < detail.columns.cell.length; i++) {
    const valid = detail.columns.valid[i] === 1;
    if (!valid && !view.voided) continue;
    if (cellFilter >= 0 && detail.columns.cell[i] !== cellFilter) continue;
    const value = metric.value(detail, i);
    if (value == null || !isFinite(value)) continue;
    out.push({ i, cell: detail.columns.cell[i], arm: detail.columns.arm[i], value, valid });
  }
  // Relative: each sample over the control arm's median in its cell (valid samples only).
  if (view.scale === 'relative') {
    const control = detail.arms.findIndex((a) => a.name === detail.control);
    const base = new Map<number, number>();
    for (const cell of new Set(out.map((p) => p.cell))) {
      const m = median(out.filter((p) => p.cell === cell && p.arm === control && p.valid).map((p) => p.value));
      if (isFinite(m) && m > 0) base.set(cell, m);
    }
    return out.filter((p) => base.has(p.cell)).map((p) => ({ ...p, value: p.value / base.get(p.cell)! }));
  }
  return out;
}

function armColor(detail: RunDetail, arm: number): string {
  if (detail.arms[arm]?.name === detail.control) return CONTROL_COLOR;
  const others = detail.arms.map((a, i) => (a.name === detail.control ? -1 : i)).filter((i) => i >= 0);
  return PALETTE[others.indexOf(arm) % PALETTE.length];
}

function drawRun(animate: boolean): void {
  const detail = shown;
  if (!detail || !spread || !timeline) return;
  const metric = METRICS[view.metric];
  const pts = points(detail, metric);
  const relative = view.scale === 'relative';
  const unit = relative ? `÷ ${detail.control ?? 'control'} median` : metric.unit;
  const better = metric.higher ? 'higher is better' : 'lower is better';
  const note = view.metric === 'gbps' ? ` Corpus rate is the corpus size over the ${detail.primary}; on no-op and update cells it is a scan rate, not bytes moved.` : '';
  $('run-spread-caption').textContent = `${metric.label}${relative ? ` relative to ${detail.control ?? 'the control'}'s median` : ''}, per arm${view.cell ? '' : ' and cell'}: the box is the middle half, the line the median, the dots every sample (${better}).${note}`;
  const arms = [...new Set(pts.map((p) => p.arm))].sort((a, b) => a - b);
  const cellOrder = detail.cells.map((_, i) => i).filter((i) => pts.some((p) => p.cell === i));
  const labels = detail.cells.map((c) => cellLabel(c.id));
  const tick = (theme: ChartTheme) => theme.colors?.muted ?? '#888';
  const valueFormat = metric.unit === 's' || metric.unit === 'CPU s' ? '.3f' : '.3~f';

  spread.show((theme) => ({
    data: arms.map((arm) => {
      const mine = pts.filter((p) => p.arm === arm);
      const color = armColor(detail, arm);
      return {
        type: 'box', name: detail.arms[arm].name,
        x: mine.map((p) => labels[p.cell]), y: mine.map((p) => p.value),
        boxpoints: 'all', jitter: 0.4, pointpos: 0,
        marker: { color, size: 4, opacity: 0.75 }, line: { color, width: 1.5 }, fillcolor: alpha(color, 0.16),
        customdata: mine.map((p) => [detail.columns.block[p.i], p.valid ? '' : ' (void)']),
        hovertemplate: `%{x}<br>${esc(detail.arms[arm].name)}: %{y:${valueFormat}} ${esc(unit)}<br>block %{customdata[0]}%{customdata[1]}<extra></extra>`,
      };
    }),
    layout: {
      boxmode: 'group', showlegend: true, legend: { orientation: 'h', y: 1.12, x: 0 },
      margin: { l: 56, r: 12, t: 28, b: cellOrder.length > 1 ? 96 : 36 },
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      xaxis: { categoryorder: 'array', categoryarray: cellOrder.map((i) => labels[i]), tickfont: { size: 10, color: tick(theme) }, tickangle: cellOrder.length > 4 ? -30 : 0 },
      yaxis: { title: { text: unit, font: { size: 11 } }, zeroline: false, rangemode: relative ? 'normal' : 'tozero' },
      ...(relative ? { shapes: [{ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 1, y1: 1, line: { color: tick(theme), width: 1, dash: 'dash' } }] } : {}),
    },
  }), animate);

  timeline.show((theme) => ({
    data: [
      ...arms.map((arm) => {
        const mine = pts.filter((p) => p.arm === arm && p.valid && detail.columns.utc[p.i] != null);
        const color = armColor(detail, arm);
        return {
          type: 'scatter', mode: 'markers', name: detail.arms[arm].name, showlegend: false,
          x: mine.map((p) => new Date(detail.columns.utc[p.i]! * 1000).toISOString()), y: mine.map((p) => p.value),
          marker: { color, size: 5, opacity: 0.85 },
          customdata: mine.map((p) => [labels[p.cell], detail.columns.block[p.i]]),
          hovertemplate: `%{x}<br>%{customdata[0]} · block %{customdata[1]}<br>${esc(detail.arms[arm].name)}: %{y:${valueFormat}} ${esc(unit)}<extra></extra>`,
        };
      }),
      ...(view.voided ? [(() => {
        const bad = pts.filter((p) => !p.valid && detail.columns.utc[p.i] != null);
        return {
          type: 'scatter', mode: 'markers', name: 'voided', showlegend: false,
          x: bad.map((p) => new Date(detail.columns.utc[p.i]! * 1000).toISOString()), y: bad.map((p) => p.value),
          marker: { color: '#dc2626', size: 7, symbol: 'x' },
          customdata: bad.map((p) => [labels[p.cell], detail.columns.void[p.i] ?? 'void']),
          hovertemplate: '%{x}<br>%{customdata[0]}<br>void: %{customdata[1]}<extra></extra>',
        };
      })()] : []),
    ],
    layout: {
      showlegend: false, margin: { l: 56, r: 12, t: 8, b: 36 },
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      xaxis: { type: 'date', tickfont: { size: 10, color: tick(theme) } },
      yaxis: { title: { text: unit, font: { size: 11 } }, zeroline: false, rangemode: relative ? 'normal' : 'tozero' },
    },
  }), animate);

  renderTable(detail, metric, pts);
}

function renderTable(detail: RunDetail, metric: Metric, pts: Point[]): void {
  const control = detail.arms.findIndex((a) => a.name === detail.control);
  const relative = view.scale === 'relative';
  const fmt = (v: number) => (!isFinite(v) ? '—' : Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(3));
  const delta = detail.delta ?? 0.03;
  const rows: string[] = [];
  for (const [ci, cell] of detail.cells.entries()) {
    const inCell = pts.filter((p) => p.cell === ci && p.valid);
    if (!inCell.length) continue;
    const base = median(inCell.filter((p) => p.arm === control).map((p) => p.value));
    const arms = [...new Set(inCell.map((p) => p.arm))].sort((a, b) => a - b);
    arms.forEach((arm, k) => {
      const values = inCell.filter((p) => p.arm === arm).map((p) => p.value);
      const m = median(values);
      const ratio = arm === control || !isFinite(base) || base === 0 ? NaN : m / base;
      const gain = isFinite(ratio) ? (metric.higher ? ratio - 1 : 1 - ratio) : 0;
      const status = !isFinite(ratio) ? '' : gain > delta ? 'success' : gain < -delta ? 'danger' : 'neutral';
      rows.push(`<tr>${k === 0 ? `<th scope="rowgroup" rowspan="${arms.length}">${esc(cellLabel(cell.id))}</th>` : ''}
        <td><span class="dash-swatch" style="--swatch:${armColor(detail, arm)}"></span>${esc(detail.arms[arm].name)}${arm === control ? ' <span class="dash-muted">(control)</span>' : ''}</td>
        <td data-numeric>${values.length}</td><td data-numeric>${fmt(m)}</td>
        <td data-numeric>${fmt(quantile(values, 0.1))} – ${fmt(quantile(values, 0.9))}</td>
        <td data-numeric>${isFinite(ratio) && !relative ? `<span class="hcss-badge" data-status="${status}">${ratio.toFixed(3)}</span>` : relative && arm !== control ? `<span class="hcss-badge" data-status="${status}">${m.toFixed(3)}</span>` : '—'}</td></tr>`);
    });
  }
  const unit = relative ? 'ratio' : metric.unit;
  $('run-table').innerHTML = `<thead><tr><th>Cell</th><th>Arm</th><th data-numeric>n</th><th data-numeric>Median (${esc(unit)})</th><th data-numeric>10th – 90th</th><th data-numeric>÷ control</th></tr></thead>
    <tbody>${rows.join('') || '<tr><td colspan="6" class="dash-muted">No valid samples for this measure.</td></tr>'}</tbody>`;
}

function toCsv(detail: RunDetail): string {
  const c = detail.columns;
  const head = ['experiment', 'run', 'cell', 'corpus', 'scenario', 'sender', 'receiver', 'client', 'link', 'cache', 'corpus_files', 'corpus_bytes',
    'arm', 'tool', 'control', 'block', 'attempt', 'position', 'valid', 'void_reason', 'utc_start', 'wall_s', 'sync_s', 'durable_s',
    'client_cpu_s', 'peer_cpu_s', 'client_rss_bytes', 'peer_rss_bytes', 'wire_bytes', 'retransmits', 'rev'];
  const quote = (v: unknown) => {
    const s = v == null ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [head.join(',')];
  for (let i = 0; i < c.cell.length; i++) {
    const cell = detail.cells[c.cell[i]], arm = detail.arms[c.arm[i]];
    lines.push([detail.experiment, detail.run, cell.id, cell.corpus, cell.scenario, cell.sender, cell.receiver, cell.client, cell.link, cell.cache,
      cell.files, cell.bytes, arm.name, arm.tool, c.control[i], c.block[i], c.attempt[i], c.position[i], c.valid[i], c.void[i],
      c.utc[i] == null ? '' : new Date(c.utc[i]! * 1000).toISOString(), c.wall_s[i], c.sync_s[i], c.durable_s[i], c.client_cpu_s[i], c.peer_cpu_s[i],
      c.client_rss[i], c.peer_rss[i], c.wire_bytes[i], c.retransmits[i], c.rev[i] == null ? '' : detail.revs[c.rev[i]!]].map(quote).join(','));
  }
  return `${lines.join('\n')}\n`;
}

// --- wiring ------------------------------------------------------------------------------

export function setupRuns(getRuns: () => RunIndex[] | undefined): void {
  $('runs-filter').addEventListener('input', () => renderRunList(getRuns()));
  $('runs-group').addEventListener('change', () => renderRunList(getRuns()));
  $('runs-list').addEventListener('click', (event) => {
    const button = (event.target as Element).closest<HTMLElement>('[data-run]');
    if (!button?.dataset.run) return;
    location.hash = `runs/${button.dataset.run}`;
    // Side by side the run is already in view; stacked, bring it up.
    const run = $('run');
    if (run.getBoundingClientRect().top > innerHeight * 0.6) run.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  });
  $('run').addEventListener('change', (event) => {
    if ((event.target as Element).closest('#run-metric, #run-cell, #run-voided, input[name="run-scale"]')) controlsChanged();
  });
}

// When the run index changes, a run on screen that has grown is fetched again.
export function runsUpdated(all: RunIndex[] | undefined): void {
  const before = runs.find((r) => r.key === view.key);
  renderRunList(all);
  const after = (all || []).find((r) => r.key === view.key);
  if (before && after && after.samples !== before.samples) {
    details.delete(view.key);
    void openRun(view.key);
  }
}

export function showRuns(all: RunIndex[] | undefined, key: string): void {
  renderRunList(all);
  if (key) void openRun(key);
  else if (!view.key) $('run').innerHTML = '<div class="hcss-empty-state"><p>Choose a run to see its samples: the spread per arm, the samples over time, and the medians against the control.</p></div>';
}
