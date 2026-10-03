"""Small, explicitly reviewed public references; never presented as Amass retrieval."""
import copy

WRIGHT = {
    'title': 'Wright et al. (2021): The low-cost Shifter microscope stage transforms the speed and robustness of protein crystal harvesting',
    'reviewed_at': '2026-10-03',
    'section': '3.2.2',
    'summary': 'Manual baseline: 8 crystals/hour from a six-person survey, including ancillary work. Shifter mean: 35 seconds/mount (103/hour), from 8271 mounts; median 30 seconds. Rates depend on operator and crystal system; do not treat them as universal guarantees.',
    'rates_per_hour': {'unassisted_manual': 8, 'shifter_mean': 103},
    'evidence': {'claim': 'Published mounting-rate comparison; application to this design needs explicit unit conversion and uncertainty.',
                 'source': 'https://doi.org/10.1107/S2059798320014114', 'provider': 'web'},
}


def search_reviewed(query):
    q = query.lower()
    if 'shifter' in q or 's2059798320014114' in q or ('crystal' in q and any(w in q for w in ('harvest', 'mount'))):
        return [copy.deepcopy(WRIGHT)]
    return []
