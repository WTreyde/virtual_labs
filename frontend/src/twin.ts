/**
 * Strand A: the landing hero. A real autonomous lab photo on the left, the same photo turned into pixel art on the
 * right (like our rendered labs), and glowing data lines running between them that break into pixel blocks as they
 * cross into the twin. Everything is drawn client-side from one public-domain photo; no extra assets.
 */

const BASE = (import.meta as any).env?.BASE_URL ?? "/";
const PHOTO = `${BASE}landing/real-lab.jpg`;

export function twinHero(): string {
  return `<figure class="twin-hero" aria-label="A real robotic lab and its pixel-art digital twin">
    <div class="twin-side twin-real"><img src="${PHOTO}" alt="Robotic screening lab: a yellow robot arm between plate handlers and instruments" /><span class="twin-tag">Real lab</span></div>
    <div class="twin-side twin-pixel"><canvas class="twin-pix" aria-hidden="true"></canvas><span class="twin-tag">Digital twin</span></div>
    <canvas class="twin-lines" aria-hidden="true"></canvas>
    <figcaption>Photo: NCATS robotic screening lab, NIH (public domain)</figcaption>
  </figure>`;
}

/** Wire up the hero once its HTML is in the page. Returns a stop function (the lines animate until called). */
export function startTwinHero(root: HTMLElement): () => void {
  const fig = root.querySelector<HTMLElement>(".twin-hero");
  if (!fig) return () => {};
  const img = fig.querySelector("img")!, pix = fig.querySelector<HTMLCanvasElement>(".twin-pix")!;
  const lines = fig.querySelector<HTMLCanvasElement>(".twin-lines")!;
  const ready = img.complete ? Promise.resolve() : new Promise<void>((r) => { img.onload = () => r(); img.onerror = () => r(); });
  ready.then(() => pixelate(img, pix));

  let raf = 0, layer: HTMLCanvasElement | undefined, curves: Curve[] = [];
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const resize = () => {
    const r = fig.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
    lines.width = Math.round(r.width * dpr); lines.height = Math.round(r.height * dpr);
    curves = makeCurves(fig, lines.width / r.width);
    layer = drawLayer(lines.width, lines.height, curves);
    if (reduce) frame(0);
  };
  const frame = (ms: number) => {
    if (!fig.isConnected) return stop(); // the landing was re-rendered or replaced
    if (fig.offsetParent === null) { raf = requestAnimationFrame(frame); return; } // hidden: idle until shown again
    const g = lines.getContext("2d")!;
    g.clearRect(0, 0, lines.width, lines.height);
    if (layer) g.drawImage(layer, 0, 0);
    drawPulses(g, curves, reduce ? 0.35 : ms / 1000);
    if (!reduce) raf = requestAnimationFrame(frame);
  };
  const ro = new ResizeObserver(resize);
  ro.observe(fig);
  resize();
  if (!reduce) raf = requestAnimationFrame(frame);
  function stop() { cancelAnimationFrame(raf); ro.disconnect(); }
  return stop;
}

/** Downsample, posterise and boost the photo so it reads like the game's pixel art; CSS scales it up crisply. */
function pixelate(img: HTMLImageElement, out: HTMLCanvasElement) {
  if (!img.naturalWidth) return;
  const W = 96, H = Math.round((W * img.naturalHeight) / img.naturalWidth);
  out.width = W; out.height = H;
  const g = out.getContext("2d", { willReadFrequently: true })!;
  g.imageSmoothingEnabled = true;
  g.drawImage(img, 0, 0, W, H);
  const data = g.getImageData(0, 0, W, H), p = data.data, LEVELS = 7, step = 255 / (LEVELS - 1);
  for (let i = 0; i < p.length; i += 4) {
    // A little extra saturation and contrast, then snap each channel to a few levels: the "game palette" look.
    const avg = (p[i] + p[i + 1] + p[i + 2]) / 3;
    for (let k = 0; k < 3; k++) {
      const v = (avg + (p[i + k] - avg) * 1.15 - 128) * 1.05 + 128;
      p[i + k] = Math.round(Math.max(0, Math.min(255, v)) / step) * step;
    }
  }
  g.putImageData(data, 0, 0);
  // Dark 1-px rule every 8 cells, a faint tile grid like the scene floor.
  g.fillStyle = "rgba(10, 20, 24, 0.1)";
  for (let x = 0; x < W; x += 8) g.fillRect(x, 0, 1, H);
  for (let y = 0; y < H; y += 8) g.fillRect(0, y, W, 1);
}

type Pt = { x: number; y: number };
type Curve = { a: Pt; b: Pt; c1: Pt; c2: Pt; hue: string; speed: number; phase: number; mid: number; right: number };

