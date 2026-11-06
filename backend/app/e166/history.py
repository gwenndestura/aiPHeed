"""
E166 for every dashboard quarter (owner decision 2026-11-06: "implemented to the whole system, not only 2027-Q1").

For each target quarter T on the dashboard timeline (2023-Q1 .. 2027-Q1), E166 is run as of the issue quarter T-1
(one quarter ahead, Lead 1), with only information published before that issue date, by the unchanged E166 code
(app.e166.temperature.forecast). Past quarters are therefore E166 back-forecasts ("what E166 would have said"), not
validated against a survey: no provincial HFIAS round exists for most of them.

Per quarter it writes data/e166/out/history/<T>.json: province forecasts, each province's per-input contributions
(SHAP for trees, exact linear contributions for ElasticNet/Ridge, LightGBM pred_contrib), article counts, and the
142 LGU rankings (paper Algorithm 5). Reproduction check: the 2027-Q1 run must equal the sealed forecast_2027-Q1.json.

    python -m app.e166.history run
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GroupKFold

from app.e147 import features as Fe
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e158 import model as E8
from app.e163 import model as C
from app.e164 import auto as U
from app.e166 import temperature as T
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e166" / "out" / "history"
FIRST, LAST = "2023-Q1", "2027-Q1"
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))


def build(issue: int):
    """app.e160.trace.build with the issue quarter as a parameter."""
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    H = E154.income()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, issue, Pv.ROUNDS, "F")
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)]
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, five.assign(T=issue + 1, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [1], "F")), H).reset_index(drop=True)
    return S, P, tr, te


def contributions(tr, te, AN, tag):
    """Per-input contributions of the chosen configuration's adjustment for the test rows, and the slope applied to them
    (AUTO's linear calibration, when chosen). Returns (phi [rows x inputs], inputs, base, mu_check)."""
    a, l, f, cal = tag.split("|")
    f = None if f == "-" else f
    tr = tr.reset_index(drop=True)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    atr, ate = AN[a]
    if l == "NONE":
        phi, use, base, pred, oof_id = np.zeros((len(te), 0)), [], 0.0, np.zeros(len(te)), atr.copy()
    else:
        m = U.LEARNERS[l](U.FS[f]).fit(tr.assign(e=y - atr))
        pred = m.predict(te)
        use = list(m.use_)
        if l == "RF":
            import shap
            ex = shap.TreeExplainer(m.m_)
            phi = ex.shap_values(te[use].fillna(m.med_).values)
            base = float(np.atleast_1d(ex.expected_value)[0])
        elif l in ("ENET", "RIDGE"):
            Xtr, Xte = m._X(tr), m._X(te)
            coef = np.asarray(m.m_.coef_, float)
            phi = coef[None, :] * (Xte - Xtr.mean(axis=0)[None, :])
            base = float(m.m_.intercept_ + coef @ Xtr.mean(axis=0))
        else:                                          # LGBM (Res2): additive contributions from the booster
            cc = m.m_.booster_.predict(te[use], pred_contrib=True)
            phi, base = cc[:, :-1], float(cc[0, -1])
            gap = pred - (base + phi.sum(axis=1))      # Res2 may add a constant; keep it in the base
            base = base + float(np.mean(gap))
        oof_id = np.zeros(len(tr))
        for i_tr, i_te in GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]):
            d = tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])
            oof_id[i_te] = atr[i_te] + U.LEARNERS[l](U.FS[f]).fit(d).predict(tr.iloc[i_te])
    slope, icpt = 1.0, 0.0
    if cal == "cal":
        Z = np.column_stack([np.ones(len(tr)), oof_id]) * np.sqrt(w)[:, None]
        icpt, slope = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
    mu_check = icpt + slope * (ate + pred)
    return phi * slope, use, base, mu_check, float(slope)


def articles(target: int) -> dict[str, int]:
    """Articles naming each province in the last complete quarter before the issue date (issue = target - 1)."""
    N = pd.read_parquet(D / "e151" / "out" / "news_panel.parquet")
    qi = target - 2
    return {p: int(N[(N["stream"] == f"prov:{p.lower()}") & (N["qi"] == qi) & (N["lag_m"] == Pv.NEWS_LAG)]["n"].sum()) for p in CAL}


