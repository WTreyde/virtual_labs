# Known-bottleneck check

Can the simulator find the bottleneck in a real autonomous lab whose authors already reported it?
Run `cd backend && python -m labforge.known_bottlenecks.run` (local catalog, no API key, ~2 s).

| Case | Reported bottleneck | Simulator's busiest unit | Throughput: simulated P50 vs observed |
|---|---|---|---|
| Liverpool mobile robotic chemist ([Burger et al., Nature 2020](https://www.nature.com/articles/s41586-020-2442-2)) | GC analysis ("The slowest step in the workflow is the GC analysis") | GC, 94% busy (photolysis next at 46%) | 5.8 vs 5.4 batches/day (+8%) |
| XChem harvesting, manual ~8 crystals/h ([Wright et al., Acta D 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC7787106/)) | crystal harvesting | harvest bench, 93% busy | 58 vs 64 crystals per 8 h (−9%) |
| XChem harvesting with Shifter ~103 crystals/h (same paper) | crystal harvesting | harvest bench, 98% busy | 730 vs 824 crystals per 8 h (−11%) |

Figures are from the simulator on `main` at 8ed4eae. On Maxim's rewrite (PR #1) all three still match, with errors of +15%, −9% and −9%.

What-if on Burger: halving GC time roughly doubles throughput (5.5 → 11.5 batches/day) and GC stays the limit; a second GC gives 11, a third 14, where photolysis starts to bind.

## Honest caveats
- In these serial, one-unit-per-station lines the bottleneck is the longest step, so identity is close to guaranteed. They show the plumbing is right, not that the simulator finds non-obvious bottlenecks.
- XChem throughput is partly circular: the harvest rate is an input. The XChem "observed" figure is the paper's rate times one shift, not a measured facility output.
- Burger prep-station times are our split of the paper's 95 min (`placeholder`). Without downtime the P10–P90 band (6.0–6.5 batches/day) misses the observed 5.4.
- With the simulator's optional downtime model (`simulate(..., downtime=...)`, a6657fc), robot charging ~32% of the time does **not** by itself explain the gap. The robot is only ~5% busy and racks queue at each station, so short charge blocks are absorbed. The band covers 5.4 only if charging comes in long blocks or as random outages, and the paper reports neither, so treat this as unexplained rather than fixed:

  | Downtime on `robot_1` (20 replicates, 96 h) | P10–P50–P90 batches/day | Covers 5.4? |
  |---|---|---|
  | none | 6.0–6.2–6.5 | no |
  | charging 32%, 1 h or 4 h cycle | 6.0–6.0–6.2 | no |
  | charging 32%, 8 h cycle | 5.8–6.0–6.0 | no |
  | charging 32%, 12 h cycle (~3.8 h charges) | 5.0–5.9–6.0 | yes |
  | random outages, MTBF 2.1 h / MTTR 1 h (32% down) | 5.2–5.6–6.0 | yes |

## Missing for a stronger test
- A sourced charging pattern for the Liverpool robot (the downtime model exists; the input does not). Operator shifts are modelled but unused in these cases.
- Batching (`batch_size`), e.g. A-Lab box furnaces holding several crucibles; then A-Lab (4 box furnaces, 1 XRD, 353 experiments in 17 days, [Szymanski et al. 2023](https://www.nature.com/articles/s41586-023-06734-w)) becomes a throughput check. Its paper names no bottleneck.
- The equipment here lives in `cases.py`, not Strand B's catalog.
