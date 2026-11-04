"""
E147 locked evaluation (docs/e147/PROTOCOL.md).

    python -m app.e147.evaluate smoke | lock | predict | score

smoke    runs one development origin, prints no metric
lock     hashes protocol, code, thresholds and the sealed label file
predict  verifies the lock, scores development rows, selects the arm, predicts 2021 and live for every arm and lead, then hashes the predictions
score    verifies the prediction hash, opens the sealed labels once, writes results.json. Refuses to run twice.
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
from sklearn.model_selection import GroupKFold

from app.e137 import model as M137
from app.e140 import model as M140
from app.e145.features import BC_COLS, RAW_COLS
from app.e147 import OUT, PROTOCOL_VERSION, RAW, VERSION
from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e147.news import YEAR
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
PROTOCOL = BACKEND_DIR.parent / "docs" / "e147" / "PROTOCOL.md"
CODE = ["features.py", "news.py", "evaluate.py"]
SEED = 147
N_BOOT = 2000
LEADS = [1, 2, 3, 4]
T = {"R1_accuracy": 0.75, "R2_auc": 0.70, "R3_recall": 0.50, "R3_precision": 0.50, "seed": SEED, "n_boot": N_BOOT, "leads": LEADS, "n_placebo": 30, "threshold_pct": 60.0}
ARMS = ["G", "GN", "GNB", "N", "DRIFT", "PERS", "LR-PSA", "LR-NLP", "LR-ALL"]
SEAL = OUT / "PREDICTIONS_SEAL.json"
LIVE_ISSUE = pd.Timestamp("2026-10-01")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e147"
    return {"protocol": _sha(PROTOCOL), "sealed_labels": _sha(Lb.SEALED), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists():
        raise RuntimeError("E147 is already locked")
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": _hashes(), "thresholds": T}, indent=2), newline="\n")


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E147 lock mismatch: {bad}")


class Change:
    """LightGBM on change from the province's own last survey. Forecast = previous + predicted change."""

    def __init__(self, cols):
        self.cols = list(cols)

    def _d(self, tr):
        d = tr.reset_index(drop=True).copy()
        d["y"] = d["y_true"] - d["y_prev"]
        d["se_y"] = np.sqrt(d["se_true"] ** 2 + d["se_prev"] ** 2)
        d["q"] = norm.cdf(d["y"] / d["se_y"])
        return d

    def fit(self, tr):
        d = self._d(tr)
        use = [c for c in self.cols if d[c].notna().any()]
        self.use_ = use
        pred = np.full(len(d), np.nan)
        for a, b in GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]):
            pred[b] = M140.LGBNative("GBC", use).fit(d.iloc[a]).predict_y(d.iloc[b])
        self.sigma_ = float(np.sqrt(np.mean((d["y"].values - pred) ** 2)))
        self.m_ = M140.LGBNative("GBC", use).fit(d)
        return self

    def predict(self, X):
        return X["y_prev"].values + self.m_.predict_y(X)

    def proba(self, X):
        return norm.cdf((self.predict(X) - Fe.LT) / self.sigma_)


def _logit(cols, tr, te):
    use = [c for c in cols if tr[c].notna().any()]
    t = tr.assign(q=tr["q_true"])
    return M137.SoftLogit(use).fit(t).predict_proba(te)


def _add_news(X, news, origin, lead):
    n = news[(news["origin"] == origin) & (news["lead"] == lead)][["key", "survey"] + RAW_COLS + BC_COLS]
    return X.merge(n, on=["key", "survey"], how="left")


