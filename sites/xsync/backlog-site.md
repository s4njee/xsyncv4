# xsync site backlog — from manual snapshot to interactive reference

Written 2026-10-10 against `sites/xsync` at `70da4f0` (VitePress 1.6.4, 13 generated
manual pages, product page with recorded terminal playback). The CLI it documents is
`xs` 0.1.0, protocol 4, at the same commit. S0 and S1 are complete apart from two partial
items (S-15, S-21); their evidence is in the completion logs at the end.

## What "fully fleshed out" means here

The bar is that a reader can **answer any question about an `xs` invocation from the site
without opening the README or the source**, and can **try it before running it**:

| reader | today | what the site needs |
|---|---|---|
| rsync user deciding whether to `alias rsync=xs` | product page, compatibility table | a migration guide, the full differences list, honest benchmark numbers |
| someone building a command | flat option table | every option deep-linkable, a command explainer, a path/slash visualizer, a filter playground |
| a script author | one JSON sample, exit table | the JSON event schema, an itemize decoder, a complete exit-code reference, runnable recipes |
| someone debugging a run | the error recording | fallback and exit-code lookups, troubleshooting, recordings of every phase |
| a contributor | development status page | architecture, protocol and feature-bit reference, test matrix, how the site is built |

Two things hold for every item below:

1. **Real output only.** The existing site already refuses to fake output: recordings come
   from the real binary, and the option table comes from `--help`. Every new widget follows
   that rule. Where a widget models behavior (filters, path semantics, option parsing), its
   logic is either the real C++ compiled to WebAssembly or a port that runs the same test
   vectors as the C++ in CI.
2. **No drift.** Each page names its sources. The build fails, or at least warns, when a
   source has changed since the page was last reviewed.

## How to read this

Status values match `backlog.md`:

- **confirmed** — reproduced on 2026-10-10 against the current site build
- **code** — known from how the site is built; not separately tested
- **new** — does not exist yet
- **partial** — some of it exists; the "Done when" column says what remains

Size: **S** an hour or two, **M** a day, **L** several days, **XL** a week or more.

IDs are `S-NN`. The tiers are in priority order, and items within a tier are roughly in the
order I would do them. Items cite source files relative to the repository root.

---

## Audit summary (2026-10-10)

What exists and works:

- `npm ci && npm run build` succeeds in about 6 s on Node 22. It regenerates the 13 pages from
  `sites/xsync/scripts/docs_content.py` and `docs-inputs/xsync-help.txt`, builds VitePress,
  and copies the result into `dist/docs/`.
- VitePress gives local search, sidebar, outline and copy buttons. The man-page styling is
  consistent.
- The product page replays 4 real PTY recordings (105, 8, 27 and 1 frames) with a scrubber,
  state buttons, a JSON sample, and downloads. It handles reduced motion and has a skip link
  and live-region announcements.
- `capture-output.py` verifies its own fixture copy with SHA-256 and checks the exit code of
  each recorded case.

What's wrong or missing:

- **The binary was renamed `xsync` → `xs` (commit `4159000`) after the site's content was
  written.** Every command, the helper path, the build path (`build/xsync`), the captured
  help and the recordings still say `xsync`.
- The option table loses its descriptions for `--rsync-path` and `--compress-level`. Their
  help lines have a single space before the description, and the parser needs two.
- The development status page contradicts `backlog.md`. It also references a
  `backlog-gui.md` that is not in this repository.
- `docs/public/sources.json` fingerprints no longer match `README.md` or `backlog.md`, and
  nothing checks them.
- README topics the site doesn't cover at all: benchmarks, how the speed is achieved, the
  protocol and feature bits, `%i` itemization codes, the JSON schema, release downloads, the
  test suite.
- There is no interactivity beyond recording playback. Docs pages link back to the product
  page instead of embedding recordings.
- Rebuilding rewrites the committed `dist/docs/` with new hashed asset names, so the
  checked-in output can't be reproduced from source.

---

## S0 — Correct: things the site says today that are wrong

