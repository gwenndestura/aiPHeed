"""
E188 (docs/e188/PROTOCOL.md): E184 with 20 synthetic draws (E188a), and E184 with survey-noise synthetic rows - inputs
copied exactly, target redrawn from the survey's sampling error - with 20 draws (E188b). Leads 1-6.

    python -m app.e188.candidate run
"""
from __future__ import annotations

import sys
import time
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e182 import candidate as C182
from app.e184 import candidate as C184

warnings.filterwarnings("ignore")
OUT = K.D / "e188" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e188" / "PROTOCOL.md"
SEEDS20 = tuple(range(17901, 17921))
SETTING_B = ("jitter", 1.0, 1.0, 0.0, "boundary")      # inputs copied exactly; target + N(0, se)
LEADS = (1, 2, 3, 4, 5, 6)
ARMS = ("E184", "E188a", "E188b")


def _mean(runs):
    return tuple(np.mean([np.asarray(r[k], float) for r in runs], axis=0) for k in range(3))


def job(survey, lead, H, L, S_P):
    t0 = time.time()
    tr, te, AN = RT.build(survey, lead, H, L, S_P, "main")
    assert "is_synthetic" not in te.columns, "outer rows must be real"
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfg, _ = C182.stage_a(tr, AN, folds)
    stream = RT.job_id(survey, lead, "main")
    runs = {}
    for name, setting in (("A", C184.SETTING), ("B", SETTING_B)):
        runs[name] = []
        for s in SEEDS20:
            P, chosen = C182.seed_run(tr, te, AN, folds, cfg, setting, s, stream)[:2]
            runs[name].append(P[chosen])
    rows = []
    for arm, rs in (("E184", runs["A"][:5]), ("E188a", runs["A"]), ("E188b", runs["B"])):
        o = te[RT.KEYS].copy()
        o["arm"] = arm
        o["mu"], o["p"], o["half"] = _mean(rs)
        rows.append(o)
    return {"rows": pd.concat(rows, ignore_index=True), "job": stream, "seconds": round(time.time() - t0, 1)}


def _stored_e184():
    a = pd.read_csv(K.D / "e184" / "out" / "all_rows.csv", float_precision="round_trip")
    b = pd.read_csv(K.D / "e184" / "out" / "lead3_rows.csv", float_precision="round_trip")
    c = pd.read_csv(K.D / "e187" / "out" / "lead4_6_rows.csv", float_precision="round_trip")
    x = pd.concat([d[(d["arm"] == "E184") & (d["mode"] == "main")] for d in (a, b, c)], ignore_index=True)
    return x[RT.KEYS + ["p"]].drop_duplicates(RT.KEYS)


def _m(x, col):
    hi, pr = x["y_high"] == 1, x[col] >= 0.5
    tp, fp, fn, tn = int((pr & hi).sum()), int((pr & ~hi).sum()), int((~pr & hi).sum()), int((~pr & ~hi).sum())
    return {"accuracy": round((tp + tn) / len(x), 4), "balanced_accuracy": round((tp / (tp + fn) + tn / (tn + fp)) / 2, 4),
            "high_recall": round(tp / (tp + fn), 3), "high_precision": round(tp / max(1, tp + fp), 3), "false_alarms": fp,
            "missed_high": fn, "brier": round(float(np.mean((x[col] - x["q_true"]) ** 2)), 5)}


