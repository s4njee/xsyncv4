# xsync product page

A grayscale product page with sans serif type and recordings of actual xsync terminal output. Served from `dist/`.

```sh
python3 -m http.server 4173 --directory dist --bind 127.0.0.1
```

Open http://127.0.0.1:4173. Replay and scrub captured terminal frames, choose recorded scanning/transfer/checksum/completion/interruption/error examples, or inspect original JSON events. Playback does not access visitor files or establish SSH connections.

Recordings in `dist/recordings/` were captured from the parent repository's actual `build/xs` binary against disposable local fixtures. The successful copy includes 130 files, verified with SHA-256 after the transfer. The capture preserves original output text, stripping only terminal cursor/control escapes for display; original `.ansi` captures and timestamped transcripts remain downloadable. JSON comes from a separate real `--progress=json` run. Runtime measurements reflect the capture machine and the explicit bandwidth limit, not a performance benchmark.

Regenerate recordings with:

```sh
python3 scripts/capture-output.py                      # uses ../../build/xs
python3 scripts/capture-output.py --binary /path/to/xs
```

HoloCSS core motion, runtime, keyframes, and view transitions are vendored from `/Users/sanjee/projects/holocss/dist/`, with its MIT license retained in `dist/vendor/holocss/LICENSE`. No network dependencies are needed by the page.

## Documentation

The `/docs/` view uses **VitePress 1.6.4**, the same version used by the local Holochart docs app. It extends the VitePress default theme with the product page’s grayscale palette, sans serif typography, compact manpage sections, and HoloCSS entrances. VitePress supplies local search, sidebar navigation, section outlines, and copyable command blocks.

```sh
npm ci
npm run build
npm run preview
```

The build regenerates 13 Markdown manuals, runs the VitePress static build, then copies it into `dist/docs/` alongside the existing product page. For docs authoring, use `npm run docs:generate` followed by `npm run docs:dev`. Curated content lives in `scripts/docs_content.py`; option descriptions come directly from `docs-inputs/xs-help.txt`. Exit codes (`docs-inputs/exit-codes.json`) are derived from the `RERR_*` definitions in `src/`, and the development status tables (`docs-inputs/backlog-status.json`) from the tier tables in `backlog.md`. These inputs, the recordings and the generated `docs/public/xs.1` are committed so this Site can build independently of the C++ checkout.

Refresh the derived inputs after changing the CLI, exit codes or backlog status:

```sh
(cd ../.. && cmake --build build)
npm run docs:refresh      # help, manpage, exit codes and backlog status from ../../build/xs and ../..
python3 scripts/capture-output.py   # when output changed; recordings must match the help's binary
npm run build
```

Commands on the Site use the executable name `xs`; prose uses the product name xsync.

The output and error pages embed the actual existing recordings. Planned GUI stories remain clearly separate from implemented CLI capabilities; the GUI backlog is maintained outside this repository and is not checked.

### Checks

```sh
npm run check
```

Run this before committing Site changes. It fails when:

- a fingerprinted source in `docs/public/sources.json` (currently the parent `README.md`) changed since the curated pages were reviewed. Re-read the pages it names, update them, then run `npm run docs:review` to record the new fingerprints and review date;
- `docs-inputs/` no longer matches the parent sources or `../../build/xs --help` (run `npm run docs:refresh`);
- the recordings and the help were captured from different binaries;
- `npm run build` does not reproduce the committed `docs/` and `dist/` exactly. This check runs only on a clean tree, so commit first, then run it;
- an internal link or download does not resolve, either at `/` or when the Site is served from a subpath.

`npm run build` itself only warns about stale fingerprints. Checks that need the parent repository or a built `xs` are skipped with a notice when those are absent.

### Serving from a subpath

The Site assumes it is served from the domain root, with the manual at `/docs/`. To serve it elsewhere, for example a GitHub Pages project site, build with `SITE_BASE`:

```sh
SITE_BASE=/xsyncv4/ npm run build
```

The product page uses relative links and needs no change. Commit only the default root build.

## Product-page fluid motion

The main page alone mounts HoloGPU’s **DOM fluid** demo, using the original `fluid-obstacles` stable-fluid solver. Blue and orange dye advects through a velocity field; real heading, navigation, text and panel rectangles form solid obstacles. Pointer movement stirs the fluid in open space. The retained standalone solver/runtime is in `dist/vendor/hologpu/` with source provenance.

`dist/fluid-motion.js` owns mounting, pause/play, OS reduced-motion handling, and disposal. Browsers without WebGPU keep a static blue/orange background. Mobile uses a smaller fluid grid; the engine sleeps while the document is hidden. VitePress pages have no canvas, fluid import, or DOM bindings.
