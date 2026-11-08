"""
E143 post-hoc analyses (run AFTER the locked evaluation; none of them changes the gate or the adoption).

    python -m app.e143.posthoc     -> data/e143/out/posthoc.json

1  origins where an anchor is identified (O2 + O3): descriptive comparison, NOT the pre-registered gate
2  2013 calibration: reliability, calibration slope, ECE expected under perfect calibration, survey-SE sensitivity
3  FSSI v2: overlap with cyclones and news volume; agreement with the measured CALABARZON rounds (descriptive, tiny n)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr
from sklearn.linear_model import LinearRegression, LogisticRegression

from app.e137 import evaluate as E137
from app.e138 import where as WH
from app.e140 import model as M140
from app.e141 import panel as P
from app.e142 import OUT as O142
from app.e142 import fssi as F2
from app.e142 import model as M142
from app.e143 import OUT
from app.e143 import model as M

SEED = 20261108


def identified_origins(rng):
    R = pd.read_csv(OUT / "oof_rolling.csv")
    S = R[R["origin"].isin(["O2", "O3"])]
    out = {"label": "DESCRIPTIVE ONLY (origins O2+O3, where training contains a measured transition); the pre-registered "
                    "gate is pooled over O1-O3 and is not changed", "n": int(len(S)), "n_regions": int(S["region"].nunique())}
    for c in ("C4 HRE-LGBM-X", "C2 RE-LGBM-X", "STATE-LGBM"):
        out[c] = {b: WH.boot(S, c, b, rng) for b in ("PERS", "REGPREV")}
    return out


def _slope(p, q):
    z = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).reshape(-1, 1)
    m = LogisticRegression(C=1e6).fit(np.vstack([z, z]), np.r_[np.ones(len(q)), np.zeros(len(q))], sample_weight=np.r_[q, 1 - q])
    return {"slope": float(m.coef_[0][0]), "intercept": float(m.intercept_[0])}


def calibration_2013(rng, n_sim=2000):
    U = pd.read_csv(OUT / "oof_untouched_2013.csv")
    tr = M140.data(lead=1).copy()
    tr["prev_survey"] = np.where(tr["prev_y"].notna(), "FNRI2015", None)
    te = P.data(1)
    te = te[te["survey"] == "NNS2013"].reset_index(drop=True)
    # level-only predictive mean and variance, refitted exactly as in the locked runs (E142 and E143 C4)
    sm = M142.StateModel("lgbm").fit(tr)
    an = M.Anchored("hre", "lgbm").fit(tr)
    pv = {"STATE-LGBM": (sm._mu(te), np.full(len(te), sm.tau2_)), "C4 HRE-LGBM-X": an.predict(te)}
    out = {}
    se = te["se_y"].values
    for name, (yh, V) in pv.items():
        p = U[name].values
        sims = []
        for _ in range(n_sim):
            yo = rng.normal(yh, np.sqrt(V + se ** 2))
            sims.append(E137.metrics(U.assign(q=norm.cdf(yo / se), _p=p), "_p")["ece"])
        bins = np.clip((p * 5).astype(int), 0, 4)
        out[name] = {"ece": E137.metrics(U, name)["ece"],
                     "ece_if_perfectly_calibrated_median_p95": [float(np.median(sims)), float(np.percentile(sims, 95))],
                     "share_of_perfectly_calibrated_runs_with_higher_ece": float(np.mean(np.asarray(sims) >= E137.metrics(U, name)["ece"])),
                     "calibration": _slope(p, U["q"].values), "sharpness_mean_abs_p_minus_half": float(np.mean(np.abs(p - 0.5))),
                     "reliability": [{"bin": int(b), "n": int((bins == b).sum()), "mean_p": float(p[bins == b].mean()),
                                      "mean_q": float(U["q"].values[bins == b].mean())} for b in range(5) if (bins == b).any()],
                     "mean_p": float(p.mean()), "mean_q": float(U["q"].mean())}
    sens = {}
    for deff in (2.0, 3.17, 4.5):
        se2 = se * np.sqrt(deff / 3.17)
        q2 = norm.cdf(te["y"].values / se2)
        sens[f"deff {deff}"] = {n: E137.metrics(U.assign(q=q2), n)["ece"] for n in ("STATE-LGBM", "C2 RE-LGBM-X", "C4 HRE-LGBM-X", "LGBM", "PRIOR")}
    out["survey_se_sensitivity_2013 (E141 approximates the 2013 SE with design effect 3.17)"] = sens
    return out


def fssi():
    d = pd.read_csv(O142 / "fssi_v2_province_quarter.csv")
    v = d[(d["articles"] > 0) & d["fssi_v2"].notna()].copy()
    v["tc"] = [F2.cyclones(p, q) for p, q in zip(v["province"], v["quarter"])]
    v["log_articles"] = np.log1p(v["articles"])
    Xc = v[["tc", "log_articles"]].values
    r2 = float(LinearRegression().fit(Xc, v["fssi_v2"]).score(Xc, v["fssi_v2"]))
    a = json.loads((F2.SRC / "audit.json").read_text())
    X = P.data(1)
    rows = []
    for _, r in X[X["province"].isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])].iterrows():
        iss = pd.Timestamp(r["issue_date"])
        qs = [f"{t.year}-Q{(t.month - 1) // 3 + 1}" for t in pd.date_range(iss - pd.DateOffset(months=12), iss, freq="QS")][:-1]
        f = d[(d["province"] == r["province"]) & d["quarter"].isin(qs)]["fssi_v2"].dropna()
        rows.append({"province": r["province"], "survey": r["survey"], "y": r["y"], "status": r["status"],
                     "fssi_v2_mean_4q_before_issue": float(f.mean()) if len(f) else None, "n_quarters": int(len(f))})
    R = pd.DataFrame(rows).dropna(subset=["fssi_v2_mean_4q_before_issue"])
    rho = spearmanr(R["fssi_v2_mean_4q_before_issue"], R["y"]).statistic if len(R) > 3 else None
    return {"outlets": a["by_site"], "geo_level_of_articles": a["geo_level"], "multi_source_events": a["multi_source_events"],
            "r2_of_fssi_v2_on_cyclones_and_volume": r2, "unique_variance_share": 1 - r2,
            "measured_rounds_with_fssi": R.to_dict(orient="records"), "rank_corr_with_measured_relative_logit": rho,
            "n_rounds": int(len(R)),
            "note": "n is too small for any inference; there are no quarterly provincial outcomes against which FSSI could be "
                    "tested as a forecast input, and no human-labelled sentiment sample may be used (owner rule)."}


def run():
    rng = np.random.default_rng(SEED)
    out = {"identified_origins_O2_O3": identified_origins(rng)}
    print("1", flush=True)
    out["calibration_2013"] = calibration_2013(rng)
    print("2", flush=True)
    out["fssi"] = fssi()
    (OUT / "posthoc.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    run()
