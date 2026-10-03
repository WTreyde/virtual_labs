import Phaser from "phaser";
import { PIX, shade, TILE } from "./iso";
import { PixelCanvas, type Pt } from "./pixel";
import type { CatalogItem, Layout } from "./types";

/**
 * Procedural pixel-art sprites. Each sprite kind is a handful of boxes ("voxels") in the item's local
 * frame, sized from the catalog footprint, with decals (windows, screens, LEDs) painted on their faces.
 * They are rasterised at 1/PIX resolution with hard edges and scaled up, so the art follows the
 * real footprint and rotation of every instrument instead of a fixed-size bitmap.
 */

export type SpriteKind =
  | "liquid_handler" | "arm" | "incubator" | "reader" | "lcms" | "crystal_imager" | "centrifuge"
  | "sealer" | "hotel" | "hood" | "mobile" | "operator" | "generic";

const KIND_BY_CAPABILITY: [SpriteKind, string[]][] = [
  ["arm", ["plate_transport_arm", "plate_transport_rail"]],
  ["mobile", ["plate_transport_mobile"]],
  ["lcms", ["lcms", "hplc", "nmr", "protein_purification", "protein_qc"]],
  ["crystal_imager", ["crystal_imaging", "imaging", "xray_diffraction"]],
  ["centrifuge", ["centrifugation", "evaporation"]],
  ["hood", ["ventilated_enclosure", "inert_atmosphere", "reaction", "heating_stirring", "crystal_harvesting"]],
  ["liquid_handler", ["liquid_handling", "reagent_dispensing", "acoustic_dispensing", "powder_dosing", "liquid_dosing", "crystallization_setup", "crystal_soaking"]],
  ["incubator", ["incubation", "cell_culture", "bioreactor", "shaking", "cold_storage", "thermocycling"]],
  ["reader", ["absorbance_read", "fluorescence_read", "luminescence_read", "concentration_measurement", "barcode_reading"]],
  ["sealer", ["plate_sealing", "plate_peeling", "delidding"]],
  ["hotel", ["plate_storage", "compound_storage"]],
];

/** Pick the sprite from capabilities (the schema's `category` is too coarse to draw from). */
export function spriteKind(item: CatalogItem): SpriteKind {
  if (item.transport?.kind === "human") return "operator";
  if (item.transport?.kind === "mobile") return "mobile";
  if (item.transport?.kind === "arm" || item.transport?.kind === "rail") return "arm";
  for (const [kind, caps] of KIND_BY_CAPABILITY) if (item.capabilities.some((c) => caps.includes(c))) return kind;
  return "generic";
}

const DEFAULT_COLOUR: Record<SpriteKind, number> = {
  liquid_handler: 0x4a7bd0, arm: 0x9aa4ad, incubator: 0xd08a4a, reader: 0x5b6b8c, lcms: 0xd9dde2,
  crystal_imager: 0x5a4f8f, centrifuge: 0xc9ced6, sealer: 0x7d8b99, hotel: 0x8d99a6, hood: 0xe6e1d3,
  mobile: 0x3fa7a0, operator: 0xf3f3f3, generic: 0x8899aa,
};

// Fixed palette (PICO-8-ish accents) so details read the same on any body colour.
const C = {
  ink: 0x1b1f24, glass: 0xbfe6f2, screen: 0x10202a, green: 0x3ee07a, cyan: 0x6fe3ff, red: 0xff5a36,
  yellow: 0xf2c94c, wood: 0xb08d5a, steel: 0x5c6670, white: 0xf4f4f4, skin: 0xf1c27d, hair: 0x4a2f1b,
  navy: 0x2c3e64, joint: 0x5a9bd5, purple: 0xc17dff,
};

type Face = "front" | "right" | "back" | "left" | "top";
type Decal = {
  face: Face; u0: number; v0: number; u1: number; v1: number; c: number;
  shape?: "rect" | "ellipse" | "line"; lit?: boolean; pts?: [number, number][];
};
type Vox = { x0: number; y0: number; z0: number; x1: number; y1: number; z1: number; c: number; decals?: Decal[]; outline?: boolean };

/** Box centred on (cx, cy) in the local frame, sx by sy metres, from z0 to z1. */
const cbox = (cx: number, cy: number, sx: number, sy: number, z0: number, z1: number, c: number, decals: Decal[] = [], outline = true): Vox =>
  ({ x0: cx - sx / 2, y0: cy - sy / 2, z0, x1: cx + sx / 2, y1: cy + sy / 2, z1, c, decals, outline });
