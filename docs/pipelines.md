# Demo pipelines

Two reference workflows the agent should be able to design end to end. Durations are rough planning estimates (marked as such in the catalog with `confidence: estimated`); the agent should cite sources via Amass where it can and widen its uncertainty where it cannot. Instruments named are typical commercial choices, not endorsements; the catalog strand fills in specs.

Legend for **Mode**: A = automated, S = semi-automated (human loads/unloads), M = manual (human operator), X = external service.

---

## 1. Chemistry: combinatorial library cascade + target screening

**Goal:** design a 2-step combinatorial library (e.g. Suzuki coupling, then amide coupling: 8 boronic acids x 12 aryl-bromide amines x 8 acids = 768 products), make it in 96-well reaction blocks, QC it, and screen every product against a protein target in a biochemical assay. Hits feed the next design round (the "cascade").

| # | Step | Mode | Typical equipment | Labware | Rough time | Notes |
|---|---|---|---|---|---|---|
| 0 | Library design | in silico | Claude + Amass (DrugCore/PatentCore for known ligands of the target) + RDKit filters | — | minutes | Enumerate products, filter by properties, pick building blocks in stock. |
| 1 | Building block stock prep | A | Powder dosing (Mettler Toledo Quantos / Chemspeed SWING GDU) + liquid handler | vials → 96-well stock plate | ~1–2 min per solid | Solids weighed and dissolved in solvent. Powder dosing is a classic bottleneck. |
| 2 | Reaction 1 setup (Suzuki) | A | Chemspeed SWING / Unchained Labs Big Kahuna, or liquid handler in an enclosure | 96-well glass-vial reaction block | ~20–30 min per block | Catalyst, base, inert atmosphere (N2 enclosure). Lives in a ventilated enclosure / fume hood zone. |
| 3 | Reaction 1 run | A | Heated shaker reaction block (e.g. Chemspeed ISYNTH, Paradox) | reaction block | 2–16 h | Long step; parallel capacity (number of blocks) drives throughput. |
| 4 | Workup + filtration | A | Liquid handler + SPE / filter plates + vacuum or positive-pressure manifold | filter plate → 96 deep-well | ~20 min per block | Remove Pd and salts before step 2. |
| 5 | Reaction 2 setup + run (amide coupling) | A | Same as 2–3 | reaction block | 1–4 h | Each product from step 1 split across 8 acids: plate count multiplies here. |
| 6 | Solvent evaporation | A | Centrifugal evaporator (Genevac EZ-2 / HT-6) | deep-well plates | 1–3 h per batch | Batch device; capacity per run matters. |
| 7 | QC by LC-MS | A | UPLC-MS with plate autosampler (Waters Acquity / Agilent InfinityLab) | 96-well | ~2–3 min per sample | Usually THE bottleneck: 768 samples x 2.5 min ≈ 32 h on one instrument. |
| 8 | Normalise in DMSO, reformat | A | Liquid handler | 384-well source plates (Echo-qualified) | ~15 min per plate | Concentration from LC-MS UV/ELSD estimate, flagged uncertain. |
| 9 | Compound storage | A | Compound store / plate hotel at RT or 4 °C | 384-well | — | |
| 10 | Assay plate prep | A | Acoustic dispenser (Beckman Echo 650) | 1536 or 384-well assay plates | ~2–5 min per plate | nL transfers of each compound, plus controls. |
| 11 | Add protein + substrate | A | Bulk reagent dispenser (Thermo Multidrop Combi) | assay plates | ~1 min per plate | Protein prepared by an operator (M) at shift start; stability window matters. |
| 12 | Incubate | A | Incubator / plate hotel | assay plates | 30–60 min | |
| 13 | Read | A | Multimode reader (BMG PHERAstar FSX) — TR-FRET / FP | assay plates | 2–5 min per plate | |
| 14 | Analysis + next design round | in silico | Claude + analysis code | — | minutes | Z' factor, IC50s for hits; flags assay interference and impure compounds. |

Transport: a central rail or 1–2 arms for the screening cell; a mobile robot or human operator between the synthesis area (fume-hood zone) and the screening cell, which is where the "opposite ends of the room" bottleneck typically appears. Human operator: solvent/reagent replenishment, waste, protein prep.

