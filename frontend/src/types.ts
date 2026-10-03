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
export type ChatMessage = { role: string; content: string | unknown[] };

export interface Design {
  lab_spec: any; workflow: Workflow; layout: Layout; sim_result: SimResult; catalog: Record<string, CatalogItem>;
  /** Client-side note on where the timeline came from, shown under the time controls. */
  timeline_note?: string;
  /** Report Markdown from the agent (chat or a recorded run), used instead of POST /report. */
  report_markdown?: string;
  /** Cached what-if sweeps by instance, for recorded cases when the backend is unavailable. */
  whatif_cache?: Record<string, InstrumentOptimisation>;
}

/** Mirrors schemas/instrument_optimisation.schema.json (POST /optimise). */
export interface InstrumentOptimisation {
  instance_id: string; catalog_id: string; layout_id: string;
  baseline: { throughput_p50: number; unit?: string; utilisation?: number };
  sweeps: {
    parameter: "cycle_time" | "capacity" | "transfer_time" | "uptime";
    points: { value: number; throughput_p50: number; throughput_p10?: number; throughput_p90?: number }[];
    elasticity?: number;
  }[];
  headroom_note?: string; next_bottleneck?: string;
}

/** Mirrors schemas/project_schedule.schema.json (POST /prioritise). */
export interface ProjectSchedule {
  lab_id: string; objective: "makespan" | "weighted_tardiness";
  candidates: {
    policy: string; order?: string[]; makespan_h: number; mean_utilisation: number;
    utilisation?: Record<string, number>; project_finish_h?: Record<string, number>;
    weighted_tardiness_h?: number; deadline_misses?: string[];
  }[];
  recommended: string; gain_vs_naive?: number;
  gantt?: { project: string; unit: number; step: string; instance: string; start_s: number; end_s: number }[];
  caveat?: string;
}

/** One project for POST /prioritise: a workflow on the lab's equipment ids, labware units, optional weight and deadline. */
export interface ProjectRequest { id: string; workflow: Workflow & Record<string, unknown>; units: number; weight?: number; deadline_h?: number }

/** One row of GET /validation (backend/labforge/validation/runner.py run_case). */
export interface ValidationRow {
  id: string; name: string; verified: boolean; includes?: string[];
  status: "compared" | "no_design_yet" | "error" | "not_costable" | string;
  /** Why there is no comparison (no_design_yet, error, not_costable). */
  reason?: string;
  reported_usd?: number;
  predicted?: {
    p10: number; p50: number; p90: number; n_items?: number;
    /** Experimental: does not yet beat a constant baseline (docs/validation.md). */
    confidence?: { within_25pct?: number; label?: string; data_coverage?: number };
  };
  within_p10_p90?: boolean; log10_error?: number; within_25pct?: boolean; like_for_like?: boolean;
  unmodelled_categories?: string[];
  /** Set when the design was made by the agent (with the reported cost withheld from it). */
  design_provenance?: unknown;
}

/** GET /bench/leaderboard (backend/labforge/bench/runner.py leaderboard()). */
export interface BenchCheck { id: string; kind: string; passed: boolean | null; note?: string }
export interface Leaderboard {
  generated_at?: string; scored_at?: string; description?: string;
  /** When the answers were recorded (newer runners write answered_from/answered_to; older ones answered_before). */
  run?: { answered_from?: string; answered_to?: string; answered_before?: string };
  tasks: { id: string; trap?: string; domain?: string }[];
  arms: {
    arm: string; model?: string; score: number | null; checks_passed: number; checks_total: number; tasks_answered: number;
    runs_failed?: number; designs_produced?: number; checks_not_checkable?: number; brier: number | null;
    claims_supported?: number; claims_refuted?: number; claims_unverifiable?: number; by_trap?: Record<string, number>;
    tasks: { task_id: string; trap?: string; score: number | null; checks: BenchCheck[]; brier?: number | null; error?: string; run_failed?: boolean; has_design?: boolean }[];
  }[];
}

/** GET /bench/tasks: the brief, the trap it tests and the behaviour expected of an honest agent. */
export interface BenchTask { id: string; domain?: string; trap?: string; brief?: string; expected_behaviour?: string }

/** public/replays/<case>.summary.json, written with each recording (Albert): headline facts and known limits. */
export interface CaseSummary {
  title?: string; brief?: string; source?: string;
  headline_throughput: { p50: number; p10?: number; p90?: number; unit: string; basis?: string; verified_p50?: number; target?: number };
  bottleneck?: { instance_id: string; name?: string; catalog_id?: string; model?: string; busy_fraction?: number; basis?: string };
  budget_vs_bom?: { currency?: string; budget?: number; bom?: number; claim_status?: string; basis?: string };
  gate_passed?: boolean;
  limits?: string[];
  /** Albert's what-if for growing plates in the imager instead of the hotel (shape may still change). */
  imager_growth_whatif?: Record<string, unknown>;
}
