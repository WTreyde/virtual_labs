import Phaser from "phaser";
import { fitRoom, iso, PIX, TILE, Z_SQUASH } from "./iso";
import { bakeRoom, bakeVoxels, model, spriteKind } from "./sprites";
import { clock, Timeline } from "./timeline";
import type { Design, Vec3 } from "./types";

type Pt = { x: number; y: number };
/** A polyline in screen space with cumulative lengths, so movers advance at even speed. */
class Path {
  private cum: number[] = [0];
  constructor(readonly pts: Pt[]) {
    for (let i = 1; i < pts.length; i++) this.cum.push(this.cum[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y));
  }
  at(f: number): Pt {
    const L = this.cum.at(-1)! * Math.min(1, Math.max(0, f));
    let i = 1;
    while (i < this.pts.length - 1 && this.cum[i] < L) i++;
    const a = this.pts[i - 1], b = this.pts[i] ?? a, seg = this.cum[i] - this.cum[i - 1] || 1, g = (L - this.cum[i - 1]) / seg;
    return { x: a.x + (b.x - a.x) * g, y: a.y + (b.y - a.y) * g };
  }
}


/**
 * Strand A: the isometric lab. Owner: Roshan.
 * Draws the room, zones and instruments as procedural pixel-art sprites sized from catalog footprints,
 * transfer paths, operators and bottleneck speech bubbles. Plates and operators move on the shared sim
 * `clock` from SimResult.timeline; busy instruments show step progress and how many plates they hold.
 * With no usable timeline it falls back to plates looping along the transfer paths.
 * Clicks emit a `select` game event that main.ts turns into the stat card; every frame emits `tick`.
 */
export class LabScene extends Phaser.Scene {
  private design!: Design;
  private sprites: Record<string, Phaser.GameObjects.Image> = {};
  private movers: { plate: Phaser.GameObjects.Image; path: Path; t: number }[] = [];
  private timeline?: Timeline;
  private plates = new Map<string, Phaser.GameObjects.Image>();
  private paths = new Map<string, { screen: Path; floor: Path }>();
  private ops: { id: string; img: Phaser.GameObjects.Image; label: Phaser.GameObjects.Text; home: Pt; pos: Pt }[] = [];
  private busy!: Phaser.GameObjects.Graphics;
  private badges: Record<string, Phaser.GameObjects.Text> = {};
  private queueBadges: Record<string, Phaser.GameObjects.Text> = {};

  constructor() { super("lab"); }

  init(data: { design: Design }) {
    this.design = data.design;
    this.movers = [];
    this.sprites = {};
    this.plates = new Map();
    this.paths = new Map();
    this.ops = [];
    this.badges = {};
    this.queueBadges = {};
    const transfers = data.design.layout.transfers;
    const travel = (from: string | undefined, to: string) =>
      transfers.find((t) => (t.from_instance === from && t.to_instance === to) || (t.from_instance === to && t.to_instance === from))?.est_time_s ?? 15;
    const tl = new Timeline(data.design.sim_result.timeline ?? [], travel);
    this.timeline = tl.usable ? tl : undefined;
    clock.end = this.timeline?.end ?? 0;
    clock.t = Math.min(clock.t, clock.end);
  }

  create() {
    const { layout } = this.design;
    // Keep the room clear of the dialogue box along the bottom.
    fitRoom(layout.room.width_m, layout.room.depth_m, this.scale.width, this.scale.height - 120);
    for (const k of this.textures.getTextureKeys()) if (k.startsWith("lf:")) this.textures.remove(k);
    this.drawRoom();
    this.drawEquipment();
    this.drawTransfers();
    this.drawOperators();
    this.drawBottlenecks();
    const pre = new URLSearchParams(location.search).get("select"); // e.g. ?select=lh_1, for screenshots
    if (pre && this.sprites[pre]) this.select(pre, this.sprites[pre]);
    const selectId = (id: string) => this.sprites[id] && this.select(id, this.sprites[id]);
    this.game.events.on("select-id", selectId);
    this.events.once("shutdown", () => this.game.events.off("select-id", selectId));
    this.input.on("pointerdown", (_: unknown, hits: unknown[]) => { if (!hits.length) this.game.events.emit("select", null); });
    this.game.events.emit("ready-clock");
    this.scale.once("resize", () => this.scene.restart({ design: this.design }));
  }

