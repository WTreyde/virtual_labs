// Hand-written mirrors of /schemas, covering only the fields the client reads.
// TODO(Roshan): generate from the JSON schemas (e.g. json-schema-to-typescript) once they settle.
export type Vec3 = { x: number; y: number; z: number };
export type Confidence = "datasheet" | "literature" | "estimated" | "placeholder";
export interface UncertainNumber { value: number; low?: number; high?: number; confidence?: Confidence; source?: string }
export interface CatalogItem {
  id: string; vendor: string; model: string; category: string; capabilities: string[];
  footprint: { width_m: number; depth_m: number; height_m: number; mount?: string };
  price_usd_estimate?: number; data_confidence?: string; visual?: { color?: string };
  transport?: { kind?: "arm" | "rail" | "mobile" | "human"; speed_m_s?: number; reach_m?: number; pick_place_s?: number };
  process?: { capacity?: number; durations_s?: Record<string, number>; setup_s?: number };
  integration?: string[]; lead_time_weeks?: number; provenance?: Record<string, UncertainNumber>;
}
export interface Workflow {
  id: string; equipment: { instance_id: string; catalog_id: string; rationale?: string }[];
  steps?: { id: string; capability?: string; name?: string }[];
}
export interface TimelineEvent {
  t_s: number; labware_id: string; event: "step_start" | "step_end" | "transfer_start" | "transfer_end" | "queued";
  instance_id?: string; step_id?: string;
}
export interface Layout {
  id: string; room: { width_m: number; depth_m: number };
  placements: { instance_id: string; position: Vec3; rotation_deg: number }[];
  transfers: { from_instance: string; to_instance: string; transporter_instance: string; distance_m: number; est_time_s?: number; path?: Vec3[] }[];
  zones?: { id: string; kind: string; min: { x: number; y: number }; max: { x: number; y: number } }[];
  operators?: { id: string; role: string; home: { x: number; y: number } }[];
  violations?: { kind: string; message: string; instances?: string[] }[];
}
export interface SimResult {
  throughput: { value: number; unit: string; target?: number; p10?: number; p50?: number; p90?: number; prob_meets_target?: number };
  utilisation: { instance_id: string; busy_fraction: number; mean_queue_wait_s?: number }[];
  bottlenecks: { kind: string; severity: string; message: string; instances?: string[]; suggestion?: string }[];
  timeline?: TimelineEvent[]; simulated_hours?: number;
}
export interface Design {
  lab_spec: any; workflow: Workflow; layout: Layout; sim_result: SimResult; catalog: Record<string, CatalogItem>;
  /** Client-side note on where the timeline came from, shown under the time controls. */
  timeline_note?: string;
}
