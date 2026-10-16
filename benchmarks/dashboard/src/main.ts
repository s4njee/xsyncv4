import './style.css';
import './text';
import { createTheme } from '@mk7s/holocss/theme';
import { createToastQueue } from '@mk7s/holocss/components/controllers';
import { Live } from './live';
import { ago, cellLabel, clock, duration, esc, gib, rate, runName, seconds, VERDICT_STATUS } from './format';
import { ForestChart, SpeedChart, type ForestRow } from './charts';
import { startInk } from './ink';
import { renderRunList, runsUpdated, setupRuns, showRuns } from './runs';
import { renderTenGig } from './tengig';
import type { DashEvent, Effect, ExperimentDetail, ExperimentIndex, HostMessage, RunnerMessage, State } from './types';

const live = new Live();
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

// --- theme, toasts, views -------------------------------------------------------
const theme = createTheme(document.documentElement);
const themeSelect = $<HTMLSelectElement>('theme');
theme.subscribe(({ theme: value }: { theme: string }) => (themeSelect.value = value));
themeSelect.addEventListener('change', () => theme.set(themeSelect.value as never));
const toasts = createToastQueue($('toast'), { maxPending: 5, duration: 8000 });

const views = ['live', 'results', 'runs', 'tengig', 'events'];
function showView(): void {
  // #runs/<group>/<experiment>/<run> opens one run.
  const [name, ...rest] = location.hash.slice(1).split('/');
  const view = views.includes(name) ? name : 'live';
  for (const name of views) {
    $(`view-${name}`).hidden = name !== view;
    document.querySelector(`[data-view="${name}"]`)?.toggleAttribute('aria-current', name === view);
    if (name === view) document.querySelector(`[data-view="${name}"]`)?.setAttribute('aria-current', 'page');
  }
  if (view === 'results') renderResults();
  if (view === 'runs') showRuns(live.state.runs, rest.join('/'));
  if (view === 'tengig') void renderTenGig(live.state.runs);
}
setupRuns(() => live.state.runs);
addEventListener('hashchange', showView);

// --- connection status ------------------------------------------------------------
live.onStatus((status) => {
  const badge = $('connection');
  badge.textContent = status === 'live' ? 'live' : status;
  badge.dataset.status = status === 'live' ? 'success' : status === 'reconnecting' ? 'warning' : 'neutral';
});
setInterval(() => {
  $('updated').textContent = live.lastMessage ? `updated ${ago(live.lastMessage / 1000)}` : '';
  tickClocks(document);
}, 1000);

// The run clocks count on their own between updates: "running for" as a stopwatch, and
// "left" down to the estimated finish. When "left" shows a new value it slides in (CSS
// dash-roll); a card rebuilt with the same value does not replay it.
const shownLeft = new Map<string, string>();

// The samples count, one card per digit like a flip clock. A digit that differs from what this
// counter last showed flips in; the card is rebuilt on every update, so the last value is kept here
// and a rebuild with the same count does not flip again. Digits are matched from the right, so
// 99 -> 100 flips every place. Reduced motion turns the flip off (CSS).
const shownSamples = new Map<string, string>();
function flipDigits(key: string, value: number): string {
  const text = String(value);
  const before = shownSamples.get(key);
  shownSamples.set(key, text);
  return `<span class="dash-flip" aria-hidden="true">${[...text].map((digit, i) => {
    const old = before?.[before.length - text.length + i];
    const flips = before !== undefined && old !== digit;
    return `<span class="dash-flip-digit${flips ? ' is-flipping' : ''}">${digit}</span>`;
  }).join('')}</span>`;
}
const stopwatch = (total: number) => {
  const t = Math.max(0, Math.floor(total)), h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60;
  return `${h ? `${h}:${String(m).padStart(2, '0')}` : m}:${String(s).padStart(2, '0')}`;
};
function tickClocks(root: ParentNode): void {
  const now = Date.now() / 1000;
  for (const el of root.querySelectorAll<HTMLElement>('[data-since]')) el.textContent = stopwatch(now - Number(el.dataset.since));
  for (const el of root.querySelectorAll<HTMLElement>('[data-until]')) {
    const text = el.dataset.until ? duration(Math.max(0, Number(el.dataset.until) - now)) : '—';
    const key = el.dataset.key ?? '';
    if (el.textContent !== text) {
      el.textContent = text;
      if (shownLeft.has(key) && shownLeft.get(key) !== text) {
        el.removeAttribute('data-changed');
        void el.offsetWidth; // restart the animation
        el.setAttribute('data-changed', '');
      }
    }
    shownLeft.set(key, text);
  }
}

