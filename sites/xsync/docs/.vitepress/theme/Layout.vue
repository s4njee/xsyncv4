<script setup>
import DefaultTheme from 'vitepress/theme';
import { useData } from 'vitepress';
const { frontmatter } = useData();
</script>
<template>
  <DefaultTheme.Layout>
    <template #nav-bar-title-after><span class="nav-manual-tag">/ MANUAL</span></template>
    <template #nav-bar-content-after><a class="product-link" href="/" target="_self">Product <span aria-hidden="true">↗</span></a></template>
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
