"""
E146 locked evaluation (docs/e146/PROTOCOL.md).

    python -m app.e146.evaluate smoke | lock | run

`smoke` runs one lead end to end to catch crashes; it prints and saves no metric. `run` verifies the lock, scores every arm
once and writes data/e146/out/{results.json, oof.csv}.
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
from scipy.stats import binomtest, norm, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from app.e137 import features as F
from app.e137 import model as M137
from app.e140 import model as M140
from app.e141 import evaluate as E141
from app.e141 import panel as P
from app.e143 import model as M143
from app.e144 import data as D
from app.e144 import link as L
from app.e144 import model as MA
from app.e145 import OUT as O145
from app.e145.evaluate import Level
from app.e146 import OUT, PROTOCOL_VERSION, VERSION
from app.e146 import soil as S
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
PROTOCOL = BACKEND_DIR.parent / "docs" / "e146" / "PROTOCOL.md"
CODE = ["soil.py", "evaluate.py"]
SEED = 146
N_BOOT = 2000
LEADS = [1, 2, 3, 4]
T = {"R1_accuracy": 0.75, "R2_auc": 0.70, "R2_auc_ci_lower": 0.50, "R3_recall": 0.50, "R3_precision": 0.50, "R5_ece": 0.10,
     "bridge_rho_ci_lower": 0.50, "seed": SEED, "n_boot": N_BOOT, "leads": LEADS}
SHOCK = ["c_soil_anom_3m", "c_rain_anom_6m", "c_tc_4q", "c_agri_yoy", "c_fish_yoy"]
NEWS = ["nb_fssi", "nb_attention", "nb_fssi_delta"]
GOV = ["p_poverty", "p_subsistence", "p_poverty_gap", "p_density", "m_food_cpi_yoy", "m_rice_cpi_yoy"] + SHOCK
ARMS = ["E2E-clean", "QS", "QS-nosoil", "QS-N", "C4-link", "PERS", "LR-PSA", "LR-NLP", "LR-ALL"]
LT = L.LT


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e146"
    return {"protocol": _sha(PROTOCOL), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists() and "--deviation-d1" not in sys.argv:
        raise RuntimeError("E146 is already locked")
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(),
                             "hashes": _hashes(), "thresholds": T}, indent=2), newline="\n")


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E146 lock mismatch: {bad}")


def rows_at(lead: int, news: pd.DataFrame | None) -> pd.DataFrame:
    """E141 rows at this lead, with the measured absolute logit and H from E144's link table (features of lead `lead`)."""
    X = P.data(lead)
    lk = L.rows()[["key", "survey", "H", "y_abs", "se_abs", "q_star"]]
    X = X.merge(lk, on=["key", "survey"], how="inner")
    X["c_soil_anom_3m"] = [S.anomaly(k.replace(" ", ""), F.issue_date(int(y), lead)) for k, y in zip(X["key"], X["year"])]
    if news is not None:
        n = news[news["lead"] == lead].drop_duplicates(["key", "survey"])[["key", "survey"] + NEWS]
        X = X.merge(n, on=["key", "survey"], how="left")
    else:
        for c in NEWS:
            X[c] = np.nan
    return X.reset_index(drop=True)


class Shock:
    """LightGBM on link residuals of real survey rows, with a learned option of no shock (protocol section 4)."""

    def __init__(self, cols):
        self.cols = list(cols)

    def _make(self, tr, res):
        d = tr.copy()
        d["y"], d["se_y"] = res, d["se_abs"]
        d["q"] = norm.cdf(res / d["se_abs"].values)
        return d

    def fit(self, tr, res):
        d = self._make(tr, res).reset_index(drop=True)
        k = min(5, d["region"].nunique())
        pred = np.zeros(len(d))
        for a, b in GroupKFold(k).split(d, groups=d["region"]):
            pred[b] = M140.LGBNative("GBC", self.cols).fit(d.iloc[a]).predict_y(d.iloc[b])
        w = 1.0 / (d["se_abs"].values ** 2 + 0.05)
        self.use_ = bool(np.sum(w * (d["y"].values - pred) ** 2) < np.sum(w * d["y"].values ** 2))
        self.m_ = M140.LGBNative("GBC", self.cols).fit(d) if self.use_ else None
        return self

    def predict(self, X):
        return self.m_.predict_y(X) if self.use_ else np.zeros(len(X))


