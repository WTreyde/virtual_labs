"""Strand D: zone needs come from what equipment is and does in this brief; walkways reach every work spot."""
from labforge.layout.placer import generate_layout, resolve_items
from labforge.layout.safety import choose_kinds, derive_zones, load_rules, zone_needs
from labforge.layout.validate import walkway_unreachable


def _spec(hazards=(), bsl=None, room=(10, 8)):
    c = {"hazards": list(hazards)}
    if bsl:
        c["biosafety_level"] = bsl
    return {"id": "s", "name": "s", "domain": "chemistry", "description": "s", "constraints": c,
            "throughput_target": {"value": 10, "unit": "plates_per_day"},
            "room": {"width_m": room[0], "depth_m": room[1], "doors": [{"x": 0, "y": room[1] / 2}]}}


def _wf(equipment, steps=()):
    return {"id": "w", "lab_spec_id": "s", "equipment": [{"instance_id": i, "catalog_id": c} for i, c in equipment.items()],
            "steps": list(steps) or [{"id": "x", "name": "x", "capability": "manual_bench", "candidate_instances": [],
                                      "duration_s": 60, "mode": "in_silico"}]}


def test_containment_equipment_does_not_need_a_zone_around_itself():
    wf = _wf({"hood_1": "labconco_fume_hood", "glovebox_1": "mbraun_glovebox", "swing_1": "chemspeed_swing_xl"})
    needs = zone_needs(_spec(["toxic_reagents", "flammable_solvents"]), wf, resolve_items(wf), load_rules())
    assert "hood_1" not in needs and "glovebox_1" not in needs
    assert any("fume_hood" in ok for ok, _ in needs["swing_1"])  # inert inside, but it still needs a hood


def test_usage_hazards_only_count_when_the_brief_has_them():
    wf = _wf({"lh_1": "hamilton_microlab_star"})
    chem = zone_needs(_spec(["flammable_solvents"]), wf, resolve_items(wf), load_rules())
    assert not any("bsl2" in ok for ok, _ in chem.get("lh_1", []))  # no biohazard in a chemistry brief
    bio = zone_needs(_spec(bsl=2), wf, resolve_items(wf), load_rules())
    assert any("bsl2" in ok for ok, _ in bio["lh_1"])


def test_conflicting_needs_get_overlapping_zones_of_each_kind():
    assert sorted(choose_kinds([{"fume_hood"}, {"fume_hood", "ventilated"}, {"cryogen"}])) == ["cryogen", "fume_hood"]
    wf = _wf({"lh_1": "opentrons_flex"})
    pl = {"lh_1": {"instance_id": "lh_1", "position": {"x": 2, "y": 2, "z": 0.9}, "rotation_deg": 0}}
    zones = derive_zones(pl, resolve_items(wf), {"lh_1": ["fume_hood", "cryogen"]}, 10, 8)
    assert sorted(z["kind"] for z in zones) == ["cryogen", "fume_hood"]


def test_a_true_one_metre_aisle_is_not_failed_by_grid_rounding():
    # Two benches leave exactly 1.0 m between them; the work spot is at the far end of that aisle.
    boxes = [(0.0, 0.0, 6.0, 1.5), (0.0, 2.5, 6.0, 4.0)]
    cut, _ = walkway_unreachable(6.0, 4.0, boxes, {"far_bench": (5.5, 2.0)}, {"x": 0, "y": 2.0}, 1.0)
    assert cut == []
    narrow = [(0.0, 0.0, 6.0, 1.6), (0.0, 2.4, 6.0, 4.0)]  # 0.8 m is not a 1.0 m walkway
    cut = walkway_unreachable(6.0, 4.0, narrow, {"far_bench": (5.5, 2.0)}, {"x": 0, "y": 2.0}, 1.0)[0]
    assert cut is None or cut == ["far_bench"]  # None: no 1 m walkway even enters the room


def test_crowded_hands_on_lab_keeps_a_walkway_to_every_work_spot():
    eq = {f"bench_{k}": "opentrons_flex" for k in range(10)}
    steps = [{"id": f"s{k}", "name": f"s{k}", "capability": "liquid_handling", "candidate_instances": [f"bench_{k}"],
              "duration_s": 600, "mode": "manual", "after": [f"s{k - 1}"] if k else []} for k in range(10)]
    spec = _spec(room=(7, 5))
    spec["operators"] = [{"role": "tech", "count": 2}]
    lay = generate_layout(spec, _wf(eq, steps))
    assert not [v for v in lay["violations"] if v["kind"] in ("egress_blocked", "overlap", "out_of_room")], lay["violations"]


def test_unguarded_arm_next_to_manual_work_proposes_a_placeholder_priced_guard():
    from labforge.layout.validate import _separation_violations, proposed_mitigations
    arm = {"transport": {"kind": "arm", "reach_m": 1.0}, "safety": {}, "access_points": [{"position": {"x": 0, "y": 0, "z": 0.9}}]}
    bench = {"access_points": [{"position": {"x": 0, "y": 0, "z": 0.9}}]}
    pos = lambda i, x: {"instance_id": i, "position": {"x": x, "y": 1, "z": 0.9}, "rotation_deg": 0}
    layout = {"operators": [{"id": "op_1"}], "placements": [pos("arm_1", 1), pos("bench_1", 1.5)],
              "transfers": [{"from_instance": "bench_1", "to_instance": "arm_1", "transporter_instance": "op_1"}]}
    found = _separation_violations(layout, {"arm_1": arm, "bench_1": bench}, load_rules(),
                                   {p["instance_id"]: p for p in layout["placements"]}, {"arm_1"})
    assert [v["kind"] for v in found] == ["safety"]
    layout["violations"] = found + found  # one line per arm, however many violations name it
    [line] = proposed_mitigations(layout)
    assert line["guards"] == ["arm_1", "bench_1"] and line["confidence"] == "placeholder" and not line["in_catalog"]
    assert line["price_range_usd"][0] < line["price_usd_estimate"] < line["price_range_usd"][1]
    assert any("pass-through" in a for a in line["alternatives"])
    arm["safety"]["collaborative"] = True
    assert not _separation_violations(layout, {"arm_1": arm, "bench_1": bench}, load_rules(),
                                      {p["instance_id"]: p for p in layout["placements"]}, {"arm_1"})
