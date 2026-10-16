// HoloChart, themed from HoloCSS. One small chart type the dashboard needs: a
// "forest" of ratios to the control, one row per cell and arm, with the 95%
// interval where there is one and a reference line at 1 (no difference).
import { composeTemplates, createChart, holochartTemplate, type Chart, type FigureInput } from '@mk7s/holochart';
import { chartTheme, watchChartTheme, type ChartTheme } from '@mk7s/holocss/holochart';

export interface ForestRow {
  label: string;
  ratio: number;
  lo: number | null;
  hi: number | null;
  status: string; // HoloCSS status: success, danger, info, warning, neutral
  n: number;
}

const STATUS_COLOR: Record<string, string> = {
  success: '#16a34a', danger: '#dc2626', warning: '#d97706', info: '#2563eb',
};

// Every chart shares one WebGL context with the others, and keeps the same config,
// which would otherwise re-create its renderer on each update.
const CONFIG = { responsive: true, displayModeBar: false, sharedRenderer: true, antialias: true, powerPreference: 'default' } as const;

export class ForestChart {
  private chart: Chart | null = null;
  private stop: (() => void) | null = null;
  private rows: ForestRow[] = [];
  private theme: ChartTheme;
  private failed = false;

  constructor(private host: HTMLElement) {
    this.theme = chartTheme(host);
  }

  update(rows: ForestRow[]): void {
    this.rows = rows;
    this.host.style.setProperty('--dash-rows', String(Math.max(3, rows.length)));
    if (this.failed) return;
    const figure = this.figure();
    if (!this.chart) {
      try {
        this.chart = createChart(this.host, figure);
      } catch {
        // No WebGL2: HoloChart leaves its own note in the element; the table beside it still has the numbers.
        this.failed = true;
        return;
      }
      this.stop = watchChartTheme(this.host, (theme) => {
        this.theme = theme;
        void this.chart?.react(this.figure());
      });
    } else void this.chart.react(figure);
  }

  destroy(): void {
    this.stop?.();
    this.chart?.destroy();
    this.chart = null;
    this.stop = null;
  }

  private figure(): FigureInput {
    const rows = this.rows;
    const muted = this.theme.colors?.muted ?? '#888';
    const accent = getComputedStyle(this.host).getPropertyValue('--dash-blue').trim() || '#1f6bff';
    const colors = rows.map((r) => STATUS_COLOR[r.status] ?? accent);
    const intervals = rows.some((r) => r.lo != null && r.hi != null);
    const lows = rows.map((r) => r.lo ?? r.ratio), highs = rows.map((r) => r.hi ?? r.ratio);
    const span = Math.max(1.25, ...highs, ...rows.map((r) => 1 / Math.min(r.ratio, r.lo ?? r.ratio)));
    return {
      data: [{
        type: 'scatter', mode: 'markers', name: 'ratio',
        x: rows.map((r) => r.ratio),
        y: rows.map((r) => r.label),
        marker: { color: colors, size: 9 },
        ...(intervals ? { error_x: { type: 'data', symmetric: false, array: rows.map((r, i) => highs[i] - r.ratio),
          arrayminus: rows.map((r, i) => r.ratio - lows[i]), color: muted, thickness: 1.5, width: 4 } } : {}),
        customdata: rows.map((r) => [r.n, r.lo ?? '', r.hi ?? '']),
        hovertemplate: intervals ? '%{y}<br>ratio %{x:.3f} [%{customdata[1]:.3f}, %{customdata[2]:.3f}]<br>%{customdata[0]} blocks<extra></extra>'
          : '%{y}<br>ratio %{x:.3f} over %{customdata[0]} blocks<extra></extra>',
      }],
      layout: {
        template: composeTemplates(holochartTemplate, this.theme.template),
        xaxis: { type: 'log', range: [Math.log10(1 / span), Math.log10(span)], title: { text: 'ratio to control (log)' }, zeroline: false },
        yaxis: { autorange: 'reversed', automargin: true },
        shapes: [{ type: 'line', xref: 'x', yref: 'paper', x0: 1, x1: 1, y0: 0, y1: 1, line: { dash: 'dash', width: 1, color: muted } }],
        margin: { l: 16, r: 16, t: 8, b: 44 },
        showlegend: false,
      },
      config: CONFIG,
    } as unknown as FigureInput;
  }
}

// The live link-speed strip on each runner card: receive (filled) and send over the last 90
// seconds. Gigabit links keep a fixed 0-1 Gb/s axis; faster links step through 1, 2.5, 5 and
// 10 Gb/s, taking the smallest step that holds the window's highest point, so a quiet 10GbE
// link is still readable. Each update animates: the points slide left with the time axis as
// the new second arrives, and a change of step rescales smoothly.
const STEPS = [1, 2.5, 5, 10];

export class SpeedChart {
  private chart: Chart | null = null;
  private stop: (() => void) | null = null;
  private series: [number, number, number][] = [];
  private gbps = 1;
  private theme: ChartTheme;
  private failed = false;

  constructor(private host: HTMLElement) {
    this.theme = chartTheme(host);
  }

