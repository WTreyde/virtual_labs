"""Validation: predicted lab cost with uncertainty, compared like-for-like with a published cost. Owner: Max.

Each catalog price gets a range from its provenance, or from its confidence if there is none. Prices are drawn
lognormally with the catalog value as the median and the range as P10-P90, so a long upper tail widens the band
without pulling the central estimate above the best price. Monte Carlo gives P10/P50/P90 for the cost categories
the published figure covers, deflated to the year of the published figure with a producer price index.
"""
import math
import random
import statistics

from labforge.catalog.store import get as get_item

# Multiplicative price ranges by data confidence when an item has no per-field provenance.
PRICE_BAND = {"datasheet": (0.9, 1.1), "literature": (0.8, 1.25), "estimated": (0.7, 1.4), "placeholder": (0.5, 2.0)}
ANALYTICS = {"absorbance_read", "fluorescence_read", "luminescence_read", "imaging", "hplc", "lcms", "nmr",
             "crystal_imaging", "xray_diffraction", "protein_qc", "concentration_measurement"}
# US BLS producer price index, analytical laboratory instrument manufacturing (series PCU334516334516), annual
# averages of monthly values, fetched 3 Oct 2026 from https://api.bls.gov/publicAPI/v1/timeseries/data/.
# Catalog prices are treated as PRICE_INDEX_REFERENCE_YEAR prices (most are 2022-2026 quotes; the latest full year
# of index data is 2025), so a 2007 figure is compared with catalog prices x index[2007] / index[2025].
PRICE_INDEX = {2006: 132.208, 2007: 133.142, 2008: 136.225, 2009: 137.945, 2010: 138.708, 2011: 139.625, 2012: 140.383, 2013: 142.258, 2014: 144.417, 2015: 147.0, 2016: 149.358, 2017: 153.35, 2018: 155.183, 2019: 159.258, 2020: 161.408, 2021: 164.466, 2022: 175.369, 2023: 185.836, 2024: 191.418, 2025: 196.119}
PRICE_INDEX_REFERENCE_YEAR = 2025
Z90 = 1.2816  # standard normal quantile at 0.9

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


# Reported-cost categories the model can price from the catalog. Consumables, software licences and staff are not
# modelled, so a published figure that includes them would be under-predicted; the runner flags such cases.
MODELLED_CATEGORIES = {"instruments", "robots", "analytics", "construction", "integration_labour"}


def cost_category(item: dict) -> str | None:
    """Which reported-cost category an item's purchase price belongs to; None for services, which are not capex."""
    if "external_service" in item["capabilities"]:
        return None  # e.g. synchrotron beamtime is priced per shift, not bought
    if item["category"] == "furniture":
        return "construction"  # fume hoods, cold rooms, benches are facility fit-out
    if (item.get("transport") or {}).get("kind") == "human":
        return "staff"  # operators are people, not capex; staff cost is not modelled
    if item["category"] == "transporter":
        return "robots"
    if ANALYTICS & set(item["capabilities"]):
        return "analytics"
    return "instruments"


# --- Evidence-aware price uncertainty -------------------------------------------------------------------------
# Each price gap widens that item's lognormal spread (log units, combined in quadrature with the source's own
# P10-P90 range), so confidence comes out of the predictive distribution rather than a hand-set score.
# Extra spread by source confidence. Assumption (estimated): a list price still varies a little between buyers;
# purchase records and derived figures more; placeholders a lot.
SOURCE_SIGMA = {"datasheet": 0.05, "literature": 0.10, "estimated": 0.15, "placeholder": 0.35}
# Drift of a product's price away from the lab-instrument PPI, per year between the price's source year and the
# target year. Estimated from catalog price histories: Tecan Fluent 780 2021-2026 drifted ~0.015/yr from the PPI,
# the OT-2 list price 2020-2025 ~0.18/yr (a repricing); 0.05/yr sits between. Unknown source year counts as 5 yr.
YEAR_SIGMA_PER_YEAR = 0.05
UNKNOWN_YEAR_GAP = 5
# Using a priced model in place of the one actually bought (e.g. Tecan Fluent for a Freedom EVO). Estimated from
# the spread within one product family in the catalog: Fluent 480 vs 780 differ by ln(316k/210k) ~ 0.41, ~0.32 as
# a P10-P90 sigma.
PROXY_MODEL_SIGMA = 0.32
# Configurable systems (liquid handlers, LC-MS, bioreactors, chromatography, synthesis platforms, imagers, acoustic
# dispensers, compound stores) vary a lot with options. Estimated from configured-price ranges within one product
# family in the catalog: Fluent 480-1080 ln(500k/209k)=0.87, Biomek i7 0.74, OT-2 workstations 0.69, ÄKTA 0.93,
# Opentrons Flex 0.74 -> typical ~0.8 between low and high, i.e. ~0.31 as a P10-P90 sigma. Applied as a floor on
# the item's own range (not for bare-unit prices), so a price that already carries a wide range is not widened twice.
CONFIGURABLE_CAPABILITIES = {"liquid_handling", "lcms", "hplc", "bioreactor", "protein_purification", "reaction",
                             "crystal_imaging", "acoustic_dispensing", "compound_storage", "powder_dosing"}
