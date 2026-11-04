"""
E145 locked evaluation (docs/e145/PROTOCOL.md).

    python -m app.e145.evaluate lock | check | run

`check` is the only step allowed before the lock to touch labels: it reproduces E143's stored C4 at lead 1 and reads no
news column. `run` verifies the lock, then scores every arm once and writes data/e145/out/{results.json, oof.csv}.
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
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e137 import model as M137
from app.e139 import evaluate as E9
from app.e139 import model as M9
from app.e140 import model as M140
from app.e141 import evaluate as E141
from app.e141 import panel as P
from app.e142 import evaluate as E142
from app.e143 import OUT as O143
from app.e143 import evaluate as E143
from app.e143 import model as M143
from app.e145 import OUT, PROTOCOL_VERSION, VERSION
from app.e145.features import BC_COLS, LEADS, RAW_COLS
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
PROTOCOL = BACKEND_DIR.parent / "docs" / "e145" / "PROTOCOL.md"
CODE = ["collect.py", "news.py", "features.py", "evaluate.py"]
SEED = 145
N_BOOT = 2000
N_PLACEBO = 30
T = {"R1_accuracy": 0.75, "R2_auc": 0.70, "R2_auc_ci_lower": 0.50, "R3_recall": 0.50, "R3_precision": 0.50, "R5_ece": 0.10,
     "alpha": 0.05, "seed": SEED, "n_boot": N_BOOT, "n_placebo": N_PLACEBO, "leads": LEADS}
ARMS = ["G", "N", "GN", "GNB", "C4", "FULL", "LR-PSA", "LR-NLP", "LR-ALL"]
HIST = M9.HIST


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e145"
    return {"protocol": _sha(PROTOCOL), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists():
        raise RuntimeError("E145 is already locked")
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(),
                             "hashes": _hashes(), "thresholds": T}, indent=2), newline="\n")


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E145 lock mismatch: {bad}")


class Auto(M140.LGBAuto):
    """E140's nested LT/GBC choice with extra columns added to both candidates; `only` replaces the columns."""

    def __init__(self, extra=(), only=None):
        self.extra, self.only = list(extra), only

    def fit(self, tr):
        lt = list(self.only) if self.only else [c for c in M140.LT_FEATURES if c not in HIST] + self.extra
        gb = list(self.only) if self.only else [c for c in M140.GBC_FEATURES if c not in HIST] + self.extra
        a = M140.LGBNative("LT", lt).fit(tr)
        b = M140.LGBNative("GBC", gb).fit(tr)
        self.chosen_ = a if a.inner_eb_ <= b.inner_eb_ else b
        self.kind_, self.n_trees_ = self.chosen_.kind, self.chosen_.n_trees_
        return self


class Level(M143.Level):
    """E143's cross-fitted level, with the LightGBM learner replaced by Auto(extra)."""

    def __init__(self, extra=()):
        self.extra = list(extra)
        self.kind = "lgbm"

    def fit(self, tr):
        tr = tr.reset_index(drop=True)
        k = min(5, tr["region"].nunique())
        self.oof_ = np.full(len(tr), np.nan)
        self.folds_ = []
        for a, b in GroupKFold(k).split(tr, groups=tr["region"]):
            m = Auto(self.extra).fit(tr.iloc[a])
            self.oof_[b] = m.predict_y(tr.iloc[b])
            self.folds_.append((set(tr["region"].iloc[b]), m))
        self.full_ = Auto(self.extra).fit(tr)
        return self


def panel(lead: int, news: pd.DataFrame | None, origin: str) -> pd.DataFrame:
    X = P.data(lead)
    if news is not None:
        n = news[(news["lead"] == lead) & (news["origin"] == origin)]
        X = X.merge(n[["key", "survey"] + RAW_COLS + BC_COLS], on=["key", "survey"], how="left")
    return X


