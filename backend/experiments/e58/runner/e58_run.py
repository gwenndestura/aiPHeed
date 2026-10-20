"""E58: calibration arms for E53-A1 (lead 1) and E55 (lead 2). Experiment only. Pre-registration: ../E58_results.md.

    python -B backend/experiments/e58/runner/e58_run.py  -> backend/experiments/e58/E58_results.json

Raw probabilities come from the unchanged E53 (lead 1) and E55 (lead 2) walk-forwards; only the calibrator changes.
  C2  p' = a p + (1 - a) base rate  (e49_run.calibrated "shrink"; must reproduce E53-A1 and the served record)
  T   p' = sigmoid(z / T)           (T by log loss on the eligible earlier dates)
  P   p' = sigmoid(A z + B)         (A, B by log loss + LAMBDA ((A - 1)^2 + B^2) on the eligible earlier dates)
Every calibrator at origin t is fitted on prior_of[t] only (the C2 dates); fewer than MIN_DATES dates -> raw p.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E58 = Path(__file__).resolve().parents[1]
BACKEND = E58.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e53" / "runner"))
import e53_run as X53  # noqa: E402

X, R, L, L6, C, np, pd = X53.X, X53.R, X53.L, X53.L6, X53.C, X53.np, X53.pd
L7 = L.L8.L7
L6.guard32.EXP = E58
from scipy.optimize import minimize, minimize_scalar  # noqa: E402

NAMES, PROVS = X53.NAMES, X53.PROVS
POOL = "E53-A1"
LAMBDA = 0.01
EPS = 1e-6
PROTECTED = {"data/e36/e36_record.json": "921f2130c2ab3380c3cd21c1b25fe31a",
             "data/e48/e48_record.json": "a2223c22f85cb4058c0e7e59229dcb67",
             "data/e49/e49_record.json": "14c818ea990b6959584fbff92afd3ade",
             "data/e49/model/E48-A1-LGBM_O2026-10-01.txt": "2b6be3e9ab5e63191aa03639a5640ab1",
             "data/e49/model/E49_C2_calibration.json": "8f0eae02d81857f1d3c72ca5965409df"}
ALSO_UNCHANGED = ["data/e53/e53_record.json", "data/e53/model/E53_C2_calibration.json"]
REPORT = {1: ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"], 2: ["2026-Q1", "2026-Q2", "2026-Q3", "2027-Q1"]}


def md5s() -> dict:
    out = {p: hashlib.md5((BACKEND / p).read_bytes()).hexdigest() for p in list(PROTECTED) + ALSO_UNCHANGED}
    bad = [p for p, h in PROTECTED.items() if out[p] != h]
    if bad:
        raise SystemExit(f"protected md5 mismatch: {bad}")
    return out


logit = lambda p: np.log(np.clip(p, EPS, 1 - EPS) / (1 - np.clip(p, EPS, 1 - EPS)))
sig = lambda z: 1 / (1 + np.exp(-z))


def logloss(p, y):
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit_T(z, y):
    r = minimize_scalar(lambda lt: logloss(sig(z / np.exp(lt)), y), bounds=(-4, 4), method="bounded")
    return {"T": float(np.exp(r.x))}


def fit_P(z, y):
    obj = lambda ab: logloss(sig(ab[0] * z + ab[1]), y) + LAMBDA * ((ab[0] - 1) ** 2 + ab[1] ** 2)
    r = minimize(obj, x0=np.array([1.0, 0.0]), method="L-BFGS-B")
    return {"A": float(r.x[0]), "B": float(r.x[1])}


def apply(params, how, p):
    z = logit(np.asarray(p, float))
    return sig(z / params["T"]) if how == "T" else sig(params["A"] * z + params["B"])


def calibrate(raw, labels, prior_of, how):
    out, params = {}, {}
    for t in raw:
        prior = prior_of[t]
        if len(prior) < R.MIN_DATES:
            out[t], params[t] = dict(raw[t]), None
            continue
        p = np.array([raw[tj][c] for tj in prior for c in PROVS])
        y = np.array([labels[tj][c] for tj in prior for c in PROVS])
        params[t] = (fit_T if how == "T" else fit_P)(logit(p), y)
        out[t] = {c: float(apply(params[t], how, [raw[t][c]])[0]) for c in PROVS}
    return out, params


def harness(k):
    """Raw probabilities, labels, base rates and C2's eligible earlier dates, exactly as E53 (k=1) / E55 (k=2)."""
    d = X53.Data(X53.build_cond())
    if k == 1:
        Pr, info = L6.walk_forward(d)
        T = L6.OPERATIONAL_T
        prior = lambda t, dates: L6.eligible_prior_dates(d, t, dates)
        train, test = (lambda t: d.train(t)), (lambda t: d.test(t))
    else:
        Pr, info = L7.walk_forward(d, k)
        T = L7.OPERATIONAL_T
        prior = lambda t, dates: L7.eligible_prior(d, t, k, dates)
        train, test = (lambda t: d.train(t, k)), (lambda t: d.test(t, k))
    dates = [C.qk(q) - k for q in info["dates"]]
    alld = dates + [T]
    labels = {t: {c: int(d.label(c, t + k, t)) for c in PROVS} for t in dates}
    labels_all = {**labels, T: {c: 0 for c in PROVS}}
    base = {t: float((train(t)["y"].sum() + 1) / (len(train(t)) + 2)) for t in alld}
    prior_of = {t: prior(t, dates) for t in alld}
    raw = {}
    for t in alld:
        if t == T:
            fs, g = (L6.operational_choice(d, Pr, POOL)[0] if k == 1 else L7.operational_choice(d, Pr, k, POOL)[0])
        else:
            fs, g = info["selections"][POOL][C.qs(t + k)]["chosen"].split("x")
        _ptr, pte, _m = X.lgbm_arrays(train(t), test(t), L6.FEATURE_SETS[fs], g)
        raw[t] = dict(zip(test(t)["province_code"], pte))
    # leakage: every fitting date's target quarter is <= t - 1 and was posted before O(t)
    leak = []
    for t in alld:
        posted = set(d.posted_quarters(L6.origin(t)))
        for tj in prior_of[t]:
            if not (tj < t and tj + k <= t - 1 and (tj + k) in posted):
                leak.append({"origin": C.qs(t), "fit_date": C.qs(tj), "target": C.qs(tj + k)})
    return {"k": k, "T": T, "dates": dates, "alld": alld, "labels": labels, "labels_all": labels_all, "base": base,
            "prior_of": prior_of, "raw": raw, "leak": leak}


