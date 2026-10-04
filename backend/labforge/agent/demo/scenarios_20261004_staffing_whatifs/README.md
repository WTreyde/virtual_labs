# XChem imager + staffing verifier what-ifs

These are deterministic verifier runs on the recorded XChem design. No agent
or external API call was made. Both use 50 replicates with verifier seed 12345,
move only the three crystal-growth residence steps from the STX44 to the
existing Rock Imager storage hotel, and preserve equipment, workflow timing,
uncertainty, yield, inspection and external-queue assumptions.

The comparison baseline is the recorded independently verified **424.0
crystals/day**.

## A. Rock Imager growth plus a third operator

- Verified P10/P50/P90: **485.3 / 634.7 / 821.3 crystals/day**.
- P50 change versus baseline: **+210.7/day**.
- All three operators bind at **94.0%, 93.9% and 93.5%** of their shifts.
- Zero layout violations; no catalog duration was restored by the verifier.

This variant beats the baseline, but it remains staff-limited. The Rock Imager
is not reported as the bottleneck.

## B. Same design plus a second staffed shift

The current LabSpec/simulator represents this as three operators available for
16 hours/day. That preserves the aggregate six 8-hour operator-shifts and the
16-hour coverage window, but does not model handoff overhead or separately
stagger named workers.

- Verified P10/P50/P90: **1082.7 / 1306.7 / 1642.7 crystals/day**.
- P50 change versus baseline: **+882.7/day**.
- All three aggregate operator resources still bind at about **92.2–92.3%** of
  their available time.
- Zero layout violations; no catalog duration was restored by the verifier.

Both what-ifs beat 424/day. The supported pitch remains: the imager has spare
capacity after growth moves into it, while skilled staff are the next limit.
