# Benchmark site backlog — from the xs bench dashboard to a reusable benchmark dashboard

Audit date: 2026-10-16. Based on the dashboard as deployed at dashboard.mk7s.dev
(`benchmarks/dashboard/`), the lab harness it reads (`benchmarks/lab/`), and what
went wrong or had to be hand-built while running it this week. This is a separate
product backlog: experiment work stays in `experiments.md`, engine work in
`backlog.md`.

## Target and scope

Today the site is a dashboard for one lab: xs against rsync on a handful of named
hosts, fed by one harness. The goal is a benchmark dashboard that another project
can adopt with a configuration file and an adapter for its own results, without
editing the page's code, and that is safe to publish by default.

Another project should be able to:

- show its runners or jobs live, with whatever live metrics it collects;
- browse every past run, with each run's raw samples, and download them;
- publish analysed results and report pages (charts with commentary) built from its own data;
- put the whole thing on the public web with nothing private leaving its machines,
  and keep every machine unreachable from the site.

Out of scope for now: running or controlling benchmarks from the site (it stays
read-only), hosting for third parties, and a statistics engine of its own (the site
displays what the harness's analysis produces).

## Foundation already available

Extend these; do not rebuild them.

| Capability | Where | Gap for reuse |
|---|---|---|
| Live runner cards: state, current run, progress, clocks, queue, write budgets | `src/main.ts` `renderRunner` | Runner fields are this harness's (`runner.py` status, `plan.json`) |
| Live link speed per interface, axis following the link | `collector.py` `watch_speed`, `src/charts.ts` `SpeedChart` | Interfaces come from `hosts.toml`; only network rates, no other live metrics |
| Past runs: index, compact columnar samples, filters, per-arm spread, timeline, medians against control, CSV/JSON export, links to a run | `server/runs.mjs`, `src/runs.ts` | Columns and metrics are xs/rsync sample fields; reads one results directory layout |
| Analysed results: forest of ratios with verdicts | `src/main.ts` results view, `src/charts.ts` `ForestChart` | Reads `analysis/effects.json` as `analyze.py` writes it |
| A report page with commentary and live charts | `src/tengig.ts`, `index.html` `#view-tengig` | Hand-written TypeScript and HTML for one question |
| Public, read-only site: push-only HMAC ingest, Durable Object fan-out, hibernating WebSockets, scrubbing on the lab side, CSP | `relay/src/index.js`, `server/index.mjs` `scrub()` | One dashboard per Worker; scrubbing is pattern-based, not an allowlist |
| Charts: HoloChart (WebGL) themed from HoloCSS, transitions, main-thread text for CSP | `src/charts.ts`, `src/text.ts` | Reaches into HoloChart's renderer through a Vite alias (`vite.config.ts`) |
| Look: HoloCSS tokens, boxy theme, dark default, ink-orbit background, reduced-motion support | `src/style.css`, `src/ink.ts` | Lab colours and the ink effect are baked in |

## Lessons from running it this week

Each of these cost time and points at a story below.

1. **Labels and structure are hard-coded.** Driver order, card titles and link names
   live in `src/main.ts` (`DRIVER_ORDER`, `DRIVER_TITLES`, `LINK_NAMES`). Moving the
   Mac–mars cable from 10 GbE to 2.5 GbE needed a code change and a deploy (BS-01).
2. **Results reached the site only after a manual collect.** Runs on the Mac's runner
   sat outside `benchmarks/results/` until `plan.py collect`, so the 10 GbE page needed
   a five-minute collect loop by hand (BS-05).
3. **A deploy did not reach the Durable Object.** The Worker served the new version
   while the Hub kept the old code, because pushes every 3 s never let it go idle.
   `/api/run` returned "not found" until the lab server was paused (BS-09).
4. **Chart text was missing in production only.** HoloChart's text worker uses eval,
   which the site's CSP forbids; the dev server sets no CSP, which hid it (BS-10, BS-17).
5. **Prose numbers drift from live charts.** The 10 GbE commentary quotes medians
   written on one day, and the charts beside it keep moving; four figures were wrong on
   first writing (BS-04).
6. **Estimates crept in beside measurements.** A "theoretical maximum" section mixed
   computed ceilings with measured rates and had to be taken out (BS-04).
7. **A hardware change broke comparability silently.** The 10G rows had to be told
   apart from the 3G rows on the same cable by a field in the plan (`min_speed_mbps`),
   and tomorrow's motherboard swap makes freya a different receiver mid-campaign
   (BS-06).
8. **Missing counters looked like zero.** The Mac reports no interface counters, so
   wire bytes for Mac-sent runs were empty until the reader fell back to the other
   end (BS-02).
9. **Failures surfaced late.** A staging job failed, the next run failed twice, and the
   runner halted; the only sign was an event line until someone looked (BS-12).
10. **Layout broke at sizes nobody tested.** Charts ran off their cards after going from
    one column to two, and the speed chart was 100 px wide on a phone (BS-16).

## Priorities

P0 is needed before a second project can adopt the site. P1 makes it good to run
day to day. P2 widens it. All stories are open. Acceptance criteria are targets.

---

## P0 — adoptable

### BS-01 Site configuration instead of code

**Why:** every name, order and grouping on the page is in TypeScript (lesson 1).

**What:** one `site.json` (or TOML), loaded by the lab server and pushed with the
state, holding: site title and brand; runner order, titles and descriptions; link and
host display names; which views are on; the metric each view leads with and its unit;
colours for arms and directions. The page reads it and has no lab names in its source.

**Done when:** `grep -E "neo|freya|mars|orion" src/` finds nothing; renaming a link or
reordering runners is a config change with no deploy; a second config renders a
different lab from the same build.

### BS-02 A documented data model and adapters

**Why:** the site reads `runner.py`'s status files, `plan.json`, `samples.jsonl` and
`analyze.py` output directly, with xs/rsync field names (`durable_s`, `wire`,
`client_cpu_s`). Missing fields fail quietly (lesson 8).

**What:** a versioned schema the page consumes: *runner* (state, current job,
progress, queue), *run* (id, experiment, design, hosts, configuration, start/end),
*sample* (cell factors, arm, block, valid/void, and named metrics with units and a
"higher is better" flag), *result* (comparison, ratio, interval, verdict), *event*.
Adapters turn a harness's files into it; the current lab becomes the first adapter.
Unknown or missing metrics are explicit (`null` with a reason), never zero.

**Done when:** the page imports only the schema's types; the xs lab adapter passes a
schema validator over every run in `benchmarks/results/`; a second adapter exists
(see BS-15).

### BS-03 Allowlist publishing

**Why:** `scrub()` removes usernames, paths and addresses by pattern. For another
project, anything a pattern misses is published.

**What:** the adapter declares which fields leave the lab; everything else is dropped
before the push. Strings that are published still pass the pattern scrub as a second
line. A dry-run command prints exactly what would be pushed.

**Done when:** a field added to `samples.jsonl` does not reach the relay unless listed;
the dry run is part of the setup guide; the existing leak check (no `/Users/`,
`/home/`, `user@`, private addresses in `/api/state` or any `/api/run`) runs in CI.

### BS-04 Report pages from data, with honest numbers

**Why:** the 10 GbE page is bespoke TypeScript (`src/tengig.ts`) and its prose quotes
numbers by hand (lessons 5, 6).

**What:** report pages written as Markdown plus chart blocks. A chart block names a
query (runs where `link_mbps >= 10000`, experiment `Z5-*`, arms, metric), a chart type
(scatter, grouped bars, box, forest, table) and options. Inline expressions such as
`{{median data_gbps where arm=xs-z2 and direction=mars>mac}}` are filled from the same
query, so the text and the chart cannot disagree. Every figure on a page is measured
unless it is marked as an estimate, and estimates render differently. Each page shows
when its data last changed and which runs it counts.

**Done when:** the 10 GbE page is rebuilt as a report file with no page-specific
TypeScript; a number in its prose updates when a run is added; an estimate cannot be
written without the estimate marker.

### BS-05 Results arrive without a manual collect

**Why:** lesson 2.

**What:** the lab server reads each runner's run directories (local or over its
existing read-only SSH route) and pushes new samples as they are written, not after
`plan.py collect`. Collection into the results tree stays the record of truth;
streaming is for display.