CONFIG_SIGMA = 0.31
# A grant award is not an invoice: it may bundle accessories, service or a workstation, or be capped. Estimated from
# five award-vs-purchase pairs for the same instrument in the catalog notes (Echo 650 S10s at Yale and Rutgers vs a
# federal purchase: ln ratio ~0.0; Echo S10s with an Access workstation at Wistar and Northwestern: ~0.4; Hamilton
# STAR S10 at Thomas Jefferson vs federal purchases: -0.06): RMS 0.25 (mean +0.15, not applied as a shift).
GRANT_SIGMA = 0.25
CONFIDENCE_TOLERANCE = 1.25  # "confidence" = chance the true cost is within x/÷ 1.25 of our P50
EVIDENCE_WEIGHT = {"datasheet": 1.0, "literature": 0.9, "estimated": 0.7, "placeholder": 0.3}


def basis_mismatch_sigma() -> float:
    """Spread to add when the requested basis (base/configured) has no price and the default must stand in.
    Learned from the catalog: half the RMS log ratio of configured to base price over items that have both."""
    from labforge.catalog.store import load_catalog
    logs = []
    for item in load_catalog().values():
        prov = item.get("provenance", {})
        b, c = prov.get("price_usd_estimate.base"), prov.get("price_usd_estimate.configured")
        if b and c and b["value"] > 0 and c["value"] > 0:
            logs.append(math.log(c["value"] / b["value"]))
    return math.sqrt(sum(x * x for x in logs) / len(logs)) / 2 if logs else 0.3


def select_price(item: dict, basis: str | None = None, year: int | None = None) -> tuple[dict | None, bool]:
    """The price entry to use and whether it matches the requested basis. Among entries for the basis (including
    dated history such as price_usd_estimate.base.2020) the one whose source year is closest to `year` wins."""
    prov = item.get("provenance", {})
    if basis:
        cands = [e for k, e in prov.items() if k == f"price_usd_estimate.{basis}" or k.startswith(f"price_usd_estimate.{basis}.")]
        if cands:
            target = year or PRICE_INDEX_REFERENCE_YEAR
            return min(cands, key=lambda e: (abs(e.get("year", target) - target), -e.get("year", 0))), True
    entry = prov.get("price_usd_estimate")
    if entry is None and item.get("price_usd_estimate") is not None:
        entry = {"value": item["price_usd_estimate"], "confidence": item.get("data_confidence", "estimated")}
    return entry, basis is None


def price_range(item: dict, basis: str | None = None, year: int | None = None) -> tuple[float, float, float]:
    """(low, value, high) of the selected price entry, in its own source year's dollars."""
    entry, _ = select_price(item, basis, year)
    if entry is None:
        return 0.0, 0.0, 0.0
    v = entry["value"]
    if entry.get("high", 0) > entry.get("low", 0):
        return entry["low"], v, entry["high"]
    lo, hi = PRICE_BAND[entry.get("confidence") or item.get("data_confidence", "estimated")]
    return v * lo, v, v * hi


def item_evidence(item: dict, basis: str | None, year: int | None, match: str = "exact") -> dict:
    """Price, total spread and the evidence behind it for one item, adjusted to `year` (today's prices if None)."""
    entry, basis_ok = select_price(item, basis, year)
    if entry is None:
        return {"catalog_id": item["id"], "priced": False}
    lo, v, hi = price_range(item, basis, year)
    target = year or PRICE_INDEX_REFERENCE_YEAR
    src_year = entry.get("year")
    gap = abs(target - src_year) if src_year else UNKNOWN_YEAR_GAP
    conf = entry.get("confidence") or item.get("data_confidence", "estimated")
    rng_sigma = math.log(hi / lo) / (2 * Z90) if lo > 0 and hi > lo else 0.0
    configurable = basis != "base" and bool(CONFIGURABLE_CAPABILITIES & set(item["capabilities"]))
    parts = {
        "range": rng_sigma,
        "configuration": math.sqrt(max(0.0, CONFIG_SIGMA ** 2 - rng_sigma ** 2)) if configurable else 0.0,
        "source": SOURCE_SIGMA.get(conf, 0.15),
        "year_gap": YEAR_SIGMA_PER_YEAR * gap,
        "basis_mismatch": 0.0 if basis_ok else basis_mismatch_sigma(),
        "proxy_model": PROXY_MODEL_SIGMA if match == "proxy" else 0.0,
    }
    sigma = math.sqrt(sum(x * x for x in parts.values()))
    factor = PRICE_INDEX[min(target, PRICE_INDEX_REFERENCE_YEAR)] / PRICE_INDEX[min(src_year or PRICE_INDEX_REFERENCE_YEAR, PRICE_INDEX_REFERENCE_YEAR)]
    score = EVIDENCE_WEIGHT.get(conf, 0.7) * (1.0 if basis_ok else 0.6) * math.exp(-gap / 10) * (0.6 if match == "proxy" else 1.0)
    return {"catalog_id": item["id"], "priced": True, "median_usd": round(v * factor), "sigma": round(sigma, 3),
            "sigma_parts": {k: round(x, 3) for k, x in parts.items()}, "confidence": conf, "source": entry.get("source"),
            "source_year": src_year, "target_year": target, "year_gap": gap, "basis_requested": basis,
            "basis_matched": basis_ok, "model_match": match, "evidence_score": round(score, 2)}


