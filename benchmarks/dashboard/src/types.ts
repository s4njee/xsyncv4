// The messages server/index.mjs sends, as collector.py and probe_runner.py build them.

export interface Sample {
  utc: string | null;
  cell: string;
  arm: string;
  block: number;
  attempt: number;
  position: number;
  valid: boolean;
  void: string | null;
  wall_s: number | null;
  durable_s: number | null;
  seconds: number | null;
  bytes: number | null;
  gbps: number | null;
  control: boolean;
  client_cpu: number | null;
  peer_cpu: number | null;
}

export interface PlanSummary {
  run?: string;
  kind?: string;
  experiment?: string;
  hypothesis?: string;
  primary?: string;
  control?: string;
  hours?: [number, number] | null;
  link?: string;
  arms?: string[];
  cells?: number;
  blocks?: number;
  samples?: number;
  writes?: Record<string, number>;
  hosts?: string[];
  steps?: number;
}

export interface CellProgress {
  cell: string;
  arms: Record<string, { n: number; median_s: number; ratio: number | null; pairs: number }>;
}

export interface RecentRun {
  run: string;
  lane?: string;
  state: string;
  detail?: string | null;
  exit?: number;
  finished_utc: string;
  requeued?: boolean;
}

export interface RunnerStatus {
  state: string;
  detail: string | null;
  current: { run: string; lane: string; started_utc: string } | null;
  utc: string;
  pid: number;
  alive: boolean;
  paused: boolean;
  queue_pending: number;
  standing_pending: number;
  standing_every_s: number;
  standing_last_utc: string | null;
  written_24h: Record<string, number>;
  write_budget: Record<string, number>;
  consecutive_failures: number;
  recent: RecentRun[];
}

export interface RunStatus {
  state: string;
  detail: string;
  utc: string;
  samples_done: number;
  samples_planned: number;
}

export interface Snapshot {
  host: string;
  utc: number;
  root: string;
  health: { load: number[] | null; cpus: number; disk_free: number | null; disk_total: number | null };
  runner: RunnerStatus | null;
  current?: {
    run: string;
    lane: string;
    started_utc: string;
    plan: PlanSummary;
    status: RunStatus | null;
    samples: Sample[];
    progress: CellProgress[];
    valid: number;
    voided: number;
  };
  backlog?: { pending: PlanSummary[]; pending_count: number; done_count: number };
  standing?: { pending: PlanSummary[]; pending_count: number; done_count: number };
}

export interface RunnerMessage {
  type: 'runner';
  driver: string;
  links: string[];
  utc: number;
  ok: boolean;
  error: string | null;
  route: string | null;
  snapshot?: Snapshot;
}

export interface HostMessage {
  type: 'host';
  host: string;
  utc: number;
  ok: boolean;
  hostname?: string;
  load?: number[];
  cpus?: number;
  disk_free?: number | null;
  disk_total?: number | null;
  route?: string;
  error?: string;
}

export interface ExperimentIndex {
  group: string;
  experiment: string;
  kind: string;
  metric: string;
  comparisons: number;
  verdicts: Record<string, number>;
  cells: number;
  arms: string[];
  runs: number;
  last_run: string | null;
  mtime: number;
}

export interface ConfigMessage {
  type: 'config';
  drivers: Record<string, string[]>;
  links: Record<string, { hosts: string[]; medium: string; driver?: string; results?: string; initiator?: string }>;
  hosts: Record<string, { name: string; hostname: string; root: string; local?: boolean; helper?: boolean }>;
}

export interface DashEvent {
  utc: number;
  kind: string;
  driver: string | null;
  text: string;
  run?: string;
}

export interface State {
  config: ConfigMessage | null;
  runners: Record<string, RunnerMessage>;
  hosts: Record<string, HostMessage>;
  results: ExperimentIndex[];
  runs?: RunIndex[];
  events: DashEvent[];
  // driver -> interface -> [utc, rx bits/s, tx bits/s], oldest first
  speed: Record<string, Record<string, [number, number, number][]>>;
  // driver -> interface -> negotiated link speed in Mb/s, where the host reports one
  link?: Record<string, Record<string, number>>;
  started: number;
}

export interface Effect {
  cell_id: string;
  corpus: string;
  scenario: string;
  sender: string;
  receiver: string;
  arm: string;
  control: string;
  metric: string;
  primary: boolean;
  n_blocks: number;
  ratio: number;
  lo: number;
  hi: number;
  p: number;
  p_holm?: number;
  verdict: string;
  kind: string;
}

export interface Absolute {
  cell_id: string;
  corpus: string;
  arm: string;
  metric: string;
  n_blocks: number;
  geomean: number;
  lo: number;
  hi: number;
}

export interface ExperimentDetail {
  group: string;
  name: string;
  effects: Effect[];
  absolutes: Absolute[];
  summary: unknown;
  report: string | null;
}

// A past run, as server/runs.mjs reads it from benchmarks/results.
export interface RunIndex {
  key: string; // group/experiment/run
  group: string;
  experiment: string;
  run: string;
  kind: string | null;
  hypothesis: string | null;
  primary: string;
  control: string | null;
  driver: string | null;
  links: string[];
  started: number | null;
  ended: number | null;
  samples: number;
  valid: number;
  voided: number;
  planned: number | null;
  state: string | null;
  arms: string[];
  corpora: string[];
  cells: number;
}

export interface RunCell {
  id: string;
  corpus: string;
  scenario: string;
  sender: string;
  receiver: string;
  client: string;
  link: string;
  cache: string;
  files: number | null;
  bytes: number | null;
}

// One array per field, one entry per sample; cell, arm and rev are indexes.
export interface RunColumns {
  cell: number[];
  arm: number[];
  block: (number | null)[];
  attempt: (number | null)[];
  position: (number | null)[];
  control: number[];
  valid: number[];
  void: (string | null)[];
  utc: (number | null)[];
  wall_s: (number | null)[];
  sync_s: (number | null)[];
  durable_s: (number | null)[];
  client_cpu_s: (number | null)[];
  peer_cpu_s: (number | null)[];
  client_rss: (number | null)[];
  peer_rss: (number | null)[];
  wire_bytes: (number | null)[];
  retransmits: (number | null)[];
  rev: (number | null)[];
}

export interface RunDetail extends Omit<RunIndex, 'arms' | 'cells'> {
  delta: number | null;
  arms: { name: string; tool: string; flags: string[] }[];
  cells: RunCell[];
  revs: string[];
  columns: RunColumns;
}
