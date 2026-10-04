import "@fontsource/press-start-2p";
import Phaser from "phaser";
import { benchTasks, catalogItems, catalogNames, chatStream, exampleDesign, health, HttpError, LIVE_CHAT_MESSAGE, leaderboard, liveCatalog, optimise, prioritise, setOffline, validation } from "./api";
import demoQueue from "../../backend/labforge/catalog/data/demo_prioritise_queue.json";
import cachedDemoSchedule from "./fixtures/demo_schedule.json";
import { galleryDesign } from "./fixtures/gallery";
import { fixCard } from "./capacity";
import { verdictsBox } from "./verdicts";
import { AgentLog } from "./agentlog";
import { CASES, renderCases, renderLanding, summaryBox } from "./landing";
import { LabScene } from "./LabScene";
import { renderPanel } from "./panel";
import { openReport } from "./report";
import { protocolsFor, renderProtocol, renderProtocolList } from "./protocols";
import { describe, emptyDesign, loadReplay, loadSummary, loadWhatIfCache, playReplay } from "./replay";
import { migrateLegacyLinks, parseRoute, routeKey, type Route } from "./router";
import { clock } from "./timeline";
import type { ChatMessage, Design, ProjectRequest, ProjectSchedule } from "./types";
import { dialogue, hideStatCard, introLines, onTick, setupClock, showStatCard } from "./ui";
import { closeModal, openModal, showError, showHtml, showLeaderboard, showLoading, showSchedule, showValidation, showWhatIf } from "./views";

/**
 * Strand A: the one-page app. Hash routes (see router.ts) pick what the shared game, panel and modal show:
 * the landing page, a recorded case (replay), live design chat, or a full-page view (bench, validation, schedule).
 */

migrateLegacyLinks();
const params = new URLSearchParams(location.search);
clock.t = +(params.get("t") ?? 0) || 0; // ?t=<sim seconds> starts mid-run, handy for screenshots

let design: Design = emptyDesign();
let history: ChatMessage[] = [];
let chatting = false;
let route: Route = parseRoute();
let replayToken = 0; // bumped on every route change so a replay still running stops touching the page
let replaySkip = { now: false };

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;
const log = $<HTMLDivElement>("#log");
const badge = $<HTMLDivElement>("#replay-badge");
const landing = $<HTMLElement>("#landing");

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game",
  backgroundColor: "#1d2b2f",
  pixelArt: true,
  scale: { mode: Phaser.Scale.RESIZE, width: window.innerWidth - 340, height: window.innerHeight },
  scene: [],
});
// The font is bundled, but a sandbox or locked-down network can still block or stall the file. Start anyway after
// at most 2 s; Phaser text then uses the monospace fallback. Catching the rejection avoids an unhandled NetworkError.
// The scene reads `design` when it starts, so whatever the route has shown by then is picked up.
const fontReady = Promise.race([document.fonts.load('8px "Press Start 2P"'), new Promise((r) => setTimeout(r, 2000))]);
fontReady.catch(() => undefined).then(() => game.scene.add("lab", LabScene, true, { design }));
game.events.on("tick", onTick);
game.events.on("ready-clock", () => setupClock(design));
game.events.on("select", (sel: { id: string; sprite?: string } | null) => {
  if (!sel) return hideStatCard();
  showStatCard(design, sel.id, sel.sprite);
});

// ---- side panel accordion: the brief and the throughput share the top of the panel ------------------

type Acc = "brief" | "metrics";
/** Open one section and fold the other; `null` folds both. */
function openAcc(which: Acc | null) {
  for (const k of ["brief", "metrics"] as Acc[]) {
    const sec = $(`#${k}-acc`), on = k === which;
    sec.classList.toggle("open", on);
    sec.querySelector(".acc-head")!.setAttribute("aria-expanded", String(on));
  }
}
for (const k of ["brief", "metrics"] as Acc[])
  $(`#${k}-acc .acc-head`).addEventListener("click", () => openAcc($(`#${k}-acc`).classList.contains("open") ? null : k));

// ---- top nav: "Menu" dropdown on phones, "Case studies" dropdown everywhere -------------------------

