"""
Score E171's saved forecasts (data/e171/out/oof.csv, all_rows.csv, written by the locked `candidates eval` before its scoring step
crashed on a missing E169 interval column). This module only reads the saved forecasts; no forecast is recomputed or changed.
The scoring is candidates.evaluate's own block; arms without a 90 % interval get NaN intervals (coverage not reported for them).

    python -m app.e171.score
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.e147 import evaluate as E7
from app.e156 import leads as LD
from app.e171 import candidates as C

OUT = C.OUT


def main():
    F = pd.read_csv(OUT / "oof.csv")
    Al = pd.read_csv(OUT / "all_rows.csv")
    main_, cor = Al[Al["mode"] == "main"], Al[Al["mode"] == "corrupt"]
    repro = float(np.max(np.abs(F["E168"] - F["R168"])))
    lk = F[C.KEY + ["mu_E171", "E171"]].merge(cor[C.KEY + ["mu_E171", "E171"]], on=C.KEY, suffixes=("", "_c"))
    leak = float(max(np.max(np.abs(lk["mu_E171"] - lk["mu_E171_c"])), np.max(np.abs(lk["E171"] - lk["E171_c"]))))
    arms = ["E168", "E169", *C.FAMILIES, "E166", "AUTO", "GOV", "NEWS", "LR", "LR_GOV", "LR_NEWS", "PSA", "PERS"]
    rel, ext, rounds, bri, no_interval = {}, {}, {}, {}, []
    rng = np.random.default_rng(171)
    for a in arms:
        if a not in F or F[a].isna().any():
            continue
        if f"mu_{a}" not in F:
            F[f"mu_{a}"] = np.log(np.clip(F[a], 1e-6, 1 - 1e-6) / np.clip(1 - F[a], 1e-6, 1))
        if f"half_{a}" not in F:
            F[f"half_{a}"] = np.nan
            no_interval.append(a)
        rel[a] = LD.evaluate(F, a, a)
        ext[a] = {int(h): C.extra(g, a) for h, g in F.groupby("lead")}
        rounds[a] = {int(h): {s: {"correct": int(((x[a] >= .5) == (x["y_high"] == 1)).sum()), "rows": int(len(x))} for s, x in g.groupby("survey")}
                     for h, g in F.groupby("lead")}
        if a != "E168":
            bri[a] = {int(h): E7.diff_ci(g.reset_index(drop=True), a, "E168", "q_true", rng, n=2000) for h, g in F.groupby("lead")}
    prov = {a: F.assign(ok=((F[a] >= .5) == (F["y_high"] == 1)).astype(int)).pivot_table(index=["province", "survey"], columns="lead", values="ok")
            .reset_index().to_dict("records") for a in ("E168", "E171", "A", "C", "D")}
    l = {r["lead"]: r for r in rel["E171"]["leads"]}
    d2 = bri["E171"][2]
    decision = {"reproduces_E168_max_abs_diff": repro, "leakage_max_abs_change": leak, "valid": bool(leak < 1e-9 and repro < 1e-9),
                "E171_lead1_C1_C6": l[1]["reliable"], "E171_lead2_C1_C6": l[2]["reliable"],
                "E171_lead2_brier_minus_E168": {"diff": round(d2["diff"], 4), "ci95": [round(z, 4) for z in d2["ci95"]]},
                "lead2_genuinely_improved_exploratory": bool(l[1]["reliable"] and l[2]["reliable"] and d2["ci95"][0] <= 0 and leak < 1e-9 and repro < 1e-9),
                "status": "EXPLORATORY (rows used in E151-E169); E168 remains the thesis model", "no_interval_arms": no_interval}
    cfg = main_.groupby(["survey", "lead"])[["scheme", "train_rounds"] + [f"tag_{f}" for f in C.FAMILIES]].first().reset_index()
    lam = main_.groupby(["survey", "lead"])[[f"lam_{f}" for f in C.FAMILIES]].first().round(3).reset_index()
    out = {"model": "E171 exploratory Lead-2 candidates", "decision": decision, "config_by_issue": cfg.to_dict("records"), "lambda_by_issue": lam.to_dict("records"),
           "reliability": rel, "extra": ext, "by_round": rounds, "by_province": prov,
           "brier_minus_E168": {a: {h: {"diff": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]} for h, v in x.items()} for a, x in bri.items()}}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(decision, indent=1))
    print(cfg.to_string(index=False))
    print(lam.to_string(index=False))
    for a in arms:
        if a in rel:
            for r in rel[a]["leads"]:
                x = ext[a][r["lead"]]
                print(f"{a:7s} L{r['lead']} {r['confusion']['tp'] + r['confusion']['tn']}/{r['rows']} acc {r['accuracy']} lo {r['accuracy_95_low_effective_n']} "
                      f"maj {r['majority_rule']} bal {r['balanced_accuracy']} prec {r['precision']} rec {r['high_recall']} f1 {r['f1']} auc {r['auc']} "
                      f"prauc {x['pr_auc']} brier {r['brier_soft']} slope {x['slope']} {x['slope_ci95']} int {x['intercept']} "
                      f"{''.join(k for k, v in r['criteria'].items() if not v) or 'ALL-PASS'}")
    for a in ("E168", "E171", "A", "C", "D"):
        print(a, {h: {s: f"{v['correct']}/{v['rows']}" for s, v in x.items()} for h, x in rounds[a].items()})
    for a in ("E171", "A", "C", "D", "E169"):
        print("brier minus E168", a, {h: v for h, v in out["brier_minus_E168"][a].items()})


if __name__ == "__main__":
    main()
