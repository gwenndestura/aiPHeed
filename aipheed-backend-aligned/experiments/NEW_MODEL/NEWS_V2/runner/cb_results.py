"""NEWS_V2: C-b's evaluation in the OPTION_1 results.json layout, for the backend export (no refit, no new choice).

    python cb_results.py   # -> ../out/results_cb.json

Every number is recomputed from the stored C-b walk-forward forecasts (out/forecasts.csv), SHAP (out/shap_cb.csv) and
the Objective 4 / H3 tests (out/obj4_h3.json), with the frozen R1-R7 (hr_lib.evaluate) and Algorithm 3 at Leads 1-8.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_news_v2 as N  # noqa: E402

V, H, R = N.V, N.H, N.R
OUT = N.OUT


def main():
    plan = N.check_plan()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    L = pd.read_csv(N.LEADS_FILE)
    F = pd.read_csv(OUT / "forecasts.csv")
    cb = F[F["name"] == "C-b"][["name", "t", "lead", "q", "p"]]
    FF = pd.concat([L[L["name"].isin(["REF", "PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]], cb],
                   ignore_index=True)
    S = pd.read_csv(OUT / "shap_cb.csv")
    o43 = json.loads((OUT / "obj4_h3.json").read_text(encoding="utf-8"))
    V.GROUPS["N1 News"] = list(V.GROUPS["N1 News"]) + ["z_N1R"]
    res = {"model": "C-b", "plan_sha256": plan,
           "rule": "Algorithm 3: mean fold accuracy >= 0.75 (one quarter per fold), k = 1..8, halt at the first failing lead",
           "leads": {}}
    mx, mx_r = 0, 0
    for k in N.TEST_LEADS:
        W = R.frame(FF, k, lab_bl)
        g = W[W["C-b"].notna()]
        r = H.evaluate(g, "C-b")
        m = r["metrics"]
        Lk = {"n_quarters": int(len(g)), "period": f"{H.qs(int(g['q'].min()))}..{H.qs(int(g['q'].max()))}",
              "mean_fold_accuracy": m["accuracy"], "alg3_pass": bool(m["accuracy"] >= .75),
              "metrics": {x: m.get(x) for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier",
                                                "TP", "FP", "FN", "TN")},
              "rules": {x.split()[0]: {"pass": v["pass"], "value": v["value"]} for x, v in r["rules"].items()},
              "failed": [x.split()[0] for x, v in r["rules"].items() if not v["pass"]],
              "persistence_accuracy": float(((g["PERSIST"] >= .5).astype(int) == g["y"]).mean())}
        if k <= 2:
            s = S[(S["lead"] == k) & S["q"].isin(g["q"])]
            Lk["shap"] = {"rows": int(len(s)), "shares": V.group_shares(s, N.MODELS["C-b"])}
            Lk["objective4"] = o43["leads"][str(k)]["objective4"]
            Lk["h3"] = o43["leads"][str(k)]["h3"]
            ref = g["REF"]
            Lk["vs_REF"] = {"n_quarters": int(len(g)), "acc_a": m["accuracy"],
                            "acc_b": float(((ref >= .5).astype(int) == g["y"]).mean()),
                            "calls_differing": int(((g["C-b"] >= .5) != (ref >= .5)).sum()),
                            "identical_probabilities": int(((g["C-b"] - ref).abs() < 1e-12).sum())}
        res["leads"][f"L{k}"] = Lk
        if Lk["alg3_pass"] and mx == k - 1:
            mx = k
        if not Lk["failed"] and mx_r == k - 1:
            mx_r = k
    res["max_reliable_lead_alg3"] = mx
    res["first_failing_lead"] = mx + 1
    res["max_reliable_lead_R1_R7"] = mx_r
    (OUT / "results_cb.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print({k: (round(v["metrics"]["accuracy"], 3), v["failed"]) for k, v in res["leads"].items()},
          "| MRLT", mx, "| R1-R7", mx_r)


if __name__ == "__main__":
    main()
