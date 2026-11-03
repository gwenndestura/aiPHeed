"""
Operational issue of the E140 LightGBM (trees, no linear prior) for the dashboard's forecast quarter, as a CANDIDATE.

    python -m app.e140.issue        -> data/e140/out/{forecast_next_quarter.json, lgus_next_quarter.csv,
                                       sealed_prediction.json} and a record in the provincial prospective register

What is issued:
    target quarter      the calendar quarter after the issue quarter (dashboard rule), issue at its start
    model               LGBM-AUTO trained on all 125 HFIAS rows with features frozen ONE quarter before each survey's
                        reference quarter (Lead 1), i.e. the same information gap as the live issue
    output              P(province HFIAS moderate-or-severe above the national level), 90 % region-bootstrap interval,
                        group effects (prediction minus prediction with the group at its training median)
    LGUs                province P x municipal vulnerability (1/2 PSA SAE 2021 poverty percentile + 1/2 POPCEN 2024
                        density percentile, region-wide; FI5 rule, OECD/JRC equal weights when no outcome exists to fit
                        weights), with the province interval carried through. A vulnerability-weighted risk RANKING,
                        not a municipal measurement.
Validation status: E140 decision C (rejected); the issue is a candidate for admin review and prospective scoring only.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.e137 import outcomes as O
from app.e139 import live as LV
from app.e140 import model as M
from app.paths import BACKEND_DIR
from app.quarterly.target import forecast_target
from app.registry import prospective_provincial as PP

OUT = BACKEND_DIR / "data" / "e140" / "out"
CAL = {"batangas": "Batangas", "cavite": "Cavite", "laguna": "Laguna", "quezon": "Quezon", "rizal": "Rizal"}
N_BOOT = 200
MIN_EFFECT = 0.05
SENTENCE = {
    "poverty": ("Higher poverty and food-poverty levels mean more households may lack the money for enough food.",
                "Lower poverty levels mean fewer households are likely to lack the money for enough food."),
    "market": ("Recent food-price changes make basic food less affordable for households.",
               "Recent food-price changes have not added pressure on household food budgets."),
    "climate": ("Recent weather, typhoons or harvests may weaken local food supply and farm incomes.",
                "Recent weather and harvests have not added pressure on local food supply."),
    "history": ("Earlier food-security surveys found this area at or above the national level of food insecurity.",
                "Earlier food-security surveys found this area below the national level of food insecurity."),
}
FAO = {"poverty": "access and vulnerability (ability to cope)", "market": "access (affordability) and stability",
       "climate": "availability and stability", "history": "measured outcome history (HFIAS)",
       "geography": "island group (Luzon/Visayas/Mindanao), a geographic covariate"}
SENTENCE["geography"] = ("Provinces in this island group have tended to show higher measured food insecurity.",
                         "Provinces in this island group have tended to show lower measured food insecurity.")


def _q(d: pd.Timestamp) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


CLAIM = ("Structural relative-risk estimate for the display quarter, issued with information public before the issue date. "
         "Its only out-of-time evidence is survey-to-survey (train 2015 + 2018, predict the 2019 provincial round; development "
         "data). No quarterly provincial food-insecurity measurement exists, so quarter-to-quarter change is NOT validated.")
GROUP_OF = {f: g for g, fs in {"poverty": M.M9.POV + M.M9.DENS, "market": M.M9.MKT, "climate": M.M9.CLI,
                                "history": M.M9.HIST, "geography": ["island_code"]}.items() for f in fs}


def contributions(final, Z: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Group contributions to the predicted relative logit. Constant-leaf trees (GBC): exact TreeSHAP, which sums with
    the base value to the model's prediction. Linear trees have no TreeSHAP, so they are not served with explanations."""
    m = final.chosen_
    if m.kind != "GBC":
        raise NotImplementedError("linear-tree explanations would be approximate; not served")
    c = pd.DataFrame(m.m_.booster_.predict(Z[m.cols], pred_contrib=True), columns=m.cols + ["base"], index=Z.index)
    g = pd.DataFrame({grp: c[[f for f in m.cols if GROUP_OF[f] == grp]].sum(axis=1)
                      for grp in dict.fromkeys(GROUP_OF[f] for f in m.cols)}, index=Z.index)
    g["base"] = c["base"] + m.mu_
    return g, "exact TreeSHAP (sums with the base value to the predicted relative logit)"


STATUS = "CANDIDATE - rejected by its gate (E140 decision C); validation pending; not a released forecast"


