"""Strand B: one-off vendor scrape into data/catalog.json. Owner: Max.

Plan (run once, then commit the cached JSON so nobody depends on the network at demo time):
1. VENDOR_PAGES lists product pages for every instrument in docs/pipelines.md.
2. A Modal function fetches each page in parallel and asks Claude to fill a CatalogItem,
   recording every number's source and confidence under `provenance`.
3. Results are validated with labforge.contracts.validate(item, "catalog_item") and merged.

Run:  modal run labforge/catalog/scrape.py   (needs `pip install -e .[modal]` and ANTHROPIC_API_KEY)
"""
VENDOR_PAGES: dict[str, str] = {
    # "opentrons_flex": "https://opentrons.com/products/flex",
    # TODO(Max): add ~60 instruments covering both pipelines.
}


def extract_item(item_id: str, url: str) -> dict:
    """TODO(Max): fetch `url`, prompt Claude with catalog_item.schema.json, return a CatalogItem."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit("Not implemented yet: see module docstring.")
