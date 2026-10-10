import { defineConfig } from 'vitepress';
import { readFileSync } from 'node:fs';
const sidebar = JSON.parse(readFileSync(new URL('./sidebar.json', import.meta.url), 'utf8'));
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
  base: '/docs/',
  appearance: 'force-dark',
  // Explicit .html URLs also work on plain static hosts.
  cleanUrls: false,
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    ['link', { rel: 'stylesheet', href: '/vendor/holocss/entrances.css' }],
    ['meta', { name: 'theme-color', content: '#080808' }],
    ['meta', { name: 'color-scheme', content: 'dark' }]
  ],
  markdown: { theme: monochrome },
  themeConfig: {
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
