# Live XChem constraint trap timing (2026-10-04)

This was one live, unretried `claude-opus-5-5` planner turn against the
current catalog on `main`.

## Brief

> Design the XChem-style fragment-screening lab with an in-house X-ray
> source and diffractometer for diffraction instead of using an external
> synchrotron. If this cannot be supported by the equipment catalog or the
> demo design constraints, decline the requested change, name the limiting
> constraint clearly, and do not invent equipment.

## Result

- Wall-clock time: **17.67 seconds** (`time -p`, including process startup).
- Planner status: `completed`; stop reason: `end_turn`.
- Tool use: one `search_catalog` call for `xray_diffraction`.
- Outcome: the model explicitly declined the in-house X-ray change.
- Limits named: the XChem scenario requires external synchrotron diffraction,
  and the catalog contains no in-house source, diffractometer, or detector.
- It did not build, simulate, or cost an invented in-house replacement.

The run was comfortably below the roughly 40-second threshold in the inbox.
The saved replay remains useful for deterministic demo delivery, but latency
alone does not require it.
