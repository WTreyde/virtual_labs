import "@fontsource/press-start-2p";
import Phaser from "phaser";
import { chat, exampleDesign, liveCatalog } from "./api";
import { galleryDesign } from "./fixtures/gallery";
import { LabScene } from "./LabScene";
import { openReport } from "./report";
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
if (!params.get("demo")) liveCatalog(design).then((catalog) => { design = { ...design, catalog }; renderPanel(design); }).catch(() => {});
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
