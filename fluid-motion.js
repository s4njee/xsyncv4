// HoloGPU's DOM fluid demo: dye flows around actual product-page rectangles.
const canvas = document.querySelector('#fluid-motion');
const toggle = document.querySelector('#motion-toggle');
const motion = matchMedia('(prefers-reduced-motion: reduce)');
let field;
let obstacles;
let cleanup = [];
let generation = 0;
let userPaused = false;

function syncControl() {
  if (!field || motion.matches) return;
  const paused = !field.playing;
  toggle.textContent = paused ? 'Play motion' : 'Pause motion';
  toggle.setAttribute('aria-label', paused ? 'Play decorative fluid motion' : 'Pause decorative fluid motion');
  toggle.setAttribute('aria-pressed', String(paused));
  toggle.hidden = false;
  canvas.dataset.state = paused ? 'paused' : 'live';
}
function dispose() {
  generation++;
  cleanup.forEach(remove => remove());
  cleanup = [];
  obstacles?.dispose();
  field?.destroy();
  field = obstacles = undefined;
  toggle.hidden = true;
  canvas.dataset.state = 'static';
}
async function start() {
  if (!canvas || motion.matches || field || !navigator.gpu) return;
  const version = ++generation;
  try {
    // The GPU engine is fetched only on the main page, when animation is allowed.
    const { createEffect, DomRectsInput, fluidObstacles } = await import('./vendor/hologpu/fluid-runtime.js');
    if (version !== generation || motion.matches) return;
    const next = await createEffect(canvas, fluidObstacles, {
      seed: 7, playing: !userPaused,
      adaptiveQuality: false, dprCap: 1, resolutionScale: 0.75,
      pointerTarget: document.body,
      params: {
        grid: matchMedia('(max-width: 720px)').matches ? 128 : 160,
        iterations: 16, initial: 'vortices', initialAmount: 2.5,
        source: 1.2, force: 0.7, vorticity: 1.4, dissipation: 0.035,
        dyeA: '#168bff', dyeB: '#ff862c', background: '#080808'
      }
    });
    if (version !== generation || motion.matches) { next.destroy(); return; }
    field = next;
    field.session.scheduler.setSubmissionLimit(8);
    obstacles = new DomRectsInput(document.body, {
      coordinateTarget: canvas,
      // Use the terminal's individual rows so its large panel cannot cover the dye source.
      selector: '.site-header, .hero h1, .hero-bottom p, .button, .capabilities, .section-caption, .terminal-chrome, .terminal-command, .output-heading, .recorded-output pre, .demo-controls, .demo-description, .recording-provenance, .states-intro, .feature h3, .feature p, .feature-code, .start-intro, .install-heading, .install-panel pre, .install-note, footer'
    });
    cleanup.push(obstacles.subscribe(() => field?.invalidate()));
    await field.setInput('obstacles', obstacles);
    if (version !== generation || motion.matches) return;
    cleanup.push(field.onChange(() => {
      if (field?.state === 'error') dispose();
      else syncControl();
    }));
    field.reset(7);
    syncControl();
  } catch {
    // Decoration must never prevent the transfer recording or navigation from working.
    if (version === generation) dispose();
  }
}
toggle?.addEventListener('click', () => {
  if (!field) return;
  userPaused = !userPaused;
  if (userPaused) field.pause(); else field.play();
  syncControl();
});
motion.addEventListener('change', () => { if (motion.matches) dispose(); else void start(); });
window.addEventListener('pagehide', event => {
  if (!event.persisted) dispose();
  else field?.pause();
});
window.addEventListener('pageshow', event => {
  if (event.persisted && field && !userPaused && !motion.matches) { field.play(); syncControl(); }
});
void start();