def evaluate(h, cal, arm):
    k = h["k"]
    g = pd.DataFrame([{"t": C.qs(t), "target_quarter": C.qs(t + k), "province_code": c, "arm": arm,
                       "p": cal[t][c], "p_raw": h["raw"][t][c], "y": h["labels"][t][c]}
                      for t in h["dates"] for c in PROVS])
    s = R.summary(g)
    pred = g["p"] >= 0.5
    m = {"n": int(len(g)), "accuracy": s["accuracy"], "balanced_accuracy": s["balanced_accuracy"], "auc": s["auc"],
         "brier": s["brier"], "log_loss": s["log_loss"], "LOW_caught": int((~pred & (g["y"] == 0)).sum()),
         "LOW_rows": int((g["y"] == 0).sum()), "HIGH_share_pred": float(pred.mean()),
         "reliability_5bin": s["reliability_5bin"], "max_p": float(g["p"].max()), "min_p": float(g["p"].min())}
    quarters = {}
    for t in h["alld"]:
        q = C.qs(t + k)
        if q not in REPORT[k]:
            continue
        ps = {NAMES[c]: float(cal[t][c]) for c in PROVS}
        r2 = [round(v, 2) for v in ps.values()]
        quarters[q] = {"provinces": ps, "index": float(np.mean(list(ps.values()))),
                       "spread": max(ps.values()) - min(ps.values()),
                       "ties_2dp": sum(1 for v in r2 if r2.count(v) > 1),
                       "raw": {NAMES[c]: float(h["raw"][t][c]) for c in PROVS}}
    return m, quarters, g


