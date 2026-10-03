# Case replay refresh after the wall-placement update

Recorded once with `claude-opus-5-5` from main `88a2341`, after Maxim's wall-placement
and break-area changes merged. Credentials were loaded from the ignored repository `.env`
and are not stored in these files.

## Chemistry

The live chemistry attempt ended with provider stop reason `refusal` after catalog and
evidence searches. It returned no workflow, layout, simulation, checked claims or report.
The previous public chemistry replay is therefore retained rather than replacing a complete
recording with an incomplete result. No duplicate paid retry was made.

## XChem baseline

The fresh baseline completed its full pipeline and all structural gates. It records:

- planning throughput P10/P50/P90: 369.6 / 410.7 / 563.7 crystals/day;
- independently recomputed P50: 424.0 crystals/day;
- checked BOM: USD 1,072,775; and
- zero layout violations under the new placer.

The binding instrument is `growth_hotel_1` (`liconic_stx44`) at 82.6% calendar-time
utilisation. The Shifter is 16.0% busy and the Rock Imager camera is 8.5% busy, so this
record does not claim harvesting or imaging binds.

## Separate hotel follow-up

The conditional follow-up added only `growth_hotel_2`, another LiCONiC STX44, and assigned
the existing growth and soak residence steps to either hotel. All numeric step durations,
uncertainty ranges, yields, inspection timing, operator shifts and external queue values
are unchanged; the model shortened some descriptive `params` wording. Planning P50 rose
to 653.3 crystals/day and the verifier returned 522.7 crystals/day. The two growth hotels
then bind jointly at 60.1% and 58.9%; the Shifter is next at 22.6%.

This is not the requested Rock Imager growth what-if. Although the catalog now records
970 SBS storage slots, the simulator has one capacity dimension and sees the Rock Imager's
single-camera `process.capacity` as one slot. It cannot independently model 970 residence
slots and one camera on the same unit. Publishing this follow-up as
`imager_growth_whatif` would therefore be misleading; it remains an auditable separate
record until the simulator supports distinct storage and processing capacities.
