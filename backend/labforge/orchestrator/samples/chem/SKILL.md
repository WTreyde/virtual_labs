---
name: run-chem-lib-768
description: Orchestrate the Two-stage chemistry library benchmark (abstract) lab through its instrument APIs. Use when running, scheduling or troubleshooting this lab's workflow; covers the devices and their limits, run order, safety rules and when to call a person.
---

# Running Two-stage chemistry library benchmark (abstract)

You orchestrate this lab. Goal: about 768 compounds_per_day (24 h/day), safely. You have the tools in `tools.json`; each device's limits, zone and confidence are listed there. This file was generated from the lab's digital twin (workflow `chem_lib_768_wf_v1`, layout `chem_lib_768_wf_v1_layout`, simulation `chem_lib_768_wf_v1_layout_sim`). Where the twin was unsure, this file says so; trust a measurement over the twin and log it with `record_measurement`.

## Before the first run

The layout check found problems that are not fixed. **Do not start until a person has fixed each one or signed it off** (`request_human`, urgency soon, listing them):

- clearance: glovebox_1 and biotage_spe_1 are closer than their service clearance.
- zone_mismatch: quantos_1 must sit in a fume hood zone (inferred: powder_dosing with toxic reagents in the brief).
- zone_mismatch: glovebox_1 must sit in a fume hood zone (catalog: mbraun_glovebox has toxic reagents).
- zone_mismatch: hamilton_1 must sit in a bsl2 zone (catalog: hamilton_microlab_star has biohazard).
- zone_mismatch: lcms_1 must sit in a fume hood zone (catalog: agilent_1290_lcmsd_iq has toxic reagents).
- zone_mismatch: lcms_2 must sit in a fume hood zone (catalog: agilent_1290_lcmsd_iq has toxic reagents).
- zone_mismatch: hood_1 must sit in a fume hood zone (catalog: labconco_fume_hood has toxic reagents).
- zone_mismatch: hood_2 must sit in a fume hood zone (catalog: labconco_fume_hood has toxic reagents).
- egress_blocked: No 1.0 m walkway from the door to where someone works at biotage_spe_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at genevac_1.
- egress_blocked: No 1.0 m walkway from the door to where someone works at glovebox_1.

These values are placeholders in the catalog. Measure each on the first run and log it with `record_measurement`:

- `glovebox_1` process.durations_s.inert_atmosphere = 600 (range 300-1800)
- `swing_1-2` process.durations_s.reaction = 14400 (range 3600-86400)
- `genevac_1` process.durations_s.evaporation = 5400 (range 1800-14400)
- `genevac_1` process.capacity = 6 (range 3-12)
- `store_1` process.durations_s.compound_storage = 120 (range 30-600)
- `amr_1` transport.pick_place_s = 15 (range 8-60)

## Devices

| Device | Model | Does | Capacity | Control | Data |
|---|---|---|---|---|---|
| `quantos_1` | Quantos QB5 | powder_dosing | 1 (datasheet) | vendor software only | estimated |
| `glovebox_1` | LABstar pro SP | inert_atmosphere | 1 (estimated) | vendor software only | estimated |
| `hamilton_1` | Microlab STAR | liquid_handling | 1 (estimated) | vendor software only | estimated |
| `swing_1-2` | SWING XL | reaction | 1 (estimated) | vendor software only | estimated |
| `biotage_filt_1` | PRESSURE+ 96 | filtration | 1 (estimated) | vendor software only | estimated |
| `biotage_spe_1` | PRESSURE+ 96 | solid_phase_extraction | 1 (estimated) | vendor software only | estimated |
| `genevac_1` | Genevac HT-6 (Series 3i) | evaporation | 6 (placeholder) | vendor api | estimated |
| `lcms_1-2` | 1290 Infinity II LC with InfinityLab LC/MSD iQ | lcms | 1 (estimated) | vendor software only | estimated |
| `store_1` | SampleStore (ambient to -20 C) | compound_storage | 1094 (estimated) | vendor software only | estimated |
| `incubator_1` | STX44 | incubation | 44 (estimated) | open standard | estimated |
| `reader_1` | CLARIOstar Plus | fluorescence_read | 1 (estimated) | vendor api | estimated |
| `amr_1` | KMR iiwa | transport/support | 1 (estimated) | vendor api | estimated |
| `hood_1-2` | Protector XStream 6 ft | transport/support | 1 (datasheet) | none listed | datasheet |

## Workflow and handoffs

Steps in run order. Times are the twin's expected value and range per unit of labware.

1. **Powder-dosing stock preparation** (`stock_powder`, semi automated, operator: chemist) on `quantos_1` (start). Expect 2.3 h (56 min-7.0 h, estimated); pause and escalate past 10.5 h.
   - handoff `quantos_1` to `glovebox_1` by `amr_1` (4.05 m, ~35 s)