Safety rules the layout must respect: synthesis and evaporation in a ventilated zone; solvent waste and flammable storage away from heat sources; humans never in the arm's work envelope without a light curtain/collaborative robot.

---

## 2. Biology: fragment-based drug discovery by crystallography (XChem-style)

**Goal:** express and purify a target protein, grow crystals, soak hundreds of fragments into individual crystals, harvest and cryo-cool them, and collect diffraction data to find fragment hits.

| # | Step | Mode | Typical equipment | Labware | Rough time | Notes |
|---|---|---|---|---|---|---|
| 1 | Transformation + starter cultures | S | Liquid handler, shaking incubator | 24 deep-well / tubes | overnight | |
| 2 | Expression (scale-up + induction) | S | Large shaking incubator (Infors Multitron) or parallel bioreactor (Sartorius ambr 250) | 2 L baffled flasks / bioreactor | ~4 h growth + 16 h induction | Needs mg of protein; plan litres, not wells. |
| 3 | Harvest | S | Floor centrifuge (Beckman Avanti) | 1 L bottles | ~30 min | Heavy human handling. |
| 4 | Lysis + clarification | S | Homogeniser / sonicator, high-speed centrifuge | tubes | ~1 h | Cold room or 4 °C. |
| 5 | Purification | S | Cytiva ÄKTA pure / ÄKTA avant: affinity (Ni-NTA) then size exclusion | columns, fractions | 4–8 h | Usually a human-attended bottleneck. |
| 6 | Protein QC + concentration | S | Capillary electrophoresis (PerkinElmer LabChip GXII) or SDS-PAGE, UV (NanoDrop / Lunatic), spin concentrators | 96-well / tubes | ~1 h | |
| 7 | Crystallisation drop setting | A | Nanolitre dispenser (SPT Labtech mosquito / Formulatrix NT8) | 96-well sitting-drop plates (e.g. SWISSCI 3-drop) | ~2–5 min per plate | |
| 8 | Crystal growth + imaging | A | Crystal hotel + imager (Formulatrix Rock Imager) at 20 °C | crystallisation plates | days | Long, so the hotel's capacity drives throughput. |
| 9 | Crystal scoring + drop selection | in silico | Image classifier / Claude vision + human check | — | minutes | Where the agent should flag low confidence. |
| 10 | Fragment soaking | A | Acoustic dispenser (Beckman Echo) directly into drops | crystal plates + fragment library source plate (e.g. DSi-Poised) | ~5 min per plate, then 1–3 h soak | One fragment per crystal. |
| 11 | Crystal harvesting ("fishing") | S | Shifter (Oxford Lab Technologies) with a human at the microscope | crystal plates → loops on pins | ~10–20 s per crystal for an expert | Human throughput limit (~150–300 crystals per operator-day). |
| 12 | Cryo-cooling + puck loading | M | Liquid nitrogen dewar, Unipucks | pucks (16 pins) | per crystal, in-line with 11 | Cryogen safety: ventilation and O2 monitor. |
| 13 | Diffraction data collection | X | Synchrotron (e.g. Diamond I04-1, unattended mode); no in-house X-ray (team decision) | pucks in a dry shipper | days turnaround; ~1–5 min per crystal at the beamline | Model as an external step with queue time. |
| 14 | Hit identification | in silico | PanDDA / automated processing + Claude summary | — | hours | Report hit rate with uncertainty. |

Transport: plates move between dispenser, imager hotel and acoustic dispenser (arm or human); expression and purification are human-run, so operator walking distance between incubators, centrifuge and ÄKTA (often in a cold room) is the layout problem to optimise.

Safety rules: BSL-1/2 zone for expression; centrifuges with clearance; liquid nitrogen handling area ventilated with an O2 sensor; Echo and imager on vibration-free benches.

---

## What "makes sense" checks the agent should run (and the benchmark tests)

- Mass balance: protein yield per litre x litres ≥ protein needed for all crystallisation plates.
- Plate arithmetic: library size / wells per plate = plate count at each step; step 5 in chemistry multiplies plates.
- Bottleneck sanity: LC-MS QC and crystal harvesting should usually show up as limits; if the simulator says otherwise, the agent should double-check rather than celebrate.
- External steps (synchrotron) cannot be "optimised away" by the layout.
