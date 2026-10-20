"""E59: Algorithm 3 lead-time scan, served E49 family (E48-A1 inputs + C2), k = 1..8. Evaluation only.
Pre-registration: ../E59_results.md (written first).

    python -B backend/experiments/e59/runner/e59_run.py  -> backend/experiments/e59/E59_results.json
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E59 = Path(__file__).resolve().parents[1]
BACKEND = E59.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e50" / "runner"))
import e50_run as X  # noqa: E402  (E49 calibration helpers, E48 data and pools; brings in e36/e37/e38 libs)

R, L, L6, C, np, pd = X.R, X.L, X.L6, X.C, X.np, X.pd
L7 = L.L8.L7
L6.guard32.EXP = E59
NAMES, PROVS = X.NAMES, X.PROVS
POOL = "E48-T5"
LEADS = range(1, 9)
MIN_DATES = 4
PROTECTED = {"data/e36/e36_record.json": "921f2130c2ab3380c3cd21c1b25fe31a",
             "data/e48/e48_record.json": "a2223c22f85cb4058c0e7e59229dcb67",
             "data/e49/e49_record.json": "14c818ea990b6959584fbff92afd3ade",
             "data/e49/model/E48-A1-LGBM_O2026-10-01.txt": "2b6be3e9ab5e63191aa03639a5640ab1",
             "data/e49/model/E49_C2_calibration.json": "8f0eae02d81857f1d3c72ca5965409df"}


def md5s() -> dict:
    out = {p: hashlib.md5((BACKEND / p).read_bytes()).hexdigest() for p in PROTECTED}
    if out != PROTECTED:
        raise SystemExit(f"protected md5 mismatch: {[p for p in out if out[p] != PROTECTED[p]]}")
    return out


def metrics(g: pd.DataFrame) -> dict:
    s = R.summary(g)
    pred, y = (g["p"] >= 0.5).astype(int), g["y"].astype(int)
    tp, fp = int(((pred == 1) & (y == 1)).sum()), int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    return {"accuracy": s["accuracy"], "accuracy_ci95": s["accuracy_ci95"], "balanced_accuracy": s["balanced_accuracy"],
            "precision": prec, "recall": rec, "f1": (2 * prec * rec / (prec + rec)) if prec and rec else None,
            "auc": s["auc"], "brier": s["brier"]}


def run_lead(d, k):
    if k == 1:
        Pr, info = L6.walk_forward(d)
        prior = lambda t, dates: L6.eligible_prior_dates(d, t, dates)
        train = lambda t: d.train(t)
    else:
        Pr, info = L7.walk_forward(d, k)
        prior = lambda t, dates: L7.eligible_prior(d, t, k, dates)
        train = lambda t: d.train(t, k)
    dates = [C.qk(q) - k for q in info["dates"]]
    if not dates:
        return {"k": k, "n_dates": 0, "n_rows": 0, "evaluable": False, "reason": "no scored date"}, None
    rows = Pr[Pr["arm"] == POOL]
    raw = {t: dict(zip(g["province_code"], g["p"])) for t, g in ((C.qk(x), g) for x, g in rows.groupby("t"))}
    labels = {t: dict(zip(g["province_code"], g["y"])) for t, g in ((C.qk(x), g) for x, g in rows.groupby("t"))}
    base = {t: float((train(t)["y"].sum() + 1) / (len(train(t)) + 2)) for t in dates}
    prior_of = {t: prior(t, dates) for t in dates}
    cal, fb, pa = R.calibrated(raw, labels, base, prior_of, "shrink")
    g = pd.DataFrame([{"t": C.qs(t), "target_quarter": C.qs(t + k), "province_code": c, "arm": f"k{k}",
                       "p": cal[t][c], "p_raw": raw[t][c], "y": int(labels[t][c])} for t in dates for c in PROVS])
    pers = Pr[Pr["arm"] == "B1_PERSISTENCE"]
    n_low = int((g["y"] == 0).sum())
    out = {"k": k, "n_dates": len(dates), "n_rows": int(len(g)), "LOW_rows": n_low, "HIGH_rows": int(len(g) - n_low),
           "target_quarters": info["dates"], "calibration_fallback_dates": len(fb),
           "evaluable": len(dates) >= MIN_DATES and g["y"].nunique() == 2,
           "model": metrics(g),
           "persistence": {k_: v for k_, v in metrics(pers).items() if k_ in ("accuracy", "balanced_accuracy", "brier")},
           "shrink_params": {C.qs(t + k): v for t, v in pa.items()}}
    if not out["evaluable"]:
        out["reason"] = f"{len(dates)} scored dates (< {MIN_DATES})" if len(dates) < MIN_DATES else "one class only"
    return out, g


def algorithm3(res: list[dict], ci: bool) -> dict:
    trail, mrlt = [], None
    for r in res:
        if not r["evaluable"]:
            trail.append({"k": r["k"], "pass": False, "why": f"not evaluable ({r.get('reason')})"})
            break
        v = r["model"]["accuracy_ci95"][0] if ci else r["model"]["accuracy"]
        ok = v is not None and v >= 0.75
        trail.append({"k": r["k"], "pass": ok, "value": v})
        if not ok:
            break
        mrlt = r["k"]
    return {"rule": "CI lower bound >= 0.75" if ci else "mean fold accuracy >= 0.75", "trail": trail,
            "maximum_reliable_lead_time": mrlt}


def main():
    os.chdir(BACKEND)
    res = {"md5_start": md5s()}
    X.register()
    d = L.Data(paper=False)
    leads, frames = [], []
    for k in LEADS:
        print("lead", k, flush=True)
        r, g = run_lead(d, k)
        leads.append(r)
        if g is not None:
            frames.append(g)
        m = r.get("model", {})
        print("  dates", r["n_dates"], "rows", r["n_rows"], "evaluable", r["evaluable"],
              {x: (round(m[x], 3) if isinstance(m.get(x), float) else m.get(x)) for x in ("accuracy", "balanced_accuracy", "auc")},
              flush=True)
        if k == 1:
            ok = (round(m["accuracy"], 3), round(m["balanced_accuracy"], 3), round(m["auc"], 3)) == (0.846, 0.841, 0.855)
            res["k1_reproduces_E49"] = ok
            if not ok:
                raise SystemExit(f"k = 1 does not reproduce E49: {m}")
    res["leads"] = leads
    res["algorithm3"] = algorithm3(leads, ci=False)
    res["algorithm3_ci"] = algorithm3(leads, ci=True)
    res["md5_end"] = md5s()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E59 / "runs" / stamp
    run.mkdir(parents=True)
    pd.concat(frames).to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E59 / "E59_results.json", C.clean(res))
    print("RUN", stamp, "MRLT", res["algorithm3"]["maximum_reliable_lead_time"], "| CI version",
          res["algorithm3_ci"]["maximum_reliable_lead_time"])


if __name__ == "__main__":
    main()
