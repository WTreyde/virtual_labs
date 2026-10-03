"""Strand D layout behaviour: multi-arm clusters, locked placements, zones, safety and egress checks."""
import copy
import time

from labforge.contracts import errors, load_example
from labforge.layout.placer import edge_weights, generate_layout, resolve_items
from labforge.layout.validate import find_violations

H = "generic_plate_hotel"


def st(sid, cands, cap, after=(), **kw):
    return {"id": sid, "name": sid, "capability": cap, "candidate_instances": cands, "duration_s": 600, "after": list(after), **kw}


def chem(arms=2):
    eq = {"dose_1": "opentrons_flex", "lh_1": "opentrons_flex", "block_1": "liconic_stx44", "filt_1": "opentrons_flex",
          "evap_1": H, "lcms_1": "bmg_clariostar", "echo_1": "agilent_plateloc", "inc_1": "liconic_stx44", "reader_1": "bmg_clariostar"}
    eq.update({f"arm_{k + 1}": "ur5e" for k in range(arms)})
    steps = [st("stock", ["dose_1"], "powder_dosing"), st("setup", ["lh_1"], "liquid_handling", ["stock"]),
             st("react", ["block_1"], "reaction", ["setup"]), st("workup", ["filt_1"], "filtration", ["react"], fan_out=8),
             st("evap", ["evap_1"], "evaporation", ["workup"], batch_size=6), st("qc", ["lcms_1"], "lcms", ["evap"]),
             st("dispense", ["echo_1"], "acoustic_dispensing", ["qc"]), st("incubate", ["inc_1"], "incubation", ["dispense"]),
             st("read", ["reader_1"], "fluorescence_read", ["incubate"])]
    spec = {"id": "chem", "name": "c", "domain": "chemistry", "description": "c",
            "throughput_target": {"value": 768, "unit": "compounds_per_day"},
            "room": {"width_m": 10, "depth_m": 8, "doors": [{"x": 0, "y": 4}]},
            "constraints": {"hazards": ["flammable_solvents"]}, "operators": [{"role": "chemist", "count": 1}]}
    wf = {"id": "chem_wf", "lab_spec_id": "chem", "steps": steps,
          "equipment": [{"instance_id": i, "catalog_id": c} for i, c in eq.items()]}
    return spec, wf


def kinds(layout):
    return [v["kind"] for v in layout["violations"]]


def test_fan_out_weights_downstream_transfers():
    _, wf = chem()
    w = edge_weights(wf)
    assert w[("filt_1", "evap_1")] == 8 * w[("block_1", "filt_1")]


def test_two_arm_clusters_without_collisions():
    spec, wf = chem(arms=2)
    t = time.time()
    lay = generate_layout(spec, wf)
    assert time.time() - t < 5
    assert errors(lay, "layout") == []
    assert not {"overlap", "out_of_room", "unreachable_transfer", "egress_blocked"} & set(kinds(lay))
    movers = {t["transporter_instance"] for t in lay["transfers"]}
    assert movers & {"arm_1", "arm_2"}  # arms do the work they can reach (a second arm may honestly turn out idle)
    assert "chemist_1" in movers  # and a person links what the arms cannot reach
    heaviest = max(edge_weights(wf).items(), key=lambda kv: kv[1])[0]  # fan-out traffic should not be hand-carried
    assert next(t for t in lay["transfers"] if (t["from_instance"], t["to_instance"]) == heaviest)["transporter_instance"] != "chemist_1"


def test_flammable_synthesis_gets_a_ventilated_enclosure():
    spec, wf = chem()
    lay = generate_layout(spec, wf)
    assert any(z["kind"] in ("fume_hood", "ventilated") for z in lay["zones"])
    assert "zone_mismatch" not in kinds(lay)

    moved = copy.deepcopy(lay)  # someone drags the reaction block out of the hood in the UI
    moved["zones"] = []
    items = resolve_items(wf)
    found = find_violations(moved, items, spec, workflow=wf)
    assert any(v["kind"] == "zone_mismatch" and "block_1" in v["instances"] for v in found)


def test_locked_placement_stays_put():
    spec, wf = chem(arms=1)
    first = generate_layout(spec, wf)
    pin = next(p for p in first["placements"] if p["instance_id"] == "lcms_1")
    pin.update(position={"x": 8.5, "y": 1.0, "z": 0.9}, rotation_deg=90, locked=True)
    again = generate_layout(spec, wf, previous=first)
    got = next(p for p in again["placements"] if p["instance_id"] == "lcms_1")
    assert got["position"] == {"x": 8.5, "y": 1.0, "z": 0.9} and got["rotation_deg"] == 90 and got["locked"]


def test_keep_out_zone_is_avoided_and_checked():
    spec, wf = load_example("lab_spec"), load_example("workflow")
    spec = copy.deepcopy(spec)
    spec["room"]["keep_out_zones"] = [{"min": {"x": 2.0, "y": 0.0}, "max": {"x": 4.0, "y": 4.0}, "reason": "pillar"}]
    lay = generate_layout(spec, wf)
    assert "keep_out" not in kinds(lay)
    bad = copy.deepcopy(lay)
    for p in bad["placements"]:
        p["position"].update(x=3.0)
    assert "keep_out" in kinds({"violations": find_violations(bad, resolve_items(wf), spec, workflow=wf)})


