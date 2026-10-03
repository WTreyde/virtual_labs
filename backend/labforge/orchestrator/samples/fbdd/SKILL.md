---
name: run-xchem-fbdd-demo
description: Orchestrate the XChem-style fragment screening demo lab through its instrument APIs. Use when running, scheduling or troubleshooting this lab's workflow; covers the devices and their limits, run order, safety rules and when to call a person.
---

# Running XChem-style fragment screening demo

You orchestrate this lab. Goal: about 300 crystals_per_day (24 h/day), safely. You have the tools in `tools.json`; each device's limits, zone and confidence are listed there. This file was generated from the lab's digital twin (workflow `xchem_wf_v1`, layout `xchem_wf_v1_layout`, simulation `xchem_wf_v1_layout_sim`). Where the twin was unsure, this file says so; trust a measurement over the twin and log it with `record_measurement`.

## Before the first run

The layout check found problems that are not fixed. **Do not start until a person has fixed each one or signed it off** (`request_human`, urgency soon, listing them):

- egress_blocked: No 1.0 m walkway from the door to where someone works at centrifuge_highg_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at cryo_bench_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at echo_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at growth_hotel_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at imager_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at ln2_dewar_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at mosquito_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at nanodrop_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at review_bench_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at shifter_1.
- safety: People hand labware into arm_1's reach at echo_1, shaker_1, and arm_1 has no collaborative rating in the catalog; add a light curtain or a pass-through hotel at the cell edge.

These values are placeholders in the catalog. Measure each on the first run and log it with `record_measurement`:

- `sonicator_1` process.durations_s.cell_lysis = 300 (range 60-900)
- `growth_hotel_1` process.durations_s.incubation = 3600 (range 600-172800)
- `cold_room_1` storage_slots = 300 (range 100-800)
- `shifter_1` process.durations_s.crystal_harvesting = 7200 (range 1800-14400)
- `dry_shipper_1-7, shifter_1` process.capacity = 1 (range 1-1)
- `ln2_dewar_1` process.durations_s.cryo_cooling = 120 (range 30-600)
- `cryo_bench_1, review_bench_1` process.durations_s.manual_bench = 900 (range 300-3600)
- `dry_shipper_1-7` storage_slots = 3 (range 1-7)

## Devices

| Device | Model | Does | Capacity | Control | Data |
|---|---|---|---|---|---|
| `shaker_1` | Multitron Pro | cell_culture | 12 (estimated) | vendor software only | estimated |
| `centrifuge_highg_1` | Avanti JXN-26 | centrifugation | 1 (datasheet) | vendor software only | estimated |
| `sonicator_1` | Q700 Sonicator | cell_lysis | 1 (datasheet) | vendor software only | estimated |
| `akta_1` | ÄKTA pure 25 | protein_purification | 1 (estimated) | open standard | estimated |
| `gel_1` | Mini-PROTEAN Tetra Cell with PowerPac Basic | protein_qc | 4 (datasheet) | vendor software only | estimated |
| `centrifuge_bench_1` | Centrifuge 5810 R | centrifugation | 16 (datasheet) | vendor api | estimated |
| `nanodrop_1` | NanoDrop Ultra (successor to NanoDrop One) | concentration_measurement | 1 (datasheet) | vendor software only | datasheet |
| `mosquito_1` | mosquito Xtal3 | crystallization_setup | 3 (datasheet) | unconfirmed | estimated |
| `growth_hotel_1` | Cytomat 2 C-LiN Automated Incubator | incubation | 42 (datasheet) | unconfirmed | estimated |
| `imager_1` | Rock Imager 1000 | crystal_imaging | 1000 (estimated) | vendor software only | datasheet |
| `cold_room_1` | Kold Locker walk-in cooler (8 ft x 8 ft) | transport/support | 300 (estimated) | none listed | estimated |
| `echo_1` | Echo 525 | crystal_soaking | 1 (estimated) | vendor software only | estimated |
| `shifter_1` | Crystal Shifter | crystal_harvesting | 1 (placeholder) | vendor software only | placeholder |
| `ln2_dewar_1` | ICB35-10 (formerly TW35-10) LN2 freezer | cryo_cooling | 10 (estimated) | none listed | estimated |
| `cryo_bench_1, review_bench_1` | Adjustable-height basic work bench (06-000-654) | manual_bench | 2 (placeholder) | none listed | placeholder |
| `arm_1` | UR5e | transport/support | 1 (estimated) | vendor software only | estimated |
| `dry_shipper_1-7` | CX100 Cryo Express Dry Shipper | transport/support | 3 (placeholder) | vendor software only | estimated |

