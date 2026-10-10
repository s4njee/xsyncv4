import { defineConfig } from 'vitepress';
import { readFileSync } from 'node:fs';
const sidebar = JSON.parse(readFileSync(new URL('./sidebar.json', import.meta.url), 'utf8'));
// Written by scripts/generate-docs.py from the captured `xs --help` version line.
const xs = JSON.parse(readFileSync(new URL('./site-meta.json', import.meta.url), 'utf8'));
// Where the product page is served. The manual lives under it at docs/.
// For example, SITE_BASE=/xsyncv4/ for a GitHub Pages project site.
const siteRoot = (process.env.SITE_BASE || '/').replace(/\/*$/, '/');
if (!siteRoot.startsWith('/')) throw new Error(`SITE_BASE must be an absolute path: ${siteRoot}`);
const monochrome = {
  name: 'xsync-greyscale', type: 'dark',
  colors: { 'editor.background': '#111111', 'editor.foreground': '#dedede' },
  tokenColors: [
    { scope: ['comment', 'punctuation.definition.comment'], settings: { foreground: '#858585' } },
    { scope: ['string', 'constant', 'keyword', 'variable', 'entity', 'support', 'punctuation'], settings: { foreground: '#dedede' } }
  ]
};
export default defineConfig({
  title: 'xsync_',
  titleTemplate: ':title · xsync manual',
  description: 'The xsync user manual. Parallel local and SSH transfers, familiar rsync commands, and real output.',
  lang: 'en-US',
  base: `${siteRoot}docs/`,
  // Index and render pages one at a time. Parallel indexing numbers search entries in
  // completion order, which changes asset hashes between identical builds.
  buildConcurrency: 1,
  appearance: 'force-dark',
  // Explicit .html URLs also work on plain static hosts.
  cleanUrls: false,
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${siteRoot}favicon.svg` }],
    ['link', { rel: 'stylesheet', href: `${siteRoot}vendor/holocss/entrances.css` }],
    ['meta', { name: 'theme-color', content: '#080808' }],
    ['meta', { name: 'color-scheme', content: 'dark' }]
  ],
  markdown: { theme: monochrome },
  themeConfig: {
    siteRoot,
    xs,
    logo: '/logo.svg',
    nav: [ { text: 'Manual', link: '/' }, { text: 'Options', link: '/options' } ],
    sidebar,
    outline: { level: 2, label: 'ON THIS PAGE' },
    search: { provider: 'local', options: { detailedView: true, translations: { button: { buttonText: 'Search the manual', buttonAriaLabel: 'Search the xsync manual' } } } },
    docFooter: { prev: 'PREVIOUS', next: 'NEXT' },
    sidebarMenuLabel: 'Manual index',
    returnToTopLabel: 'Back to top',
    notFound: { title: 'Manual page not found', quote: 'This path is not in the xsync manual.', linkLabel: 'Return to xsync(1)' }
  }
});
