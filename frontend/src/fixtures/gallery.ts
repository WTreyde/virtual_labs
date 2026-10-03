import type { CatalogItem, Design } from "../types";

/**
 * Client-only fixture (open with `?demo=gallery`): one of every sprite kind in a chemistry-style room,
 * for checking art and UI without the backend. Not a real design; every number is a placeholder.
 */
const item = (id: string, vendor: string, model: string, capabilities: string[], w: number, d: number, h: number, extra: Partial<CatalogItem> = {}): CatalogItem =>
  ({ id, vendor, model, category: "instrument", capabilities, footprint: { width_m: w, depth_m: d, height_m: h }, data_confidence: "placeholder", ...extra });

const catalog: CatalogItem[] = [
  item("fume_hood", "Generic", "Fume hood + SWING", ["reaction", "ventilated_enclosure"], 1.5, 0.8, 1.1, { price_usd_estimate: 250000 }),
  item("quantos", "Mettler Toledo", "Quantos", ["powder_dosing"], 0.5, 0.5, 0.55, { price_usd_estimate: 60000, visual: { color: "#c8ccd2" } }),
  item("genevac", "Genevac", "EZ-2", ["evaporation"], 0.7, 0.7, 0.6, { price_usd_estimate: 40000 }),
  item("acquity", "Waters", "Acquity UPLC-MS", ["lcms"], 0.9, 0.65, 0.75, { price_usd_estimate: 180000 }),
  item("ur5e", "Universal Robots", "UR5e", ["plate_transport_arm"], 0.2, 0.2, 0.2, { category: "transporter", transport: { kind: "arm" }, price_usd_estimate: 35000 }),
  item("echo", "Beckman", "Echo 650", ["acoustic_dispensing"], 0.7, 0.6, 0.6, { price_usd_estimate: 300000, visual: { color: "#e9ecef" } }),
  item("stx44", "LiCONiC", "STX44", ["incubation"], 0.6, 0.7, 0.85, { price_usd_estimate: 45000 }),
  item("pherastar", "BMG LABTECH", "PHERAstar FSX", ["fluorescence_read"], 0.45, 0.55, 0.4, { price_usd_estimate: 120000 }),
  item("plateloc", "Agilent", "PlateLoc", ["plate_sealing"], 0.25, 0.5, 0.45, { price_usd_estimate: 20000 }),
  item("hotel", "Generic", "Plate hotel", ["plate_storage"], 0.3, 0.3, 0.6, { category: "storage", price_usd_estimate: 3000 }),
  item("rock_imager", "Formulatrix", "Rock Imager 1000", ["crystal_imaging"], 0.9, 0.9, 1.4, { price_usd_estimate: 400000 }),
  item("mir", "MiR", "MiR250 + arm", ["plate_transport_mobile"], 0.8, 0.58, 0.6, { category: "transporter", transport: { kind: "mobile" }, price_usd_estimate: 70000 }),
  item("centrifuge", "Agilent", "Plate centrifuge", ["centrifugation"], 0.4, 0.5, 0.35, { price_usd_estimate: 15000 }),
];

const place = (instance_id: string, x: number, y: number, z = 0.9, rotation_deg = 0) => ({ instance_id, position: { x, y, z }, rotation_deg });
const equipment: [string, string][] = [
  ["hood_1", "fume_hood"], ["doser_1", "quantos"], ["evap_1", "genevac"], ["lcms_1", "acquity"], ["lcms_2", "acquity"],
  ["arm_1", "ur5e"], ["echo_1", "echo"], ["incubator_1", "stx44"], ["reader_1", "pherastar"], ["sealer_1", "plateloc"],
  ["hotel_1", "hotel"], ["imager_1", "rock_imager"], ["mobile_1", "mir"], ["spin_1", "centrifuge"],
];

const p = (x: number, y: number, z: number) => ({ x, y, z });

export const galleryDesign: Design = {
  lab_spec: { id: "sprite_gallery", name: "Sprite gallery (client fixture, not a real design)" },
  workflow: { id: "sprite_gallery_wf", equipment: equipment.map(([instance_id, catalog_id]) => ({ instance_id, catalog_id })) },
  catalog: Object.fromEntries(catalog.map((c) => [c.id, c])),
  layout: {
    id: "sprite_gallery_layout",
    room: { width_m: 8, depth_m: 5 },
    placements: [
      place("hood_1", 1.1, 0.55, 0), place("doser_1", 2.5, 0.5), place("evap_1", 0.6, 1.9, 0),
      place("lcms_1", 4.0, 0.5), place("lcms_2", 5.1, 0.5),
      place("arm_1", 5.4, 2.4), place("echo_1", 5.4, 1.5), place("incubator_1", 4.5, 2.5), place("reader_1", 6.3, 2.4),
      place("sealer_1", 5.4, 3.2), place("hotel_1", 6.2, 3.2), place("spin_1", 4.6, 3.3),
      place("imager_1", 7.3, 1.0, 0), place("mobile_1", 2.8, 3.2, 0),
    ],
    transfers: [
      { from_instance: "echo_1", to_instance: "incubator_1", transporter_instance: "arm_1", distance_m: 1.2, path: [p(5.4, 1.85, 1.0), p(5.4, 2.4, 1.4), p(4.85, 2.5, 1.1)] },
      { from_instance: "incubator_1", to_instance: "reader_1", transporter_instance: "arm_1", distance_m: 1.8, path: [p(4.85, 2.5, 1.1), p(5.4, 2.4, 1.4), p(6.05, 2.4, 1.0)] },
      { from_instance: "hood_1", to_instance: "lcms_1", transporter_instance: "mobile_1", distance_m: 4.2, path: [p(1.9, 1.2, 0.5), p(2.8, 2.6, 0.5), p(4.0, 1.3, 0.5)] },
    ],
    zones: [
      { id: "hood_zone", kind: "fume_hood", min: { x: 0.2, y: 0.05 }, max: { x: 3.0, y: 1.1 } },
      { id: "cell", kind: "robot_only", min: { x: 4.0, y: 1.1 }, max: { x: 6.8, y: 3.7 } },
      { id: "aisle", kind: "walkway", min: { x: 0.2, y: 4.2 }, max: { x: 7.8, y: 4.9 } },
    ],
    operators: [{ id: "op_1", role: "chemist", home: { x: 1.8, y: 2.3 } }, { id: "op_2", role: "technician", home: { x: 7.0, y: 3.9 } }],
  },
  sim_result: {
    throughput: { value: 420, unit: "compounds/day", target: 768, p10: 300, p50: 420, p90: 560, prob_meets_target: 0.04 },
    utilisation: [{ instance_id: "lcms_1", busy_fraction: 0.97 }],
    bottlenecks: [{ kind: "instrument", severity: "high", message: "I'm the bottleneck (32 h per library)", instances: ["lcms_1"] }],
  },
};