  update(time: number, dtMs: number) {
    const dt = dtMs / 1000;
    for (const m of this.movers) {
      m.t = (m.t + dt * 0.25) % 1;
      const q = m.path.at(m.t);
      m.plate.setPosition(q.x, q.y);
    }
    const tl = this.timeline;
    if (!tl) return;
    if (clock.playing) clock.t = (clock.t + dt * clock.speed) % Math.max(1, tl.end);
    const t = clock.t;

    // Plates in transit; a move lasts at least 0.6 s on screen so it stays visible at fast-forward.
    const seen = new Set<string>(), carrying = new Map<string, Pt>();
    for (const { move, f } of tl.movesAt(t, 0.6 * clock.speed)) {
      const p = this.pathFor(move.from, move.to);
      if (!p) continue;
      const q = p.screen.at(f);
      this.plateFor(move.labware).setPosition(q.x, q.y).setVisible(true);
      seen.add(move.labware);
      if (this.ops.some((o) => o.id === move.by)) carrying.set(move.by, p.floor.at(f));
    }
    for (const [lab, img] of this.plates) if (!seen.has(lab)) img.setVisible(false);

    // Operators: follow what they carry, otherwise walk home.
    for (const o of this.ops) {
      const target = carrying.get(o.id) ?? o.home;
      const dx = target.x - o.pos.x, dy = target.y - o.pos.y, dist = Math.hypot(dx, dy), step = 1.5 * dt;
      const walking = dist > 0.02;
      if (carrying.has(o.id) || dist <= step) o.pos = { ...target };
      else { o.pos.x += (dx / dist) * step; o.pos.y += (dy / dist) * step; }
      const s = iso(o.pos.x, o.pos.y, 0), bob = Math.floor(time / (walking ? 140 : 500)) % 2 ? PIX : 0;
      o.img.setPosition(s.x, s.y - bob).setDepth(o.pos.x + o.pos.y);
      const top = o.img.getTopCenter();
      o.label.setPosition(top.x, top.y - 2);
    }

    // Busy instruments: progress of the oldest running step, and a count when several plates are inside.
    // Queued plates (red badge) make the bottleneck visible as a pile-up.
    const active = tl.activeSteps(t), queued = tl.queuedAt(t);
    this.busy.clear();
    for (const [id, badge] of Object.entries(this.badges)) {
      const steps = active.get(id), img = this.sprites[id], q = queued.get(id)?.length ?? 0, qb = this.queueBadges[id];
      const top = img.getTopCenter(), w = 34, x = top.x - w / 2, y = top.y - 10;
      badge.setVisible(!!steps && steps.length > 1);
      qb.setVisible(q > 0).setText(`+${q} queued`).setPosition(top.x, y - 6);
      if (!steps) continue;
      const s0 = steps.reduce((a, b) => (b.t0 < a.t0 ? b : a)), f = (t - s0.t0) / (s0.t1 - s0.t0);
      this.busy.fillStyle(0x2b2f36).fillRect(x - 2, y - 2, w + 4, 8).fillStyle(0xe8e8e0).fillRect(x, y, w, 4);
      this.busy.fillStyle(0x3ec46d).fillRect(x, y, Math.round(w * f), 4);
      badge.setText(`×${steps.length}`).setPosition(top.x + w / 2 + 6, y + 2);
    }
    const last = this.design.workflow.steps?.at(-1)?.id;
    this.game.events.emit("tick", { t, end: tl.end, done: tl.finishedBy(t, last), moving: tl.movesAt(t, 0).length });
  }

  private plateFor(lab: string) {
    let img = this.plates.get(lab);
    if (!img) {
      const tex = this.textures.get("lf:plate"), src = tex.getSourceImage(), o = tex.customData as { ox: number; oy: number };
      img = this.add.image(0, 0, "lf:plate").setScale(PIX).setDepth(850).setOrigin(o.ox / src.width, o.oy / src.height);
      this.plates.set(lab, img);
    }
    return img;
  }

