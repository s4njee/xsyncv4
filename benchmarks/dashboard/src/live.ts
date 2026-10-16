// The live feed: one WebSocket to server/index.mjs, reconnecting with backoff,
// holding the latest state and telling subscribers when it changes.
import type { DashEvent, State } from './types';

type Listener = (state: State, changed: { kind: string; key?: string }) => void;
type Status = 'connecting' | 'live' | 'reconnecting';

export class Live {
  state: State = { config: null, runners: {}, hosts: {}, results: [], events: [], speed: {}, started: 0 };
  status: Status = 'connecting';
  lastMessage = 0;
  private listeners = new Set<Listener>();
  private statusListeners = new Set<(status: Status) => void>();
  private eventListeners = new Set<(event: DashEvent) => void>();
  private socket: WebSocket | null = null;
  private retry = 0;
  private closed = false;

  connect(): void {
    const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
    const socket = new WebSocket(url);
    this.socket = socket;
    socket.addEventListener('open', () => {
      this.retry = 0;
      this.setStatus('live');
    });
    socket.addEventListener('message', (message) => this.receive(JSON.parse(message.data)));
    socket.addEventListener('close', () => {
      if (this.closed) return;
      this.setStatus('reconnecting');
      const delay = Math.min(15000, 500 * 2 ** this.retry++);
      setTimeout(() => this.connect(), delay);
    });
  }

  close(): void {
    this.closed = true;
    this.socket?.close();
  }

  onChange(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onStatus(listener: (status: Status) => void): () => void {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => this.statusListeners.delete(listener);
  }

  onEvent(listener: (event: DashEvent) => void): () => void {
    this.eventListeners.add(listener);
    return () => this.eventListeners.delete(listener);
  }

  private setStatus(status: Status): void {
    this.status = status;
    for (const listener of this.statusListeners) listener(status);
  }

  private notify(kind: string, key?: string): void {
    this.lastMessage = Date.now();
    for (const listener of this.listeners) listener(this.state, { kind, key });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private receive(payload: any): void {
    if (payload.type === 'state') {
      this.state = payload.state;
      this.notify('all');
    } else if (payload.type === 'event') {
      this.state.events.unshift(payload.event);
      this.state.events.length = Math.min(this.state.events.length, 200);
      for (const listener of this.eventListeners) listener(payload.event);
      this.notify('event');
    } else if (payload.type === 'update') {
      const message = payload.message;
      if (message.type === 'config') this.state.config = message;
      else if (message.type === 'runner') this.state.runners[message.driver] = message;
      else if (message.type === 'host') this.state.hosts[message.host] = message;
      else if (message.type === 'results') this.state.results = message.experiments;
      else if (message.type === 'speed') {
        const driver = (this.state.speed[message.driver] ??= {});
        const series = (driver[message.iface] ??= []);
        series.push([message.utc, message.rx_bps, message.tx_bps]);
        if (series.length > 90) series.splice(0, series.length - 90);
      }
      this.notify(message.type, message.driver ?? message.host);
    }
  }
}
