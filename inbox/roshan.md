# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-03 17:20 BST by the integrator. Main at `087d2af`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Pull main. Build the unified app inside the existing client (no new framework):
1. Hash routes and a top nav: #/ (landing), #/case/chem, #/case/fbdd, #/design (live chat),
   #/bench, #/validation, #/schedule. Keep ?replay= and ?view= working as aliases. Keep
   ?demo=gallery as a hidden dev route, not in the nav.
2. Landing: a one-line pitch, two case cards and a "Design your own lab" card. Case titles
   (the user asked for specific names):
     "768-compound library: two-step synthesis, LC-MS QC and protein screening"
     "XChem fragment screening: from E. coli expression to synchrotron shipping"
   Each subtitle shows the headline throughput and the bottleneck, read from the replay data
   (or from Albert's summary file once it lands), never hard-coded numbers.
3. Case pages reuse replay mode. From the final design, the BOM, Boss report and what-if
   must be one click away.
4. Use the API base from VITE_API (empty = same origin) everywhere, so it works under
   make demo at http://localhost:8000 as well as under make frontend.
5. Cosmetic: on #/validation, the labels of the OT-2 / DNA-BOT cluster overlap.
Run make check and npm run check:replays, then push and open a PR into main.

After the items above (nice to have, depends on PR #31, the orchestrator export, merging):
6. A "Download agent skill" button next to "Report for your boss" that saves SKILL.md and tools.json for
   the current design. Offline/replay: serve backend/labforge/orchestrator/samples/<case>/ files statically.
```
