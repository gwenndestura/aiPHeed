"""
E148 locked evaluation (docs/e148/PROTOCOL.md).

    python -m app.e148.evaluate smoke | lock | predict | score | issue

predict  verifies the lock; scores development rows, selects the arm, predicts 2021 for all arms and leads, runs the quarterly series and
         its independent SWS check, then hashes the 2021 predictions
score    verifies the hash, opens the sealed 2021 labels once, writes results.json
issue    after score: 2021 becomes an anchor; five provincial forecasts for the next four quarters and the LGU ranking
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm, spearmanr

from app.e144 import data as D
from app.e145 import lgu as LGU
from app.e147 import OUT as O147
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e148 import OUT, PROTOCOL_VERSION, VERSION
from app.e148 import model as M
from app.e148 import panel as Pn
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
PROTOCOL = BACKEND_DIR.parent / "docs" / "e148" / "PROTOCOL.md"
CODE = ["panel.py", "model.py", "evaluate.py"]
SEED = 148
N_BOOT = 2000
LEADS = list(range(1, 9))
ARMS = ["Q-G", "Q-GN", "Q-GNB", "Q-noSWS", "Q-frozen", "N", "DRIFT", "PERS", "LR-PSA", "LR-NLP", "LR-ALL"]
TESTS = {"O2": "ENNS2018", "O3": "ENNS2019"}
T = {"R1_accuracy": 0.75, "R2_auc": 0.70, "R3_recall": 0.50, "R3_precision": 0.50, "seed": SEED, "n_boot": N_BOOT, "leads": LEADS, "n_placebo": 30, "threshold_pct": 60.0, "anchor_lag_q": Pn.ANCHOR_LAG}
SEAL = OUT / "PREDICTIONS_SEAL.json"
ALL_TRAIN = ["FNRI2015", "ENNS2018", "ENNS2019"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e148"
    return {"protocol": _sha(PROTOCOL), "sealed_labels": _sha(Lb.SEALED), "gov_panel": _sha(OUT / "gov_panel.parquet"), "news_panel": _sha(OUT / "news_panel.parquet"), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists() and "--deviation" not in sys.argv:
        raise RuntimeError("E148 is already locked")
    p.write_text(json.dumps({"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": _hashes(), "thresholds": T}, indent=2), newline="\n")


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E148 lock mismatch: {bad}")


def released(i, lag=Pn.ANCHOR_LAG):
    return [s for s in ALL_TRAIN if M.RQ[s] + lag <= i]


def targets_2021(S):
    t = E7.targets_2021(S.base)
    t["T"] = M.RQ["ENNS2021"]
    return t


def task(oid, test_survey, lead, lag=Pn.ANCHOR_LAG, shuffle=None, arms=None, mask=False):
    S = M.Store()
    Tq = M.RQ[test_survey]
    i = Tq - lead
    train = released(i, lag)
    tgt = targets_2021(S) if test_survey == "ENNS2021" else M.targets(S, [test_survey])
    origin = "F" if test_survey == "ENNS2021" else oid
    if not train:
        return None
    tr = M.rows_for(S, M.targets(S, train), LEADS, origin, lag=lag)
    te = M.rows_for(S, tgt, [lead], origin, lag=lag)
    if tr.empty or te.empty:
        return None
    if shuffle is not None:
        r = np.random.default_rng(shuffle)
        for fr in (tr, te):
            for _, g in fr.groupby(["survey", "lead"]):
                fr.loc[g.index, M.NEWS] = fr.loc[r.permutation(g.index.values), M.NEWS].values
    if mask:
        r = np.random.default_rng(SEED)
        te = te.copy()
        for c in M.NOW + M.SINCE:
            te.loc[r.random(len(te)) < 0.20, c] = np.nan
    fz = M.rows_for(S, tgt, [lead], origin, lag=lag, frozen=True) if arms is None else None
    p = M.predict_all(tr, te, fz, arms)
    keep = ["key", "province", "region", "island", "survey", "T", "lead", "i", "y_anchor", "gap_q", "rq_anchor"] + [c for c in ("y_true", "se_true", "q_true", "p_true") if c in te]
    o = te[keep].copy()
    for k, v in p.items():
        o[k] = v
    o["origin"], o["n_train_rows"], o["train_surveys"] = oid, len(tr), "+".join(train)
    return o


def eb(p, q):
    return E7.eb(np.asarray(p, float), np.asarray(q, float))


def series_task(i):
    """Lead-1 estimate for quarter i + 1 from what was public at issue quarter i. Sealed 2021 labels are never used."""
    S = M.Store()
    train = released(i)
    if not train:
        return None
    b = S.base.drop_duplicates("key").copy()
    b["T"], b["survey"] = i + 1, "SERIES"
    origin = "O2" if i < qindex("2017-Q3") else "O3" if i < qindex("2019-Q3") else "F"
    tr = M.rows_for(S, M.targets(S, train), LEADS, origin)
    te = M.rows_for(S, b.drop(columns=["y", "se_y", "q_high", "p"]), [1], origin)
    if tr.empty or te.empty:
        return None
    o = te[["key", "province", "region", "sws_area", "T", "i", "y_anchor", "gap_q"]].copy()
    for a in ("Q-G", "Q-noSWS"):
        m = M.QModel(M.SETS[a]).fit(tr)
        o["mu_" + a], o["sigma_" + a] = m.mu(te), m.sigma(te)
    o["n_train_surveys"] = len(train)
    return o


def sws_check(Sr: pd.DataFrame, rng) -> dict:
    """Independent temporal check: does the survey-trained series, which never saw SWS, move with measured SWS hunger?"""
    s = D.sws_quarterly()[["area", "qi", "hunger"]].rename(columns={"area": "sws_area", "qi": "T"})
    out = {}
    for a in ("Q-noSWS", "Q-G"):
        g = Sr.groupby(["sws_area", "T"])["mu_" + a].mean().reset_index().merge(s, on=["sws_area", "T"]).sort_values(["sws_area", "T"])
        g["h"] = Fe._logit(g["hunger"])
        g["dm"], g["dh"], g["gap"] = g.groupby("sws_area")["mu_" + a].diff(), g.groupby("sws_area")["h"].diff(), g.groupby("sws_area")["T"].diff()
        c = g[(g["gap"] == 1) & g["dm"].notna() & g["dh"].notna()]
        qs = c["T"].unique()
        draws = []
        by = {q: c[c["T"] == q] for q in qs}
        for _ in range(N_BOOT):
            x = pd.concat([by[q] for q in rng.choice(qs, len(qs))])
            if x["dm"].nunique() > 2:
                draws.append(spearmanr(x["dm"], x["dh"]).statistic)
        out[a] = {"n_area_quarters": int(len(c)), "n_quarters": int(len(qs)), "change_rho": float(spearmanr(c["dm"], c["dh"]).statistic), "ci95": [float(np.nanpercentile(draws, 2.5)), float(np.nanpercentile(draws, 97.5))],
                  "level_rho": float(spearmanr(g["mu_" + a], g["h"]).statistic), "first_T": qlabel(int(c["T"].min())), "last_T": qlabel(int(c["T"].max()))}
    out["passes_independent_check"] = bool(out["Q-noSWS"]["ci95"][0] > 0)
    return out


def smoke():
    o = task("O2", "ENNS2018", 1)
    f = task("F", "ENNS2021", 1)
    s = series_task(qindex("2020-Q2"))
    assert len(o) and f["Q-G"].notna().all() and f["Q-GNB"].notna().all() and len(s)
    print("smoke ok: dev", len(o), "final", len(f), "series", len(s), "train rows", int(f["n_train_rows"].iloc[0]), f["train_surveys"].iloc[0])


def predict():
    verify_lock()
    if SEAL.exists():
        raise RuntimeError("predictions are already sealed")
    rng = np.random.default_rng(SEED)
    dev = [x for x in Parallel(n_jobs=12)(delayed(task)(o, t, h) for o, t in TESTS.items() for h in LEADS) if x is not None]
    Dv = pd.concat(dev, ignore_index=True)
    Dv["y_high"] = (Dv["y_true"] >= Fe.LT).astype(int)
    Dv.to_csv(OUT / "oof_dev.csv", index=False, lineterminator="\n")
    res = {"by_lead": {}}
    for h, g in Dv.groupby("lead"):
        e = {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "metrics": {a: E7.metrics(g[a].fillna(0.5), g["y_high"], g["q_true"]) for a in ARMS if a in g}, "always_high_accuracy": float(g["y_high"].mean())}
        for x, y in (("Q-G", "PERS"), ("Q-G", "DRIFT"), ("Q-GNB", "Q-G"), ("Q-GN", "Q-G"), ("Q-G", "Q-noSWS")):
            e[f"{x}_minus_{y}"] = E7.diff_ci(g, x, y, "q_true", rng)
        z = g.dropna(subset=["Q-frozen"])
        e["Q-G_minus_Q-frozen"] = E7.diff_ci(z, "Q-G", "Q-frozen", "q_true", rng)
        pc, dy = (g["mu_Q-G"] - g["y_anchor"]).values, (g["y_true"] - g["y_anchor"]).values
        e["change_rho_Q-G"] = float(spearmanr(pc, dy).statistic)
        res["by_lead"][f"L{h}"] = e
    sel = "Q-GNB" if res["by_lead"]["L1"]["Q-GNB_minus_Q-G"]["ci95"][1] < 0 else "Q-G"
    res["selected_arm_on_development"] = sel
    lag8 = [x for x in Parallel(n_jobs=4)(delayed(task)(o, t, 1, 8, None, ["Q-G"]) for o, t in TESTS.items()) if x is not None]
    if lag8:
        L8 = pd.concat(lag8).merge(Dv[Dv["lead"] == 1][["key", "survey", "mu_Q-G"]], on=["key", "survey"], suffixes=("_lag8", ""))
        res["sensitivity_anchor_lag8"] = {"mean_abs_change_logit": float((L8["mu_Q-G_lag8"] - L8["mu_Q-G"]).abs().mean()), "n": int(len(L8))}
    ms = [x for x in Parallel(n_jobs=4)(delayed(task)(o, t, 1, Pn.ANCHOR_LAG, None, ["Q-G"], True) for o, t in TESTS.items()) if x is not None]
    M1 = pd.concat(ms).assign(yh=lambda d: (d["y_true"] >= Fe.LT).astype(int))
    res["sensitivity_mask20"] = {"brier": eb(M1["Q-G"], M1["q_true"]), "brier_base": eb(Dv[Dv["lead"] == 1]["Q-G"], Dv[Dv["lead"] == 1]["q_true"])}
    F = pd.concat(Parallel(n_jobs=8)(delayed(task)("F", "ENNS2021", h) for h in LEADS), ignore_index=True)
    F.to_csv(OUT / "predictions_2021.csv", index=False, lineterminator="\n")
    pl = Parallel(n_jobs=16)(delayed(task)("F", "ENNS2021", 1, Pn.ANCHOR_LAG, 3000 + d, ["Q-GNB"]) for d in range(T["n_placebo"]))
    pd.concat([x.assign(draw=d) for d, x in enumerate(pl)], ignore_index=True)[["key", "Q-GNB", "draw"]].to_csv(OUT / "placebo_2021.csv", index=False, lineterminator="\n")
    Sr = pd.concat([x for x in Parallel(n_jobs=12)(delayed(series_task)(i) for i in range(qindex("2015-Q1"), qindex("2026-Q4"))) if x is not None], ignore_index=True)
    Sr.round(5).to_csv(OUT / "quarterly_series_lead1.csv", index=False, lineterminator="\n")
    res["independent_sws_check"] = sws_check(Sr, rng)
    (OUT / "dev_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    seal = {"selected_arm": sel, "sealed_utc": datetime.now(timezone.utc).isoformat(), "predictions_sha256": _sha(OUT / "predictions_2021.csv"), "placebo_sha256": _sha(OUT / "placebo_2021.csv"), "labels_sha256": _sha(Lb.SEALED)}
    SEAL.write_text(json.dumps(seal, indent=1), newline="\n")
    print(json.dumps(seal, indent=1))


def score():
    s = json.loads(SEAL.read_text())
    if _sha(OUT / "predictions_2021.csv") != s["predictions_sha256"] or _sha(Lb.SEALED) != s["labels_sha256"]:
        raise RuntimeError("seal mismatch")
    if (OUT / "results.json").exists():
        raise RuntimeError("sealed labels were already scored by E148")
    rng = np.random.default_rng(SEED + 1)
    L = pd.read_csv(Lb.SEALED)
    w = L[L["fs_survey_category"] == "Food Insecure Households"].drop_duplicates("key")[["key", "pct"]]
    P_ = pd.read_csv(OUT / "predictions_2021.csv").merge(w, on="key", how="left")
    P_ = P_[P_["pct"].notna()].copy()
    P_["y_true"], P_["y_high"] = Fe._logit(P_["pct"]), (P_["pct"] >= 60.0).astype(int)
    P_["q_true"] = norm.cdf((P_["y_true"] - Fe.LT) / (0.03 / (P_["pct"] / 100 * (1 - P_["pct"] / 100))))
    P_.to_csv(OUT / "oof_2021.csv", index=False, lineterminator="\n")
    sel = s["selected_arm"]
    out = {"selected_arm": sel, "version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(), "by_lead": {}}
    mrl, stop, news_p = 0, False, {}
    for h, g in P_.groupby("lead"):
        e = {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "metrics": {a: E7.metrics(g[a].fillna(0.5), g["y_high"], g["q_true"]) for a in ARMS}, "always_high_accuracy": float(g["y_high"].mean()), "always_low_accuracy": float(1 - g["y_high"].mean()),
             "train_surveys": g["train_surveys"].iloc[0], "n_train_rows": int(g["n_train_rows"].iloc[0])}
        for x, y in ((sel, "PERS"), (sel, "DRIFT"), ("Q-GNB", "Q-G"), ("Q-GN", "Q-G"), ("Q-G", "Q-noSWS")):
            e[f"{x}_minus_{y}"] = E7.diff_ci(g, x, y, "q_true", rng)
        z = g.dropna(subset=["Q-frozen"])
        e["Q-G_minus_Q-frozen"] = E7.diff_ci(z, "Q-G", "Q-frozen", "q_true", rng) if len(z) else None
        news_p[int(h)] = e["Q-GNB_minus_Q-G"]["p_ge_0"]
        pc, dy = (g["mu_" + sel] - g["y_anchor"]).values, (g["y_true"] - g["y_anchor"]).values
        gs, v = list(g.groupby("region").indices.values()), []
        for _ in range(1000):
            i = np.concatenate([gs[j] for j in rng.integers(0, len(gs), len(gs))])
            v.append(spearmanr(pc[i], dy[i]).statistic)
        chg = {"rho": float(spearmanr(pc, dy).statistic), "ci95": [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]}
        pp = g[sel].values
        ece95 = float(np.percentile([E7.metrics(pp, (rng.random(len(pp)) < pp).astype(int))["ece"] for _ in range(2000)], 95))
        m = e["metrics"][sel]
        ck = {"R1_accuracy": m["accuracy"] >= T["R1_accuracy"], "R2_auc": (m["auc"] or 0) >= T["R2_auc"], "R3_recall_precision": m["recall"] >= T["R3_recall"] and m["precision"] >= T["R3_precision"],
              "R4_beats_persistence": e[f"{sel}_minus_PERS"]["ci95"][1] < 0, "R5_calibration": m["ece"] <= ece95, "R6_predicts_change": chg["ci95"][0] > 0}
        e["reliability"] = {"checks": {k: bool(x) for k, x in ck.items()}, "passes": bool(all(ck.values())), "change": chg, "ece_95th_perfect_calibration": ece95}
        lz = g[g["island"] == "Luzon"]
        e["differentiation"] = {"spearman_all": float(spearmanr(g["mu_" + sel], g["y_true"]).statistic), "spearman_luzon": float(spearmanr(lz["mu_" + sel], lz["y_true"]).statistic), "n_luzon": int(len(lz)), "pers_spearman_all": float(spearmanr(g["y_anchor"], g["y_true"]).statistic), "pers_spearman_luzon": float(spearmanr(lz["y_anchor"], lz["y_true"]).statistic),
                                "mae_points": {a: float(np.mean(np.abs(100 / (1 + np.exp(-g["mu_" + a])) - g["pct"]))) for a in (sel, "PERS", "DRIFT")}}
        e["calabarzon"] = g[g["province"].isin(["Batangas", "Cavite"])][["province", "pct", "y_high", sel, "Q-G", "Q-GNB", "PERS", "DRIFT", "mu_" + sel, "y_anchor"]].round(4).to_dict(orient="records")
        out["by_lead"][f"L{h}"] = e
        if e["reliability"]["passes"] and not stop:
            mrl = int(h)
        else:
            stop = True
    out["maximum_reliable_lead"] = mrl
    order, st, holm = sorted([1, 2, 3, 4], key=lambda h: news_p[h]), False, {}
    for k, h in enumerate(order):
        a = 0.05 / (4 - k)
        ok = (not st) and news_p[h] < a / 2
        st = st or not ok
        holm[f"L{h}"] = {"p_ge_0": news_p[h], "level": 1 - a, "news_improves": ok}
    out["news_holm"] = holm
    g1 = P_[P_["lead"] == 1]
    Dp = pd.read_csv(OUT / "placebo_2021.csv").merge(g1[["key", "q_true"]], on="key")
    pl = [eb(x["Q-GNB"], x["q_true"]) - eb(g1.set_index("key").loc[x["key"], "Q-G"], x["q_true"]) for _, x in Dp.groupby("draw")]
    real = out["by_lead"]["L1"]["Q-GNB_minus_Q-G"]["diff"]
    out["placebo_L1"] = {"real_diff": real, "share_placebo_better_or_equal": float(np.mean(np.array(pl) <= real)), "draws": pl}
    out["news_claim_L1"] = bool(holm["L1"]["news_improves"] and out["placebo_L1"]["share_placebo_better_or_equal"] <= 0.05)
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps({k: out[k] for k in ("selected_arm", "maximum_reliable_lead", "news_claim_L1")}, indent=1))


def issue():
    """After scoring: 2021 joins anchors and training. Quarters 2027-Q1 to Q4 from the 2026-Q4 issue. News stops in 2021, so a news arm cannot run live."""
    S = M.Store()
    res = json.loads((OUT / "results.json").read_text())
    L = pd.read_csv(Lb.SEALED)
    w = L[L["fs_survey_category"] == "Food Insecure Households"].drop_duplicates("key")[["key", "pct"]]
    base = S.base.drop_duplicates("key").set_index("key")
    e = w[w["key"].isin(base.index)].copy()
    e["survey"], e["year"], e["ref_quarter"], e["p"], e["se_p"] = "ENNS2021", 2021, "2021-Q3", e["pct"], 3.0
    e["y"] = Fe._logit(e["p"])
    e["se_y"] = 0.03 / (e["p"] / 100 * (1 - e["p"] / 100))
    e["q_high"] = norm.cdf((e["y"] - Fe.LT) / e["se_y"])
    for c in ("province", "region", "sws_area", "island"):
        e[c] = e["key"].map(base[c])
    S.base = pd.concat([S.base, e[S.base.columns]], ignore_index=True)
    i = qindex("2026-Q4")
    tr = M.rows_for(S, M.targets(S, ALL_TRAIN + ["ENNS2021"]), LEADS, "F")
    arm = "Q-G"
    m = M.QModel(M.SETS[arm]).fit(tr)
    five = S.base.drop_duplicates("key")
    five = five[five["province"].isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])].copy()
    rows = []
    for h in (1, 2, 3, 4):
        f = five.assign(T=i + h, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"])
        te = M.rows_for(S, f, [h], "F")
        mu, sd = m.mu(te), m.sigma(te)
        for k in range(len(te)):
            rows.append({"province": te["province"].iloc[k], "issue_quarter": qlabel(i), "target_quarter": qlabel(i + h), "lead": h, "anchor_quarter": qlabel(int(te["rq_anchor"].iloc[k])), "anchor_pct": round(100 / (1 + np.exp(-te["y_anchor"].iloc[k])), 1),
                         "forecast_pct": round(100 / (1 + np.exp(-mu[k])), 1), "low90": round(100 / (1 + np.exp(-(mu[k] - 1.645 * sd[k]))), 1), "high90": round(100 / (1 + np.exp(-(mu[k] + 1.645 * sd[k]))), 1), "p_high_ge60": round(float(norm.cdf((mu[k] - Fe.LT) / sd[k])), 3), "row_type": "forecast"})
    Lv = pd.DataFrame(rows)
    (OUT / "issue").mkdir(exist_ok=True)
    Lv.to_csv(OUT / "issue" / "five_province_forecasts.csv", index=False, lineterminator="\n")
    q1 = Lv[Lv["lead"] == 1]
    LGU.rank(dict(zip(q1["province"], q1["p_high_ge60"])), qlabel(i + 1)).to_csv(OUT / "issue" / f"lgu_priority_{qlabel(i + 1)}.csv", index=False, lineterminator="\n")
    print(Lv.to_string(index=False))


if __name__ == "__main__":
    {"smoke": smoke, "lock": lock, "predict": predict, "score": score, "issue": issue}[sys.argv[1]]()