2. **Inert handling of stock rack** (`inert_transfer`, semi automated, operator: chemist) on `glovebox_1` after stock_powder. Expect 10 min (5 min-30 min, placeholder); pause and escalate past 45 min.
   - handoff `glovebox_1` to `hamilton_1` by `amr_1` (3.28 m, ~34 s)
3. **Liquid-handling dissolution of stocks** (`dissolve`, automated) on `hamilton_1` after inert_transfer. Expect 15 min (5 min-45 min, estimated); pause and escalate past 68 min.
4. **Stage-1 dispense into reaction block** (`s1_dispense`, automated) on `hamilton_1` after dissolve. Expect 10 min (5 min-30 min, estimated); pause and escalate past 45 min.
   - handoff `hamilton_1` to `swing_1` by `amr_1` (4.23 m, ~35 s)
   - handoff `hamilton_1` to `swing_2` by `amr_1` (3.88 m, ~35 s)
5. **Stage-1 reaction (inert)** (`s1_react`, automated) on `swing_1` or `swing_2` after s1_dispense. Expect 4.0 h (2.0 h-8.0 h, placeholder); pause and escalate past 12.0 h.
   - handoff `swing_1` to `biotage_filt_1` by `amr_1` (5.42 m, ~36 s)
   - handoff `swing_2` to `biotage_filt_1` by `amr_1` (2.52 m, ~33 s)
6. **Stage-1 workup filtration** (`s1_filter`, semi automated, operator: chemist) on `biotage_filt_1` after s1_react. Expect 5 min (60 s-15 min, estimated); pause and escalate past 22 min.
   - handoff `biotage_filt_1` to `hamilton_1` by `amr_1` (3.83 m, ~35 s)
7. **Stage-2 expansion dispense (1 block -> 8 blocks)** (`s2_dispense`, automated) on `hamilton_1` after s1_filter. Expect 80 min (40 min-4.0 h, estimated); pause and escalate past 6.0 h.
   - handoff `hamilton_1` to `swing_1` by `amr_1` (4.23 m, ~35 s)
   - handoff `hamilton_1` to `swing_2` by `amr_1` (3.88 m, ~35 s)
8. **Stage-2 reaction (inert)** (`s2_react`, automated) on `swing_1` or `swing_2` after s2_dispense. Expect 4.0 h (2.0 h-8.0 h, placeholder); pause and escalate past 12.0 h.
   - handoff `swing_1` to `biotage_filt_1` by `amr_1` (5.42 m, ~36 s)
   - handoff `swing_2` to `biotage_filt_1` by `amr_1` (2.52 m, ~33 s)
9. **Stage-2 workup filtration** (`s2_filter`, semi automated, operator: chemist) on `biotage_filt_1` after s2_react. Expect 5 min (60 s-15 min, estimated); pause and escalate past 22 min.
   - handoff `biotage_filt_1` to `biotage_spe_1` by `amr_1` (3.24 m, ~34 s)
10. **Purification (SPE)** (`purify_spe`, semi automated, operator: chemist) on `biotage_spe_1` after s2_filter. Expect 10 min (5 min-30 min, estimated); pause and escalate past 45 min.
   - handoff `biotage_spe_1` to `genevac_1` by `amr_1` (2.58 m, ~33 s)
11. **Evaporation** (`evaporate`, semi automated, operator: chemist) on `genevac_1` after purify_spe. Expect 90 min (30 min-4.0 h, placeholder); pause and escalate past 6.0 h.
   - handoff `genevac_1` to `hamilton_1` by `amr_1` (5.26 m, ~36 s)
12. **Reconstitute and reformat to stock plate** (`reconstitute`, automated) on `hamilton_1` after evaporate. Expect 10 min (5 min-30 min, estimated); pause and escalate past 45 min.
   - handoff `hamilton_1` to `lcms_1` by `amr_1` (8.22 m, ~40 s)
   - handoff `hamilton_1` to `lcms_2` by `amr_1` (2.44 m, ~33 s)
13. **LC-MS QC of every product** (`lcms_qc`, automated) on `lcms_1` or `lcms_2` after reconstitute. Expect 4.0 h (2.7 h-8.0 h, estimated); pause and escalate past 12.0 h.
   - handoff `lcms_1` to `hamilton_1` by `amr_1` (8.25 m, ~40 s)
   - handoff `lcms_2` to `hamilton_1` by `amr_1` (2.44 m, ~33 s)
14. **Assay prep: compounds + supplied protein target into assay plate** (`assay_prep`, automated) on `hamilton_1` after lcms_qc. Expect 15 min (5 min-45 min, estimated); pause and escalate past 68 min.
   - handoff `hamilton_1` to `store_1` by `amr_1` (3.0 m, ~34 s)
   - handoff `hamilton_1` to `incubator_1` by `amr_1` (6.67 m, ~38 s)