def main():
    os.chdir(BACKEND)
    res = {"md5_start": md5s(), "lambda_platt": LAMBDA, "leads": {}}
    X53.register()
    rec = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
    served = {(q["quarter"], q["lead"]): {NAMES[c]: v["p_high"] for c, v in q["provinces"].items()} for q in rec["quarters"]}
    frames = []
    for k in (1, 2):
        print("lead", k, flush=True)
        h = harness(k)
        c2, _fb, pa = R.calibrated(h["raw"], h["labels_all"], h["base"], h["prior_of"], "shrink")
        tcal, tpar = calibrate(h["raw"], h["labels_all"], h["prior_of"], "T")
        pcal, ppar = calibrate(h["raw"], h["labels_all"], h["prior_of"], "P")
        arms, params = {"C2": c2, "T": tcal, "P": pcal}, {"C2": pa, "T": tpar, "P": ppar}
        L_ = {"leakage_violations": h["leak"], "fit_dates_per_origin": {C.qs(t + k): len(h["prior_of"][t]) for t in h["alld"]},
              "arms": {}}
        for arm, cal in arms.items():
            m, quarters, g = evaluate(h, cal, f"L{k}-{arm}")
            frames.append(g)
            L_["arms"][arm] = {"metrics": m, "quarters": quarters,
                               "params": {C.qs(t + k): v for t, v in params[arm].items()}}
        # C2 must reproduce the served record (every served lead-k row) and, at lead 1, E53-A1
        diffs = [abs(c2[t][c] - served[(C.qs(t + k), k)][NAMES[c]]) for t in h["alld"] if (C.qs(t + k), k) in served
                 for c in PROVS]
        L_["C2_vs_served_record_max_abs_diff"] = max(diffs) if diffs else None
        L_["C2_rows_compared_with_record"] = len(diffs)
        m = L_["arms"]["C2"]["metrics"]
        print("  C2", {x: round(m[x], 3) for x in ("accuracy", "balanced_accuracy", "auc", "brier", "log_loss")},
              "record diff", L_["C2_vs_served_record_max_abs_diff"], flush=True)
        for arm in ("T", "P"):
            mm = L_["arms"][arm]["metrics"]
            print(f"  {arm}", {x: round(mm[x], 3) for x in ("accuracy", "balanced_accuracy", "auc", "brier", "log_loss")},
                  flush=True)
        if k == 1:
            ok = (round(m["accuracy"], 3), round(m["balanced_accuracy"], 3), round(m["auc"], 3), round(m["brier"], 3)) \
                == (0.785, 0.836, 0.880, 0.150) and (L_["C2_vs_served_record_max_abs_diff"] or 0) < 1e-4
            res["C2_reproduces_E53_A1"] = ok
            if not ok:
                raise SystemExit("C2 does not reproduce E53-A1 / the served record")
        res["leads"][str(k)] = L_
    # adoption (lead 1 only)
    l1 = res["leads"]["1"]["arms"]
    c2m = l1["C2"]["metrics"]
    adopt = {}
    for arm in ("T", "P"):
        mm = l1[arm]["metrics"]
        crit = {"a_brier_and_logloss_le_C2": mm["brier"] <= c2m["brier"] + 1e-12 and mm["log_loss"] <= c2m["log_loss"] + 1e-12,
                "b_bal_ge_0.826_and_auc_within_0.005": mm["balanced_accuracy"] >= 0.836 - 0.01 - 1e-12
                                                      and abs(mm["auc"] - c2m["auc"]) <= 0.005,
                "c_leakage_check": not res["leads"]["1"]["leakage_violations"]}
        adopt[arm] = {"criteria": crit, "eligible": all(crit.values()), "auc_exactly_equal": mm["auc"] == c2m["auc"],
                      "auc_diff": mm["auc"] - c2m["auc"]}
    elig = [a for a in ("T", "P") if adopt[a]["eligible"]]
    pick = min(elig, key=lambda a: l1[a]["metrics"]["brier"]) if elig else None
    res["adoption"] = {"arms": adopt, "eligible": elig,
                       "verdict": f"adopt {pick} (not served; awaiting approval)" if pick
                       else "Keep C2; calibration experiments closed."}
    if pick:
        cal_out = {"arm": pick, "lambda_platt": LAMBDA if pick == "P" else None,
                   "note": "fitted at each origin on the eligible earlier dates only (C2's dates); null = raw probability "
                           "(fewer than 3 eligible dates). NOT SERVED.",
                   "lead1_params_by_target_quarter": res["leads"]["1"]["arms"][pick]["params"],
                   "lead2_params_by_target_quarter": res["leads"]["2"]["arms"][pick]["params"]}
        C.write_json(E58 / "E58_calibration.json", C.clean(cal_out))
    # what the dashboard shows now (served record) vs C2 recomputed vs each arm
    dash = {}
    for k, qs_ in ((1, REPORT[1]), (2, ["2027-Q1"])):
        for q in qs_:
            cur = served.get((q, k))
            row = {"current_served": {"index": float(np.mean(list(cur.values()))), **cur} if cur else None}
            for arm in ("C2", "T", "P"):
                qq = res["leads"][str(k)]["arms"][arm]["quarters"][q]
                row[arm] = {"index": qq["index"], **qq["provinces"]}
            dash[f"{q} (lead {k})"] = row
    res["dashboard_comparison"] = dash
    res["md5_end"] = md5s()
    res["md5_unchanged"] = res["md5_start"] == res["md5_end"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E58 / "runs" / stamp
    run.mkdir(parents=True)
    pd.concat(frames).to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E58 / "E58_results.json", C.clean(res))
    print("RUN", stamp, "eligible", elig, "|", res["adoption"]["verdict"], "| md5 unchanged", res["md5_unchanged"])


if __name__ == "__main__":
    main()
