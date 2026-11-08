"""
E143 provincial candidate issue for the dashboard's display quarter (viewing quarter + 1, issued at the start of the
viewing quarter with information published before it).

    python -m app.e143.issue   -> data/e143/out/issue/{forecast_next_quarter.json, lgus_next_quarter.csv,
                                  sealed_prediction_<issue>_{re,hre}.json} + two provincial register records

Primary output: C2 RE-LGBM-X (protocol section 6: no candidate was adopted, so C2 is issued). C1, C3, C4 and E142 are
reported for every province as model-selection spread. Per province:
  P(elevated) = Phi(y_hat / sqrt(V)); refit range (30 region-bootstrap refits); exact explanation
  (TreeSHAP of the cross-fitted level by group + measured-survey anchor); variance decomposition.
Class (stricter than E142): HIGH if P >= 0.80, the whole refit range >= 0.5 and every candidate model >= 0.5;
LOW symmetrically below 0.20 / 0.5; otherwise UNCERTAIN.
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
from app.e142 import model as M142
from app.e143 import OUT
from app.e143 import model as M
from app.quarterly.target import forecast_target
from app.registry import prospective_provincial as PP

IDS = {"C2 RE-LGBM-X": "e143-re-lgbm-1.0", "C4 HRE-LGBM-X": "e143-hre-lgbm-1.0"}
PRIMARY = "C2 RE-LGBM-X"
STATUS = ("CANDIDATE - E143 gate not passed (S1, S2: not better than persistence or the region's previous level with "
          "Holm-adjusted confidence); validation pending; not a released forecast")
CLAIM = ("Estimated relative food-insecurity risk of the province in the target quarter: an indicator-based structural "
         "level (LightGBM, trained without the province's own region) plus the province's measured HFIAS history, "
         "weighted by how strongly measured deviations persisted between survey rounds (a permanent province component; "
         "no time decay is identified). Validated survey-to-survey only, on re-used development folds; the "
         "quarter-to-quarter change is NOT validated, because no quarterly provincial measurement exists.")
HIGH, LOW, N_BOOT = 0.80, 0.20, 30
FAO_GROUPS = {"poverty": M140.M9.POV + M140.M9.DENS, "market": M140.M9.MKT, "climate": M140.M9.CLI, "geography": ["island_code"]}


def _q(t: pd.Timestamp) -> str:
    return f"{t.year}-Q{(t.month - 1) // 3 + 1}"


def _frame(issue, X):
    Z = LV.build(issue, write=False)
    ref = X.assign(k=X["key"].str.replace(" ", "")).drop_duplicates("k").set_index("k")
    Z["key"], Z["region"], Z["province"] = Z["k"].map(ref["key"]), Z["k"].map(ref["region"]), Z["k"].map(ref["province"])
    isl = O.load().assign(k=lambda d: d["key"].str.replace(" ", "")).drop_duplicates("k").set_index("k")["island"]
    Z["island_code"] = Z["k"].map(isl).map(M140.ISLAND).astype(float)
    return Z


def _fit(X):
    lv = {"lgbm": M.Level("lgbm").fit(X), "ridge": M.Level("ridge").fit(X)}
    return {c: M.Anchored(f, l).fit(X, lv[l]) for c, (f, l) in M.CANDIDATES.items()}


def _explain(m, Z, i, yhat_i):
    """Exact: base + TreeSHAP of the fold model that produced the province's level + anchor."""
    regs = [(r, fm) for r, fm in m.lv_.folds_ if Z.at[i, "region"] in r]
    fm = regs[0][1] if regs else m.lv_.full_
    ch = fm.chosen_
    row = Z.loc[[i]]
    if ch.kind != "GBC":
        return None, ch.kind
    c = pd.DataFrame(ch.m_.booster_.predict(row[ch.cols], pred_contrib=True), columns=ch.cols + ["base"])
    g = {f: grp for grp, fs in FAO_GROUPS.items() for f in fs}
    out = {grp: float(c[[f for f in ch.cols if g[f] == grp]].sum(axis=1).iloc[0]) for grp in dict.fromkeys(g[f] for f in ch.cols)}
    out["history (measured HFIAS rounds)"] = float(m.last_detail_.loc[i, "anchor"])
    base = float(c["base"].iloc[0] + ch.mu_)
    if abs(base + sum(out.values()) - yhat_i) > 1e-6:
        raise RuntimeError("explanation does not add up to the forecast")
    return {"base_logit": base, "groups": out}, "GBC"