def fit_predict(arm: str, tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
    if arm == "G":
        return Auto().fit(tr).predict_proba(te)
    if arm == "N":
        return Auto(only=BC_COLS).fit(tr).predict_proba(te)
    if arm == "GN":
        return Auto(RAW_COLS).fit(tr).predict_proba(te)
    if arm == "GNB":
        return Auto(BC_COLS).fit(tr).predict_proba(te)
    if arm == "C4":
        return M143.Anchored("hre", "lgbm").fit(tr, Level().fit(tr)).predict_proba(te)
    if arm == "FULL":
        return M143.Anchored("hre", "lgbm").fit(tr, Level(BC_COLS).fit(tr)).predict_proba(te)
    if arm == "LR-PSA":
        return M137.SoftLogit(M137.PSA_ONLY).fit(tr).predict_proba(te)
    fill = {c: 0.0 for c in BC_COLS}                             # corrected news is centred on 0 and can be all-missing in early rounds
    if arm == "LR-NLP":
        return M137.SoftLogit(BC_COLS).fit(tr.fillna(fill)).predict_proba(te.fillna(fill))
    if arm == "LR-ALL":
        return M137.SoftLogit([c for c in M140.LT_FEATURES if c not in HIST] + BC_COLS).fit(tr.fillna(fill)).predict_proba(te.fillna(fill))
    raise KeyError(arm)


def task(arm, lead, oid, rounds, target, news, shuffle_seed=None, mask=False):
    X = panel(lead, news, oid)
    if shuffle_seed is not None:
        r = np.random.default_rng(shuffle_seed)
        for s, g in X.groupby("survey"):
            perm = r.permutation(g.index.values)
            X.loc[g.index, BC_COLS] = X.loc[perm, BC_COLS].values
    tr, te = X[X["survey"].isin(rounds)].reset_index(drop=True), X[X["survey"] == target].reset_index(drop=True)
    if mask:
        r = np.random.default_rng(SEED)
        cols = [c for c in M140.LT_FEATURES if c not in HIST] + (BC_COLS if arm in ("FULL", "GNB") else [])
        te = te.copy()
        for c in cols:
            te.loc[r.random(len(te)) < 0.20, c] = np.nan
    p = fit_predict(arm, tr, te)
    train_p = fit_predict(arm, tr, tr) if arm in ("G", "GNB", "C4", "FULL") and shuffle_seed is None and not mask else None
    return {"arm": arm, "lead": lead, "origin": oid, "key": te["key"].values, "p": p,
            "train_eb": float(M137.expected_brier(train_p, tr["q"])) if train_p is not None else None}


def check():
    """Reproduce stored E143 C4 at lead 1 with the Level/Auto wrappers, on no news. Reads labels only through E143's own rows."""
    ref = pd.read_csv(O143 / "oof_rolling.csv")
    worst = 0.0
    for oid, rounds, target in E141.ORIGINS:
        X = P.data(1)
        tr, te = X[X["survey"].isin(rounds)].reset_index(drop=True), X[X["survey"] == target].reset_index(drop=True)
        p = fit_predict("C4", tr, te)
        r = ref[ref["origin"] == oid].set_index("key").loc[te["key"], "C4 HRE-LGBM-X"].values
        worst = max(worst, float(np.abs(p - r).max()))
    print("max |C4 - stored E143 C4| =", worst)
    if worst > 1e-9:
        raise SystemExit("C4 does not reproduce E143")


def _rel(arm, R, res_vs, auc_ci, chg):
    L = E9.metrics(R, arm)
    ck = {"R1_accuracy": L.get("accuracy", 0) >= T["R1_accuracy"],
          "R2_auc": L.get("auc", 0) >= T["R2_auc"] and auc_ci[0] > T["R2_auc_ci_lower"],
          "R3_recall_precision": L.get("recall_elevated", 0) >= T["R3_recall"] and (L.get("precision_elevated") or 0) >= T["R3_precision"],
          "R4_beats_persistence": res_vs["ci95"][1] < 0, "R5_calibration": L["ece"] <= T["R5_ece"],
          "R6_predicts_change": chg["ci95"][0] > 0}
    return {"checks": {k: bool(v) for k, v in ck.items()}, "passes": bool(all(ck.values()))}


def run():
    verify_lock()
    check()
    rng = np.random.default_rng(SEED)
    news = pd.read_parquet(OUT / "news_features.parquet")
    ref = pd.read_csv(O143 / "oof_rolling.csv")
    jobs = [(a, h, o, r, t) for a in ARMS for h in LEADS for o, r, t in E141.ORIGINS]
    print("fits", len(jobs), flush=True)
    res_ = Parallel(n_jobs=18)(delayed(task)(*j, news) for j in jobs)
    base = ref[E141.KEEP + ["origin", "PERS", "REGPREV", "NAT"]].copy()
    tables = {}
    for h in LEADS:
        R = base.copy()
        for r in res_:
            if r["lead"] != h:
                continue
            s = pd.Series(r["p"], index=r["key"])
            m = R["origin"] == r["origin"]
            R.loc[m, r["arm"]] = R.loc[m, "key"].map(s)
        tables[h] = R
        R.assign(lead=h).to_csv(OUT / "oof.csv", mode="w" if h == LEADS[0] else "a", header=h == LEADS[0], index=False)
    names = ARMS + ["PERS", "REGPREV", "NAT"]
    out = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(), "by_lead": {}}
    news_p = {}
    for h, R in tables.items():
        D = E143._boot(R, ARMS, "PERS", rng, N_BOOT)
        DN = E143._boot(R, ["FULL"], "C4", rng, N_BOOT)["FULL"]
        DG = E143._boot(R, ["GNB", "GN"], "G", rng, N_BOOT)
        e = {"metrics": {n: E9.metrics(R, n) for n in names}, "metrics_by_origin": {o: {n: E9.metrics(g, n) for n in names} for o, g in R.groupby("origin")}}
        for n in names:
            pt = (R[n] >= 0.5).astype(int)
            e["metrics"][n]["accuracy_all_rows_point_estimate"] = float((pt == (R["y"] > 0).astype(int)).mean())
        e["vs_persistence"] = {a: {"diff": float(M137.expected_brier(R[a], R["q"]) - M137.expected_brier(R["PERS"], R["q"])),
                                   "ci95": [float(np.percentile(D[a], 2.5)), float(np.percentile(D[a], 97.5))]} for a in ARMS}
        e["news"] = {"FULL_minus_C4": {"diff": float(M137.expected_brier(R["FULL"], R["q"]) - M137.expected_brier(R["C4"], R["q"])),
                                       "ci95": [float(np.percentile(DN, 2.5)), float(np.percentile(DN, 97.5))], "p_ge_0": float(np.mean(DN >= 0))},
                     "GNB_minus_G": {"diff": float(M137.expected_brier(R["GNB"], R["q"]) - M137.expected_brier(R["G"], R["q"])),
                                     "ci95": [float(np.percentile(DG["GNB"], 2.5)), float(np.percentile(DG["GNB"], 97.5))]},
                     "GN_minus_G": {"diff": float(M137.expected_brier(R["GN"], R["q"]) - M137.expected_brier(R["G"], R["q"])),
                                    "ci95": [float(np.percentile(DG["GN"], 2.5)), float(np.percentile(DG["GN"], 97.5))]}}
        news_p[h] = e["news"]["FULL_minus_C4"]["p_ge_0"]
        e["reliability"] = {}
        for a in ("FULL", "C4", "GNB", "G"):
            ci = E9.auc_ci(R, a, rng)
            chg = E142.change_rho(R, a, rng)
            e["metrics"][a]["auc_ci95"], e["metrics"][a]["change_rho"] = ci, chg
            e["reliability"][a] = _rel(a, R, e["vs_persistence"][a], ci, chg)
        e["calabarzon"] = R[R["province"].isin(E141.CAL)][["origin", "province", "survey", "y", "se_y", "status", "q"] + names].round(4).to_dict(orient="records")
        out["by_lead"][f"L{h}"] = e
        print("lead", h, {a: round(e["metrics"][a]["expected_brier"], 4) for a in ("FULL", "C4", "G", "GNB", "PERS")},
              "accFULL", e["metrics"]["FULL"].get("accuracy"), flush=True)
    # Holm over leads 1-4 for the news claim
    order, stop, holm = sorted([1, 2, 3, 4], key=lambda h: news_p[h]), False, {}
    for k, h in enumerate(order):
        a = T["alpha"] / (4 - k)
        ok = (not stop) and news_p[h] < a / 2
        stop = stop or not ok
        holm[f"L{h}"] = {"p_ge_0": news_p[h], "level": 1 - a, "news_improves": ok}
    out["news_holm"] = holm
    # placebo at lead 1
    pl = Parallel(n_jobs=18)(delayed(task)("FULL", 1, o, r, t, news, 1000 + i) for i in range(N_PLACEBO) for o, r, t in E141.ORIGINS)
    R1 = tables[1]
    diffs = []
    for i in range(N_PLACEBO):
        Z = R1.copy()
        for r in pl[i * 3:(i + 1) * 3]:
            s = pd.Series(r["p"], index=r["key"])
            m = Z["origin"] == r["origin"]
            Z.loc[m, "pl"] = Z.loc[m, "key"].map(s)
        diffs.append(float(M137.expected_brier(Z["pl"], Z["q"]) - M137.expected_brier(Z["C4"], Z["q"])))
    real = out["by_lead"]["L1"]["news"]["FULL_minus_C4"]["diff"]
    out["placebo_L1"] = {"real_diff": real, "placebo_diffs": diffs, "share_placebo_better_or_equal": float(np.mean(np.array(diffs) <= real)),
                         "passes": bool(np.mean(np.array(diffs) <= real) <= 0.05)}
    # coverage tercile of news at lead 1
    cov = news[(news["lead"] == 1)].drop_duplicates(["key", "survey"])[["key", "survey", "n"]]
    Rc = R1.merge(cov, on=["key", "survey"], how="left")
    Rc["tercile"] = pd.qcut(Rc["n"].rank(method="first"), 3, labels=["low", "mid", "high"])
    out["news_by_coverage_L1"] = {str(t): {"n": int(len(g)), "mean_articles": float(g["n"].mean()),
                                           "FULL_minus_C4": float(M137.expected_brier(g["FULL"], g["q"]) - M137.expected_brier(g["C4"], g["q"]))} for t, g in Rc.groupby("tercile", observed=True)}
    # missing data
    ms = Parallel(n_jobs=6)(delayed(task)(a, 1, o, r, t, news, None, True) for a in ("C4", "FULL") for o, r, t in E141.ORIGINS)
    Zm = R1.copy()
    for r in ms:
        s = pd.Series(r["p"], index=r["key"])
        m = Zm["origin"] == r["origin"]
        Zm.loc[m, r["arm"] + "_m"] = Zm.loc[m, "key"].map(s)
    out["missing_20pct_L1"] = {a: {"eb": float(M137.expected_brier(Zm[a + "_m"], Zm["q"])), "change": float(M137.expected_brier(Zm[a + "_m"], Zm["q"]) - M137.expected_brier(Zm[a], Zm["q"]))} for a in ("C4", "FULL")}
    # overfitting
    out["train_vs_test_L1"] = {f"{r['arm']}|{r['origin']}": {"train_eb": r["train_eb"]} for r in res_ if r["lead"] == 1 and r["train_eb"] is not None}
    # maximum reliable lead
    mrl = {}
    for a in ("FULL", "C4", "GNB", "G"):
        m = 0
        for h in LEADS:
            if out["by_lead"][f"L{h}"]["reliability"][a]["passes"]:
                m = h
            else:
                break
        mrl[a] = m
    out["maximum_reliable_lead"] = mrl
    p = out["by_lead"]["L1"]
    out["decisions"] = {"H_N145_news_improves_L1": bool(holm["L1"]["news_improves"] and out["placebo_L1"]["passes"]),
                        "maximum_reliable_lead_FULL": mrl["FULL"], "L1_reliability_FULL": p["reliability"]["FULL"]}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)), newline="\n")
    print(json.dumps(out["decisions"], indent=1))


if __name__ == "__main__":
    {"lock": lock, "run": run, "check": check}[sys.argv[1]]()
