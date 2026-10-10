// Refresh the retained, standalone runtime from the user's local HoloGPU checkout.
import { build } from 'esbuild';
import { mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
const sourceRoot = process.argv[2];
if (!sourceRoot) throw new Error('Usage: node scripts/vendor-hologpu.mjs /absolute/path/to/hologpu');
const source = path.resolve(sourceRoot);
const out = path.resolve('dist/vendor/hologpu');
await mkdir(out, { recursive: true });
await build({
  stdin: {
    contents: `export { createEffect } from '@mk7s/hologpu-core';\nexport { DomRectsInput } from '@mk7s/hologpu-dom';\nexport { default as fluidObstacles } from ${JSON.stringify(source + '/packages/effects/src/fluid-obstacles/index.ts')};`,
    resolveDir: source,
    loader: 'ts',
    sourcefile: 'xsync-hologpu-runtime.ts'
  },
  alias: {
    '@mk7s/hologpu-core': source + '/packages/core/src/index.ts',
    '@mk7s/hologpu-dom': source + '/packages/dom/src/index.ts',
    '@mk7s/hologpu-effects': source + '/packages/effects/src/index.ts'
  },
  bundle: true, format: 'esm', target: 'es2022', minify: true,
  outfile: out + '/fluid-runtime.js',
  banner: { js: '// HoloGPU runtime, vendored from the local research/hologpu checkout. See PROVENANCE.md.' }
});
for (const old of ['runtime.js', 'attractor-dom-effect.ts', 'attractor-effect.js']) {
  await rm(path.join(out, old), { force: true });
}
console.log('Vendored HoloGPU DOM fluid solver and runtime.');
