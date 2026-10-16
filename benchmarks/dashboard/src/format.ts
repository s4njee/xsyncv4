// Small formatting helpers; every string that reaches innerHTML goes through esc().

export function esc(value: unknown): string {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}

export function gib(bytes: number | null | undefined, digits = 0): string {
  if (bytes == null) return '—';
  const value = bytes / 2 ** 30;
  return value >= 1024 ? `${(value / 1024).toFixed(1)} TiB` : `${value.toFixed(digits)} GiB`;
}

export function seconds(value: number | null | undefined): string {
  if (value == null) return '—';
  if (value < 1) return `${(value * 1000).toFixed(0)} ms`;
  if (value < 100) return `${value.toFixed(1)} s`;
  return duration(value);
}

export function duration(total: number): string {
  if (!isFinite(total) || total < 0) return '—';
  const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), s = Math.floor(total % 60);
  if (h >= 24) return `${Math.floor(h / 24)} d ${h % 24} h`;
  if (h) return `${h} h ${m.toString().padStart(2, '0')} min`;
  if (m) return `${m} min ${s.toString().padStart(2, '0')} s`;
  return `${s} s`;
}

export function utcToDate(value: string | number | null | undefined): Date | null {
  if (value == null) return null;
  return typeof value === 'number' ? new Date(value * 1000) : new Date(value);
}

export function clock(value: string | number | null | undefined): string {
  const date = utcToDate(value);
  return date ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';
}

export function ago(value: string | number | null | undefined): string {
  const date = utcToDate(value);
  if (!date) return '—';
  const delta = (Date.now() - date.getTime()) / 1000;
  return delta < 5 ? 'just now' : `${duration(delta)} ago`;
}

export function runName(run: string | undefined): string {
  return (run || '').replace(/^\d{8}T\d{6}Z-/, '');
}

// "small-flat.fresh.neo-freya.sender.warm" -> short label for tables and charts.
export function cellLabel(cell: string): string {
  const [corpus, scenario, direction, , cache] = cell.split('.');
  return `${corpus} · ${scenario} · ${direction?.replace('-', '→')}${cache && cache !== 'warm' ? ` · ${cache}` : ''}`;
}

export function rate(gbps: number | null | undefined): string {
  if (gbps == null) return '—';
  return gbps >= 10 ? `${gbps.toFixed(0)} Gb/s` : `${gbps.toFixed(2)} Gb/s`;
}

export const VERDICT_STATUS: Record<string, string> = {
  faster: 'success', slower: 'danger', equivalent: 'info', inconclusive: 'neutral', 'too few blocks': 'neutral',
};
