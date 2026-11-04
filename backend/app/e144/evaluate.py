"""
E144 locked evaluation (docs/e144/PROTOCOL.md).

    python -m app.e144.evaluate lock | run    -> data/e144/out/{PROTOCOL_LOCK.json, results.json, stage_a_oof.csv, e2e_oof.csv}
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from app.e144 import OUT, PROTOCOL_VERSION, VERSION
from app.e144 import link as L
from app.e144 import model as MA
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

PROTOCOL = BACKEND_DIR.parent / "docs" / "e144" / "PROTOCOL.md"
CODE = ["gnews.py", "data.py", "model.py", "link.py", "evaluate.py"]
T = {"R1_auc": 0.70, "R1_auc_ci_lower": 0.50, "R2_recall": 0.50, "R2_precision": 0.50, "R5_ece": 0.10,
     "primary_first_issue": "2022-Q1", "secondary_first_issue": "2014-Q1", "last_issue": "2025-Q4",
     "data_cutoff": "2026-10-01", "n_boot": 2000, "seed": 144, "alpha": 0.05}
MAIN, NONEWS, PERS = "A LightGBM (full)", "B5 LightGBM, no news", "B1 Persistence"
MODELS = [MAIN, NONEWS, "B6 LightGBM, news only", "B2 Logistic, combined", "B3 Logistic, government + history (PSA-only)",
          "B4 Logistic, news only (NLP-only)", PERS, "Climatology"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e144"
    return {"protocol": _sha(PROTOCOL), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists() and "--deviation-d1" not in sys.argv:
        raise RuntimeError("E144 is already locked")
    p.write_text(json.dumps({"version": VERSION, "protocol_version": PROTOCOL_VERSION,
                             "locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": _hashes(), "thresholds": T},
                            indent=2))


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E144 lock mismatch: {bad}")


def metrics(y, p) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= 0.5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    tn, fn = int(((yh == 0) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    rec = tp / (tp + fn) if tp + fn else np.nan
    spec = tn / (tn + fp) if tn + fp else np.nan
    prec = tp / (tp + fp) if tp + fp else np.nan
    bins = np.clip((p * 5).astype(int), 0, 4)
    ece = float(sum(abs(p[bins == b].mean() - y[bins == b].mean()) * (bins == b).mean() for b in range(5) if (bins == b).any()))
    return {"n": int(len(y)), "n_high": int(y.sum()), "accuracy": float((yh == y).mean()),
            "balanced_accuracy": float(np.nanmean([rec, spec])), "precision": prec, "recall_high": rec,
            "f1": (2 * prec * rec / (prec + rec)) if prec and rec and (prec + rec) else 0.0,
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None, "brier": float(np.mean((p - y) ** 2)),
            "ece": ece, "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}}


def _blocks(W):
    return {i: np.flatnonzero(W["issue_qi"].values == i) for i in W["issue_qi"].unique()}


def boot(W, rng, n):
    """Block bootstrap by issue quarter: Brier differences (A - B1, A - B5, A - climatology) and AUC of A."""
    blocks = _blocks(W)
    keys = list(blocks)
    y = W["y"].values.astype(int)
    P = {m: W[m].values for m in MODELS}
    d = {k: [] for k in ("A-B1", "A-B5", "A-clim", "auc")}
    for _ in range(n):
        ii = np.concatenate([blocks[k] for k in rng.choice(keys, len(keys))])
        b = {m: np.mean((P[m][ii] - y[ii]) ** 2) for m in (MAIN, NONEWS, PERS, "Climatology")}
        d["A-B1"].append(b[MAIN] - b[PERS])
        d["A-B5"].append(b[MAIN] - b[NONEWS])
        d["A-clim"].append(b[MAIN] - b["Climatology"])
        if len(set(y[ii])) == 2:
            d["auc"].append(roc_auc_score(y[ii], P[MAIN][ii]))
    ci = lambda v, a=0.05: [float(np.percentile(v, 100 * a / 2)), float(np.percentile(v, 100 * (1 - a / 2)))]
    return {k: {"ci95": ci(v), "p_ge_0": float(np.mean(np.asarray(v) >= 0)) if k != "auc" else None, "draws": v} for k, v in d.items()}


def run():
    verify_lock()
    rng = np.random.default_rng(T["seed"])
    res = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat()}
    X = MA.panel()
    W = MA.walk_forward(X, qindex(T["secondary_first_issue"]), qindex(T["last_issue"]), pd.Timestamp(T["data_cutoff"]))
    W.to_csv(OUT / "stage_a_oof.csv", index=False)
    print("walk-forward rows", len(W), flush=True)
    for win, first in (("primary", T["primary_first_issue"]), ("secondary", T["secondary_first_issue"])):
        Wv = W[W["issue_qi"] >= qindex(first)]
        out = {}
        for h in MA.HORIZONS:
            g = Wv[Wv["h"] == h]
            m = {n: metrics(g["y"], g[n]) for n in MODELS}
            b = boot(g, rng, T["n_boot"])
            news_draws = np.asarray(b["A-B5"]["draws"])
            r = {"metrics": m,
                 "A_minus_persistence_brier": {"diff": m[MAIN]["brier"] - m[PERS]["brier"], "ci95": b["A-B1"]["ci95"]},
                 "A_minus_no_news_brier": {"diff": m[MAIN]["brier"] - m[NONEWS]["brier"], "ci95": b["A-B5"]["ci95"],
                                           "p_ge_0": b["A-B5"]["p_ge_0"]},
                 "A_minus_climatology_brier": {"diff": m[MAIN]["brier"] - m["Climatology"]["brier"], "ci95": b["A-clim"]["ci95"]},
                 "auc_ci95": b["auc"]["ci95"]}
            M = m[MAIN]
            r["reliability"] = {
                "R1_auc": bool(M["auc"] is not None and M["auc"] >= T["R1_auc"] and b["auc"]["ci95"][0] > T["R1_auc_ci_lower"]),
                "R2_recall_precision": bool((M["recall_high"] or 0) >= T["R2_recall"] and (M["precision"] or 0) >= T["R2_precision"]),
                "R3_below_climatology": bool(M["brier"] < m["Climatology"]["brier"]),
                "R4_below_persistence": bool(b["A-B1"]["ci95"][1] < 0),
                "R5_calibration": bool(M["ece"] <= T["R5_ece"])}
            r["reliability"]["passes"] = all(r["reliability"].values())
            r["_news_p"] = float(np.mean(news_draws >= 0))
            out[f"h{h}"] = r
        mrlt = 0
        for h in MA.HORIZONS:
            if out[f"h{h}"]["reliability"]["passes"]:
                mrlt = h
            else:
                break
        # Holm across horizons for the news contribution
        order = sorted(MA.HORIZONS, key=lambda h: out[f"h{h}"]["_news_p"])
        stop, holm = False, {}
        for k, h in enumerate(order):
            a = T["alpha"] / (len(order) - k)
            ok = (not stop) and out[f"h{h}"]["_news_p"] < a / 2
            stop = stop or not ok
            holm[f"h{h}"] = {"one_sided_p": out[f"h{h}"]["_news_p"], "level": 1 - a, "news_improves": ok}
        res[win] = {"by_horizon": out, "maximum_reliable_lead_time_quarters": mrlt, "news_holm": holm,
                    "n_issues": int(Wv["issue_qi"].nunique())}
    print("stage A done", flush=True)
    res["link"] = L.link_tests(rng)
    print("link done", flush=True)
    e, R = L.e2e(X, rng)
    R.to_csv(OUT / "e2e_oof.csv", index=False)
    res["e2e"] = e
    P = res["primary"]
    res["decisions"] = {
        "H_A_dashboard_horizon": P["by_horizon"]["h1"]["reliability"]["passes"],
        "maximum_reliable_lead_time_quarters": P["maximum_reliable_lead_time_quarters"],
        "H_N_news_improves_h1": P["news_holm"]["h1"]["news_improves"],
        "H_C_link": bool(res["link"]["gamma_ci95"][0] > 0 or res["link"]["gamma_ci95"][1] < 0)
                    and res["link"]["loro_mean_wrmse"]["M1 (with area hunger)"] < res["link"]["loro_mean_wrmse"]["M0 (no time signal)"],
        "H_E2E": e["E2E_minus"]["C4-only"]["ci95"][1] < 0,
    }
    res["decisions"]["validated_forecast"] = bool(res["decisions"]["H_A_dashboard_horizon"] and res["decisions"]["H_C_link"]
                                                  and res["decisions"]["H_E2E"])
    for win in ("primary", "secondary"):
        for h in res[win]["by_horizon"].values():
            h.pop("_news_p", None)
    def _str_keys(o):  # P2 deviation D1 (fix-only): some link tables are keyed by tuples, which json cannot write
        if isinstance(o, dict):
            return {str(k): _str_keys(v) for k, v in o.items()}
        return [_str_keys(v) for v in o] if isinstance(o, (list, tuple)) else o

    (OUT / "results.json").write_text(json.dumps(_str_keys(res), indent=1, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)))
    print(json.dumps(res["decisions"], indent=1))
    return res


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
