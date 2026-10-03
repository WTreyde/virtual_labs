---
name: run-xchem-demo
description: Orchestrate the XChem-style fragment screening demo lab through its instrument APIs. Use when running, scheduling or troubleshooting this lab's workflow; covers the devices and their limits, run order, safety rules and when to call a person.
---

# Running XChem-style fragment screening demo

You orchestrate this lab. Goal: about 300 crystals_per_day (24 h/day), safely. You have the tools in `tools.json`; each device's limits, zone and confidence are listed there. This file was generated from the lab's digital twin (workflow `xchem_demo_wf_v1`, layout `xchem_demo_wf_v1_layout`, simulation `xchem_demo_wf_v1_layout_sim`). Where the twin was unsure, this file says so; trust a measurement over the twin and log it with `record_measurement`.

## Before the first run

The layout check found problems that are not fixed. **Do not start until a person has fixed each one or signed it off** (`request_human`, urgency soon, listing them):

- safety: People hand labware into arm_1's reach at akta_1, centrifuge_hs_1, gel_1, sonicator_1, and arm_1 has no collaborative rating in the catalog; add a light curtain or a pass-through hotel at the cell edge.

These values are placeholders in the catalog. Measure each on the first run and log it with `record_measurement`:

- `sonicator_1` process.durations_s.cell_lysis = 300 (range 60-900)
- `cold_room_1` storage_slots = 300 (range 100-800)
- `dry_shipper_1, shifter_1` process.capacity = 1 (range 1-1)
- `ln2_dewar_1` process.durations_s.cryo_cooling = 120 (range 30-600)
- `dry_shipper_1` storage_slots = 3 (range 1-7)
- `bench_1` process.durations_s.manual_bench = 900 (range 300-3600)

## Devices

| Device | Model | Does | Capacity | Control | Data |
|---|---|---|---|---|---|
| `shaker_1` | Multitron Pro | cell_culture | 12 (estimated) | vendor software only | estimated |
| `centrifuge_hs_1` | Avanti JXN-26 | centrifugation | 1 (datasheet) | vendor software only | estimated |
| `sonicator_1` | Q700 Sonicator | cell_lysis | 1 (datasheet) | vendor software only | estimated |
| `akta_1` | ÄKTA pure 25 | protein_purification | 1 (estimated) | open standard | estimated |
| `gel_1` | Mini-PROTEAN Tetra Cell with PowerPac Basic | protein_qc | 4 (datasheet) | vendor software only | estimated |
| `benchtop_centrifuge_1` | Centrifuge 5810 R | centrifugation | 16 (datasheet) | vendor api | estimated |
| `nanodrop_1` | NanoDrop Ultra (successor to NanoDrop One) | concentration_measurement | 1 (datasheet) | vendor software only | datasheet |
| `mosquito_1` | mosquito Xtal3 | crystallization_setup | 3 (datasheet) | unconfirmed | estimated |
| `incubator_1` | STX44 | incubation | 44 (estimated) | open standard | estimated |
| `imager_1` | Rock Imager 1000 | crystal_imaging | 1000 (estimated) | vendor software only | datasheet |
| `cold_room_1` | Kold Locker walk-in cooler (8 ft x 8 ft) | transport/support | 300 (estimated) | none listed | estimated |
| `echo_1` | Echo 525 | crystal_soaking | 1 (estimated) | vendor software only | estimated |
| `shifter_1` | Crystal Shifter | crystal_harvesting | 1 (placeholder) | vendor software only | placeholder |
| `vib_table_1` | CleanBench 63 Series | transport/support | 1 (datasheet) | none listed | datasheet |
| `ln2_dewar_1` | ICB35-10 (formerly TW35-10) LN2 freezer | cryo_cooling | 10 (estimated) | none listed | estimated |
| `dry_shipper_1` | CX100 Cryo Express Dry Shipper | transport/support | 3 (placeholder) | vendor software only | estimated |
| `bench_1` | Adjustable-height basic work bench (06-000-654) | manual_bench | 2 (placeholder) | none listed | placeholder |
| `arm_1` | UR5e | transport/support | 1 (estimated) | vendor software only | estimated |

## Workflow and handoffs

Steps in run order. Times are the twin's expected value and range per unit of labware.

1. **E. coli expression in shake flasks** (`expression`, automated) on `shaker_1` (start). Expect 18.0 h (12.0 h-30.0 h, estimated); pause and escalate past 45.0 h.
   - handoff `shaker_1` to `centrifuge_hs_1` by `skilled_operator_1` (1.87 m, ~17 s)
2. **Cell harvest spin** (`cell_harvest`, manual, operator: skilled_operator) on `centrifuge_hs_1` after expression. Expect 30 min (10 min-60 min, estimated); pause and escalate past 90 min.
   - handoff `centrifuge_hs_1` to `sonicator_1` by `skilled_operator_1` (4.87 m, ~20 s)
