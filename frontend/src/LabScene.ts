import Phaser from "phaser";
import { footprintCorners, iso, ORIGIN, shade } from "./iso";
import type { Design } from "./types";

/**
 * Strand A: the isometric lab. Owner: Roshan.
 * v0 draws the room, zones, instruments as shaded iso boxes, transfer paths with moving plates,
 * operators and bottleneck speech bubbles. TODO(Roshan): pixel-art sprites per instrument category,
 * walking operator/robot animations from SimResult.timeline, stat card on click, Pokemon-style UI frame.
 */
export class LabScene extends Phaser.Scene {
  private design!: Design;
  private movers: { dot: Phaser.GameObjects.Arc; pts: { x: number; y: number }[]; t: number; speed: number }[] = [];

  constructor() { super("lab"); }

  init(data: { design: Design }) { this.design = data.design; }

  create() {
    const { layout } = this.design;
    ORIGIN.x = this.scale.width / 2 - ((layout.room.width_m - layout.room.depth_m) * 64 * 0.866) / 2;
    this.drawFloor();
    this.drawZones();
    this.drawEquipment();
    this.drawTransfers();
    this.drawOperators();
    this.drawBottlenecks();
  }

  update(_: number, dtMs: number) {
    for (const m of this.movers) {
      m.t = (m.t + (dtMs / 1000) * m.speed) % 1;
      const seg = m.t * (m.pts.length - 1), i = Math.floor(seg), f = seg - i;
      const a = m.pts[i], b = m.pts[Math.min(i + 1, m.pts.length - 1)];
      m.dot.setPosition(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f);
    }
  }

  private poly(points: { x: number; y: number }[], fill: number, alpha = 1, line = 0x333333) {
    const g = this.add.graphics();
    g.fillStyle(fill, alpha).lineStyle(2, line, 1);
    g.beginPath(); g.moveTo(points[0].x, points[0].y);
    points.slice(1).forEach((p) => g.lineTo(p.x, p.y));
    g.closePath(); g.fillPath(); g.strokePath();
    return g;
  }

  private drawFloor() {
    const { width_m: W, depth_m: D } = this.design.layout.room;
    for (let x = 0; x < W; x += 0.5)
      for (let y = 0; y < D; y += 0.5) {
        const even = (Math.round(x * 2) + Math.round(y * 2)) % 2 === 0;
        this.poly([iso(x, y), iso(x + 0.5, y), iso(x + 0.5, y + 0.5), iso(x, y + 0.5)], even ? 0xd8d0b8 : 0xcfc6ab, 1, 0xbdb398);
      }
  }

  private drawZones() {
    const colours: Record<string, number> = { fume_hood: 0xf2c94c, bsl2: 0xeb5757, cold_room: 0x56ccf2, cryogen: 0x9b51e0 };
    for (const z of this.design.layout.zones ?? []) {
      this.poly([iso(z.min.x, z.min.y), iso(z.max.x, z.min.y), iso(z.max.x, z.max.y), iso(z.min.x, z.max.y)], colours[z.kind] ?? 0xaaaaaa, 0.35);
    }
  }

  private drawEquipment() {
    const { layout, workflow, catalog } = this.design;
    const itemOf = Object.fromEntries(workflow.equipment.map((e) => [e.instance_id, catalog[e.catalog_id]]));
    const sorted = [...layout.placements].sort((a, b) => a.position.x + a.position.y - (b.position.x + b.position.y));
    for (const p of sorted) {
      const item = itemOf[p.instance_id];
      if (!item) continue;
      const { width_m: w, depth_m: d, height_m: h } = item.footprint;
      const base = p.position.z * 0.3; // squash bench height so boxes sit visibly on the floor
      const c = footprintCorners(p.position.x, p.position.y, w, d, p.rotation_deg);
      const colour = item.visual?.color ?? "#8899aa";
      // Side faces whose outward normal points toward the viewer (+x+y), then the top.
      for (let i = 0; i < 4; i++) {
        const a = c[i], b = c[(i + 1) % 4];
        const nx = b.y - a.y, ny = -(b.x - a.x);
        if (nx + ny <= 0) continue;
        const f = nx > ny ? 0.75 : 0.9;
        this.poly([iso(a.x, a.y, base), iso(b.x, b.y, base), iso(b.x, b.y, base + h), iso(a.x, a.y, base + h)], shade(colour, f));
      }
      this.poly(c.map((q) => iso(q.x, q.y, base + h)), shade(colour, 1.1));
      const top = iso(p.position.x, p.position.y, base + h);
      this.add.text(top.x, top.y - 14, p.instance_id, { fontSize: "10px", color: "#111", backgroundColor: "#fffde8" }).setOrigin(0.5);
    }
  }

  private drawTransfers() {
    for (const t of this.design.layout.transfers) {
      if (!t.path?.length) continue;
      const pts = t.path.map((q) => iso(q.x, q.y, q.z * 0.3));
      const g = this.add.graphics().lineStyle(2, t.transporter_instance.startsWith("arm") ? 0x2d6cdf : 0xe08a2d, 0.8);
      g.beginPath(); g.moveTo(pts[0].x, pts[0].y); pts.slice(1).forEach((q) => g.lineTo(q.x, q.y)); g.strokePath();
      const dot = this.add.circle(pts[0].x, pts[0].y, 4, 0xffffff).setStrokeStyle(2, 0x333333);
      this.movers.push({ dot, pts, t: Math.random(), speed: 0.25 });
    }
  }

  private drawOperators() {
    for (const op of this.design.layout.operators ?? []) {
      const s = iso(op.home.x, op.home.y);
      this.add.circle(s.x, s.y - 10, 7, 0xf2994a).setStrokeStyle(2, 0x333333);
      this.add.text(s.x, s.y + 2, op.role, { fontSize: "9px", color: "#111" }).setOrigin(0.5, 0);
    }
  }

  private drawBottlenecks() {
    const where = Object.fromEntries(this.design.layout.placements.map((p) => [p.instance_id, p.position]));
    for (const b of this.design.sim_result.bottlenecks) {
      const pos = b.instances?.[0] && where[b.instances[0]];
      if (!pos) continue;
      const s = iso(pos.x, pos.y, 1.2);
      const aura = this.add.circle(s.x, s.y + 40, 36, 0xe0503c, 0.25);
      this.tweens.add({ targets: aura, alpha: 0.05, yoyo: true, repeat: -1, duration: 700 });
      this.add.text(s.x, s.y - 30, b.message, {
        fontSize: "10px", color: "#111", backgroundColor: "#ffffff", padding: { x: 6, y: 4 }, wordWrap: { width: 180 },
      }).setOrigin(0.5, 1);
    }
  }
}
