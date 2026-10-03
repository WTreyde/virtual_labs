// Isometric projection: room metres (x along width, y along depth, z up) -> screen pixels.
export const TILE = 64; // pixels per metre along an iso axis
export const ORIGIN = { x: 0, y: 120 };

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

export function shade(hex: string, f: number): number {
  const n = parseInt(hex.replace("#", ""), 16);
  const ch = (k: number) => Math.min(255, Math.round(((n >> k) & 255) * f));
  return (ch(16) << 16) | (ch(8) << 8) | ch(0);
}