def lgu_rank(prob: dict[str, float], n: dict[str, int], target_label: str) -> pd.DataFrame:
    """Paper Algorithm 5 (identical to app.e166.objectives.lgu)."""
    from app.e166.objectives import LABEL, MIN_ARTICLES, W_DEN, W_POV
    c = pd.read_parquet(D / "processed" / "lgu_census.parquet")
    l = pd.read_csv(D / "e143" / "out" / "issue" / "lgus_next_quarter.csv", dtype={"lgu_psgc": str})
    c["k"], l["k"] = c["lgu_code"].astype(str).str.zfill(9), l["lgu_psgc"].astype(str).str.zfill(9)
    d = c.merge(l[["k", "poverty_incidence_2021"]], on="k", how="inner")
    d["density"] = np.where(d["land_area_km2"] > 0, d["population_2020"] / d["land_area_km2"].where(d["land_area_km2"] > 0), np.nan)
    d["density"] = d["density"].fillna(d.groupby("province_name")["density"].transform("mean"))
    mm = lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else x * 0.0
    d["poverty_norm"] = d.groupby("province_name")["poverty_incidence_2021"].transform(mm)
    d["density_norm"] = d.groupby("province_name")["density"].transform(mm)
    d["vulnerability"] = W_POV * d["poverty_norm"] + W_DEN * d["density_norm"]
    d["province_risk_prob"] = d["province_name"].map(prob)
    d["risk_index"] = (d["province_risk_prob"] * d["vulnerability"]).clip(0, 1)
    d["articles_last_quarter"] = d["province_name"].map(n)
    d["data_sufficiency_flag"] = np.where(d["articles_last_quarter"] >= MIN_ARTICLES, "OK", "LIMITED_SIGNAL")
    d["disaggregation_label"] = LABEL
    d = d.sort_values(["risk_index", "poverty_incidence_2021"], ascending=[False, False]).reset_index(drop=True)
    d["rank_in_region"] = np.arange(1, len(d) + 1)
    d["rank_in_province"] = d.groupby("province_name")["risk_index"].rank(ascending=False, method="first").astype(int)
    d["target_quarter"] = target_label
    return d


def one(target_label: str, SW: pd.DataFrame) -> dict:
    from app.e148 import panel as Pn
    target = qindex(target_label)
    issue = target - 1
    S, P, tr, te = build(issue)
    AN = U.anchors(S, P, tr, te)
    mu, sd, half, pa, s, ps, half_s, cls, tag, lam, src, la, va, lb, vb, nb, kb, n_rounds = T.forecast(tr, te, AN, SW, Pn.q_start(issue), 1)
    phi, use, base, mu_check, slope = contributions(tr, te, AN, tag)
    assert np.max(np.abs(mu_check - mu)) < 1e-6, ("contribution model does not reproduce the forecast", target_label)
    news = set(Pv.NEWS_ALL)
    contrib = [{"province": te["province"].iloc[k], "feature": c, "group": C.gmap(c) or "timing", "source": "news" if c in news else "official",
                "contribution": float(phi[k, j] * lam)} for k in range(len(te)) for j, c in enumerate(use)]
    n = articles(target)
    rows = [{"province": te["province"].iloc[k], "score": round(float(pct(s[k])), 1), "low90": round(float(pct(s[k] - half_s[k])), 1),
             "high90": round(float(pct(s[k] + half_s[k])), 1), "p_high": round(float(ps[k]), 4), "class": "HIGH" if cls[k] else "LOW",
             "articles_last_quarter": n[te["province"].iloc[k]]} for k in range(len(te))]
    lg = lgu_rank({r["province"]: r["p_high"] for r in rows}, n, target_label)
    out = {"model": "E166", "target_quarter": target_label, "issue_quarter": qlabel(issue), "issue_date": str(Pn.q_start(issue).date()),
           "lead": 1, "kind": "forecast" if target_label == LAST else "back-forecast (as of the issue date; no survey for this quarter)",
           "config": tag, "lam": lam, "lam_source": src, "train_rows": int(len(tr)), "released_rounds": list(P.rel),
           "forecasts": rows, "contributions": contrib, "lgus": lg.round(6).to_dict("records")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{target_label}.json").write_text(json.dumps(out, default=float), newline="\n")
    return {"target": target_label, "config": tag, "lam": round(lam, 3), "p_high": {r["province"]: r["p_high"] for r in rows}}


def run():
    from app.e144 import data as SWSD
    targets = [qlabel(i) for i in range(qindex(FIRST), qindex(LAST) + 1)]
    SW = T.sws_forecasts(SWSD.sws_quarterly(), qindex(LAST) - 1)          # each SWS forecast uses only data before its own issue
    R = Parallel(n_jobs=12)(delayed(one)(t, SW) for t in targets)
    sealed = {r["province"]: r["p_high"] for r in json.loads((D / "e166" / "out" / "objectives" / "forecast_2027-Q1.json").read_text())["forecasts"]}
    last = next(r for r in R if r["target"] == LAST)["p_high"]
    diff = max(abs(sealed[p] - last[p]) for p in sealed)
    print("reproduction of the sealed 2027-Q1 forecast, max |diff|:", diff)
    assert diff < 1e-4, "history run does not reproduce the sealed 2027-Q1 forecast"
    for r in R:
        print(r["target"], r["config"], "lam", r["lam"], r["p_high"])
    (OUT / "index.json").write_text(json.dumps({"quarters": targets, "first": FIRST, "last": LAST, "reproduction_max_diff": diff}, indent=1), newline="\n")


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