## Workflow and handoffs

Steps in run order. Times are the twin's expected value and range per unit of labware.

1. **E. coli shake-flask expression** (`expression`, automated) on `shaker_1` (start). Expect 20.0 h (12.0 h-36.0 h, estimated); pause and escalate past 2.2 d.
   - handoff `shaker_1` to `centrifuge_highg_1` by `xchem_scientist_1` (3.78 m, ~19 s)
2. **Cell harvest centrifugation** (`cell_harvest`, semi automated, operator: xchem_scientist) on `centrifuge_highg_1` after expression. Expect 30 min (20 min-60 min, estimated); pause and escalate past 90 min.
   - handoff `centrifuge_highg_1` to `sonicator_1` by `xchem_scientist_1` (2.84 m, ~18 s)
3. **Cell lysis (probe sonication)** (`lysis`, manual, operator: xchem_scientist) on `sonicator_1` after cell_harvest. Expect 30 min (15 min-60 min, estimated); pause and escalate past 90 min.
   - handoff `sonicator_1` to `centrifuge_highg_1` by `xchem_scientist_1` (2.88 m, ~18 s)
4. **Lysate clarification** (`clarification`, semi automated, operator: xchem_scientist) on `centrifuge_highg_1` after lysis. Expect 30 min (20 min-60 min, estimated); pause and escalate past 90 min.
   - handoff `centrifuge_highg_1` to `akta_1` by `xchem_scientist_1` (4.6 m, ~20 s)
5. **Affinity purification** (`purify_affinity`, semi automated, operator: xchem_scientist) on `akta_1` after clarification. Expect 60 min (40 min-2.0 h, estimated); pause and escalate past 3.0 h.
6. **Size-exclusion polishing** (`purify_sec`, semi automated, operator: xchem_scientist) on `akta_1` after purify_affinity. Expect 90 min (60 min-3.0 h, estimated); pause and escalate past 4.5 h.
   - handoff `akta_1` to `gel_1` by `xchem_scientist_1` (1.1 m, ~16 s)
7. **SDS-PAGE purity QC** (`qc_gel`, semi automated, operator: xchem_scientist) on `gel_1` after purify_sec. Expect 40 min (35 min-45 min, datasheet); pause and escalate past 68 min.
   - handoff `gel_1` to `centrifuge_bench_1` by `xchem_scientist_1` (5.6 m, ~21 s)
8. **Spin concentration** (`concentrate`, semi automated, operator: xchem_scientist) on `centrifuge_bench_1` after qc_gel. Expect 30 min (15 min-60 min, estimated); pause and escalate past 90 min.
   - handoff `centrifuge_bench_1` to `nanodrop_1` by `xchem_scientist_1` (2.54 m, ~18 s)
9. **Concentration measurement** (`conc_measure`, manual, operator: xchem_scientist) on `nanodrop_1` after concentrate. Expect 5 min (2 min-10 min, estimated); pause and escalate past 15 min.
   - handoff `nanodrop_1` to `mosquito_1` by `xchem_scientist_1` (4.09 m, ~19 s)
10. **Crystallisation drop setup** (`drop_setup`, automated) on `mosquito_1` after conc_measure. Expect 20 min (10 min-50 min, estimated); pause and escalate past 75 min.
   - handoff `mosquito_1` to `imager_1` by `xchem_scientist_1` (2.87 m, ~18 s)
