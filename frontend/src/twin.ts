/**
 * Strand A: the landing hero. Our rendered chemistry case (end of its simulation) on the left, a picture of a real
 * lab on the right, and glowing data lines running between them: blocky pixel art where they leave the twin,
 * sharpening into smooth glowing lines as they reach the real lab. Pulses flow left to right.
 */

const BASE = (import.meta as any).env?.BASE_URL ?? "/";
const TWIN = `${BASE}landing/chem-twin.png`;
const REAL = `${BASE}landing/real-lab.jpg`;

export function twinHero(): string {
  return `<figure class="twin-hero" aria-label="Our pixel-art digital twin of a lab, linked to a real lab">
    <div class="twin-side twin-left"><img class="twin-pix" src="${TWIN}" alt="LabForge's rendered chemistry case at the end of its simulation" /><span class="twin-tag">Digital twin</span></div>
    <div class="twin-side twin-right"><img src="${REAL}" alt="The same chemistry lab built for real: synthesis robots, sample store, LC-MS benches and a technician" /><span class="twin-tag">Real lab</span></div>
    <canvas class="twin-lines" aria-hidden="true"></canvas>
  </figure>`;
}

/** Wire up the hero once its HTML is in the page. Returns a stop function (the lines animate until called). */
export function startTwinHero(root: HTMLElement): () => void {
  const fig = root.querySelector<HTMLElement>(".twin-hero");
  if (!fig) return () => {};
  const lines = fig.querySelector<HTMLCanvasElement>(".twin-lines")!;
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

type Pt = { x: number; y: number };
/** One line from a (on the twin, left) to b (on the real lab, right); `coarse` and `mid` bound the pixel bands. */
type Curve = { a: Pt; b: Pt; c1: Pt; c2: Pt; hue: string; speed: number; phase: number; mid: number; coarse: number };

/** Lines leave points on the twin's right edge and land on the real lab, fanned out vertically. */
function makeCurves(fig: HTMLElement, k: number): Curve[] {
  const f = fig.getBoundingClientRect();
  const left = fig.querySelector(".twin-left")!.getBoundingClientRect(), right = fig.querySelector(".twin-right")!.getBoundingClientRect();
  const x0 = (left.right - f.left - left.width * 0.18) * k, x1 = (right.left - f.left + right.width * 0.18) * k;
  const top = (Math.max(left.top, right.top) - f.top) * k, h = Math.min(left.height, right.height) * k;
  const mid = (x0 + x1) / 2, edge = (left.right - f.left) * k, coarse = edge + (mid - edge) * 0.45;
  const N = 7, hues = ["#6fe3ff", "#3ee07a", "#ffd23f", "#6fe3ff", "#c17dff", "#3ee07a", "#6fe3ff"];
  return Array.from({ length: N }, (_, i) => {
    const ya = top + h * (0.2 + (0.6 * ((i * 3) % N)) / (N - 1)), yb = top + h * (0.14 + (0.72 * i) / (N - 1));
    const a = { x: x0, y: ya }, b = { x: x1, y: yb };
    return { a, b, c1: { x: mid - (x1 - x0) * 0.1, y: ya }, c2: { x: mid + (x1 - x0) * 0.1, y: yb }, hue: hues[i], speed: 0.16 + 0.05 * (i % 3), phase: i / N, mid, coarse };
  });
}

function at(c: Curve, t: number): Pt {
  const u = 1 - t;
  return {
    x: u * u * u * c.a.x + 3 * u * u * t * c.c1.x + 3 * u * t * t * c.c2.x + t * t * t * c.b.x,
    y: u * u * u * c.a.y + 3 * u * u * t * c.c1.y + 3 * u * t * t * c.c2.y + t * t * t * c.b.y,
  };
}

/** Block size of the line at screen x: 6 px by the twin, 3 px nearer the middle, smooth (0) from the middle on. */
const blockAt = (c: Curve, x: number) => (x < c.coarse ? 6 : x < c.mid ? 3 : 0);

/**
 * The static lines: the curves rasterised in coarse, then finer pixel blocks as they leave the twin, then smooth
 * and glowing from the middle to the real lab.
 */
function drawLayer(W: number, H: number, curves: Curve[]): HTMLCanvasElement {
  const out = document.createElement("canvas");
  out.width = W; out.height = H;
  const g = out.getContext("2d")!;
  if (!curves.length) return out;
  const { mid, coarse } = curves[0];

  // Pixel half: two bands, blockiest next to the twin.
  const bands: [number, number, number][] = [[0, coarse, 6], [coarse, mid, 3]];
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
      if (c.a.x >= xa && c.a.x <= xb) l.fillRect(Math.floor(c.a.x / P) - 1, Math.floor(c.a.y / P) - 1, 3, 3); // square node on the twin
    }
    g.save();
    g.beginPath(); g.rect(xa, 0, xb - xa, H); g.clip();
    g.imageSmoothingEnabled = false; g.globalAlpha = 0.95;
    g.drawImage(lo, 0, 0, lo.width * P, lo.height * P);
    g.restore();
  }

  // Smooth, glowing half.
  g.save();
  g.beginPath(); g.rect(mid, 0, W - mid, H); g.clip();
  g.lineCap = "round";
  for (const c of curves) {
    g.strokeStyle = c.hue; g.globalAlpha = 0.85; g.lineWidth = 2;
    g.shadowColor = c.hue; g.shadowBlur = 10;
    g.beginPath(); g.moveTo(c.a.x, c.a.y); g.bezierCurveTo(c.c1.x, c.c1.y, c.c2.x, c.c2.y, c.b.x, c.b.y); g.stroke();
    g.shadowBlur = 0;
    g.fillStyle = c.hue; g.beginPath(); g.arc(c.b.x, c.b.y, 3.5, 0, Math.PI * 2); g.fill(); // round node on the real lab
  }
  g.restore();
  return out;
}

/** Data pulses running left to right: hard square blocks on the twin side, soft glowing dots on the real side. */
function drawPulses(g: CanvasRenderingContext2D, curves: Curve[], s: number) {
  for (const c of curves) {
    for (const off of [0, 0.5]) {
      const t = (s * c.speed + c.phase + off) % 1, p = at(c, t), P = blockAt(c, p.x);
      if (!P) {
        g.save();
        g.fillStyle = "#ffffff"; g.shadowColor = c.hue; g.shadowBlur = 14;
        g.beginPath(); g.arc(p.x, p.y, 3, 0, Math.PI * 2); g.fill();
        g.restore();
      } else {
        const x = Math.floor(p.x / P) * P, y = Math.floor(p.y / P) * P;
        g.fillStyle = "#ffffff";
        g.fillRect(x - P, y - P, P * 2, P * 2);
        g.fillStyle = c.hue;
        g.fillRect(x - P * 2, y - P / 2, P, P); // trailing block, behind the pulse
      }
    }
  }
}
