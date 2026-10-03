import { clock } from "./timeline";
import type { CatalogItem, Confidence, Design, UncertainNumber } from "./types";

/** Strand A: Pokémon-style HTML overlay over the game: agent dialogue box and instrument stat card. Owner: Roshan. */

const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const money = (n?: number) => (n == null ? "?" : `$${Math.round(n).toLocaleString()}`);

function duration(s: number) {
  if (s < 120) return `${+s.toFixed(1)} s`;
  if (s < 7200) return `${+(s / 60).toFixed(1)} min`;
  return `${+(s / 3600).toFixed(1)} h`;
}

const BADGE: Record<Confidence, string> = { datasheet: "DATASHEET", literature: "LITERATURE", estimated: "ESTIMATE", placeholder: "PLACEHOLDER" };
function badge(c?: string) {
  if (!c) return `<span class="badge badge-unknown" title="No provenance given">UNSOURCED</span>`;
  return `<span class="badge badge-${esc(c)}">${BADGE[c as Confidence] ?? esc(c).toUpperCase()}</span>`;
}

/** Field confidence: per-field provenance if the catalog has it, else the item's overall confidence. */
function fieldConf(item: CatalogItem, path: string): { conf?: string; prov?: UncertainNumber } {
  const prov = item.provenance?.[path];
  return { conf: prov?.confidence ?? item.data_confidence, prov };
}

function range(prov: UncertainNumber | undefined, fmt: (n: number) => string) {
  return prov?.low != null && prov?.high != null ? ` <span class="range">(${fmt(prov.low)}–${fmt(prov.high)})</span>` : "";
}

// ---- dialogue box -----------------------------------------------------------------------------

class Dialogue {
  private pages: string[] = [];
  private typing?: number;
  private shown = 0;
  private el = document.querySelector<HTMLDivElement>("#dialogue")!;
  private text = this.el.querySelector<HTMLDivElement>(".text")!;

  constructor() {
    this.el.addEventListener("click", () => this.advance());
    window.addEventListener("keydown", (e) => {
      if ((e.key === " " || e.key === "Enter") && document.activeElement?.tagName !== "INPUT") { e.preventDefault(); this.advance(); }
    });
  }

  /** Queue agent text, split into pages that fit the box. Replaces anything unread. */
  say(lines: string[]) {
    this.pages = lines.flatMap(paginate);
    this.next();
  }

  private next() {
    clearInterval(this.typing);
    const page = this.pages.shift();
    this.el.classList.toggle("hidden", page == null);
    if (page == null) return;
    this.el.classList.remove("done");
    this.el.classList.toggle("more", this.pages.length > 0);
    this.shown = 0;
    this.typing = window.setInterval(() => {
      this.shown += 2;
      this.text.textContent = page.slice(0, this.shown);
      if (this.shown >= page.length) { clearInterval(this.typing); this.typing = undefined; this.el.classList.add("done"); }
    }, 18);
    this.text.dataset.full = page;
  }

  private advance() {
    if (this.typing != null) {
      clearInterval(this.typing); this.typing = undefined;
      this.text.textContent = this.text.dataset.full ?? "";
      this.el.classList.add("done");
    } else this.next();
  }
}

function paginate(line: string): string[] {
  const words = line.split(/\s+/).filter(Boolean), pages: string[] = [];
  let cur = "";
  for (const w of words) {
    if ((cur + " " + w).trim().length > 150) { pages.push(cur); cur = w; } else cur = (cur + " " + w).trim();
  }
  if (cur) pages.push(cur);
  return pages;
}

export const dialogue = new Dialogue();

/** What the agent says when a design appears: headline, uncertainty, bottlenecks and what it doesn't trust. */
export function introLines(d: Design): string[] {
  const t = d.sim_result.throughput, items = d.workflow.equipment.map((e) => d.catalog[e.catalog_id]).filter(Boolean);
  const total = items.reduce((s, i) => s + (i.price_usd_estimate ?? 0), 0);
  const lines = [`Here's your lab: ${items.length} pieces of equipment, about ${money(total)} in total.`];
  const band = t.p10 != null && t.p90 != null ? ` (P10–P90: ${t.p10}–${t.p90})` : "";
  let tput = `I expect ${t.p50 ?? t.value} ${t.unit}${band}.`;
  if (t.target != null && t.prob_meets_target != null) tput += ` Chance of hitting your target of ${t.target}: ${Math.round(t.prob_meets_target * 100)}%.`;
  lines.push(tput);
  for (const b of d.sim_result.bottlenecks) lines.push(b.suggestion ? `${b.message} ${b.suggestion}` : b.message);
  const shaky = items.filter((i) => i.data_confidence === "estimated" || i.data_confidence === "placeholder" || !i.data_confidence);
  if (shaky.length)
    lines.push(`Careful: specs for ${shaky.length} of ${items.length} items are estimates or placeholders, not datasheet values. Click an instrument to see which numbers I don't trust.`);
  return lines;
}

// ---- stat card --------------------------------------------------------------------------------

const card = document.querySelector<HTMLDivElement>("#statcard")!;
card.addEventListener("click", (e) => { if ((e.target as HTMLElement).closest(".close")) hideStatCard(); });
window.addEventListener("keydown", (e) => { if (e.key === "Escape") hideStatCard(); });

