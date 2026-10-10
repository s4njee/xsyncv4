<script setup>
// Draws one Holochart figure from a generated JSON file in docs/public/charts/.
// The script loads once per page view; the figure's caption and data table render without it.
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { withBase } from 'vitepress';

const props = defineProps({
  set: { type: String, required: true },
  chart: { type: String, required: true },
  height: { type: Number, default: 340 },
  label: { type: String, default: '' },
});
const el = ref(null);
const failed = ref(false);
let instance = null;

function loadHolochart() {
  if (window.Holochart) return Promise.resolve(window.Holochart);
  window.__xsyncHolochart ??= new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = withBase('/vendor/holochart/holochart.iife.min.js');
    script.onload = () => resolve(window.Holochart);
    script.onerror = reject;
    document.head.appendChild(script);
  });
  return window.__xsyncHolochart;
}

function loadSet(name) {
  window.__xsyncChartSets ??= {};
  window.__xsyncChartSets[name] ??= fetch(withBase(`/charts/${name}.json`)).then((r) => r.json());
  return window.__xsyncChartSets[name];
}

onMounted(async () => {
  try {
    const [Holochart, figures] = await Promise.all([loadHolochart(), loadSet(props.set)]);
    const full = figures[props.chart];
    if (!el.value || !full) throw new Error(`unknown chart ${props.chart}`);
    const figure = full.narrow && el.value.clientWidth < 560 ? full.narrow : full;
    instance = Holochart.createChart(el.value, {
      data: figure.data,
      layout: figure.layout,
      config: { responsive: true, displayModeBar: false, scrollZoom: false },
    });
  } catch (error) {
    failed.value = true;
    console.warn('[xsync] chart unavailable:', error);
  }
});

onBeforeUnmount(() => instance?.destroy());
</script>

<template>
  <div class="holochart-frame" :style="{ height: `${height}px` }">
    <div v-if="!failed" ref="el" class="holochart-canvas" role="img" :aria-label="`${label || chart}. The numbers are in the table below.`"></div>
    <p v-else class="holochart-fallback">This chart needs WebGL. The numbers are in the table below.</p>
  </div>
</template>
