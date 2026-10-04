import { describe, type AgentEvent } from "./replay";

/**
 * Strand A: the agent log under the BOM total. One collapsible block per planning step, one row per tool call, with
 * status, duration and a one-line summary. Uses the lifecycle events from the planner (Albert's #52): starts and ends
 * share `event_id`; ends carry `status`, `duration_ms` and `summary`. Older recordings have none of these, so a
 * tool end is paired with the earliest open start of the same tool, and the summary is derived from its output.
 * Durations are shown only when the event reports them; nothing is estimated.
 */

type Status = "running" | "succeeded" | "failed" | "declined";
interface Row { key: string; name: string; label: string; status: Status; ms?: number; summary?: string; el: HTMLElement }
interface Step { n: number; status: Status; ms?: number; summary?: string; rows: Row[]; el: HTMLDetailsElement }

const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const secs = (ms?: number) => (ms == null ? "" : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} s`);
const ICON: Record<Status, string> = { running: "…", succeeded: "✓", failed: "✗", declined: "⊘" };
/** The planner reports a provider refusal as status "declined_by_model". */
const norm = (s?: string): Status | undefined => (s === "declined_by_model" ? "declined" : (s as Status | undefined));

/** One-line summary for recordings made before the planner emitted `summary`. */
function derivedSummary(e: AgentEvent): string | undefined {
  const out = e.output ?? {};
  if (e.type === "tool_error") return e.error ?? "Failed.";
  if (e.name === "search_catalog" || e.name === "search_evidence") {
    const items = out.items ?? out.results;
    if (Array.isArray(items)) return `Found ${items.length} ${e.name === "search_catalog" ? "catalog item" : "evidence result"}${items.length === 1 ? "" : "s"}.`;
  }
  if (e.name === "layout_and_simulate" && out.sim_result?.throughput) {
    const t = out.sim_result.throughput, v = (out.layout?.violations ?? []).length;
    return `Simulated at p50 ${t.p50 ?? t.value} ${String(t.unit ?? "").replace(/_/g, " ")}; ${v} layout violation${v === 1 ? "" : "s"}.`;
  }
  if (e.name === "verify_claims" && Array.isArray(out.claims)) {
    const n = (s: string) => out.claims.filter((c: any) => c.status === s).length;
    return `Checked ${out.claims.length} claims: ${n("supported")} supported, ${n("refuted")} refuted.`;
  }
  return undefined;
}

export class AgentLog {
  private steps: Step[] = [];
  private open = new Map<string, Row>();

  constructor(private el: HTMLElement) {}

  clear() { this.el.innerHTML = ""; this.steps = []; this.open.clear(); }
  get isEmpty() { return !this.el.childElementCount; }

  /** A plain entry: the user's message, the agent's answer, or a notice. */
  note(text: string, kind: "user" | "agent" | "notice" | "declined" = "notice") {
    const div = document.createElement("div");
    div.className = `log-note ${kind}`;
    div.textContent = text;
    this.el.append(div);
    this.scroll();
  }

  event(e: AgentEvent) {
    const ev = e as AgentEvent & { event_id?: string; status?: Status; duration_ms?: number; summary?: string };
    if (e.type === "model_call") return this.startStep(ev.step);
    if (e.type === "model_result") {
      const s = this.stepFor(ev.step);
      Object.assign(s, { status: norm(ev.status) ?? "succeeded", ms: ev.duration_ms, summary: ev.summary });
      return this.renderStep(s);
    }
    if (e.type === "tool_start") {
      const s = this.stepFor(ev.step);
      const row: Row = { key: ev.event_id ?? `${e.name}#${Math.random()}`, name: e.name ?? "tool", label: describe(e)?.replace(/…$/, "") ?? e.name ?? "tool", status: "running", el: document.createElement("li") };
      s.rows.push(row);
      s.el.querySelector("ul")!.append(row.el);
      this.open.set(row.key, row);
      this.renderRow(row); this.renderStep(s);
      return;
    }
    if (e.type === "tool_end" || e.type === "tool_error") {
      const row = (ev.event_id && this.open.get(ev.event_id)) ?? [...this.open.values()].find((r) => r.name === e.name);
      if (!row) return;
      this.open.delete(row.key);
      Object.assign(row, { status: e.type === "tool_error" ? "failed" : ev.status === "failed" ? "failed" : "succeeded", ms: ev.duration_ms, summary: ev.summary ?? derivedSummary(e) });
      this.renderRow(row);
      this.renderStep(this.steps.find((s) => s.rows.includes(row))!);
    }
  }

  private stepFor(n?: number): Step { return (n != null && this.steps.find((s) => s.n === n)) || this.steps.at(-1) || this.startStep(n); }

  /**
   * Settle steps that never got a model_result (older recordings): a step is done once a later step starts or the
   * run ends, and its status comes from its tool calls. Call at the end of a replay or a live turn.
   */
  finish() { for (const s of this.steps) this.settle(s); }

  /** The turn ended with a refusal: mark its last step declined, even when no step event said so (older backends). */
  declineLast() {
    const s = this.steps.at(-1);
    if (s && s.status !== "failed") { s.status = "declined"; this.renderStep(s); }
  }

  private settle(s: Step) {
    if (s.status !== "running") return;
    s.status = s.rows.some((r) => r.status === "failed") ? "failed" : "succeeded";
    this.renderStep(s);
  }

  private startStep(n?: number): Step {
    for (const s of this.steps) { s.el.open = false; this.settle(s); } // fold and settle earlier steps
    const el = document.createElement("details");
    el.className = "log-step"; el.open = true;
    el.innerHTML = "<summary></summary><ul></ul>";
    const s: Step = { n: n ?? this.steps.length + 1, status: "running", rows: [], el };
    this.steps.push(s);
    this.el.append(el);
    this.renderStep(s);
    return s;
  }

  private renderStep(s: Step) {
    const failed = s.rows.some((r) => r.status === "failed"), running = s.status === "running" && s.rows.some((r) => r.status === "running");
    const status: Status = s.status === "declined" ? "declined" : failed || s.status === "failed" ? "failed" : running ? "running" : s.status;
    const calls = s.rows.length ? `${s.rows.length} tool call${s.rows.length === 1 ? "" : "s"}` : "thinking";
    s.el.querySelector("summary")!.innerHTML = `<span class="st ${status}">${ICON[status]}</span> <b>Step ${s.n}</b> · ${calls}${s.ms != null ? ` · ${secs(s.ms)}` : ""}${
      s.summary ? `<div class="sum">${esc(s.summary)}</div>` : ""}`;
    this.scroll();
  }

  private renderRow(r: Row) {
    r.el.className = `log-tool ${r.status}`;
    r.el.innerHTML = `<span class="st ${r.status}">${ICON[r.status]}</span> <span class="what">${esc(r.label)}</span>${r.ms != null ? ` <span class="ms">${secs(r.ms)}</span>` : ""}${
      r.summary ? `<div class="sum">${esc(r.summary)}</div>` : ""}`;
  }

  private scroll() { this.el.scrollTop = this.el.scrollHeight; }
}