const d = (face: Face, u0: number, v0: number, u1: number, v1: number, c: number, extra: Partial<Decal> = {}): Decal =>
  ({ face, u0, v0, u1, v1, c, ...extra });

/** Bench slab and legs under bench-mounted items, so they sit on furniture rather than float. */
function bench(w: number, dp: number, B: number): Vox[] {
  if (B < 0.05) return [];
  const W = w + 0.12, D = dp + 0.12, top = cbox(0, 0, W, D, B - 0.05, B, C.wood);
  const legs = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sy]) =>
    cbox((sx * (W - 0.06)) / 2, (sy * (D - 0.06)) / 2, 0.04, 0.04, 0, B - 0.05, C.steel, [], false));
  return [...legs, top];
}

/** The voxel model for one sprite kind. w, dp, h: footprint in metres; B: base height above the floor. */
export function model(kind: SpriteKind, w: number, dp: number, h: number, B: number, colour?: number): Vox[] {
  const body = colour ?? DEFAULT_COLOUR[kind];
  const out = bench(w, dp, B);
  const z1 = B + h;
  const led = (face: Face, u: number, v: number, c = C.green) => d(face, u, v, u + 0.06, v + 0.06, c, { lit: true });
  switch (kind) {
    case "liquid_handler":
      out.push(cbox(0, 0, w, dp, B, z1, body, [
        d("front", 0.07, 0.2, 0.93, 0.86, C.glass),
        d("front", 0.13, 0.22, 0.3, 0.32, C.white), d("front", 0.4, 0.22, 0.57, 0.32, C.yellow), d("front", 0.67, 0.22, 0.85, 0.32, 0xf28bb0),
        d("front", 0.1, 0.72, 0.9, 0.76, C.steel), d("front", 0.44, 0.48, 0.58, 0.74, C.ink),
        d("right", 0.08, 0.2, 0.92, 0.86, C.glass), d("right", 0.2, 0.22, 0.8, 0.32, C.white),
        led("front", 0.84, 0.9),
        d("top", 0.1, 0.1, 0.9, 0.9, shade(body, 1.1)),
      ]));
      break;
    case "arm": {
      const g = 0.6; // reach height of the drawn arm, independent of the tiny catalog footprint
      out.push(
        cbox(0, 0, 0.16, 0.16, B, B + 0.08, 0x3d4650),
        cbox(0, 0, 0.12, 0.12, B + 0.08, B + 0.16, C.joint),
        cbox(0, 0, 0.07, 0.07, B + 0.16, B + g * 0.85, body),
        cbox(0, 0, 0.11, 0.11, B + g * 0.8, B + g, C.joint),
        { x0: 0, y0: -0.035, z0: B + g * 0.84, x1: 0.34, y1: 0.035, z1: B + g * 0.95, c: body, outline: true },
        cbox(0.34, 0, 0.08, 0.08, B + g * 0.68, B + g * 0.97, C.joint),
        cbox(0.34, 0, 0.05, 0.1, B + g * 0.58, B + g * 0.68, C.yellow),
      );
      break;
    }
    case "incubator":
      out.push(cbox(0, 0, w, dp, B, z1, body, [
        d("front", 0.06, 0.05, 0.94, 0.95, shade(body, 1.08)),
        d("front", 0.8, 0.38, 0.87, 0.64, C.ink),
        d("front", 0.12, 0.76, 0.44, 0.9, C.screen), d("front", 0.15, 0.8, 0.36, 0.86, C.green, { lit: true }),
        ...[0.3, 0.45, 0.6].map((v) => d("right", 0.2, v, 0.8, v + 0.05, shade(body, 0.6))),
        d("top", 0.2, 0.2, 0.8, 0.8, shade(body, 0.9)),
      ]));
      break;
    case "reader":
      out.push(cbox(0, 0, w, dp, B, z1, body, [
        d("front", 0.12, 0.28, 0.6, 0.44, C.ink),
        d("front", 0.66, 0.52, 0.9, 0.84, C.screen), d("front", 0.7, 0.62, 0.86, 0.68, C.cyan, { lit: true }),
        led("front", 0.12, 0.7),
        d("top", 0.1, 0.1, 0.9, 0.9, shade(body, 1.08)),
      ]));
      break;
    case "lcms": {
      const trace: [number, number][] = [[0.57, 0.76], [0.66, 0.76], [0.69, 0.88], [0.72, 0.76], [0.88, 0.76]];
      out.push(cbox(0, 0, w, dp, B, z1, body, [
        d("front", 0.06, 0.34, 0.94, 0.34, shade(body, 0.55), { shape: "line" }),
        d("front", 0.06, 0.64, 0.94, 0.64, shade(body, 0.55), { shape: "line" }),
        d("front", 0.08, 0.06, 0.46, 0.28, C.glass),
        d("front", 0.54, 0.7, 0.92, 0.92, C.screen),
        d("front", 0, 0, 0, 0, C.green, { shape: "line", lit: true, pts: trace }),
        led("front", 0.1, 0.42), led("front", 0.1, 0.72, C.yellow),
        ...[0.2, 0.4].map((v) => d("right", 0.15, v, 0.85, v + 0.06, shade(body, 0.7))),
      ]));
      out.push(cbox(-w * 0.15, 0, w * 0.55, dp * 0.5, z1, z1 + 0.03, C.steel));
      [C.cyan, C.yellow, C.white, C.red].forEach((c, i) =>
        out.push(cbox(-w * 0.36 + i * w * 0.14, 0, 0.06, 0.06, z1 + 0.03, z1 + 0.17, c)));
      break;
    }
    case "crystal_imager":
      out.push(cbox(0, 0, w, dp, B, z1, body, [
        d("front", 0.22, 0.3, 0.78, 0.82, 0x23395b, { shape: "ellipse" }),
        d("front", 0.3, 0.38, 0.7, 0.74, C.cyan, { shape: "ellipse", lit: true }),
        d("front", 0.36, 0.6, 0.44, 0.68, C.white, { lit: true }),
        led("front", 0.84, 0.88, C.purple),
        d("right", 0.15, 0.15, 0.85, 0.85, shade(body, 1.1)),
        d("top", 0.15, 0.15, 0.85, 0.85, shade(body, 1.2), { shape: "ellipse" }),
      ]));
      break;
    case "centrifuge":
      out.push(cbox(0, 0, w, dp, B, z1, body, [
        ...[0, 1, 2, 3, 4, 5].map((i) => d("front", 0.06 + i * 0.148, 0.06, 0.06 + (i + 1) * 0.148, 0.18, i % 2 ? C.ink : C.yellow)),
        d("front", 0.62, 0.62, 0.9, 0.82, C.screen), d("front", 0.66, 0.68, 0.86, 0.75, C.red, { lit: true }),
        d("top", 0.1, 0.1, 0.9, 0.9, shade(body, 1.15), { shape: "ellipse" }),
        d("top", 0.32, 0.32, 0.68, 0.68, shade(body, 0.6), { shape: "ellipse" }),
      ]));
      break;
    case "sealer":
      out.push(cbox(0, 0, w, dp, B, z1, body, [
        d("front", 0.15, 0.42, 0.85, 0.56, C.ink),
        d("front", 0.15, 0.62, 0.85, 0.7, C.red, { lit: true }),
        led("front", 0.8, 0.84),
      ]));
      out.push(cbox(0, -dp * 0.15, w * 0.7, 0.08, z1, z1 + 0.06, 0xd8dde3));
      break;
    case "hotel": {
      const n = Math.max(3, Math.min(9, Math.round(h / 0.07)));
      const shelves: Decal[] = [];
      for (let i = 0; i < n; i++) {
        const v0 = 0.06 + (i * 0.88) / n, v1 = v0 + (0.88 / n) * 0.55;
        shelves.push(d("front", 0.12, v0, 0.88, v1, i % 3 === 1 ? C.yellow : 0xdfe3e8));
        shelves.push(d("right", 0.12, v0, 0.88, v1, 0xdfe3e8));
      }
      out.push(cbox(0, 0, w, dp, B, z1, body, [d("front", 0.08, 0.04, 0.92, 0.96, shade(body, 0.55)), d("right", 0.08, 0.04, 0.92, 0.96, shade(body, 0.55)), ...shelves]));
      break;
    }
    case "hood":
      out.push(cbox(0, 0, w, dp, B, z1, body, [
        d("front", 0.06, 0.28, 0.94, 0.86, C.glass),
        d("front", 0.2, 0.44, 0.38, 0.66, C.ink, { shape: "ellipse" }), d("front", 0.62, 0.44, 0.8, 0.66, C.ink, { shape: "ellipse" }),
        d("front", 0.06, 0.08, 0.94, 0.2, shade(body, 0.8)),
        led("front", 0.86, 0.9), d("right", 0.1, 0.28, 0.9, 0.86, C.glass),
      ]));
      out.push(cbox(-w * 0.2, -dp * 0.1, 0.22, 0.22, z1, z1 + 0.18, C.steel));
      break;
    case "mobile":
      out.push(cbox(0, 0, w, dp, B, B + h * 0.6, body, [
        d("front", 0, 0.08, 1, 0.28, C.ink), d("right", 0, 0.08, 1, 0.28, C.ink),
        led("front", 0.45, 0.6, C.cyan),
        d("top", 0.15, 0.15, 0.85, 0.85, shade(body, 0.8)),
      ]));
      out.push(cbox(w * 0.25, 0, 0.1, 0.1, B + h * 0.6, B + h * 0.6 + 0.08, C.ink, [d("front", 0.1, 0.3, 0.9, 0.6, C.cyan, { lit: true })]));
      break;
    case "operator":
      out.push(
        cbox(-0.07, 0, 0.1, 0.1, 0, 0.75, C.navy, [], false), cbox(0.07, 0, 0.1, 0.1, 0, 0.75, C.navy, [], false),
        cbox(0, 0, 0.34, 0.2, 0.55, 1.36, body, [d("front", 0.45, 0.4, 0.55, 0.95, shade(body, 0.75)), d("front", 0.62, 0.7, 0.8, 0.8, C.cyan)]),
        cbox(-0.21, 0, 0.08, 0.1, 0.8, 1.32, body), cbox(0.21, 0, 0.08, 0.1, 0.8, 1.32, body),
        cbox(-0.21, 0, 0.07, 0.08, 0.72, 0.8, C.skin, [], false), cbox(0.21, 0, 0.07, 0.08, 0.72, 0.8, C.skin, [], false),
        cbox(0, 0, 0.2, 0.2, 1.38, 1.62, C.skin, [
          d("front", 0.12, 0.42, 0.88, 0.62, C.cyan, { lit: true }), d("front", 0.25, 0.47, 0.4, 0.58, C.ink), d("front", 0.6, 0.47, 0.75, 0.58, C.ink),
        ]),
        cbox(0, -0.01, 0.22, 0.22, 1.58, 1.7, C.hair),
      );
      break;
    default:
      out.push(cbox(0, 0, w, dp, B, z1, body, [d("front", 0.15, 0.2, 0.85, 0.8, shade(body, 1.1)), led("front", 0.8, 0.86)]));
  }
  return out;
}