/** Lines leave points on the photo's right edge and land on the twin, fanned out vertically. */
function makeCurves(fig: HTMLElement, k: number): Curve[] {
  const f = fig.getBoundingClientRect();
  const real = fig.querySelector(".twin-real")!.getBoundingClientRect(), twin = fig.querySelector(".twin-pixel")!.getBoundingClientRect();
  const x0 = (real.right - f.left - real.width * 0.18) * k, x1 = (twin.left - f.left + twin.width * 0.18) * k;
  const top = (Math.max(real.top, twin.top) - f.top) * k, h = Math.min(real.height, twin.height) * k;
  const mid = (x0 + x1) / 2, right = (twin.left - f.left) * k;
  const N = 7, hues = ["#6fe3ff", "#3ee07a", "#ffd23f", "#6fe3ff", "#c17dff", "#3ee07a", "#6fe3ff"];
  return Array.from({ length: N }, (_, i) => {
    const ya = top + h * (0.14 + (0.72 * i) / (N - 1)), yb = top + h * (0.2 + (0.6 * ((i * 3) % N)) / (N - 1));
    const a = { x: x0, y: ya }, b = { x: x1, y: yb };
    return { a, b, c1: { x: mid - (x1 - x0) * 0.1, y: ya }, c2: { x: mid + (x1 - x0) * 0.1, y: yb }, hue: hues[i], speed: 0.16 + 0.05 * (i % 3), phase: i / N, mid, right };
  });
}

function at(c: Curve, t: number): Pt {
  const u = 1 - t;
  return {
    x: u * u * u * c.a.x + 3 * u * u * t * c.c1.x + 3 * u * t * t * c.c2.x + t * t * t * c.b.x,
    y: u * u * u * c.a.y + 3 * u * u * t * c.c1.y + 3 * u * t * t * c.c2.y + t * t * t * c.b.y,
  };
}

/**
 * The static lines: smooth and glowing up to the middle, then the same curves rasterised at coarser and coarser
 * pixel sizes (3, then 6 screen px) towards the twin, so they visibly turn into pixel art.
 */
function drawLayer(W: number, H: number, curves: Curve[]): HTMLCanvasElement {
  const out = document.createElement("canvas");
  out.width = W; out.height = H;
  const g = out.getContext("2d")!;
  if (!curves.length) return out;
  const mid = curves[0].mid, right = curves[0].right;

  // Smooth half.
  g.save();
  g.beginPath(); g.rect(0, 0, mid, H); g.clip();
  g.lineCap = "round";
  for (const c of curves) {
    g.strokeStyle = c.hue; g.globalAlpha = 0.85; g.lineWidth = 2;
    g.shadowColor = c.hue; g.shadowBlur = 10;
    g.beginPath(); g.moveTo(c.a.x, c.a.y); g.bezierCurveTo(c.c1.x, c.c1.y, c.c2.x, c.c2.y, c.b.x, c.b.y); g.stroke();
    g.shadowBlur = 0;
    g.fillStyle = c.hue; g.beginPath(); g.arc(c.a.x, c.a.y, 3.5, 0, Math.PI * 2); g.fill(); // node on the photo
  }
  g.restore();

  // Pixel half: two bands of increasing block size.
  const bands: [number, number, number][] = [[mid, mid + (right - mid) * 0.55, 3], [mid + (right - mid) * 0.55, W, 6]];
  for (const [xa, xb, P] of bands) {
    const lo = document.createElement("canvas");
    lo.width = Math.ceil(W / P); lo.height = Math.ceil(H / P);
    const l = lo.getContext("2d")!;
    for (const c of curves) {
      l.fillStyle = c.hue;
      for (let i = 0; i <= 400; i++) {
        const p = at(c, i / 400);
        if (p.x < xa - P || p.x > xb + P) continue;
        l.fillRect(Math.floor(p.x / P), Math.floor(p.y / P), 1, 1);
      }
      const e = { x: Math.floor(c.b.x / P), y: Math.floor(c.b.y / P) }; // square node on the twin
      if (c.b.x >= xa && c.b.x <= xb) l.fillRect(e.x - 1, e.y - 1, 3, 3);
    }
    g.save();
    g.beginPath(); g.rect(xa, 0, xb - xa, H); g.clip();
    g.imageSmoothingEnabled = false; g.globalAlpha = 0.95;
    g.drawImage(lo, 0, 0, lo.width * P, lo.height * P);
    g.restore();
  }
  return out;
}

/** Data pulses running along each line: soft glowing dots on the real side, hard square blocks on the twin side. */
function drawPulses(g: CanvasRenderingContext2D, curves: Curve[], s: number) {
  for (const c of curves) {
    for (const off of [0, 0.5]) {
      const t = (s * c.speed + c.phase + off) % 1, p = at(c, t);
      if (p.x < c.mid) {
        g.save();
        g.fillStyle = "#ffffff"; g.shadowColor = c.hue; g.shadowBlur = 14;
        g.beginPath(); g.arc(p.x, p.y, 3, 0, Math.PI * 2); g.fill();
        g.restore();
      } else {
        const P = p.x < c.mid + (c.right - c.mid) * 0.55 ? 3 : 6;
        g.fillStyle = "#ffffff";
        g.fillRect(Math.floor(p.x / P) * P - P, Math.floor(p.y / P) * P - P, P * 2, P * 2);
        g.fillStyle = c.hue;
        g.fillRect(Math.floor(p.x / P) * P - P * 2, Math.floor(p.y / P) * P - P / 2, P, P); // trailing block
      }
    }
  }
}
