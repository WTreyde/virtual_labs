import "@fontsource/press-start-2p";
import Phaser from "phaser";
import { chat, exampleDesign, leaderboard, liveCatalog, optimise, prioritise, setOffline, validation } from "./api";
import { exampleProjects } from "./fixtures/projects";
import { galleryDesign } from "./fixtures/gallery";
import { LabScene } from "./LabScene";
import { openReport } from "./report";
import { emptyDesign, loadReplay, playReplay } from "./replay";
import { showError, showHtml, showLeaderboard, showLoading, showSchedule, showValidation, showWhatIf } from "./views";
import { clock } from "./timeline";
import { renderPanel } from "./panel";
import type { ChatMessage, Design } from "./types";
import { dialogue, hideStatCard, introLines, onTick, setupClock, showStatCard } from "./ui";

// `?demo=gallery` shows every sprite kind; the default is the worked example from examples/.
const params = new URLSearchParams(location.search);
clock.t = +(params.get("t") ?? 0) || 0; // ?t=<sim seconds> starts mid-run, handy for screenshots
// `?replay=<name>` plays a recorded agent run from public/replays/ with no backend calls.
const replay = params.get("replay");
if (replay) setOffline(true);
let design: Design = replay ? emptyDesign() : params.get("demo") === "gallery" ? galleryDesign : exampleDesign();
let history: ChatMessage[] = [];
let chatting = false;

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game",
  backgroundColor: "#1d2b2f",
  pixelArt: true,
  scale: { mode: Phaser.Scale.RESIZE, width: window.innerWidth - 340, height: window.innerHeight },
  scene: [],
});
// Wait for the pixel font so Phaser text doesn't bake in the fallback face.
// ?view=bench and ?view=validation are full-page views (the demo opens them in their own tab): no game behind them.
const pageView = ["bench", "validation"].includes(params.get("view") ?? "");
if (pageView) document.body.classList.add("page-view");
else {
  // The font is bundled, but a sandbox or locked-down network can still block or stall the file. Start anyway after
  // at most 2 s; Phaser text then uses the monospace fallback. Catching the rejection avoids an unhandled NetworkError.
  const fontReady = Promise.race([document.fonts.load('8px "Press Start 2P"'), new Promise((r) => setTimeout(r, 2000))]);
  fontReady.catch(() => undefined).then(() => game.scene.add("lab", LabScene, true, { design }));
}
// (reads `design` when the font is ready, so a replay that has already moved on is picked up)
renderPanel(design);
if (!replay && !pageView) dialogue.say(introLines(design));
// With the backend up, use its catalog so BOM prices match /report; offline, keep examples/catalog.json.
if (!params.get("demo") && !replay) liveCatalog(design).then((catalog) => { design = { ...design, catalog }; renderPanel(design); if (!params.get("view")) dialogue.say(introLines(design)); }).catch(() => {});
game.events.on("tick", onTick);
game.events.on("ready-clock", () => setupClock(design));
game.events.on("select", (sel: { id: string; sprite?: string } | null) => (sel ? showStatCard(design, sel.id, sel.sprite) : hideStatCard()));

function show(d: Design) {
  design = d;
  // Before the font has loaded the scene doesn't exist yet; it will start with the current `design`.
  game.scene.getScene("lab")?.scene.restart({ design });
  renderPanel(d);
}

const log = document.querySelector<HTMLDivElement>("#log")!;

if (replay) startReplay(replay);
async function startReplay(name: string) {
  const badge = document.querySelector<HTMLDivElement>("#replay-badge")!, skip = { now: false };
  badge.classList.remove("hidden");
  badge.querySelector("#replay-skip")!.addEventListener("click", () => { skip.now = true; });
  for (const el of document.querySelectorAll<HTMLInputElement | HTMLButtonElement>("#chat-input, #chat-form button")) el.disabled = true;
  try {
    const run = await loadReplay(name);
    badge.querySelector(".text")!.textContent = `Replay of a recorded run${run.model ? ` · ${run.model}` : ""}`;
    if (run.output.lab_spec) show(emptyDesign(run.output.lab_spec));
    await playReplay(run, {
      say: (lines, speaker) => dialogue.say(lines, speaker),
      log: (line) => { log.textContent += `\n${line}`; log.scrollTop = log.scrollHeight; },
      showDesign: (d) => { show(d); dialogue.say(introLines(d)); },
      showAnswer: (title, html) => showHtml(title, html),
    }, skip);
  } catch (e) {
    dialogue.say([String((e as Error).message ?? e)]);
  }
  badge.querySelector("#replay-skip")!.remove();
}
document.querySelector<HTMLFormElement>("#chat-form")!.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (chatting || replay) return; // the form is also disabled during a replay
  chatting = true;
  const input = document.querySelector<HTMLInputElement>("#chat-input")!;
  history.push({ role: "user", content: input.value });
  log.textContent += `\nYou: ${input.value}`;
  input.value = "";
  try {
    const out = await chat(history, design);
    history = out.history;
    log.textContent += `\nAgent: ${out.reply}`;
    show(out.design);
    hideStatCard();
    dialogue.say([out.reply]);
  } catch (error) {
    history.pop(); // the failed request was not committed to the conversation
    log.textContent += `\n${error instanceof Error ? error.message : "Chat failed"}`;
  } finally {
    chatting = false;
  }
});

document.querySelector("#report-btn")!.addEventListener("click", () => {
  const snapshot = () => new Promise<string | undefined>((resolve) =>
    game.renderer.snapshot((img) => resolve(img instanceof HTMLImageElement ? img.src : undefined)));
  openReport(design, snapshot);
});

// Vendor what-if from the stat card.
async function openWhatIf(id: string) {
  const eq = design.workflow.equipment.find((x) => x.instance_id === id), item = eq && design.catalog[eq.catalog_id];
  const name = item ? item.model : id, title = `How could ${name} be better?`;
  showLoading(title);
  try {
    const { result, cached } = await optimise(design, id);
    showWhatIf(result, name, design.lab_spec?.throughput_target?.value, cached);
    if (result.headroom_note) dialogue.say([result.headroom_note]);
  } catch {
    showError(title, "Needs the backend (make backend); no cached run for this design.");
  }
}
document.querySelector("#statcard")!.addEventListener("click", (e) => {
  const id = (e.target as HTMLElement).closest<HTMLElement>(".whatif")?.dataset.id;
  if (id) openWhatIf(id);
});

// Project planning: until the demo scenario lands, plans the fixture projects on the example lab.
async function openPlan() {
  showLoading("What order should these projects run in?");
  const { result, cached } = await prioritise(exampleProjects, design.layout.id);
  showSchedule(result, exampleProjects, cached);
}
document.querySelector("#plan-btn")!.addEventListener("click", openPlan);

async function openValidation() {
  showLoading("Does LabForge price real labs right?", "Comparing against published labs…");
  try { showValidation(await validation()); } catch { showError("Does LabForge price real labs right?", "Needs the backend (make backend)."); }
}
async function openBench() {
  showLoading("LabDesignBench", "Loading the leaderboard…");
  try { showLeaderboard(await leaderboard()); } catch { showError("LabDesignBench", "Needs the backend (make backend)."); }
}
document.querySelector("#validation-btn")!.addEventListener("click", openValidation);
document.querySelector("#bench-btn")!.addEventListener("click", openBench);

// Deep links for demos and screenshots: ?view=plan | validation | bench | whatif:<instance_id>
const view = params.get("view");
if (view === "plan") openPlan();
else if (view === "validation") openValidation();
else if (view === "bench") openBench();
else if (view?.startsWith("whatif:")) openWhatIf(view.slice(7));
