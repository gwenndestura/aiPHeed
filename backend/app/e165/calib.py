"""
E165: AUTO (app.e164.auto) + shrink-only score calibration, per docs/e165/PROTOCOL.md (committed before the run).

mu_CAL = b * mu_AUTO with b in [0.25, 1] learned from training rows only. b > 0 keeps every sign, so no HIGH/LOW class changes.

    python -m app.e165.calib eval    once; refuses if code or protocol are uncommitted, or if it already ran
    python -m app.e165.calib live    2027-Q1 forecast and seal, only if eval adopted CAL
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e164 import auto as U
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e165" / "out"
BMIN, BMAX = 0.25, 1.0
LOCKED = [BACKEND_DIR / "app" / "e165" / "calib.py", BACKEND_DIR.parent / "docs" / "e165" / "PROTOCOL.md"]
K = ["key", "survey", "lead"]


def wslope(mu, y, w) -> float:
    """Weighted least-squares slope of y on mu, with intercept."""
    mu, y, w = (np.asarray(v, float) for v in (mu, y, w))
    if len(mu) < 3 or np.std(mu) == 0:
        return float("nan")
    Z = np.column_stack([np.ones(len(mu)), mu]) * np.sqrt(w)[:, None]
    return float(np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0][1])


def clip_b(b_raw: float) -> float:
    return 1.0 if not np.isfinite(b_raw) else float(min(BMAX, max(BMIN, b_raw)))


def procedure(tr, te, AN):
    """app.e164.auto.run_procedure (kind ALL, no fixed configs), also returning the selected configuration's inner OOF scores."""
    tr = tr.reset_index(drop=True)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    res = []
    for a, l, f in U.menu("ALL"):
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
    best = min(res, key=lambda r: r["sse"])
    a, l, f = best["cfg"]
    atr, ate = AN[a]
    mu = ate if l == "NONE" else ate + U.LEARNERS[l](U.FS[f]).fit(tr.assign(e=y - atr)).predict(te)
    if best["calib"]:
        Z = np.column_stack([np.ones(len(tr)), best["oof_id"]]) * np.sqrt(w)[:, None]
        ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
        mu = ab[0] + ab[1] * mu
    tag = f"{a}|{l}|{f or '-'}|{'cal' if best['calib'] else 'id'}"
    return np.asarray(mu, float), tag, best["oof"], y, w


def estimate_b(tr, AN, oof_sel, y, w):
    """Temporal estimate when training holds >= 2 rounds, else the inner OOF of the selected configuration."""
    tr = tr.reset_index(drop=True)
    yr = tr["survey"].astype(str).str[-4:].astype(int).values
    rounds = sorted(set(yr))
    if len(rounds) >= 2:
        mus, ys, ws = [], [], []
        for r in rounds[1:]:
            A, B = yr < r, yr == r
            ANs = {k: (v[0][A], v[0][B]) for k, v in AN.items()}
            trA, trB = tr[A].reset_index(drop=True), tr[B].reset_index(drop=True)
            m_, _, _, _, _ = procedure(trA, trB, ANs)
            mus.append(m_)
            ys.append(trB["y_true"].values)
            ws.append((1.0 / (trB["se_true"] ** 2 + 0.05)).values)
        b_raw = wslope(np.concatenate(mus), np.concatenate(ys), np.concatenate(ws))
        return b_raw, "temporal:" + ",".join(str(r) for r in rounds[1:])
    return wslope(oof_sel, y, w), "inner_oof"


def calibrated(tr, te, AN):
    mu, tag, oof, y, w = procedure(tr, te, AN)
    sd_a, half_a = U.scale(y - oof, tr["gap_q"].values, te["gap_q"].values)
    b_raw, src = estimate_b(tr, AN, oof, y, w)
    b = clip_b(b_raw)
    sd_c, half_c = U.scale(y - b * oof, tr["gap_q"].values, te["gap_q"].values)
    mu_c = b * mu
    return {"mu_AUTO_r": mu, "AUTO_r": norm.cdf(mu / sd_a), "mu_CAL": mu_c, "CAL": norm.cdf(mu_c / sd_c), "half_CAL": half_c, "sd_CAL": sd_c,
            "b_raw": b_raw, "b": b, "b_source": src, "cfg": tag}


def task(survey, lead, H):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    if not M.released(i, Pv.ROUNDS):
        return None
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    r = calibrated(tr, te, AN)
    out = te[K].copy()
    for c in ("mu_AUTO_r", "AUTO_r", "mu_CAL", "CAL", "half_CAL", "sd_CAL"):
        out[c] = r[c]
    for c in ("b_raw", "b", "b_source", "cfg"):
        out[c] = r[c]
    return out


def _git(*a):
    return subprocess.run(["git", *a], cwd=BACKEND_DIR.parent, capture_output=True, text=True).stdout.strip()


def _check_lock():
    rel = [str(p.relative_to(BACKEND_DIR.parent)).replace("\\", "/") for p in LOCKED]
    if _git("status", "--porcelain", "--", *rel):
        sys.exit(f"uncommitted changes in {rel}: commit the protocol and code before the run (docs/e165/PROTOCOL.md)")
    if (OUT / "results.json").exists():
        sys.exit("E165 has already run once. Re-running is not allowed by the protocol.")
    return _git("log", "-1", "--format=%H", "--", *rel), {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in LOCKED}


