"""Strand D: where Monte Carlo replicates run. Owner: Maxim.

Every job is the keyword arguments of `run_replicate` (plain JSON), so jobs run the same way in
this process, in local worker processes, or on Modal. Pick with `backend=` or the
LABFORGE_SIM_BACKEND environment variable: "serial" (default), "process" or "modal".
If Modal is not installed or not authenticated, it falls back to local processes and says so.
"""
import logging
import os
from concurrent.futures import ProcessPoolExecutor

log = logging.getLogger(__name__)
MIN_JOBS_FOR_POOL = 24  # below this, process start-up costs more than it saves


def _run(job: dict) -> dict:
    from labforge.sim.simulate import run_replicate
    return run_replicate(**job)


def map_replicates(jobs: list[dict], backend: str | None = None) -> list[dict]:
    backend = backend or os.environ.get("LABFORGE_SIM_BACKEND", "serial")
    if backend == "modal":
        try:
            return run_on_modal(jobs)
        except Exception as e:  # no token, no network, modal not installed: the demo must still run
            log.warning("Modal unavailable (%s); running replicates on local processes.", e)
            backend = "process"
    if backend == "process" and len(jobs) >= MIN_JOBS_FOR_POOL:
        with ProcessPoolExecutor(max_workers=min(len(jobs), os.cpu_count() or 2)) as pool:
            return list(pool.map(_run, jobs, chunksize=max(1, len(jobs) // (4 * (os.cpu_count() or 2)))))
    return [_run(j) for j in jobs]


def run_on_modal(jobs: list[dict]) -> list[dict]:
    """Fan jobs out to the deployed `labforge-sim` app, or to an ephemeral run of it if it is not deployed."""
    import modal

    from labforge.sim.modal_app import APP_NAME, app, replicate
    try:
        fn = modal.Function.from_name(APP_NAME, "replicate")
        return list(fn.map(jobs))
    except modal.exception.NotFoundError:
        with app.run():
            return list(replicate.map(jobs))
