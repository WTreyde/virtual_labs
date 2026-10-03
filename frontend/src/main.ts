import "@fontsource/press-start-2p";
import Phaser from "phaser";
import { chat, exampleDesign, report } from "./api";
import { galleryDesign } from "./fixtures/gallery";
import { LabScene } from "./LabScene";
import { renderPanel } from "./panel";
import type { Design } from "./types";
import { dialogue, hideStatCard, introLines, showStatCard } from "./ui";

// `?demo=gallery` shows every sprite kind; the default is the worked example from examples/.
let design: Design = new URLSearchParams(location.search).get("demo") === "gallery" ? galleryDesign : exampleDesign();
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

document.querySelector("#report-btn")!.addEventListener("click", async () => {
  const md = await report(design).catch(() => "Backend not reachable.");
  const w = window.open("", "_blank");
  w?.document.write(`<pre style="white-space:pre-wrap;font-family:system-ui">${md.replace(/</g, "&lt;")}</pre>`);
});
