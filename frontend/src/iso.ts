// Isometric projection: room metres (x along width, y along depth, z up) -> screen pixels.
export let TILE = 64; // pixels per metre along an iso axis
export const ORIGIN = { x: 0, y: 120 };
/** Sprites are drawn at 1/PIX resolution and scaled up, so every art pixel is PIX screen pixels. */
export const PIX = 3;
/** Bench heights are squashed so instruments sit visibly on the floor rather than floating. */
export const Z_SQUASH = 0.3;

/** Size the projection so a room of W x D metres fills a view of the given pixel size. */
export function fitRoom(W: number, D: number, viewW: number, viewH: number) {
  const fit = Math.min((viewW * 0.9) / ((W + D) * 0.866), (viewH * 0.8) / ((W + D) * 0.5 + 1.4));
  TILE = Math.max(PIX * 8, Math.floor(fit / PIX) * PIX); // multiple of PIX keeps art pixels square
  ORIGIN.x = Math.round(viewW / 2 - ((W - D) * TILE * 0.866) / 2);
  ORIGIN.y = Math.round((viewH - (W + D) * 0.5 * TILE) / 2 + 0.6 * TILE);
}

export function iso(x: number, y: number, z = 0): { x: number; y: number } {
  return { x: ORIGIN.x + (x - y) * TILE * 0.866, y: ORIGIN.y + (x + y) * TILE * 0.5 - z * TILE };
}

/** Corners of a rotated footprint in room coordinates, counter-clockwise. */
export function footprintCorners(cx: number, cy: number, w: number, d: number, rotDeg: number) {
  const a = (rotDeg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sy]) => {
    const lx = (sx * w) / 2, ly = (sy * d) / 2;
    return { x: cx + lx * c - ly * s, y: cy + lx * s + ly * c };
  });
}

export function shade(hex: string | number, f: number): number {
  const n = typeof hex === "number" ? hex : parseInt(hex.replace("#", ""), 16);
  const ch = (k: number) => Math.min(255, Math.round(((n >> k) & 255) * f));
  return (ch(16) << 16) | (ch(8) << 8) | ch(0);
}