// ---- rasterising ---------------------------------------------------------------------------

type Rot = (x: number, y: number) => Pt;
const FACES: Face[] = ["back", "right", "front", "left"];

/** Room-frame AABB of a voxel after rotation (exact for multiples of 90 degrees). */
function aabb(v: Vox, rot: Rot) {
  const cs = [rot(v.x0, v.y0), rot(v.x1, v.y0), rot(v.x1, v.y1), rot(v.x0, v.y1)];
  const xs = cs.map((c) => c.x), ys = cs.map((c) => c.y);
  return { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys), z0: v.z0, z1: v.z1 };
}

/** Painter's order: draw a voxel only once nothing that must be behind it is left. */
function paintOrder(vox: Vox[], rot: Rot): Vox[] {
  const e = 1e-6, boxes = vox.map((v) => ({ v, b: aabb(v, rot) }));
  const behind = (a: ReturnType<typeof aabb>, b: ReturnType<typeof aabb>) =>
    a.z1 <= b.z0 + e || a.x1 <= b.x0 + e || a.y1 <= b.y0 + e;
  const key = (b: ReturnType<typeof aabb>) => b.x0 + b.x1 + b.y0 + b.y1 + b.z0 + b.z1;
  const left = [...boxes], out: Vox[] = [];
  while (left.length) {
    let i = left.findIndex((a) => !left.some((o) => o !== a && behind(o.b, a.b) && !behind(a.b, o.b)));
    if (i < 0) i = left.reduce((best, a, k) => (key(a.b) < key(left[best].b) ? k : best), 0);
    out.push(left.splice(i, 1)[0].v);
  }
  return out;
}

