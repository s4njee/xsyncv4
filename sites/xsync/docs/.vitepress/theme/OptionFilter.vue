<script setup>
// Filters the statically rendered option rows. Without JavaScript every row stays visible.
import { onMounted, ref, watch } from 'vue';

const filters = [
  { id: 'all', label: 'All', test: () => true },
  { id: 'native', label: 'rsync options', test: row => row.dataset.class === 'native' },
  { id: 'xs-only', label: 'xs only', test: row => row.dataset.class === 'xs-only' },
  { id: 'feature', label: 'Needs helper feature', test: row => row.dataset.feature === 'yes' },
  { id: 'macos', label: 'macOS only', test: row => row.dataset.platform === 'macOS' },
  { id: 'no-op', label: 'No-ops', test: row => row.dataset.class === 'no-op' },
];
const active = ref('all');
const query = ref('');
const shown = ref(0);
const total = ref(0);
let rows = [];

function apply() {
  const filter = filters.find(item => item.id === active.value);
  const words = query.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
  shown.value = 0;
  for (const row of rows) {
    const visible = filter.test(row) && words.every(word => row.dataset.search.includes(word));
    row.hidden = !visible;
    if (visible) shown.value++;
  }
  // Hide a section's table when none of its rows match.
  for (const table of document.querySelectorAll('.option-table')) {
    table.closest('.manual-table-wrap').hidden = !table.querySelector('.option-row:not([hidden])');
  }
}

onMounted(() => {
  rows = [...document.querySelectorAll('.option-row')];
  total.value = rows.length;
  apply();
});
watch([active, query], apply);
</script>

<template>
  <div class="option-filter" role="search" aria-label="Filter options">
    <div class="option-filter-buttons" role="group" aria-label="Option class">
      <button v-for="filter in filters" :key="filter.id" type="button" :aria-pressed="String(active === filter.id)" @click="active = filter.id">{{ filter.label }}</button>
    </div>
    <label class="option-filter-search"><span>Search</span><input v-model="query" type="search" placeholder="delete, ssh, acl…" autocomplete="off"></label>
    <p class="option-filter-count" role="status" aria-live="polite">{{ shown }} of {{ total }} options</p>
  </div>
</template>
