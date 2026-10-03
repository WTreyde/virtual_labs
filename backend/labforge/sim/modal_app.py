"""Strand D: Modal app that runs simulation replicates and bench tasks in parallel. Owner: Maxim.

Deploy once:   cd backend && modal deploy labforge/sim/modal_app.py
Then:          LABFORGE_SIM_BACKEND=modal make backend   (or simulate(..., backend="modal"))
"""
from pathlib import Path

import modal

APP_NAME = "labforge-sim"
REPO_ROOT = Path(__file__).resolve().parents[3]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("simpy>=4.1", "jsonschema>=4.21", "referencing")
    # Package with its data files (catalog JSON, safety rules); contracts.py finds schemas at /schemas.
    .add_local_python_source("labforge", ignore=["**/__pycache__/**"])
    .add_local_dir(REPO_ROOT / "schemas", "/schemas")
)
app = modal.App(APP_NAME, image=image)


@app.function(cpu=1.0, timeout=900, max_containers=200)
def replicate(job: dict) -> dict:
    from labforge.sim.simulate import run_replicate
    return run_replicate(**job)


@app.local_entrypoint()
def smoke(replicates: int = 50):
    """modal run labforge/sim/modal_app.py : simulate the worked example with replicates on Modal."""
    from labforge.contracts import load_example
    from labforge.layout.placer import generate_layout
    from labforge.sim.simulate import simulate
    spec, wf = load_example("lab_spec"), load_example("workflow")
    out = simulate(spec, wf, generate_layout(spec, wf), replicates=replicates, backend="modal")
    print(out["throughput"], out["sensitivity"])
