import { cp, rm } from 'node:fs/promises';
await rm('dist/docs', { recursive: true, force: true });
await cp('docs/.vitepress/dist', 'dist/docs', { recursive: true });
console.log('VitePress documentation installed at dist/docs/');
