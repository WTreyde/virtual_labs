import "@fontsource/press-start-2p";
import Phaser from "phaser";
import { chat, exampleDesign, liveCatalog, optimise, prioritise } from "./api";
import { exampleProjects } from "./fixtures/projects";
import { galleryDesign } from "./fixtures/gallery";
import { LabScene } from "./LabScene";
import { openReport } from "./report";
import { showError, showLoading, showSchedule, showWhatIf } from "./views";
import { clock } from "./timeline";
import { renderPanel } from "./panel";
import type { Design } from "./types";
import { dialogue, hideStatCard, introLines, onTick, setupClock, showStatCard } from "./ui";

// `?demo=gallery` shows every sprite kind; the default is the worked example from examples/.
const params = new URLSearchParams(location.search);
clock.t = +(params.get("t") ?? 0) || 0; // ?t=<sim seconds> starts mid-run, handy for screenshots
let design: Design = params.get("demo") === "gallery" ? galleryDesign : exampleDesign();
const history: { role: string; content: string }[] = [];

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game",
  backgroundColor: "#1d2b2f",
  pixelArt: true,
  scale: { mode: Phaser.Scale.RESIZE, width: window.innerWidth - 340, height: window.innerHeight },
  scene: [],
});
// Wait for the pixel font so Phaser text doesn't bake in the fallback face.
document.fonts.load('8px "Press Start 2P"').finally(() => game.scene.add("lab", LabScene, true, { design }));
renderPanel(design);
dialogue.say(introLines(design));
// With the backend up, use its catalog so BOM prices match /report; offline, keep examples/catalog.json.
if (!params.get("demo")) liveCatalog(design).then((catalog) => { design = { ...design, catalog }; renderPanel(design); if (!params.get("view")) dialogue.say(introLines(design)); }).catch(() => {});
game.events.on("tick", onTick);
game.events.on("ready-clock", () => setupClock(design));
game.events.on("select", (sel: { id: string; sprite?: string } | null) => (sel ? showStatCard(design, sel.id, sel.sprite) : hideStatCard()));

function show(d: Design) {
  design = d;
  game.scene.getScene("lab").scene.restart({ design });
  renderPanel(d);
}

const log = document.querySelector<HTMLDivElement>("#log")!;
document.querySelector<HTMLFormElement>("#chat-form")!.addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.querySelector<HTMLInputElement>("#chat-input")!;
  history.push({ role: "user", content: input.value });
  log.textContent += `\nYou: ${input.value}`;
  input.value = "";
  try {
    const out = await chat(history, design);
    history.push({ role: "assistant", content: out.reply });
    log.textContent += `\nAgent: ${out.reply}`;
    show(out.design);
    hideStatCard();
    dialogue.say([out.reply]);
  } catch {
    log.textContent += "\n(backend not reachable: start it with `make backend`)";
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

// Deep links for demos and screenshots: ?view=plan or ?view=whatif:<instance_id>
const view = params.get("view");
if (view === "plan") openPlan();
else if (view?.startsWith("whatif:")) openWhatIf(view.slice(7));
