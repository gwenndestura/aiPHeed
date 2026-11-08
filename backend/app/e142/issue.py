"""
E142 provincial candidate issue: the risk-state model (STATE-LGBM) fitted on all 203 measured province-rounds, issued
for the dashboard's display quarter (viewing quarter + 1, issued at the start of the viewing quarter).

    python -m app.e142.issue    -> data/e142/out/issue/{forecast_next_quarter.json, lgus_next_quarter.csv,
                                   sealed_prediction_<issue>.json} + provincial prospective register record

Per province: relative-logit forecast y_hat = mu(x at issue) + phi^h x m0, variance V (grows with h, the quarters since
the province's last measured round), P(elevated) = Phi(y_hat / sqrt(V)), a 90 % predictive interval of the relative
logit, and an exact decomposition: TreeSHAP of mu by group (constant-leaf trees) + the decayed survey-anchor term.
Class (candidate display): HIGH if P >= 0.80 and the model-refit range is >= 0.5; LOW if P <= 0.20 and the range is < 0.5;
otherwise UNCERTAIN.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e137 import outcomes as O
from app.e139 import live as LV
from app.e140 import issue as I140
from app.e140 import model as M140
from app.e141 import panel as P
from app.e142 import OUT
from app.e142 import model as M
from app.quarterly.target import forecast_target
from app.registry import prospective_provincial as PP

MODEL_ID = "e142-state-lgbm-1.0"
STATUS = "CANDIDATE - E142 gate not passed (S1, S2, S3); validation pending; not a released forecast"
CLAIM = ("Forecast of the province's relative food-insecurity risk in the target quarter from a survey-anchored risk-state "
         "model: a LightGBM structural level from indicators, pulled toward the province's last measured HFIAS round with "
         "a weight that decays with the quarters since that survey (persistence estimated from measured survey-to-survey "
         "transitions). Validated survey-to-survey only (development); the quarterly transition form is an assumption and "
         "quarter-to-quarter change is NOT validated.")
HIGH, LOW = 0.80, 0.20
N_BOOT = 30                  # region-bootstrap refits for the model-refit range of P (LGU intervals)


def _q(t: pd.Timestamp) -> str:
    return f"{t.year}-Q{(t.month - 1) // 3 + 1}"


def run(issue: pd.Timestamp | None = None) -> dict:
    if issue is None:
        issue = pd.Timestamp(forecast_target()["origin"])
    target = issue + pd.DateOffset(months=3)
    X = P.data(1)
    sm = M.StateModel("lgbm").fit(X)
    Z = LV.build(issue, write=False)
    isl = O.load().assign(k=lambda d: d["key"].str.replace(" ", "")).drop_duplicates("k").set_index("k")["island"]
    Z["island_code"] = Z["k"].map(isl).map(M140.ISLAND).astype(float)
    last = X.sort_values("round").groupby("key").last().reset_index()
    last["k"] = last["key"].str.replace(" ", "")
    last = last.set_index("k").reindex(Z["k"])
    tq = target.year * 4 + (target.month - 1) // 3
    h = (tq - last["survey"].map(M.ROUND_QUARTER)).values.astype(float)
    Zp = Z.copy()
    Zp["prev_y"], Zp["prev_se_y"] = last["y"].values, last["se_y"].values
    yhat, V = sm.predict(Zp, prev_rows=last.reset_index(drop=True).set_index(Z.index), h=h)
    p = norm.cdf(yhat / np.sqrt(V))
    mu = sm._mu(Z)
    anchor = yhat - mu
    mm = sm.mu_model_.chosen_
    if mm.kind != "GBC":
        raise NotImplementedError("linear-tree level: explanations would be approximate; not served")
    c = pd.DataFrame(mm.m_.booster_.predict(Z[mm.cols], pred_contrib=True), columns=mm.cols + ["base"], index=Z.index)
    groups = {f: g for g, fs in {"poverty": M140.M9.POV + M140.M9.DENS, "market": M140.M9.MKT, "climate": M140.M9.CLI,
                                  "geography": ["island_code"]}.items() for f in fs}
    G = pd.DataFrame({g: c[[f for f in mm.cols if groups[f] == g]].sum(axis=1) for g in dict.fromkeys(groups[f] for f in mm.cols)})
    G["history"] = anchor
    base = c["base"] + mm.mu_
    if not np.allclose(G.sum(axis=1) + base, yhat):
        raise RuntimeError("explanations do not add up to the forecast")
    cal = Z.index[Z["k"].isin(I140.CAL)]
    rng = np.random.default_rng(20261105)
    regs = X["region"].unique()
    B = []
    for _ in range(N_BOOT):
        Xb = pd.concat([X[X["region"] == r] for r in rng.choice(regs, len(regs))]).reset_index(drop=True)
        mb = M.StateModel("lgbm").fit(Xb)
        yb, Vb = mb.predict(Zp.loc[cal], prev_rows=last.reset_index(drop=True).set_index(Z.index).loc[cal], h=h[cal])
        B.append(norm.cdf(yb / np.sqrt(Vb)))
    B = np.asarray(B)
    provinces = []
    for j, i in enumerate(cal):
        lo, hi = yhat[i] - 1.645 * np.sqrt(V[i]), yhat[i] + 1.645 * np.sqrt(V[i])
        provinces.append({
            "province": I140.CAL[Z.at[i, "k"]], "target_quarter": _q(target), "p_elevated": round(float(p[i]), 4),
            "relative_logit_forecast": round(float(yhat[i]), 3), "relative_logit_interval90": [round(float(lo), 3), round(float(hi), 3)],
            "p_interval90": [round(float(np.percentile(B[:, j], 5)), 4), round(float(np.percentile(B[:, j], 95)), 4)],
            "risk_class": ("HIGH" if p[i] >= HIGH and np.percentile(B[:, j], 5) >= 0.5 else
                           "LOW" if p[i] <= LOW and np.percentile(B[:, j], 95) < 0.5 else "UNCERTAIN"),
            "last_measured_round": last.at[Z.at[i, "k"], "survey"], "quarters_since_last_survey": int(h[i]),
            "weight_on_last_survey": round(float(sm.phi_ ** h[i]), 3),
            "explanations": [{"group": g, "fao_dimension": I140.FAO[g], "contribution_logit": round(float(v), 3),
                              "sentence": (I140.SENTENCE[g][0 if v > 0 else 1] if abs(v) >= I140.MIN_EFFECT
                                           else "This factor did not noticeably change the estimate.")}
                             for g, v in G.loc[i].items()],
            "base_logit": round(float(base[i]), 3),
            "not_model_inputs": {"employment_remittances": "no provincial series for the survey years",
                                 "news_nlp": "FSSI v2 exists for CALABARZON only; not testable as a provincial input",
                                 "utilization": "no nutrition, water or sanitation data held"}})
    out = {"model": f"{MODEL_ID} (risk-state; LightGBM structural level, {sm.mu_model_.n_trees_} trees; phi {sm.phi_} per quarter)",
           "validation_status": STATUS, "claim": CLAIM, "issue_date": issue.date().isoformat(), "issue_quarter": _q(issue),
           "information_cutoff": f"{issue.date().isoformat()} (exclusive)", "target_quarter": _q(target), "display_lead": 1,
           "final_model": {"phi_per_quarter": sm.phi_, "tau2": sm.tau2_, "n_transitions": sm.n_transitions_,
                           "level_kind": mm.kind, "level_trees": int(sm.mu_model_.n_trees_)},
           "explanation_method": "exact: TreeSHAP of the structural level by group + the decayed survey-anchor term (history)",
           "class_rule": f"HIGH if P >= {HIGH} and the whole model-refit range is >= 0.5; LOW if P <= {LOW} and the whole "
                         "model-refit range is < 0.5; otherwise UNCERTAIN (P includes the full predictive variance)",
           "interval_note": f"p_interval90 = model-refit range ({N_BOOT} region-bootstrap refits); relative_logit_interval90 = "
                            "predictive interval of the province's relative logit (state uncertainty, grows with time since survey)",
           "meaning": "Estimated probability that the province's household food insecurity (HFIAS moderate-or-severe) is above "
                      "the national level in the target quarter. A risk estimate: HIGH does not confirm food insecurity and LOW "
                      "does not guarantee food security. It is not the share of food-insecure households.",
           "provinces": provinces}
    out_dir = OUT / "issue"
    out_dir.mkdir(parents=True, exist_ok=True)
    I140.lgu_priority(provinces, _q(target), out_dir)
    seal = {"model": out["model"], "issue_date": out["issue_date"], "target": "HFIAS/FIES moderate-or-severe above national, next provincial round",
            "predictions": [{"k": k, "p_elevated": round(float(v), 5)} for k, v in zip(Z["k"], p)],
            "sealed_utc": datetime.now(timezone.utc).isoformat()}
    sp = out_dir / f"sealed_prediction_{out['issue_date']}.json"
    if not sp.exists():
        sp.write_text(json.dumps(seal, indent=1, sort_keys=True))
    sha = hashlib.sha256(sp.read_text().encode()).hexdigest()
    PP.register(MODEL_ID, sp, sha, out["issue_date"])
    out["sealed_prediction_sha256"] = sha
    (out_dir / "forecast_next_quarter.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    o = run()
    print(o["target_quarter"], o["final_model"])
    for q in o["provinces"]:
        print(q["province"], q["p_elevated"], q["relative_logit_interval90"], q["risk_class"], q["last_measured_round"],
              q["quarters_since_last_survey"], q["weight_on_last_survey"], [(e["group"], e["contribution_logit"]) for e in q["explanations"]])