def year_factor(year: int | None) -> float:
    """Multiplier that turns reference-year prices into prices of `year`; 1.0 if unknown."""
    if year is None or year not in PRICE_INDEX:
        return 1.0
    return PRICE_INDEX[year] / PRICE_INDEX[PRICE_INDEX_REFERENCE_YEAR]


def predicted_cost(workflow: dict, includes: list[str], samples: int = 2000, seed: int = 0,
                   build: str = "turnkey", year: int | None = None, basis: str | None = None,
                   figure_type: str | None = None) -> dict:
    """P10/P50/P90 cost of the workflow's equipment in the given categories, in `year` dollars (today's if None),
    with a confidence block. Each item is drawn lognormally around its selected price adjusted from its own source
    year; its spread grows with every evidence gap (see item_evidence). Workflow equipment may mark
    "match": "proxy" when the catalog model stands in for the one actually used. figure_type "grant_award" predicts
    a grant amount rather than a purchase price, adding GRANT_SIGMA of noise for unknown contents."""
    rng = random.Random(seed)
    entries = [(get_item(e["catalog_id"]), e.get("match", "exact")) for e in workflow["equipment"]]
    entries = [(it, m) for it, m in entries if cost_category(it) in includes]
    ev = [item_evidence(it, basis, year, m) for it, m in entries]
    priced = [e for e in ev if e["priced"]]
    draws = {i: [] for i in range(len(priced))}
    totals = []
    for _ in range(samples):
        hw = 0.0
        for i, e in enumerate(priced):
            x = e["median_usd"] * math.exp(rng.gauss(0, e["sigma"]))
            draws[i].append(x)
            hw += x
        if "integration_labour" in includes:
            lo, mode, hi = INTEGRATION_FRACTION[build]
            hw *= 1 + rng.triangular(lo, hi, mode)
        if figure_type == "grant_award":
            hw *= math.exp(rng.gauss(0, GRANT_SIGMA))
        totals.append(hw)
    if not priced:
        # Nothing in the requested categories can be priced: say so instead of predicting $0 with full confidence.
        return {"p10": None, "p50": None, "p90": None, "n_items": len(entries), "price_year_factor": round(year_factor(year), 3),
                "confidence": {"within_25pct": None, "label": "none", "data_coverage": 0.0,
                               "unpriced_items": [e["catalog_id"] for e in ev], "drivers": [], "figure_noise": 0.0},
                "items": ev, "not_costable": "no priced equipment in the reported cost categories"}
    q = statistics.quantiles(totals, n=10, method="inclusive")
    p50 = statistics.median(totals)
    within = sum(p50 / CONFIDENCE_TOLERANCE <= t <= p50 * CONFIDENCE_TOLERANCE for t in totals) / samples
    var = [statistics.pvariance(draws[i]) for i in draws]
    value = sum(e["median_usd"] for e in priced) or 1
    coverage = sum(e["median_usd"] * e["evidence_score"] for e in priced) / value
    unpriced = [e["catalog_id"] for e in ev if not e["priced"]]
    label = "low" if unpriced or within < 0.4 else "medium" if within < 0.7 else "high"
    drivers = sorted(({"catalog_id": e["catalog_id"], "variance_share": round(v / sum(var), 2) if sum(var) else 0.0,
                       "main_gap": max(e["sigma_parts"], key=e["sigma_parts"].get)} for e, v in zip(priced, var)),
                     key=lambda d: -d["variance_share"])[:3]
    return {"p10": round(q[0]), "p50": round(p50), "p90": round(q[-1]), "n_items": len(entries),
            "price_year_factor": round(year_factor(year), 3),
            "confidence": {"within_25pct": round(within, 2), "label": label, "data_coverage": round(coverage, 2),
                           "unpriced_items": unpriced, "drivers": drivers,
                           "figure_noise": GRANT_SIGMA if figure_type == "grant_award" else 0.0},
            "items": ev}


def bom_estimate(workflow: dict, year: int | None = None, basis: str | None = "configured",
                 includes: tuple[str, ...] = ("instruments", "robots", "analytics", "construction")) -> dict:
    """Equipment cost of a designed lab with a confidence block, for the agent report, verifier and UI.
    Defaults to configured prices (a lab buys working systems) in today's dollars; services are excluded."""
    return predicted_cost(workflow, list(includes), year=year, basis=basis)


def compare(reported_usd: float, predicted: dict) -> dict:
    return {
        "reported_usd": reported_usd,
        "predicted": predicted,
        "within_p10_p90": predicted["p10"] <= reported_usd <= predicted["p90"],
        "log10_error": round(math.log10(predicted["p50"] / reported_usd), 3) if reported_usd and predicted["p50"] else None,
    }