def fit_all(tr, te, shuffle_seed=None, arms=ARMS):
    if shuffle_seed is not None:
        r = np.random.default_rng(shuffle_seed)
        for frame_ in (tr, te):
            for _, g in frame_.groupby("survey"):
                frame_.loc[g.index, BC_COLS] = frame_.loc[r.permutation(g.index.values), BC_COLS].values
    H, G = [c for c in Fe.HIST], Fe.GOV
    out = {}
    sets = {"G": H + G, "GN": H + G + RAW_COLS, "GNB": H + G + BC_COLS}
    for a in [x for x in sets if x in arms]:
        m = Change(sets[a]).fit(tr)
        out[a], out["mu_" + a], out["sigma_" + a] = m.proba(te), m.predict(te), np.full(len(te), m.sigma_)
    if "N" in arms:
        t2 = tr.assign(y=tr["y_true"], se_y=tr["se_true"], q=tr["q_true"])
        use = [c for c in BC_COLS if t2[c].notna().any()]
        m = M140.LGBNative("GBC", use).fit(t2)
        res = t2["y"].values - m.predict_y(t2)
        out["N"] = norm.cdf((m.predict_y(te) - Fe.LT) / float(np.std(res)))
    if "DRIFT" in arms:
        dy = (tr["y_true"] - tr["y_prev"]).values
        out["DRIFT"], out["mu_DRIFT"] = norm.cdf((te["y_prev"].values + dy.mean() - Fe.LT) / float(dy.std())), te["y_prev"].values + dy.mean()
    if "PERS" in arms:
        dy = (tr["y_true"] - tr["y_prev"]).values
        out["PERS"], out["mu_PERS"] = norm.cdf((te["y_prev"].values - Fe.LT) / float(np.sqrt(np.mean(dy ** 2)))), te["y_prev"].values
    if "LR-PSA" in arms:
        out["LR-PSA"] = _logit(Fe.PSA, tr, te)
    if "LR-NLP" in arms:
        f = {c: 0.0 for c in BC_COLS}
        out["LR-NLP"] = _logit(BC_COLS, tr.fillna(f), te.fillna(f))
    if "LR-ALL" in arms:
        f = {c: 0.0 for c in BC_COLS}
        out["LR-ALL"] = _logit(Fe.HIST + Fe.GOV + BC_COLS, tr.fillna(f), te.fillna(f))
    return out


def train_rows(rounds, lead, news, origin, base):
    b = base[base["survey"].isin(rounds)]
    X = Fe.frame(b, base, lead)
    t = b.merge(X, on=["key", "survey"])
    t = _add_news(t, news, origin, lead).rename(columns={"y": "y_true", "se_y": "se_true", "q_high": "q_true"})
    return t[t["y_prev"].notna()].reset_index(drop=True)


def dev_task(oid, rounds, target, lead, news, base):
    tr = train_rows(rounds, lead, news, oid, base)
    te = train_rows([target], lead, news, oid, base)
    p = fit_all(tr, te)
    o = te[["key", "province", "region", "island", "survey", "y_true", "se_true", "q_true", "y_prev", "p"]].copy()
    for k, v in p.items():
        o[k] = v
    o["origin"], o["lead"] = oid, lead
    return o


def targets_2021(base) -> pd.DataFrame:
    a = json.loads((OUT / "label_audit.json").read_text())
    names = {Lb.ALIAS.get(n.lower(), Lb.key(n)) for n in a["areas_2021_with_panel_features"]}
    r = base.drop_duplicates("key").set_index("key")
    t = pd.DataFrame({"key": sorted(names)})
    for c in ("province", "region", "sws_area", "island"):
        t[c] = t["key"].map(r[c])
    t["survey"], t["year"], t["ref_quarter"] = "ENNS2021", 2021, "2021-Q3"
    return t


def final_task(lead, news, base, shuffle_seed=None, arms=ARMS):
    tr = train_rows(["FNRI2015", "ENNS2018", "ENNS2019"], lead, news, "F", base)
    t = targets_2021(base)
    te = t.merge(Fe.frame(t, base, lead), on=["key", "survey"])
    te = _add_news(te, news, "F", lead)
    p = fit_all(tr, te, shuffle_seed, arms)
    o = te[["key", "province", "region", "island", "survey", "y_prev"]].copy()
    for k, v in p.items():
        o[k] = v
    o["lead"] = lead
    return o


def eb(p, q):
    return float(np.mean((p - q) ** 2 + q * (1 - q)))


