"""
E187 (docs/e187/PROTOCOL.md).
  (A) E184 unchanged at Leads 4-6 vs E168's Lead 4-6 rows and persistence (owner serving rule per lead).
  (B) E184 with the HIGH cut-off chosen on the real training rows' inner out-of-fold P(HIGH) (max balanced accuracy,
      grid 0.30-0.60), evaluated at Leads 1-3.

    python -m app.e187.tests run
"""
from __future__ import annotations

import sys
import time
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest

from app.e168 import lgbm_only as E
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T
from app.e182 import candidate as C182
from app.e184 import candidate as C184

warnings.filterwarnings("ignore")
OUT = K.D / "e187" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e187" / "PROTOCOL.md"
GRID = tuple(round(0.30 + 0.05 * k, 2) for k in range(7))


def choose_cutoff(p, high) -> float:
    """Maximise balanced accuracy on the training rows; ties go to the cut-off closest to 0.50."""
    p, high = np.asarray(p), np.asarray(high) == 1
    def bal(t):
        pr = p >= t
        return ((pr & high).sum() / max(1, high.sum()) + (~pr & ~high).sum() / max(1, (~high).sum())) / 2
    return max(GRID, key=lambda t: (round(bal(t), 12), -abs(t - 0.5)))


def threshold_job(survey, lead, H, L, S_P):
    t0 = time.time()
    tr, te, AN = RT.build(survey, lead, H, L, S_P, "main")
    r = C182.fixed(tr, te, AN, T.SEEDS, RT.job_id(survey, lead, "main"), setting=C184.SETTING, oof_p=True)
    t = choose_cutoff(r["oof_p"], r["train_high"])
    mu, p, half = r[C182.NAME]
    o = te[RT.KEYS].copy().reset_index(drop=True)
    o["mu"], o["p"], o["half"], o["cutoff"] = mu, p, half, t
    return {"rows": o, "job": f"{survey}|L{lead}", "cutoff": t, "seconds": round(time.time() - t0, 1)}


def _truth(lead):
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    return G[G["lead"] == lead]


