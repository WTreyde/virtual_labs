# XChem replay after verifier PR #26

Recorded live with `claude-opus-5-5` from main `9998609`, after the verifier
learned the catalog's per-crystal duration basis. The runner made one baseline
turn and, because the growth/soak hotel was the busiest instrument, one separate
conditional hotel-remedy turn. Credentials and model history are not stored.

## Baseline (`xchem.json`)

- Planning throughput: P10/P50/P90 89.1/123.8/229.8 crystals/day.
- Independent verifier P50: 172.0 crystals/day. The greater-than-20% difference
  keeps the acceptance gate red; both values remain below the 300/day target.
- Actual limiting instrument: `incubator_1`, a 44-slot LiCONiC STX44 used for
  growth and soak residence, at 85.4% utilisation.
- Harvesting: 32 mount attempts at 35 seconds each = 1120 seconds per plate,
  with a 480-second catalog low bound. The Shifter is only 6.1% utilised.
- Imaging is also non-binding. One layout violation remains at unguarded UR5e
  hand-offs. Checked BOM is USD 1,022,850 against the USD 2,000,000 budget.

## Separate remedy (`xchem-whatif.json`)

The remedy adds only `incubator_2`, an identical LiCONiC STX44, and assigns the
two growth stages and soak residence across both hotels. A structured diff found
no change to step durations, uncertainty ranges, yields, imaging schedule,
operator shifts, external queue, fan-out, or output assumptions.

- Planning throughput rises to P10/P50/P90 91.5/192.6/238.0 crystals/day.
- Independent verifier P50 rises to 247.7 crystals/day; the acceptance gate
  remains red for disagreement and both values still miss 300/day.
- The two operators and two hotels bind together at roughly 89-91% utilisation.
  Harvesting remains non-binding at 8.5% and imaging at 7.9%.
- BOM rises by USD 40,000 to USD 1,062,850. The same single layout violation
  remains. Crystallisation-plate compatibility for the STX44 needs vendor
  confirmation.

The remedy is not substituted for the observed baseline. `frontend/public/replays/fbdd.json`
is copied from `xchem.json`; the what-if stays here as a separate audit record.

## Integration note

`frontend/scripts/cache_offline.py` currently also opens the new
`*.summary.json` files and fails with `KeyError: output`. The FBDD instrument
what-if cache was regenerated directly from the baseline with the same
`labforge.sim.whatif.optimise_instrument` call. The frontend owner should make
the cache script skip summary files.
