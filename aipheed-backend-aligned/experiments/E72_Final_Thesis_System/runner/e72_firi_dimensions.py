"""E72 audit of the served FIRI v2 along the food-security dimensions (run with cwd = backend, thesis env).
Uses the serving code path (thesis_system.firi_for, dimensions.breakdown) for every Lead-2 history row and the served
2027-Q1 estimate. Writes ../aipheed-backend-aligned/experiments/E72_Final_Thesis_System/out/firi_dimensions.json."""
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")
sys.path.insert(0, ".")
from app.ml.inference import dimensions as D  # noqa: E402
from app.ml.inference import e41_lead2 as LEAD2  # noqa: E402
from app.ml.inference import thesis_system as T  # noqa: E402

OUT = Path("../aipheed-backend-aligned/experiments/E72_Final_Thesis_System/out/firi_dimensions.json")
rec = LEAD2.record()
rows = list(csv.DictReader(open(T.FIRI_HISTORY, encoding="utf-8")))
keys = sorted({(r["target"], r["province_code"]) for r in rows if r["FIRI"]} | {(rec["targetQuarter"], c) for c in rec["provinces"]})
res, err = [], 0.0
for q, c in keys:
    f = T.firi_for(rec, q, c)
    if not f or f["firi"] is None:
        continue
    b = D.breakdown(f)
    tot = sum(d["push"] for d in b if d["push"] is not None)
    err = max(err, abs(tot - (f["firi"] - 0.5)))
    wo = D.without_outcome(f)
    res.append({"target": q, "province_code": c, "firi": f["firi"], "class": f["class"], "without_outcome": wo,
                "class_without_outcome": None if wo is None else ("HIGH" if wo >= 0.5 else "LOW"),
                **{f"push_{d['key']}": d["push"] for d in b}, **{f"share_{k}": v for k, v in D.shares(f).items()}})
n = len(res)
hi = [r for r in res if r["class"] == "HIGH"]
summ = {"rows": n, "targets": [min(r["target"] for r in res), max(r["target"] for r in res)],
        "max_reconstruction_error": err, "HIGH": len(hi),
        "mean_abs_share": {k: sum(r.get(f"share_{k}", 0.0) for r in res) / n for k in D.ORDER if k != "UTILIZATION"},
        "HIGH_rows_low_without_outcome": sum(1 for r in hi if r["class_without_outcome"] == "LOW"),
        "HIGH_rows_without_outcome_computable": sum(1 for r in hi if r["class_without_outcome"] is not None),
        "largest_positive_push_of_HIGH_rows": {}}
cnt = defaultdict(int)
for r in hi:
    p = {k: r[f"push_{k}"] for k in D.ORDER if r.get(f"push_{k}") is not None}
    cnt[max(p, key=p.get)] += 1
summ["largest_positive_push_of_HIGH_rows"] = dict(cnt)
byq = defaultdict(list)
for r in res:
    byq[r["target"]].append(r)
summ["by_target"] = {q: {"HIGH": sum(x["class"] == "HIGH" for x in v), "n": len(v),
                         "HIGH_without_outcome": sum(x["class_without_outcome"] == "HIGH" for x in v),
                         "mean_push_OUTCOME": sum(x["push_OUTCOME"] or 0 for x in v) / len(v),
                         "mean_push_ACCESS": sum(x["push_ACCESS"] or 0 for x in v) / len(v)} for q, v in sorted(byq.items())}
OUT.write_text(json.dumps({"summary": summ, "rows": res}, indent=1))
print(json.dumps({k: v for k, v in summ.items() if k != "by_target"}, indent=1))
for q, v in summ["by_target"].items():
    print(q, v)
