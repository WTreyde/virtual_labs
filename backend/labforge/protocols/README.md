# Protocol library (Strand B)

20 published lab protocols for the two demo pipelines in `docs/pipelines.md`: 10 for the chemistry library (HTE setup, powder dosing, parallel synthesis and workup, amide library with SPE, LC-MS QC, acoustic dose-response, TR-FRET screening, Z' validation) and 10 for XChem (expression, Ni-NTA, size exclusion, SDS-PAGE, mosquito drop setting, Echo soaking, Shifter harvesting, cryo-cooling and puck loading, dry-shipper shipping, PanDDA).

- One file per protocol in `library/`, validated against `protocol.schema.json` (a Strand B draft; propose for `schemas/` if the UI adopts it).
- Steps are mapped to LabForge capabilities and catalog ids, so a design can find its protocols: `labforge.protocols.for_workflow(workflow)`.
- Static export for the offline UI: `cd backend && python -m labforge.protocols ../frontend/public/protocols` (writes `index.json` and `<id>.json`).

## Licensing and honesty rules
- **Every protocol is a paraphrase in our own words with a link to the original.** No full text is copied. The UI must always show the source link and the licence, and must never present a paraphrase as the official protocol.
- Licences are recorded exactly as stated. Five sources are non-commercial or no-derivatives (CC BY-NC, BY-NC-ND, BY-NC-SA), and four have no stated licence ("unknown: link and paraphrase only"). Paraphrase-and-link is appropriate for all of them; do not paste their text.
- Times carry confidence: `literature` when the source states them, `estimated` when derived (the note says how). Where no time is given, there is none: show "time not stated by source".
- Catalog ids are our suggested equivalents, not necessarily the instrument the paper used; the notes say when.

## Known gaps
- No open step-by-step Suzuki-Miyaura HTE procedure was found (sources paywalled); the HTE setup protocol covers it generically.
- The TR-FRET example is a CBP bromodomain screen, not BRD4.
- No source for the E. coli transformation step; lysis is covered inside the Ni-NTA protocol.
- The expression, Ni-NTA and SEC protocols come from one paper's construct (Kroupova 2024): a worked example, not a universal recipe.
- One candidate (a university NanoDrop handout) was dropped: no licence, and the document contained login credentials.
