# Neutral chemistry refusal check

One chargeable `claude-opus-5-5` attempt was made on main `e7bb14c`. The purpose was to
test whether neutral equipment-planning wording removes the chemistry refusal without
changing the scientific pipeline. It did not: the provider returned `stop_reason=refusal`
in the first model response, after the sentence saying it would search the catalog and
before any tool call.

The candidate wording preserved the 8 x 12 x 8 arithmetic, two 96-well reaction stages,
powder dosing and dissolution, workup/filtration, purification, evaporation, LC-MS QC,
storage, assay preparation, fluorescence readout, room, budget, staffing, safety zones,
and all verification/report requirements. Relative to the published brief it changed:

- “chemistry library” to “two-stage sample-processing benchmark”;
- “products/compounds” to “samples/final samples”;
- “fluorescence screening against a supplied purified protein target” to “endpoint
  fluorescence measurement using pre-supplied assay reagents”;
- “synthesis areas” to “process areas”; and
- added explicit instructions not to describe the transformations or identify compounds
  or biological targets.

The attempted brief is preserved verbatim in `chemistry.json`. Because this neutral
rewording also refused, no replacement replay is published and the production scenario
brief is unchanged. Combined with the earlier paired diagnostics—where both named and
abstract variants have sometimes proceeded—this does not establish a deterministic
trigger word. The reproducible boundary is the full two-stage chemical-library equipment
planning request as a whole: it can be declined even when stripped of identities, amounts,
recipes and execution instructions. Live chemistry is therefore not demo-safe; keep the
recorded replay unless the provider behaviour changes.