  update(series: [number, number, number][], linkMbps: number | undefined): void {
    this.series = series;
    // The link's own ceiling, in Gb/s; unknown links get the gigabit axis.
    const link = Math.max(1, (linkMbps ?? 1000) / 1000);
    const peak = Math.max(0, ...series.map(([, rx, tx]) => Math.max(rx, tx))) / 1e9;
    this.gbps = STEPS.find((step) => step >= link || step >= peak * 1.05) ?? link;
    if (this.failed || !series.length) return;
    const figure = this.figure(true);
    if (!this.chart) {
      try {
        this.chart = createChart(this.host, this.figure(false));
      } catch {
        this.failed = true;
        this.host.hidden = true;
        return;
      }
      this.stop = watchChartTheme(this.host, (theme) => {
        this.theme = theme;
        void this.chart?.react(this.figure(false));
      });
    } else void this.chart.react(figure);
  }

  destroy(): void {
    this.stop?.();
    this.chart?.destroy();
    this.chart = null;
    this.stop = null;
  }

  private figure(animate: boolean): FigureInput {
    const style = getComputedStyle(this.host);
    const blue = style.getPropertyValue('--dash-blue').trim() || '#1f6bff';
    const cyan = style.getPropertyValue('--dash-cyan').trim() || '#22d3ee';
    const muted = this.theme.colors?.muted ?? '#888';
    const series = this.series;
    const now = series[series.length - 1][0];
    const x = series.map(([utc]) => utc);
    const gb = (index: 1 | 2) => series.map((point) => point[index] / 1e9);
    const top = this.gbps;
    const ticks = [0, top / 2, top];
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    return {
      data: [
        { type: 'scatter', mode: 'lines', name: 'receive', x, y: gb(1), fill: 'tozeroy',
          line: { color: blue, width: 2, shape: 'linear' }, fillcolor: alpha(blue, 0.28),
          hovertemplate: '↓ %{y:.2f} Gb/s<extra></extra>' },
        { type: 'scatter', mode: 'lines', name: 'send', x, y: gb(2),
          line: { color: cyan, width: 1.5, shape: 'linear' },
          hovertemplate: '↑ %{y:.2f} Gb/s<extra></extra>' },
      ],
      layout: {
        template: composeTemplates(holochartTemplate, this.theme.template),
        showlegend: false,
        margin: { l: 30, r: 4, t: 8, b: 8 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        hovermode: 'x unified',
        xaxis: { range: [now - 89, now], showticklabels: false, ticks: '', showgrid: false, showline: false, zeroline: false, fixedrange: true },
        yaxis: { range: [-top * 0.03, top * 1.03], fixedrange: true, ticks: '', showline: false, tickvals: ticks, ticktext: ticks.map((t) => `${t}G`),
          tickfont: { size: 9, color: muted }, gridcolor: alpha(muted, 0.22), zeroline: false },
        ...(animate && !reduced ? { transition: { duration: 700, easing: 'cubic-in-out' } } : {}),
      },
      config: CONFIG,
    };
  }
}

// A CSS colour (#rgb, #rrggbb or rgb()) at the given opacity, as rgba() the renderer reads.
function alpha(color: string, opacity: number): string {
  let rgb: number[] | undefined;
  const hex = color.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const h = hex[1].length === 3 ? [...hex[1]].map((c) => c + c).join('') : hex[1];
    rgb = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  } else {
    const m = color.match(/rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/);
    if (m) rgb = [m[1], m[2], m[3]].map(Number);
  }
  return rgb ? `rgba(${rgb.join(',')},${opacity})` : color;
}

// Any chart drawn from a figure function, re-drawn when the theme changes. `draw` makes the
// figure from the current HoloChart theme; later draws animate when `transition` is set.
export class Plot {
  private chart: Chart | null = null;
  private stop: (() => void) | null = null;
  private theme: ChartTheme;
  private draw: ((theme: ChartTheme) => FigureInput) | null = null;
  private failed = false;

  constructor(private host: HTMLElement) {
    this.theme = chartTheme(host);
  }

  show(draw: (theme: ChartTheme) => FigureInput, transition = true): void {
    this.draw = draw;
    if (this.failed) return;
    const figure = withConfig(draw(this.theme));
    if (!this.chart) {
      try {
        this.chart = createChart(this.host, figure);
      } catch {
        this.failed = true;
        return;
      }
      this.stop = watchChartTheme(this.host, (theme) => {
        this.theme = theme;
        if (this.draw) void this.chart?.react(withConfig(this.draw(theme)));
      });
      return;
    }
    const animate = transition && !matchMedia('(prefers-reduced-motion: reduce)').matches;
    void this.chart.react(animate ? { ...figure, layout: { ...figure.layout, transition: { duration: 450, easing: 'cubic-in-out' } } } : figure);
  }

  destroy(): void {
    this.stop?.();
    this.chart?.destroy();
    this.chart = null;
    this.stop = null;
  }
}

function withConfig(figure: FigureInput): FigureInput {
  return { ...figure, config: CONFIG };
}

export { alpha, composeTemplates, holochartTemplate };
export type { ChartTheme };