Ship nothing new until these are fixed. Each one is a place where a reader copies a command
and it fails.

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| S-01 | **Commands use the old executable name.** Every example on every page is `xsync …`. Getting started says `build/xsync --version`. The SSH page says helpers are looked up at `~/.local/bin/xsync`, but `src/remote.cpp:2522` and `src/install.cpp:86` use `~/.local/bin/xs`. The product page install panel (`dist/app.js`, `dist/index.html`) and `sites/xsync/README.md` (`build/xsync`) are wrong too. | **done** | All runnable commands use `xs`. The product name stays whatever Decision 1 says. `grep -rn '\bxsync ' docs/*.md dist/*.html dist/app.js` finds only product-name prose, never a command. | S |
| S-02 | **Captured help is stale and mis-parsed.** `docs-inputs/xsync-help.txt` reads `xsync version 0.1.0 … git 2f3e27633fac-dirty`. In `generate-docs.py` the `\s{2,}` split folds `--rsync-path=PROGRAM specify…` and `--compress-level=NUM explicitly…` into the option cell with an empty description. `--version, --help` has no description, and the no-op rows keep a leading space. | **done** | Help and `xs.1` are recaptured from the current `build/xs`. The parser handles single-space separation (options never contain a space before their argument). A generator test asserts every row has a non-empty description. | S |
| S-03 | **Development page is out of date.** It shows U-01 as "partial", but `backlog.md` says skipped at the user's request. It shows U-11 as "unverified", but it is done and P2 is closed. It omits F-01 (partial) and the P3/P4 tiers. Its GUI roadmap cites `backlog-gui.md`, which this repository does not contain. | **done** | The status table is generated from the `backlog.md` tier tables (ID, status, item title), not hand-copied. The GUI section is removed or points to a file that exists (Decision 5). | M |
| S-04 | **Source fingerprints are never checked.** `docs/public/sources.json` records SHA-256 for `README.md` (`ce77da…`) and `backlog.md` (`5b29f3…`). Both now hash differently (`1b7e40…`, `ba63a3…`). | **done** | `npm run build` compares each fingerprint and lists the pages whose sources changed. CI treats a mismatch as a failure. `npm run docs:review` updates `reviewed_at` and the hashes after a person has re-read those pages. | S |
| S-05 | **Exit-code table is incomplete.** 127 (`RERR_CMD_NOTFOUND`, `src/common.h:236`) is how a missing remote helper is reported under `--no-fallback` (`src/remote.cpp:2627`), and 255 is passed through when ssh itself fails (`src/remote.cpp:2628`). Neither is listed. (The original audit also named 124; it is defined but never returned.) | **done** | The table is generated from the `RERR_*` enum plus the message strings in `src/util.cpp`, with curated "what to do" text per code. | S |
| S-06 | **Version and protocol are hard-coded.** `Layout.vue` prints `VERSION 0.1.0` and `NATIVE PROTOCOL 4`, and `app.js` prints `protocol 4`. | **done** | Both come from the captured `--version` line through VitePress `themeConfig` and `sessions.json`. | S |
| S-07 | **Root-relative URLs assume a domain root.** `/favicon.svg`, `/vendor/holocss/…`, `href="/"` in `Layout.vue`, `/docs/xs.1` and `base: '/docs/'` all break if the site is served from a subpath, such as a GitHub Pages project site at `/xsyncv4/`. | **done** | One `SITE_BASE` setting drives both the product page and VitePress `base`. A build at `/xsyncv4/` passes the link checker (S-54). | S |
| S-08 | **Committed `dist/` can't be reproduced.** Running `npm run build` on a clean checkout deletes and renames hashed files under `dist/docs/assets/`. Reviewers can't tell whether the committed site matches the source. | **done** | Decision 2 is applied. Either `dist/docs/` is untracked and built in CI, or CI rebuilds and fails on `git diff --exit-code dist/`. | S |

## S1 — Complete: content the CLI has that the site doesn't

