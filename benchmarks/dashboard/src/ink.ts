// The ink orbit effect from holofx's watertemple, behind the dashboard: luminous
// trails in a WebGPU fluid that circle every element marked data-wt-obstacle
// (the top bar, the runner cards, the host strip). It runs only on the dark
// themes and only where the browser has WebGPU; otherwise the page is unchanged.
// Loaded on demand, so the dashboard never waits for it.

type Host = { canvas: HTMLCanvasElement; pause(): void; resume(): void; destroy(): void; loaded?: { params: Record<string, unknown> } };

const DARK = new Set(['shadcn-dark', 'dark']);

// The effect wants the paper colour as linear RGB.
function linear(css: string): [number, number, number] | undefined {
  const match = css.match(/rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/);
  if (!match) return undefined;
  const channel = (value: string) => {
    const c = Number(value) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return [channel(match[1]), channel(match[2]), channel(match[3])];
}

export async function startInk(stage: HTMLElement): Promise<void> {
  if (!('gpu' in navigator)) return;
  let host: Host | null = null;
  let session: unknown = null;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');

  const dark = () => DARK.has(document.documentElement.dataset.hcssResolvedTheme || document.documentElement.dataset.hcssTheme || '');

  async function mountInk(): Promise<void> {
    const [{ createGpuSession, mount }, { effect }] = await Promise.all([
      import('@mk7s/watertemple'),
      import('@mk7s/watertemple/effects/ink-orbit'),
    ]);
    session ??= await createGpuSession();
    const canvas = document.createElement('canvas');
    canvas.className = 'dash-ink-canvas';
    stage.replaceChildren(canvas);
    const paper = linear(getComputedStyle(document.documentElement).backgroundColor);
    // The demo page's look: luminous RGB trails on a dark ground, cycling red, green and blue.
    host = mount(session as never, canvas, effect as never, {
      initialParams: {
        ...(paper ? { paper } : {}),
        ground: 'dark', palette: 'rgb cycle', vignette: 0, gain: 1.4, sheen: 0,
        heads: 16, ink: 0.5, dyeResolution: '768', demo: 'never', pull: 1, current: 0.05,
      },
      paused: reduced.matches,
      maxDpr: 1.5,
      allowHdr: false,
    }) as unknown as Host;
    document.body.dataset.ink = 'live';
  }

  async function sync(): Promise<void> {
    if (dark()) {
      stage.hidden = false;
      if (!host) {
        try { await mountInk(); } catch { document.body.dataset.ink = 'off'; stage.hidden = true; }
      } else if (!reduced.matches) host.resume();
    } else {
      stage.hidden = true;
      host?.pause();
    }
  }

  // Follow theme changes made from the theme menu or by the operating system.
  new MutationObserver(() => void sync()).observe(document.documentElement, { attributes: true, attributeFilter: ['data-hcss-theme', 'data-hcss-resolved-theme'] });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => void sync());

  // The canvas lies behind the page and gets no pointer of its own: pass movement on so hovering
  // stirs the water. Presses on cards, text and controls are not passed, so clicking still works.
  const forward = (event: PointerEvent) => {
    const canvas = host?.canvas;
    if (!canvas || stage.hidden) return;
    canvas.dispatchEvent(new PointerEvent(event.type, {
      pointerId: event.pointerId, pointerType: event.pointerType, isPrimary: event.isPrimary,
      clientX: event.clientX, clientY: event.clientY, pressure: event.pressure, button: event.button, buttons: event.buttons,
    }));
  };
  const onWater = (target: EventTarget | null) => !(target instanceof Element && target.closest('[data-wt-obstacle], a, button, input, select, label, summary'));
  addEventListener('pointermove', forward, { passive: true });
  addEventListener('pointerdown', (event) => { if (onWater(event.target)) forward(event); });
  addEventListener('pointerup', forward);
  addEventListener('pointercancel', forward);

  // No reason to simulate a fluid nobody can see.
  document.addEventListener('visibilitychange', () => {
    if (!host || stage.hidden) return;
    if (document.hidden) host.pause();
    else if (!reduced.matches) host.resume();
  });

  await sync();
}