  /** Screen path for a move between two instances: the layout's transfer path if any, else a straight hop. */
  private pathFor(from: string | undefined, to: string) {
    const key = `${from}>${to}`;
    if (this.paths.has(key)) return this.paths.get(key)!;
    const { transfers, placements } = this.design.layout;
    let pts: Vec3[] | undefined = transfers.find((t) => t.from_instance === from && t.to_instance === to)?.path;
    if (!pts?.length) pts = transfers.find((t) => t.from_instance === to && t.to_instance === from)?.path?.slice().reverse();
    if (!pts?.length) {
      const a = placements.find((p) => p.instance_id === from)?.position, b = placements.find((p) => p.instance_id === to)?.position;
      if (!b) return undefined;
      pts = [a ?? b, b].map((q) => ({ x: q.x, y: q.y, z: q.z + 0.3 }));
    }
    const entry = {
      screen: new Path(pts.map((q) => iso(q.x, q.y, q.z * Z_SQUASH))),
      floor: new Path(pts.map((q) => ({ x: q.x, y: q.y }))), // room metres, for operators walking it
    };
    this.paths.set(key, entry);
    return entry;
  }

  /** Tell the HTML overlay which instance was clicked, with its sprite for the stat card. */
  private select(id: string, img: Phaser.GameObjects.Image) {
    const src = this.textures.get(img.texture.key).getSourceImage() as HTMLCanvasElement;
    this.game.events.emit("select", { id, sprite: src.toDataURL() });
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
      this.sprites[p.instance_id] = img;
      const lbl = this.label(img, item.model).setVisible(false);
      img.setInteractive({ pixelPerfect: true, useHandCursor: true })
        .on("pointerover", () => { lbl.setVisible(true); img.setTint(0xfff3c4); })
        .on("pointerout", () => { lbl.setVisible(false); img.clearTint(); })
        .on("pointerdown", () => this.select(p.instance_id, img));
    }
  }

  private drawTransfers() {
    const plate = bakeVoxels(this, "lf:plate", model("generic", 0.13, 0.09, 0.025, 0, 0xf4f4f4));
    this.textures.get(plate.key).customData = { ox: plate.ox, oy: plate.oy };
    this.busy = this.add.graphics().setDepth(1002);
    const badge = (bg: string) => this.add.text(0, 0, "", {
      fontFamily: '"Press Start 2P", monospace', fontSize: "8px", color: "#fbfbf5", backgroundColor: bg, padding: { x: 3, y: 2 },
    }).setDepth(1003).setVisible(false);
    for (const id of Object.keys(this.sprites)) {
      this.badges[id] = badge("#2b2f36").setOrigin(0, 0.5);
      this.queueBadges[id] = badge("#e0503c").setOrigin(0.5, 1);
    }
    for (const t of this.design.layout.transfers) {
      if (!t.path?.length) continue;
      const pts = t.path.map((q) => iso(q.x, q.y, q.z * Z_SQUASH));
      const g = this.add.graphics().lineStyle(2, t.transporter_instance.startsWith("arm") ? 0x2d6cdf : 0xe08a2d, 0.45).setDepth(800);
      g.beginPath(); g.moveTo(pts[0].x, pts[0].y); pts.slice(1).forEach((q) => g.lineTo(q.x, q.y)); g.strokePath();
      if (this.timeline) continue; // the timeline drives the plates instead
      const img = this.plateFor(`loop:${this.movers.length}`).setPosition(pts[0].x, pts[0].y);
      this.movers.push({ plate: img, path: new Path(pts), t: Math.random() });
    }
  }

  private drawOperators() {
    for (const op of this.design.layout.operators ?? []) {
      const img = this.place(bakeVoxels(this, `lf:op:${op.id}`, model("operator", 0.4, 0.25, 1.7, 0), 0, { w: 0.4, d: 0.25 }), op.home.x, op.home.y);
      this.sprites[op.id] = img;
      const label = this.label(img, op.role).setAlpha(0.85);
      this.ops.push({ id: op.id, img, label, home: { ...op.home }, pos: { ...op.home } });
      img.setInteractive({ pixelPerfect: true, useHandCursor: true }).on("pointerdown", () => this.select(op.id, img));
    }
  }

  /**
   * Capacity bottlenecks get a red aura and a speech bubble (one per instance, at most three, highest severity first,
   * raised to clear earlier bubbles); long transfers get a red dashed line between the two instances. Every bottleneck
   * is also read out in the dialogue box, so nothing is lost when a run reports many.
   */
  private drawBottlenecks() {
    const { layout, sim_result } = this.design;
    const where: Record<string, { x: number; y: number; z: number }> = Object.fromEntries(layout.placements.map((p) => [p.instance_id, p.position]));
    for (const op of layout.operators ?? []) where[op.id] ??= { x: op.home.x, y: op.home.y, z: 0 };
    const rank: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
    const sorted = [...sim_result.bottlenecks].sort((a, b) => (rank[a.severity] ?? 9) - (rank[b.severity] ?? 9));

    for (const b of sorted.filter((b) => b.kind === "long_transfer" && b.instances?.length === 2)) {
      const [p, q] = b.instances!.map((id) => where[id]);
      if (!p || !q) continue;
      const a = iso(p.x, p.y, 0), c = iso(q.x, q.y, 0), n = Math.max(2, Math.floor(Math.hypot(c.x - a.x, c.y - a.y) / 10));
      const g = this.add.graphics().lineStyle(2, 0xe0503c, 0.7).setDepth(-500);
      for (let i = 0; i < n; i += 2) g.lineBetween(a.x + ((c.x - a.x) * i) / n, a.y + ((c.y - a.y) * i) / n, a.x + ((c.x - a.x) * (i + 1)) / n, a.y + ((c.y - a.y) * (i + 1)) / n);
    }

    const placed: Phaser.Geom.Rectangle[] = [], done = new Set<string>();
    for (const b of sorted.filter((b) => b.kind !== "long_transfer")) {
      const id = b.instances?.[0], pos = id && where[id];
      if (!pos || done.has(id) || placed.length >= 3) continue;
      done.add(id);
      const f = iso(pos.x, pos.y, 0);
      const aura = this.add.ellipse(f.x, f.y, TILE * 1.6, TILE * 0.8, 0xe0503c, 0.35).setDepth(pos.x + pos.y - 0.01);
      this.tweens.add({ targets: aura, alpha: 0.08, yoyo: true, repeat: -1, duration: 700 });
      const s = iso(pos.x, pos.y, 1.4);
      const txt = this.add.text(s.x, s.y - 64, b.message, {
        fontFamily: '"Press Start 2P", monospace', fontSize: "8px", lineSpacing: 5, color: "#222", wordWrap: { width: 210 },
      }).setOrigin(0.5, 1).setDepth(1001);
      const pad = 9;
      // Raise this bubble until it clears the ones already placed.
      for (let tries = 0; tries < 8; tries++) {
        const r = txt.getBounds(), box = new Phaser.Geom.Rectangle(r.x - pad - 4, r.y - pad - 4, r.width + 2 * pad + 8, r.height + 2 * pad + 8);
        if (!placed.some((o) => Phaser.Geom.Intersects.RectangleToRectangle(o, box))) { placed.push(box); break; }
        txt.y -= 24;
      }
      // Speech bubble in the same frame style as the HTML dialogue box, tail pointing at the instrument.
      const r = txt.getBounds(), g = this.add.graphics().setDepth(1000);
      g.fillStyle(0x2b2f36).fillRoundedRect(r.x - pad - 3, r.y - pad - 3, r.width + 2 * pad + 6, r.height + 2 * pad + 6, 8);
      g.fillTriangle(s.x - 10, r.bottom + pad, s.x + 10, r.bottom + pad, s.x, r.bottom + pad + 14);
      g.fillStyle(0xfbfbf5).fillRoundedRect(r.x - pad, r.y - pad, r.width + 2 * pad, r.height + 2 * pad, 6);
      g.fillTriangle(s.x - 6, r.bottom + pad - 1, s.x + 6, r.bottom + pad - 1, s.x, r.bottom + pad + 9);
      this.tweens.add({ targets: [txt, g], y: "-=3", yoyo: true, repeat: -1, duration: 600, ease: "Stepped" });
    }
  }
}