// --- runner cards -----------------------------------------------------------------
// Drivers in the order their cards appear: the week's wired pair first.
const DRIVER_ORDER = ['neo', 'mac', 'mars'];
const DRIVER_TITLES: Record<string, string> = { neo: 'neo ↔ freya', mac: 'Mac ↔ mars', mars: 'orion ↔ mars' };
const LINK_NAMES: Record<string, string> = {
  lan: 'neo ↔ freya (wired)', mesh: 'neo ↔ mars', wifi: 'orion ↔ mars (Wi-Fi)', 'mac-mars': 'Mac ↔ mars (mesh)',
  'mac-mars-direct': 'Mac ↔ mars (10 GbE)', 'mac-mars-hdd': 'Mac ↔ mars hard drive',
  'mac-mars-2g5': 'Mac ↔ mars (2.5 GbE)', 'mac-mars-hdd-2g5': 'Mac ↔ mars hard drive (2.5 GbE)',
};
interface Card { root: HTMLElement; body: HTMLElement; speed: HTMLElement; spark: SpeedChart; chart: ForestChart | null; chartHost: HTMLElement; chartKey: string; shown: number }
const cards = new Map<string, Card>();

function stateBadge(message: RunnerMessage): [string, string] {
  if (!message.ok) return ['unreachable', 'danger'];
  const runner = message.snapshot?.runner;
  if (!runner) return ['no runner', 'neutral'];
  if (!runner.alive) return ['not running', 'danger'];
  if (runner.paused || runner.state === 'paused') return ['paused', 'warning'];
  if (runner.state === 'halted') return ['halted', 'danger'];
  if (runner.state === 'running') return ['running', 'success'];
  return [runner.state, 'info'];
}

function ensureCard(driver: string): Card {
  let card = cards.get(driver);
  if (card) return card;
  const root = document.createElement('article');
  root.className = 'hcss-card hcss-stack dash-runner';
  root.innerHTML = `<header class="hcss-cluster dash-runner-head"></header>
    <div class="dash-speed" aria-label="Link speed">
      <div class="dash-speed-figure"><span class="dash-speed-value">0</span><span class="dash-speed-unit">Mbps</span></div>
      <div class="dash-speed-detail"><span class="dash-speed-dir" data-dir="rx">↓ 0</span><span class="dash-speed-dir" data-dir="tx">↑ 0</span><span class="dash-speed-iface dash-muted"></span></div>
      <div class="dash-spark" aria-hidden="true"></div>
    </div>
    <div class="dash-runner-body hcss-stack"></div>
    <figure class="dash-chart-figure"><figcaption class="dash-muted">Each arm against the control, by cell, over the blocks so far (below 1 is faster)</figcaption><div class="dash-chart"></div></figure>`;
  root.dataset.driver = driver;
  // Solid to the ink orbit behind the page; neighbouring cards turn it opposite ways.
  root.setAttribute('data-wt-obstacle', '');
  root.dataset.wtOrbit = cards.size % 2 ? 'ccw' : 'cw';
  root.style.order = String(DRIVER_ORDER.includes(driver) ? DRIVER_ORDER.indexOf(driver) : 99);
  $('runners').append(root);
  card = { root, body: root.querySelector('.dash-runner-body')!, speed: root.querySelector('.dash-speed')!, spark: new SpeedChart(root.querySelector('.dash-spark')!), chart: null, chartHost: root.querySelector('.dash-chart')!, chartKey: '', shown: 0 };
  cards.set(driver, card);
  return card;
}