def test_blocked_door_and_people_in_arm_envelope_are_flagged():
    spec, wf = load_example("lab_spec"), load_example("workflow")
    lay = generate_layout(spec, wf)
    items = resolve_items(wf)
    bad = copy.deepcopy(lay)
    hotel = next(p for p in bad["placements"] if p["instance_id"] == "hotel_1")
    hotel["position"].update(x=0.3, y=2.0)
    bad["operators"] = [{"id": "tech_1", "role": "tech", "home": {"x": 0, "y": 2}}]
    for t in bad["transfers"]:
        if t["to_instance"] == "lh_1":
            t["transporter_instance"] = "tech_1"
    found = find_violations(bad, items, spec, workflow=wf)
    assert any(v["kind"] == "egress_blocked" and "hotel_1" in v["instances"] for v in found)
    assert any(v["kind"] == "safety" and "arm_1" in v["instances"] for v in found)


def test_unknown_catalog_id_gets_placeholder_geometry():
    spec, wf = load_example("lab_spec"), copy.deepcopy(load_example("workflow"))
    wf["equipment"].append({"instance_id": "mystery_1", "catalog_id": "not_in_catalog_yet"})
    wf["steps"].append(st("mystery", ["mystery_1"], "manual_bench", ["read"]))
    lay = generate_layout(spec, wf)
    assert any(p["instance_id"] == "mystery_1" for p in lay["placements"])


def _manual_lab():
    """A hands-on lab with no arms: every instrument is free-standing, so all of them should line the walls."""
    eq = {"lh_1": "opentrons_flex", "inc_1": "liconic_stx44", "reader_1": "bmg_clariostar", "seal_1": "agilent_plateloc",
          "bench_1": "lab_bench"}
    steps = [st("prep", ["bench_1"], "manual_bench", mode="manual"), st("dispense", ["lh_1"], "liquid_handling", ["prep"]),
             st("seal", ["seal_1"], "plate_sealing", ["dispense"]), st("incubate", ["inc_1"], "incubation", ["seal"]),
             st("read", ["reader_1"], "fluorescence_read", ["incubate"])]
    spec = {"id": "m", "name": "m", "domain": "biology", "description": "m", "throughput_target": {"value": 10, "unit": "plates_per_day"},
            "room": {"width_m": 8, "depth_m": 6, "doors": [{"x": 0, "y": 3}]}, "operators": [{"role": "tech", "count": 3}]}
    wf = {"id": "w", "lab_spec_id": "m", "equipment": [{"instance_id": i, "catalog_id": c} for i, c in eq.items()], "steps": steps}
    return spec, wf


def test_free_standing_instruments_line_the_walls_in_process_order():
    from labforge.layout.geometry import aabb
    from labforge.layout.placer import Placer
    spec, wf = _manual_lab()
    lay = generate_layout(spec, wf)
    assert not lay["violations"], lay["violations"]
    items, W, D = resolve_items(wf), 8, 6
    order = ["bench_1", "lh_1", "seal_1", "inc_1", "reader_1"]
    pos = {p["instance_id"]: p for p in lay["placements"]}
    for i in order:  # every bench backs onto a wall
        x0, y0, x1, y1 = aabb(pos[i], items[i])
        assert min(x0, y0, W - x1, D - y1) <= 0.08, (i, (x0, y0, x1, y1))
    p = Placer(spec, wf, None, 0)  # ...and they follow the process around the room from the door, in one direction
    perim = []
    for i in order:
        x, y = pos[i]["position"]["x"], pos[i]["position"]["y"]
        wall = p._wall_of(aabb(pos[i], items[i]))
        t = {"W": y, "N": D + x, "E": D + W + (D - y), "S": 2 * D + W + (W - x)}[wall]  # clockwise from (0, 0)
        perim.append((t - spec["room"]["doors"][0]["y"]) % (2 * (W + D)))
    steps = [b - a for a, b in zip(perim, perim[1:])]
    assert all(s > 0 for s in steps) or all(s < 0 for s in steps), perim


def test_lab_like_layout_never_has_more_violations_than_the_annealed_one():
    from labforge.layout.placer import Placer, _one_layout
    for spec, wf in (chem(2), _manual_lab(), (load_example("lab_spec"), load_example("workflow"))):
        p = Placer(spec, wf, None, 0)
        state = p.anneal(p.initial(), min(6000, 1500 + 200 * len(p.movable)))
        annealed = p.build(state)
        annealed_v = find_violations(annealed, p.items, spec, p.rules, workflow=wf)
        assert len(_one_layout(spec, wf, None, 0, None)["violations"]) <= len(annealed_v)


def test_break_area_gives_idle_staff_their_own_spots_clear_of_equipment_and_hazards():
    from labforge.layout.geometry import aabb, overlap_area
    from labforge.layout.safety import door_box
    spec, wf = _manual_lab()
    lay = generate_layout(spec, wf)
    [rest] = [z for z in lay["zones"] if z["id"] == "break_area"]
    assert rest["kind"] == "human_only"
    box = (rest["min"]["x"], rest["min"]["y"], rest["max"]["x"], rest["max"]["y"])
    items = resolve_items(wf)
    assert all(overlap_area(box, aabb(p, items[p["instance_id"]], clearance=True)) == 0 for p in lay["placements"])
    assert overlap_area(box, door_box(spec["room"]["doors"][0], 8, 6, 1.2)) == 0
    assert all(overlap_area(box, (z["min"]["x"], z["min"]["y"], z["max"]["x"], z["max"]["y"])) == 0
               for z in lay["zones"] if z is not rest)
    homes = [(o["home"]["x"], o["home"]["y"]) for o in lay["operators"]]
    assert len(homes) == 3 and len(set(homes)) == 3  # not all back to one spot
    assert all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in homes)
