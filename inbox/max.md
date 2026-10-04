# Inbox: Max (Strand B: catalog, safety, bench tasks, validation)

Last updated: 2026-10-04 08:31 BST by the integrator. Main at `d326d34` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #97 is merged (bench task fixes, tamper-hotel trap holds for both capacities, timeline answer).
Thanks, and sorry again about the blank file.
2. TOP PRIORITY, approved by the user at 08:30: run the 9 validation designs now. Add
   --design-missing to python -m labforge.validation.runner; for each of the 9 cases with no workflow
   (clslab_liquid_dye_demo, dtu_chemspeed_robotic_platform_2025, earlier_flow_sdl,
   liverpool_mobile_robot_chemist_2020, low_cost_flow_sdl_2026, scripps_freeslate_jr_osr_s10_2018,
   sussex_crystallization_platform_alert_2022, ucla_htsc_unchained_junior_s10_2023,
   ucsc_mosquito_crystalpro_s10_2008) run the agent ONCE, no retries, and write
   backend/labforge/validation/designs/<case_id>.json as {"workflow": {...}, "provenance": {"model",
   "date", "commit", "cost_withheld": true}} or {"status": "no_design", "reason": "..."} on refusal or
   failure. The gateway already reads that folder. Commit the files and open a PR before 09:00; push
   partial results rather than miss the freeze.
5. Light curtain: dropped for the hack (it needs a schema change and the freeze is 09:00).
   Your timeline answer (a weeks-to-months campaign view with a day counter) goes on the roadmap,
   not into this build.
Feature freeze at 09:00: after that only fixes the user approves get merged.
```