3. **Cell lysis** (`lysis`, manual, operator: skilled_operator) on `sonicator_1` after cell_harvest. Expect 20 min (10 min-45 min, estimated); pause and escalate past 68 min.
   - handoff `sonicator_1` to `centrifuge_hs_1` by `skilled_operator_1` (4.87 m, ~20 s)
4. **Lysate clarification spin** (`clarification`, manual, operator: skilled_operator) on `centrifuge_hs_1` after lysis. Expect 30 min (10 min-60 min, estimated); pause and escalate past 90 min.
   - handoff `centrifuge_hs_1` to `akta_1` by `skilled_operator_1` (4.85 m, ~20 s)
5. **Affinity chromatography** (`affinity_purification`, semi automated, operator: skilled_operator) on `akta_1` after clarification. Expect 60 min (20 min-4.0 h, estimated); pause and escalate past 6.0 h.
6. **Size-exclusion polishing** (`sec_purification`, semi automated, operator: skilled_operator) on `akta_1` after affinity_purification. Expect 60 min (30 min-4.0 h, estimated); pause and escalate past 6.0 h.
   - handoff `akta_1` to `gel_1` by `arm_1` (0.79 m, ~10 s)
7. **SDS-PAGE purity QC** (`protein_qc`, manual, operator: skilled_operator) on `gel_1` after sec_purification. Expect 40 min (35 min-45 min, datasheet); pause and escalate past 68 min.
   - handoff `gel_1` to `benchtop_centrifuge_1` by `skilled_operator_1` (2.88 m, ~18 s)
8. **Concentrate protein (centrifugal concentrator)** (`concentrate`, manual, operator: skilled_operator) on `benchtop_centrifuge_1` after protein_qc. Expect 20 min (10 min-60 min, estimated); pause and escalate past 90 min.
   - handoff `benchtop_centrifuge_1` to `nanodrop_1` by `skilled_operator_1` (1.72 m, ~17 s)
9. **Concentration measurement** (`concentration_check`, manual, operator: skilled_operator) on `nanodrop_1` after concentrate. Expect 3 min (60 s-6 min, estimated); pause and escalate past 9 min.
   - handoff `nanodrop_1` to `mosquito_1` by `skilled_operator_1` (3.72 m, ~19 s)
10. **Crystallisation drop setup** (`drop_setup`, semi automated, operator: skilled_operator) on `mosquito_1` after concentration_check. Expect 24 min (12 min-60 min, estimated); pause and escalate past 90 min.
   - handoff `mosquito_1` to `imager_1` by `skilled_operator_1` (2.19 m, ~17 s)
11. **Inspection t0** (`image_t0`, automated) on `imager_1` after drop_setup. Expect 3 min (3 min-4 min, estimated); pause and escalate past 6 min.
   - handoff `imager_1` to `incubator_1` by `skilled_operator_1` (2.22 m, ~17 s)
12. **Crystal growth residence day 0-1** (`grow_1`, automated) on `incubator_1` after image_t0. Expect 24.0 h (12.0 h-2.0 d, estimated); pause and escalate past 3.0 d.
   - handoff `incubator_1` to `imager_1` by `skilled_operator_1` (2.22 m, ~17 s)
13. **Inspection day 1** (`image_d1`, automated) on `imager_1` after grow_1. Expect 3 min (3 min-4 min, estimated); pause and escalate past 6 min.
   - handoff `imager_1` to `incubator_1` by `skilled_operator_1` (2.22 m, ~17 s)
14. **Crystal growth residence day 1-3** (`grow_2`, automated) on `incubator_1` after image_d1. Expect 2.0 d (24.0 h-12.0 d, estimated); pause and escalate past 18.0 d.
   - handoff `incubator_1` to `imager_1` by `skilled_operator_1` (2.22 m, ~17 s)
15. **Inspection day 3** (`image_d3`, automated) on `imager_1` after grow_2. Expect 3 min (3 min-4 min, estimated); pause and escalate past 6 min.
   - handoff `imager_1` to `bench_1` by `skilled_operator_1` (4.31 m, ~19 s)
16. **Image review and drop selection** (`drop_selection`, manual, operator: skilled_operator) on `bench_1` after image_d3. Expect 10 min (5 min-30 min, estimated); pause and escalate past 45 min.
   - handoff `bench_1` to `echo_1` by `skilled_operator_1` (6.13 m, ~21 s)
17. **Acoustic fragment soaking** (`soak_dispense`, automated) on `echo_1` after drop_selection. Expect 15 min (5 min-40 min, estimated); pause and escalate past 60 min.
   - handoff `echo_1` to `incubator_1` by `skilled_operator_1` (2.11 m, ~17 s)
18. **Soak residence** (`soak_residence`, automated) on `incubator_1` after soak_dispense. Expect 2.0 h (60 min-24.0 h, estimated); pause and escalate past 36.0 h.
   - handoff `incubator_1` to `shifter_1` by `skilled_operator_1` (2.38 m, ~17 s)