const menuBtn = $<HTMLButtonElement>("#menu-btn"), topnav = $("#topnav");
function setMenu(open: boolean) {
  topnav.classList.toggle("menu-open", open);
  menuBtn.setAttribute("aria-expanded", String(open));
}
menuBtn.addEventListener("click", (e) => { e.stopPropagation(); setMenu(!topnav.classList.contains("menu-open")); });
document.addEventListener("click", (e) => { if (!topnav.contains(e.target as Node)) setMenu(false); });
window.addEventListener("keydown", (e) => { if (e.key === "Escape") setMenu(false); });

function show(d: Design) {
  design = d;
  game.scene.getScene("lab")?.scene.restart({ design });
  renderPanel(d);
  updateWhatIfButton();
  updateProtocolsPanel(d);
}

/** "Protocols for this lab": published protocols covering this design's capabilities (client-side for_workflow). */
async function updateProtocolsPanel(d: Design) {
  const box = $("#protocols-for");
  const caps = [...new Set(d.workflow.equipment.flatMap((e) => d.catalog[e.catalog_id]?.capabilities ?? []))];
  const found = caps.length ? await protocolsFor(caps) : [];
  if (design !== d) return;
  box.classList.toggle("hidden", !found.length);
  box.innerHTML = found.length ? `<b>Protocols for this lab</b><ul>${found.map(({ row, matched }) =>
    `<li><a href="#/protocols/${encodeURIComponent(row.id)}">${row.title.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`)}</a><div class="muted">covers ${matched.map((c) => c.replace(/_/g, " ")).join(", ")}</div></li>`).join("")}</ul>` : "";
}

/** One log entry per line, scrolled to the newest. */
const agentLog = new AgentLog(log);
function appendLog(line: string, kind: "user" | "agent" | "notice" | "declined" = "notice") {
  agentLog.note(line, kind);
  log.scrollTop = log.scrollHeight;
}

const setChatEnabled = (on: boolean) => {
  for (const el of document.querySelectorAll<HTMLInputElement | HTMLButtonElement>("#chat-input, #chat-form button")) el.disabled = !on;
};

// ---- routing ------------------------------------------------------------------------------------

async function go(r: Route) {
  route = r;
  replayToken++;
  replaySkip.now = true;
  closeModal();
  hideStatCard();
  badge.classList.add("hidden");
  badge.querySelector("button")?.remove();
  $("#checked").classList.add("hidden");
  $("#fix").classList.add("hidden");
  $("#verdicts").classList.add("hidden");
  $("#brief-acc").classList.add("hidden");
  openAcc("metrics");
  setMenu(false);
  $("#skill-btn").classList.add("hidden");
  $("#agent-banner").classList.add("hidden");
  agentLog.clear();
  history = [];
  chatting = false;
  setOffline(false);
  setChatEnabled(r.page === "design");
  $<HTMLInputElement>("#chat-input").placeholder = "Describe your lab...";
  document.body.classList.toggle("page-view", ["bench", "validation", "schedule", "protocols"].includes(r.page));
  const onLanding = r.page === "landing" || r.page === "cases";
  document.body.classList.toggle("on-landing", onLanding);
  landing.classList.toggle("hidden", !onLanding);
  for (const a of document.querySelectorAll<HTMLAnchorElement>("#topnav a"))
    a.classList.toggle("active", a.dataset.route === routeKey(r));
  $(".nav-group[data-group=case]").classList.toggle("active", r.page === "case" || r.page === "cases");

  switch (r.page) {
    case "landing": return renderLanding(landing);
    case "cases": return renderCases(landing);
    case "case": return startReplay(r.name);
    case "design": {
      const d = exampleDesign();
      show(d);
      dialogue.say(["Describe the lab you want in the box on the right. Meanwhile, here is the worked example.", ...introLines(d)]);
      // With the backend up, use its catalog so BOM prices match /report; offline, keep examples/catalog.json.
      liveCatalog(d).then((catalog) => { if (route === r) show({ ...design, catalog }); }).catch(() => {});
      // Public demo (live_chat: false) or no backend: say so instead of offering a chat box that errors.
      health().then(({ state, liveAgent, note }) => {
        if (route !== r) return;
        if (state !== "on") {
          setChatEnabled(false);
          $<HTMLInputElement>("#chat-input").placeholder = state === "off" ? "Live design is off in this demo" : "Backend not reachable";
          appendLog(LIVE_CHAT_MESSAGE[state]);
          dialogue.say([LIVE_CHAT_MESSAGE[state], ...introLines(d)]);
        } else if (!liveAgent) {
          // Chat still answers, but with the offline worked example: say so plainly instead of pretending.
          const banner = $("#agent-banner");
          banner.textContent = note ?? "Live agent off: the backend has no API key, so replies use the offline worked example.";
          banner.classList.remove("hidden");
        }
      });
      if (r.whatif) openWhatIf(r.whatif);
      return;
    }
    case "gallery": show(galleryDesign); dialogue.say(["Sprite gallery: one of every instrument kind. Development view; not a real design."]); return;
    case "bench": return openBench();
    case "validation": return openValidation();
    case "schedule": return openSchedule();
    case "protocols": return openProtocols(r.id);
  }
}
window.addEventListener("hashchange", () => go(parseRoute()));
// Clicking the nav link of the page you're on restarts it (no hashchange fires for the same hash).
for (const a of document.querySelectorAll<HTMLAnchorElement>("#topnav a"))
  a.addEventListener("click", () => { if (a.getAttribute("href") === location.hash) go(parseRoute()); });

// ---- case pages: recorded runs ------------------------------------------------------------------

async function startReplay(name: string) {
  const token = replayToken, skip = { now: false };
  replaySkip = skip;
  const live = () => token === replayToken;
  setOffline(true); // the replay itself never calls the backend
  badge.classList.remove("hidden");
  const skipBtn = document.createElement("button");
  skipBtn.id = "replay-skip";
  skipBtn.textContent = "Skip ▸▸";
  skipBtn.addEventListener("click", () => { skip.now = true; });
  badge.append(skipBtn);
  show(emptyDesign());
  try {
    const [run, whatif, summary] = await Promise.all([loadReplay(name), loadWhatIfCache(name), loadSummary(name)]);
    if (!live()) return;
    badge.querySelector(".text")!.textContent = `Replay of a recorded run${run.model ? ` · ${run.model}` : ""}`;
    showBrief(name, run.brief, summary?.brief);
    if (run.output.lab_spec) show(emptyDesign(run.output.lab_spec));
    await playReplay(run, {
      say: (lines, speaker) => live() && dialogue.say(lines, speaker),
      log: (line, kind) => { if (live()) appendLog(line, kind); },
      event: (e) => { if (live()) agentLog.event(e); },
      showDesign: (d) => {
        if (!live()) return;
        show({ ...d, whatif_cache: whatif });
        const lines = introLines(d);
        if (summary) {
          // Planned vs independently checked, and the recorded limits, shown with the design (not only on the landing card).
          const box = $("#checked");
          box.innerHTML = summaryBox(summary);
          box.classList.remove("hidden");
          const t = summary.headline_throughput;
          if (t.verified_p50 != null)
            lines.push(`Careful: my planning simulation says ${Math.round(t.p50)}, but an independent check of the same design gives ${Math.round(t.verified_p50)} ${t.unit.replace(/_/g, " ")}. The limits are listed on the right.`);
        }
        const verdicts = verdictsBox(run.output.claims, summary);
        if (verdicts) { $("#verdicts").innerHTML = verdicts; $("#verdicts").classList.remove("hidden"); }
        const fix = fixCard(d, summary);
        if (fix) { $("#fix").innerHTML = fix; $("#fix").classList.remove("hidden"); }
        dialogue.say(lines);
      },
      showAnswer: (title, html) => live() && showHtml(title, html),
    }, skip);
    if (live()) agentLog.finish();
  } catch (e) {
    if (live()) dialogue.say([String((e as Error).message ?? e)]);
  }
  if (!live()) return;
  skipBtn.remove();
  if (await skillAvailable(name) && live()) {
    const btn = $<HTMLButtonElement>("#skill-btn");
    btn.classList.remove("hidden");
    btn.onclick = () => downloadSkill(name);
  }
  // Playback is over: the what-if may now ask the backend (it falls back to the case's cached sweep offline).
  setOffline(false);
}

/**
 * Keep the case's problem statement in the side panel for the whole replay: the case title, the short brief from
 * the summary, and the agent's full brief behind a toggle. Open by default; the Throughput bar below folds it away.
 */
function showBrief(name: string, full: string, short?: string) {
  const el = $("#brief"), title = CASES.find((c) => c.name === name)?.title ?? name;
  const esc = (v: string) => v.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
  el.innerHTML = `<div class="brief-title">${esc(title)}</div>
    <p class="brief-short">${esc(short ?? full.split(/(?<=\.)\s/)[0])}</p>
    <details><summary>Full brief</summary><p class="brief-full">${esc(full)}</p></details>`;
  $("#brief-acc").classList.remove("hidden");
  openAcc("brief");
}

// ---- live chat ----------------------------------------------------------------------------------

$<HTMLFormElement>("#chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (chatting || route.page !== "design") return; // the form is also disabled outside #/design
  chatting = true;
  const input = $<HTMLInputElement>("#chat-input"), started = route;
  history.push({ role: "user", content: input.value });
  appendLog(`You: ${input.value}`, "user");
  input.value = "";
  try {
    // Stream the agent's steps into the log and dialogue box as they happen.
    let writing = false;
    const out = await chatStream(history, design, (ev) => {
      if (route !== started) return;
      if (ev.type === "text_delta") {
        if (!writing) { writing = true; dialogue.say(["Writing the answer…"]); }
        return;
      }
      agentLog.event(ev); // structured log: steps, tool calls, status, timings
      const line = describe(ev);
      if (!line) return;
      dialogue.say([line]);
      writing = false;
    });
    if (route !== started) return;
    history = out.history;
    if (out.declined) {
      // A refusal is the model's answer, not a failure: say so plainly and keep the lab on screen as it was.
      agentLog.declineLast();
      appendLog(`The model declined this request. ${out.declined}`, "declined");
      dialogue.say(["The model declined this request.", out.declined]);
      return;
    }
    appendLog(`Agent: ${out.reply}`, "agent");
    show(out.design);
    hideStatCard();
    dialogue.say([out.reply]);
  } catch (error) {
    history.pop(); // the failed request was not committed to the conversation
    appendLog(error instanceof Error ? error.message : "Chat failed");
  } finally {
    agentLog.finish();
    chatting = false;
  }
});

// ---- report and what-if -------------------------------------------------------------------------

$("#report-btn").addEventListener("click", () => {
  const snapshot = () => new Promise<string | undefined>((resolve) =>
    game.renderer.snapshot((img) => resolve(img instanceof HTMLImageElement ? img.src : undefined)));
  openReport(design, snapshot);
});

async function openWhatIf(id: string) {
  const eq = design.workflow.equipment.find((x) => x.instance_id === id), item = eq && design.catalog[eq.catalog_id];
  const name = item ? item.model : id, title = `How could ${name} be better?`;
  showLoading(title);
  try {
    const { result, cached } = await optimise(design, id);
    showWhatIf(result, name, design.lab_spec?.throughput_target?.value, cached);
    if (result.headroom_note) dialogue.say([result.headroom_note]);
  } catch {
    showError(title, "Needs the backend (make backend); there is no cached sweep for this instrument.");
  }
}
// "Show the <instrument>" on the fix card opens that instrument's stat card, as clicking it in the scene would.
$("#fix").addEventListener("click", (e) => {
  const id = (e.target as HTMLElement).closest<HTMLElement>(".fix-show")?.dataset.id;
  if (id) game.events.emit("select-id", id);
});
$("#statcard").addEventListener("click", (e) => {
  const id = (e.target as HTMLElement).closest<HTMLElement>(".whatif")?.dataset.id;
  if (id) openWhatIf(id);
});

/** One click from the final design to the what-if for its main bottleneck instrument. */
const SEVERITY: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
function updateWhatIfButton() {
  const btn = $<HTMLButtonElement>("#whatif-btn");
  const ids = new Set(design.workflow.equipment.map((e) => e.instance_id));
  const b = [...design.sim_result.bottlenecks].filter((x) => x.kind !== "long_transfer" && ids.has(x.instances?.[0] ?? ""))
    .sort((x, y) => (SEVERITY[x.severity] ?? 9) - (SEVERITY[y.severity] ?? 9))[0];
  btn.classList.toggle("hidden", !b);
  if (!b) return;
  const id = b.instances![0], eq = design.workflow.equipment.find((e) => e.instance_id === id);
  btn.textContent = `What if ${(eq && design.catalog[eq.catalog_id]?.model) ?? id} were better?`;
  btn.onclick = () => openWhatIf(id);
}

// ---- agent skill download ---------------------------------------------------------------------

// Each case ships the agent skill generated from its digital twin (public/skills/<case>/, copied from
// backend/labforge/orchestrator/samples by scripts/copy_skills.py), so the download works offline.
const SKILL_FILES = ["SKILL.md", "tools.json"];
const skillUrl = (name: string, file: string) => `${(import.meta as any).env?.BASE_URL ?? "/"}skills/${encodeURIComponent(name)}/${file}`;

async function skillAvailable(name: string) {
  try {
    const res = await fetch(skillUrl(name, "SKILL.md"), { method: "HEAD" });
    return res.ok && !(res.headers.get("content-type") ?? "").includes("text/html"); // dev servers answer misses with index.html
  } catch { return false; }
}

async function downloadSkill(name: string) {
  for (const file of SKILL_FILES) {
    const res = await fetch(skillUrl(name, file));
    if (!res.ok) continue;
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: file });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    await new Promise((r) => setTimeout(r, 300)); // browsers drop back-to-back downloads
  }
}

// ---- full-page views ----------------------------------------------------------------------------

async function openSchedule() {
  // Max's demo queue (three projects on one screening cell); offline, a cached /prioritise run of the same queue.
  const projects = demoQueue.projects as unknown as ProjectRequest[];
  showLoading("What order should these projects run in?");
  const { result, cached } = await prioritise(projects, demoQueue.lab_id, cachedDemoSchedule.schedule as ProjectSchedule);
  showSchedule(result, projects, cached);
}
/** #/protocols (list) and #/protocols/<id> (detail), static files from public/protocols/. */
async function openProtocols(id?: string) {
  openModal(id ? "Protocol" : "Protocols", `<div id="proto-root"><p class="muted">Loading…</p></div>`, true);
  const root = $("#proto-root"), r = route;
  if (!id) return renderProtocolList(root);
  const extra = await Promise.all(["chem", "fbdd"].map((n) => loadReplay(n).then((x) => x.catalog ?? {}).catch(() => ({}))));
  const catalog = await catalogItems(extra);
  if (route !== r) return;
  await renderProtocol(root, id, catalog);
  const h2 = document.querySelector("#modal h2"), title = root.querySelector<HTMLElement>(".proto-head")?.dataset.title;
  if (h2 && title) h2.textContent = title;
  // Equipment chips open the catalog stat card, as clicking the instrument in the lab would.
  root.addEventListener("click", (e) => {
    const cid = (e.target as HTMLElement).closest<HTMLElement>(".equip[data-cid]")?.dataset.cid;
    if (!cid) return;
    const d = emptyDesign();
    d.catalog = catalog;
    d.workflow = { id: "protocol", equipment: [{ instance_id: cid, catalog_id: cid }] };
    showStatCard(d, cid);
  });
}

async function openValidation() {
  showLoading("Does LabForge price real labs right?", "Comparing against published labs…");
  try {
    const [rows, names] = await Promise.all([validation(), catalogNames()]);
    showValidation(rows, names);
  } catch (e) {
    showError("Does LabForge price real labs right?", e instanceof HttpError ? `The backend returned an error (${e.status}).` : "Needs the backend (make backend).");
  }
}
async function openBench() {
  showLoading("LabDesignBench", "Loading the leaderboard…");
  try {
    const [board, tasks] = await Promise.all([leaderboard(), benchTasks()]);
    showLeaderboard(board, tasks);
  } catch (e) {
    showError("LabDesignBench", e instanceof HttpError ? `The backend returned an error (${e.status}).` : "Needs the backend (make backend).");
  }
}

go(route);