The README is 831 lines. Most of it is accurate, detailed behavior that the site summarizes
in a sentence or leaves out. These items close that gap. They are written once as structured
data where possible, so S2's widgets can reuse them.

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| S-10 | **Option data model.** Each option is a table row and nothing more. There is nothing to link to and no metadata. | **done** | `data/options.json` is generated from `--help` and joined with a curated annotations file. Each entry has: short/long forms, argument, help text, class (`native`, `delegates`, `no-op`, `xs-only`, `platform:macOS`), implied options (`-a` → `-rlptgoD`, `-A` → `-p`, `-P` → `--partial --progress`), required feature bit, related pages, and an example. The build fails if `--help` lists an option the annotations don't cover. | M |
| S-11 | **Per-option anchors and detail.** You can't link to `--delete`. | **done** | The options page renders from S-10 with stable anchors (`options#delete`, `options#z`), filters by class, and has an expandable detail for each option. Detail text covers the README nuances, for example `--chown` versus `--no-owner` ordering on push, and `-E` on Apple rsync. | M |
| S-12 | **Performance page.** The site has no benchmark content. The README has the neo/freya table, the historical APFS baseline and methodology caveats. `benchmarks/results/*.json` has per-sample wall time, CPU and RSS data. | **done** | The page is generated from `benchmarks/results/*-run-manifest.json` and the per-case JSON. It shows: hosts and filesystems, medians with the per-sample spread, CPU and peak RSS, losses as well as wins (`checksum` 0.65×, `tiny` 0.96×), and the cache policy. The historical table is labeled as predating the trust fixes. Adding a new run directory adds it to the page with no hand edits. | M |
| S-13 | **How it works.** "How it gets its speed" (parallel scan, two-queue pool, APFS clones, pipelined DIR/NEED/DATA protocol) isn't on the site. | **done** | An architecture page with three diagrams: the local engine pipeline, the remote sender/receiver frame flow, and the atomic-write and verified-resume lifecycle. It links to the `src/` files in the README layout table, which must be refreshed: it lists 9 of 26 `.cpp` files. | M |
| S-14 | **Protocol and feature-bit reference.** There is one paragraph. `src/common.h:25-49` defines 34 `PF_*` bits that decide when a request delegates or fails with code 4. | **done** | The page is generated from `common.h`: bit, value, name, what requests it, and what happens without it (fallback or exit 4). Also covers the N/N-1 window, the frozen protocol-3 fixture (`tests/fixtures/README.md`) and the rule for adding a feature. This covers the protocol half of backlog Q-13 (`docs/protocol.md`). | M |
| S-15 | **Itemization and `--out-format` reference.** `%i` is never explained. That includes the eleven positions, the twelfth `f` flag for `--fileflags`, `hf`/`hL`/`hS`, `=>` versus `->`, and `\#ooo` escaping. | **partial** | A position-by-position reference with real `-ii` output from a fixture covering every character. Each `%` escape has an example and a note on how `%b` differs from rsync. | S |
| S-16 | **JSON event schema.** The site shows one sample event and describes the fields in prose. | **done** | `progress`, `file` and `complete` are published as a JSON Schema (`docs/public/progress.schema.json`), validated in CI against a fresh `--progress=json` capture. The page documents `path_bytes_hex`, null `exit_code`, and the fact that the schema is unversioned (the GUI backlog's versioned API is a separate thing). It includes a `jq` and a Python consumer. | S |
| S-17 | **Migration guide from rsync.** Differences are split across compatibility, metadata and progress pages, and the README has more. | **done** | One page walks through the invocation shapes from `backlog.md` ("What daily driver means"), what changes for each, the fallback notice, `alias rsync=xs` caveats, Apple rsync `-E`, and clones carrying extra metadata. The differences list is generated from the difftest skip/expectation data once Q-13 lands. Until then it is curated and fingerprinted. | M |
| S-18 | **Recipes.** The examples are one-liners. | **done** | At least eight full, runnable recipes, each with expected output (S-50): rotating `--link-dest` snapshots; safe mirror (dry run → review → `--max-delete`); Raspberry Pi over SSH with `--install`; `find -print0 \| xs --files-from`; cron/launchd with exit-code handling; parsing `--progress=json` for a wrapper; bandwidth-limited overnight push with `--timeout`; preserving everything on macOS (`-aHAXN --fileflags`). | M |
| S-19 | **Troubleshooting and FAQ.** There is none. | **done** | Entries for: "xs fell back to rsync" (what each notice means, how to see why, `--no-fallback`), exit 4 in strict mode, remote helper not found (127), SSH prompt behavior, why `-z` does nothing locally, why the progress bar stops below 100 % on a push, and clone metadata surprises. Each entry quotes the real diagnostic text. | M |
| S-20 | **Install and releases page.** Release artifacts, the SHA-256 manifest, the local Homebrew tap, and `--install` are scattered across getting-started and SSH pages. | **done** | One page covers building, `cmake --install`, the Homebrew tap, release presets, checksum verification, `--install HOST` with its refusal rules, and the helper lookup order shown as a flowchart. If releases are published, each release is listed with its hashes. | S |
| S-21 | **Changelog and versioned docs.** None exist. | **partial** | `CHANGELOG.md` exists (backlog Q-13) and renders on the site. Each tagged release gets a frozen copy of the docs under `/docs/vX.Y/`, with a version switcher. | M |
| S-22 | **Contributor pages.** The development page is status only. | **done** | Pages for: the test matrix (from the README Tests section, grouped by area, with platform and privilege needs), the source layout, how to recapture recordings and help, and how the site is built. | S |

## S2 — Interactive: let the reader try it before running it

These are the items that make the site interactive. Each one runs entirely in the browser and
never touches the reader's files or network. Each one also states how it is kept honest
against the real binary.

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| S-30 | **Command explainer.** You paste `xs -azP --delete -e "ssh -p 2222" src/ host:/backup/` and the widget breaks it down token by token: each flag's meaning (S-10), the `-a` expansion, the source/destination roles, and warnings. Warnings cover a missing trailing slash, `--delete` without `-n` first, options that will delegate to rsync, no-ops, and macOS-only flags on a Linux target. | **new** | It works for every option in `--help`. Its accept/reject verdicts match `xs` on a table of argument vectors generated by running `build/xs` (the same table backlog Q-10 wants). It is linkable via a URL fragment. | L |
| S-31 | **Path and trailing-slash visualizer.** You toggle the source slash, whether the destination exists, `-R` with `/./`, `--files-from` with `dir` versus `dir/`, and `--mkpath`. The widget shows the resulting destination tree. | **new** | Every combination shown is generated at build time by running `xs` on a fixture and recording the resulting tree. No hand-written results. | M |
| S-32 | **Filter playground.** You edit rules (`--include`, `--exclude`, `-f`, `P`/`R`/`H`/`S`, modifiers) against a sample or pasted tree. The widget shows, per path, the outcome (transfer, skip, protect, delete with `--delete`) and which rule matched first, with source-side and receiver-side views. | **new** | The matcher is `src/filter.cpp` compiled to WebAssembly (Decision 3), or a port that passes `tests/filter_test.cpp`'s vectors in CI. It demonstrates `--include='*/'` ordering and `--delete-excluded`. | L |
| S-33 | **Itemize decoder.** You paste `-i` output lines and get a per-character explanation. | **new** | Every code produced by the S-15 fixture decodes correctly. Unknown characters are flagged, not guessed. | S |
| S-34 | **Recording player as a reusable component.** Today the player lives only on the product page, renders stripped text, and exists only at 120 columns. | **partial** | A `<Recording name="…">` VitePress component embeds on any docs page. It renders the raw `.ansi` stream faithfully (bold, dim and the bar glyphs; for example via xterm.js in read-only mode). It has a width switcher backed by captures at 40, 80 and 120 columns, and keyboard frame stepping. It works on phone widths without horizontal page scroll. | M |
| S-35 | **More recordings.** Only local copy, checksum, interrupt and missing-source runs exist. | **new** | `capture-output.py` adds: an SSH push through `tests/fakessh.sh` with `-z` (wire rate and ratio), `-vv` limiting stage, `deleting N`, `waiting for receiver`, a dry-run plan summary, resume after interrupt (prefix reuse), `--link-dest`, `TERM=dumb`, `LC_ALL=C`, and a fallback notice. Each recording is embedded on the page it illustrates. | M |
| S-36 | **JSON event explorer.** It shows the recorded `progress.ndjson`, or a file the reader drops in (read locally and never uploaded), as a timeline: files and bytes over time, phase bands, and a file-event table with itemization decoded. It plays in sync with the matching terminal recording. | **new** | Accepts any stream that validates against S-16. Malformed lines are reported by line number. | M |
| S-37 | **Benchmark explorer.** S-12's data shown as an interactive chart: filter by dataset, direction, flags and cache; per-sample dots behind the medians; CPU and RSS toggles; each point links to its evidence JSON. | **new** | Every number traces to a results file. A run with incomplete scenarios is shown as incomplete, not dropped silently. | M |
| S-38 | **Defaults precedence simulator.** You enter a config file, `XSYNC_OPTS`, the `XSYNC_*`/`RSYNC_RSH` variables and command-line flags. The widget shows the effective value of each setting and which layer won, including the six-step remote-shell chain and the `--filter='!'` reset. | **new** | Results match `xs` on generated vectors. That probably needs a hidden or debug way to print the effective options (Decision 7); without one, vectors come from existing tests. | M |
| S-39 | **"Will this run natively?" checker.** You enter flags, the peer's protocol (4, 3, or none) and the peer OS. The widget answers native, delegates to rsync, or fails with exit 4 under `--no-fallback`, and names the missing feature bit. | **new** | Driven by S-10 and S-14 data. Matches `tests/protocol_test.py` and `tests/fallback_test.py` outcomes for the cases they cover. | M |
| S-40 | **Rate and size calculator.** `--bwlimit` input shows the effective bytes/s, using the rules in `parse_rate` (`src/main.cpp`): bare numbers are KiB/s, suffixes, rounding, and the 512 B/s floor. Byte counts show as they would appear with the default units, `-h` and `-hh`. | **new** | Vectors come from `tests/io_limit_test.py` and `tests/progress_units_test.py`, and the widget passes them in CI. | S |
| S-41 | **Exit-code and diagnostic lookup.** You paste a code or a line of stderr and get the code's meaning, likely causes, and the next step, linked to troubleshooting. | **new** | Covers every `RERR_*` code and every message prefix in the S-35 recordings. | S |
| S-42 | **Personalised examples.** You set `SRC`, `DEST` and `user@host` once, and every example on every page updates to use them. Copy buttons copy the personalised command. The values are kept in `localStorage`. | **new** | Placeholders are explicit tokens in the example markup. Clearing the values restores the defaults. Nothing is sent anywhere. | S |
| S-43 | **Protocol handshake visualizer.** You choose client and server protocol versions and feature sets, then step through Hello, feature intersection, and the first DIR/NEED/DATA frames. | **new** | Frame names and order match `src/remote.cpp`. Feature sets come from S-14. | M |

## S3 — Trust: docs that cannot silently drift

The project's culture is evidence first: completion logs, verified benchmarks, frozen
fixtures. The site should meet the same bar.

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| S-50 | **Every example runs in CI.** Examples are copied into Python strings and never executed, which is how S-01 happened. | **new** | Examples are marked runnable or illustrative. Runnable ones execute against fixture trees with the built `xs`: local examples directly, SSH examples through `tests/fakessh.sh`, with paths substituted. The exit code and key output lines are asserted. The captured output is available under each example as "actual output". | L |
| S-51 | **One source for reference data.** Environment variables are documented in `tools/help_to_man.py`, `docs_content.py` and the README, each written separately. | **new** | Options, environment variables, exit codes and feature bits are each generated from one place (`--help`, `src/common.h`, `src/util.cpp`, plus one annotations file) and consumed by the man page, the site and the README tables. | M |
| S-52 | **Widgets share vectors with the C++ tests.** | **new** | S-30, S-32, S-33, S-38, S-39 and S-40 each load a vector file that a C++ or Python test also checks, and one CI job runs both sides. | M |
| S-53 | **Recordings tied to the documented binary.** `sessions.json` says `xsync … git 2f3e27633fac-dirty` while the help may come from a different build. | **confirmed** | The build fails if the recordings' `binary_version` differs from the help capture's version line. The release workflow recaptures both. | S |
| S-54 | **Link and anchor checking.** There is none. | **new** | CI checks every internal link and `#anchor`, README → site links, and the downloads (`xs.1`, recordings, help). It runs at the configured base path (S-07). | S |
| S-55 | **Docs CI job.** The repository has no CI at all (backlog Q-02). | **new** | A GitHub Actions job builds `xs`, recaptures help and recordings, regenerates the docs, runs S-04, S-50, S-52, S-53, S-54 and S-61, and uploads a preview. It deploys on `main` (S-64). | M |

## S4 — Polish: authoring, accessibility, hosting

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| S-60 | **Author in Markdown, not Python strings.** `docs_content.py` holds all 12 curated pages as HTML inside Python literals, in 123 lines up to 984 characters long. Editing a sentence means editing escaped HTML. | **code** | Curated pages are `.md` files using small Vue components (`<Example>`, `<Note>`, `<Recording>`, `<OptionRef>`). The generator only writes reference pages (options, exit codes, feature bits, benchmarks, status). "Edit this page" links point at the real source file. | M |
| S-61 | **Readable type and contrast.** `dist/style.css` sets 48 font sizes between 6 px and 9 px, and much of the text is `#686868`–`#808080` on `#080808`. | **confirmed** | No text is under 12 px. All text meets WCAG AA contrast. axe-core runs in CI on every page with zero serious violations. | M |
| S-62 | **Remove dead CSS.** `.route`, `.sparkline`, `.file-table`, `.telemetry`, `.segmented-progress` and related rules belong to an earlier mock and have no markup in `index.html` or `app.js`. | **confirmed** | The rules are deleted. The page renders the same before and after (screenshot diff). | S |
| S-63 | **Light theme.** Both views force dark (`appearance: 'force-dark'`, `color-scheme: dark`). | **code** | Decision 6. If yes: grayscale light tokens, and the page follows `prefers-color-scheme` with a toggle. The recording player stays legible in both themes. | M |
| S-64 | **Hosting and deploy.** `.openai/hosting.json` names a static host for `dist/`, but nothing documents or automates a deploy. | **code** | Decision 4. A documented deploy runs from CI on `main`, with a preview URL for each PR, and the production URL is linked from the repository README. | S |
| S-65 | **Search tuned for rsync vocabulary.** | **new** | Searching `--del`, `rsync -P`, `exit 23`, `delete-before` or `itemize` reaches the right section. Option aliases and rsync terms are indexed as synonyms. | S |
| S-66 | **Product page carries real substance.** It has three feature cards and the demo. | **partial** | Adds an honest benchmark headline (from S-12, wins and losses), a "differences from rsync" teaser (S-17), the command explainer (S-30) as a second interactive section, and download or install links (S-20). | M |
| S-67 | **Metadata for sharing and crawling.** | **new** | Open Graph and Twitter tags with a generated preview image per page, `sitemap.xml`, `robots.txt`, and canonical URLs at the configured base. | S |
| S-68 | **Mobile terminal views.** 120-column recordings are clipped on phones. | **new** | Covered by S-34's 40-column captures. Checked at 375 px with no horizontal page scroll. | S |

---

## Decisions needed from you

Decisions 1, 2 and 5 were made on 2026-10-10 and are applied by S0; see the completion log.

1. **Product name versus command name.** *Resolved: xsync brand, `xs` in every command.* The executable is `xs`, the README title is
   "xs (xsyncv4)", and the config directory and environment variables are `xsync`. The site
   brands everything "xsync". Recommendation: keep **xsync** as the product name and `xs` in
   every command. The CLI diagnostics now follow the same rule (`d3a49f8`).
2. **Committed build output.** *Resolved: keep `dist/docs/` committed; `npm run check` proves a rebuild reproduces it.* Either stop committing `dist/docs/` and build it in CI, or keep
   it committed with a CI diff check. Recommendation: stop committing it. The product page in
   `dist/` is hand-written source and stays committed.
3. **WebAssembly or ports for widgets.** Compiling `filter.cpp` and the option parser with
   Emscripten gives exact behavior, but adds a toolchain to the site build. JavaScript ports
   are lighter but need shared vectors (S-52). Recommendation: WebAssembly for the filter
   playground (S-32), where the semantics are deepest; ports with shared vectors for the rest.
4. **Hosting target and base path.** Keep the existing host named in `.openai/hosting.json`,
   or use GitHub Pages at `/xsyncv4/`. This decides S-07 and S-64.
5. **GUI roadmap.** *Resolved: keep the section, marked as maintained outside this repository and unchecked.* The development page describes G-01 to G-24 from a `backlog-gui.md` that
   is not in this repository. Add that file here, or remove the section.
6. **Light theme.** The grayscale dark look is deliberate. Should light mode be offered (S-63)?
7. **CLI support for the site.** S-38 is far simpler and more trustworthy if `xs` can print
   its effective options and their sources (for example a hidden `--debug-options`). This is
   a small CLI change made for the docs. Is that acceptable?

## Suggested order

1. **Correct** — S-01, S-02, S-05, S-06 (one recapture pass), then S-03, S-04, S-08. After
   this, nothing on the site is wrong.
2. **Make drift impossible** — S-55 with S-04, S-53 and S-54, then S-60 and S-51. Every later
   page lands on a base that checks itself.
3. **Data model** — S-10 and S-14. Most of S1 and S2 reads from these.
4. **Fill the gaps readers hit first** — S-11, S-17, S-19, S-15, S-16, S-12.
5. **First interactive tools** — S-30 (explainer), S-31 (paths), S-33 (itemize), S-40,
   S-41, S-42. They are cheap, they reuse S-10, and they cover the most common questions.
6. **Recordings everywhere** — S-34, S-35, S-36.
7. **Deep tools** — S-32 (filter playground), S-39, S-38, S-37, S-43.
8. **Run every example** — S-50, then S-18 recipes on top of it.
9. **Polish** — S-61 and S-62 early if time allows (they are cheap); then S-63 to S-68, S-13,
   S-20 to S-22.

---

## S0 completion log — 2026-10-10

All eight S0 items are done. Evidence, from `sites/xsync`:

- **S-01.** Every runnable command uses `xs` across the 13 manuals, the product page and
  `README.md`. That includes helper lookup at `~/.local/bin/xs`, `--rsync-path=/opt/bin/xs` and
  `build/xs`. Manual page names follow the command (`xs(1)`, `xs-ssh(1)`, …). Prose keeps the
  product name xsync, and `~/.config/xsync/config` keeps its real path. Recordings were
  recaptured from `build/xs` at `1fff2a09ae2c` on Linux: transfer exit 0 with 130 files
  verified by SHA-256, checksum run exit 0, SIGINT exit 20, missing source exit 23.
- **S-02.** The help moved to `docs-inputs/xs-help.txt`, captured by `npm run docs:refresh`.
  That command also regenerates `docs/public/xs.1`, dated by the source commit so it
  reproduces. Option specs are now matched as comma-separated forms, whatever spacing
  follows them. All 88 rows have descriptions; `--rsync-path` and `--compress-level` were
  fixed, and `--blocking-io, --no-blocking-io` and `-s, --protect-args, --secluded-args` were
  split correctly. The generator exits with an error if any row has no description.
  `--version, --help` gets the one curated description (`HELP_DESCRIPTIONS`).
- **S-03.** The tier summary and open-item tables on `development.html` are generated from
  the `backlog.md` tier tables via `docs-inputs/backlog-status.json`. They now show P2 with 10
  done and U-01 closed, and P3 and P4 open with R-01 and F-01 partial. The GUI roadmap is
  kept and labeled external and unchecked (Decision 5).
- **S-04.** `npm run check` fails on a stale fingerprint. It was confirmed to fail against
  the old `ce77da…` README hash before review. `npm run docs:review` records new hashes and
  the date, and `npm run build` warns. The README was re-fingerprinted after checking its
  changes since `4159000`: the Site pointer and benchmark tables, neither covered by a
  curated page yet. `backlog.md` is not fingerprinted any more. Its status content is
  generated, and the derived-input check catches a changed tier table without failing on
  every completion-log entry.
- **S-05.** The exit-code table comes from the `RERR_*` enum (`src/common.h`) and
  `error_kind` (`src/util.cpp`), joined with curated meanings in `EXIT_CODES`. The build fails
  if the source adds or drops a code. 127 and 255 are listed; both statuses and messages were
  reproduced with `-e "sh -c 'exit N'"`. 124 is noted as defined but not returned.
- **S-06.** `docs/.vitepress/site-meta.json` is written from the captured help. The colophon
  shows `xs VERSION 0.1.0`, the sidebar shows `NATIVE PROTOCOL 4`, and the product page parses
  program, version and protocol from `sessions.json`.
- **S-07.** `SITE_BASE` (default `/`) drives the VitePress `base`, the head links, the product
  link and the downloads. `npm run check` builds at `/xsyncv4/` and resolves every internal
  `href`/`src`. A negative test showed the checker reporting 407 out-of-base links when a
  root build is checked as `/xsyncv4/`, and a missing `xs.1` when one is deleted.
- **S-08.** The rebuilds were not reproducible because VitePress indexed pages for search
  concurrently, numbering entries in completion order. `buildConcurrency: 1` fixes this:
  three consecutive builds were byte-identical. `npm run check` rebuilds on a clean tree and
  fails on any `git status` change under `docs/`, `dist/` or `docs-inputs/`.

`npm run check` also verifies that `docs-inputs/` matches the parent sources and `build/xs
--help` (ignoring the git revision), and that the recordings were captured from the same
binary as the help. That second check is part of S-53.

The CLI still prints `remote xsync is not installed` (`src/remote.cpp:2627`). That is a
CLI change outside the Site, left for Decision 1's follow-up.

---

## S1 completion log — 2026-10-10

The manual grew from 13 pages to 24. New pages: Install & releases, Coming from rsync,
Recipes, Itemize & out-format, JSON progress events, Troubleshooting, Protocol &
compatibility, Performance, How it works, Changelog and Contributing. The options
page was rebuilt as well.

Two pieces of infrastructure carry most of S1, and S2 and S3 will reuse them:

- **Markdown pages** in `content/*.md`, merged into the build by frontmatter. They can
  include `<!--generated:NAME-->` sections from `scripts/generated.py` and captured
  examples. This is a first step toward S-60.
- **Captured examples.** `scripts/capture-examples.py` runs 38 documented examples
  against the real binary in disposable sandboxes and records stdout, stderr and the exit
  status in `docs-inputs/examples.json`. Remote examples go through `tests/fakessh.sh`.
  Two of them use a feature-subset helper (`-DXSYNC_PROTOCOL_FEATURES=127`), so the exit-4
  and fallback paths are real. `npm run check` requires the examples, the recordings and
  the help to come from one binary.

Per item:

- **S-10.** `docs/public/options.json` joins `--help` (88 rows), `scripts/option_notes.py`
  and the parser's own tables, which `docs-inputs/option-source.json` derives from
  `src/main.cpp`: 147 accepted names and 65 refused names. The build fails on a `--help`
  option without notes, notes for a removed option, a long name the parser does not
  accept, an unknown feature bit, a duplicate anchor, or a "see" link to a missing page
  or section.
- **S-11.** Every option has a stable anchor (`options.html#delete`, `#z`) and a
  *Details* disclosure: README nuances, implied options, required helper features
  linked to the protocol table, and related sections. A small Vue filter
  (`OptionFilter.vue`) narrows rows by class or platform, by helper feature, or by text;
  without JavaScript every row stays visible. The page also lists 11 accepted spellings
  `--help` omits, and the options delegated to rsync, both read from the parser.
- **S-12.** `docs-inputs/benchmarks.json` is derived from `benchmarks/results/*.json`. It
  covers both runs, `715fa0` (neo/freya over SSH) and the APFS no-op diagnostic, with
  hosts, datasets, medians, the fastest–slowest range, CPU, peak RSS and evidence links.
  Losses are marked as such. The in-progress Congress push is listed as incomplete. The
  historical baseline is labeled. A new run in `benchmarks/results/` appears after
  `npm run docs:refresh`, with no hand edits.
- **S-13.** Three inline SVG diagrams (local engine, remote exchange, life of one file)
  and a source map. The README layout table now lists all 26 source files.
- **S-14.** `docs-inputs/protocol.json` is derived from `src/common.h` and
  `src/remote.cpp`: versions, 34 feature bits, the platform exclusions, 36 frame types, 7
  data records and the frozen protocol-3 option layout. `scripts/protocol_notes.py` adds
  what requests each bit and what happens without it; the build fails when the two
  disagree. Facts were checked against the source. For example, `R_END` carries
  status, not a checksum, and an unsupported option under `--no-fallback` exits 1, not 4.
- **S-15 (partial).** Real output covers every change-code position except
  macOS-only ones: the BSD-flag `f`, and `n`/`b` for creation times. Covered are `<`,
  `>`, `c`, `h`, `.`, `*`, the types `f d L D S`, and `c s t T p o g u a x`. Remaining:
  capture those positions on macOS.
- **S-16.** `docs/public/progress.schema.json` describes all three record types, with
  `additionalProperties: false`. `npm run check` validates the committed recording
  plus fresh local, dry-run, checksum and push streams with a small built-in validator,
  which was negative-tested against five kinds of bad event. The page's field tables are
  generated from the schema.
- **S-17.** A migration page covers the backlog's invocation shapes, a differences
  table, and steps for switching a script. It is fingerprinted against the README until
  Q-13 can generate the differences.
- **S-18.** Eight recipes, all with captured output. The cron and launchd snippets and the
  macOS `-N --fileflags` variant are labeled as not captured.
- **S-19.** Troubleshooting quotes the real text for all three fallback causes, plus exits
  1, 4, 12, 23, 25, 30, 127 and 255.
- **S-20.** The install page covers local install, the Homebrew tap, release outputs and
  `manifest.json`, a captured `--install` run against a host without xs, and a
  helper-lookup flowchart. No releases are published (none exist on GitHub).
- **S-21 (partial).** `CHANGELOG.md` exists at the repository root, written from the
  backlog's completed stories, and the site renders it (`docs-inputs/changelog.md`, kept
  current by `npm run check`). Versioned manuals wait for the first tag.