def issue_candidate(X: pd.DataFrame, model_id: str, out_dir, claim: str, status: str,
                    issue: pd.Timestamp | None = None) -> dict:
    """Fit LGBM-AUTO on the measured rows X, issue the display-quarter estimate for every province, the 142 LGU
    priority ranking, a write-once seal and its prospective-register record. Shared by E140 and E141."""
    if issue is None:                                        # dashboard rule: issue at the start of the viewing quarter
        issue = pd.Timestamp(forecast_target()["origin"])
    final = M.make("LGBM-AUTO").fit(X)
    Z = LV.build(issue, write=False)
    isl = O.load().assign(k=lambda d: d["key"].str.replace(" ", "")).drop_duplicates("k").set_index("k")["island"]
    Z["island_code"] = Z["k"].map(isl).map(M.ISLAND).astype(float)
    Z["p_elevated"] = final.predict_proba(Z)
    Z["y_hat"] = final.predict_y(Z)
    contrib, method = contributions(final, Z)
    if not np.allclose(contrib.sum(axis=1), Z["y_hat"]):
        raise RuntimeError("explanations do not add up to the prediction")
    rng = np.random.default_rng(M.SEED)
    regs = X["region"].unique()
    cal = Z[Z["k"].isin(CAL)].reset_index()
    B = np.asarray([M.make("LGBM-AUTO").fit(pd.concat([X[X["region"] == r] for r in rng.choice(regs, len(regs))])
                                             .reset_index(drop=True)).predict_proba(cal) for _ in range(N_BOOT)])
    target = issue + pd.DateOffset(months=3)
    provinces = []
    for i, r in cal.iterrows():
        e = contrib.loc[r["index"]].drop("base")
        lo, hi = float(np.percentile(B[:, i], 5)), float(np.percentile(B[:, i], 95))
        provinces.append({
            "province": CAL[r["k"]], "target_quarter": _q(target), "p_elevated": round(float(r["p_elevated"]), 4),
            "p_interval90": [round(lo, 4), round(hi, 4)],
            "risk_class": "HIGH" if lo >= 0.5 else "LOW" if hi < 0.5 else "UNCERTAIN",
            "explanations": [{"group": g, "fao_dimension": FAO[g], "contribution_logit": round(float(v), 3),
                              "sentence": (SENTENCE[g][0 if v > 0 else 1] if abs(v) >= MIN_EFFECT
                                           else "This factor did not noticeably change the estimate.")}
                             for g, v in e.items()],
            "base_logit": round(float(contrib.loc[r["index"], "base"]), 3),
            "not_model_inputs": {"employment_remittances": "no provincial series for the training years",
                                 "news_nlp": "CALABARZON-only archive; regional context",
                                 "utilization": "no nutrition, water or sanitation data held"}})
    rank_first = pd.Series([CAL[cal["k"][j]] for j in B.argmax(axis=1)]).value_counts(normalize=True).round(3).to_dict()
    out = {"model": f"{model_id} (LGBM-AUTO, trained on {len(X)} measured HFIAS rows)",
           "validation_status": status,
           "claim": claim, "issue_date": issue.date().isoformat(), "issue_quarter": _q(issue),
           "information_cutoff": f"{issue.date().isoformat()} (exclusive)", "target_quarter": _q(target), "display_lead": 1,
           "final_model": {"kind": final.kind_, "n_trees": int(final.n_trees_), "sigma": float(final.chosen_.sigma_)},
           "explanation_method": method,
           "interval_note": "model-refit uncertainty (16-region bootstrap, 200 refits); excludes survey sampling error and "
                            "temporal change, so it understates the total uncertainty",
           "class_rule": "HIGH if the whole 90 % interval is >= 0.5, LOW if it is < 0.5, otherwise UNCERTAIN",
           "meaning": "Estimated probability that the province's household food insecurity (HFIAS moderate-or-severe) is above "
                      "the national level. A risk estimate: HIGH does not confirm food insecurity and LOW does not guarantee "
                      "food security. It is not the share of food-insecure households.",
           "provinces": provinces, "p_rank_first": rank_first}
    lg = pd.read_csv(BACKEND_DIR / "data" / "fi5" / "out" / "lgu_rankings.csv")
    lg = lg[["province_name", "lgu_psgc", "lgu_name", "lgu_type", "population_2024", "poverty_incidence_2021", "poverty_source",
             "density_2024", "pct_poverty", "pct_density", "vulnerability"]].copy()
    pm = {p["province"]: p for p in provinces}
    lg["province_p_elevated"] = lg["province_name"].map(lambda n: pm[n]["p_elevated"])
    lg["priority_score"] = lg["province_p_elevated"] * lg["vulnerability"]
    lg["priority_score_low"] = lg["province_name"].map(lambda n: pm[n]["p_interval90"][0]) * lg["vulnerability"]
    lg["priority_score_high"] = lg["province_name"].map(lambda n: pm[n]["p_interval90"][1]) * lg["vulnerability"]
    lg["priority_rank_in_region"] = lg["priority_score"].rank(ascending=False, method="min").astype(int)
    lg["target_quarter"] = _q(target)
    lg["status"] = "candidate ranking pending provincial forecast validation"
    lg["label"] = ("LGU vulnerability-weighted priority ranking derived from the provincial candidate estimate; not a municipal "
                   "food-insecurity measurement or classification")
    lg.sort_values("priority_rank_in_region").to_csv(out_dir / "lgus_next_quarter.csv", index=False)
    seal = {"model": out["model"], "issue_date": out["issue_date"], "target": "HFIAS/FIES moderate-or-severe above national, next provincial round",
            "predictions": Z[["k", "p_elevated"]].round(5).to_dict(orient="records"), "sealed_utc": datetime.now(timezone.utc).isoformat()}
    sp = out_dir / f"sealed_prediction_{out['issue_date']}.json"
    if not sp.exists():                       # one seal per issue date: the first issue is the prospective record
        sp.write_text(json.dumps(seal, indent=1, sort_keys=True))
    sha = hashlib.sha256(sp.read_text().encode()).hexdigest()      # LF-normalised text, as for the E138/E139 seals
    PP.register(model_id, sp, sha, out["issue_date"])
    out["sealed_prediction_sha256"] = sha
    (out_dir / "forecast_next_quarter.json").write_text(json.dumps(out, indent=2))
    return out


def run(issue: pd.Timestamp | None = None) -> dict:
    return issue_candidate(M.data(lead=1), "e140-lgbm-native-1.0", OUT, CLAIM, STATUS, issue)


if __name__ == "__main__":
    o = run()
    print(o["target_quarter"], o["final_model"], o["p_rank_first"])
    for p in o["provinces"]:
        print(p["province"], p["p_elevated"], p["p_interval90"], p["risk_class"], [(e["group"], e["contribution_logit"]) for e in p["explanations"]])
