---
name: run-chem-library-768
description: Orchestrate the Two-stage chemistry library benchmark (abstract equipment demand) lab through its instrument APIs. Use when running, scheduling or troubleshooting this lab's workflow; covers the devices and their limits, run order, safety rules and when to call a person.
---

# Running Two-stage chemistry library benchmark (abstract equipment demand)

You orchestrate this lab. Goal: about 768 compounds_per_day (24 h/day), safely. You have the tools in `tools.json`; each device's limits, zone and confidence are listed there. This file was generated from the lab's digital twin (workflow `chem_library_768_wf_v1`, layout `chem_library_768_wf_v1_layout`, simulation `chem_library_768_wf_v1_layout_sim`). Where the twin was unsure, this file says so; trust a measurement over the twin and log it with `record_measurement`.

## Before the first run

The layout check passed with no violations.

These values are placeholders in the catalog. Measure each on the first run and log it with `record_measurement`:

- `swing_1-2` process.durations_s.reaction = 14400 (range 3600-86400)
- `evap_1` process.durations_s.evaporation = 5400 (range 1800-14400)
- `evap_1` process.capacity = 6 (range 3-12)
- `store_1` process.durations_s.compound_storage = 120 (range 30-600)
- `cytomat_1` process.durations_s.incubation = 3600 (range 600-172800)
- `kmr_1` transport.pick_place_s = 15 (range 8-60)

## Devices

| Device | Model | Does | Capacity | Control | Data |
|---|---|---|---|---|---|
| `quantos_1` | Quantos QB5 | powder_dosing | 1 (datasheet) | vendor software only | estimated |
| `fume_hood_1` | Protector XStream 6 ft | transport/support | 1 (datasheet) | none listed | datasheet |
| `star_1` | Microlab STAR | liquid_handling | 1 (estimated) | vendor software only | estimated |
| `swing_1-2` | SWING XL | liquid_dosing, reaction | 1 (estimated) | vendor software only | estimated |
| `pressure_1` | PRESSURE+ 96 | filtration | 1 (estimated) | vendor software only | estimated |
| `pressure_2` | PRESSURE+ 96 | solid_phase_extraction | 1 (estimated) | vendor software only | estimated |
| `evap_1` | Genevac HT-6 (Series 3i) | evaporation | 6 (placeholder) | vendor api | estimated |
| `lcms_1-2` | 1290 Infinity II LC with InfinityLab LC/MSD iQ | lcms | 1 (estimated) | vendor software only | estimated |
| `store_1` | SampleStore (ambient to -20 C) | compound_storage | 1094 (estimated) | vendor software only | estimated |
| `echo_1` | Echo 650 Plus | acoustic_dispensing | 1 (datasheet) | vendor api | estimated |
| `combi_1` | Multidrop Combi | reagent_dispensing | 1 (datasheet) | vendor software only | datasheet |
| `cytomat_1` | Cytomat 2 C-LiN Automated Incubator | incubation | 42 (datasheet) | unconfirmed | estimated |
| `pherastar_1` | PHERAstar FSX | fluorescence_read | 1 (estimated) | vendor api | estimated |
| `kmr_1` | KMR iiwa | transport/support | 1 (estimated) | vendor api | estimated |

## Workflow and handoffs

Steps in run order. Times are the twin's expected value and range per unit of labware.

1. **Stock preparation: powder dosing of building-block stock vials** (`stock_powder_dosing`, semi automated, operator: chemist_operator) on `quantos_1` (start). Expect 2.3 h (56 min-7.0 h, estimated); pause and escalate past 10.5 h.
   - handoff `quantos_1` to `star_1` by `kmr_1` (6.79 m, ~38 s)
2. **Stock dissolution (liquid handling)** (`stock_dissolution`, automated) on `star_1` after stock_powder_dosing. Expect 5 min (2 min-15 min, estimated); pause and escalate past 22 min.
   - handoff `star_1` to `swing_1` by `kmr_1` (7.95 m, ~40 s)
   - handoff `star_1` to `swing_2` by `kmr_1` (8.99 m, ~41 s)
3. **Stage 1: dose stocks into reaction block** (`s1_dosing`, automated) on `swing_1` or `swing_2` after stock_dissolution. Expect 24 min (10 min-50 min, estimated); pause and escalate past 75 min.
   - handoff `swing_1` to `swing_2` by `kmr_1` (5.51 m, ~37 s)
   - handoff `swing_2` to `swing_1` by `kmr_1` (5.51 m, ~37 s)