export interface SpriteTexture { key: string; ox: number; oy: number }

/**
 * Rasterise voxels into a Phaser texture. Returns the art-pixel position of the local origin
 * (footprint centre on the floor) so the caller can anchor the image at iso(x, y, 0).
 */
export function bakeVoxels(scene: Phaser.Scene, key: string, vox: Vox[], rotDeg = 0, shadow?: { w: number; d: number }): SpriteTexture {
  const t = TILE / PIX;
  const a = (rotDeg * Math.PI) / 180, ca = Math.cos(a), sa = Math.sin(a);
  const rot: Rot = (x, y) => ({ x: x * ca - y * sa, y: x * sa + y * ca });
  const proj = (p: Pt, z: number): Pt => ({ x: (p.x - p.y) * t * 0.866, y: (p.x + p.y) * t * 0.5 - z * t });

  const all = vox.flatMap((v) => [v.z0, v.z1].flatMap((z) => [rot(v.x0, v.y0), rot(v.x1, v.y0), rot(v.x1, v.y1), rot(v.x0, v.y1)].map((p) => proj(p, z))));
  const ox = Math.ceil(-Math.min(...all.map((p) => p.x))) + 2, oy = Math.ceil(-Math.min(...all.map((p) => p.y))) + 2;
  const W = ox + Math.ceil(Math.max(...all.map((p) => p.x))) + 2, H = oy + Math.ceil(Math.max(...all.map((p) => p.y))) + 2;
  const pc = new PixelCanvas(W, H);
  const at = (p: Pt, z: number): Pt => { const q = proj(p, z); return { x: q.x + ox, y: q.y + oy }; };

  if (shadow) {
    const s = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sy]) => rot((sx * (shadow.w + 0.12)) / 2 + 0.04, (sy * (shadow.d + 0.12)) / 2 + 0.04));
    pc.fillPoly(s.map((p) => at(p, 0)), 0x000000, 0.28);
  }

  for (const v of paintOrder(vox, rot)) {
    const cs = [rot(v.x0, v.y0), rot(v.x1, v.y0), rot(v.x1, v.y1), rot(v.x0, v.y1)];
    const faceMap: Partial<Record<Face, { f: number; pt: (u: number, w: number) => Pt }>> = {};
    for (let i = 0; i < 4; i++) {
      const p = cs[i], q = cs[(i + 1) % 4];
      const nx = q.y - p.y, ny = -(q.x - p.x);
      if (nx + ny <= 1e-9) continue;
      // Reverse the edge so u runs left to right on screen.
      faceMap[FACES[i]] = { f: nx > ny ? 0.72 : 0.92, pt: (u, w) => at({ x: q.x + (p.x - q.x) * u, y: q.y + (p.y - q.y) * u }, v.z0 + (v.z1 - v.z0) * w) };
    }
    const c0 = cs[0], c1 = cs[1], c3 = cs[3];
    faceMap.top = { f: 1.12, pt: (u, w) => at({ x: c0.x + (c1.x - c0.x) * u + (c3.x - c0.x) * w, y: c0.y + (c1.y - c0.y) * u + (c3.y - c0.y) * w }, v.z1) };

    const quad = (pt: (u: number, w: number) => Pt, u0: number, v0: number, u1: number, v1: number) => [pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)];
    for (const [name, fm] of Object.entries(faceMap) as [Face, { f: number; pt: (u: number, w: number) => Pt }][]) {
      const poly = quad(fm.pt, 0, 0, 1, 1);
      pc.fillPoly(poly, shade(v.c, fm.f));
      for (const dc of v.decals ?? []) {
        if (dc.face !== name) continue;
        const col = dc.lit ? dc.c : shade(dc.c, fm.f);
        if (dc.shape === "line") {
          const pts = dc.pts ?? [[dc.u0, dc.v0], [dc.u1, dc.v1]];
          for (let k = 0; k + 1 < pts.length; k++) pc.line(fm.pt(...pts[k]), fm.pt(...pts[k + 1]), col);
        } else if (dc.shape === "ellipse") {
          const cu = (dc.u0 + dc.u1) / 2, cv = (dc.v0 + dc.v1) / 2, ru = (dc.u1 - dc.u0) / 2, rv = (dc.v1 - dc.v0) / 2;
          pc.fillPoly(Array.from({ length: 20 }, (_, k) => fm.pt(cu + ru * Math.cos((k * Math.PI) / 10), cv + rv * Math.sin((k * Math.PI) / 10))), col);
        } else pc.fillPoly(quad(fm.pt, dc.u0, dc.v0, dc.u1, dc.v1), col);
      }
      if (v.outline !== false) pc.outline(poly, shade(v.c, fm.f * 0.5));
    }
  }

  if (scene.textures.exists(key)) scene.textures.remove(key);
  scene.textures.addCanvas(key, pc.toCanvas());
  return { key, ox, oy };
}

