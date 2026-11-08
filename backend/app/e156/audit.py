"""
E156 audit of the E151 required model (GNT) at Lead 1. No model is selected here; these are checks.

1. Leakage: every input dated at or after the issue quarter is replaced with noise; the forecasts must not change.
2. Effective sample size: how many independent rows the 72 are worth, given errors shared within a round and region.
3. Province-held-out: the LightGBM adjustment refitted without any row of the province being forecast.
4. Employment and remittances: why they carry almost no weight.
5. All-LOW: what drives the five CALABARZON forecasts.
6. Threshold sensitivity, reported only; the 50 line is not changed.
7. Feature-usage table: every input, its group, scope, missingness, and whether it reaches the model.

    python -m app.e156.audit -> data/e156/out/audit.json, feature_usage.csv
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import OUT as O51
from app.e151 import prov as Pv
from app.e151.issue import group_of
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
OUT = BACKEND_DIR / "data" / "e156" / "out"
SCOPE = {"market": "province (PSA CPI, monthly)", "climate": "province; ONI national", "employment": "national; regional annual from 2021", "remittance": "national", "poverty": "province, by PSA round", "news": "province, area or national stream", "h2_quarterly_signal": "SWS area model applied to province inputs", "state": "survey timing"}


def setup(survey, corrupt=False, seed=0):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - 1
    if corrupt:
        r = np.random.default_rng(seed)
        g = S.s8.gov
        fut = g.index.get_level_values("qi") > i
        num = g.select_dtypes("number").columns
        g.loc[fut, num] = r.normal(size=(int(fut.sum()), len(num))) * 50
        S.s8.gov = g
        c = S.cpi
        fc = c.index.get_level_values("qi") > i
        cn = c.select_dtypes("number").columns
        c.loc[fc, cn] = r.normal(size=(int(fc.sum()), len(cn))) * 50
        S.cpi = c
        p = S.P.reset_index()
        fp = p["qi"] > i
        pn = [x for x in p.select_dtypes("number").columns if x not in ("qi", "lag_m")]
        p.loc[fp, pn] = r.normal(size=(int(fp.sum()), len(pn))) * 50
        S.P = p.set_index(["stream", "qi"]).sort_index()
        S.h2 = {k: (v if k[1] <= i else float(r.normal() * 50)) for k, v in S.h2.items()}
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey])).reset_index(drop=True)
    tr = Pv.add_inputs(S, P.tr).reset_index(drop=True)
    base, _ = P.hier.predict(te, te["T"].values)
    return S, P, tr, te, base


def gnt(survey, corrupt=False, seed=0):
    S, P, tr, te, base = setup(survey, corrupt, seed)
    m = Pv.Res2(Pv.GNT_COLS).fit(tr)
    return te[["key", "survey"]].assign(mu=base + m.predict(te), base=base)


def province_out(survey):
    S, P, tr, te, base = setup(survey)
    out = []
    for k in te["key"].unique():
        m = Pv.Res2(Pv.GNT_COLS).fit(tr[tr["key"] != k])
        sd, _, _ = m.scale(te["gap_q"].values)
        x = te[te["key"] == k]
        b = base[te["key"].values == k]
        mu = b + m.predict(x)
        out.append(pd.DataFrame({"key": k, "survey": survey, "mu_ho": mu, "p_ho": norm.cdf(mu / sd[: len(mu)])}))
    return pd.concat(out)


def usage(survey="ENNS2021"):
    S, P, tr, te, base = setup(survey)
    m = Pv.Res2(Pv.GNT_COLS).fit(tr)
    C = np.abs(m.m_.booster_.predict(tr[m.use_], pred_contrib=True)[:, :-1]).mean(axis=0)
    shap = dict(zip(m.use_, C))
    rows = []
    for c in Pv.GNT_COLS:
        g = group_of(c)
        v = tr[c] if c in tr else pd.Series(dtype=float)
        rows.append({"feature": c, "group": g, "scope": SCOPE.get(g, ""), "missing_share_train": round(float(v.isna().mean()), 3) if len(v) else 1.0, "distinct_values_train": int(v.nunique()), "same_for_all_provinces_in_a_quarter": bool(tr.groupby("i")[c].nunique().max() <= 1) if c in tr else None, "reaches_model": c in m.use_, "mean_abs_shap": round(float(shap.get(c, 0.0)), 5)})
    U = pd.DataFrame(rows)
    # employment and remittances: how much of their variation is just time, and how many distinct issue quarters training has
    emp = [c for c in M.GROUPS["employment"] + M.GROUPS["remittance"] if c in tr]
    diag = {"training_rows": int(len(tr)), "distinct_issue_quarters": int(tr["i"].nunique()), "distinct_surveys": int(tr["survey"].nunique())}
    for c in emp:
        x = tr[[c, "i", "survey", "lead", "e"]].dropna()
        if len(x) > 10:
            diag[c] = {"distinct_values": int(x[c].nunique()), "share_variance_explained_by_issue_quarter": round(float(1 - x.groupby("i")[c].transform(lambda s: s - s.mean()).var() / max(1e-12, x[c].var())), 3), "corr_with_survey_error": round(float(np.corrcoef(x[c], x["e"])[0, 1]), 3)}
    return U, diag


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    F = pd.read_csv(O51 / "prov_oof.csv")
    x = F[F["lead"] == 1].reset_index(drop=True)
    res = {"model": "E151 required (GNT), Lead 1, 72 rows", "commit_at_start": "44531bcb on pfi/e151-news-quarterly"}
    # 1. leakage
    base = pd.concat(Parallel(n_jobs=3)(delayed(gnt)(s) for s in ("ENNS2018", "ENNS2019", "ENNS2021")))
    bad = pd.concat(Parallel(n_jobs=3)(delayed(gnt)(s, True, 7) for s in ("ENNS2018", "ENNS2019", "ENNS2021")))
    d = (base["mu"].values - bad["mu"].values)
    res["leakage_future_inputs_corrupted"] = {"rows": int(len(d)), "max_abs_change_logit": float(np.max(np.abs(d))), "rows_changed_over_1e-9": int((np.abs(d) > 1e-9).sum()), "pass": bool(np.max(np.abs(d)) < 1e-9)}
    # 2. effective sample size from error sharing
    x["err"] = x["mu_GNT"] - x["y_true"]
    tot = x["err"].var()
    icc_round = x.groupby("survey")["err"].transform("mean").var() / tot
    icc_reg = x.groupby(["survey", "region"])["err"].transform("mean").var() / tot
    n_reg = x.groupby(["survey", "region"]).size().mean()
    res["effective_sample_size"] = {"rows": 72, "share_of_error_variance_shared_in_round": round(float(icc_round), 3), "share_shared_in_round_and_region": round(float(icc_reg), 3), "mean_rows_per_round_region": round(float(n_reg), 2), "effective_n_approx": round(float(72 / (1 + (n_reg - 1) * max(0.0, icc_reg))), 1), "independent_rounds": 3,
                                    "accuracy_95_range_at_effective_n": None}
    ne = res["effective_sample_size"]["effective_n_approx"]
    p = float(((x["GNT"] >= .5) == (x["y_high"] == 1)).mean())
    res["effective_sample_size"]["accuracy_95_range_at_effective_n"] = [round(p - 1.96 * np.sqrt(p * (1 - p) / ne), 3), round(p + 1.96 * np.sqrt(p * (1 - p) / ne), 3)]
    # 3. province held out
    H = pd.concat(Parallel(n_jobs=3)(delayed(province_out)(s) for s in ("ENNS2018", "ENNS2019", "ENNS2021"))).merge(x[["key", "survey", "y_high", "q_true", "GNT"]], on=["key", "survey"])
    res["province_held_out"] = {"accuracy_held_out": float(((H["p_ho"] >= .5) == (H["y_high"] == 1)).mean()), "accuracy_standard": float(((H["GNT"] >= .5) == (H["y_high"] == 1)).mean()), "brier_held_out": float(np.mean((H["p_ho"] - H["q_true"]) ** 2)), "brier_standard": float(np.mean((H["GNT"] - H["q_true"]) ** 2)), "note": "the anchor still uses the province's own earlier surveys, as the method defines; only the LightGBM adjustment is refitted without the province"}
    # 4. employment and remittances, feature usage
    U, diag = usage()
    U.to_csv(OUT / "feature_usage.csv", index=False, lineterminator="\n")
    res["employment_remittance_diagnosis"] = diag
    res["feature_usage_summary"] = U.groupby("group").agg(features=("feature", "size"), reaching_model=("reaches_model", "sum"), same_value_all_provinces=("same_for_all_provinces_in_a_quarter", "sum"), shap=("mean_abs_shap", "sum")).reset_index().to_dict(orient="records")
    # 5. all-LOW: anchor vs adjustment for CALABARZON live, from the sealed E151 forecast
    seal = json.loads((O51 / "issue" / "sealed_forecast_2027-Q1.json").read_text())["forecasts"]
    res["calabarzon_2027Q1"] = [{"province": r["province"], "latest_survey": r["latest_measured_pct"], "anchor": r["anchor_only_pct"], "score": r["score"], "p_high": r["p_high_ge50"]} for r in seal if r["lead"] == 1]
    res["share_forecast_high_by_island_L1"] = x.assign(h=x["GNT"] >= .5).groupby("island")["h"].mean().round(3).to_dict()
    res["share_actual_high_by_island_L1"] = x.groupby("island")["y_high"].mean().round(3).to_dict()
    # 6. threshold sensitivity, report only
    pct = 100 / (1 + np.exp(-x["mu_GNT"]))
    tp = 100 / (1 + np.exp(-x["y_true"]))
    res["threshold_sensitivity_report_only"] = {str(t): {"share_actual_high": round(float((tp >= t).mean()), 3), "accuracy": round(float(((pct >= t) == (tp >= t)).mean()), 3)} for t in (40, 45, 50, 55, 60)}
    (OUT / "audit.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
