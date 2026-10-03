import "@fontsource/press-start-2p";
import Phaser from "phaser";
import { chat, exampleDesign, LIVE_CHAT_MESSAGE, leaderboard, liveCatalog, liveChat, optimise, prioritise, setOffline, validation } from "./api";
import demoQueue from "../../backend/labforge/catalog/data/demo_prioritise_queue.json";
import cachedDemoSchedule from "./fixtures/demo_schedule.json";
import { galleryDesign } from "./fixtures/gallery";
import { fixCard } from "./capacity";
import { renderLanding, summaryBox } from "./landing";
import { LabScene } from "./LabScene";
import { renderPanel } from "./panel";
import { openReport } from "./report";
import { emptyDesign, loadReplay, loadSummary, loadWhatIfCache, playReplay } from "./replay";
import { migrateLegacyLinks, parseRoute, routeKey, type Route } from "./router";
import { clock } from "./timeline";
import type { ChatMessage, Design, ProjectRequest, ProjectSchedule } from "./types";
import { dialogue, hideStatCard, introLines, onTick, setupClock, showStatCard } from "./ui";
import { closeModal, showError, showHtml, showLeaderboard, showLoading, showSchedule, showValidation, showWhatIf } from "./views";

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
game.events.on("select", (sel: { id: string; sprite?: string } | null) => (sel ? showStatCard(design, sel.id, sel.sprite) : hideStatCard()));

function show(d: Design) {
  design = d;
  game.scene.getScene("lab")?.scene.restart({ design });
  renderPanel(d);
  updateWhatIfButton();
}

/** One log entry per line, scrolled to the newest. */
function appendLog(line: string) {
  log.textContent += (log.textContent ? "\n\n" : "") + line;
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
  log.textContent = "";
  history = [];
  chatting = false;
  setOffline(false);
  setChatEnabled(r.page === "design");
  $<HTMLInputElement>("#chat-input").placeholder = "Describe your lab...";
  document.body.classList.toggle("page-view", ["bench", "validation", "schedule"].includes(r.page));
  document.body.classList.toggle("on-landing", r.page === "landing");
  landing.classList.toggle("hidden", r.page !== "landing");
  for (const a of document.querySelectorAll<HTMLAnchorElement>("#topnav a"))
    a.classList.toggle("active", a.dataset.route === routeKey(r));

  switch (r.page) {
    case "landing": return renderLanding(landing);
    case "case": return startReplay(r.name);
    case "design": {
      const d = exampleDesign();
      show(d);
      dialogue.say(["Describe the lab you want in the box on the right. Meanwhile, here is the worked example.", ...introLines(d)]);
      // With the backend up, use its catalog so BOM prices match /report; offline, keep examples/catalog.json.
      liveCatalog(d).then((catalog) => { if (route === r) show({ ...design, catalog }); }).catch(() => {});
      // Public demo (live_chat: false) or no backend: say so instead of offering a chat box that errors.
      liveChat().then((state) => {
        if (route !== r || state === "on") return;
        setChatEnabled(false);
        $<HTMLInputElement>("#chat-input").placeholder = state === "off" ? "Live design is off in this demo" : "Backend not reachable";
        appendLog(LIVE_CHAT_MESSAGE[state]);
        dialogue.say([LIVE_CHAT_MESSAGE[state], ...introLines(d)]);
      });
      if (r.whatif) openWhatIf(r.whatif);
      return;
    }
    case "gallery": show(galleryDesign); dialogue.say(["Sprite gallery: one of every instrument kind. Development view; not a real design."]); return;
    case "bench": return openBench();
    case "validation": return openValidation();
    case "schedule": return openSchedule();
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
    if (run.output.lab_spec) show(emptyDesign(run.output.lab_spec));
    await playReplay(run, {
      say: (lines, speaker) => live() && dialogue.say(lines, speaker),
      log: (line) => { if (live()) appendLog(line); },
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
        const fix = fixCard(d, summary);
        if (fix) { $("#fix").innerHTML = fix; $("#fix").classList.remove("hidden"); }
        dialogue.say(lines);
      },
      showAnswer: (title, html) => live() && showHtml(title, html),
    }, skip);
  } catch (e) {
    if (live()) dialogue.say([String((e as Error).message ?? e)]);
  }
  if (!live()) return;
  skipBtn.remove();
  // Playback is over: the what-if may now ask the backend (it falls back to the case's cached sweep offline).
  setOffline(false);
}

// ---- live chat ----------------------------------------------------------------------------------

$<HTMLFormElement>("#chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (chatting || route.page !== "design") return; // the form is also disabled outside #/design
  chatting = true;
  const input = $<HTMLInputElement>("#chat-input"), started = route;
  history.push({ role: "user", content: input.value });
  appendLog(`You: ${input.value}`);
  input.value = "";
  try {
    const out = await chat(history, design);
    if (route !== started) return;
    history = out.history;
    appendLog(`Agent: ${out.reply}`);
    show(out.design);
    hideStatCard();
    dialogue.say([out.reply]);
  } catch (error) {
    history.pop(); // the failed request was not committed to the conversation
    appendLog(error instanceof Error ? error.message : "Chat failed");
  } finally {
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

// ---- full-page views ----------------------------------------------------------------------------

async function openSchedule() {
  // Max's demo queue (three projects on one screening cell); offline, a cached /prioritise run of the same queue.
  const projects = demoQueue.projects as unknown as ProjectRequest[];
  showLoading("What order should these projects run in?");
  const { result, cached } = await prioritise(projects, demoQueue.lab_id, cachedDemoSchedule.schedule as ProjectSchedule);
  showSchedule(result, projects, cached);
}
async function openValidation() {
  showLoading("Does LabForge price real labs right?", "Comparing against published labs…");
  try { showValidation(await validation()); } catch { showError("Does LabForge price real labs right?", "Needs the backend (make backend)."); }
}
async function openBench() {
  showLoading("LabDesignBench", "Loading the leaderboard…");
  try { showLeaderboard(await leaderboard()); } catch { showError("LabDesignBench", "Needs the backend (make backend)."); }
}

go(route);
