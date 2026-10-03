"""Strand B: the one-off vendor scrape, run on Modal. Owner: Max.

Each item in scrape.VENDOR_PAGES becomes one Modal call. Inside it, Claude reads the product page and
datasheets with the server-side web_fetch / web_search tools and submits a CatalogItem through a tool whose
input schema is catalog_item.schema.json; schema errors go back to Claude to fix. Locally, every result is
validated with labforge.contracts, gets its sourced price from scrape.PRICE_REFERENCES, and is merged into
data/catalog.json. Raw results are kept in data/scraped/<id>.json for audit.

Run from backend/:
    modal run labforge/catalog/scrape_modal.py                          # every item not yet in catalog.json
    modal run labforge/catalog/scrape_modal.py --only genevac_ez2,ur5e  # just these
    modal run labforge/catalog/scrape_modal.py --only ur5e --overwrite  # replace an existing entry
Hand-tuned entries already in catalog.json are kept unless --overwrite is given (tests depend on them).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import modal

from labforge.catalog.scrape import CAPABILITY_HINTS, PRICE_REFERENCES, VENDOR_PAGES, apply_price_reference

MODEL = "claude-opus-5-5"
DATA_DIR = Path(__file__).parent / "data"
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

# USD per million tokens (claude-opus-5-5) and per web search, for the cost printout only.
PRICE_IN, PRICE_OUT, PRICE_CACHE_READ, PRICE_CACHE_WRITE, PRICE_SEARCH = 4.0, 20.0, 0.20, 5.0, 0.01

SYSTEM = """You extract specs of one commercial lab instrument into a CatalogItem for a lab-design simulator.

Research: use web_fetch on the product page you are given, then web_search / web_fetch for the datasheet,
brochure or manual (PDFs are best) to find dimensions, weight, throughput, capacity, power and interfaces.

Rules for numbers (this project is judged on knowing what it does not know):
- Every number you put in the item (footprint, durations, capacity, speeds, reach, power, lead time) gets an
  entry in `provenance`, keyed by its JSON path (e.g. "footprint.width_m", "process.durations_s.lcms"), with
  value, low, high, confidence and source (the URL it came from, or "agent_estimate").
- confidence: "datasheet" = stated by the vendor for this model; "literature" = paper or application note;
  "estimated" = derived from related figures (say how in the source string after the URL, e.g.
  "https://... ; 2.5 min/sample x 96"); "placeholder" = no evidence, a rough guess with a wide range.
- Never present a guess as a datasheet value. If you could not find something, use "placeholder".
- Do not set price_usd_estimate; prices are handled separately.

Conventions:
- Metres and seconds. footprint is the bounding box including doors/lids closed; width along local x,
  depth along local y. clearance_m is service space needed around it. mount: floor, bench, ceiling or rail.
- access_points: where labware enters/leaves, in the item's local frame, origin at the footprint centre,
  metres, z up from the mounting surface. Name them (e.g. "plate_nest", "front_door", "deck"). List the
  labware each accepts, using only the labware enum.
- process.durations_s: typical time per labware unit for each capability (e.g. one 96-well plate for a
  reader, one sample x 96 for LC-MS, one run for a batch device), keyed by capability. process.capacity is
  labware units processed at once. For storage, set storage_slots.
- Transporters: transport.kind (arm, rail, mobile), reach_m (arms), speed_m_s, pick_place_s, payload_kg.
- integration: control interfaces actually supported (SiLA 2, OPC-UA, vendor SDK/API name, RS-232, ...).
- safety.hazards uses: flammable_solvents, toxic_reagents, cryogens, biohazard, high_voltage, moving_parts,
  laser, heavy. safety.requires_zone uses: fume_hood, ventilated, cryogen, bsl2, cold_room, vibration_free.
  Set needs_light_curtain / collaborative for robots.
- External services (e.g. a synchrotron beamline): category "instrument", a small placeholder footprint for
  the local dry-shipper drop-off point, and durations_s for the turnaround time.
- source_urls: every URL you used. data_confidence: your overall confidence in the item.

