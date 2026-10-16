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
    const colors = rows.map((r) => STATUS_COLOR[r.status] ?? muted);
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
