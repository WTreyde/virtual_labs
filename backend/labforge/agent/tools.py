"""Strand C: tools the planner agent can call. Owner: Albert.

Each entry pairs a Claude tool definition with the Python function that runs it.
Tool functions take and return plain JSON-able dicts that follow /schemas.
"""
from labforge.catalog.store import search
from labforge.agent.validation import validate_design
from labforge.contracts import validate


def _search_catalog(capability: str | None = None, labware: str | None = None, max_price_usd: float | None = None) -> dict:
    items = search(capability, labware, max_price_usd)
    return {"items": [{k: it.get(k) for k in ("id", "vendor", "model", "capabilities", "footprint", "process",
                                                 "transport", "price_usd_estimate", "data_confidence", "access_points",
                                                 "provenance", "source_urls", "safety", "integration")} for it in items]}


def _layout_and_simulate(lab_spec: dict, workflow: dict) -> dict:
    validate_design(lab_spec, workflow)
    from labforge.layout.placer import generate_layout
    from labforge.sim.simulate import simulate

    layout = generate_layout(lab_spec, workflow)
    sim = simulate(lab_spec, workflow, layout, replicates=10)
    validate(layout, "layout")
    validate(sim, "sim_result")
    return {"layout": layout, "sim_result": sim}


TOOLS = {
    "search_catalog": (
        {
            "name": "search_catalog",
            "description": "Search the cached vendor catalog for instruments and robots. Returns specs, prices and how confident the data is.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "capability": {"type": "string", "description": "A capability from schemas/common.schema.json, e.g. liquid_handling."},
                    "labware": {"type": "string"},
                    "max_price_usd": {"type": "number"},
                },
            },
        },
        _search_catalog,
    ),
    "layout_and_simulate": (
        {
            "name": "layout_and_simulate",
            "description": "Place the workflow's equipment in the room and run a Monte Carlo throughput simulation. "
                           "Returns the layout (with violations) and P10/P50/P90 throughput, utilisation and bottlenecks.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "lab_spec": {"type": "object", "description": "A LabSpec (schemas/lab_spec.schema.json)."},
                    "workflow": {"type": "object", "description": "A Workflow (schemas/workflow.schema.json)."},
                },
                "required": ["lab_spec", "workflow"],
            },
        },
        _layout_and_simulate,
    ),
    # TODO(Albert): cite_evidence (Amass), record_claim (schemas/claim.schema.json), update_spec.
}