def _var_parts(m, key, region, tq):
    """C2/C4 variance decomposition (relative-logit scale)."""
    t2, sA = m.tau2_, m.sA_
    _, expl, _, n = m._one(key, region, tq)
    own, oth = m._past(key, region, tq)
    save = m.tr_.copy()
    m.tr_.loc[m.tr_["key"].isin(own["key"]) | m.tr_["key"].isin(oth["key"]), "se_y"] = 0.0
    _, expl0, _, _ = m._one(key, region, tq)
    m.tr_ = save
    return {"total_V": t2 - expl, "transitory_round_shock_sigma2_b": t2 - sA,
            "permanent_component_uncertainty": sA - expl,
            "of_which_survey_error_of_anchoring_rounds": max(0.0, expl0 - expl),
            "of_which_finite_number_of_rounds": max(0.0, sA - expl0),
            "note": "tau2 is estimated from out-of-fold deviations, so the structural level's out-of-sample error is "
                    "inside these components; parameter and model-selection uncertainty are reported separately"}


def run(issue: pd.Timestamp | None = None) -> dict:
    if issue is None:
        issue = pd.Timestamp(forecast_target()["origin"])
    target = issue + pd.DateOffset(months=3)
    tq = target.year * 4 + (target.month - 1) // 3
    X = P.data(1)
    Z = _frame(issue, X)
    models = _fit(X)
    pred = {}
    for c, m in models.items():
        yh, V = m.predict(Z, target_q=tq)
        pred[c] = {"yhat": yh, "V": V, "p": norm.cdf(yh / np.sqrt(V)), "detail": m.last_detail_.copy()}
    e142 = M142.StateModel("lgbm").fit(X)
    last = X.sort_values("round").groupby("key").last().reindex(Z["key"]).reset_index()
    Zp = Z.assign(prev_y=last["y"].values, prev_se_y=last["se_y"].values)
    h142 = (tq - last["survey"].map(M142.ROUND_QUARTER)).values.astype(float)
    y142, V142 = e142.predict(Zp, prev_rows=last.set_index(Z.index), h=h142)
    p142 = norm.cdf(y142 / np.sqrt(V142))
    cal = Z.index[Z["k"].isin(I140.CAL)]
    rng = np.random.default_rng(20261108)
    # parameter uncertainty CONDITIONAL on the target provinces' own measurements: CALABARZON's measured rows are kept
    # in every refit (they are the anchoring data, not a sampling unit of the parameters); the other regions are
    # resampled with replacement
    target_region = "CALABARZON"
    regs = [r for r in X["region"].unique() if r != target_region]
    B = {c: [] for c in IDS}
    for _ in range(N_BOOT):
        Xb = pd.concat([X[X["region"] == target_region]] + [X[X["region"] == r] for r in rng.choice(regs, len(regs))]).reset_index(drop=True)
        lb = M.Level("lgbm").fit(Xb)
        for c in IDS:
            f, _l = M.CANDIDATES[c]
            B[c].append(M.Anchored(f, "lgbm").fit(Xb, lb).predict_proba(Z.loc[cal], target_q=tq))
    B = {c: np.asarray(v) for c, v in B.items()}
    provinces = []
    for j, i in enumerate(cal):
        key, reg = Z.at[i, "key"], Z.at[i, "region"]
        own = X[X["key"] == key].sort_values("round")
        prim = pred[PRIMARY]
        p = float(prim["p"][i])
        lo, hi = (float(np.percentile(B[PRIMARY][:, j], q)) for q in (5, 95))
        spread = {c: round(float(pred[c]["p"][i]), 4) for c in pred} | {"E142 STATE-LGBM": round(float(p142[i]), 4)}
        cands = [pred[c]["p"][i] for c in M.CANDIDATES]
        cls = ("HIGH" if p >= HIGH and lo >= 0.5 and min(cands) >= 0.5 else
               "LOW" if p <= LOW and hi < 0.5 and max(cands) < 0.5 else "UNCERTAIN")
        ex, kind = _explain(models[PRIMARY], Z, i, float(prim["yhat"][i]))
        sd = float(np.sqrt(prim["V"][i]))
        provinces.append({
            "province": Z.at[i, "province"], "issue_quarter": _q(issue), "target_quarter": _q(target),
            "output_type": "candidate next-quarter estimate of relative risk (NOT a validated forecast)",
            "p_elevated": round(p, 4), "p_refit_range90": [round(lo, 4), round(hi, 4)],
            "relative_logit": round(float(prim["yhat"][i]), 3),
            "relative_logit_interval90": [round(float(prim["yhat"][i]) - 1.645 * sd, 3), round(float(prim["yhat"][i]) + 1.645 * sd, 3)],
            "risk_class": cls,
            "measured_rounds": [{"survey": r["survey"], "relative_logit": round(float(r["y"]), 3), "se": round(float(r["se_y"]), 3),
                                 "status": r["status"]} for _, r in own.iterrows()],
            "last_direct_survey": own["survey"].iloc[-1] if len(own) else None,
            "quarters_since_last_survey": int(tq - M142.ROUND_QUARTER[own["survey"].iloc[-1]]) if len(own) else None,
            "structural_level_logit": round(float(prim["detail"].loc[i, "level"]), 3),
            "survey_anchor_logit": round(float(prim["detail"].loc[i, "anchor"]), 3),
            "weight_on_own_surveys": round(float(prim["detail"].loc[i, "weight_on_own_surveys"]), 3),
            "explanation": ex, "explanation_level_kind": kind,
            "model_selection_spread": spread,
            "hierarchical_C4_refit_range90": [round(float(np.percentile(B["C4 HRE-LGBM-X"][:, j], 5)), 4),
                                              round(float(np.percentile(B["C4 HRE-LGBM-X"][:, j], 95)), 4)],
            "transition_form": {"C2 permanent component: weight on own surveys": round(float(pred["C2 RE-LGBM-X"]["detail"].loc[i, "weight_on_own_surveys"]), 3),
                                "C1 AR(1): weight on last survey": round(float(pred["C1 STATE-LGBM-X"]["detail"].loc[i, "weight_on_own_surveys"]), 3)},
            "variance_decomposition": _var_parts(models[PRIMARY], key, reg, tq),
            "not_model_inputs": {"employment_remittances": "no provincial series for the survey years",
                                 "news_nlp": "FSSI v2 exists for CALABARZON only (95 % one outlet); not testable as a provincial input",
                                 "utilization": "no nutrition, water or sanitation data held"},
            "validation_status": STATUS})
    out = {"model": f"{IDS[PRIMARY]} ({PRIMARY}; c {models[PRIMARY].c_:.3f}, tau2 {models[PRIMARY].tau2_:.3f})",
           "validation_status": STATUS, "claim": CLAIM, "issue_date": issue.date().isoformat(), "issue_quarter": _q(issue),
           "information_cutoff": f"{issue.date().isoformat()} (exclusive)", "target_quarter": _q(target), "display_lead": 1,
           "final_model": {c: {"tau2": m.tau2_, "c": m.c_, "sigma2_A": m.sA_, "sigma2_G": m.sG_, "phi": m.phi_}
                           for c, m in models.items()},
           "class_rule": f"HIGH if P >= {HIGH}, the whole refit range >= 0.5 and every candidate model >= 0.5; LOW if "
                         f"P <= {LOW}, the whole refit range < 0.5 and every candidate model < 0.5; otherwise UNCERTAIN",
           "meaning": "Estimated probability that the province's household food insecurity (HFIAS moderate-or-severe) is above "
                      "the national level in the target quarter. A risk estimate: HIGH does not confirm food insecurity and LOW "
                      "does not guarantee food security. It is not the share of food-insecure households.",
           "concepts": {"directly_measured": "measured_rounds (FNRI HFIAS)", "estimated_current_relative_risk": "relative_logit",
                        "latent_state": "structural_level_logit + survey_anchor_logit",
                        "next_quarter_forecast": "p_elevated for target_quarter (candidate; the quarterly change is assumed, not validated)",
                        "independently_validated_future_prediction": "none yet (prospective register, awaiting a provincial round after 2019)",
                        "lgu_priority": "lgus_next_quarter.csv (vulnerability-weighted priority, not a municipal measurement)"},
           "provinces": provinces}
    out_dir = OUT / "issue"
    out_dir.mkdir(parents=True, exist_ok=True)
    I140.lgu_priority([{"province": q["province"], "p_elevated": q["p_elevated"], "p_interval90": q["p_refit_range90"],
                        "risk_class": q["risk_class"]} for q in provinces], _q(target), out_dir)
    out["seals"] = {}
    for c, mid in IDS.items():
        seal = {"model": f"{mid} ({c})", "issue_date": out["issue_date"],
                "target": "HFIAS moderate-or-severe above national, next provincial round",
                "predictions": [{"k": k, "p_elevated": round(float(v), 5)} for k, v in zip(Z["k"], pred[c]["p"])],
                "sealed_utc": datetime.now(timezone.utc).isoformat()}
        sp = out_dir / f"sealed_prediction_{out['issue_date']}_{c.split()[1].split('-')[0].lower()}.json"
        if not sp.exists():
            sp.write_text(json.dumps(seal, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
        sha = hashlib.sha256(sp.read_text(encoding="utf-8").encode()).hexdigest()
        PP.register(mid, sp, sha, out["issue_date"])
        out["seals"][mid] = sha
    (out_dir / "forecast_next_quarter.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8", newline="\n")
    return out


if __name__ == "__main__":
    o = run()
    for q in o["provinces"]:
        print(q["province"], q["p_elevated"], q["p_refit_range90"], q["risk_class"], q["last_direct_survey"],
              q["quarters_since_last_survey"], q["weight_on_own_surveys"], q["model_selection_spread"], q["explanation_level_kind"])
