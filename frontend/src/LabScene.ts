import Phaser from "phaser";
import { fitRoom, iso, PIX, TILE, Z_SQUASH } from "./iso";
import { bakeRoom, bakeVoxels, model, spriteKind } from "./sprites";
import type { Design } from "./types";

/**
 * Strand A: the isometric lab. Owner: Roshan.
 * Draws the room, zones and instruments as procedural pixel-art sprites sized from catalog footprints,
 * transfer paths with moving plates, operators and bottleneck speech bubbles.
 * TODO(Roshan): animate from SimResult.timeline, stat card on click, Pokemon-style UI frame.
 */
export class LabScene extends Phaser.Scene {
  private design!: Design;
  private movers: { plate: Phaser.GameObjects.Image; pts: { x: number; y: number }[]; t: number; speed: number }[] = [];

  constructor() { super("lab"); }

  init(data: { design: Design }) {
    this.design = data.design;
    this.movers = [];
  }

  create() {
    const { layout } = this.design;
    fitRoom(layout.room.width_m, layout.room.depth_m, this.scale.width, this.scale.height);
    for (const k of this.textures.getTextureKeys()) if (k.startsWith("lf:")) this.textures.remove(k);
    this.drawRoom();
    this.drawEquipment();
    this.drawTransfers();
    this.drawOperators();
    this.drawBottlenecks();
    this.scale.once("resize", () => this.scene.restart({ design: this.design }));
  }

  update(_: number, dtMs: number) {
    for (const m of this.movers) {
      m.t = (m.t + (dtMs / 1000) * m.speed) % 1;
      const seg = m.t * (m.pts.length - 1), i = Math.floor(seg), f = seg - i;
      const a = m.pts[i], b = m.pts[Math.min(i + 1, m.pts.length - 1)];
      m.plate.setPosition(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f);
    }
  }

  /** Place a baked texture so its local origin lands on floor point (x, y). Depth sorts by x + y. */
  private place(tex: { key: string; ox: number; oy: number }, x: number, y: number) {
    const s = iso(x, y, 0), img = this.add.image(s.x, s.y, tex.key).setScale(PIX);
    const src = this.textures.get(tex.key).getSourceImage();
    return img.setOrigin(tex.ox / src.width, tex.oy / src.height).setDepth(x + y);
  }

  private label(img: Phaser.GameObjects.Image, text: string) {
    const top = img.getTopCenter();
    return this.add.text(top.x, top.y - 2, text, {
      fontFamily: '"Press Start 2P", monospace', fontSize: "8px", color: "#f4efe1", backgroundColor: "#1d2b2fcc", padding: { x: 3, y: 3 },
    }).setOrigin(0.5, 1).setDepth(900);
  }

  private drawRoom() {
    const tex = bakeRoom(this, "lf:room", this.design.layout);
    this.place(tex, 0, 0).setDepth(-1000);
  }

  private drawEquipment() {
    const { layout, workflow, catalog } = this.design;
    const itemOf = Object.fromEntries(workflow.equipment.map((e) => [e.instance_id, catalog[e.catalog_id]]));
    for (const p of layout.placements) {
      const item = itemOf[p.instance_id];
      if (!item) continue;
      const { width_m: w, depth_m: d, height_m: h } = item.footprint;
      const colour = item.visual?.color ? parseInt(item.visual.color.replace("#", ""), 16) : undefined;
      const vox = model(spriteKind(item), w, d, h, p.position.z * Z_SQUASH, colour);
      const img = this.place(bakeVoxels(this, `lf:${p.instance_id}`, vox, p.rotation_deg, { w, d }), p.position.x, p.position.y);
      const lbl = this.label(img, item.model).setVisible(false);
      img.setInteractive({ pixelPerfect: true, useHandCursor: true })
        .on("pointerover", () => { lbl.setVisible(true); img.setTint(0xfff3c4); })
        .on("pointerout", () => { lbl.setVisible(false); img.clearTint(); });
    }
  }

  private drawTransfers() {
    const plate = bakeVoxels(this, "lf:plate", model("generic", 0.13, 0.09, 0.025, 0, 0xf4f4f4));
    for (const t of this.design.layout.transfers) {
      if (!t.path?.length) continue;
      const pts = t.path.map((q) => iso(q.x, q.y, q.z * Z_SQUASH));
      const g = this.add.graphics().lineStyle(2, t.transporter_instance.startsWith("arm") ? 0x2d6cdf : 0xe08a2d, 0.45).setDepth(800);
      g.beginPath(); g.moveTo(pts[0].x, pts[0].y); pts.slice(1).forEach((q) => g.lineTo(q.x, q.y)); g.strokePath();
      const img = this.add.image(pts[0].x, pts[0].y, plate.key).setScale(PIX).setDepth(850);
      const src = this.textures.get(plate.key).getSourceImage();
      img.setOrigin(plate.ox / src.width, plate.oy / src.height);
      this.movers.push({ plate: img, pts, t: Math.random(), speed: 0.25 });
    }
  }

  private drawOperators() {
    for (const op of this.design.layout.operators ?? []) {
      const img = this.place(bakeVoxels(this, `lf:op:${op.id}`, model("operator", 0.4, 0.25, 1.7, 0), 0, { w: 0.4, d: 0.25 }), op.home.x, op.home.y);
      this.tweens.add({ targets: img, y: img.y - PIX, yoyo: true, repeat: -1, duration: 500 + Math.random() * 300, ease: "Stepped" });
      this.label(img, op.role).setAlpha(0.85);
    }
  }

  private drawBottlenecks() {
    const where = Object.fromEntries(this.design.layout.placements.map((p) => [p.instance_id, p.position]));
    for (const b of this.design.sim_result.bottlenecks) {
      const pos = b.instances?.[0] && where[b.instances[0]];
      if (!pos) continue;
      const f = iso(pos.x, pos.y, 0);
      const aura = this.add.ellipse(f.x, f.y, TILE * 1.6, TILE * 0.8, 0xe0503c, 0.35).setDepth(pos.x + pos.y - 0.01);
      this.tweens.add({ targets: aura, alpha: 0.08, yoyo: true, repeat: -1, duration: 700 });
      const s = iso(pos.x, pos.y, 1.4);
      this.add.text(s.x, s.y, b.message, {
        fontFamily: '"Press Start 2P", monospace', fontSize: "8px", lineSpacing: 4, color: "#111", backgroundColor: "#ffffff",
        padding: { x: 6, y: 6 }, wordWrap: { width: 200 },
      }).setOrigin(0.5, 1).setDepth(1000);
    }
  }
}
