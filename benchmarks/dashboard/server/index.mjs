// The dashboard's server: runs collector.py, keeps the latest state of every
// runner and host, and pushes it to browsers over a WebSocket. Also serves
// analysed results from benchmarks/results and, after `npm run build`, the page.
// Listens on 127.0.0.1 only: it reads private hosts' state.
import { spawn } from 'node:child_process';
import { createHmac } from 'node:crypto';
import { homedir } from 'node:os';
import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { createInterface } from 'node:readline';
import { dirname, extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';

const HERE = dirname(fileURLToPath(import.meta.url));
const DASHBOARD = resolve(HERE, '..');
const RESULTS = resolve(DASHBOARD, '..', 'results');
const DIST = join(DASHBOARD, 'dist');
const PORT = Number(process.env.XSDASH_PORT || 8787);
const INTERVAL = process.env.XSDASH_INTERVAL || '5';

const state = { config: null, runners: {}, hosts: {}, results: [], events: [], speed: {}, started: Date.now() / 1000 };
const SPEED_HISTORY = 90; // seconds of per-interface rates kept for the sparklines
const MAX_EVENTS = 200;

function event(kind, driver, text, extra = {}) {
  const entry = { utc: Date.now() / 1000, kind, driver, text, ...extra };
  state.events.unshift(entry);
  state.events.length = Math.min(state.events.length, MAX_EVENTS);
  broadcast({ type: 'event', event: entry });
}

// Notice what changed between two snapshots of one runner, as events.
function compare(driver, before, after) {
  const was = before?.snapshot?.runner, now = after?.snapshot?.runner;
  if (before && before.ok !== after.ok) event(after.ok ? 'reachable' : 'unreachable', driver, after.ok ? 'reachable again' : `unreachable: ${after.error}`);
  if (!was || !now) return;
  if (was.state !== now.state && ['halted', 'paused', 'stopped', 'idle'].includes(now.state))
    event(now.state === 'halted' ? 'danger' : 'state', driver, `runner ${now.state}${now.detail ? `: ${now.detail}` : ''}`);
  const seen = new Set((was.recent || []).map((r) => r.run + r.finished_utc));
  for (const done of now.recent || []) {
    if (seen.has(done.run + done.finished_utc)) continue;
    const bad = done.state !== 'complete';
    event(bad ? 'warning' : 'finished', driver, `${done.run.slice(17)} ${done.state}${done.detail ? `: ${done.detail}` : ''}`, { run: done.run });
  }
  if (now.current?.run && now.current.run !== was.current?.run) event('started', driver, `started ${now.current.run.slice(17)} (${now.current.lane})`, { run: now.current.run });
}

function apply(message) {
  if (message.type === 'config') state.config = message;
  else if (message.type === 'runner') {
    const before = state.runners[message.driver];
    state.runners[message.driver] = message;
    compare(message.driver, before, message);
  } else if (message.type === 'host') state.hosts[message.host] = message;
  else if (message.type === 'speed') {
    const driver = (state.speed[message.driver] ??= {});
    const series = (driver[message.iface] ??= []);
    series.push([message.utc, message.rx_bps, message.tx_bps]);
    if (series.length > SPEED_HISTORY) series.splice(0, series.length - SPEED_HISTORY);
  }
  else if (message.type === 'results') {
    if (state.results.length && message.experiments.length > state.results.length)
      event('results', null, `${message.experiments.length - state.results.length} new analysed experiment(s)`);
    state.results = message.experiments;
  }
  broadcast({ type: 'update', message });
}

let collector;
function startCollector() {
  collector = spawn('python3', [join(DASHBOARD, 'collector.py'), '--interval', INTERVAL], { stdio: ['ignore', 'pipe', 'inherit'] });
  createInterface({ input: collector.stdout }).on('line', (line) => {
    try { apply(JSON.parse(line)); } catch (error) { console.error('bad collector line', error.message); }
  });
  collector.on('exit', (code) => {
    console.error(`collector exited ${code}; restarting in 5 s`);
    event('danger', null, `collector exited ${code}; restarting`);
    setTimeout(startCollector, 5000);
  });
}

// --- WebSocket --------------------------------------------------------------
const sockets = new Set();
function broadcast(payload) {
  const text = JSON.stringify(payload);
  for (const socket of sockets) if (socket.readyState === 1) socket.send(text);
  relay?.queue(payload);
}

// --- the relay: push-only copy of everything to dashboard.mk7s.dev -------------------
// Configured by ~/.config/xsdash/relay.json, {"url": "https://dashboard.mk7s.dev", "secret": "..."},
// kept outside the repository. Nothing on the relay can call back into this machine.
// What leaves this machine is scrubbed first: no usernames or home paths, no addresses,
// no SSH routes or error text, no process ids or host roots. Numbers and names stay.
const DROP = new Set(['route', 'root', 'pid', 'runner_path']);
function scrubText(text) {
  return text
    .replace(/\/(?:Users|home)\/[^/\s"'`]+/g, '~')
    .replace(/\b[\w.+-]+@[\w.-]+\b/g, '[host]')
    .replace(/\b\d{1,3}(?:\.\d{1,3}){3}\b/g, '[address]')
    .replace(/\bfe80:[0-9a-f:%\w]*/gi, '[address]');
}
function scrub(value, key) {
  if (typeof value === 'string') {
    if (key === 'runner' || key === 'error') return key === 'error' ? 'unreachable' : undefined;
    return scrubText(value);
  }
  if (Array.isArray(value)) return value.map((item) => scrub(item));
  if (value && typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      if (DROP.has(k)) continue;
      const cleaned = scrub(v, k);
      if (cleaned !== undefined) out[k] = cleaned;
    }
    return out;
  }
  return value;
}

const RELAY_FILE = process.env.XSDASH_RELAY_FILE || join(homedir(), '.config', 'xsdash', 'relay.json');
const relay = (() => {
  let settings;
  try { settings = JSON.parse(readFileSync(RELAY_FILE, 'utf8')); } catch { return null; }
  if (!settings.url || !settings.secret) return null;
  const endpoint = new URL('/ingest', settings.url).toString();
  let pending = [], failures = 0, lastFull = 0;
  const pushed = new Map(); // experiment key -> mtime pushed
  async function post(messages) {
    const body = JSON.stringify({ sent: Date.now(), messages: scrub(messages) });
    const stamp = String(Date.now());
    const signature = createHmac('sha256', settings.secret).update(`${stamp}.${body}`).digest('hex');
    const response = await fetch(endpoint, { method: 'POST', body, headers: { 'content-type': 'application/json', 'x-timestamp': stamp, 'x-signature': signature } });
    if (!response.ok) throw new Error(`${response.status} ${await response.text()}`.slice(0, 200));
  }
  async function flush() {
    const now = Date.now();
    let messages = pending;
    pending = [];
    // A full snapshot every five minutes, and after any failure, so a fresh relay catches up.
    if (now - lastFull > 300_000 || failures) messages = [{ type: 'state', state }, ...messages.filter((m) => m.type === 'event')];
    if (!messages.length) return;
    try {
      await post(messages);
      if (messages[0].type === 'state') lastFull = now;
      if (failures) console.log('relay: pushing again');
      failures = 0;
    } catch (error) {
      if (!failures++) console.error(`relay: push failed (${error.message}); retrying with a full snapshot`);
    }
  }
  async function pushResults() {
    for (const entry of state.results) {
      const key = `${entry.group}/${entry.experiment}`;
      if (pushed.get(key) === entry.mtime) continue;
      const detail = experiment(entry.group, entry.experiment);
      if (!detail) continue;
      const primary = detail.effects.filter((e) => e.primary);
      const metric = primary[0]?.metric;
      const trimmed = { ...detail, summary: null,
        effects: primary.map(({ cell_id, corpus, scenario, sender, receiver, arm, control, metric, primary, n_blocks, ratio, lo, hi, p, p_holm, verdict, kind }) =>
          ({ cell_id, corpus, scenario, sender, receiver, arm, control, metric, primary, n_blocks, ratio, lo, hi, p, p_holm, verdict, kind })),
        absolutes: detail.absolutes.filter((a) => a.metric === metric) };
      try { await post([{ type: 'experiment', key, detail: trimmed }]); pushed.set(key, entry.mtime); }
      catch (error) { console.error(`relay: could not push ${key}: ${error.message}`); return; }
    }
  }
  setInterval(flush, 3000);
  setInterval(pushResults, 60_000);
  setTimeout(pushResults, 10_000);
  console.log(`relay: pushing to ${endpoint}`);
  return { queue(payload) { if (pending.length < 2000) pending.push(payload); } };
})();

// --- HTTP: results and the built page --------------------------------------
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json',
  '.woff2': 'font/woff2', '.png': 'image/png', '.map': 'application/json' };

function readMaybe(path) {
  try { return JSON.parse(readFileSync(path, 'utf8')); } catch { return null; }
}

function experiment(group, name) {
  if (!/^[A-Za-z0-9_-]+$/.test(group) || !/^[A-Za-z0-9_.-]+$/.test(name)) return null;
  const directory = join(RESULTS, group, name);
  if (!existsSync(join(directory, 'analysis'))) return null;
  let report = null;
  try { report = readFileSync(join(directory, 'report.md'), 'utf8'); } catch {}
  return {
    group, name,
    effects: readMaybe(join(directory, 'analysis', 'effects.json')) || [],
    absolutes: readMaybe(join(directory, 'analysis', 'absolutes.json')) || [],
    summary: readMaybe(join(directory, 'analysis', 'summary.json')),
    report,
  };
}

const server = createServer((request, response) => {
  const url = new URL(request.url, 'http://localhost');
  if (url.pathname === '/api/state') return send(response, 200, state);
  if (url.pathname === '/api/experiment') {
    const found = experiment(url.searchParams.get('group') || '', url.searchParams.get('name') || '');
    return send(response, found ? 200 : 404, found || { error: 'no such analysed experiment' });
  }
  // The built page, if there is one; `npm run dev` serves it from Vite instead.
  const relative = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, '');
  let file = join(DIST, relative === '/' ? 'index.html' : relative);
  if (!file.startsWith(DIST) || !existsSync(file) || statSync(file).isDirectory()) file = join(DIST, 'index.html');
  if (!existsSync(file)) return send(response, 404, { error: 'not built: run `npm run build`, or use `npm run dev`' });
  response.writeHead(200, { 'content-type': TYPES[extname(file)] || 'application/octet-stream' });
  createReadStream(file).pipe(response);
});

function send(response, code, body) {
  response.writeHead(code, { 'content-type': 'application/json', 'cache-control': 'no-store' });
  response.end(JSON.stringify(body));
}

const wss = new WebSocketServer({ server, path: '/ws' });
wss.on('connection', (socket) => {
  sockets.add(socket);
  socket.send(JSON.stringify({ type: 'state', state }));
  socket.on('close', () => sockets.delete(socket));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`xs bench dashboard server on http://127.0.0.1:${PORT}`);
  startCollector();
});
process.on('SIGINT', () => { collector?.kill(); process.exit(0); });
process.on('SIGTERM', () => { collector?.kill(); process.exit(0); });
