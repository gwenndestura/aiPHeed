"""
Score E172's saved forecasts (data/e172/out/oof.csv, all_rows.csv) with the unchanged app.e156.leads.evaluate, and apply the
protocol's decision rule. Reads forecasts only; nothing is recomputed.

    python -m app.e172.score
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.e147 import evaluate as E7
from app.e156 import leads as LD
from app.e171 import candidates as C171
from app.e172 import lgbm_only as E

OUT = E.OUT
ARMS = ["E168", "E171", "E172", "POOLED", "EXACT", "SIMPLE", "BAG", "E166", "AUTO", "GOV", "NEWS", "LR", "LR_GOV", "LR_NEWS", "PSA", "PERS"]
LGBM_ARMS = {"E168", "E171", "E172", "POOLED", "EXACT", "SIMPLE", "BAG", "GOV", "NEWS"}


def main():
    F = pd.read_csv(OUT / "oof.csv")
    Al = pd.read_csv(OUT / "all_rows.csv")
    main_, cor = Al[Al["mode"] == "main"], Al[Al["mode"] == "corrupt"]
    repro = float(np.max(np.abs(F["E168"] - F["R168"])))
    lk = F[E.KEY + ["mu_E172", "E172"]].merge(cor[E.KEY + ["mu_E172", "E172"]], on=E.KEY, suffixes=("", "_c"))
    leak = float(max(np.max(np.abs(lk["mu_E172"] - lk["mu_E172_c"])), np.max(np.abs(lk["E172"] - lk["E172_c"]))))
    rel, ext, rounds, bri, conf = {}, {}, {}, {}, {}
    rng = np.random.default_rng(172)
    for a in ARMS:
        if a not in F or F[a].isna().any():
            continue
        if f"mu_{a}" not in F:
            F[f"mu_{a}"] = np.log(np.clip(F[a], 1e-6, 1 - 1e-6) / np.clip(1 - F[a], 1e-6, 1))
        if f"half_{a}" not in F:
            F[f"half_{a}"] = np.nan
        rel[a] = LD.evaluate(F, a, a)
        ext[a] = {int(h): C171.extra(g, a) for h, g in F.groupby("lead")}
        rounds[a] = {int(h): {s: f"{int(((x[a] >= .5) == (x['y_high'] == 1)).sum())}/{len(x)}" for s, x in g.groupby("survey")} for h, g in F.groupby("lead")}
        if a != "E168":
            bri[a] = {int(h): E7.diff_ci(g.reset_index(drop=True), a, "E168", "q_true", rng, n=2000) for h, g in F.groupby("lead")}
    prov = F.assign(E168_ok=((F["E168"] >= .5) == (F["y_high"] == 1)).astype(int), E172_ok=((F["E172"] >= .5) == (F["y_high"] == 1)).astype(int))
    changed = prov[prov["E168_ok"] != prov["E172_ok"]][["province", "survey", "lead", "y_high", "E168", "E172", "E168_ok", "E172_ok"]].round(3)
    # training-only comparison: E172's chosen configuration vs E168's configuration, same folds, per issue
    tcmp = []
    for r in main_.itertuples(index=False):
        sc = json.loads(r.train_scores)
        a, l, f, _ = r.tag_E172.split("|")
        tcmp.append({"survey": r.survey, "lead": int(r.lead), "scheme": r.scheme, "E172_cfg": r.tag_E172, "E172_score": sc[f"{a}|{l}|{f}"],
                     "E168_score": sc.get("E168_chosen"), "not_worse": sc[f"{a}|{l}|{f}"] <= sc.get("E168_chosen", np.inf) + 1e-12})
    tcmp = pd.DataFrame(tcmp).drop_duplicates(["survey", "lead"])
    l = {r["lead"]: r for r in rel["E172"]["leads"]}
    d2 = bri["E172"][2]
    t2 = tcmp[tcmp["lead"] == 2]
    rule = {"lightgbm": True, "valid": bool(leak < 1e-9 and repro < 1e-9), "lead2_C1_C6": bool(l[2]["reliable"]), "lead1_C1_C6": bool(l[1]["reliable"]),
            "lead2_brier_not_significantly_worse": bool(d2["ci95"][0] <= 0),
            "training_score_not_worse_in_majority_of_lead2_issues": bool(t2["not_worse"].sum() * 2 > len(t2))}
    decision = {"reproduces_E168_max_abs_diff": repro, "leakage_max_abs_change": leak, "rule": rule,
                "candidate_for_adoption_review": bool(all(rule.values())),
                "lead2_brier_minus_E168": {"diff": round(d2["diff"], 4), "ci95": [round(z, 4) for z in d2["ci95"]]},
                "status": "EXPLORATORY (rows examined in E151-E171); E168 remains the thesis model"}
    cfg = main_.groupby(["survey", "lead"])[["scheme", "anchor", "train_rounds"] + [f"tag_{s}" for s in E.SUBSETS]].first().reset_index()
    out = {"model": "E172 exploratory LightGBM-only Lead-2 candidates", "decision": decision, "config_by_issue": cfg.to_dict("records"),
           "training_only_comparison": tcmp.to_dict("records"), "train_scores_by_issue": {f"{r.survey}|{int(r.lead)}": json.loads(r.train_scores) for r in main_.itertuples(index=False)},
           "reliability": rel, "extra": ext, "by_round": rounds, "rows_changed_vs_E168": changed.to_dict("records"),
           "brier_minus_E168": {a: {h: {"diff": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]} for h, v in x.items()} for a, x in bri.items()}}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(decision, indent=1))
    print(cfg.to_string(index=False))
    print(tcmp.to_string(index=False))
    for a in ARMS:
        if a in rel:
            for r in rel[a]["leads"]:
                c, x = r["confusion"], ext[a][r["lead"]]
                print(f"{a:7s} {'LGBM' if a in LGBM_ARMS else 'ref ':4s} L{r['lead']} {c['tp'] + c['tn']}/{r['rows']} acc {r['accuracy']} lo {r['accuracy_95_low_effective_n']} "
                      f"maj {r['majority_rule']} FP {c['fp']} FN {c['fn']} bal {r['balanced_accuracy']} prec {r['precision']} rec {r['high_recall']} f1 {r['f1']} "
                      f"auc {r['auc']} prauc {x['pr_auc']} brier {r['brier_soft']} slope {x['slope']} {x['slope_ci95']} int {x['intercept']} "
                      f"{' '.join(k + ('=1' if v else '=0') for k, v in r['criteria'].items())}")
    for a in ("E168", "E172", "POOLED", "EXACT", "SIMPLE", "BAG"):
        print("by round", a, rounds.get(a))
    print("rows changed vs E168:\n", changed.to_string(index=False))
    for a in ("E172", "POOLED", "EXACT", "SIMPLE", "BAG"):
        print("brier minus E168", a, out["brier_minus_E168"].get(a))


if __name__ == "__main__":
    main()