def metrics(p, y, q=None) -> dict:
    p, y = np.asarray(p, float), np.asarray(y, int)
    h = (p >= 0.5).astype(int)
    tp, fp, tn, fn = int(((h == 1) & (y == 1)).sum()), int(((h == 1) & (y == 0)).sum()), int(((h == 0) & (y == 0)).sum()), int(((h == 0) & (y == 1)).sum())
    pr, rc = tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0
    q_ = y.astype(float) if q is None else np.asarray(q, float)
    bins = np.clip((p * 5).astype(int), 0, 4)
    return {"n": int(len(y)), "n_high": int(y.sum()), "accuracy": (tp + tn) / len(y), "precision": pr, "recall": rc, "f1": 2 * pr * rc / (pr + rc) if pr + rc else 0.0,
            "false_negative_rate": fn / (tp + fn) if tp + fn else None, "false_alarm_rate": fp / (fp + tn) if fp + tn else None, "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
            "brier": eb(p, q_), "ece": float(sum(abs(p[bins == b].mean() - q_[bins == b].mean()) * (bins == b).mean() for b in range(5) if (bins == b).any())), "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}}


def diff_ci(R, a, b, q, rng, n=N_BOOT):
    gs = list(R.groupby("region").indices.values())
    pa, pb, Q = R[a].values, R[b].values, R[q].values
    v = [eb(pa[i], Q[i]) - eb(pb[i], Q[i]) for i in (np.concatenate([gs[j] for j in rng.integers(0, len(gs), len(gs))]) for _ in range(n))]
    return {"diff": eb(pa, Q) - eb(pb, Q), "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], "n_regions": len(gs), "p_ge_0": float(np.mean(np.array(v) >= 0))}


def smoke():
    base = Fe.base_rows()
    news = pd.read_parquet(OUT / "news_features.parquet")
    o = dev_task("O2", ["FNRI2015"], "ENNS2018", 1, news, base)
    f = final_task(1, news, base)
    assert len(o) and f["G"].notna().all() and f["GNB"].notna().all()
    print("smoke ok: dev rows", len(o), "final rows", len(f), "inputs with data at the 2021 issue:")
    t = targets_2021(base)
    X = Fe.frame(t, base, 1)
    print(X[Fe.GOV + Fe.HIST].notna().mean().round(2).to_dict())


def predict():
    verify_lock()
    if SEAL.exists():
        raise RuntimeError("predictions are already sealed")
    rng = np.random.default_rng(SEED)
    base, news = Fe.base_rows(), pd.read_parquet(OUT / "news_features.parquet")
    dev = Parallel(n_jobs=8)(delayed(dev_task)(o, r, t, h, news, base) for h in LEADS for o, r, t in (("O2", ["FNRI2015"], "ENNS2018"), ("O3", ["FNRI2015", "ENNS2018"], "ENNS2019")))
    D = pd.concat(dev, ignore_index=True)
    D["y_high"] = (D["y_true"] >= Fe.LT).astype(int)
    D.to_csv(OUT / "oof_dev.csv", index=False, lineterminator="\n")
    res = {"by_lead": {}}
    for h, g in D.groupby("lead"):
        res["by_lead"][f"L{h}"] = {"metrics": {a: metrics(g[a], g["y_high"], g["q_true"]) for a in ARMS}, "by_origin": {o: {a: metrics(x[a], x["y_high"], x["q_true"]) for a in ("G", "GNB", "PERS", "DRIFT")} for o, x in g.groupby("origin")},
                                   "G_minus_PERS": diff_ci(g, "G", "PERS", "q_true", rng), "G_minus_DRIFT": diff_ci(g, "G", "DRIFT", "q_true", rng), "GNB_minus_G": diff_ci(g, "GNB", "G", "q_true", rng)}
    sel = "GNB" if res["by_lead"]["L1"]["GNB_minus_G"]["ci95"][1] < 0 else "G"
    res["selected_arm_on_development"] = sel
    (OUT / "dev_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    F = pd.concat(Parallel(n_jobs=4)(delayed(final_task)(h, news, base) for h in LEADS), ignore_index=True)
    F.to_csv(OUT / "predictions_2021.csv", index=False, lineterminator="\n")
    pl = Parallel(n_jobs=16)(delayed(final_task)(1, news, base, 2000 + i, ["GNB"]) for i in range(T["n_placebo"]))
    pd.concat([p.assign(draw=i) for i, p in enumerate(pl)], ignore_index=True)[["key", "GNB", "draw"]].to_csv(OUT / "placebo_2021.csv", index=False, lineterminator="\n")
    seal = {"selected_arm": sel, "sealed_utc": datetime.now(timezone.utc).isoformat(), "predictions_sha256": _sha(OUT / "predictions_2021.csv"), "placebo_sha256": _sha(OUT / "placebo_2021.csv"), "labels_sha256": _sha(Lb.SEALED)}
    SEAL.write_text(json.dumps(seal, indent=1), newline="\n")
    print(json.dumps(seal, indent=1))
    print("dev L1", {a: round(res["by_lead"]["L1"]["metrics"][a]["accuracy"], 3) for a in ARMS}, {a: round(res["by_lead"]["L1"]["metrics"][a]["brier"], 3) for a in ARMS})


def score():
    s = json.loads(SEAL.read_text())
    if _sha(OUT / "predictions_2021.csv") != s["predictions_sha256"] or _sha(Lb.SEALED) != s["labels_sha256"]:
        raise RuntimeError("seal mismatch")
    if (OUT / "results.json").exists():
        raise RuntimeError("sealed labels were already scored")
    rng = np.random.default_rng(SEED + 1)
    L = pd.read_csv(Lb.SEALED)
    w = L[L["fs_survey_category"] == "Food Insecure Households"].drop_duplicates("key")[["key", "province_name", "pct"]]
    P_ = pd.read_csv(OUT / "predictions_2021.csv").merge(w, on="key", how="left")
    miss = sorted(P_.loc[P_["pct"].isna(), "key"].unique())
    P_ = P_[P_["pct"].notna()].copy()
    P_["y_true"], P_["y_high"] = Fe._logit(P_["pct"]), (P_["pct"] >= 60.0).astype(int)
    se_y = 0.03 / (P_["pct"] / 100 * (1 - P_["pct"] / 100))                   # flagged: SE not published in the Heat Map; about 3 points as in 2018-2019 provinces
    P_["q_true"] = norm.cdf((P_["y_true"] - Fe.LT) / se_y)
    P_.to_csv(OUT / "oof_2021.csv", index=False, lineterminator="\n")
    sel, out = s["selected_arm"], {"selected_arm": s["selected_arm"], "missing_labels": miss, "by_lead": {}, "version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat()}
    mrl, stop = 0, False
    for h, g in P_.groupby("lead"):
        e = {"metrics": {a: metrics(g[a], g["y_high"], g["q_true"]) for a in ARMS}, "always_high_accuracy": float(g["y_high"].mean()), "always_low_accuracy": float(1 - g["y_high"].mean())}
        e["sel_minus_PERS"] = diff_ci(g, sel, "PERS", "q_true", rng)
        e["sel_minus_DRIFT"] = diff_ci(g, sel, "DRIFT", "q_true", rng)
        e["GNB_minus_G"] = diff_ci(g, "GNB", "G", "q_true", rng)
        e["GN_minus_G"] = diff_ci(g, "GN", "G", "q_true", rng)
        pc, dy = (g["mu_" + sel] - g["y_prev"]).values, (g["y_true"] - g["y_prev"]).values
        gs, v = list(g.groupby("region").indices.values()), []
        for _ in range(1000):
            i = np.concatenate([gs[j] for j in rng.integers(0, len(gs), len(gs))])
            v.append(spearmanr(pc[i], dy[i]).statistic)
        chg = {"rho": float(spearmanr(pc, dy).statistic), "ci95": [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]}
        pp = g[sel].values
        sim = [metrics(pp, (rng.random(len(pp)) < pp).astype(int))["ece"] for _ in range(2000)]
        ece95 = float(np.percentile(sim, 95))
        m = e["metrics"][sel]
        ck = {"R1_accuracy": m["accuracy"] >= T["R1_accuracy"], "R2_auc": (m["auc"] or 0) >= T["R2_auc"], "R3_recall_precision": m["recall"] >= T["R3_recall"] and m["precision"] >= T["R3_precision"],
              "R4_beats_persistence": e["sel_minus_PERS"]["ci95"][1] < 0, "R5_calibration": m["ece"] <= ece95, "R6_predicts_change": chg["ci95"][0] > 0}
        e["reliability"] = {"checks": {k: bool(x) for k, x in ck.items()}, "passes": bool(all(ck.values())), "change": chg, "ece_95th_perfect_calibration": ece95}
        lz = g[g["island"] == "Luzon"]
        e["differentiation"] = {"spearman_all": float(spearmanr(g["mu_" + sel], g["y_true"]).statistic), "spearman_luzon": float(spearmanr(lz["mu_" + sel], lz["y_true"]).statistic), "n_luzon": int(len(lz)), "pers_spearman_all": float(spearmanr(g["y_prev"], g["y_true"]).statistic)}
        e["calabarzon"] = g[g["province"].isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])][["province", "pct", "y_high", sel, "G", "GNB", "PERS", "DRIFT", "mu_" + sel]].round(4).to_dict(orient="records")
        out["by_lead"][f"L{h}"] = e
        if e["reliability"]["passes"] and not stop:
            mrl = int(h)
        else:
            stop = True
    out["maximum_reliable_lead"] = mrl
    g1 = P_[P_["lead"] == 1]
    D = pd.read_csv(OUT / "placebo_2021.csv").merge(g1[["key", "q_true"]], on="key")
    pl = [eb(x["GNB"].values, x["q_true"].values) - eb(g1.set_index("key").loc[x["key"], "G"].values, x["q_true"].values) for _, x in D.groupby("draw")]
    real = out["by_lead"]["L1"]["GNB_minus_G"]["diff"]
    out["placebo_L1"] = {"real_diff": real, "share_placebo_better_or_equal": float(np.mean(np.array(pl) <= real)), "draws": pl}
    out["news_claim_L1"] = bool(out["by_lead"]["L1"]["GNB_minus_G"]["ci95"][1] < 0 and out["placebo_L1"]["share_placebo_better_or_equal"] <= 0.05)
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps({k: out[k] for k in ("selected_arm", "maximum_reliable_lead", "news_claim_L1", "missing_labels")}, indent=1))


if __name__ == "__main__":
    {"smoke": smoke, "lock": lock, "predict": predict, "score": score}[sys.argv[1]]()
