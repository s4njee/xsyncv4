---
title: "xsync-status(7)"
description: "Current capabilities and remaining work, reviewed against the project backlog."
manual: "xsync-status(7)"
manualName: "Development status"
sectionNumber: "7"
---

# xsync-status(7)

<div class="manual-deck"><strong>Development status</strong><p>Current capabilities and remaining work, reviewed against the project backlog.</p></div>

## SCOPE {#scope}

<p>Reviewed 10 October 2026 against the current README, executable help, daily-driver backlog, and GUI backlog. Earlier backlog problem statements are historical; the latest status and completion entries describe the implemented CLI.</p>

<aside class="manual-note"><span>NOTE</span><p>This page describes development status. Planned capabilities are not part of the command reference.</p></aside>

## IMPLEMENTED CLI {#implemented}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Area</th><th scope="col">Current status</th></tr></thead><tbody><tr><td>Trust hardening</td><td>All 15 P0 stories recorded complete</td></tr><tr><td>Reach and everyday CLI</td><td>R-02–R-09 and E-01–E-13 recorded complete; R-01 remains partial</td></tr><tr><td>Progress</td><td>U-02–U-10 recorded complete</td></tr><tr><td>Data reuse</td><td>Verified-prefix resume, large-file delta, sparse output, and link-dest snapshots</td></tr><tr><td>Metadata</td><td>Hard links, xattrs, ACLs, incoming mode/owner overrides, platform-specific times and flags</td></tr><tr><td>Automation</td><td>Itemization, formatted stdout, error summaries, JSON progress, bandwidth limits, idle timeouts</td></tr></tbody></table></div>

## REMAINING VALIDATION {#validation}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Backlog item</th><th scope="col">Status and remaining work</th></tr></thead><tbody><tr><td><code>R-01</code></td><td>Partial: remaining physical-host SSH checklist coverage</td></tr><tr><td><code>U-01</code></td><td>Partial: native terminal visual checks remain incomplete</td></tr><tr><td><code>U-11</code></td><td>Unverified: suspend/resume and cursor hygiene acceptance</td></tr><tr><td>Performance work</td><td>Broader target benchmarks and regression gates remain tracked; see the <a href="roadmap.html">roadmap</a></td></tr></tbody></table></div><p>The recorded product demo is a real local execution. It does not establish completion of remaining physical-host or native terminal acceptance checks. Historical benchmark speedups predate trust fixes and the atomic-write default.</p>



## GUI ENGINE ROADMAP {#gui}

<p>All GUI backlog stories G-01–G-24 are open. Existing copy, listing, selection, metadata, and progress primitives are foundations for these requirements, rather than evidence that the full GUI contract exists.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Priority</th><th scope="col">Proposed work</th></tr></thead><tbody><tr><td>P0 · G-01–G-08</td><td>Versioned machine interface, deterministic execution, structured browsing, authoritative completion, typed per-item errors, headless SSH auth, conflict decisions, job cancellation</td></tr><tr><td>P1 · G-09–G-18</td><td>Rename/move/delete workflows, private partials, persistent queue/recovery, previews, responsive browsing, preflight/refresh, aggregate controls, helper lifecycle, acceptance client</td></tr><tr><td>P2 · G-19–G-24</td><td>Remote-to-remote copies, additional endpoint adapters, Windows support, large-directory budgets, preview/edit, optional embedded library</td></tr></tbody></table></div>

## CURRENT BOUNDARIES {#boundaries}

<p>Two-pane browsing does not imply automatic bidirectional synchronization. Persistent queues, interactive conflict choices, job-control APIs, and runtime aggregate limits remain proposed GUI integration work. Current <code>--progress=json</code> is documented on the <a href="progress.html#json">output page</a>; it is not a promise of that future versioned GUI API.</p>



## MAINTENANCE {#sources}

<p>The option reference and downloadable manpage are generated from <code>xsync --help</code>. Workflow pages are curated from README behavior. Development status comes from the latest backlog states rather than unresolved wording in the original audit.</p>

<p>Source fingerprints for this documentation build are available in <a href="sources.json">sources.json</a>. Regenerate the docs when command behavior or feature status changes.</p>



