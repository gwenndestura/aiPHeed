"""
E150 locked evaluation (docs/e150/PROTOCOL.md).

    python -m app.e150.evaluate smoke | lock | dev | seal_holdout | score_holdout | retro

dev            development comparison on 2018 and 2019; fixes the primary arm
seal_holdout   predicts the 12 unopened 2021 areas as of 2021-04-01, hashes the file
score_holdout  verifies the hash, reads those 12 labels once
retro          retrospective scoring on the opened 2021 provinces and the pool
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
from sklearn.metrics import roc_auc_score

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e148 import model as M8
from app.e149 import OUT as O149
from app.e150 import OUT, PROTOCOL_VERSION, VERSION
from app.e150 import model as M
from app.hfias.panel import norm as key_norm
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
Fe.LT = 0.0
SEED = 150
N_BOOT = 2000
LEADS = list(range(1, 9))
ROUNDS = ["NNS2013", "FNRI2015", "ENNS2018", "ENNS2019"]
ORIGIN = {"ENNS2018": "O2", "ENNS2019": "O3", "ENNS2021": "F"}
PROTOCOL = BACKEND_DIR.parent / "docs" / "e150" / "PROTOCOL.md"
CODE = ["acquire.py", "panel.py", "response.py", "news_v2.py", "model.py", "evaluate.py"]
T = {"threshold_pct": 50.0, "R1": 0.75, "R2": 0.70, "R2_lower": 0.50, "R3": 0.50, "R8": 0.50, "R9": [0.80, 0.98], "seed": SEED, "n_boot": N_BOOT, "leads": LEADS, "n_placebo": 30}
PRIMARY_POOL = ["A-H", "A-Hh", "A-G"]
ARMS = ["A-H", "A-Hh", "A-G", "A-GN", "A-frozen", "B-score", "DRIFT", "PERS", "LR-PSA", "LR-NLP", "LR-ALL"]
HOLD_SEAL = OUT / "HOLDOUT_SEAL.json"
PARENT = {"ANGELES CITY": "pampanga", "BAGUIO CITY": "benguet", "BUTUAN CITY": "agusan del norte", "CAGAYAN DE ORO CITY": "misamis oriental", "DAVAO CITY": "davao del sur", "ILOILO CITY": "iloilo", "ISABELA CITY": "basilan", "CITY OF ISABELA": "basilan", "LAPU-LAPU CITY": "cebu", "MANDAUE CITY": "cebu",
          "OLONGAPO CITY": "zambales", "PUERTO PRINCESA CITY": "palawan", "TACLOBAN CITY": "leyte", "ZAMBOANGA CITY": "zamboanga del sur", "BACOLOD CITY": "negros occidental", "CEBU CITY": "cebu", "COTABATO CITY": "maguindanao", "GENERAL SANTOS CITY": "south cotabato", "ILIGAN CITY": "lanao del norte", "LUCENA CITY": "quezon"}
NCR = {"CALOOCAN CITY", "LAS PIÑAS CITY", "MAKATI CITY", "MALABON CITY", "MANDALUYONG CITY", "MANILA CITY", "MARIKINA CITY", "PARAÑAQUE CITY", "PATEROS", "QUEZON CITY", "SAN JUAN CITY", "TAGUIG CITY", "DISTRICT I", "DISTRICT II", "DISTRICT III", "DISTRICT IV", "MUNTINLUPA CITY", "NAVOTAS CITY", "PASAY CITY", "PASIG CITY", "VALENZUELA CITY"}
HOLD = ["BACOLOD CITY", "BATANES", "CEBU CITY", "COTABATO CITY", "GENERAL SANTOS CITY", "ILIGAN CITY", "LUCENA CITY", "MUNTINLUPA CITY", "NAVOTAS CITY", "PASAY CITY", "PASIG CITY", "VALENZUELA CITY"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e150"
    return {"protocol": _sha(PROTOCOL), "sealed_labels": _sha(Lb.SEALED), "cpi": _sha(OUT / "cpi_panel.parquet"), "h": _sha(OUT / "h_signal.parquet"), "news": _sha(OUT / "news_v2_panel.parquet"), **{c: _sha(here / c) for c in CODE}, "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists() and "--deviation" not in sys.argv:
        raise RuntimeError("E150 is already locked")
    p.write_text(json.dumps({"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": _hashes(), "thresholds": T}, indent=2), newline="\n")


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E150 lock mismatch: {bad}")


def targets_2021(S):
    t = E7.targets_2021(S.base)
    t["T"] = M8.RQ["ENNS2021"]
    return t


def task(survey, lead, shuffle=None, arms_news=True):
    Fe.LT = 0.0
    S = M.Store()
    Tq, i = M8.RQ[survey], M8.RQ[survey] - lead
    if not M.released(i, ROUNDS):
        return None
    P = M.Pipeline(S, i, ROUNDS, ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = M.rows_for(S, tg, [lead], ORIGIN[survey])
    if te.empty:
        return None
    if shuffle is not None:
        r = np.random.default_rng(shuffle)
        for fr in (P.tr, te):
            for _, g in fr.groupby(["survey", "lead"]):
                fr.loc[g.index, M.NEWS] = fr.loc[r.permutation(g.index.values), M.NEWS].values
    fz = None if shuffle is not None else M.rows_for(S, tg, [lead], ORIGIN[survey], frozen=True)
    p = M.predict_all(P, te, fz)
    keep = ["key", "province", "region", "island", "survey", "T", "lead", "i", "y_anchor", "gap_q", "rq_anchor", "h_signal"] + [c for c in ("y_true", "se_true", "q_true", "p_true") if c in te]
    o = te[keep].copy()
    for k, v in p.items():
        o[k] = v
    o["loading"], o["sigma_base"], o["released"] = P.loading, P.sigma_base, "+".join(P.rel)
    return o


def met(g, a):
    m = E7.metrics(g[a].fillna(0.5), g["y_high"], g["q_true"])
    c = m["confusion"]
    m["low_recall"] = c["tn"] / (c["tn"] + c["fp"]) if c["tn"] + c["fp"] else None
    m["balanced_accuracy"] = (m["recall"] + m["low_recall"]) / 2 if m["low_recall"] is not None else None
    return m


def continuous(g, a) -> dict:
    mu = g["mu_" + a].values
    y = g["y_true"].values
    pct = 100 / (1 + np.exp(-mu))
    meas = 100 / (1 + np.exp(-y))
    sl = np.polyfit(mu, y, 1)
    return {"mae_points": float(np.mean(np.abs(pct - meas))), "rmse_points": float(np.sqrt(np.mean((pct - meas) ** 2))), "calibration_slope": float(sl[0]), "calibration_intercept": float(sl[1]), "spearman": float(spearmanr(mu, y).statistic), "change_rho": float(spearmanr(mu - g["y_anchor"].values, y - g["y_anchor"].values).statistic)}


def slope_ci(g, a, rng, n=1000):
    gs, v = list(g.groupby("region").indices.values()), []
    mu, y = g["mu_" + a].values, g["y_true"].values
    for _ in range(n):
        i = np.concatenate([gs[j] for j in rng.integers(0, len(gs), len(gs))])
        if np.ptp(mu[i]) > 0:
            v.append(np.polyfit(mu[i], y[i], 1)[0])
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def coverage(g, a="A-G"):
    q = g["q90_A-G"].values if "q90_A-G" in g else 1.645 * g["sigma_base"].values
    return float(np.mean(np.abs(g["y_true"].values - g["mu_" + a].values) <= q))


def smoke():
    f = task("ENNS2021", 1)
    d = task("ENNS2018", 1)
    assert f["A-G"].notna().all() and f["A-GN"].notna().all() and len(d)
    print("smoke ok", len(f), len(d), "trees G", f["n_trees_A-G"].iloc[0], "GN", f["n_trees_A-GN"].iloc[0], "loading", round(float(f["loading"].iloc[0]), 3), "released", f["released"].iloc[0])


def dev():
    verify_lock()
    rng = np.random.default_rng(SEED)
    D = pd.concat([x for x in Parallel(n_jobs=14)(delayed(task)(s, h) for s in ("ENNS2018", "ENNS2019") for h in LEADS) if x is not None], ignore_index=True)
    D["y_high"] = (D["y_true"] >= 0).astype(int)
    D.to_csv(OUT / "oof_dev.csv", index=False, lineterminator="\n")
    res = {"by_lead": {}}
    for h, g in D.groupby("lead"):
        e = {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "always_high_accuracy": float(g["y_high"].mean()), "metrics": {a: met(g, a) for a in ARMS if a in g}, "continuous": {a: continuous(g, a) for a in ("A-H", "A-Hh", "A-G", "A-GN", "DRIFT", "PERS")}, "coverage_A-G": coverage(g),
             "n_trees_A-G": float(g["n_trees_A-G"].mean()), "loading": float(g["loading"].mean())}
        for x, y in (("A-G", "PERS"), ("A-G", "DRIFT"), ("A-G", "A-H"), ("A-Hh", "A-H"), ("A-GN", "A-G"), ("B-score", "A-G")):
            e[f"{x}_minus_{y}"] = E7.diff_ci(g, x, y, "q_true", rng)
        res["by_lead"][f"L{h}"] = e
    b14 = {a: float(np.mean([res["by_lead"][f"L{h}"]["metrics"][a]["brier"] for h in (1, 2, 3, 4)])) for a in PRIMARY_POOL}
    best = min(b14, key=b14.get)
    sel = "A-G" if b14["A-G"] <= b14[best] + 0.001 else best
    if res["by_lead"]["L1"]["A-GN_minus_A-G"]["ci95"][1] < 0:
        sel = "A-GN"
    g1 = D[D["lead"] == 1]
    slope, ci, cov = continuous(g1, sel)["calibration_slope"], slope_ci(g1, sel, rng), coverage(g1, sel)
    is_prev = bool(ci[0] <= 1 <= ci[1] and 0.80 <= cov <= 0.98)
    bd = res["by_lead"]["L1"]["B-score_minus_A-G"]["ci95"][1]
    res["selection"] = {"pooled_brier_L1_4": b14, "primary_arm": sel, "approach_A_calibration_slope": slope, "slope_ci95": ci, "coverage": cov, "A_is_prevalence_on_development": is_prev, "classification_uses": "B-score" if (not is_prev and bd < 0) else sel}
    (OUT / "dev_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res["selection"], indent=1, default=float))
    f = lambda m: {k: (round(m[k], 3) if isinstance(m.get(k), float) else m.get(k)) for k in ("accuracy", "balanced_accuracy", "recall", "low_recall", "auc", "brier", "ece")}
    for L in ("L1", "L2"):
        print(L, res["by_lead"][L]["n"], res["by_lead"][L]["n_high"], {a: f(res["by_lead"][L]["metrics"][a]) for a in ("A-H", "A-Hh", "A-G", "A-GN", "B-score", "PERS", "DRIFT", "LR-PSA")})
        print({k: (round(res["by_lead"][L][k]["diff"], 4), [round(x, 4) for x in res["by_lead"][L][k]["ci95"]]) for k in res["by_lead"][L] if "_minus_" in k}, res["by_lead"][L]["continuous"]["A-G"], res["by_lead"][L]["n_trees_A-G"], res["by_lead"][L]["loading"])


def _city_rows():
    d = pd.read_csv(Lb.DEV)
    h = d[d["fs_survey_category"] == "Food Insecure Households"].copy()
    h = h[h["actual_year"].astype(str).isin(["2013", "2015", "2018", "2019"])]
    h["survey"] = h["actual_year"].astype(str).map({"2013": "NNS2013", "2015": "FNRI2015", "2018": "ENNS2018", "2019": "ENNS2019"})
    h["y"] = Fe._logit(h["pct"])
    return h


def seal_holdout():
    verify_lock()
    if HOLD_SEAL.exists():
        raise RuntimeError("holdout already sealed")
    S = M.Store()
    i = M8.RQ["ENNS2021"] - 1
    rel = M.released(i, ROUNDS)
    H = M.Hier().fit(S, rel)
    TQ = M8.RQ["ENNS2021"]
    shared_T = float(H.shared(np.array([TQ]))[0])
    cities = _city_rows()
    cities = cities[cities["survey"].isin(rel)]
    keys = S.base.drop_duplicates("key").set_index("key")

    def parent_rel(pk):
        x = keys.loc[[pk]].assign(T=TQ)
        i2 = TQ - 1
        g = S.s8.gov.loc[(pk, i2)]
        for c in M.LEVEL:
            x[c] = float(g[c]) if c in g.index else np.nan
        x["rc2011"] = Fe.radimer_2011().get(pk, np.nan)
        p = H.province(x, np.array([TQ]))
        return float(p["level"].iloc[0] + p["adj"].iloc[0])

    rows = []
    for _, r in cities.iterrows():
        n = r["province_name"]
        if n in PARENT and PARENT[n] in keys.index:
            rows.append({"name": n, "kind": "city", "rel": r["y"] - H.N[r["survey"]], "parent_rel": parent_rel(PARENT[n])})
        elif n in NCR:
            rows.append({"name": n, "kind": "ncr", "rel": r["y"] - H.N[r["survey"]], "parent_rel": 0.0})
        elif n == "BATANES":
            rows.append({"name": n, "kind": "batanes", "rel": r["y"] - H.N[r["survey"]], "parent_rel": 0.0})
    R = pd.DataFrame(rows)
    city = R[R["kind"] == "city"]
    delta = float((city["rel"] - city["parent_rel"]).mean())
    ncr_mean = float(R[R["kind"] == "ncr"]["rel"].mean())
    bat = R[R["kind"] == "batanes"]
    errs = list((city["rel"] - city["parent_rel"] - delta).values) + list((R[R["kind"] == "ncr"]["rel"] - ncr_mean).values)
    sigma = float(np.sqrt(np.mean(np.square(errs))))
    out = []
    for n in HOLD:
        if n == "BATANES":
            rel_ = float(bat["rel"].mean() * H.tau2 / (H.tau2 + 0.05)) if len(bat) else 0.0
        elif n in NCR:
            rel_ = ncr_mean
        else:
            rel_ = parent_rel(PARENT[n]) + delta
        mu = shared_T + rel_
        out.append({"name": n, "mu_proposed": mu, "p_proposed": float(norm.cdf(mu / sigma)), "mu_shared_only": shared_T, "p_shared_only": float(norm.cdf(shared_T / sigma)), "p_latest_level": float(norm.cdf(H.last_n / sigma))})
    O = pd.DataFrame(out)
    released_high = float((_city_rows()[lambda d: d["survey"].isin(rel)]["pct"] >= 50).mean())
    O["majority_high_of_released_city_rows"] = released_high
    O.to_csv(OUT / "holdout_predictions.csv", index=False, lineterminator="\n")
    HOLD_SEAL.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), "predictions_sha256": _sha(OUT / "holdout_predictions.csv"), "labels_sha256": _sha(Lb.SEALED), "sigma": sigma, "city_offset": delta, "ncr_mean": ncr_mean, "n_rows_used": len(R), "released": rel}, indent=1), newline="\n")
    print(json.dumps(json.loads(HOLD_SEAL.read_text()), indent=1))


def score_holdout():
    s = json.loads(HOLD_SEAL.read_text())
    if _sha(OUT / "holdout_predictions.csv") != s["predictions_sha256"]:
        raise RuntimeError("holdout seal mismatch")
    if (OUT / "holdout_results.json").exists():
        raise RuntimeError("holdout already scored")
    L = pd.read_csv(Lb.SEALED)
    L = L[L["fs_survey_category"] == "Food Insecure Households"].drop_duplicates("province_name")[["province_name", "pct"]]
    O = pd.read_csv(OUT / "holdout_predictions.csv").merge(L, left_on="name", right_on="province_name", how="left")
    O["y_high"], O["y_true"] = (O["pct"] >= 50).astype(int), Fe._logit(O["pct"])
    O["q_true"] = norm.cdf(O["y_true"] / (0.03 / (O["pct"] / 100 * (1 - O["pct"] / 100))))
    res = {"n": int(len(O)), "n_high": int(O["y_high"].sum()), "always_high_accuracy": float(O["y_high"].mean()), "always_low_accuracy": float(1 - O["y_high"].mean()), "majority_rule_from_released": "HIGH" if O["majority_high_of_released_city_rows"].iloc[0] >= 0.5 else "LOW"}
    for a in ("proposed", "shared_only", "latest_level"):
        m = E7.metrics(O[f"p_{a}"], O["y_high"], O["q_true"])
        c = m["confusion"]
        m["low_recall"] = c["tn"] / (c["tn"] + c["fp"]) if c["tn"] + c["fp"] else None
        m["balanced_accuracy"] = (m["recall"] + m["low_recall"]) / 2 if m["low_recall"] is not None else None
        res[a] = m
    pct = 100 / (1 + np.exp(-O["mu_proposed"]))
    res["proposed_mae_points"], res["shared_mae_points"] = float(np.mean(np.abs(pct - O["pct"]))), float(np.mean(np.abs(100 / (1 + np.exp(-O["mu_shared_only"])) - O["pct"])))
    res["spearman"] = float(spearmanr(O["mu_proposed"], O["y_true"]).statistic)
    res["rows"] = O[["name", "pct", "y_high", "p_proposed", "p_shared_only"]].round(3).to_dict(orient="records")
    (OUT / "holdout_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, indent=1, default=float))


def retro():
    rng = np.random.default_rng(SEED + 1)
    sel = json.loads((OUT / "dev_results.json").read_text())["selection"]["primary_arm"]
    L = pd.read_csv(Lb.SEALED)
    w = L[L["fs_survey_category"] == "Food Insecure Households"].drop_duplicates("key")[["key", "pct"]]
    F = pd.concat([x for x in Parallel(n_jobs=8)(delayed(task)("ENNS2021", h) for h in LEADS) if x is not None], ignore_index=True).merge(w, on="key", how="left")
    F = F[F["pct"].notna()].copy()
    F["y_true"], F["y_high"] = Fe._logit(F["pct"]), (F["pct"] >= 50).astype(int)
    F["q_true"] = norm.cdf(F["y_true"] / (0.03 / (F["pct"] / 100 * (1 - F["pct"] / 100))))
    F.to_csv(OUT / "oof_2021_retrospective.csv", index=False, lineterminator="\n")
    D = pd.read_csv(OUT / "oof_dev.csv")
    Pool = pd.concat([D, F], ignore_index=True)
    old = pd.read_csv(O149 / "oof_2021.csv")[["key", "lead", "Q-G", "mu_Q-G"]].rename(columns={"Q-G": "E149", "mu_Q-G": "mu_E149"})
    F49 = F.merge(old, on=["key", "lead"], how="left")
    res = {"primary_arm": sel, "evidence_status": "retrospective; 2021 provinces opened by E148 and E149", "pool": {}, "only_2021": {}}
    mrl, stop = 0, False
    for label, X, store in (("pool", Pool, res["pool"]), ("only_2021", F, res["only_2021"])):
        for h, g in X.groupby("lead"):
            g = g.reset_index(drop=True)
            e = {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "always_high_accuracy": float(g["y_high"].mean()), "metrics": {a: met(g, a) for a in ARMS if a in g and g[a].notna().any()}, "continuous": {a: continuous(g, a) for a in ("A-H", "A-Hh", "A-G", "A-GN", "DRIFT", "PERS")}, "coverage": coverage(g, sel)}
            for x, y in ((sel, "PERS"), (sel, "DRIFT"), (sel, "A-H"), ("A-Hh", "A-H"), ("A-GN", "A-G"), ("B-score", sel)):
                if x != y:
                    e[f"{x}_minus_{y}"] = E7.diff_ci(g, x, y, "q_true", rng)
            z = g.dropna(subset=["A-frozen"])
            if len(z):
                e[f"{sel}_minus_frozen"] = E7.diff_ci(z, sel, "A-frozen", "q_true", rng)
            gs, ca, va = list(g.groupby("region").indices.values()), [], []
            mu, y, an, pp, yh = g["mu_" + sel].values, g["y_true"].values, g["y_anchor"].values, g[sel].values, g["y_high"].values
            for _ in range(1000):
                i = np.concatenate([gs[j] for j in rng.integers(0, len(gs), len(gs))])
                ca.append(spearmanr(mu[i] - an[i], y[i] - an[i]).statistic)
                if len(set(yh[i])) == 2:
                    va.append(roc_auc_score(yh[i], pp[i]))
            chg, auc_l = float(np.nanpercentile(ca, 2.5)), float(np.percentile(va, 2.5))
            ece95 = float(np.percentile([E7.metrics(pp, (rng.random(len(pp)) < pp).astype(int))["ece"] for _ in range(1000)], 95))
            m = e["metrics"][sel]
            nir = max(e["always_high_accuracy"], 1 - e["always_high_accuracy"])
            ck = {"R1": m["accuracy"] >= T["R1"], "R2": (m["auc"] or 0) >= T["R2"] and auc_l > T["R2_lower"], "R3": m["recall"] >= T["R3"] and m["precision"] >= T["R3"], "R4": e[f"{sel}_minus_PERS"]["ci95"][1] < 0, "R5": m["ece"] <= ece95, "R6": chg > 0, "R7": m["accuracy"] > nir, "R8": (m["low_recall"] or 0) >= T["R8"], "R9": T["R9"][0] <= e["coverage"] <= T["R9"][1]}
            e["gates"], e["passes"], e["auc_lower"], e["change_lower"] = {k: bool(v) for k, v in ck.items()}, bool(all(ck.values())), auc_l, chg
            store[f"L{h}"] = e
            if label == "pool":
                if e["passes"] and not stop:
                    mrl = int(h)
                else:
                    stop = True
    res["maximum_reliable_lead"] = mrl
    z = F49[F49["lead"] == 1]
    res["compare_E149_L1_2021"] = {"E150": met(z, sel), "E149": met(z, "E149"), "E150_minus_E149": E7.diff_ci(z, sel, "E149", "q_true", rng), "mae_E150": continuous(z, sel)["mae_points"], "mae_E149": float(np.mean(np.abs(100 / (1 + np.exp(-z["mu_E149"])) - z["pct"])))}
    # news: Holm on the pool, placebo on 2021 lead 1
    p = {h: res["pool"][f"L{h}"]["A-GN_minus_A-G"]["p_ge_0"] for h in (1, 2, 3, 4)}
    order, st, holm = sorted(p, key=p.get), False, {}
    for k, h in enumerate(order):
        a = 0.05 / (4 - k)
        ok = (not st) and p[h] < a / 2
        st = st or not ok
        holm[f"L{h}"] = {"p_ge_0": p[h], "level": 1 - a, "news_improves": ok}
    res["news_holm"] = holm
    pl = Parallel(n_jobs=12)(delayed(task)("ENNS2021", 1, 5000 + d) for d in range(T["n_placebo"]))
    g1 = F[F["lead"] == 1].set_index("key")
    vals = [E7.eb(x.set_index("key").loc[g1.index, "A-GN"].values, g1["q_true"].values) - E7.eb(g1["A-G"].values, g1["q_true"].values) for x in pl]
    real = float(E7.eb(g1["A-GN"].values, g1["q_true"].values) - E7.eb(g1["A-G"].values, g1["q_true"].values))
    res["placebo_L1"] = {"real_diff": real, "share_placebo_better_or_equal": float(np.mean(np.array(vals) <= real))}
    res["news_claim"] = bool(holm["L1"]["news_improves"] and res["placebo_L1"]["share_placebo_better_or_equal"] <= 0.05)
    (OUT / "retro_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps({k: res[k] for k in ("primary_arm", "maximum_reliable_lead", "news_claim", "news_holm", "placebo_L1")}, indent=1, default=float))


if __name__ == "__main__":
    {"smoke": smoke, "lock": lock, "dev": dev, "seal_holdout": seal_holdout, "score_holdout": score_holdout, "retro": retro}[sys.argv[1]]()
