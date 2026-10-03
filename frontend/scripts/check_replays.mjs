// Plays each recorded run end to end, then again with Skip pressed at several moments, and checks it lands on the
// final state (the design, or the agent's answer) with no backend calls. Strand A (Roshan).
//
//   npm run frontend   (or: cd frontend && npx vite)       then:   npm run check:replays -- chem fbdd
// Env: BASE_URL (default http://localhost:5173), CHROME (path to Chrome; default: macOS install).
import { chromium } from "playwright-core";

const names = process.argv.slice(2).length ? process.argv.slice(2) : ["chem", "fbdd"];
const base = process.env.BASE_URL ?? "http://localhost:5173";
const browser = await chromium.launch({
  executablePath: process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
const errors = [];
let apiCalls = 0;
page.on("pageerror", (e) => errors.push(e.message));
page.on("request", (r) => { if (!r.url().startsWith(base)) apiCalls++; });

const finalState = () => page.evaluate(() => ({
  equipment: Math.max(0, document.querySelectorAll("#bom tr").length - 1),
  throughput: document.querySelector("#metrics .metric-big")?.textContent?.trim() ?? null,
  answer: document.querySelector("#modal:not(.hidden) h2")?.textContent ?? null,
  dialogue: document.querySelector("#dialogue .text")?.textContent?.slice(0, 80),
}));

let failed = false;
for (const name of names) {
  let reference;
  for (const skipAt of [null, 0.3, 3, 10]) {
    await page.goto(`${base}/?replay=${name}`);
    const t0 = Date.now();
    if (skipAt == null) {
      await page.waitForFunction(() => !document.querySelector("#replay-skip"), null, { timeout: 300000 });
    } else {
      await page.waitForTimeout(skipAt * 1000);
      if (await page.$("#replay-skip")) await page.click("#replay-skip");
      await page.waitForFunction(() => !document.querySelector("#replay-skip"), null, { timeout: 5000 });
    }
    await page.waitForTimeout(1000); // typewriter and scene restart
    const s = await finalState();
    reference ??= s;
    const ok = s.equipment > 0 || !!s.answer;
    const same = s.equipment === reference.equipment && s.throughput === reference.throughput && s.answer === reference.answer;
    if (!ok || !same) failed = true;
    console.log(`${ok && same ? "ok  " : "FAIL"} ${name} ${skipAt == null ? "full run" : `skip at ${skipAt}s`} (${((Date.now() - t0) / 1000).toFixed(1)}s):`,
      s.equipment ? `${s.equipment} items, ${s.throughput}` : s.answer ? `answer "${s.answer}"` : `no design: ${s.dialogue}`);
    if (skipAt == null) await page.screenshot({ path: `/tmp/replay_${name}_final.png` });
  }
}
if (apiCalls) { failed = true; console.log(`FAIL ${apiCalls} backend request(s) during replay`); }
if (errors.length) { failed = true; console.log("FAIL page errors:", errors); }
console.log(failed ? "Replay check FAILED" : "Replay check passed; final frames in /tmp/replay_<name>_final.png");
await browser.close();
process.exit(failed ? 1 : 0);
