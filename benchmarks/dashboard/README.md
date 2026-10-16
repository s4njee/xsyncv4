# xs bench dashboard

A live view of the benchmark runners: what each is running, its samples as they
land, a per-second link-speed readout, host load and disk, the queue, events,
and every analysed experiment's ratios and verdicts.

```sh
pnpm install
pnpm dev            # Vite on http://127.0.0.1:5174, with the feed server beside it
```

`collector.py` probes each runner's host over SSH (read-only: it reads the
files `runner.py` and `agent.py` write) and samples link interfaces once a
second. `server/index.mjs` keeps the latest state, serves it to browsers over a
WebSocket on 127.0.0.1:8787, and serves analysed results from
`benchmarks/results`. Nothing listens on anything but this machine's loopback.

## dashboard.mk7s.dev

`relay/` is a Cloudflare Worker with one Durable Object. The Mac's server
**pushes** to it (`POST /ingest`, HMAC-signed with a shared secret, timestamped
to refuse replays); browsers read from it. Nothing at Cloudflare can connect to
the Mac or to any lab host. Every browser request must carry a Cloudflare
Access login, which the Worker verifies itself as well, so a gap in the Access
configuration fails closed.

One-time setup:

1. `wrangler login`.
2. In Cloudflare Zero Trust, Access → Applications, add a self-hosted
   application for `dashboard.mk7s.dev` with an Allow policy for your email.
   Note the **team domain** (`TEAM.cloudflareaccess.com`) and the
   application's **audience (AUD) tag**, and put both in `relay/wrangler.jsonc`.
3. Add a second self-hosted application for `dashboard.mk7s.dev/ingest` with a
   **Bypass** policy for Everyone: the Mac signs its pushes instead.
4. `pnpm build`, then `cd relay && wrangler deploy`.
5. `relay/setup-secret.sh`: makes the shared secret, stores it in the Worker
   and in `~/.config/xsdash/relay.json` (mode 600, outside the repository).
6. Restart the Mac's server (`pnpm dev` or `pnpm start`); it logs
   `relay: pushing to https://dashboard.mk7s.dev/ingest`.

The relay keeps the latest state, about 90 s of link speed, and each analysed
experiment's ratios. Without `relay.json` the server pushes nothing.
