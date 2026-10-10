<script setup>
import DefaultTheme from 'vitepress/theme';
import { useData } from 'vitepress';
const { frontmatter } = useData();
</script>
<template>
  <DefaultTheme.Layout>
    <template #nav-bar-title-after><span class="nav-manual-tag">/ MANUAL</span></template>
    <template #nav-bar-content-after><a class="github-link" href="https://github.com/s4njee/xsyncv4" target="_blank" rel="noopener noreferrer" aria-label="xsync on GitHub" title="xsync on GitHub"><svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg></a><a class="product-link" href="/" target="_self">Product <span aria-hidden="true">↗</span></a></template>
    <template #doc-before>
      <div class="manual-ruler hcss-entrance hcss-enter-fade" :key="frontmatter.manual"><span>XSYNC USER MANUAL</span><span>SECTION {{ frontmatter.sectionNumber || '01' }}</span></div>
    </template>
    <template #doc-after>
      <div class="manual-colophon"><span>{{ frontmatter.manual }} · VERSION 0.1.0</span><a href="/docs/development.html">Development status ↗</a></div>
    </template>
    <template #sidebar-nav-after>
      <div class="sidebar-meta"><span class="sidebar-status" aria-hidden="true"></span> NATIVE PROTOCOL 4<br><span>macOS + Linux / C++20</span><a href="/docs/xs.1" download>Download manpage ↓</a></div>
    </template>
  </DefaultTheme.Layout>
</template>
