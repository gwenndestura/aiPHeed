"""
E166: E164 AUTO with (Fix 1) every anchor shifted by a shrunk national drift nowcast and (Fix 4) the top-5 configurations,
ranked by AUTO's training-only inner score, averaged with equal weights. Per docs/e166/PROTOCOL.md.

    python -m app.e166.drift lock    check files, hash code, protocol and inputs (owner approval required first)
    python -m app.e166.drift eval    once; refuses if not locked, if anything changed since the lock, or if it already ran
    python -m app.e166.drift live    2027-Q1 forecast and seal, only if eval passed
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
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e160 import arms as A
from app.e164 import auto as U
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e166" / "out"
W, CAP, K_TOP = 0.5, 0.5, 5
LEADS = range(1, 9)
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")
KEY = ["key", "survey", "lead"]
VARIANTS = ("AUTO_R", "AVG", "DRIFT", "E166")
BASELINES = ("AUTO", "E158", "GNT", "GOV", "NEWS", "LR", "LR_NEWS", "PSA", "PERS", "ANCHOR")
CODE = [BACKEND_DIR / "app" / "e166" / "drift.py", BACKEND_DIR.parent / "docs" / "e166" / "PROTOCOL.md"]
INPUTS = [D / "e164" / "out" / "oof.csv", D / "e158" / "out" / "oof.csv", D / "e151" / "out" / "prov_oof.csv", E154.RAW / "regional_income_long.csv",
          D / "e147" / "raw" / "sealed_2021_labels.csv", D / "e147" / "raw" / "heatmap_provincial.jsonl"]
FILES = CODE + INPUTS


# ---------- Fix 1: drift ----------
def drift_value(slope: float, last_q: float, T: float) -> float:
    """D = clip(W * r * (T - last_q), -CAP, +CAP); r is the per-quarter slope of released national levels."""
    return float(np.clip(W * slope * (T - last_q), -CAP, CAP))


def drift_rows(Ca, d: pd.DataFrame) -> pd.DataFrame:
    assert {"i", "T"} <= set(d.columns), "rows need issue quarter i and target quarter T"
    out = []
    for i, T in zip(d["i"].astype(int), d["T"].astype(float)):
        hp = Ca.get(i)[0]
        n = len(hp.N)
        # hp.slope is per quarter (polyfit of N on M8.RQ quarter indices); T and hp.last_q are quarter indices too.
        # One released round: no slope exists, so D = 0 (the flat level of E151).
        Dv = drift_value(hp.slope, hp.last_q, T) if n >= 2 else 0.0
        out.append({"D": Dv, "r": float(hp.slope) if n >= 2 else 0.0, "gap": float(T - hp.last_q), "n_rounds": n})
    return pd.DataFrame(out, index=d.index)


# ---------- Fix 4: top-K ----------
def rank_top(sses, k=K_TOP):
    """Indices of the k lowest scores; ties go to the earlier menu position (stable)."""
    order = sorted(range(len(sses)), key=lambda j: (sses[j], j))
    return order[:min(k, len(order))]


def procedure(tr, te, AN):
    """app.e164.auto.run_procedure (kind ALL) scoring every configuration on training rows only; returns top-1 and top-5 forecasts."""
    tr = tr.reset_index(drop=True)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    res = []
    for a, l, f in U.menu("ALL"):
        try:
            atr, ate = AN[a]
            if l == "NONE":
                oof = atr.copy()
            else:
                oof = np.zeros(len(tr))
                for i_tr, i_te in folds:
                    d = tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])
                    oof[i_te] = atr[i_te] + U.LEARNERS[l](U.FS[f]).fit(d).predict(tr.iloc[i_te])
            sse_id = float(np.sum(w * (y - oof) ** 2))
            cal = np.zeros(len(tr))
            for i_tr, i_te in folds:
                Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
                ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
                cal[i_te] = ab[0] + ab[1] * oof[i_te]
            sse_cal = float(np.sum(w * (y - cal) ** 2))
            res.append({"cfg": (a, l, f), "sse": min(sse_id, sse_cal), "calib": sse_cal < sse_id, "oof": cal if sse_cal < sse_id else oof, "oof_id": oof})
        except Exception as ex:                                   # excluded and counted (PROTOCOL section 4)
            print("config failed", (a, l, f), repr(ex))
    top = rank_top([r["sse"] for r in res])
    mus, oofs, tags = [], [], []
    for j in top:
        r = res[j]
        a, l, f = r["cfg"]
        atr, ate = AN[a]
        mu = ate if l == "NONE" else ate + U.LEARNERS[l](U.FS[f]).fit(tr.assign(e=y - atr)).predict(te)
        if r["calib"]:
            Z = np.column_stack([np.ones(len(tr)), r["oof_id"]]) * np.sqrt(w)[:, None]
            ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
            mu = ab[0] + ab[1] * mu
        mus.append(np.asarray(mu, float))
        oofs.append(np.asarray(r["oof"], float))
        tags.append(f"{a}|{l}|{f or '-'}|{'cal' if r['calib'] else 'id'}")
    out = {}
    for name, sel in (("top1", [0]), ("top5", list(range(len(top))))):
        mu, oof = np.mean([mus[k] for k in sel], axis=0), np.mean([oofs[k] for k in sel], axis=0)
        sd, half = U.scale(y - oof, tr["gap_q"].values, te["gap_q"].values)
        out[name] = (mu, norm.cdf(mu / sd), half)
    return out, tags, len(res)


def task(survey, lead, H, mode="main"):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if not rel:
        return None
    if mode == "corrupt":                                          # as E164: unreleased rounds replaced by random values
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    Ca = A.Cache(S)
    d_tr, d_te = drift_rows(Ca, tr), drift_rows(Ca, te)
    ANd = {k: (v[0] + d_tr["D"].values, v[1] + d_te["D"].values) for k, v in AN.items()}
    o = te[KEY].copy()
    o["mode"] = mode
    runs = {"drift": procedure(tr, te, ANd)} if mode == "corrupt" else {"flat": procedure(tr, te, AN), "drift": procedure(tr, te, ANd)}
    names = {("flat", "top1"): "AUTO_R", ("flat", "top5"): "AVG", ("drift", "top1"): "DRIFT", ("drift", "top5"): "E166"}
    for (run, sel), name in names.items():
        if run in runs:
            mu, p, half = runs[run][0][sel]
            o[f"mu_{name}"], o[name], o[f"half_{name}"] = mu, p, half
    o["D"], o["r"], o["gap"], o["n_rounds"] = d_te["D"].values, d_te["r"].values, d_te["gap"].values, d_te["n_rounds"].values
    o["top5_drift"] = " ; ".join(runs["drift"][1])
    o["n_configs_fitted"] = runs["drift"][2]
    return o


# ---------- lock ----------
def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _preflight():
    miss = [str(p) for p in FILES if not p.exists()]
    if miss:
        sys.exit("missing files, nothing locked:\n  " + "\n  ".join(miss))


def lock():
    _preflight()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "lock.json").exists():
        sys.exit("already locked: one locked run only (docs/e166/PROTOCOL.md)")
    (OUT / "lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {str(p.relative_to(BACKEND_DIR.parent)): _sha(p) for p in FILES}}, indent=1), newline="\n")
    print("locked", {p.name: _sha(p)[:12] for p in FILES})


def _check_lock():
    lk = OUT / "lock.json"
    if not lk.exists():
        sys.exit("not locked: run `python -m app.e166.drift lock` first, after owner approval")
    h = json.loads(lk.read_text())["hashes"]
    bad = [p.name for p in FILES if h.get(str(p.relative_to(BACKEND_DIR.parent))) != _sha(p)]
    if bad:
        sys.exit(f"changed since lock: {bad}. The locked run is void; report it as such.")
    if (OUT / "results.json").exists():
        sys.exit("E166 has already run once. Re-running is not allowed by the protocol.")


# ---------- evaluation ----------
def cal_ci(g, a, n=2000):
    """Slope and intercept of y_true on mu_a, region bootstrap (as app.e151.prov.scale_test)."""
    rng = np.random.default_rng(166)
    regs = list(g.groupby("region").indices.values())
    mu, y = g[f"mu_{a}"].values, g["y_true"].values
    sl, ic = [], []
    for _ in range(n):
        i = np.concatenate([regs[j] for j in rng.integers(0, len(regs), len(regs))])
        if np.std(mu[i]) > 0:
            b1, b0 = np.polyfit(mu[i], y[i], 1)
            sl.append(b1)
            ic.append(b0)
    b1, b0 = np.polyfit(mu, y, 1)
    return {"slope": round(float(b1), 3), "slope_ci95": [round(float(np.percentile(sl, q)), 3) for q in (2.5, 97.5)],
            "intercept": round(float(b0), 3), "intercept_ci95": [round(float(np.percentile(ic, q)), 3) for q in (2.5, 97.5)]}


def cls(g, a):
    y, p = g["y_high"].values == 1, g[a].values >= .5
    tp, fp, fn, tn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
    prec, hr, lr = tp / max(1, tp + fp), tp / max(1, tp + fn), tn / max(1, tn + fp)
    return {"correct": tp + tn, "rows": len(g), "accuracy": round((tp + tn) / len(g), 3), "precision": round(prec, 3), "high_recall": round(hr, 3), "low_recall": round(lr, 3),
            "f1": round(2 * prec * hr / max(1e-9, prec + hr), 3), "auc": round(float(roc_auc_score(y, g[a])), 3), "brier": round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4),
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}}


def _bins(x, a):
    b = pd.cut(x[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
    return x.groupby(b, observed=False).agg(n=("y_high", "size"), mean_p=(a, "mean"), observed=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")


def evaluate():
    _preflight()
    _check_lock()
    H = E154.income()
    jobs = [(s, h, "main") for s in SURVEYS for h in LEADS] + [(s, 1, "corrupt") for s in SURVEYS]
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, m) for s, h, m in jobs) if x is not None]
    Al = pd.concat(R, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    main, cor = Al[Al["mode"] == "main"].drop(columns="mode"), Al[Al["mode"] == "corrupt"]
    E = pd.read_csv(D / "e158" / "out" / "oof.csv")
    G = pd.read_csv(D / "e151" / "out" / "prov_oof.csv")[KEY + ["GOV", "mu_GOV", "ANCHOR", "mu_ANCHOR"]]
    AU = pd.read_csv(D / "e164" / "out" / "oof.csv")[KEY + ["AUTO", "mu_AUTO", "half_AUTO"]]
    F = E.merge(G, on=KEY, how="left").merge(AU, on=KEY, how="left").merge(main, on=KEY, how="inner")
    assert len(F) == len(E), ("row mismatch with E158", len(F), len(E))
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    a4 = F[F["lead"] <= 4]
    repro = float(np.max(np.abs(a4["mu_AUTO"] - a4["mu_AUTO_R"])))
    x1 = F[F["lead"] == 1].reset_index(drop=True)
    lk = x1[KEY + ["mu_E166"]].merge(cor[KEY + ["mu_E166"]].rename(columns={"mu_E166": "mu_c"}), on=KEY)
    leak = float(np.max(np.abs(lk["mu_E166"] - lk["mu_c"])))
    rel = {v: LD.evaluate(F, v, v) for v in VARIANTS}
    rel["E158"] = LD.evaluate(F, "E158", "E158")
    rel["AUTO"] = LD.evaluate(a4.reset_index(drop=True), "AUTO", "AUTO")
    calib = {L: {a: cal_ci(g.reset_index(drop=True), a) for a in VARIANTS + ("E158",) + (("AUTO",) if L <= 4 else ())} for L, g in F.groupby("lead")}
    cover = {L: {a: round(float((np.abs(g[f"mu_{a}"] - g["y_true"]) <= g[f"half_{a}"]).mean()), 3) for a in VARIANTS} for L, g in F.groupby("lead")}
    rng = np.random.default_rng(166)
    comp1 = {b: {"metrics": cls(x1, b), "E166_minus_brier": (lambda d: {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]})(E7.diff_ci(x1, "E166", b, "q_true", rng, n=2000))} for b in BASELINES}
    by_lead = {}
    for L, g in F.groupby("lead"):
        g = g.reset_index(drop=True)
        bs = [b for b in ("E158", "GNT", "GOV", "PERS") + (("AUTO",) if L <= 4 else ())]
        by_lead[int(L)] = {v: cls(g, v) for v in VARIANTS} | {"E166_minus_brier": {b: (lambda d: {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]})(E7.diff_ci(g, "E166", b, "q_true", rng, n=2000)) for b in bs}}
    l1 = next(r for r in rel["E166"]["leads"] if r["lead"] == 1)
    c1 = cls(x1, "E166")
    void = bool(repro >= 1e-6 or leak >= 1e-9)
    decision = {"reproduction_max_abs_mu_AUTO": repro, "leakage_max_abs_change": leak, "void": void,
                "lead1_correct": c1["correct"], "lead1_criteria": {k: bool(v) for k, v in l1["criteria"].items()},
                "lead1_brier_E166_minus_AUTO": comp1["AUTO"]["E166_minus_brier"],
                "rule": {"C1_to_C6": bool(all(l1["criteria"].values())), "correct_ge_55": c1["correct"] >= 55, "brier_not_worse_than_AUTO": comp1["AUTO"]["E166_minus_brier"]["diff"] <= 0, "valid": not void},
                "max_reliable_lead_E166": rel["E166"]["maximum_reliable_lead"]}
    decision["pass"] = bool(all(decision["rule"].values()))
    drift_tbl = main.groupby(["survey", "lead"])[["D", "r", "gap", "n_rounds", "n_configs_fitted", "top5_drift"]].first().reset_index().to_dict("records")
    out = {"model": "E164 AUTO + national drift nowcast (W 0.5, CAP 0.5) + top-5 equal-weight averaging", "decision": decision, "drift_and_top5_by_cell": drift_tbl,
           "reliability": rel, "calibration_slope_intercept": calib, "coverage_90": cover, "lead1_vs_baselines": comp1, "by_lead": by_lead,
           "lead1_reliability_table": {"E166": _bins(x1, "E166"), "AUTO": _bins(x1, "AUTO")}}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(decision, indent=1))
    print(pd.DataFrame(drift_tbl).drop(columns="top5_drift").to_string(index=False))
    for v in VARIANTS + ("E158",):
        for r in rel[v]["leads"]:
            print(v, r["lead"], r["rows"], r["accuracy"], r["f1"], r["auc"], r["brier_soft"], r["calibration_slope_ci95"], {k: int(z) for k, z in r["criteria"].items()})
    print("lead1 calibration", json.dumps(calib[1]))
    print("lead1 vs baselines", json.dumps({b: [v["metrics"]["accuracy"], v["metrics"]["brier"], v["E166_minus_brier"]] for b, v in comp1.items()}))
    print("reliability table", json.dumps(out["lead1_reliability_table"]))


def live():
    p = OUT / "results.json"
    if not p.exists() or not json.loads(p.read_text())["decision"]["pass"]:
        sys.exit("live runs only after eval passed (docs/e166/PROTOCOL.md)")
    from app.e160.trace import build
    S, P, tr, m, te = build()
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    Ca = A.Cache(S)
    d_tr, d_te = drift_rows(Ca, tr), drift_rows(Ca, te)
    ANd = {k: (v[0] + d_tr["D"].values, v[1] + d_te["D"].values) for k, v in AN.items()}
    res, tags, nfit = procedure(tr, te, ANd)
    mu, pr, half = res["top5"]
    pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))
    rows = [{"province": te["province"].iloc[k], "score": round(float(pct(mu[k])), 1), "low90": round(float(pct(mu[k] - half[k])), 1), "high90": round(float(pct(mu[k] + half[k])), 1),
             "p_high": round(float(pr[k]), 3), "class": "HIGH" if mu[k] >= 0 else "LOW", "drift_D": round(float(d_te["D"].iloc[k]), 4)} for k in range(len(te))]
    out = {"issue": "2026-10-01", "target_quarter": "2027-Q1", "lead": 1, "top5": tags, "n_configs_fitted": nfit, "forecasts": rows, "train_rows": int(len(tr))}
    (OUT / "live.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    sp = OUT / "sealed_2027-Q1.json"
    if not sp.exists():
        sp.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **out}, indent=1, default=float), newline="\n")
    print("seal", hashlib.sha256(sp.read_bytes()).hexdigest())
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"lock": lock, "eval": evaluate, "live": live}[sys.argv[1]]()
