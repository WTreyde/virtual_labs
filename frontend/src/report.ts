import { marked } from "marked";
import { report } from "./api";
import type { Design } from "./types";

/**
 * Strand A: the "Report" button. Renders the /report Markdown as a printable page with a snapshot of
 * the lab scene; the browser's print dialog saves it as PDF. Works offline with a clearly labelled draft.
 */

/** Markdown built from the design alone, for when the backend (and the agent's report) is unavailable. */
function offlineDraft(d: Design): string {
  const t = d.sim_result.throughput;
  const rows = d.workflow.equipment.map((e) => {
    const i = d.catalog[e.catalog_id];
    return `| ${e.instance_id} | ${i?.vendor ?? "?"} | ${i?.model ?? e.catalog_id} | ${i?.price_usd_estimate?.toLocaleString() ?? "Unknown"} | ${i?.data_confidence ?? "unsourced"} |`;
  });
  const total = d.workflow.equipment.reduce((s, e) => s + (d.catalog[e.catalog_id]?.price_usd_estimate ?? 0), 0);
  return [
    `# ${d.lab_spec?.name ?? "Lab design"}: offline draft`,
    "",
    "> **Draft built in the browser because the backend was not reachable.** It lists what the client already has; it has no checked claims, evidence or assumptions. Generate the full report with the backend running.",
    "",
    "## Bill of materials",
    "",
    "| Instance | Vendor | Model | Est. price (USD) | Data confidence |",
    "|---|---|---|---|---|",
    ...rows,
    `| **Known-price subtotal** | | | **${total.toLocaleString()}** | |`,
    "",
    "## Throughput",
    "",
    `Median ${t.p50 ?? t.value} ${t.unit}; P10 ${t.p10 ?? "?"}; P90 ${t.p90 ?? "?"}. Probability of meeting the target: ${t.prob_meets_target ?? "?"}.`,
    "",
    "## Bottlenecks",
    "",
    ...(d.sim_result.bottlenecks.length ? d.sim_result.bottlenecks.map((b) => `- **${b.severity}**: ${b.message}${b.suggestion ? ` ${b.suggestion}` : ""}`) : ["- None reported."]),
  ].join("\n");
}

/**
 * In the report's Evidence section keep only items with a real link. Search bookkeeping with no source
 * ("Literature search `...`: unavailable / retrieved", "reviewed"-only lines) is dropped; if nothing is left,
 * the section says so instead of listing searches that found nothing usable.
 */
export function linkedEvidenceOnly(md: string): string {
  return md.replace(/(^## Evidence[^\n]*\n)([\s\S]*?)(?=^## |(?![\s\S]))/m, (_, head: string, body: string) => {
    const lines = body.split("\n");
    const items = lines.filter((l) => /^\s*[-*] /.test(l));
    const linked = items.filter((l) => /https?:\/\/\S+/.test(l));
    const prose = lines.filter((l) => l.trim() && !/^\s*[-*] /.test(l));
    const dropped = items.length - linked.length;
    const note = dropped ? `\n_${dropped} search ${dropped === 1 ? "entry" : "entries"} without a source link not shown._\n` : "";
    return `${head}\n${prose.join("\n")}${prose.length ? "\n\n" : ""}${linked.length ? linked.join("\n") : "No linked evidence: durations and yields remain estimates."}\n${note}\n`;
  });
}

const PAGE_CSS = `
  body { font: 14px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; color: #1d2330; max-width: 860px; margin: 32px auto; padding: 0 24px; background: #fff; }
  .bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; }
  .bar button { font: inherit; padding: 8px 14px; border: 2px solid #2b2f36; border-radius: 6px; background: #fbfbf5; cursor: pointer; }
  .meta { color: #667; font-size: 12px; }
  .scene { width: 100%; border: 3px solid #2b2f36; border-radius: 8px; image-rendering: pixelated; margin: 8px 0 4px; }
  .caption { color: #667; font-size: 12px; margin-bottom: 16px; }
  h1 { font-size: 24px; margin: 8px 0 4px; } h2 { font-size: 17px; margin-top: 28px; border-bottom: 2px solid #e2e4e8; padding-bottom: 4px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 8px 0; }
  th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid #e2e4e8; } th { background: #f4f5f7; }
  td:nth-child(4) { text-align: right; font-variant-numeric: tabular-nums; }
  blockquote { margin: 12px 0; padding: 8px 14px; border-left: 4px solid #e0503c; background: #fdf1ef; }
  @media print { .bar button { display: none; } body { margin: 0 auto; } h2 { break-after: avoid; } table, img { break-inside: avoid; } }
`;

/**
 * Opens the report window. The window is opened synchronously in the click handler so popup blockers allow it,
 * then filled once the snapshot and /report arrive.
 */
export async function openReport(d: Design, snapshot: () => Promise<string | undefined>) {
  const w = window.open("", "_blank");
  if (!w) return alert("Allow pop-ups for this page to open the report.");
  w.document.write(`<!doctype html><title>Generating report…</title><body style="font:16px system-ui;padding:40px">Generating report…</body>`);

  const [img, md] = await Promise.all([
    snapshot().catch(() => undefined),
    report(d).then((text) => ({ text, live: !d.report_markdown })).catch(() => ({ text: offlineDraft(d), live: false })),
  ]);
  const title = String(d.lab_spec?.name ?? "Lab design");
  const when = new Date().toLocaleString();
  w.document.open();
  w.document.write(`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${title.replace(/</g, "&lt;")}: lab proposal</title>
    <style>${PAGE_CSS}</style></head><body>
    <div class="bar"><span class="meta">LabForge · ${when} · ${d.report_markdown ? "report from a recorded agent run" : md.live ? "report from the agent backend" : "offline draft"}</span>
      <button onclick="print()">Print / Save as PDF</button></div>
    ${img ? `<img class="scene" src="${img}" alt="Isometric view of the proposed lab layout"><div class="caption">Proposed layout as shown in LabForge. Instrument sizes follow catalog footprints; art is schematic.</div>` : ""}
    ${await marked.parse(linkedEvidenceOnly(md.text).replace(/</g, "&lt;"))}
    </body></html>`);
  w.document.close();
}
