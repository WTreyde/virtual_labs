# Inbox: Max (Strand B: catalog, safety, bench tasks, validation)

Last updated: 2026-10-04 07:00 BST by the integrator. Main at `9ffb0d4` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Sorry: from 01:30 to 05:30 this file was blank on main by an integrator error, so you may not have
seen these items. Nothing below is done yet. Freeze is 09:00, so work them in order and push small PRs.
1. Question from the integrator, please answer in your PR or to the user: your feedback "the whole
   project should last a couple of months rather than a couple of days" -- do you mean the simulated
   timeline and animation should cover a realistic campaign (weeks to months, with a day counter), or
   something else (e.g. the sim horizon, the schedule, the report's timeline)?
2. P0 Validation tab: the integrator made GET /validation cost only stored designs (never the agent).
   Add "--design-missing" to python -m labforge.validation.runner: for each case with no workflow (9 of
   28: clslab_liquid_dye_demo, dtu_chemspeed_robotic_platform_2025, earlier_flow_sdl,
   liverpool_mobile_robot_chemist_2020, low_cost_flow_sdl_2026, scripps_freeslate_jr_osr_s10_2018,
   sussex_crystallization_platform_alert_2022, ucla_htsc_unchained_junior_s10_2023,
   ucsc_mosquito_crystalpro_s10_2008), run the agent ONCE (Albert is making design_from_brief stream),
   and write backend/labforge/validation/designs/<case_id>.json as
   {"workflow": {...}, "provenance": {"model", "date", "commit", "cost_withheld": true}}
   or, when no design comes out, {"status": "no_design", "reason": "..."}. Never retry until something
   passes. The gateway already reads that folder and passes provenance through. Make run_case and
   main() use the same files so the CLI and the tab agree. Commit the generated files.
3. From Maxim's #44: bench task wording. xchem_vendor_harvest_rate scores 0.33 although the platform
   did what expected_behaviour asks (cites_evidence and calibration need a design: make them not
   checkable on a no-design answer, or read citations in the text). chem_cascade_tiny_room:
   no_violations fails the agent for showing the violations the task asks for. Fix the task files.
4. From Maxim's #61: the sim now models the Rock Imager's 970 storage slots. Check that the
   xchem_tamper_hotel task still traps (its premise is that hotel capacity is the bottleneck).
5. Optional: generic_safety_light_curtain catalog item (capability safeguarding, placeholder price,
   confidence placeholder) so the agent can add the guard Maxim's layout proposes.
Run make check, push strand/catalog, and open a PR into main.
```
