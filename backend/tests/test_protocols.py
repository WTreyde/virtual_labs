"""Strand B: the protocol library loads, validates and links to designs."""
from labforge.contracts import load_example
from labforge.protocols import for_workflow, index, load_protocols


def test_library_loads_and_validates():
    protocols = load_protocols()
    assert len(protocols) >= 20
    for p in protocols.values():
        assert p["source"]["url"].startswith("http") and p["license"]


def test_index_and_workflow_matching():
    rows = index()
    assert {r["pipeline"] for r in rows} >= {"chem_library", "xchem"}
    matched = for_workflow(load_example("workflow"))
    assert matched and all(r["matched_capabilities"] for r in matched)
