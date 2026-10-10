# HoloGPU DOM fluid

Retained from the user-owned local HoloGPU checkout at `/Users/sanjee/projects/research/hologpu`, commit `5718a792379388696681da6c3551ceb351e5d8d1`, on 10 October 2026.

- `fluid-runtime.js`: standalone ESM bundle of the HoloGPU core effect field, DOM rectangles, and original `packages/effects/src/fluid-obstacles/index.ts` solver with its shared `_fluid` implementation.
- Integration follows `apps/playground/src/fluid-dom.ts`: DOM rectangle obstacle input, pointer stirring, fixed quality, 16 pressure iterations, and a bounded GPU submission pipeline.
- xsync’s `fluid-motion.js`: page-specific mounting, blue/orange dye, obstacle selectors, motion controls and cleanup. Uses the engine’s default SDR presentation.

The original solver retains velocity advection, pressure projection, vorticity, dye advection and solid DOM boundaries. No particle/attractor effect is included. No HoloGPU code runs in the VitePress docs. No standalone license was present in this local research checkout; no license claim has been added.

To refresh the retained assets, run `node scripts/vendor-hologpu.mjs /absolute/path/to/hologpu` from the Site root. Normal Site builds use the retained browser file and do not need that checkout.
