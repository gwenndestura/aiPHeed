"""E28 additive view (deviation M-E28-3 in BUG_FIXES.md): every arm on the rows ALL arms share.

E25's PROPOSED_lgbm_combined (PROPOSED_E25) has no prediction for origin 2026-Q1 at lead 1 (E25's features end at
2025-Q4), so its metrics in results.json are on 140 of 145 T1 rows (205 of 210 T2). This script re-scores every arm on
the common rows with the same metrics and paired tests. It reads runs/e28_eval/predictions.csv only; the frozen
evaluation is not re-run and no decision rule changes.   -> runs/e28_eval_common_rows.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard28  # noqa: E402

guard28.install()
import pandas as pd  # noqa: E402

import e28_metrics as M  # noqa: E402

EXP = guard28.EXP
P = pd.read_csv(EXP / "runs" / "e28_eval" / "predictions.csv", dtype={"province_code": str})
REFS = ["B1", "ALWAYS_HIGH", "CLIM", "MAJ", "PSA_LR", "PSA_LGBM", "NLP_LR", "NLP_LGBM", "LR_COMB"]
out = {}
for tg, g in P.groupby("target"):
    keys = None
    for a, h in g.groupby("arm"):
        k = set(zip(h["lead"], h["t"], h["province_code"]))
        keys = k if keys is None else keys & k
    c = g[[x in keys for x in zip(g["lead"], g["t"], g["province_code"])]]
    res = {"rows": len(keys), "dates": int(c["t"].nunique()), "arms": {}}
    for a, h in c.groupby("arm"):
        l1 = h[h["lead"] == 1]
        m1 = M.point_metrics(l1["y"], l1["p"])
        mp = M.point_metrics(h["y"], h["p"])
        la = M.per_date_losses(h)
        tests = {}
        for ref in ("B1", "ALWAYS_HIGH", "CLIM"):
            if ref == a:
                continue
            j = la.join(M.per_date_losses(c[c["arm"] == ref]), lsuffix="_a", rsuffix="_r", how="inner")
            tests[ref] = {"brier_diff_mean": float((j["bri_r"] - j["bri_a"]).mean()),
                          "p_brier": M.signflip_p(j["bri_r"] - j["bri_a"]),
                          "acc_diff_mean": float((j["err_r"] - j["err_a"]).mean()),
                          "p_acc": M.signflip_p(j["err_r"] - j["err_a"])}
        res["arms"][a] = {"lead1": {k: m1[k] for k in ("n", "HIGH", "LOW", "accuracy", "brier", "roc_auc", "TP", "FP", "TN", "FN")},
                          "pooled": {k: mp[k] for k in ("n", "accuracy", "brier", "log_loss")}, "vs": tests}
    out[tg] = res
(EXP / "runs" / "e28_eval_common_rows.json").write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
for tg, res in out.items():
    print(f"== {tg}: {res['rows']} common rows, {res['dates']} dates")
    for a in ["B1", "ALWAYS_HIGH", "PROPOSED", "PROPOSED_PERSIST", "LR_STRUCT", "PSA_LR", "LR_COMB", "PROPOSED_E25", "PCF21_E25", "M4_21_E25"]:
        if a in res["arms"]:
            x = res["arms"][a]
            vb = x["vs"].get("B1", {})
            print(f"{a:18s} L1 acc {x['lead1']['accuracy']:.3f} brier {x['lead1']['brier']:.3f} | pooled acc {x['pooled']['accuracy']:.3f} "
                  f"brier {x['pooled']['brier']:.3f} | vs B1 brier {vb.get('brier_diff_mean', 0):+.3f} p={vb.get('p_brier')}")
