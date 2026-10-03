"""Published autonomous labs whose bottleneck the authors report, rebuilt for the Strand D simulator.

Each case has the paper's own numbers (marked `source`), our fill-ins for what the paper does not
give (marked `placeholder`), the bottleneck the authors name, and the throughput they observed.
`run.py` simulates each case and checks whether the simulator names the same bottleneck and lands
near the observed throughput. Equipment lives in a local catalog so Strand B's cache is untouched.
"""

# Durations in seconds. One labware unit = one batch rack (Burger) or one crystal plate (XChem).
MIN = 60

CATALOG = [
    # Burger et al. 2020: KUKA KMR iiwa mobile manipulator moving 16-vial racks between stations.
    {"id": "kuka_kmr_iiwa", "category": "transporter", "process": {}},
    {"id": "solid_dispense_station", "category": "instrument", "process": {"capacity": 1}},
    {"id": "liquid_dispense_station", "category": "instrument", "process": {"capacity": 1}},
    {"id": "capping_station", "category": "instrument", "process": {"capacity": 1}},
    {"id": "sonicator", "category": "instrument", "process": {"capacity": 1}},
    {"id": "photolysis_station", "category": "instrument", "process": {"capacity": 1}},
    {"id": "headspace_gc", "category": "instrument", "process": {"capacity": 1}},
    # XChem at Diamond: Echo soaking, crystal hotel, Shifter-assisted manual harvesting.
    {"id": "echo_650", "category": "instrument", "process": {"capacity": 1}},
    {"id": "crystal_hotel", "category": "instrument", "process": {"capacity": 200}},
    {"id": "harvest_bench", "category": "instrument", "process": {"capacity": 1}},
    {"id": "plate_cart_human", "category": "transporter", "process": {}},
]


def _step(id_, inst, dur, after, conf, unc=None):
    s = {"id": id_, "name": id_, "capability": id_, "candidate_instances": [inst] if inst else [],
         "duration_s": dur, "after": after, "confidence": conf}
    if unc:
        s["duration_uncertainty"] = {"low": unc[0], "high": unc[1]}
    return s


def _chain(steps):
    for prev, cur in zip(steps, steps[1:]):
        cur["after"] = [prev["id"]]
    return steps


def _transfers(order, mover, est_s, dist_m):
    return [{"from_instance": a, "to_instance": b, "transporter_instance": mover, "distance_m": dist_m, "est_time_s": est_s}
            for a, b in zip(order, order[1:]) if a != b]


def burger_2020():
    # Paper: 183 min to prepare + photolyse a batch, of which 60 min photolysis and 28 min load/unload;
    # 232 min GC per batch; "The slowest step in the workflow is the GC analysis".
    # The 95 min of preparation is split across the four prep stations by us (placeholder).
    steps = _chain([
        _step("solid_dispense", "solid_1", 40 * MIN, [], "placeholder"),
        _step("liquid_dispense", "liquid_1", 30 * MIN, [], "placeholder"),
        _step("cap", "cap_1", 10 * MIN, [], "placeholder"),
        _step("sonicate", "sonic_1", 15 * MIN, [], "placeholder"),
        _step("photolyse", "photo_1", 88 * MIN, [], "source"),  # 60 min light + 28 min load/unload
        _step("gc_analysis", "gc_1", 232 * MIN, [], "source", unc=(220 * MIN, 250 * MIN)),
    ])
    order = ["solid_1", "liquid_1", "cap_1", "sonic_1", "photo_1", "gc_1"]
    equipment = [{"instance_id": i, "catalog_id": c} for i, c in [
        ("solid_1", "solid_dispense_station"), ("liquid_1", "liquid_dispense_station"), ("cap_1", "capping_station"),
        ("sonic_1", "sonicator"), ("photo_1", "photolysis_station"), ("gc_1", "headspace_gc"), ("robot_1", "kuka_kmr_iiwa")]]
    # 2.17 km over 319 moves = 6.8 m per move (source); ~2 min per move incl. docking (placeholder).
    transfers = _transfers(order, "robot_1", 120, 6.8)
    return {
        "id": "burger_2020",
        "title": "Liverpool mobile robotic chemist (Burger et al., Nature 2020)",
        "sources": ["https://www.nature.com/articles/s41586-020-2442-2",
                    "https://strathprints.strath.ac.uk/74759/1/Burger_etal_Nature_2020_A_mobile_robotic.pdf"],
        "reported_bottleneck": "gc_1",
        "reported_quote": "The slowest step in the workflow is the GC analysis",
        "observed": {"value": 688 / 16 / 8, "unit": "batches_per_day",
                     "note": "688 experiments in 8 days at 16 per batch; the robot was charging ~32% of the time"},
        "spec": {"throughput_target": {"value": 5, "unit": "batches_per_day", "operating_hours_per_day": 24}},
        "workflow": {"id": "burger_2020_wf", "equipment": equipment, "steps": steps},
        "layout": {"id": "burger_2020_layout", "transfers": transfers},
        "whatif_instance": "gc_1",
    }


def xchem(crystals_per_hour: float, label: str):
    # Wright et al. 2021 (Acta D, Shifter): manual harvesting ~8 crystals/h; Shifter mean 103/h, median 120/h,
    # "a bottleneck in the wider MX workflow". One plate = 96 soaked drops (placeholder: one crystal per drop).
    # Echo soak ~5 min per plate and 1-3 h soak come from docs/pipelines.md (estimated).
    per_plate = 96
    harvest_s = per_plate / crystals_per_hour * 3600
    steps = _chain([
        _step("echo_soak", "echo_1", 5 * MIN, [], "estimated", unc=(3 * MIN, 8 * MIN)),
        _step("soak_incubate", "hotel_1", 2 * 3600, [], "estimated", unc=(3600, 3 * 3600)),
        _step("harvest", "harvest_1", harvest_s, [], "source", unc=(harvest_s * 0.8, harvest_s * 1.5)),
    ])
    equipment = [{"instance_id": i, "catalog_id": c} for i, c in [
        ("echo_1", "echo_650"), ("hotel_1", "crystal_hotel"), ("harvest_1", "harvest_bench"), ("cart_1", "plate_cart_human")]]
    transfers = _transfers(["echo_1", "hotel_1", "harvest_1"], "cart_1", 60, 4.0)
    return {
        "id": f"xchem_{label}",
        "title": f"XChem fragment soaking + harvesting, {label} ({crystals_per_hour:g} crystals/h)",
        "sources": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC7787106/",
                    "https://www.diamond.ac.uk/Instruments/Mx/Fragment-Screening/The-XChem-Pipeline.html"],
        "reported_bottleneck": "harvest_1",
        "reported_quote": "Manual mounting of crystals ... is a bottleneck in the wider MX workflow",
        "observed": {"value": crystals_per_hour * 8, "unit": "crystals_per_8h_shift",
                     "note": "harvest rate from the Shifter paper times one 8 h shift; not a measured facility figure"},
        "spec": {"throughput_target": {"value": 1, "unit": "plates_per_day", "operating_hours_per_day": 8}},
        "workflow": {"id": f"xchem_{label}_wf", "equipment": equipment, "steps": steps},
        "layout": {"id": f"xchem_{label}_layout", "transfers": transfers},
        "whatif_instance": "harvest_1",
        "crystals_per_plate": per_plate,
    }


def all_cases():
    return [burger_2020(), xchem(8, "manual"), xchem(103, "shifter")]