/** The room as one baked texture: chequered floor, tinted zones, two back walls and a diorama edge. */
export function bakeRoom(scene: Phaser.Scene, key: string, layout: Layout): SpriteTexture {
  const t = TILE / PIX, { width_m: W, depth_m: D } = layout.room, WALL = 0.8, SLAB = 0.15;
  const proj = (x: number, y: number, z = 0): Pt => ({ x: (x - y) * t * 0.866, y: (x + y) * t * 0.5 - z * t });
  const ox = Math.ceil(D * t * 0.866) + 4, oy = Math.ceil((WALL + 0.1) * t) + 4;
  const pc = new PixelCanvas(Math.ceil((W + D) * t * 0.866) + 8, Math.ceil(((W + D) * 0.5 + WALL + SLAB + 0.1) * t) + 8);
  const at = (x: number, y: number, z = 0): Pt => { const q = proj(x, y, z); return { x: q.x + ox, y: q.y + oy }; };
  const quad = (x0: number, y0: number, x1: number, y1: number, z = 0) => [at(x0, y0, z), at(x1, y0, z), at(x1, y1, z), at(x0, y1, z)];

  // Diorama slab edges (front-right and front-left), then walls, then floor tiles.
  pc.fillPoly([at(W, 0), at(W, D), at(W, D, -SLAB), at(W, 0, -SLAB)], 0x6d6252);
  pc.fillPoly([at(0, D), at(W, D), at(W, D, -SLAB), at(0, D, -SLAB)], 0x8a7d68);
  pc.fillPoly([at(0, 0, WALL), at(W, 0, WALL), at(W, 0), at(0, 0)], 0xcfd8dc);
  pc.fillPoly([at(0, D, WALL), at(0, 0, WALL), at(0, 0), at(0, D)], 0xaebcc3);
  pc.fillPoly([at(0, 0, 0.12), at(W, 0, 0.12), at(W, 0), at(0, 0)], 0x78909c);
  pc.fillPoly([at(0, D, 0.12), at(0, 0, 0.12), at(0, 0), at(0, D)], 0x67808c);
  for (let x = 1; x + 0.8 < W; x += 2) {
    pc.fillPoly([at(x, 0, 0.65), at(x + 0.8, 0, 0.65), at(x + 0.8, 0, 0.3), at(x, 0, 0.3)], 0x8fd3f4);
    pc.line(at(x + 0.4, 0, 0.65), at(x + 0.4, 0, 0.3), 0xe8f6fc);
    pc.outline([at(x, 0, 0.65), at(x + 0.8, 0, 0.65), at(x + 0.8, 0, 0.3), at(x, 0, 0.3)], 0x55707c);
  }
  pc.line(at(0, 0, WALL), at(W, 0, WALL), 0x455a64);
  pc.line(at(0, 0, WALL), at(0, D, WALL), 0x455a64);
  for (let x = 0; x < W - 1e-6; x += 0.5)
    for (let y = 0; y < D - 1e-6; y += 0.5) {
      const even = (Math.round(x * 2) + Math.round(y * 2)) % 2 === 0;
      const q = quad(x, y, Math.min(W, x + 0.5), Math.min(D, y + 0.5));
      pc.fillPoly(q, even ? 0xe2dac2 : 0xd6cdb1);
    }
  const ZONE: Record<string, number> = {
    fume_hood: 0xf2c94c, ventilated: 0xf2994a, bsl2: 0xeb5757, cold_room: 0x56ccf2, cryogen: 0x9b51e0,
    robot_only: 0x2d6cdf, human_only: 0x27ae60, collaborative: 0x6fcf97, walkway: 0x9e9e9e,
  };
  for (const z of layout.zones ?? []) {
    const q = quad(z.min.x, z.min.y, z.max.x, z.max.y), c = ZONE[z.kind] ?? 0xaaaaaa;
    pc.fillPoly(q, c, 0.35);
    pc.outline(q, shade(c, 0.7));
  }
  if (scene.textures.exists(key)) scene.textures.remove(key);
  scene.textures.addCanvas(key, pc.toCanvas());
  return { key, ox, oy };
}