11. **Inspection 1 (day 0)** (`image_t0`, automated) on `imager_1` after drop_setup. Expect 3 min (3 min-3 min, datasheet); pause and escalate past 4 min.
   - handoff `imager_1` to `growth_hotel_1` by `xchem_scientist_1` (1.35 m, ~16 s)
12. **Crystal growth residence day 0-1** (`growth_1`, automated) on `growth_hotel_1` after image_t0. Expect 24.0 h (12.0 h-2.0 d, estimated); pause and escalate past 3.0 d.
   - handoff `growth_hotel_1` to `imager_1` by `xchem_scientist_1` (1.35 m, ~16 s)
13. **Inspection 2 (day 1)** (`image_d1`, automated) on `imager_1` after growth_1. Expect 3 min (3 min-3 min, datasheet); pause and escalate past 4 min.
   - handoff `imager_1` to `growth_hotel_1` by `xchem_scientist_1` (1.35 m, ~16 s)
14. **Crystal growth residence day 1-3** (`growth_2`, automated) on `growth_hotel_1` after image_d1. Expect 2.0 d (24.0 h-5.0 d, estimated); pause and escalate past 7.5 d.
   - handoff `growth_hotel_1` to `imager_1` by `xchem_scientist_1` (1.35 m, ~16 s)
15. **Inspection 3 (day 3)** (`image_d3`, automated) on `imager_1` after growth_2. Expect 3 min (3 min-3 min, datasheet); pause and escalate past 4 min.
   - handoff `imager_1` to `review_bench_1` by `xchem_scientist_1` (2.78 m, ~18 s)
16. **Operator drop selection from images** (`drop_selection`, manual, operator: xchem_scientist) on `review_bench_1` after image_d3. Expect 10 min (5 min-20 min, estimated); pause and escalate past 30 min.
   - handoff `review_bench_1` to `echo_1` by `xchem_scientist_1` (3.27 m, ~18 s)
17. **Acoustic fragment soaking** (`soak_dispense`, automated) on `echo_1` after drop_selection. Expect 15 min (5 min-40 min, estimated); pause and escalate past 60 min.
   - handoff `echo_1` to `growth_hotel_1` by `xchem_scientist_1` (3.02 m, ~18 s)
18. **Soak residence** (`soak_residence`, automated) on `growth_hotel_1` after soak_dispense. Expect 3.0 h (60 min-24.0 h, estimated); pause and escalate past 36.0 h.
   - handoff `growth_hotel_1` to `shifter_1` by `xchem_scientist_1` (3.76 m, ~19 s)
19. **Shifter-assisted manual crystal harvesting** (`harvest`, manual, operator: xchem_scientist) on `shifter_1` after soak_residence. Expect 19 min (16 min-32 min, literature); pause and escalate past 48 min.
   - handoff `shifter_1` to `ln2_dewar_1` by `xchem_scientist_1` (3.44 m, ~18 s)
20. **Cryo-cooling / puck handling in LN2 dewar** (`cryo_puck`, manual, operator: xchem_scientist) on `ln2_dewar_1` after harvest. Expect 2 min (30 s-10 min, placeholder); pause and escalate past 15 min.
   - handoff `ln2_dewar_1` to `cryo_bench_1` by `xchem_scientist_1` (2.25 m, ~17 s)
21. **Load filled puck into charged dry shipper** (`load_shipper`, manual, operator: xchem_scientist) on `cryo_bench_1` after cryo_puck. Expect 5 min (60 s-15 min, estimated); pause and escalate past 22 min.
22. **Ship dry shipper to synchrotron (transit + beamline queue)** (`ship_out`, external) on people outside the lab after load_shipper. Expect 60 min (30 min-2.0 h, estimated); pause and escalate past 3.0 h.
23. **External synchrotron diffraction** (`diffraction`, external) on people outside the lab after ship_out. Expect 40 min (16 min-2.0 h, estimated); pause and escalate past 3.0 h.
24. **In-silico hit analysis** (`hit_analysis`, in silico) on compute after diffraction. Expect 60 min (20 min-4.0 h, estimated); pause and escalate past 6.0 h.

