# Full human harvesting replay — 3 October 2026

Fresh live Opus run against main `440a9ff` with this PR's agent changes. Amass credentials were available. The recording completed with a workflow, independently checked claims, report and original 500-event animation. `frontend/public/replays/fbdd.json` copies this run; chemistry uses the previously successful live chemistry record from `scenarios_20261003_repaired` (not a new run).

## Honest outcome

All XChem structural/pipeline checks pass, including full-time manual harvesting, handling-based puck loading, external diffraction and no in-house X-ray. **Independent throughput agreement fails**: planner 312 versus verifier 112 crystals/day. The overall gate is therefore false. Target 300 is refuted by the verifier; budget $1,035,400 is supported; zero layout violations is refuted (11). This is an informative completed replay, not a passing physical design.

The busiest instrument is the growth hotel (80.1%). Imaging is 5.8%; harvesting is 14.5% of calendar time. Operators use 74.6% and 75.1% of scheduled shifts. Operator and instrument percentages have different denominators. We did not tune inputs or add parallel units to obtain the requested harvesting-limited story.

## Model audit

- Rock Imager camera retains catalog process capacity 1 and 180 seconds per plate inspection, estimated schedule days 0, 1 and 3. Its 1000 storage slots are not interpreted as parallel cameras. Growth and soak residence use a separate Cytomat hotel; crystallisation-plate compatibility needs catalog confirmation.
- Shifter harvesting is `manual`: an operator is reserved throughout. Reviewed Wright et al., Acta D 2021 section 3.2.2 (https://doi.org/10.1107/S2059798320014114) reports an unassisted 8/hour survey baseline including ancillary work, and a Shifter mean 35 seconds/mount (103/hour; median 30 seconds) across 8271 mounts. These are equipment/context-specific measurements, not guaranteed rates.
- The agent assumes 32 harvested crystals per plate, taking 1118 seconds at 103/hour, then fans out to two 16-pin pucks. The independent verifier restores catalog harvesting 7200 seconds because the estimate is below its 1800-second floor. Catalog duration is a placeholder; the model explicitly records the differing batch basis. No workaround or post-hoc duration change was applied.
- Manual puck loading uses a bench with an operator. Seven dry shippers remain transit containers, with a disclosed placeholder three-puck capacity and estimated four-day external transit/beamline queue. Container concurrency is not independently established by this replay.

## Ownership handoff

**Max (catalog):** confirm harvesting duration per crystal/plate and uncertainty with batch basis; confirm crystallisation-plate support for the growth hotel and dry-shipper puck capacity.

**Maxim (layout/sim):** reconcile verifier duration restoration with the actual crystals-per-batch/labware basis, review residence/storage modelling, and resolve the 11 layout violations. A duration below a catalog floor is not automatically validated by a literature citation, and this PR does not bypass that safeguard.

## Evidence and output budget

Amass returned real literature candidates for protein expression and XChem searches, retained with DOI metadata in `evidence_searches` and the report. They are labelled candidates requiring relevance review. The Wright query was unavailable in this run; exact harvesting numbers come from separately labelled reviewed public primary evidence, not a fabricated Amass retrieval. Public references enter the allowed citation set only through `search_evidence`.

Two earlier attempts stopped at `max_tokens` before emitting a workflow. `budget_diagnostics.json` distinguishes these from refusal. Increasing the response budget from 16000 to 24000 allowed the complete record. Chemistry refusal remains handled gracefully; the previously recorded successful abstract equipment-demand benchmark is now published as `?replay=chem`.

Validation: main-based `make check` passes 118 tests and 12 subtests plus example/schema validation and frontend typecheck. A temporary merge of latest `origin/strand/sim` (`3e89920`) passes 119 tests and 12 subtests; merge aborted. Both public replay JSON files serve with completed, checked designs and 500 timeline events. No pending catalog/simulator branches are shipped here.
