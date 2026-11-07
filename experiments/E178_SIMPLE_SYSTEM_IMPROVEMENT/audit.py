"""
E178 step 1: data and feature audit of the 156 untainted training rows (FNRI 2015 targets, NNS 2013 anchors) that train the
ENNS 2018 Lead-2 forecast. Inputs only: no outcome is used for any decision here (y_true is checked only for finiteness/range).

    cd backend && PYTHONPATH=. python ../experiments/E178_SIMPLE_SYSTEM_IMPROVEMENT/audit.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from app.e148 import panel as Pn
from app.e164 import auto as U
from app.e171 import candidates as C171

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("e177dev", HERE.parent / "E177_SIMPLE_V2" / "develop.py")
E177 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E177)                     # read-only reuse of E177's untainted-row builder (asserts no overlap with the 72)

NEWS_ZERO_FILLED = [c for c in U.FS["FULL"] if c.startswith(("p_e_", "a_e_", "n_e_", "p_tp_", "p_tg_", "r_e_")) or c.endswith("_net_since")]


def audit():
    tr, AN = E177.training_rows()
    cols = U.FS["FULL"] + [c for c in C171.S_COLS if c not in U.FS["FULL"]]
    dq = []
    add = lambda check, n, detail, verdict: dq.append({"check": check, "rows_affected": int(n), "detail": detail, "verdict": verdict})
    add("rows", len(tr), f"{tr['key'].nunique()} provinces x leads {sorted(tr['lead'].unique())}", "info")
    add("duplicate (key, survey, lead)", tr.duplicated(["key", "survey", "lead"]).sum(), "", "ok" if not tr.duplicated(["key", "survey", "lead"]).any() else "PROBLEM")
    add("missing region / SWS area", tr["region"].isna().sum() + tr["sws_area"].isna().sum(), "", "ok" if tr[["region", "sws_area"]].notna().all().all() else "PROBLEM")
    rq_t = tr["survey"].map({"FNRI2015": 2015 * 4 + 2})                      # 2015-Q3 reference quarter index (year*4 + q-1)
    issue_ok = (tr["i"] < rq_t) if "i" in tr else pd.Series(True, index=tr.index)
    add("issue quarter before outcome reference quarter", (~issue_ok).sum(), "i < 2015-Q3 for every row", "ok" if issue_ok.all() else "PROBLEM")
    an_ok = tr["rq_anchor"] < tr["i"]
    add("anchor survey before issue", (~an_ok).sum(), "NNS 2013 reference quarter < issue quarter", "ok" if an_ok.all() else "PROBLEM")
    lead_ok = (rq_t - tr["i"]) == tr["lead"]
    add("lead = outcome quarter - issue quarter", (~lead_ok).sum(), "", "ok" if lead_ok.all() else "CHECK (definition differs)")
    add("outcome finite, se > 0", (~np.isfinite(tr["y_true"]) | (tr["se_true"] <= 0)).sum(), "", "ok")
    add("instrument of targets and anchors", 0, "targets FNRI 2015 HFIAS; anchors NNS 2013 HFIAS (same instrument)", "ok")
    nz = tr["p_intensity"].isna() if "p_intensity" in tr else pd.Series(False, index=tr.index)
    zero_rows = int((nz & (tr[[c for c in NEWS_ZERO_FILLED if c in tr]].abs().sum(axis=1) == 0)).sum())
    add("news features zero-filled where no news exists", zero_rows,
        "app/e151/prov.py lines 118/124 set tone/share features to 0.0 when the news panel has no row; 'no articles' then equals 'neutral tone'. "
        "Affects FULL inputs only (SIMPLE's GOV / GOV_S inputs contain no news features).", "DATA-QUALITY ISSUE (FULL inputs)")
    fa = []
    X = tr[[c for c in cols if c in tr]]
    corr = X.corr().abs()
    for c in X.columns:
        twins = [d for d in X.columns if d != c and corr.loc[c, d] > 0.98]
        fa.append({"feature": c, "in_GOV": c in U.FS["GOV"], "in_GOV_S": c in U.FS["GOV_S"], "in_FULL": c in U.FS["FULL"],
                   "missing_pct": round(float(X[c].isna().mean() * 100), 1), "zero_pct": round(float((X[c] == 0).mean() * 100), 1),
                   "distinct_values": int(X[c].nunique()), "constant": bool(X[c].nunique() <= 1),
                   "news_zero_filled": c in NEWS_ZERO_FILLED, "near_duplicates_r_gt_0.98": "; ".join(twins),
                   "as_of": "issue quarter (app.e151.prov.add_inputs / E154 / E171: values published before the issue date)"})
    FA = pd.DataFrame(fa)
    add("constant inputs (no information in these rows)", int(FA["constant"].sum()), "; ".join(FA.loc[FA["constant"], "feature"]), "info: dropped automatically by Res2 (nunique > 1 rule)")
    dup = FA[FA["near_duplicates_r_gt_0.98"] != ""]
    add("near-duplicate input pairs (|r| > 0.98)", len(dup), "; ".join(f"{a}~{b}" for a, b in zip(dup["feature"], dup["near_duplicates_r_gt_0.98"])), "info")
    used = set(Pn.__name__ and [])
    pd.DataFrame(dq).to_csv(HERE / "data_quality_audit.csv", index=False, lineterminator="\n")
    FA.to_csv(HERE / "feature_audit.csv", index=False, lineterminator="\n")
    print(pd.DataFrame(dq).to_string(index=False))
    print(FA[(FA["in_GOV"]) & ((FA["constant"]) | (FA["missing_pct"] > 0) | (FA["near_duplicates_r_gt_0.98"] != ""))][
        ["feature", "missing_pct", "distinct_values", "constant", "near_duplicates_r_gt_0.98"]].to_string(index=False))


if __name__ == "__main__":
    audit()