## Run order and dispatch

The twin's bottleneck is `growth_hotel_1` (busy 80%; steps growth_1, growth_2, soak_residence; parallel units growth_hotel_1).
Pull-based release paced by the bottleneck (drum-buffer-rope): keep 1-2 units queued in front of growth_hotel_1 (growth_1, growth_2, soak_residence) so it never idles, and release a new unit at the first step only when that buffer drops below 2. Among ready steps, serve the one feeding the bottleneck first, then oldest labware first.
_Heuristic from the twin's utilisation; not an optimised schedule. Confirm in the simulator before relying on it._

Work-in-progress limits (never exceed): `growth_hotel_1` 42, `imager_1` 1000, `cold_room_1` 300, `ln2_dewar_1` 10, `dry_shipper_1-7` 3 each.

## Safety rules (hard limits)

- Only call tools in the manifest, with step ids and routes from their enums. Never improvise a device action, parameter or route that is not listed.
- Never load a device beyond its capacity or storage slots, and never load labware types it does not accept.
- Never start a step before every step in its `after` list has finished for that labware unit.
- Keep walkways of at least 1.0 m and egress of at least 1.2 m clear; mobile robots must not park in them.
- flammable solvents: akta_1 must only run inside a fume_hood or ventilated zone with its extraction or monitoring confirmed on.
- toxic reagents: gel_1 must only run inside a fume_hood zone with its extraction or monitoring confirmed on.
- cryogens: dry_shipper_1-7, ln2_dewar_1, shifter_1 must only run inside a cryogen zone with its extraction or monitoring confirmed on.
- High-g centrifuge: only start a run when the rotor is balanced and the lid interlock reports closed.
- Cryogens: no one handles liquid nitrogen alone; confirm the O2 monitor reads normal before any cryo step.

## When to call a person

- Manual or semi-automated steps (cell_harvest, lysis, clarification, purify_affinity, purify_sec, qc_gel, concentrate, conc_measure, drop_selection, harvest, cryo_puck, load_shipper): call `request_human` with the step's operator role before the labware arrives. xchem_scientist works 8 h shifts. Out of shift, hold the labware in storage rather than skipping the step.
- External steps (ship_out, diffraction) leave the lab: a human books, packs and ships them. Never mark them done yourself.
- A step still running at 1.5x its high bound (`pause_after_s` in the run order) is outside what the twin expects: check the device status, `pause_line` from that step, and `request_human` (urgency soon).
- Any device error, safety interlock, labware mismatch or barcode you cannot read: stop that device, `request_human` (urgency now). Do not retry a failed physical action more than once.
- dry_shipper_1-7 hold contents for about 12.6 d each: track when each was charged, alert a human at 75% of that, and ship or unload before it expires.
- No confirmed programmable interface for centrifuge_highg_1, echo_1, gel_1, growth_hotel_1, imager_1, mosquito_1, shaker_1: until a driver is verified, treat their tools as 'ask a human to do this and confirm', not as direct control.
- Design claim refuted by the verifier: "Simulated P50 throughput meets the 300 crystals/day target." (verified throughput.p50 = 112.0). Never report the claimed value as expected performance; use the verified one.
- Design claim refuted by the verifier: "The layout has zero violations." (verified layout.violations = 11.0). Never report the claimed value as expected performance; use the verified one.

## What the twin expects

Throughput P10/P50/P90: 219.2 / 312.0 / 372.8 crystals_per_day (target 300, chance of meeting it 0.6).

**The verifier did not reproduce this.** Its independent recompute gives throughput.p50 = 112.0. Plan on the verified number until real runs say otherwise.

Inputs that move throughput most (measure these first): growth_2.duration_s (-176), soak_residence.duration_s (-34.7), growth_1.duration_s (-32), cryo_puck.duration_s (+8), load_shipper.duration_s (+8).

If real throughput or utilisation drifts outside these bands for a full day, tell the lab manager and log the measurements so the twin can be re-run. Do not hide a shortfall by skipping QC or overloading devices.