19. **Shifter-assisted manual crystal harvesting** (`harvest`, manual, operator: skilled_operator) on `shifter_1` after soak_residence. Expect 19 min (8 min-19 min, literature); pause and escalate past 29 min.
   - handoff `shifter_1` to `ln2_dewar_1` by `skilled_operator_1` (2.49 m, ~18 s)
20. **Load filled puck into charged dry shipper** (`puck_to_shipper`, manual, operator: skilled_operator) on `ln2_dewar_1` after harvest. Expect 5 min (2 min-15 min, estimated); pause and escalate past 22 min.
21. **Ship to synchrotron, beamline queue and diffraction** (`ship_and_collect`, external) on people outside the lab after puck_to_shipper. Expect 32 min (16 min-80 min, estimated); pause and escalate past 2.0 h.
22. **In-silico processing and hit analysis** (`hit_analysis`, in silico) on compute after ship_and_collect. Expect 60 min (30 min-4.0 h, estimated); pause and escalate past 6.0 h.

## Run order and dispatch

The twin's bottleneck is `incubator_1` (busy 85%; steps grow_1, grow_2, soak_residence; parallel units incubator_1).
Pull-based release paced by the bottleneck (drum-buffer-rope): keep 1-2 units queued in front of incubator_1 (grow_1, grow_2, soak_residence) so it never idles, and release a new unit at the first step only when that buffer drops below 2. Among ready steps, serve the one feeding the bottleneck first, then oldest labware first.
_Heuristic from the twin's utilisation; not an optimised schedule. Confirm in the simulator before relying on it._

Work-in-progress limits (never exceed): `incubator_1` 44, `imager_1` 1000, `cold_room_1` 300, `ln2_dewar_1` 10, `dry_shipper_1` 3.

## Safety rules (hard limits)

- Only call tools in the manifest, with step ids and routes from their enums. Never improvise a device action, parameter or route that is not listed.
- Never load a device beyond its capacity or storage slots, and never load labware types it does not accept.
- Never start a step before every step in its `after` list has finished for that labware unit.
- Keep walkways of at least 1.0 m and egress of at least 1.2 m clear; mobile robots must not park in them.
- flammable solvents: akta_1 must only run inside a fume_hood or ventilated zone with its extraction or monitoring confirmed on.
- toxic reagents: gel_1 must only run inside a fume_hood zone with its extraction or monitoring confirmed on.
- cryogens: dry_shipper_1, ln2_dewar_1, shifter_1 must only run inside a cryogen zone with its extraction or monitoring confirmed on.
- Cryogens: no one handles liquid nitrogen alone; confirm the O2 monitor reads normal before any cryo step.
- High-g centrifuge: only start a run when the rotor is balanced and the lid interlock reports closed.

## When to call a person

- Manual or semi-automated steps (cell_harvest, lysis, clarification, affinity_purification, sec_purification, protein_qc, concentrate, concentration_check, drop_setup, drop_selection, harvest, puck_to_shipper): call `request_human` with the step's operator role before the labware arrives. skilled_operator works 8 h shifts. Out of shift, hold the labware in storage rather than skipping the step.
- External steps (ship_and_collect) leave the lab: a human books, packs and ships them. Never mark them done yourself.
- A step still running at 1.5x its high bound (`pause_after_s` in the run order) is outside what the twin expects: check the device status, `pause_line` from that step, and `request_human` (urgency soon).
- Any device error, safety interlock, labware mismatch or barcode you cannot read: stop that device, `request_human` (urgency now). Do not retry a failed physical action more than once.
- dry_shipper_1 hold contents for about 12.6 d each: track when each was charged, alert a human at 75% of that, and ship or unload before it expires.
- No confirmed programmable interface for echo_1, imager_1, mosquito_1, shaker_1: until a driver is verified, treat their tools as 'ask a human to do this and confirm', not as direct control.
- The twin gives only a 10% chance of meeting the 300 crystals_per_day target. Tell the lab manager on day one instead of pushing devices past their limits to catch up.
- Design claim refuted by the verifier: "Median simulated throughput meets the 300 crystals/day target" (verified throughput.p50 = 172.0). Never report the claimed value as expected performance; use the verified one.
- Design claim refuted by the verifier: "Layout has zero violations" (verified layout.violations = 1.0). Never report the claimed value as expected performance; use the verified one.

## What the twin expects

Throughput P10/P50/P90: 89.1 / 123.8 / 229.8 crystals_per_day (target 300, chance of meeting it 0.1).

**The verifier did not reproduce this.** Its independent recompute gives throughput.p50 = 172.0. Plan on the verified number until real runs say otherwise.

Inputs that move throughput most (measure these first): grow_2.duration_s (-190.9), puck_to_shipper.duration_s (-48.2), soak_residence.duration_s (-20.6), affinity_purification.duration_s (+20.6), sec_purification.duration_s (+9.2).

If real throughput or utilisation drifts outside these bands for a full day, tell the lab manager and log the measurements so the twin can be re-run. Do not hide a shortfall by skipping QC or overloading devices.