4. **Stage 1 reaction (inert, heated/stirred)** (`s1_reaction`, automated) on `swing_1` or `swing_2` after s1_dosing. Expect 4.0 h (60 min-24.0 h, placeholder); pause and escalate past 36.0 h.
   - handoff `swing_1` to `pressure_1` by `kmr_1` (6.82 m, ~38 s)
   - handoff `swing_2` to `pressure_1` by `kmr_1` (7.51 m, ~39 s)
5. **Stage 1 workup/filtration** (`s1_workup_filtration`, manual, operator: chemist_operator) on `pressure_1` after s1_reaction. Expect 7 min (2 min-25 min, estimated); pause and escalate past 38 min.
   - handoff `pressure_1` to `star_1` by `kmr_1` (3.09 m, ~34 s)
6. **Stage 2 expansion: distribute each stage-1 product into 8 variant blocks** (`s2_expansion`, automated) on `star_1` after s1_workup_filtration. Expect 40 min (16 min-2.0 h, estimated); pause and escalate past 3.0 h.
   - handoff `star_1` to `swing_1` by `kmr_1` (7.95 m, ~40 s)
   - handoff `star_1` to `swing_2` by `kmr_1` (8.99 m, ~41 s)
7. **Stage 2: dose variant stocks into each block** (`s2_dosing`, automated) on `swing_1` or `swing_2` after s2_expansion. Expect 24 min (10 min-50 min, estimated); pause and escalate past 75 min.
   - handoff `swing_1` to `swing_2` by `kmr_1` (5.51 m, ~37 s)
   - handoff `swing_2` to `swing_1` by `kmr_1` (5.51 m, ~37 s)
8. **Stage 2 reaction (inert, heated/stirred)** (`s2_reaction`, automated) on `swing_1` or `swing_2` after s2_dosing. Expect 4.0 h (60 min-24.0 h, placeholder); pause and escalate past 36.0 h.
   - handoff `swing_1` to `pressure_2` by `kmr_1` (6.2 m, ~38 s)
   - handoff `swing_2` to `pressure_2` by `kmr_1` (6.89 m, ~38 s)
9. **Purification (solid-phase extraction)** (`purification_spe`, manual, operator: chemist_operator) on `pressure_2` after s2_reaction. Expect 12 min (6 min-40 min, estimated); pause and escalate past 60 min.
   - handoff `pressure_2` to `evap_1` by `kmr_1` (9.73 m, ~42 s)
10. **Solvent evaporation** (`evaporation`, automated) on `evap_1` after purification_spe. Expect 90 min (30 min-4.0 h, placeholder); pause and escalate past 6.0 h.
   - handoff `evap_1` to `star_1` by `kmr_1` (11.9 m, ~44 s)
11. **Reconstitution into 96-well QC/master plate** (`reconstitution`, automated) on `star_1` after evaporation. Expect 5 min (2 min-15 min, estimated); pause and escalate past 22 min.
   - handoff `star_1` to `lcms_1` by `kmr_1` (3.33 m, ~34 s)
   - handoff `star_1` to `lcms_2` by `kmr_1` (2.16 m, ~33 s)
12. **LC-MS QC of every product** (`lcms_qc`, automated) on `lcms_1` or `lcms_2` after reconstitution. Expect 4.0 h (2.7 h-8.0 h, estimated); pause and escalate past 12.0 h.
   - handoff `lcms_1` to `star_1` by `kmr_1` (3.3 m, ~34 s)
   - handoff `lcms_2` to `star_1` by `kmr_1` (2.14 m, ~33 s)
13. **Reformat to 384-well acoustic source plate** (`reformat_384`, automated) on `star_1` after lcms_qc. Expect 5 min (2 min-15 min, estimated); pause and escalate past 22 min.
   - handoff `star_1` to `store_1` by `kmr_1` (7.84 m, ~40 s)
14. **Compound storage deposit/retrieve** (`compound_storage`, automated) on `store_1` after reformat_384. Expect 2 min (30 s-10 min, placeholder); pause and escalate past 15 min.
   - handoff `store_1` to `echo_1` by `kmr_1` (1.62 m, ~32 s)
15. **Assay prep: acoustic compound transfer** (`assay_compound_transfer`, automated) on `echo_1` after compound_storage. Expect 3 min (60 s-10 min, estimated); pause and escalate past 15 min.
   - handoff `echo_1` to `combi_1` by `kmr_1` (2.3 m, ~33 s)
