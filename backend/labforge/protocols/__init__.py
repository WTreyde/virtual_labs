"""Strand B: library of published lab protocols for the Protocols tab. Owner: Max.

Each protocol in library/<id>.json is paraphrased from an openly accessible source, links to it, records its licence,
and maps its steps to LabForge capabilities and catalog ids (protocol.schema.json, a Strand B draft). Nothing here
calls the network or an API.

    from labforge.protocols import load_protocols, index, for_workflow
    index()                    # light list for the tab: id, title, pipeline, capabilities, source, licence
    load_protocols()["id"]     # the full protocol
    for_workflow(workflow)     # protocols relevant to a design, ranked by how many of its step capabilities they cover

Export static files for an offline UI:  python -m labforge.protocols ../frontend/public/protocols
"""
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).parent
LIBRARY = HERE / "library"
SCHEMA = json.loads((HERE / "protocol.schema.json").read_text())


def errors(protocol: dict) -> list[str]:
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in Draft202012Validator(SCHEMA).iter_errors(protocol)]


@lru_cache
def load_protocols() -> dict[str, dict]:
    out = {}
    for path in sorted(LIBRARY.glob("*.json")):
        protocol = json.loads(path.read_text())
        errs = errors(protocol)
        if errs:
            raise ValueError(f"{path.name} breaks protocol.schema.json: {errs[:3]}")
        out[protocol["id"]] = protocol
    return out


def capabilities(protocol: dict) -> list[str]:
    caps = list(protocol.get("pipeline_steps", [])) + [s["capability"] for s in protocol["steps"] if s.get("capability")]
    return sorted(set(caps))


def index() -> list[dict]:
    """One light row per protocol, for listing and filtering in the UI."""
    return [{"id": p["id"], "title": p["title"], "domain": p["domain"], "pipeline": p["pipeline"],
             "automation_level": p.get("automation_level"), "capabilities": capabilities(p), "n_steps": len(p["steps"]),
             "catalog_ids": sorted({i for s in p["steps"] for i in s.get("catalog_ids", [])}
                                   | {e["catalog_id"] for e in p.get("equipment", []) if e.get("catalog_id")}),
             "source": p["source"], "license": p["license"], "access": p.get("access"), "confidence": p["confidence"]}
            for p in load_protocols().values()]


def for_workflow(workflow: dict) -> list[dict]:
    """Index rows for protocols sharing capabilities with the workflow's steps, most overlap first."""
    used = {s["capability"] for s in workflow.get("steps", [])}
    rows = [dict(r, matched_capabilities=sorted(used & set(r["capabilities"]))) for r in index()]
    return sorted((r for r in rows if r["matched_capabilities"]), key=lambda r: (-len(r["matched_capabilities"]), r["title"]))


def export(out_dir: str) -> None:
    """Write index.json and one <id>.json per protocol for a static, offline UI."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.json").write_text(json.dumps(index(), indent=2, ensure_ascii=False) + "\n")
    for pid, p in load_protocols().items():
        (out / f"{pid}.json").write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n")