**Done when:** a sample appears in the Runs view and on report pages within a minute
of being written, on any runner, with no command run.

### BS-06 Configuration epochs

**Why:** results from different hardware were told apart by an incidental plan field,
and a motherboard swap will change a host mid-campaign (lesson 7).

**What:** each run records a configuration fingerprint per host: CPU, memory, board,
storage device and filesystem, NIC and negotiated link speed, OS and kernel, tool
builds. The site groups runs into epochs when a fingerprint changes, labels charts and
tables with the epoch, never pools across epochs by default, and can compare two
epochs side by side.

**Done when:** the 10 GbE page selects its runs by epoch instead of `min_speed_mbps`;
freya's runs before and after the 2026-10-17 swap show as two epochs.

---

## P1 — good to run

### BS-07 Live metrics beyond link rate

The speed strip is the only live metric. Let an adapter declare live series per host
(CPU busy, temperature, dirty bytes, disk throughput, power) with units and an axis
policy (fixed, stepped like the link axis, or auto). The collector already samples
some of these in `probe.py snapshot`.

**Done when:** a runner card can show any declared series, and adding one is config
plus an adapter function.

### BS-08 Statistics shown with their uncertainty

The live forest shows running ratios without intervals; the Runs view shows medians and
the 10th–90th range but no interval on a ratio. Show bootstrap or analysis-provided
intervals everywhere a ratio appears, state the threshold (delta) and the number of
blocks, mark comparisons that are still screening, and explain verdicts in one line
each.

