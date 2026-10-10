# xsync product page

A grayscale product page with sans serif type and recordings of actual xsync terminal output. Served from `dist/`.

```sh
python3 -m http.server 4173 --directory dist --bind 127.0.0.1
```

Open http://127.0.0.1:4173. Replay and scrub captured terminal frames, choose recorded scanning/transfer/checksum/completion/interruption/error examples, or inspect original JSON events. Playback does not access visitor files or establish SSH connections.

Recordings in `dist/recordings/` were captured from the parent repository's actual `build/xsync` binary against disposable local fixtures. The successful copy includes 130 files, verified with SHA-256 after the transfer. The capture preserves original output text, stripping only terminal cursor/control escapes for display; original `.ansi` captures and timestamped transcripts remain downloadable. JSON comes from a separate real `--progress=json` run. Runtime measurements reflect the capture machine and the explicit bandwidth limit, not a performance benchmark.

Regenerate recordings with:

```sh
python3 scripts/capture-output.py --binary /absolute/path/to/build/xsync
```

HoloCSS core motion, runtime, keyframes, and view transitions are vendored from `/Users/sanjee/projects/holocss/dist/`, with its MIT license retained in `dist/vendor/holocss/LICENSE`. No network dependencies are needed by the page.

## Documentation

The `/docs/` view uses **VitePress 1.6.4**, the same version used by the local Holochart docs app. It extends the VitePress default theme with the product page’s grayscale palette, sans serif typography, compact manpage sections, and HoloCSS entrances. VitePress supplies local search, sidebar navigation, section outlines, and copyable command blocks.

```sh
npm ci
npm run build
npm run preview
```

The build regenerates 13 Markdown manuals, runs the VitePress static build, then copies it into `dist/docs/` alongside the existing product page. For docs authoring, use `npm run docs:generate` followed by `npm run docs:dev`. Curated content lives in `scripts/docs_content.py`; option descriptions come directly from `docs-inputs/xsync-help.txt`. The captured help and generated `docs/public/xs.1` are retained so this Site can build independently of the C++ checkout.

Refresh the authoritative command reference after changing the CLI:

```sh
../../build/xsync --help > docs-inputs/xsync-help.txt
python3 ../../tools/help_to_man.py ../../build/xsync docs/public/xs.1
npm run build
```

The output and error pages embed the actual existing recordings. `docs/public/sources.json` records SHA-256 fingerprints of the README, both backlogs, and exit-code definitions reviewed for the current documentation. Update those fingerprints and the reviewed date when revising development status. Planned GUI stories remain clearly separate from implemented CLI capabilities.

## Product-page fluid motion

The main page alone mounts HoloGPU’s **DOM fluid** demo, using the original `fluid-obstacles` stable-fluid solver. Blue and orange dye advects through a velocity field; real heading, navigation, text and panel rectangles form solid obstacles. Pointer movement stirs the fluid in open space. The retained standalone solver/runtime is in `dist/vendor/hologpu/` with source provenance.

`dist/fluid-motion.js` owns mounting, pause/play, OS reduced-motion handling, and disposal. Browsers without WebGPU keep a static blue/orange background. Mobile uses a smaller fluid grid; the engine sleeps while the document is hidden. VitePress pages have no canvas, fluid import, or DOM bindings.