function renderRunner(message: RunnerMessage): void {
  const card = ensureCard(message.driver);
  const [label, status] = stateBadge(message);
  const link = message.snapshot?.current?.plan.link;
  const title = DRIVER_TITLES[message.driver] || message.links.map((l) => LINK_NAMES[l] || l).join(', ');
  const via = message.route && message.route !== 'local' && message.route !== 'direct' ? ` · reached ${esc(message.route)}` : '';
  card.root.querySelector('header')!.innerHTML = `
    <div class="hcss-stack dash-tight"><p class="hcss-eyebrow">runner on ${esc(message.driver)}${via}</p>
    <h2>${esc(title)}</h2>${link ? `<p class="dash-muted">now on ${esc(LINK_NAMES[link] || link)}</p>` : ''}</div>
    <span class="hcss-badge dash-push" data-status="${status}">${esc(label)}</span>`;
  const snapshot = message.snapshot;
  const runner = snapshot?.runner;
  if (!message.ok || !snapshot || !runner) {
    card.body.innerHTML = `<div class="hcss-inline-alert" data-status="${message.ok ? 'warning' : 'danger'}"><p>${esc(message.ok ? 'No runner has run on this host.' : `Cannot reach ${message.driver}: ${message.error}`)}</p></div>`;
    card.chartHost.parentElement!.hidden = true;
    return;
  }
  const current = snapshot.current;
  const parts: string[] = [];
  if (current) {
    const plan = current.plan, run = current.status;
    const done = run?.samples_done ?? 0, planned = run?.samples_planned ?? plan.samples ?? 0;
    const started = new Date(current.started_utc).getTime() / 1000;
    const last = current.samples[current.samples.length - 1];
    // Estimate the finish from the pace up to the latest sample, so it holds still between
    // samples; the page counts down to it on its own (see tickClocks).
    const lastUtc = last?.utc ? new Date(last.utc).getTime() / 1000 : Date.now() / 1000;
    const finish = done > 3 && planned > done ? lastUtc + ((lastUtc - started) / done) * (planned - done) : NaN;
    parts.push(`
      <div class="hcss-stack dash-tight">
        <p class="dash-current"><strong>${esc(plan.experiment || runName(current.run))}</strong>
          <span class="hcss-badge" data-status="neutral">${esc(plan.kind || current.lane)}</span>
          ${current.lane === 'standing' ? '<span class="hcss-badge" data-status="info">sentinel</span>' : ''}</p>
        ${plan.hypothesis ? `<p class="dash-muted dash-hypothesis">${esc(plan.hypothesis)}</p>` : ''}
      </div>
      <progress class="hcss-progress" max="${planned || 1}" value="${done}" aria-label="Samples done">${done} of ${planned}</progress>
      <div class="hcss-stat-row dash-stats">
        <dl class="hcss-stat"><dt>Samples</dt><dd aria-label="${done} of ${planned} samples">${flipDigits(`${message.driver}:${current.run}`, done)} / ${planned}</dd></dl>
        <dl class="hcss-stat"><dt>Voided</dt><dd>${current.voided}</dd></dl>
        <dl class="hcss-stat"><dt>Running for</dt><dd class="dash-clock" data-since="${started}"></dd></dl>
        <dl class="hcss-stat"><dt>Left, about</dt><dd class="dash-clock" data-until="${isNaN(finish) ? '' : finish}" data-key="${esc(message.driver)}"></dd></dl>
      </div>
      <p class="dash-muted">Now: ${esc(run?.detail || run?.state || '—')}</p>`);
    if (current.samples.length) {
      const rows = current.samples.slice(-10).reverse().map((s) => `<tr>
        <td>${esc(clock(s.utc))}</td><td>${esc(cellLabel(s.cell))}</td><td>${esc(s.arm)}${s.control ? ' <span class="dash-muted">(control)</span>' : ''}</td>
        <td data-numeric>${esc(seconds(s.seconds))}</td><td data-numeric>${esc(rate(s.gbps))}</td>
        <td>${s.valid ? '<span class="hcss-badge" data-status="success">valid</span>' : `<span class="hcss-badge" data-status="danger" title="${esc(s.void)}">void</span>`}</td></tr>`).join('');
      parts.push(`<details class="hcss-disclosure" ${cards.size <= 2 ? 'open' : ''}><summary>Latest samples${last ? ` · last ${esc(ago(last.utc))}` : ''}</summary>
        <div class="hcss-table-scroll" role="region" tabindex="0" aria-label="Latest samples"><table class="hcss-table dash-table">
        <thead><tr><th>Time</th><th>Cell</th><th>Arm</th><th data-numeric>Time</th><th data-numeric>Rate</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody></table></div></details>`);
    }
  } else {
    parts.push(`<p class="dash-muted">${esc(runner.detail || (runner.state === 'idle' ? 'Nothing waiting.' : runner.state))}</p>`);
  }
  const backlog = snapshot.backlog, standing = snapshot.standing;
  const next = (backlog?.pending || []).slice(0, 6).map((p) => `<li><span>${esc(p.experiment || runName(p.run))}</span>
    <span class="dash-muted">${p.kind === 'job' ? 'maintenance' : `${p.samples ?? '?'} samples`}${p.hours ? ` · ${p.hours[0]}:00–${p.hours[1]}:00` : ''}</span></li>`).join('');
  const budgets = Object.keys({ ...runner.write_budget, ...runner.written_24h }).map((host) => {
    const used = runner.written_24h[host] || 0, allowance = runner.write_budget[host];
    return `<li><span>${esc(host)}</span><span class="dash-muted">${gib(used)} written in 24 h${allowance ? ` of ${gib(allowance)}` : ''}</span></li>`;
  }).join('');
  const recent = (runner.recent || []).slice(-5).reverse().map((r) => `<li><span>${esc(runName(r.run))}</span>
    <span class="hcss-badge" data-status="${r.state === 'complete' ? 'success' : r.state === 'failed' ? 'danger' : 'warning'}">${esc(r.state)}</span>
    <span class="dash-muted">${esc(r.detail || '')}</span></li>`).join('');
  parts.push(`<div class="hcss-grid dash-lists" style="--hcss-grid-min: 16rem">
    <section><h3>Up next <span class="dash-muted">· ${backlog?.pending_count ?? 0} waiting${standing?.pending_count ? `, ${standing.pending_count} sentinels` : ''}</span></h3><ol class="dash-list">${next || '<li class="dash-muted">nothing queued</li>'}</ol></section>
    <section><h3>Finished</h3><ul class="dash-list">${recent || '<li class="dash-muted">none since the runner started</li>'}</ul></section>
    ${budgets ? `<section><h3>Drive writes</h3><ul class="dash-list">${budgets}</ul></section>` : ''}
  </div>`);
  card.body.innerHTML = parts.join('');
  tickClocks(card.body);

  // The chart: one row per cell and arm, the running ratio to the control.
  const rows: ForestRow[] = [];
  for (const cell of current?.progress || [])
    for (const [arm, value] of Object.entries(cell.arms))
      if (value.ratio != null) rows.push({ label: `${cellLabel(cell.cell)} · ${arm}`, ratio: value.ratio, lo: null, hi: null, status: 'neutral', n: value.pairs });
  const figure = card.chartHost.parentElement!;
  figure.hidden = rows.length === 0;
  if (rows.length) {
    if (!card.chart) card.chart = new ForestChart(card.chartHost);
    card.chart.update(rows);
  }
}