**Done when:** no ratio is shown without its interval and block count; the Results and
Runs views agree on a comparison's numbers.

### BS-09 Deploys that verify themselves

Lesson 3. A `deploy` script builds, deploys, then checks that the Worker *and* the
Durable Object report the new build id (add `/api/version`), and if the Hub is stale,
asks it to restart (an authenticated `ctx.abort()` path on ingest), then confirms the
lab server re-pushed state and run details.

**Done when:** one command deploys and prints "Worker and Hub on <build>, N runs
present"; the stale-Hub case is tested.

### BS-10 Production parity in development

Lesson 4. The dev server serves the same CSP and headers as the Worker, so CSP faults
appear locally; `wrangler dev` with local Durable Object storage is the documented
preview; the Vite file-watcher staleness seen this week is understood or worked around
(restart on server-file changes).

**Done when:** loading the dev site with the text worker re-enabled shows the same CSP
error as production.

### BS-11 Faster first load

The page ships about 2 MB of JavaScript (640 kB compressed: HoloChart with three.js)
before anything shows. Split by view, load HoloChart only when a chart is about to draw, preload text
fonts, and keep the live cards usable as plain HTML before the charts arrive.

**Done when:** the Live view is readable in under a second on a mid-range phone, and
the largest initial script is under 300 kB compressed.

### BS-12 Alerts

Lesson 9. Notify (webhook, email or push, configured in the lab server, never from the
relay) when a runner halts, a run fails before its first sample, a host becomes
unreachable, a void rate passes a threshold, or a run's sentinel drifts.

**Done when:** the 2026-10-16 congress staging failure would have sent one message
within a minute of the runner halting.

### BS-13 Shareable views and an API

Every view state (run, metric, cell, scale, filters, epoch) is in the URL. Document
`/api/state`, `/api/run` and the report queries as a read-only public API with the
schema version, so others can pull data without scraping the page.

**Done when:** a copied link reopens the exact chart; the API reference lives beside the
schema.

### BS-14 Reproducibility panel

Each run and report shows how to reproduce it: spec file, engine revision, bundle
hash, corpus digests, host epochs, and the command that queues it. Link to the commit.

**Done when:** from any chart a reader can reach the spec and revision that produced
each point.

---

## P2 — wider

### BS-15 A second adapter to prove the boundary

Write adapters for one or two common formats (hyperfine JSON, criterion, pytest-benchmark,
k6 or wrk output) with example data, and run the site on them in CI. The data model
(BS-02) is not done until something other than this lab uses it.

### BS-16 Layout tests at real sizes

Lesson 10. Playwright runs over fixture data at 375, 768, 1280 and 1920 px, in light and
dark themes, asserting no element is wider than its card or the page, and taking
screenshots for review. Include the one-column-to-two-column resize that broke the
charts.

### BS-17 Upstream fixes instead of workarounds

Remove the `@mk7s/holochart-render` alias once HoloChart exports `configureText`
(task already spawned); consider asking for a non-eval text worker. Track any other
library workaround here with the upstream issue.

### BS-18 Several dashboards on one deployment

One Worker serving several dashboards (a Hub per dashboard id, its own ingest secret
and public/private setting), so a team runs one deployment for many benchmark suites.
Includes per-dashboard storage limits and run-detail chunking for runs larger than a
Durable Object value allows.

### BS-19 Theming and the background as options

Brand colours, fonts and logo from config; the ink-orbit background as an optional
plug-in with a static fallback; contrast checked against the background in both themes.

### BS-20 Accessibility pass

Every chart has a text summary and a data table (HoloChart already builds one); the
flip-clock and clock animations have no effect under reduced motion; keyboard paths
through every view; screen-reader names for live regions without announcing every
second's speed.

### BS-21 Durable history

Events are capped at 200 in memory and speed history at 90 seconds. Keep a day of
events and an hour of live series in Durable Object storage (or D1), with the page
able to scroll back.

### BS-22 Setup guide

A guide for adopting the site: install, write `site.json`, write or pick an adapter,
dry-run the publish (BS-03), create the Worker and secret, deploy (BS-09), and check
the result. Measured against someone doing it from scratch.

## Suggested order

BS-01 and BS-02 first, since every other story builds on them; then BS-03 before any
other project publishes; BS-05 and BS-04 to remove the two hand-maintained parts of
this site; BS-06 before the motherboard swap's results are compared. BS-09, BS-10 and
BS-12 are small and remove this week's operational surprises.
