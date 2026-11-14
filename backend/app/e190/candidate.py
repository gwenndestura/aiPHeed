"""
E190 (docs/e190/PROTOCOL.md): E184 with truly class-balanced synthetic rows. E190a = parity allocation; E190b = parity
allocation + label-preserving outcomes. Leads 1-6. Local only.

    python -m app.e190.candidate run
"""
from __future__ import annotations

import sys
import time
import warnings
from contextlib import ExitStack

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e178 import augment as A
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T
from app.e182 import candidate as C182
from app.e184 import candidate as C184
from app.e188 import candidate as C188

warnings.filterwarnings("ignore")
OUT = K.D / "e190" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e190" / "PROTOCOL.md"
LEADS = (1, 2, 3, 4, 5, 6)
ARMS = ("E184", "E190a", "E190b")


def parity_allocate(high, n_syn):
    """Synthetic rows per class so that real + synthetic is exactly half HIGH (as near as integers allow)."""
    high = np.asarray(high, bool)
    n1, n0 = int(high.sum()), int((~high).sum())
    s1 = int(np.clip(round((n1 + n0 + n_syn) / 2) - n1, 0, n_syn))
    return {1: s1, 0: n_syn - s1}


def _fold_augment(orig, log):
    def wrapped(real, an, s, seed, job, fold):
        out = orig(real, an, s, seed, job, fold)
        syn = out[0]
        par_high = real.reset_index(drop=True)["y_true"].values[syn["parent"].values] >= 0
        y = syn["y_true"].values.copy()
        flip = (y >= 0) != par_high
        y[flip] = -y[flip]
        y[(y == 0) & ~par_high] = -1e-9
        syn["y_true"], syn["q_true"] = y, norm.cdf(y / syn["se_true"].values)
        log.append((job, fold, seed, int(flip.sum()), float((y >= 0).mean()), float(np.r_[real["y_true"].values >= 0, y >= 0].mean())))
        return (syn,) + tuple(out[1:])
    return wrapped


def _share_logger(orig, log):
    def wrapped(real, an, s, seed, job, fold):
        out = orig(real, an, s, seed, job, fold)
        y = out[0]["y_true"].values
        log.append((job, fold, seed, 0, float((y >= 0).mean()), float(np.r_[real["y_true"].values >= 0, y >= 0].mean())))
        return out
    return wrapped


def job(survey, lead, H, L, S_P):
    t0 = time.time()
    tr, te, AN = RT.build(survey, lead, H, L, S_P, "main")
    assert "is_synthetic" not in te.columns, "outer rows must be real"
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfg, _ = C182.stage_a(tr, AN, folds)
    stream = RT.job_id(survey, lead, "main")
    rows, bal = [], []
    for arm in ARMS:
        log = []
        with ExitStack() as st:
            if arm in ("E190a", "E190b"):
                st.enter_context(K.patched(A, "allocate", parity_allocate))
            orig = T._augment
            st.enter_context(K.patched(T, "_augment", _fold_augment(orig, log) if arm == "E190b" else _share_logger(orig, log)))
            runs = []
            for s in T.SEEDS:
                P, chosen = C182.seed_run(tr, te, AN, folds, cfg, C184.SETTING, s, stream)[:2]
                runs.append(P[chosen])
        o = te[RT.KEYS].copy()
        o["arm"] = arm
        o["mu"], o["p"], o["half"] = C188._mean(runs)
        rows.append(o)
        fin = [b for b in log if b[1] == "final"]
        bal.append({"job": stream, "arm": arm, "real_high_share": round(float((tr["y_true"] >= 0).mean()), 4),
                    "final_syn_high_share_mean": round(float(np.mean([b[4] for b in fin])), 4),
                    "final_combined_high_share_mean": round(float(np.mean([b[5] for b in fin])), 4),
                    "final_flips_folded_mean": round(float(np.mean([b[3] for b in fin])), 1)})
    return {"rows": pd.concat(rows, ignore_index=True), "balance": bal, "job": stream, "seconds": round(time.time() - t0, 1)}


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL))
    H, L, S_P = K.pipeline_inputs()
    out = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(job)(s, l, H, L, S_P) for s in RT.SURVEYS for l in LEADS)
    for o in out:
        log("job", job=o["job"], seconds=o["seconds"])
    R = pd.concat([o["rows"] for o in out], ignore_index=True)
    R.to_csv(OUT / "rows.csv", index=False, lineterminator="\n")
    Bal = pd.DataFrame([b for o in out for b in o["balance"]])
    Bal.to_csv(OUT / "balance.csv", index=False, lineterminator="\n")
    # evaluation: E188's evaluator with this experiment's arm names
    res = _evaluate(R, log)
    res["balance_summary"] = Bal.groupby("arm")[["real_high_share", "final_combined_high_share_mean", "final_flips_folded_mean"]].mean().round(4).to_dict("index")
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("rows.csv", "balance.csv", "results.json", "run_log.jsonl")], OUT / "hashes.json")
    print(Bal.groupby(["arm", Bal["job"].str.split("|").str[0]])[["real_high_share", "final_syn_high_share_mean", "final_combined_high_share_mean", "final_flips_folded_mean"]].mean().round(3).to_string())
    for Ld, v in res["leads"].items():
        m = v["metrics"]
        print(f"Lead {Ld}: repro {v['reproduction_max_abs_diff_p']:.1e} | acc E184 {m['E184']['accuracy']} a {m['E190a']['accuracy']} b {m['E190b']['accuracy']} "
              f"| FA {m['E184']['false_alarms']}/{m['E190a']['false_alarms']}/{m['E190b']['false_alarms']} miss {m['E184']['missed_high']}/{m['E190a']['missed_high']}/{m['E190b']['missed_high']} "
              f"| brier {m['E184']['brier']}/{m['E190a']['brier']}/{m['E190b']['brier']} | a-E184 {v['E190a']['brier_minus_E184']} b-E184 {v['E190b']['brier_minus_E184']} "
              f"| mcn a {v['E190a']['mcnemar_vs_E184']} b {v['E190b']['mcnemar_vs_E184']} | bal {m['E184']['balanced_accuracy']}/{m['E190a']['balanced_accuracy']}/{m['E190b']['balanced_accuracy']}")
    print(res["decision_checks"])
    print(res["decision"])


def _evaluate(R, log):
    """C188.evaluate with arms E184 / E190a / E190b (the same metrics, CIs, McNemar and decision rule)."""
    res = C188.evaluate(R.replace({"arm": {"E190a": "E188a", "E190b": "E188b"}}), log)
    import json
    s = json.dumps(res).replace("E188a", "E190a").replace("E188b", "E190b").replace("docs/e188/PROTOCOL.md", "docs/e190/PROTOCOL.md")
    return json.loads(s)


if __name__ == "__main__":
    {"run": run}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: python -m app.e190.candidate run"))()