// --- live link speed ----------------------------------------------------------------
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
const mbps = (bits: number) => bits / 1e6;
const formatMbps = (value: number) => Math.round(value).toLocaleString();

function renderSpeed(driver: string): void {
  const card = cards.get(driver);
  const interfaces = live.state.speed[driver];
  if (!card || !interfaces) return;
  // Show the busiest interface over the last ten seconds; ties go to the first.
  const busy = (series: [number, number, number][]) => series.slice(-10).reduce((sum, [, rx, tx]) => sum + rx + tx, 0);
  const [iface, series] = Object.entries(interfaces).sort((a, b) => busy(b[1]) - busy(a[1]))[0];
  const [, rx, tx] = series[series.length - 1];
  const target = mbps(Math.max(rx, tx));
  card.speed.dataset.active = String(target > 5);
  card.speed.querySelector<HTMLElement>('[data-dir="rx"]')!.textContent = `↓ ${formatMbps(mbps(rx))}`;
  card.speed.querySelector<HTMLElement>('[data-dir="tx"]')!.textContent = `↑ ${formatMbps(mbps(tx))}`;
  // The interface and what it is linked at now, e.g. "en13 · 2.5 GbE".
  const linked = live.state.link?.[driver]?.[iface];
  card.speed.querySelector<HTMLElement>('.dash-speed-iface')!.textContent =
    linked ? `${iface} · ${linked >= 1000 ? `${linked / 1000} GbE` : `${linked} Mb/s`}` : iface;
  card.speed.setAttribute('aria-label', `Link speed on ${iface}: ${formatMbps(target)} Mbps`);
  // The last 90 seconds on an axis fixed by the link's own speed (1 or 10 Gb/s).
  card.spark.update(series, live.state.link?.[driver]?.[iface]);
  // Count the big number toward the new value over most of a second.
  const value = card.speed.querySelector<HTMLElement>('.dash-speed-value')!;
  const from = card.shown, start = performance.now();
  if (reduceMotion.matches) { card.shown = target; value.textContent = formatMbps(target); return; }
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / 800), eased = 1 - (1 - t) ** 3;
    card.shown = from + (target - from) * eased;
    value.textContent = formatMbps(card.shown);
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function renderHosts(state: State): void {
  const chips = Object.values(state.hosts).sort((a, b) => a.host.localeCompare(b.host)).map((h: HostMessage) => {
    const used = h.disk_total && h.disk_free != null ? 1 - h.disk_free / h.disk_total : null;
    const load = h.load?.[0];
    const busy = load != null && h.cpus ? load / h.cpus : null;
    return `<div class="hcss-card dash-host" data-ok="${h.ok}">
      <p class="hcss-eyebrow">${esc(h.host)}</p>
      ${h.ok ? `<p><span title="1-minute load per core">load ${load?.toFixed(1)}</span> <span class="dash-muted">/ ${h.cpus}</span></p>
      <p class="dash-muted">${gib(h.disk_free)} free${used != null ? ` · ${(used * 100).toFixed(0)}% used` : ''}</p>
      <span class="dash-meter" style="--dash-fill:${((busy ?? 0) * 100).toFixed(0)}%" aria-hidden="true"></span>`
        : `<p><span class="hcss-badge" data-status="danger">unreachable</span></p>`}
    </div>`;
  });
  for (const message of Object.values(state.runners)) {
    const health = message.snapshot?.health;
    if (!health) continue;
    chips.unshift(`<div class="hcss-card dash-host" data-ok="true"><p class="hcss-eyebrow">${esc(message.driver)} <span class="dash-muted">driver</span></p>
      <p>load ${health.load?.[0]?.toFixed(1) ?? '—'} <span class="dash-muted">/ ${health.cpus}</span></p>
      <p class="dash-muted">${gib(health.disk_free)} free</p>
      <span class="dash-meter" style="--dash-fill:${(((health.load?.[0] ?? 0) / (health.cpus || 1)) * 100).toFixed(0)}%" aria-hidden="true"></span></div>`);
  }
  $('hosts').innerHTML = chips.join('');
}

