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
- Burger prep-station times are our split of the paper's 95 min (`placeholder`). The +8% gap is about what the robot's charging (idle ~32% of the time) would cost; the simulator has no downtime model, so its P10–P90 band is too narrow and misses the observed value.

## Missing for a stronger test
- Downtime and charging of transporters and instruments, and operator shifts (human works 8 h, machines 24 h). These are the interactions that make bottlenecks non-obvious.
- Batching (`batch_size`), e.g. A-Lab box furnaces holding several crucibles; then A-Lab (4 box furnaces, 1 XRD, 353 experiments in 17 days, [Szymanski et al. 2023](https://www.nature.com/articles/s41586-023-06734-w)) becomes a throughput check. Its paper names no bottleneck.
- The equipment here lives in `cases.py`, not Strand B's catalog.