def area_forecast(Xa, T_q: int, h: int):
    """E144 Stage A level at horizon h for target quarter T_q, only labels published by the issue date."""
    i = T_q - 1 - h
    d = D.q_end(i)
    A = Xa[Xa["y"].notna() & (Xa["label_published"] <= d)]
    lv = MA.LGBLevel(MA.SETS["A LightGBM (full)"]).fit(A)
    q = Xa[(Xa["issue_qi"] == i) & (Xa["h"] == h)].set_index("area")
    mh, sh = lv.predict(q)
    return dict(zip(q.index, mh)), dict(zip(q.index, sh))


def origin_lead(oid, rounds, target, lead, news, Xa):
    X = rows_at(lead, news)
    tr, te = X[X["survey"].isin(rounds)].reset_index(drop=True), X[X["survey"] == target].reset_index(drop=True)
    an = M143.Anchored("hre", "lgbm").fit(tr, Level().fit(tr))
    yh, V = an.predict(te)
    tr = tr.assign(r_hat=an.lv_.oof_, r_var=0.0)                 # out-of-fold, earlier rounds only (protocol section 3)
    te = te.assign(r_hat=yh, r_var=V)
    m1, m0 = L.fit(tr, True), L.fit(tr, False)
    T_q = qindex(te["ref_quarter"].iloc[0])
    hm, hs = area_forecast(Xa, T_q, lead)
    mu1, v1 = L.predict(m1, te, te["sws_area"].map(hm).values, te["sws_area"].map(hs).values)
    mu0, v0 = L.predict(m0, te)
    A_tr = L.design(tr, True)
    res = tr["y_abs"].values - A_tr @ m1["beta"]
    out = te[E141.KEEP + ["y_abs", "se_abs", "q_star", "sws_area", "survey"]].loc[:, lambda d: ~d.columns.duplicated()].copy()
    out["origin"], out["lead"] = oid, lead
    z = lambda mu, v: norm.cdf((mu - LT) / np.sqrt(v))
    out["E2E-clean"], out["C4-link"] = z(mu1, v1), z(mu0, v0)
    out["mu_E2E-clean"], out["mu_C4-link"] = mu1, mu0
    used = {}
    for arm, cols in (("QS", SHOCK), ("QS-nosoil", [c for c in SHOCK if c != "c_soil_anom_3m"]), ("QS-N", SHOCK + NEWS)):
        s = Shock(cols).fit(tr, res)
        used[arm] = s.use_
        out[arm] = z(mu1 + s.predict(te), v1)
        out["mu_" + arm] = mu1 + s.predict(te)
    fill = {c: 0.0 for c in NEWS}                                # news columns are centred on 0 and can be all-missing in early rounds
    ltr, lte = tr.assign(q=tr["q_star"]).fillna(fill), te.fillna(fill)
    lr = lambda cols: M137.SoftLogit([c for c in cols if ltr[c].notna().any()]).fit(ltr).predict_proba(lte)
    out["LR-PSA"], out["LR-NLP"], out["LR-ALL"] = lr(M137.PSA_ONLY), lr(NEWS), lr(GOV + NEWS)
    all_ = L.rows().set_index(["key", "survey"])
    pv = pd.DataFrame([all_.loc[(k, s), ["y_abs", "se_abs"]] if (k, s) in all_.index else pd.Series({"y_abs": np.nan, "se_abs": np.nan})
                       for k, s in zip(te["key"], te["prev_survey"].fillna("NONE"))]).reset_index(drop=True)
    out["prev_y_abs"] = pv["y_abs"].astype(float).values
    out["PERS"] = norm.cdf((pv["y_abs"].astype(float).values - LT) / np.sqrt(pv["se_abs"].astype(float).values ** 2 + m0["s2"]))
    out["shock_used"] = json.dumps(used)
    return out, {"origin": oid, "lead": lead, "gamma": float(m1["beta"][2]), "delta": float(m1["beta"][1]), "s2": float(m1["s2"]), "shock_used": used,
                 "n_train": int(len(tr))}


def eb(p, q):
    return float(np.mean((p - q) ** 2 + q * (1 - q)))