def _m(x, col, cut=0.5):
    hi, pr = x["y_high"] == 1, x[col] >= cut
    tp, fp, fn, tn = int((pr & hi).sum()), int((pr & ~hi).sum()), int((~pr & hi).sum()), int((~pr & ~hi).sum())
    return {"accuracy": round((tp + tn) / len(x), 3), "balanced_accuracy": round((tp / (tp + fn) + tn / (tn + fp)) / 2, 3),
            "high_recall": round(tp / (tp + fn), 3), "high_precision": round(tp / max(1, tp + fp), 3), "false_alarms": fp, "missed_high": fn,
            "brier": round(float(np.mean((x[col] - x["q_true"]) ** 2)), 4)}


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), grid=GRID)
    H, L, S_P = K.pipeline_inputs()
    t0 = time.time()
    jobsA = [delayed(C184.job)(s, l, H, L, S_P, "main") for s in RT.SURVEYS for l in (4, 5, 6)]
    jobsB = [delayed(threshold_job)(s, l, H, L, S_P) for s in RT.SURVEYS for l in (1, 2, 3)]
    R = Parallel(n_jobs=RT.N_JOBS, verbose=5)(jobsA + jobsB)
    RA, RB_ = R[:len(jobsA)], R[len(jobsA):]
    A = pd.concat([r["rows"] for r in RA], ignore_index=True)
    A.to_csv(OUT / "lead4_6_rows.csv", index=False, lineterminator="\n")
    B = pd.concat([r["rows"] for r in RB_], ignore_index=True)
    B.to_csv(OUT / "threshold_rows.csv", index=False, lineterminator="\n")
    log("fitted", seconds=round(time.time() - t0, 1), cutoffs={r["job"]: r["cutoff"] for r in RB_})
    res = {"protocol": "docs/e187/PROTOCOL.md", "A_longer_leads": {}, "B_cutoff": {}}
    # (A)
    e8 = pd.read_csv(E.OUT / "all_rows_l3_8.csv", float_precision="round_trip")
    horizon, ok_all = 3, True
    for Ld in (4, 5, 6):
        x = _truth(Ld).merge(e8[(e8["lead"] == Ld) & (e8["mode"] == "main")][RT.KEYS + ["mu", "p", "half"]].rename(columns={"mu": "mu_E168", "p": "E168", "half": "half_E168"}), on=RT.KEYS)
        x = x.merge(A[(A["lead"] == Ld) & (A["arm"] == "E184")][RT.KEYS + ["mu", "p", "half"]].rename(columns={"mu": "mu_E184", "p": "E184", "half": "half_E184"}), on=RT.KEYS)
        assert len(x) == 72, (Ld, len(x))
        rng = np.random.default_rng(187)
        vp = E.E7.diff_ci(x, "E184", "PERS", "q_true", rng, n=2000)
        v8 = E.E7.diff_ci(x, "E184", "E168", "q_true", np.random.default_rng(187), n=2000)
        mm = {"PERS": _m(x, "PERS"), "E168": _m(x, "E168"), "E184": _m(x, "E184")}
        passes = mm["E184"]["accuracy"] >= 0.75 and vp["ci95"][1] < 0
        res["A_longer_leads"][Ld] = {"metrics": mm, "brier_minus_persistence": [round(vp["diff"], 4), [round(z, 4) for z in vp["ci95"]]],
                                     "brier_minus_E168": [round(v8["diff"], 4), [round(z, 4) for z in v8["ci95"]]], "passes_owner_rule": passes,
                                     "e168_rerun_max_abs_diff_p": float(np.max(np.abs(x["E168"] - A[(A["lead"] == Ld) & (A["arm"] == "E168_rerun")].set_index(RT.KEYS).loc[pd.MultiIndex.from_frame(x[RT.KEYS]), "p"].values)))}
        if ok_all and passes:
            horizon = Ld
        ok_all = ok_all and passes
    res["A_served_horizon_E184"] = horizon
    # (B)
    dec = []
    for Ld in (1, 2, 3):
        src = pd.read_csv(K.D / "e184" / "out" / ("lead3_rows.csv" if Ld == 3 else "all_rows.csv"), float_precision="round_trip")
        e84 = src[(src["lead"] == Ld) & (src["mode"] == "main") & (src["arm"] == "E184")][RT.KEYS + ["p"]].rename(columns={"p": "E184"})
        x = _truth(Ld).merge(B[B["lead"] == Ld][RT.KEYS + ["p", "cutoff"]].rename(columns={"p": "E187p"}), on=RT.KEYS).merge(e84, on=RT.KEYS)
        assert len(x) == 72
        same = float(np.max(np.abs(x["E187p"] - x["E184"])))
        x["E187cls"] = (x["E187p"] >= x["cutoff"]).astype(float)
        m187, m184 = _m(x.assign(c=x["E187cls"]), "c", 0.5), _m(x, "E184")
        m187["brier"] = m184["brier"]                                 # probabilities unchanged; only the HIGH/LOW decision moves
        cA, cB = (x["E187cls"] == 1) == (x["y_high"] == 1), (x["E184"] >= .5) == (x["y_high"] == 1)
        bb, cc = int((cA & ~cB).sum()), int((~cA & cB).sum())
        res["B_cutoff"][Ld] = {"cutoffs_by_round": x.groupby("survey")["cutoff"].first().to_dict(), "E187": m187, "E184_at_0.50": m184,
                               "E168": None, "mcnemar_vs_E184": {"E187_only_right": bb, "E184_only_right": cc, "p": round(float(binomtest(bb, bb + cc, .5).pvalue), 4) if bb + cc else 1.0},
                               "probabilities_equal_E184_max_abs_diff": same}
        dec.append(m187["balanced_accuracy"] >= m184["balanced_accuracy"] and m187["high_recall"] >= m184["high_recall"])
    res["B_decision"] = "E187 cut-off preferred to 0.50" if all(dec) else "E184 keeps the 0.50 cut-off"
    K.dump_json(res, OUT / "results.json")
    log("evaluated", horizon=horizon, B=res["B_decision"])
    K.write_hashes([OUT / n for n in ("lead4_6_rows.csv", "threshold_rows.csv", "results.json")] + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    for Ld, v in res["A_longer_leads"].items():
        print(f"(A) Lead {Ld}:", v["metrics"], "vsPERS", v["brier_minus_persistence"], "vsE168", v["brier_minus_E168"], "passes", v["passes_owner_rule"])
    print("(A) E184 served horizon:", horizon)
    for Ld, v in res["B_cutoff"].items():
        print(f"(B) Lead {Ld}: cutoffs {v['cutoffs_by_round']} E187 {v['E187']} | E184@0.50 {v['E184_at_0.50']} | {v['mcnemar_vs_E184']} same-p {v['probabilities_equal_E184_max_abs_diff']:.1e}")
    print("(B)", res["B_decision"])


if __name__ == "__main__":
    {"run": run}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: python -m app.e187.tests run"))()