- **S-22.** The contributing page has build and test commands, a test matrix grouped by
  area with what each test needs, all 26 source files, and the maintenance workflow for
  this site.

Verification: `npm run check` passes, including links at `/` and `/xsyncv4/`. A
Chromium pass found no console errors and no horizontal overflow at 375 px on the
architecture, performance and options pages. The option filter counts were 88 total,
26 needing a helper feature, 2 macOS-only and 5 matching "delete".

**S-08 follow-up.** The repository-root `.gitignore` ignores every `dist/` directory, so
new files under `sites/xsync/dist` were silently left out of commits, and `git status` did
not show them. `sites/xsync/.gitignore` now re-includes `dist/`, and `npm run check` fails if
any output under `dist/`, `docs/*.md`, `docs/public/` or `docs-inputs/` is ignored. This
was negative-tested.

Two CLI issues turned up while capturing, and both were queued as suggested tasks rather
than changed here: diagnostics still said "remote xsync", and an older helper prints its
own "connection unexpectedly closed (code 12)" lines before the client's real
message. The first is now fixed (`d3a49f8`): the missing-helper, shell-banner and
wrong-magic diagnostics say `xs`, `tests/fallback_test.py` asserts their wording, and
the site's examples and recordings were recaptured. Decision 1 is resolved, and so is
its CLI follow-up.