Finish by calling submit_catalog_item exactly once with the complete item. If it returns errors, fix them
and call it again."""


def inline_schema() -> dict:
    """catalog_item.schema.json with every $ref to common.schema.json inlined (tool schemas must stand alone)."""
    from labforge.contracts import _registry

    schemas = _registry()[1]
    defs = schemas["common.schema.json"]["$defs"]

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if ref:
                name = ref.split("/")[-1]
                return resolve(defs[name]) | {k: resolve(v) for k, v in node.items() if k != "$ref"}
            return {k: resolve(v) for k, v in node.items() if k not in ("$schema", "$id")}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schemas["catalog_item.schema.json"])


def _read_api_key() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    for line in ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []:
        key, _, value = line.partition("=")
        if key.strip() == "ANTHROPIC_API_KEY":
            return value.strip().strip("'\"")
    return ""


app = modal.App("labforge-catalog-scrape")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("anthropic>=1.11", "jsonschema>=4.21")
    .add_local_python_source("labforge")
)
# Only the Anthropic key is sent to Modal, read from the local .env at launch.
secrets = [modal.Secret.from_dict({"ANTHROPIC_API_KEY": _read_api_key()})] if modal.is_local() else []


@app.function(image=image, secrets=secrets, timeout=900, max_containers=8, retries=1)
def extract(item_id: str, url: str, hint: tuple[str, list[str]], price_note: str, schema: dict, max_turns: int = 10) -> dict:
    import anthropic
    from jsonschema import Draft202012Validator

    client = anthropic.Anthropic(max_retries=5)
    validator = Draft202012Validator(schema)
    category, capabilities = hint
    tools = [
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 10},
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 6},
        {
            "name": "submit_catalog_item",
            "description": "Submit the finished CatalogItem. Returns schema errors to fix, or 'accepted'.",
            "input_schema": schema,
        },
    ]
    prompt = (
        f"Item id: {item_id}\nProduct page: {url}\nWhat we know: {price_note}\n"
        f"Required: category \"{category}\" and capabilities including {capabilities}.\n"
        "Research it and submit the CatalogItem with this exact id."
    )
    messages = [{"role": "user", "content": prompt}]
    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "searches": 0, "fetches": 0}

    for _ in range(max_turns):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            tools=tools,
            messages=messages,
        )
        u = response.usage
        usage["input"] += u.input_tokens
        usage["output"] += u.output_tokens
        usage["cache_read"] += u.cache_read_input_tokens or 0
        usage["cache_write"] += u.cache_creation_input_tokens or 0
        if u.server_tool_use:
            usage["searches"] += u.server_tool_use.web_search_requests or 0
            usage["fetches"] += getattr(u.server_tool_use, "web_fetch_requests", 0) or 0
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            return {"id": item_id, "item": None, "error": "refused", "usage": usage}
        if response.stop_reason == "pause_turn":
            continue  # server-side tool loop hit its limit; resend and it resumes
        submits = [b for b in response.content if b.type == "tool_use" and b.name == "submit_catalog_item"]
        if not submits:
            messages.append({"role": "user", "content": "Call submit_catalog_item now with the complete item."})
            continue
        results, accepted = [], None
        for block in submits:
            item = block.input
            errs = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in validator.iter_errors(item)]
            if item.get("id") != item_id:
                errs.append(f"id must be {item_id!r}")
            missing = set(capabilities) - set(item.get("capabilities", []))
            if missing:
                errs.append(f"capabilities must include {sorted(missing)}")
            if errs:
                results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": "\n".join(errs[:20])})
            else:
                accepted = item
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": "accepted"})
        if accepted:
            return {"id": item_id, "item": accepted, "error": None, "usage": usage}
        messages.append({"role": "user", "content": results})

    return {"id": item_id, "item": None, "error": f"no valid item after {max_turns} turns", "usage": usage}


def cost_usd(usage: dict) -> float:
    return (usage["input"] * PRICE_IN + usage["output"] * PRICE_OUT + usage["cache_read"] * PRICE_CACHE_READ
            + usage["cache_write"] * PRICE_CACHE_WRITE) / 1e6 + usage["searches"] * PRICE_SEARCH


@app.local_entrypoint()
def main(only: str = "", overwrite: bool = False):
    from labforge.contracts import validate

    catalog_path = DATA_DIR / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    existing = {item["id"] for item in catalog}
    ids = [i.strip() for i in only.split(",") if i.strip()] or list(VENDOR_PAGES)
    unknown = [i for i in ids if i not in VENDOR_PAGES]
    if unknown:
        raise SystemExit(f"Not in VENDOR_PAGES: {unknown}")
    if not overwrite:
        ids = [i for i in ids if i not in existing]
    if not ids:
        raise SystemExit("Nothing to scrape (all requested items are already in catalog.json; use --overwrite).")
    if not _read_api_key():
        raise SystemExit(f"ANTHROPIC_API_KEY not found in the environment or {ENV_FILE}")

    schema = inline_schema()
    args = [(i, VENDOR_PAGES[i], CAPABILITY_HINTS[i], PRICE_REFERENCES[i]["note"], schema) for i in ids]
    print(f"Scraping {len(ids)} items on Modal ...")

    scraped_dir = DATA_DIR / "scraped"
    scraped_dir.mkdir(exist_ok=True)
    by_id = {item["id"]: item for item in catalog}
    total, failed = 0.0, []
    for result in extract.starmap(args, return_exceptions=True):
        if isinstance(result, Exception):
            failed.append(f"? {result!r}")
            continue
        item_id, usage = result["id"], result["usage"]
        total += cost_usd(usage)
        if result["item"] is None:
            failed.append(f"{item_id}: {result['error']}")
            continue
        item = result["item"]
        item["category"] = CAPABILITY_HINTS[item_id][0]
        item["scraped_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        apply_price_reference(item)
        try:
            validate(item, "catalog_item")
        except ValueError as e:
            failed.append(f"{item_id}: {e}")
            continue
        (scraped_dir / f"{item_id}.json").write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n")
        by_id[item_id] = item
        print(f"  ok  {item_id:30s} ${cost_usd(usage):.2f}  {usage['searches']} searches")

    order = [i["id"] for i in catalog] + [i for i in VENDOR_PAGES if i not in existing]
    merged = [by_id[i] for i in order if i in by_id]
    catalog_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    print(f"\ncatalog.json now has {len(merged)} items. Estimated Claude cost this run: ${total:.2f}")
    if failed:
        print("Failed:\n  " + "\n  ".join(failed))
