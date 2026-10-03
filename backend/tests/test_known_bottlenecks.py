from labforge.catalog import store
from labforge.known_bottlenecks.cases import all_cases
from labforge.known_bottlenecks.run import _use_local_catalog, check
from labforge.sim import simulate as sim_mod


def test_simulator_names_the_reported_bottleneck(monkeypatch):
    # Record the originals so monkeypatch restores them and the local catalog doesn't leak into other tests.
    monkeypatch.setattr(store, "load_catalog", store.load_catalog)
    monkeypatch.setattr(sim_mod, "load_catalog", getattr(sim_mod, "load_catalog", None), raising=False)
    monkeypatch.setenv("LABFORGE_SIM_BACKEND", "serial")
    _use_local_catalog()
    for case in all_cases():
        r = check(case, hours=96, replicates=4)
        assert r["match"], r
        if "throughput_observed_range" in r:  # the paper gives a range, so require overlap instead
            assert r["observed_in_band"], r
        else:
            assert abs(r["error_pct"]) < 25, r