export function hideStatCard() { card.classList.add("hidden"); }

export function showStatCard(d: Design, instanceId: string, sprite?: string) {
  const eq = d.workflow.equipment.find((e) => e.instance_id === instanceId);
  const op = d.layout.operators?.find((o) => o.id === instanceId);
  const item = eq && d.catalog[eq.catalog_id];
  const util = d.sim_result.utilisation.find((u) => u.instance_id === instanceId);
  const flagged = d.sim_result.bottlenecks.filter((b) => b.instances?.includes(instanceId));
  const img = sprite ? `<img class="sprite" src="${sprite}" alt="" />` : "";

  let body = "";
  if (item) {
    const price = fieldConf(item, "price_usd_estimate");
    body += `<div class="row"><span>Price</span><span>${money(item.price_usd_estimate)}${range(price.prov, money)} ${badge(price.conf)}</span></div>`;
    const cap = item.process?.capacity ?? 1;
    for (const [capName, s] of Object.entries(item.process?.durations_s ?? {})) {
      const f = fieldConf(item, `process.durations_s.${capName}`);
      const perH = (cap * 3600) / s;
      body += `<div class="row"><span>${esc(capName.replace(/_/g, " "))}</span><span>${duration(s)}${range(f.prov, duration)}/plate ${badge(f.conf)}</span></div>
        <div class="sub">≈ ${perH >= 10 ? Math.round(perH) : +perH.toFixed(1)} plates/h${cap > 1 ? ` · ${cap} at once` : ""}</div>`;
    }
    if (item.transport?.speed_m_s) {
      const f = fieldConf(item, "transport.speed_m_s");
      body += `<div class="row"><span>Speed</span><span>${item.transport.speed_m_s} m/s ${badge(f.conf)}</span></div>`;
    }
    if (item.integration?.length) body += `<div class="row"><span>Control</span><span>${item.integration.map(esc).join(", ")}</span></div>`;
  } else if (op) {
    body += `<div class="row"><span>Role</span><span>${esc(op.role)}</span></div>
      <div class="sub">Human operator: a slow but flexible transporter who also runs the manual steps.</div>`;
  }
  if (util) {
    const pct = Math.round(util.busy_fraction * 100);
    const tone = pct >= 85 ? "red" : pct >= 60 ? "yellow" : "green";
    body += `<div class="row"><span>BUSY</span><span class="hp"><span class="hp-fill hp-${tone}" style="width:${pct}%"></span></span><span>${pct}%</span></div>`;
    if (util.mean_queue_wait_s) body += `<div class="sub">Plates wait ${duration(util.mean_queue_wait_s)} on average.</div>`;
  }
  for (const b of flagged) body += `<div class="warn">⚠ ${esc(b.message)}</div>`;
  if (eq?.rationale) body += `<div class="why">“${esc(eq.rationale)}”</div>`;
  if (item) body += `<button class="whatif" data-id="${esc(instanceId)}">How could this be better?</button>`;

  const title = item ? `${esc(item.vendor)} ${esc(item.model)}` : op ? esc(op.role) : esc(instanceId);
  card.innerHTML = `<button class="close" aria-label="Close">✕</button>
    <div class="head">${img}<div><div class="name">${title}</div><div class="id">${esc(instanceId)}${item ? ` · ${badge(item.data_confidence)}` : ""}</div></div></div>
    ${body}`;
  card.classList.remove("hidden");
}

// ---- time controls ----------------------------------------------------------------------------

const bar = document.querySelector<HTMLDivElement>("#clockbar")!;
const play = bar.querySelector<HTMLButtonElement>("#play")!, scrub = bar.querySelector<HTMLInputElement>("#scrub")!;
const hms = (s: number) => [s / 3600, (s / 60) % 60, s % 60].map((n) => String(Math.floor(n)).padStart(2, "0")).join(":");
let scrubbing = false;

function setPlaying(on: boolean) { clock.playing = on; play.textContent = on ? "❚❚" : "▶"; }
play.addEventListener("click", () => setPlaying(!clock.playing));
window.addEventListener("keydown", (e) => { if (e.key === "p" && document.activeElement?.tagName !== "INPUT") setPlaying(!clock.playing); });
bar.querySelector<HTMLSelectElement>("#speed")!.addEventListener("change", (e) => { clock.speed = +(e.target as HTMLSelectElement).value; });
scrub.addEventListener("input", () => { scrubbing = true; clock.t = (+scrub.value / 1000) * clock.end; });
scrub.addEventListener("change", () => { scrubbing = false; });

/** Show the controls only when there is a timeline to play; note where it came from. */
export function setupClock(d: Design) {
  bar.classList.toggle("hidden", clock.end <= 0);
  bar.querySelector("#clock-src")!.textContent = d.timeline_note ?? "simulator";
}

export function onTick(e: { t: number; end: number; done: number; moving: number }) {
  bar.querySelector("#clock-t")!.textContent = `T+${hms(e.t)}`;
  bar.querySelector("#clock-done")!.textContent = `${e.done} plates done · ${e.moving} moving`;
  if (!scrubbing) scrub.value = String(Math.round((1000 * e.t) / Math.max(1, e.end)));
}