def metrics(R, a) -> dict:
    d = R.dropna(subset=[a])
    p, q = d[a].values, d["q_star"].values
    bins = np.clip((p * 5).astype(int), 0, 4)
    m = {"n": int(len(d)), "eb": eb(p, q),
         "ece": float(sum(abs(p[bins == b].mean() - q[bins == b].mean()) * (bins == b).mean() for b in range(5) if (bins == b).any()))}
    dec = (np.abs(d["y_abs"] - LT) > 1.645 * d["se_abs"]).values
    yt, ph = (d["y_abs"][dec] > LT).astype(int).values, p[dec]
    yh = (ph >= 0.5).astype(int)
    tp, fp, tn, fn = int(((yh == 1) & (yt == 1)).sum()), int(((yh == 1) & (yt == 0)).sum()), int(((yh == 0) & (yt == 0)).sum()), int(((yh == 0) & (yt == 1)).sum())
    pr, rc = tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0
    ci = binomtest(tp + tn, len(yt)).proportion_ci(method="wilson")
    m.update({"n_decisive": int(len(yt)), "n_high": int(yt.sum()), "accuracy": (tp + tn) / len(yt), "accuracy_ci95": [float(ci.low), float(ci.high)],
              "precision": pr, "recall": rc, "f1": 2 * pr * rc / (pr + rc) if pr + rc else 0.0, "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
              "auc": float(roc_auc_score(yt, ph)) if len(set(yt)) == 2 else None, "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}})
    return m


def _diff_ci(R, a, b, unit, rng, n=N_BOOT):
    g = R.dropna(subset=[a, b])
    groups = list(g.groupby(unit).indices.values())
    pa, pb, q = g[a].values, g[b].values, g["q_star"].values
    v = []
    for _ in range(n):
        ii = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        v.append(eb(pa[ii], q[ii]) - eb(pb[ii], q[ii]))
    return {"diff": eb(pa, q) - eb(pb, q), "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], "n_units": len(groups)}


def _auc_ci(R, a, rng, n=N_BOOT):
    d = R.dropna(subset=[a])
    d = d[(np.abs(d["y_abs"] - LT) > 1.645 * d["se_abs"])]
    gs = list(d.groupby("region").indices.values())
    yt, p, v = (d["y_abs"] > LT).astype(int).values, d[a].values, []
    for _ in range(n):
        ii = np.concatenate([gs[i] for i in rng.integers(0, len(gs), len(gs))])
        if len(set(yt[ii])) == 2:
            v.append(roc_auc_score(yt[ii], p[ii]))
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def _change(R, a, rng, n=1000):
    d = R.dropna(subset=["mu_" + a, "prev_y_abs"])
    pc, dy = (d["mu_" + a] - d["prev_y_abs"]).values, (d["y_abs"] - d["prev_y_abs"]).values
    gs, v = list(d.groupby("region").indices.values()), []
    for _ in range(n):
        ii = np.concatenate([gs[i] for i in rng.integers(0, len(gs), len(gs))])
        v.append(spearmanr(pc[ii], dy[ii]).statistic)
    return {"rho": float(spearmanr(pc, dy).statistic), "ci95": [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))], "n": int(len(d))}


def bridge(rng) -> dict:
    h = pd.read_csv(BACKEND_DIR / "data" / "hfias" / "clean" / "enns_hfias.csv")
    h = h[(h["year"] == 2019)].dropna(subset=["fies_mod_sev_pct", "mod_sev_pct"])
    a, b = h["mod_sev_pct"].values, h["fies_mod_sev_pct"].values
    v = [spearmanr(a[i], b[i]).statistic for i in (rng.integers(0, len(a), len(a)) for _ in range(N_BOOT))]
    ci = [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
    return {"n": int(len(a)), "rho": float(spearmanr(a, b).statistic), "ci95": ci, "usable_for_live_update": bool(ci[0] > T["bridge_rho_ci_lower"])}


def score_all(news):
    Xa = MA.panel()
    jobs = [(o, r, t, h) for h in LEADS for o, r, t in E141.ORIGINS]
    res = Parallel(n_jobs=12)(delayed(origin_lead)(o, r, t, h, news, Xa) for o, r, t, h in jobs)
    return pd.concat([r[0] for r in res], ignore_index=True), [r[1] for r in res]


def smoke():
    Xa = MA.panel()
    o, r, t = E141.ORIGINS[1]
    out, _ = origin_lead(o, r, t, 1, None, Xa)
    assert len(out) and out["QS"].notna().all() and out["E2E-clean"].notna().all()
    print("smoke ok: rows", len(out), "columns", out.shape[1])


def run():
    verify_lock()
    rng = np.random.default_rng(SEED)
    news = pd.read_parquet(O145 / "news_features.parquet")
    R, params = score_all(news)
    R["cell"] = R["survey"] + "|" + R["sws_area"]
    R = R[R["PERS"].notna()].reset_index(drop=True)
    R.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    out = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(), "params": params, "by_lead": {}}
    for h, g in R.groupby("lead"):
        e = {"metrics": {a: metrics(g, a) for a in ARMS}, "by_origin": {o: {a: metrics(x, a) for a in ARMS} for o, x in g.groupby("origin")}}
        e["vs_persistence"] = {a: _diff_ci(g, a, "PERS", "region", rng) for a in ("E2E-clean", "QS", "QS-N", "C4-link")}
        e["QS_minus_E2E"] = _diff_ci(g, "QS", "E2E-clean", "region", rng)
        e["soil"] = _diff_ci(g, "QS", "QS-nosoil", "region", rng)
        e["QSN_minus_QS"] = _diff_ci(g, "QS-N", "QS", "region", rng)
        e["QSN_minus_E2E"] = _diff_ci(g, "QS-N", "E2E-clean", "region", rng)
        e["time_signal"] = {a: {"region": _diff_ci(g, a, "C4-link", "region", rng), "cell": _diff_ci(g, a, "C4-link", "cell", rng)} for a in ("E2E-clean", "QS", "QS-N")}
        e["calabarzon"] = g[g["province"].isin(E141.CAL)][["origin", "province", "survey", "y_abs", "se_abs", "q_star"] + ARMS].round(4).to_dict(orient="records")
        out["by_lead"][f"L{h}"] = e
    L1 = out["by_lead"]["L1"]
    sel = "E2E-clean"
    if L1["QS_minus_E2E"]["ci95"][1] < 0:
        sel = "QS"
    if L1["QSN_minus_QS" if sel == "QS" else "QSN_minus_E2E"]["ci95"][1] < 0:
        sel = "QS-N"
    mrl, rel = 0, {}
    stop = False
    for h in LEADS:
        g, e = R[R["lead"] == h], out["by_lead"][f"L{h}"]
        m, ci, ch = e["metrics"][sel], _auc_ci(g, sel, rng), _change(g, sel, rng)
        vs = e["vs_persistence"][sel]
        ck = {"R1_accuracy": m["accuracy"] >= T["R1_accuracy"], "R2_auc": (m["auc"] or 0) >= T["R2_auc"] and ci[0] > T["R2_auc_ci_lower"],
              "R3_recall_precision": m["recall"] >= T["R3_recall"] and m["precision"] >= T["R3_precision"], "R4_beats_persistence": vs["ci95"][1] < 0,
              "R5_calibration": m["ece"] <= T["R5_ece"], "R6_predicts_change": ch["ci95"][0] > 0}
        rel[f"L{h}"] = {"checks": {k: bool(v) for k, v in ck.items()}, "passes": bool(all(ck.values())), "auc_ci95": ci, "change": ch}
        if rel[f"L{h}"]["passes"] and not stop:
            mrl = h
        else:
            stop = True
    ts = L1["time_signal"][sel]
    out["selected_arm"], out["reliability"], out["maximum_reliable_lead"] = sel, rel, mrl
    out["time_signal_claim_L1"] = bool(ts["region"]["ci95"][1] < 0 and ts["cell"]["ci95"][1] < 0)
    out["bridge"] = bridge(rng)
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)), newline="\n")
    print(json.dumps({k: out[k] for k in ("selected_arm", "maximum_reliable_lead", "time_signal_claim_L1", "bridge")}, indent=1))


if __name__ == "__main__":
    {"lock": lock, "run": run, "smoke": smoke}[sys.argv[1]]()
