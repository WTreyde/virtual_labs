"""Strand C: the "report for your boss". Owner: Albert.

v0 renders Markdown from the design objects; the UI turns it into a PDF.
TODO(Albert): Claude-written executive summary, layout screenshot from the game client, claims table.
"""
from labforge.catalog.store import get as get_item


def render_report(lab_spec: dict, workflow: dict, layout: dict, sim: dict) -> str:
    lines = [f"# {lab_spec['name']}: automated lab proposal", "", lab_spec["description"], "", "## Bill of materials", "",
             "| Instance | Vendor | Model | Est. price (USD) | Data confidence |", "|---|---|---|---|---|"]
    total = 0
    for e in workflow["equipment"]:
        it = get_item(e["catalog_id"])
        price = it.get("price_usd_estimate", 0)
        total += price
        lines.append(f"| {e['instance_id']} | {it['vendor']} | {it['model']} | {price:,.0f} | {it.get('data_confidence', 'estimated')} |")
    lines += [f"| **Total** | | | **{total:,.0f}** | |", ""]
    t = sim["throughput"]
    lines += ["## Throughput", "",
              f"Median {t.get('p50', t['value'])} {t['unit']} (P10 {t.get('p10', '?')}, P90 {t.get('p90', '?')}) against a target of {t.get('target')}. "
              f"Probability of meeting the target: {t.get('prob_meets_target', '?')}.", "", "## Bottlenecks and risks", ""]
    lines += [f"- **{b['severity']}**: {b['message']} {b.get('suggestion', '')}" for b in sim["bottlenecks"]] or ["- None found."]
    lines += ["", "## Layout issues", ""]
    lines += [f"- {v['message']}" for v in layout.get("violations", [])] or ["- None."]
    return "\n".join(lines) + "\n"
