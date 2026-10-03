"""Validation: predicted lab cost with uncertainty, compared like-for-like with a published cost. Owner: Max.

Each catalog price gets a range from its provenance, or from its confidence if there is none.
Monte Carlo over those ranges gives P10/P50/P90 for the cost categories the published figure covers.
"""
import random
import statistics

from labforge.catalog.store import get as get_item

# Multiplicative price ranges by data confidence when an item has no per-field provenance.
PRICE_BAND = {"datasheet": (0.9, 1.1), "literature": (0.8, 1.25), "estimated": (0.7, 1.4), "placeholder": (0.5, 2.0)}
ANALYTICS = {"absorbance_read", "fluorescence_read", "luminescence_read", "imaging", "hplc", "lcms", "nmr",
             "crystal_imaging", "xray_diffraction", "protein_qc", "concentration_measurement"}
# Systems integration (software, fixtures, commissioning) as a fraction of hardware. Placeholder:
# TODO(Max): replace with a sourced range; it is the biggest unknown in turnkey quotes.
INTEGRATION_FRACTION = (0.2, 1.0)


def cost_category(item: dict) -> str:
    if item["category"] == "transporter":
        return "robots"
    if ANALYTICS & set(item["capabilities"]):
        return "analytics"
    return "instruments"


def price_range(item: dict) -> tuple[float, float, float]:
    p = item.get("price_usd_estimate", 0.0)
    prov = item.get("provenance", {}).get("price_usd_estimate")
    if prov and "low" in prov and "high" in prov:
        return prov["low"], prov.get("value", p), prov["high"]
    lo, hi = PRICE_BAND[item.get("data_confidence", "estimated")]
    return p * lo, p, p * hi


def predicted_cost(workflow: dict, includes: list[str], samples: int = 2000, seed: int = 0) -> dict:
    rng = random.Random(seed)
    items = [get_item(e["catalog_id"]) for e in workflow["equipment"]]
    items = [it for it in items if cost_category(it) in includes]
    totals = []
    for _ in range(samples):
        hw = sum(rng.triangular(lo, hi, mode) for lo, mode, hi in map(price_range, items))
        if "integration_labour" in includes:
            hw *= 1 + rng.uniform(*INTEGRATION_FRACTION)
        totals.append(hw)
    q = statistics.quantiles(totals, n=10, method="inclusive")
    return {"p10": round(q[0]), "p50": round(statistics.median(totals)), "p90": round(q[-1]), "n_items": len(items)}


def compare(reported_usd: float, predicted: dict) -> dict:
    import math
    return {
        "reported_usd": reported_usd,
        "predicted": predicted,
        "within_p10_p90": predicted["p10"] <= reported_usd <= predicted["p90"],
        "log10_error": round(math.log10(predicted["p50"] / reported_usd), 3) if reported_usd and predicted["p50"] else None,
    }
