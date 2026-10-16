import { defineConfig, type Plugin } from 'vite';
import { spawn, type ChildProcess } from 'node:child_process';
import { copyFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';

// HoloCSS's classic theme script must run before first paint, so it is served as a plain file.
const require = createRequire(import.meta.url);
mkdirSync('public', { recursive: true });
copyFileSync(require.resolve('@mk7s/holocss/theme/bootstrap.js'), 'public/theme-bootstrap.js');

// In development the WebSocket server runs beside Vite, so one command starts both.
function feedServer(): Plugin {
  let child: ChildProcess | null = null;
  return {
    name: 'xs-bench-feed',
    apply: 'serve',
    configureServer() {
      if (process.env.XSDASH_NO_SERVER) return;
      child = spawn(process.execPath, ['server/index.mjs'], { stdio: 'inherit' });
      const stop = () => child?.kill();
      process.once('exit', stop);
      process.once('SIGINT', () => { stop(); process.exit(0); });
      process.once('SIGTERM', () => { stop(); process.exit(0); });
    },
  };
}

// `pnpm dev`: Vite serves the page and forwards the live feed and results to server/index.mjs.
export default defineConfig({
  plugins: [feedServer()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    // HoloCSS and HoloChart are linked from sibling checkouts outside this folder.
    fs: { allow: ['.', '../../../holocss', '../../../holochart'] },
    proxy: {
      '/ws': { target: 'ws://127.0.0.1:8787', ws: true },
      '/api': 'http://127.0.0.1:8787',
    },
  },
  build: { outDir: 'dist', emptyOutDir: true, chunkSizeWarningLimit: 4000 },
});