16. **Assay prep: dispense supplied purified protein target/reagents** (`assay_protein_dispense`, automated) on `combi_1` after assay_compound_transfer. Expect 70 s (35 s-5 min, estimated); pause and escalate past 8 min.
   - handoff `combi_1` to `cytomat_1` by `kmr_1` (1.63 m, ~32 s)
17. **Assay incubation** (`assay_incubation`, automated) on `cytomat_1` after assay_protein_dispense. Expect 60 min (30 min-2.0 h, placeholder); pause and escalate past 3.0 h.
   - handoff `cytomat_1` to `pherastar_1` by `kmr_1` (1.71 m, ~32 s)
18. **Fluorescence screening readout** (`fluorescence_read`, automated) on `pherastar_1` after assay_incubation. Expect 30 s (14 s-90 s, estimated); pause and escalate past 2 min.
19. **Hit analysis (in silico) - counting sink** (`hit_analysis`, in silico) on compute after fluorescence_read. Expect 10 min (2 min-30 min, placeholder); pause and escalate past 45 min.

## Run order and dispatch

The twin's bottleneck is `swing_1` (busy 100%; steps s1_dosing, s1_reaction, s2_dosing, s2_reaction; parallel units swing_1, swing_2).
Pull-based release paced by the bottleneck (drum-buffer-rope): keep 1-2 units queued in front of swing_1 (s1_dosing, s1_reaction, s2_dosing, s2_reaction) so it never idles, and release a new unit at the first step only when that buffer drops below 2. Among ready steps, serve the one feeding the bottleneck first, then oldest labware first.
_Heuristic from the twin's utilisation; not an optimised schedule. Confirm in the simulator before relying on it._

Work-in-progress limits (never exceed): `store_1` 1094, `cytomat_1` 42.

## Safety rules (hard limits)

- Only call tools in the manifest, with step ids and routes from their enums. Never improvise a device action, parameter or route that is not listed.
- Never load a device beyond its capacity or storage slots, and never load labware types it does not accept.
- Never start a step before every step in its `after` list has finished for that labware unit.
- Keep walkways of at least 1.0 m and egress of at least 1.2 m clear; mobile robots must not park in them.
- flammable solvents: evap_1, fume_hood_1, lcms_1-2, pressure_1-2, quantos_1, swing_1-2 must only run inside a fume_hood or ventilated zone with its extraction or monitoring confirmed on.
- toxic reagents: combi_1, fume_hood_1, lcms_1-2, swing_1-2 must only run inside a fume_hood zone with its extraction or monitoring confirmed on.
- biohazard: star_1 must only run inside a bsl2 zone with its extraction or monitoring confirmed on.

## When to call a person

- Manual or semi-automated steps (stock_powder_dosing, s1_workup_filtration, purification_spe): call `request_human` with the step's operator role before the labware arrives. chemist_operator works 8 h shifts. Out of shift, hold the labware in storage rather than skipping the step.
- A step still running at 1.5x its high bound (`pause_after_s` in the run order) is outside what the twin expects: check the device status, `pause_line` from that step, and `request_human` (urgency soon).
- Any device error, safety interlock, labware mismatch or barcode you cannot read: stop that device, `request_human` (urgency now). Do not retry a failed physical action more than once.
- No confirmed programmable interface for combi_1, cytomat_1, lcms_1-2, quantos_1, star_1, store_1, swing_1-2: until a driver is verified, treat their tools as 'ask a human to do this and confirm', not as direct control.
- The twin gives only a 0% chance of meeting the 768 compounds_per_day target. Tell the lab manager on day one instead of pushing devices past their limits to catch up.
- Design claim refuted by the verifier: "Simulated P50 throughput meets the 768 compounds/day target" (verified throughput.p50 = 320.0). Never report the claimed value as expected performance; use the verified one.
- Design claim refuted by the verifier: "Total BOM is within the USD 2,000,000 equipment budget" (verified bom.total_usd = 5890359.0). Never report the claimed value as expected performance; use the verified one.

## What the twin expects

Throughput P10/P50/P90: 212.8 / 312.0 / 372.8 compounds_per_day (target 768, chance of meeting it 0.0).

**The verifier did not reproduce this.** Its independent recompute gives throughput.p50 = 320.0. Plan on the verified number until real runs say otherwise.

Inputs that move throughput most (measure these first): s2_reaction.duration_s (-646), s1_reaction.duration_s (-238), s1_dosing.duration_s (-32), stock_powder_dosing.duration_s (-16), s2_dosing.duration_s (+12).

If real throughput or utilisation drifts outside these bands for a full day, tell the lab manager and log the measurements so the twin can be re-run. Do not hide a shortfall by skipping QC or overloading devices.