def evaluate(R, log):
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    st = _stored_e184()
    res = {"protocol": "docs/e188/PROTOCOL.md", "leads": {}}
    for Ld in LEADS:
        x = G[G["lead"] == Ld]
        for arm in ARMS:
            x = x.merge(R[(R["lead"] == Ld) & (R["arm"] == arm)][RT.KEYS + ["p"]].rename(columns={"p": arm}), on=RT.KEYS)
        x = x.merge(st.rename(columns={"p": "E184_stored"}), on=RT.KEYS)
        assert len(x) == 72, (Ld, len(x))
        L_ = {"reproduction_max_abs_diff_p": float(np.max(np.abs(x["E184"] - x["E184_stored"]))),
              "metrics": {a: _m(x, a) for a in ("PERS",) + ARMS}}
        for arm in ("E188a", "E188b"):
            v = E.E7.diff_ci(x, arm, "E184", "q_true", np.random.default_rng(188), n=2000)
            vp = E.E7.diff_ci(x, arm, "PERS", "q_true", np.random.default_rng(188), n=2000)
            cA, cB = (x[arm] >= .5) == (x["y_high"] == 1), (x["E184"] >= .5) == (x["y_high"] == 1)
            b, c = int((cA & ~cB).sum()), int((~cA & cB).sum())
            L_[arm] = {"brier_minus_E184": [round(v["diff"], 5), [round(z, 5) for z in v["ci95"]]],
                       "mcnemar_vs_E184": {"only_this_right": b, "only_E184_right": c, "p": round(float(binomtest(b, b + c, .5).pvalue), 4) if b + c else 1.0},
                       "owner_rule": bool(L_["metrics"][arm]["accuracy"] >= 0.75 and vp["ci95"][1] < 0)}
        res["leads"][Ld] = L_
    ok = {}
    for arm in ("E188a", "E188b"):
        acc = [res["leads"][l]["metrics"][arm]["accuracy"] - res["leads"][l]["metrics"]["E184"]["accuracy"] for l in LEADS]
        br = [res["leads"][l]["metrics"][arm]["brier"] - res["leads"][l]["metrics"]["E184"]["brier"] for l in LEADS]
        ok[arm] = {"acc_ge_all": all(a >= -1e-12 for a in acc), "brier_le_all": all(b <= 1e-12 for b in br), "acc_gt_any": any(a > 1e-12 for a in acc),
                   "mean_brier": float(np.mean([res["leads"][l]["metrics"][arm]["brier"] for l in LEADS]))}
        ok[arm]["qualifies"] = ok[arm]["acc_ge_all"] and ok[arm]["brier_le_all"] and ok[arm]["acc_gt_any"]
    q = [a for a in ok if ok[a]["qualifies"]]
    res["decision_checks"] = ok
    res["decision"] = (f"{min(q, key=lambda a: ok[a]['mean_brier'])} preferred to E184 (candidate only; not staged)" if q
                       else "Neither variant meets the rule: E184 stays")
    log("evaluated", decision=res["decision"])
    return res


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), seeds=[SEEDS20[0], SEEDS20[-1]], setting_b=list(SETTING_B))
    H, L, S_P = K.pipeline_inputs()
    t0 = time.time()
    out = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(job)(s, l, H, L, S_P) for s in RT.SURVEYS for l in LEADS)
    for o in out:
        log("job", job=o["job"], seconds=o["seconds"])
    R = pd.concat([o["rows"] for o in out], ignore_index=True)
    R.to_csv(OUT / "rows.csv", index=False, lineterminator="\n")
    log("fitted", seconds=round(time.time() - t0, 1))
    res = evaluate(R, log)
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("rows.csv", "results.json", "run_log.jsonl")], OUT / "hashes.json")
    for Ld, v in res["leads"].items():
        m = v["metrics"]
        print(f"Lead {Ld}: repro {v['reproduction_max_abs_diff_p']:.1e} | acc PERS {m['PERS']['accuracy']} E184 {m['E184']['accuracy']} "
              f"E188a {m['E188a']['accuracy']} E188b {m['E188b']['accuracy']} | brier E184 {m['E184']['brier']} a {m['E188a']['brier']} "
              f"b {m['E188b']['brier']} | a-E184 {v['E188a']['brier_minus_E184']} b-E184 {v['E188b']['brier_minus_E184']} "
              f"| mcn a {v['E188a']['mcnemar_vs_E184']} b {v['E188b']['mcnemar_vs_E184']} | rule a {v['E188a']['owner_rule']} b {v['E188b']['owner_rule']}")
        print("   balacc/recall/FA:", {a: (m[a]["balanced_accuracy"], m[a]["high_recall"], m[a]["false_alarms"]) for a in ARMS})
    print(res["decision_checks"])
    print(res["decision"])


if __name__ == "__main__":
    {"run": run}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: python -m app.e188.candidate run"))()
