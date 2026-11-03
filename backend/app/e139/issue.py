"""
E139 final audit outputs, run once after the locked evaluation:

    python -m app.e139.issue    final model (all rows, Lead 0) -> live provincial estimates for 2026-Q4 with
                                uncertainty and group explanations; CALABARZON 142-LGU vulnerability table; sealed
                                predictions for the next provincial survey round; artifact for the registry.

Outputs (data/e139/out/): model_artifact.json, provinces_live.json, lgus_calabarzon.csv, sealed_prediction.json.
Leads beyond the validated maximum are never written as forecasts.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.e139 import OUT, PROTOCOL_VERSION, VERSION
from app.e139 import live as LV
from app.e139 import model as M
from app.paths import BACKEND_DIR

CAL = {"batangas": "Batangas", "cavite": "Cavite", "laguna": "Laguna", "quezon": "Quezon", "rizal": "Rizal"}
N_BOOT = 200
MIN_EFFECT = 0.05            # |contribution| on the relative-logit scale below which a group is "not influential"
SENTENCE = {
    "poverty": ("Higher poverty and food-poverty levels mean more households may not afford enough food.",
                "Lower poverty levels mean fewer households are likely to lack the money for enough food."),
    "market": ("Recent food-price movements make basic food less affordable for households.",
               "Recent food-price movements have not added pressure on household food budgets."),
    "climate": ("Recent weather, typhoons or harvest results may weaken local food supply and farm incomes.",
                "Recent weather and harvests have not added pressure on local food supply."),
    "history": ("Earlier food-security surveys found this area at or above the national level of food insecurity.",
                "Earlier food-security surveys found this area below the national level of food insecurity."),
}


def quarter_of(d: pd.Timestamp) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def run() -> dict:
    res = json.loads((OUT / "results.json").read_text())
    X = M.data()
    final = M.LGBM().fit(X)
    Z = LV.build()
    Z["p_elevated"] = final.predict_proba(Z)
    Z["y_hat"] = final.predict_y(Z)
    gc = final.group_contributions(Z)
    rng = np.random.default_rng(M.SEED)
    cal = Z[Z["k"].isin(CAL)].reset_index(drop=True)
    regs = X["region"].unique()
    boots = []
    for _ in range(N_BOOT):
        s = pd.concat([X[X["region"] == r] for r in rng.choice(regs, len(regs))]).reset_index(drop=True)
        boots.append(M.LGBM().fit(s).predict_proba(cal))
    B = np.asarray(boots)
    issue = pd.Timestamp(LV.ISSUE)
    max_lead = res["max_reliable_lead"]
    provinces = []
    for i, r in cal.iterrows():
        g = gc.loc[Z.index[Z["k"] == r["k"]][0]]
        expl = []
        for grp, v in g.items():
            if abs(v) >= MIN_EFFECT:
                expl.append({"group": grp, "direction": "raises" if v > 0 else "lowers", "effect_logit": round(float(v), 3),
                             "sentence": SENTENCE[grp][0 if v > 0 else 1]})
            else:
                expl.append({"group": grp, "direction": "not influential", "effect_logit": round(float(v), 3),
                             "sentence": "This factor did not noticeably change the estimate for this province."})
        provinces.append({
            "province": CAL[r["k"]], "estimate_quarter": quarter_of(issue), "p_elevated": round(float(r["p_elevated"]), 4),
            "p_interval90": [round(float(np.percentile(B[:, i], 5)), 4), round(float(np.percentile(B[:, i], 95)), 4)],
            "class_at_0_5": "ELEVATED" if r["p_elevated"] >= 0.5 else "NOT ELEVATED",
            "explanations": expl,
            "context_only": {"employment": "no nationally comparable provincial series; not a model input",
                             "news": "CALABARZON-only archive; not a model input"}})
    p_first = pd.Series([CAL[cal["k"][j]] for j in B.argmax(axis=1)]).value_counts(normalize=True).round(3).to_dict()
    leads = []
    for k in range(0, 4):
        q = issue + pd.DateOffset(months=3 * k)
        leads.append({"lead": k, "quarter": quarter_of(q), "validated": max_lead is not None and k <= max_lead})
    live = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "issue_date": issue.date().isoformat(),
            "status_from_gate": "passed" if res["passed"] else "rejected", "max_reliable_lead": max_lead, "leads": leads,
            "what_this_is": "Estimated probability that the province's household food insecurity (HFIAS moderate-or-severe) "
                            "is above the national level. It is a risk estimate, not a measured prevalence.",
            "final_model": {"n_trees": final.n_trees_, "base_alpha": final.alpha_, "sigma": final.sigma_},
            "provinces": provinces, "p_rank_first": p_first}
    (OUT / "provinces_live.json").write_text(json.dumps(live, indent=2))
    # LGUs: vulnerability (PSA SAE poverty x density), never a measured or modelled municipal outcome
    lg = pd.read_csv(BACKEND_DIR / "data" / "fi5" / "out" / "lgu_rankings.csv")
    pmap = {p["province"]: p["p_elevated"] for p in provinces}
    lg = lg[["province_name", "lgu_psgc", "lgu_name", "lgu_type", "population_2024", "poverty_incidence_2021",
             "density_2024", "vulnerability"]].copy()
    lg["province_structural_p_elevated"] = lg["province_name"].map(pmap)
    lg["vulnerability_rank_in_region"] = lg["vulnerability"].rank(ascending=False, method="min").astype(int)
    lg["label"] = "municipal vulnerability (PSA poverty x density), not a municipal food-insecurity measurement"
    lg.to_csv(OUT / "lgus_calabarzon.csv", index=False)
    # seal + artifact
    seal = {"model": VERSION, "sealed_utc": datetime.now(timezone.utc).isoformat(), "issue_date": issue.date().isoformat(),
            "target": "P(province HFIAS/FIES moderate-or-severe significantly above national) at the next provincial round",
            "predictions": Z[["k", "p_elevated", "y_hat"]].round(5).to_dict(orient="records")}
    body = json.dumps(seal, indent=1, sort_keys=True)
    (OUT / "sealed_prediction.json").write_text(body)
    art = {"version": VERSION, "results_sha256": hashlib.sha256((OUT / "results.json").read_bytes()).hexdigest(),
           "sealed_prediction_sha256": hashlib.sha256(body.encode()).hexdigest(),
           "final_model": live["final_model"], "features": M.ALL, "trees_grid": M.TREES, "lgb_params": M.LGB_PARAMS}
    (OUT / "model_artifact.json").write_text(json.dumps(art, indent=2))
    print(json.dumps({k: live[k] for k in ("max_reliable_lead", "final_model", "p_rank_first")}, indent=1))
    for p in provinces:
        print(p["province"], p["p_elevated"], p["p_interval90"], [(e["group"], e["direction"]) for e in p["explanations"]])
    return live


if __name__ == "__main__":
    run()
