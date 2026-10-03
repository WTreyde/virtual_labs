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
# Systems integration (scheduler software, fixtures, enclosures, installation, commissioning, validation) as a
# fraction of hardware, as (low, mode, high) for a triangular draw. Confidence: estimated. No peer-reviewed ratio
# was found (3 Oct 2026); these rest on trade-press rules of thumb, so treat them as the biggest unknown:
# - "integration, support contracts, consulting, and the scientist time ... often cost as much again" as the
#   hardware (https://www.robotonrails.com/pages/guides/how-much-does-lab-automation-cost.html; includes support,
#   so an upper-side figure);
# - itemised one-off costs (facility $5-50k, software $10-100k, GLP/GMP validation $20-100k) on a $150-500k
#   mid-range system, i.e. ~0.1-0.5x (https://www.roboticscenter.ai/guides/what-is-lab-automation);
# - industrial robot cells: "total installed cost running 2x to 5x the hardware price"
#   (https://www.industrialroboticshub.com/articles/true-cost-of-an-industrial-robot/), heavier than lab cells.
# Self-built academic labs pay little cash for integration (open-source software, printed fixtures, unpriced
# student time), so their range is lower; RoboChem-Flex (~US$5k) shows how far in-house builds cut cost.
INTEGRATION_FRACTION = {
    "turnkey": (0.3, 0.6, 1.5),
    "self_built": (0.1, 0.3, 1.0),
}


def cost_category(item: dict) -> str | None:
    """Which reported-cost category an item's purchase price belongs to; None for services, which are not capex."""
    if "external_service" in item["capabilities"]:
        return None  # e.g. synchrotron beamtime is priced per shift, not bought
    if item["category"] == "furniture":
        return "construction"  # fume hoods, cold rooms, benches are facility fit-out
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


def predicted_cost(workflow: dict, includes: list[str], samples: int = 2000, seed: int = 0,
                   build: str = "turnkey") -> dict:
    """P10/P50/P90 cost of the workflow's equipment in the given categories. `build` picks the integration
    range ("turnkey" vendor workcell or "self_built" academic lab); it only matters if integration_labour is included."""
    rng = random.Random(seed)
    items = [get_item(e["catalog_id"]) for e in workflow["equipment"]]
    items = [it for it in items if cost_category(it) in includes]
    totals = []
    for _ in range(samples):
        hw = sum(rng.triangular(lo, hi, mode) for lo, mode, hi in map(price_range, items))
        if "integration_labour" in includes:
            lo, mode, hi = INTEGRATION_FRACTION[build]
            hw *= 1 + rng.triangular(lo, hi, mode)
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
