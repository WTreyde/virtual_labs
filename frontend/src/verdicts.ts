import type { CaseSummary } from "./types";

/**
 * Strand A: the verifier's verdict on each claim the agent made, shown next to the BOM on case pages, so a passed
 * pipeline gate is never the only thing on screen. Read from the recording's checked claims; numbers are the
 * verifier's own (verified_value), with the case summary adding planned throughput where it has it.
 */

export interface CheckedClaim {
  id?: string; statement?: string; metric?: string; comparator?: string; predicted_value?: number;
  confidence?: number; status?: string; verified_value?: number; verifier_note?: string;
}

const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const usd = (v: number) => (v >= 1e6 ? `$${+(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`);
const num = (v: number) => (Math.abs(v) >= 100 ? Math.round(v).toLocaleString() : String(+v.toFixed(1)));

function kind(c: CheckedClaim): "budget" | "throughput" | "layout" | "other" {
  const m = `${c.metric ?? ""} ${c.id ?? ""} ${c.statement ?? ""}`.toLowerCase();
  if (/bom|budget|cost|price|usd/.test(m)) return "budget";
  if (/throughput|per_day|\/day/.test(m)) return "throughput";
  if (/layout|violation/.test(m)) return "layout";
  return "other";
}

const ORDER: Record<string, number> = { refuted: 0, unverifiable: 1, supported: 2 };

export function verdictsBox(claims: CheckedClaim[] | undefined, summary?: CaseSummary): string {
  const checked = (claims ?? []).filter((c) => c.status);
  if (!checked.length) return "";
  const t = summary?.headline_throughput, unit = t ? `/${t.unit.replace(/^.*_per_/, "")}` : "";
  const rows = [...checked].sort((a, b) => (ORDER[a.status!] ?? 9) - (ORDER[b.status!] ?? 9)).map((c) => {
    const k = kind(c), v = c.verified_value, p = c.predicted_value;
    let label = c.statement ?? c.metric ?? "Claim", detail = "";
    if (k === "budget") {
      label = "Budget";
      const bom = v ?? summary?.budget_vs_bom?.bom, budget = p ?? summary?.budget_vs_bom?.budget;
      if (bom != null && budget != null) detail = `BOM ${usd(bom)} vs ${usd(budget)} budget`;
    } else if (k === "throughput") {
      label = "Throughput";
      const target = p ?? t?.target;
      if (v != null && target != null) detail = `${num(v)}${unit} checked${t ? ` (${num(t.p50)} planned)` : ""} vs ${num(target)} target`;
    } else if (k === "layout") {
      label = "Layout";
      if (v != null) detail = `${num(v)} violation${v === 1 ? "" : "s"} found`;
    } else if (v != null) detail = `verifier: ${num(v)}${p != null ? ` vs claimed ${c.comparator ?? ""} ${num(p)}` : ""}`;
    const conf = c.confidence != null ? `agent was ${Math.round(c.confidence * 100)}% confident` : "";
    return `<div class="verdict ${esc(c.status)}" title="${esc([c.statement, c.verifier_note].filter(Boolean).join(" — "))}">
      <span class="v-status">${esc(c.status)}</span><span class="v-label">${esc(label)}</span>
      <span class="v-detail">${esc(detail || c.statement || "")}${conf ? ` <span class="muted">· ${esc(conf)}</span>` : ""}</span></div>`;
  }).join("");
  const refuted = checked.filter((c) => c.status === "refuted").length;
  return `<b>Verifier verdicts</b>
    <div class="v-sum ${refuted ? "warn" : "ok"}">${refuted ? `${refuted} of ${checked.length} claims refuted` : `All ${checked.length} claims supported`}${
      summary?.gate_passed && refuted ? " (the pipeline gate passed anyway: it checks the process ran, not that the lab meets the brief)" : ""}</div>
    ${rows}`;
}
