// A tiny non-antialiased rasteriser. Canvas 2D always smooths polygon edges, which looks blurry
// once scaled up; filling by pixel centres gives the hard stair-step edges of real pixel art.

export type Pt = { x: number; y: number };

export class PixelCanvas {
  readonly data: Uint8ClampedArray<ArrayBuffer>;
  constructor(readonly w: number, readonly h: number) {
    this.data = new Uint8ClampedArray(w * h * 4);
  }

  /** Write one pixel; alpha < 1 blends over what is already there. */
  set(x: number, y: number, rgb: number, alpha = 1) {
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    const i = (y * this.w + x) * 4, d = this.data;
    const r = (rgb >> 16) & 255, g = (rgb >> 8) & 255, b = rgb & 255;
    if (alpha >= 1 || d[i + 3] === 0) {
      d[i] = r; d[i + 1] = g; d[i + 2] = b; d[i + 3] = alpha >= 1 ? 255 : Math.round(alpha * 255);
    } else {
      d[i] += (r - d[i]) * alpha; d[i + 1] += (g - d[i + 1]) * alpha; d[i + 2] += (b - d[i + 2]) * alpha;
    }
  }

  /** Fill every pixel whose centre lies inside the polygon (even-odd rule). */
  fillPoly(pts: Pt[], rgb: number, alpha = 1) {
    const ys = pts.map((p) => p.y);
    const y0 = Math.max(0, Math.floor(Math.min(...ys))), y1 = Math.min(this.h - 1, Math.ceil(Math.max(...ys)));
    for (let y = y0; y <= y1; y++) {
      const cy = y + 0.5, xs: number[] = [];
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], b = pts[(i + 1) % pts.length];
        if ((a.y <= cy && b.y > cy) || (b.y <= cy && a.y > cy)) xs.push(a.x + ((cy - a.y) / (b.y - a.y)) * (b.x - a.x));
      }
      xs.sort((p, q) => p - q);
      for (let k = 0; k + 1 < xs.length; k += 2)
        for (let x = Math.ceil(xs[k] - 0.5); x <= Math.floor(xs[k + 1] - 0.5); x++) this.set(x, y, rgb, alpha);
    }
  }

  /** Bresenham line, endpoints snapped to pixel centres. */
  line(a: Pt, b: Pt, rgb: number) {
    let x0 = Math.floor(a.x), y0 = Math.floor(a.y);
    const x1 = Math.floor(b.x), y1 = Math.floor(b.y);
    const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    let err = dx + dy;
    for (;;) {
      this.set(x0, y0, rgb);
      if (x0 === x1 && y0 === y1) return;
      const e2 = 2 * err;
      if (e2 >= dy) { err += dy; x0 += sx; }
      if (e2 <= dx) { err += dx; y0 += sy; }
    }
  }

  outline(pts: Pt[], rgb: number) {
    pts.forEach((p, i) => this.line(p, pts[(i + 1) % pts.length], rgb));
  }

  toCanvas(): HTMLCanvasElement {
    const c = document.createElement("canvas");
    c.width = this.w; c.height = this.h;
    c.getContext("2d")!.putImageData(new ImageData(this.data, this.w, this.h), 0, 0);
    return c;
  }
}
