"""E48 controlled diagnostics on the ACTUAL served E38 next-quarter model (data/e36/model/E38-LGBM-NQ_O2026-10-01_lead2.txt).

1. Reproduce: booster raw score + the record's prior shift -> sigmoid must equal the record's 2027-Q1 p_high.
2. One input at a time, across its historical range in the record (all quarters, all provinces), for each province's
   2027-Q1 inputs: the probability response, the number of distinct output values (tree steps).
DIAGNOSTIC ONLY: the varied inputs are synthetic, never presented as forecasts.

    (from backend/) venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E48_Score_Variation/runner/e48_sensitivity.py
"""
import json
import math
from pathlib import Path

import lightgbm as lgb
import numpy as np

OUT = Path(__file__).resolve().parents[1] / "runs"
rec = json.loads(Path("data/e36/e36_record.json").read_text(encoding="utf-8"))
nq = rec["next_quarter_model"]
feats = nq["config"]["features"]
booster = lgb.Booster(model_file=nq["file"])
assert booster.feature_name() == feats, (booster.feature_name(), feats)
q = next(x for x in rec["quarters"] if x["quarter"] == "2027-Q1")
hist = {f: [] for f in feats}
for qq in rec["quarters"]:
    for v in qq["provinces"].values():
        for d in v.get("drivers", []):
            if d["key"] in hist and d["value"] is not None:
                hist[d["key"]].append(float(d["value"]))
rng = {f: (min(v), max(v)) if v else (0.0, 0.0) for f, v in hist.items()}
sig = lambda z: 1 / (1 + math.exp(-z))  # noqa: E731
out = {"model": nq["file"], "features": feats, "historical_range": rng, "provinces": {}}
for code, v in q["provinces"].items():
    x = {d["key"]: d["value"] for d in v["drivers"]}
    vec = np.array([[x[f] for f in feats]], dtype=float)
    raw = float(booster.predict(vec, raw_score=True)[0])
    p = sig(raw + v.get("prior_shift_logodds", 0.0))
    one = {}
    for j, f in enumerate(feats):
        lo, hi = rng[f]
        grid = np.linspace(lo, hi, 41)
        X = np.repeat(vec, len(grid), axis=0)
        X[:, j] = grid
        ps = [sig(r + v.get("prior_shift_logodds", 0.0)) for r in booster.predict(X, raw_score=True)]
        one[f] = {"actual_value": x[f], "p_min": round(min(ps), 4), "p_max": round(max(ps), 4),
                  "distinct_outputs": int(len(set(np.round(ps, 6))))}
    out["provinces"][v["province"]] = {"record_p": v["p_high"], "reproduced_p": round(p, 6),
                                       "reproduction_error": abs(p - v["p_high"]), "inputs": x, "one_at_a_time": one}
used = {}
for t in booster.dump_model()["tree_info"]:
    def walk(n):
        if "split_feature" in n:
            used[feats[n["split_feature"]]] = used.get(feats[n["split_feature"]], 0) + 1
            walk(n["left_child"]); walk(n["right_child"])
    walk(t["tree_structure"])
out["splits_per_feature"] = used
out["n_trees"] = booster.num_trees()
(OUT / "sensitivity_e38_nq.json").write_text(json.dumps(out, indent=1))
print("splits per feature:", used, "trees:", booster.num_trees())
for n, r in out["provinces"].items():
    print(n, "record", r["record_p"], "reproduced", r["reproduced_p"])
    for f, o in r["one_at_a_time"].items():
        print(f"   {f:9s} actual {o['actual_value']:>8} -> p {o['p_min']:.4f}..{o['p_max']:.4f}  distinct {o['distinct_outputs']}")
