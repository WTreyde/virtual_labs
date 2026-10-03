"""Strand B: equipment catalog. Owner: Max.

The cached catalog lives in data/catalog.json (a list of CatalogItem). scrape.py fills it once;
everything else only reads it.
"""
import json
from functools import lru_cache
from pathlib import Path

from labforge.contracts import validate

CATALOG_PATH = Path(__file__).parent / "data" / "catalog.json"


@lru_cache
def load_catalog() -> dict[str, dict]:
    items = json.loads(CATALOG_PATH.read_text())
    return {item["id"]: validate(item, "catalog_item") for item in items}


def get(item_id: str) -> dict:
    return load_catalog()[item_id]


def search(capability: str | None = None, labware: str | None = None, max_price_usd: float | None = None,
           include_people: bool = False) -> list[dict]:
    """Filter the catalog. Exposed to the agent as the `search_catalog` tool and at GET /catalog.
    Human operator entries (transport.kind "human") are left out unless include_people is set: people are staffed
    through LabSpec.operators, and a capability search must not offer a person as an instrument."""
    out = []
    for item in load_catalog().values():
        if not include_people and (item.get("transport") or {}).get("kind") == "human":
            continue
        if capability and capability not in item["capabilities"]:
            continue
        if labware and not any(labware in ap.get("labware", [labware]) for ap in item["access_points"]):
            continue
        if max_price_usd is not None and item.get("price_usd_estimate", 0) > max_price_usd:
            continue
        out.append(item)
    return out
