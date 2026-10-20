"""Q4 2026 five-driver percentages (via the dashboard service) and the news-title topic counts behind them."""
import json

from app.ml.inference import e31_engine as E31
from app.services import dashboard as svc
from app.services import reference as ref

Q = "2026-Q4"
row = E31.quarter_row(Q, "forecast")
ev = row["provenance"]["news_evidence_window"]["evidence_quarter"]
order = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
print(f"Q4 2026 (evidence quarter {ev})")
print(f"{'':12s}" + "".join(f"{k:>16s}" for k in order) + "   index")
reg = svc.explainability_region(Q)
pct = {t["key"]: t["pct"] for t in reg["triggers"]}
print(f"{'CALABARZON':12s}" + "".join(f"{pct[k]:>15d}%" for k in order))
for slug in ref.PROVINCES:
    code = ref.province_code(slug)
    e = svc.explainability(code, Q)
    pct = {t["key"]: t["pct"] for t in e["triggers"]}
    print(f"{ref.PROVINCES[slug]['name']:12s}" + "".join(f"{pct[k]:>15d}%" for k in order)
          + f"   p={row['provinces'][code]['p_high']}")
print("\nvalidated news titles in", ev, "by topic (a title can have several topics):")
for slug in ref.PROVINCES:
    code = ref.province_code(slug)
    _, c = E31.news_topic_shares(code, ev)
    print(f"  {ref.PROVINCES[slug]['name']:10s} {json.dumps(c)}")
_, c = E31.news_topic_shares(None, ev)
print(f"  {'REGION':10s} {json.dumps(c)}")
for slug in ref.PROVINCES:
    code = ref.province_code(slug)
    titles = [a["title"] for a in E31.record()["news"]["articles"] if a["quarter"] == ev and a["province_code"] == code]
    from app.ml.nlp.trigger_classifier import classify_triggers
    for t in titles:
        print(f"    [{ref.PROVINCES[slug]['name']}] {classify_triggers(t)} {t[:90]}")
