import Phaser from "phaser";
import { chat, exampleDesign, report } from "./api";
import { LabScene } from "./LabScene";
import { renderPanel } from "./panel";
import type { Design } from "./types";

let design: Design = exampleDesign();
const history: { role: string; content: string }[] = [];

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game",
  backgroundColor: "#1d2b2f",
  scale: { mode: Phaser.Scale.RESIZE, width: window.innerWidth - 340, height: window.innerHeight },
  scene: [],
});
game.scene.add("lab", LabScene, true, { design });
renderPanel(design);

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
  } catch {
    log.textContent += "\n(backend not reachable: start it with `make backend`)";
  }
});

document.querySelector("#report-btn")!.addEventListener("click", async () => {
  const md = await report(design).catch(() => "Backend not reachable.");
  const w = window.open("", "_blank");
  w?.document.write(`<pre style="white-space:pre-wrap;font-family:system-ui">${md.replace(/</g, "&lt;")}</pre>`);
});