// --- events -----------------------------------------------------------------------
const EVENT_STATUS: Record<string, string> = { finished: 'success', started: 'info', warning: 'warning', danger: 'danger', unreachable: 'danger', reachable: 'success', state: 'neutral', results: 'info' };
function renderEvents(state: State): void {
  $('events').innerHTML = state.events.slice(0, 150).map((e: DashEvent) => `<li>
    <span class="dash-muted">${esc(clock(e.utc))}</span>
    <span class="hcss-badge" data-status="${EVENT_STATUS[e.kind] || 'neutral'}">${esc(e.kind)}</span>
    ${e.driver ? `<strong>${esc(e.driver)}</strong>` : ''} <span>${esc(e.text)}</span></li>`).join('') || '<li class="dash-muted">No events yet. They appear as runs start, finish or fail.</li>';
}
live.onEvent((e) => {
  if (['finished', 'warning', 'danger', 'unreachable'].includes(e.kind)) toasts.enqueue(`${e.driver ? `${e.driver}: ` : ''}${e.text}`);
});

// --- results ----------------------------------------------------------------------
let selected: { group: string; name: string } | null = null;
let resultChart: ForestChart | null = null;
function renderResults(): void {
  const filter = ($<HTMLInputElement>('results-filter').value || '').toLowerCase();
  const group = $<HTMLSelectElement>('results-group').value;
  const groups = [...new Set(live.state.results.map((e) => e.group))].sort();
  const groupSelect = $<HTMLSelectElement>('results-group');
  if (groupSelect.options.length - 1 !== groups.length)
    groupSelect.innerHTML = `<option value="">All links</option>${groups.map((g) => `<option value="${esc(g)}">${esc(g)}</option>`).join('')}`;
  groupSelect.value = group;
  const list = live.state.results
    .filter((e) => (!group || e.group === group) && (!filter || e.experiment.toLowerCase().includes(filter)))
    .sort((a, b) => b.mtime - a.mtime);
  $('experiments').innerHTML = list.map((e: ExperimentIndex) => {
    const counts = Object.entries(e.verdicts).map(([v, n]) => `<span class="hcss-badge" data-status="${VERDICT_STATUS[v] || 'neutral'}">${n} ${esc(v)}</span>`).join('');
    const current = selected?.group === e.group && selected?.name === e.experiment;
    return `<li><button class="hcss-button dash-exp" data-variant="ghost" type="button" data-group="${esc(e.group)}" data-name="${esc(e.experiment)}" ${current ? 'aria-current="true"' : ''}>
      <span class="dash-exp-name">${esc(e.experiment)}</span><span class="dash-muted">${esc(e.group)} · ${esc(e.kind)} · ${e.comparisons} comparisons</span>
      <span class="hcss-cluster dash-tight">${counts}</span></button></li>`;
  }).join('') || '<li class="dash-muted">No analysed experiments match.</li>';
}
$('results-filter').addEventListener('input', renderResults);
$('results-group').addEventListener('change', renderResults);
$('experiments').addEventListener('click', async (event) => {
  const button = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-name]');
  if (!button) return;
  selected = { group: button.dataset.group!, name: button.dataset.name! };
  renderResults();
  const host = $('experiment');
  host.setAttribute('aria-busy', 'true');
  const response = await fetch(`/api/experiment?group=${encodeURIComponent(selected.group)}&name=${encodeURIComponent(selected.name)}`);
  host.removeAttribute('aria-busy');
  if (!response.ok) { host.innerHTML = `<div class="hcss-inline-alert" data-status="danger"><p>Could not load ${esc(selected.name)}.</p></div>`; return; }
  renderExperiment(await response.json());
});

