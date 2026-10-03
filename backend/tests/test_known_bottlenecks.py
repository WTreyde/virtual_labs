from labforge.known_bottlenecks.cases import all_cases
from labforge.known_bottlenecks.run import _use_local_catalog, check


def test_simulator_names_the_reported_bottleneck(monkeypatch):
    from labforge.catalog import store
    monkeypatch.setattr(store, "load_catalog", store.load_catalog)  # restored after the test
    _use_local_catalog()
    for case in all_cases():
        r = check(case, hours=96, replicates=4)
        assert r["match"], r
        assert abs(r["error_pct"]) < 25, r