def _bins(x, a):
    b = pd.cut(x[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
    return x.groupby(b, observed=False).agg(n=("y_high", "size"), mean_p=(a, "mean"), observed=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")


def evaluate():
    commit, hashes = _check_lock()
    OUT.mkdir(parents=True, exist_ok=True)
    H = E154.income()
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in (1, 2, 3, 4)) if x is not None]
    N = pd.concat(R, ignore_index=True)
    G = pd.read_csv(D / "e164" / "out" / "oof.csv")
    F = G.merge(N, on=K, how="inner")
    assert len(F) == len(G), (len(F), len(G))
    repro = float(np.max(np.abs(F["mu_AUTO"] - F["mu_AUTO_r"])))
    same_class = bool(((F["mu_CAL"] >= 0) == (F["mu_AUTO"] >= 0)).all())
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    rc, ra = LD.evaluate(F, "CAL", "CAL"), LD.evaluate(F, "AUTO", "AUTO")
    rng = np.random.default_rng(165)
    x1 = F[F["lead"] == 1].reset_index(drop=True)
    vs = {b: E7.diff_ci(x1, "CAL", b, "q_true", rng, n=2000) for b in ("AUTO", "E158", "PERS")}
    sc = {a: Pv.scale_test(x1, a, np.random.default_rng(165), n=2000) for a in ("CAL", "AUTO")}
    bt = N.groupby(["survey", "lead"])[["b_raw", "b", "b_source", "cfg"]].first().reset_index().to_dict("records")
    void = repro >= 1e-6
    decision = {"reproduction_max_abs_mu_AUTO": repro, "void": bool(void), "classes_identical": same_class,
                "max_reliable_lead_CAL": rc["maximum_reliable_lead"], "max_reliable_lead_AUTO": ra["maximum_reliable_lead"],
                "lead1_criteria_CAL": {k: bool(v) for k, v in rc["leads"][0]["criteria"].items()},
                "adopt_CAL": bool((not void) and same_class and rc["maximum_reliable_lead"] >= 1)}
    out = {"model": "E164 AUTO + shrink-only score calibration", "locked_commit": commit, "locked_hashes": hashes, "decision": decision, "b_by_issue": bt,
           "reliability_CAL": rc, "reliability_AUTO": ra, "lead1_brier_CAL_minus": {k: {"diff": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]} for k, v in vs.items()},
           "lead1_calibration": {a: {k: v for k, v in s.items()} for a, s in sc.items()}, "lead1_reliability_table": {"CAL": _bins(x1, "CAL"), "AUTO": _bins(x1, "AUTO")}}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print("locked commit", commit)
    print(json.dumps(decision, indent=1))
    print(pd.DataFrame(bt).to_string(index=False))
    for tag, rr in (("CAL", rc), ("AUTO", ra)):
        for r in rr["leads"]:
            print(tag, r["lead"], r["rows"], r["accuracy"], r["precision"], r["high_recall"], r["low_recall"], r["f1"], r["auc"], r["brier_soft"], r["calibration_slope_ci95"], {k: int(v) for k, v in r["criteria"].items()}, r["confusion"])
    print("lead1 Brier CAL minus", out["lead1_brier_CAL_minus"])
    print("lead1 calibration", json.dumps(out["lead1_calibration"]))
    print("reliability table", json.dumps(out["lead1_reliability_table"], indent=1))


def live():
    p = OUT / "results.json"
    if not p.exists() or not json.loads(p.read_text())["decision"]["adopt_CAL"]:
        sys.exit("live runs only after eval adopted CAL (docs/e165/PROTOCOL.md)")
    from app.e160.trace import build
    S, P, tr, m, te = build()
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    r = calibrated(tr, te, AN)
    pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))
    rows = [{"province": te["province"].iloc[k], "score": round(float(pct(r["mu_CAL"][k])), 1), "low90": round(float(pct(r["mu_CAL"][k] - r["half_CAL"][k])), 1),
             "high90": round(float(pct(r["mu_CAL"][k] + r["half_CAL"][k])), 1), "p_high": round(float(r["CAL"][k]), 3), "class": "HIGH" if r["mu_CAL"][k] >= 0 else "LOW",
             "auto_score": round(float(pct(r["mu_AUTO_r"][k])), 1)} for k in range(len(te))]
    out = {"issue": "2026-10-01", "target_quarter": "2027-Q1", "lead": 1, "config": r["cfg"], "b": r["b"], "b_raw": r["b_raw"], "b_source": r["b_source"], "forecasts": rows, "train_rows": int(len(tr))}
    (OUT / "live.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    sp = OUT / "sealed_2027-Q1.json"
    if not sp.exists():
        sp.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **out}, indent=1, default=float), newline="\n")
    print("seal", hashlib.sha256(sp.read_bytes()).hexdigest())
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"eval": evaluate, "live": live}[sys.argv[1]]()