function renderExperiment(detail: ExperimentDetail): void {
  resultChart?.destroy();
  resultChart = null;
  const host = $('experiment');
  const primary = detail.effects.filter((e) => e.primary);
  const metric = primary[0]?.metric || 'durable_s';
  const absolute = new Map(detail.absolutes.filter((a) => a.metric === metric).map((a) => [`${a.cell_id}|${a.arm}`, a]));
  const rows = primary.map((e: Effect) => {
    const mine = absolute.get(`${e.cell_id}|${e.arm}`), control = absolute.get(`${e.cell_id}|${e.control}`);
    return `<tr><td>${esc(cellLabel(e.cell_id))}</td><td>${esc(e.arm)}</td>
      <td data-numeric>${seconds(control?.geomean)}</td><td data-numeric>${seconds(mine?.geomean)}</td>
      <td data-numeric>${e.ratio.toFixed(3)} <span class="dash-muted">[${e.lo.toFixed(3)}, ${e.hi.toFixed(3)}]</span></td>
      <td data-numeric>${e.n_blocks}</td>
      <td><span class="hcss-badge" data-status="${VERDICT_STATUS[e.verdict] || 'neutral'}">${esc(e.verdict)}</span></td></tr>`;
  }).join('');
  host.innerHTML = `<header class="hcss-stack dash-tight"><p class="hcss-eyebrow">${esc(detail.group)} · ${esc(primary[0]?.kind || '')} · ${esc(metric)}</p><h2>${esc(detail.name)}</h2></header>
    <figure class="dash-chart-figure"><figcaption class="dash-muted">Ratio to the control with its 95% interval; below 1 is faster</figcaption><div class="dash-chart dash-chart-tall"></div></figure>
    <div class="hcss-table-scroll" role="region" tabindex="0" aria-label="Comparisons"><table class="hcss-table dash-table">
      <thead><tr><th>Cell</th><th>Arm</th><th data-numeric>Control</th><th data-numeric>Arm</th><th data-numeric>Ratio [95%]</th><th data-numeric>Blocks</th><th>Verdict</th></tr></thead>
      <tbody>${rows}</tbody></table></div>
    ${detail.report ? `<details class="hcss-disclosure"><summary>Full report</summary><pre class="dash-report">${esc(detail.report)}</pre></details>` : ''}`;
  const chartHost = host.querySelector<HTMLElement>('.dash-chart')!;
  chartHost.style.setProperty('--dash-rows', String(Math.max(4, primary.length)));
  resultChart = new ForestChart(chartHost);
  resultChart.update(primary.map((e) => ({ label: `${cellLabel(e.cell_id)} · ${e.arm}`, ratio: e.ratio, lo: e.lo, hi: e.hi, status: VERDICT_STATUS[e.verdict] || 'neutral', n: e.n_blocks })));
}

// --- wiring -----------------------------------------------------------------------
live.onChange((state, changed) => {
  if (changed.kind === 'all') {
    for (const message of Object.values(state.runners)) renderRunner(message);
    renderHosts(state);
    renderEvents(state);
    renderResults();
    renderRunList(state.runs);
    if (!$('view-tengig').hidden) void renderTenGig(state.runs);
  } else if (changed.kind === 'runner' && changed.key) {
    renderRunner(state.runners[changed.key]);
    renderHosts(state);
  } else if (changed.kind === 'host') renderHosts(state);
  else if (changed.kind === 'speed' && changed.key) renderSpeed(changed.key);
  else if (changed.kind === 'event') renderEvents(state);
  else if (changed.kind === 'results') renderResults();
  else if (changed.kind === 'runs') {
    runsUpdated(state.runs);
    if (!$('view-tengig').hidden) void renderTenGig(state.runs);
  }
});
showView();
live.connect();
void startInk($('stage'));
