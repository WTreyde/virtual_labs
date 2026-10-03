// Plays each recorded run end to end, then again with Skip pressed at several moments, and checks it lands on the
// final state (the design, or the agent's answer) with no backend calls. Strand A (Roshan).
//
//   make frontend (or make demo)       then:   npm run check:replays -- chem fbdd
// Env: BASE_URL (default http://localhost:5173; http://localhost:8000 under make demo), CHROME (default: macOS install).
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
page.on("pageerror", (e) => errors.push(`page error: ${e.message}`));
page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
// net::ERR_ABORTED is the browser cancelling in-flight requests when the checker navigates to the next run.
page.on("requestfailed", (r) => { if (r.failure()?.errorText !== "net::ERR_ABORTED") errors.push(`request failed (${r.failure()?.errorText}): ${r.url()}`); });
page.on("response", (r) => { if (r.status() >= 400 && !r.url().endsWith("/favicon.ico")) errors.push(`HTTP ${r.status()}: ${r.url()}`); });
// Backend routes, whether the API is another origin (make frontend) or the same one (make demo).
const API_PATH = /^\/(chat|catalog|layout|simulate|verify|report|optimise|prioritise|validation|bench|example|health)\b/;
page.on("request", (r) => { const u = new URL(r.url()); if (!r.url().startsWith(base) || API_PATH.test(u.pathname)) { apiCalls++; console.log("  backend request:", r.method(), r.url()); } });

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
    await page.goto("about:blank"); // a same-URL hash navigation would not reload the page
    await page.goto(`${base}/#/case/${name}`);
    const t0 = Date.now();
    await page.waitForSelector("#replay-skip", { timeout: 15000 }); // appears when the replay starts
    if (skipAt == null) {
      await page.waitForFunction(() => !document.querySelector("#replay-skip"), null, { timeout: 300000 });
    } else {
      await page.waitForTimeout(skipAt * 1000);
      await page.click("#replay-skip");
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
if (errors.length) { failed = true; console.log("FAIL errors during replay:\n  " + [...new Set(errors)].join("\n  ")); }
console.log(failed ? "Replay check FAILED" : "Replay check passed; final frames in /tmp/replay_<name>_final.png");
await browser.close();
process.exit(failed ? 1 : 0);