15. **Compound storage of stock plate** (`store_stock`, automated) on `store_1` after assay_prep. Expect 2 min (30 s-10 min, placeholder); pause and escalate past 15 min.
15. **Assay incubation** (`incubate`, automated) on `incubator_1` after assay_prep. Expect 60 min (30 min-2.0 h, estimated); pause and escalate past 3.0 h.
   - handoff `incubator_1` to `reader_1` by `amr_1` (1.75 m, ~32 s)
16. **Fluorescence screening readout** (`read_fluor`, automated) on `reader_1` after incubate. Expect 3 min (90 s-10 min, estimated); pause and escalate past 15 min.
17. **Screening data analysis (sink)** (`hit_analysis`, in silico) on compute after read_fluor. Expect 10 min (2 min-30 min, estimated); pause and escalate past 45 min.

## Run order and dispatch

The twin's bottleneck is `swing_2` (busy 100%; steps s1_react, s2_react; parallel units swing_1, swing_2).
Pull-based release paced by the bottleneck (drum-buffer-rope): keep 1-2 units queued in front of swing_2 (s1_react, s2_react) so it never idles, and release a new unit at the first step only when that buffer drops below 2. Among ready steps, serve the one feeding the bottleneck first, then oldest labware first.
_Heuristic from the twin's utilisation; not an optimised schedule. Confirm in the simulator before relying on it._

Work-in-progress limits (never exceed): `store_1` 1094, `incubator_1` 44.

## Safety rules (hard limits)

- Only call tools in the manifest, with step ids and routes from their enums. Never improvise a device action, parameter or route that is not listed.
- Never load a device beyond its capacity or storage slots, and never load labware types it does not accept.
- Never start a step before every step in its `after` list has finished for that labware unit.
- Keep walkways of at least 1.0 m and egress of at least 1.2 m clear; mobile robots must not park in them.
- flammable solvents: biotage_filt_1, biotage_spe_1, genevac_1, hood_1-2, lcms_1-2, quantos_1, swing_1-2 must only run inside a fume_hood or ventilated zone with its extraction or monitoring confirmed on.
- toxic reagents: glovebox_1, hood_1-2, lcms_1-2, swing_1-2 must only run inside a fume_hood zone with its extraction or monitoring confirmed on.
- biohazard: hamilton_1 must only run inside a bsl2 zone with its extraction or monitoring confirmed on.

## When to call a person

- Manual or semi-automated steps (stock_powder, inert_transfer, s1_filter, s2_filter, purify_spe, evaporate): call `request_human` with the step's operator role before the labware arrives. chemist works 8 h shifts. Out of shift, hold the labware in storage rather than skipping the step.
- A step still running at 1.5x its high bound (`pause_after_s` in the run order) is outside what the twin expects: check the device status, `pause_line` from that step, and `request_human` (urgency soon).
- Any device error, safety interlock, labware mismatch or barcode you cannot read: stop that device, `request_human` (urgency now). Do not retry a failed physical action more than once.
- No confirmed programmable interface for biotage_filt_1, biotage_spe_1, glovebox_1, hamilton_1, lcms_1-2, quantos_1, store_1, swing_1-2: until a driver is verified, treat their tools as 'ask a human to do this and confirm', not as direct control.
- The twin gives only a 10% chance of meeting the 768 compounds_per_day target. Tell the lab manager on day one instead of pushing devices past their limits to catch up.
- Design claim refuted by the verifier: "Simulated P50 throughput meets the 768 compounds/day target." (verified throughput.p50 = 688.0). Never report the claimed value as expected performance; use the verified one.
- Design claim refuted by the verifier: "Total BOM is within the USD 2,000,000 budget." (verified bom.total_usd = 5506050.0). Never report the claimed value as expected performance; use the verified one.
- Design claim refuted by the verifier: "Layout has zero violations." (verified layout.violations = 11.0). Never report the claimed value as expected performance; use the verified one.

## What the twin expects

Throughput P10/P50/P90: 521.6 / 632.0 / 753.6 compounds_per_day (target 768, chance of meeting it 0.1).

**The verifier did not reproduce this.** Its independent recompute gives throughput.p50 = 688.0. Plan on the verified number until real runs say otherwise.

Inputs that move throughput most (measure these first): s2_react.duration_s (-608), s1_react.duration_s (-368), lcms_qc.duration_s (-184), stock_powder.duration_s (+80), s1_filter.duration_s (-16).

If real throughput or utilisation drifts outside these bands for a full day, tell the lab manager and log the measurements so the twin can be re-run. Do not hide a shortfall by skipping QC or overloading devices.
