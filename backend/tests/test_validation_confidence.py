"""Strand B: cost predictions carry a confidence that reflects the evidence behind each price."""
from labforge.catalog.store import get
from labforge.contracts import load_example
from labforge.validation.cost import bom_estimate, item_evidence, select_price
from labforge.validation.runner import calibration, load_cases, run_case


def test_bom_estimate_has_band_and_confidence():
    out = bom_estimate(load_example("workflow"))
    assert out["p10"] < out["p50"] < out["p90"]
    c = out["confidence"]
    assert 0 <= c["within_25pct"] <= 1 and 0 <= c["data_coverage"] <= 1
    assert c["label"] in ("low", "medium", "high") and c["drivers"]


def test_each_evidence_gap_widens_the_spread():
    ot2 = get("opentrons_ot2")
    exact = item_evidence(ot2, "base", 2025)
    assert exact["basis_matched"] and exact["year_gap"] == 0
    assert item_evidence(ot2, "base", 2025, match="proxy")["sigma"] > exact["sigma"]
    assert item_evidence(get("formulatrix_rock_imager_1000"), "configured", 2023)["sigma_parts"]["year_gap"] > 0
    assert not item_evidence(get("formulatrix_rock_imager_1000"), "base", 2023)["basis_matched"]  # quote-only: no base price


def test_dated_price_history_picks_the_closest_year():
    entry, matched = select_price(get("opentrons_ot2"), "base", 2020)
    assert matched and entry["year"] == 2020 and entry["value"] == 5000


def test_calibration_reports_brier_against_a_baseline(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # cases without a workflow would otherwise call the live planner
    monkeypatch.setenv("LABFORGE_ENV_FILE", "/missing/test/.env")
    cal = calibration([run_case(c) for c in load_cases()])
    assert cal["n"] >= 1 and "brier" in cal and "brier_constant_baseline" in cal
