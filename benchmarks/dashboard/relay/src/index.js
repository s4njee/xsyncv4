// xs bench dashboard relay, at dashboard.mk7s.dev.
//
// The Mac's dashboard server pushes state to POST /ingest, signed with a shared
// secret; nothing here can reach the Mac or any lab host. Browsers get the built
// page and a WebSocket fed from one Durable Object, and only with a valid
// Cloudflare Access login, which this Worker verifies itself as well: if Access
// is not configured, every browser request is refused.

const MAX_BODY = 4 << 20;          // bytes accepted per push
const MAX_SKEW_MS = 120_000;       // a signed push older or newer than this is refused
const SPEED_HISTORY = 90;
const MAX_VIEWERS = 200;           // open WebSockets at once; more are turned away
const RUN_KEY = /^[A-Za-z0-9_-]+\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/ingest') return ingest(request, env);
    // PUBLIC_READ makes the page and its feed readable by anyone; pushes stay signed either way.
    if (env.PUBLIC_READ !== 'true') {
      const denied = await checkAccess(request, env);
      if (denied) return denied;
    } else if (!['GET', 'HEAD'].includes(request.method)) return text(405, 'read-only');
    if (url.pathname === '/ws' || url.pathname.startsWith('/api/')) {
      const hub = env.HUB.get(env.HUB.idFromName('lab'));
      return hub.fetch(request);
    }
    const response = await env.ASSETS.fetch(request);
    return secure(response);
  },
};

// --- the Mac's pushes --------------------------------------------------------------

async function ingest(request, env) {
  if (request.method !== 'POST') return text(405, 'POST only');
  if (!env.INGEST_SECRET) return text(503, 'ingest secret not configured');
  const length = Number(request.headers.get('content-length') || 0);
  if (length > MAX_BODY) return text(413, 'too large');
  const stamp = request.headers.get('x-timestamp') || '';
  const signature = request.headers.get('x-signature') || '';
  if (!/^\d{13}$/.test(stamp) || Math.abs(Date.now() - Number(stamp)) > MAX_SKEW_MS) return text(401, 'stale');
  const body = await request.text();
  if (body.length > MAX_BODY) return text(413, 'too large');
  const expected = await hmac(env.INGEST_SECRET, `${stamp}.${body}`);
  if (!timingSafeEqual(expected, signature)) return text(401, 'bad signature');
  const hub = env.HUB.get(env.HUB.idFromName('lab'));
  return hub.fetch('https://hub/ingest', { method: 'POST', body });
}

async function hmac(secret, message) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
  return [...new Uint8Array(signature)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function timingSafeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let difference = 0;
  for (let i = 0; i < a.length; i++) difference |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return difference === 0;
}

// --- Cloudflare Access, checked here as well as at the edge ------------------------

let jwks = { keys: null, fetched: 0 };

async function checkAccess(request, env) {
  if (!env.ACCESS_TEAM_DOMAIN || !env.ACCESS_AUD) return text(503, 'Access is not configured for this dashboard.');
  const token = request.headers.get('cf-access-jwt-assertion') || cookie(request, 'CF_Authorization');
  if (!token) return text(403, 'Sign in through Cloudflare Access.');
  try {
    const claims = await verifyJwt(token, env);
    const audience = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
    if (!audience.includes(env.ACCESS_AUD)) throw new Error('audience');
    if (claims.iss !== `https://${env.ACCESS_TEAM_DOMAIN}`) throw new Error('issuer');
    if (!claims.exp || claims.exp * 1000 < Date.now()) throw new Error('expired');
    return null;
  } catch {
    return text(403, 'Sign in through Cloudflare Access.');
  }
}

