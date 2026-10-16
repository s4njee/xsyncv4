// Past runs for the Runs view: every run directory under benchmarks/results that has
// samples, read into a compact, public-safe form. Only measurements and the run's
// design leave this module: no argv, host state, output, paths or SSH routes.
// Samples are columnar (one array per field) to keep a run of a thousand samples small.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const NAME = /^[A-Za-z0-9_.-]+$/;
const cache = new Map(); // run directory -> { stamp, index, detail }

function readJson(path) {
  try { return JSON.parse(readFileSync(path, 'utf8')); } catch { return null; }
}

function dirs(path) {
  try { return readdirSync(path, { withFileTypes: true }).filter((d) => d.isDirectory() && NAME.test(d.name)).map((d) => d.name); }
  catch { return []; }
}

const seconds = (utc) => (utc ? Math.round(Date.parse(utc) / 10) / 100 : null);
const round = (value, places = 4) => (typeof value === 'number' && isFinite(value) ? Number(value.toFixed(places)) : null);
const cpu = (side) => (side ? round((side.user_seconds ?? 0) + (side.system_seconds ?? 0), 3) : null);

function load(root, group, experiment, run) {
  const directory = join(root, group, experiment, run);
  const samplesPath = join(directory, 'samples.jsonl');
  let stat;
  try { stat = statSync(samplesPath); } catch { return null; }
  const statusPath = join(directory, 'status.json');
  const stamp = `${stat.mtimeMs}:${stat.size}:${existsSync(statusPath) ? statSync(statusPath).mtimeMs : 0}`;
  const cached = cache.get(directory);
  if (cached?.stamp === stamp) return cached;

  const plan = readJson(join(directory, 'plan.json')) || readJson(join(directory, 'run.json'))?.plan || {};
  const status = readJson(statusPath) || {};
  const armIndex = new Map(), cellIndex = new Map();
  const arms = [], cells = [];
  for (const arm of plan.arms || []) { armIndex.set(arm.name, arms.length); arms.push({ name: arm.name, tool: arm.tool, flags: arm.flags || [] }); }
  for (const cell of plan.cells || []) {
    cellIndex.set(cell.id, cells.length);
    cells.push({ id: cell.id, corpus: cell.corpus, scenario: cell.scenario, sender: cell.sender, receiver: cell.receiver,
      client: cell.client, link: cell.link, cache: cell.cache, files: null, bytes: null });
  }
  const columns = { cell: [], arm: [], block: [], attempt: [], position: [], control: [], valid: [], void: [], utc: [],
    wall_s: [], sync_s: [], durable_s: [], client_cpu_s: [], peer_cpu_s: [], client_rss: [], peer_rss: [], wire_bytes: [], retransmits: [], rev: [] };
  const revs = [];
  let lines;
  try { lines = readFileSync(samplesPath, 'utf8').split('\n'); } catch { return null; }
  for (const line of lines) {
    if (!line) continue;
    let s;
    try { s = JSON.parse(line); } catch { continue; }
    if (!armIndex.has(s.arm)) { armIndex.set(s.arm, arms.length); arms.push({ name: s.arm, tool: s.tool, flags: s.flags || [] }); }
    if (!cellIndex.has(s.cell_id)) {
      cellIndex.set(s.cell_id, cells.length);
      cells.push({ id: s.cell_id, ...(s.cell || {}), files: null, bytes: null });
    }
    const cell = cells[cellIndex.get(s.cell_id)];
    cell.files ??= s.corpus_files ?? null;
    cell.bytes ??= s.corpus_bytes ?? null;
    if (s.rev && !revs.includes(s.rev)) revs.push(s.rev);
    columns.cell.push(cellIndex.get(s.cell_id));
    columns.arm.push(armIndex.get(s.arm));
    columns.block.push(s.block ?? null);
    columns.attempt.push(s.attempt ?? null);
    columns.position.push(s.position ?? null);
    columns.control.push(s.control ? 1 : 0);
    columns.valid.push(s.valid ? 1 : 0);
    // Void reasons are short codes from the agent; anything longer is cut, never shown whole.
    columns.void.push(s.valid ? null : String(s.void_reason || 'void').split(/[:\n]/)[0].slice(0, 48));
    columns.utc.push(seconds(s.utc_start));
    columns.wall_s.push(round(s.wall_s));
    columns.sync_s.push(round(s.sync_s));
    columns.durable_s.push(round(s.durable_s));
    columns.client_cpu_s.push(cpu(s.client));
    columns.peer_cpu_s.push(cpu(s.peer));
    columns.client_rss.push(s.client?.max_rss_bytes ?? null);
    columns.peer_rss.push(s.peer?.max_rss_bytes ?? null);
    // Bytes that crossed the link, from whichever end counts its interface (the Mac reports neither).
    columns.wire_bytes.push(s.wire?.sender_tx_bytes || s.wire?.receiver_rx_bytes || null);
    columns.retransmits.push(s.wire?.sender_retransmits ?? null);
    columns.rev.push(s.rev ? revs.indexOf(s.rev) : null);
  }
  const n = columns.cell.length;
  if (!n) return null;
  const utcs = columns.utc.filter((u) => u != null);
  const valid = columns.valid.reduce((a, b) => a + b, 0);
  const links = [...new Set(cells.map((c) => c.link).filter(Boolean))];
  // The speed the run's preflight required of its link: on the direct cable, 2500 while it
  // ran at about 3 Gb/s and 10000 once it reached 10 GbE, which is how the 10 GbE view picks runs.
  const floors = links.map((l) => plan.links?.[l]?.min_speed_mbps).filter((v) => typeof v === 'number');
  const index = {
    key: `${group}/${experiment}/${run}`, group, experiment, run,
    kind: plan.kind ?? null, hypothesis: plan.hypothesis ?? null, primary: plan.primary ?? 'wall_s', control: plan.control ?? null,
    driver: plan.driver ?? null, links, link_mbps: floors.length ? Math.max(...floors) : null,
    started: utcs.length ? Math.min(...utcs) : null, ended: utcs.length ? Math.max(...utcs) : null,
    samples: n, valid, voided: n - valid,
    planned: status.samples_planned ?? null, state: status.state ?? null,
    arms: arms.map((a) => a.name), corpora: [...new Set(cells.map((c) => c.corpus))], cells: cells.length,
  };
  const detail = { ...index, delta: plan.delta ?? null, arms, cells, revs, columns };
  const entry = { stamp, index, detail };
  cache.set(directory, entry);
  return entry;
}

function* runDirectories(root) {
  for (const group of dirs(root))
    for (const experiment of dirs(join(root, group)))
      for (const run of dirs(join(root, group, experiment)))
        if (/^\d{8}T\d{6}Z/.test(run)) yield [group, experiment, run];
}

// Newest first, by when each run actually began (a queued run can start hours after its id).
export function runsIndex(root) {
  const runs = [];
  for (const [group, experiment, run] of runDirectories(root)) {
    const entry = load(root, group, experiment, run);
    if (entry) runs.push({ ...entry.index, stamp: entry.stamp });
  }
  return runs.sort((a, b) => (b.started ?? 0) - (a.started ?? 0) || b.run.localeCompare(a.run));
}

export function runDetail(root, key) {
  const parts = String(key || '').split('/');
  if (parts.length !== 3 || !parts.every((p) => NAME.test(p))) return null;
  return load(root, ...parts)?.detail ?? null;
}