function cookie(request, name) {
  const header = request.headers.get('cookie') || '';
  const match = header.split(/;\s*/).find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

function base64url(input) {
  const padded = input.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((input.length + 3) % 4);
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

async function verifyJwt(token, env) {
  const [headerPart, payloadPart, signaturePart] = token.split('.');
  if (!signaturePart) throw new Error('malformed');
  const header = JSON.parse(new TextDecoder().decode(base64url(headerPart)));
  if (header.alg !== 'RS256') throw new Error('algorithm');
  if (!jwks.keys || Date.now() - jwks.fetched > 3_600_000) {
    const response = await fetch(`https://${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`);
    jwks = { keys: (await response.json()).keys, fetched: Date.now() };
  }
  const jwk = jwks.keys.find((key) => key.kid === header.kid);
  if (!jwk) throw new Error('unknown key');
  const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
  const valid = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, base64url(signaturePart),
    new TextEncoder().encode(`${headerPart}.${payloadPart}`));
  if (!valid) throw new Error('signature');
  return JSON.parse(new TextDecoder().decode(base64url(payloadPart)));
}

function text(status, body) {
  return secure(new Response(body, { status, headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store' } }));
}

function secure(response) {
  const headers = new Headers(response.headers);
  headers.set('x-content-type-options', 'nosniff');
  headers.set('referrer-policy', 'no-referrer');
  headers.set('x-frame-options', 'DENY');
  headers.set('content-security-policy',
    "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
    + "font-src 'self' data: blob:; connect-src 'self' wss: data: blob:; worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers, webSocket: response.webSocket });
}

// --- the hub: latest state, fanned out to browsers ---------------------------------

export class Hub {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
    this.state = null;
    this.ready = ctx.blockConcurrencyWhile(async () => {
      this.state = (await ctx.storage.get('state')) || { config: null, runners: {}, hosts: {}, results: [], runs: [], events: [], speed: {}, link: {}, started: Date.now() / 1000 };
    });
    this.dirty = false;
  }

  async fetch(request) {
    await this.ready;
    const url = new URL(request.url);
    if (url.pathname === '/ingest') return this.ingest(await request.text());
    if (url.pathname === '/ws') {
      if (request.headers.get('upgrade') !== 'websocket') return new Response('expected a WebSocket', { status: 426 });
      if (this.ctx.getWebSockets().length >= MAX_VIEWERS) return new Response('too many viewers', { status: 503 });
      const [client, server] = Object.values(new WebSocketPair());
      this.ctx.acceptWebSocket(server);
      server.send(JSON.stringify({ type: 'state', state: this.state }));
      return new Response(null, { status: 101, webSocket: client });
    }
    if (url.pathname === '/api/state') return json(200, this.state);
    if (url.pathname === '/api/run') {
      const key = url.searchParams.get('key') || '';
      const detail = RUN_KEY.test(key) ? await this.ctx.storage.get(`run:${key}`) : null;
      return detail ? json(200, detail) : json(404, { error: 'no such run' });
    }
    if (url.pathname === '/api/experiment') {
      const key = `experiment:${url.searchParams.get('group')}/${url.searchParams.get('name')}`;
      const detail = await this.ctx.storage.get(key);
      return detail ? json(200, detail) : json(404, { error: 'no such analysed experiment' });
    }
    return new Response('not found', { status: 404 });
  }

  // Browsers only listen; one that sends anything is disconnected.
  webSocketMessage(ws) { try { ws.close(1008, 'read-only'); } catch {} }
  webSocketClose(ws) { try { ws.close(); } catch {} }

  async ingest(body) {
    let batch;
    try { batch = JSON.parse(body); } catch { return new Response('bad json', { status: 400 }); }
    const outgoing = [];
    for (const payload of batch.messages || []) {
      if (payload.type === 'state') {
        this.state = { ...payload.state, speed: payload.state.speed || this.state.speed || {}, link: payload.state.link || this.state.link || {} };
        outgoing.push(payload);
      } else if (payload.type === 'update') {
        this.apply(payload.message);
        outgoing.push(payload);
      } else if (payload.type === 'event') {
        this.state.events.unshift(payload.event);
        this.state.events.length = Math.min(this.state.events.length, 200);
        outgoing.push(payload);
      } else if (payload.type === 'experiment' && typeof payload.key === 'string' && /^[A-Za-z0-9_-]+\/[A-Za-z0-9_.-]+$/.test(payload.key)) {
        await this.ctx.storage.put(`experiment:${payload.key}`, payload.detail);
      } else if (payload.type === 'run' && typeof payload.key === 'string' && RUN_KEY.test(payload.key)) {
        await this.ctx.storage.put(`run:${payload.key}`, payload.detail);
      }
    }
    const sockets = this.ctx.getWebSockets();
    for (const payload of outgoing) {
      const text = JSON.stringify(payload);
      for (const socket of sockets) {
        try { socket.send(text); } catch {}
      }
    }
    // Keep a copy for a fresh Durable Object, at most every half minute.
    if (!this.dirty) {
      this.dirty = true;
      await this.ctx.storage.setAlarm(Date.now() + 30_000);
    }
    return new Response('ok');
  }

  apply(message) {
    const state = this.state;
    if (message.type === 'config') state.config = message;
    else if (message.type === 'runner') state.runners[message.driver] = message;
    else if (message.type === 'host') state.hosts[message.host] = message;
    else if (message.type === 'results') state.results = message.experiments;
    else if (message.type === 'runs') state.runs = message.runs;
    else if (message.type === 'speed') {
      const driver = (state.speed[message.driver] ??= {});
      const series = (driver[message.iface] ??= []);
      series.push([message.utc, message.rx_bps, message.tx_bps]);
      if (series.length > SPEED_HISTORY) series.splice(0, series.length - SPEED_HISTORY);
      if (message.link_mbps) ((state.link ??= {})[message.driver] ??= {})[message.iface] = message.link_mbps;
    }
  }

  async alarm() {
    this.dirty = false;
    await this.ctx.storage.put('state', this.state);
  }
}

function json(status, body) {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
}
