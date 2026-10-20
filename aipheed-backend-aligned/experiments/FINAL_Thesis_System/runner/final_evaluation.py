"""Final thesis evaluation (Objectives 2 and 4), computed only from frozen, sealed predictions; nothing is refitted or
tuned here.

  Objective 2 I-IV and V: every feasible lead (1-3; lead 4 not computable under the cutoffs) from the sealed E63
  walk-forward predictions (E56-TUNED LightGBM, expanding window, issue-date cutoffs). Reliability criterion = the E63
  section 8 rule, pre-registered 2026-10-19 (protocol sha 5b3ee7e9...) before any lead-1/lead-3 result: paired Brier
  better than persistence AND climatology, each with a quarter-cluster 95% CI below 0 and a quarter sign test p < 0.05.
  Objective 4: the four Chapter I baselines (E55 run baselines_20261017T154832Z) against E56 on the identical 45 rows
  (targets 2024-Q3..2026-Q3, same issue dates, same T43 labels), plus the majority class.

Writes backend/data/thesis/final_evaluation.json (served by the thesis mode) and the tables beside this file.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/FINAL_Thesis_System/runner/final_evaluation.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "E66_Best_Methodology_Review" / "runner"))
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e66_lib as H  # noqa: E402
import e56_lib as G  # noqa: E402

F, L, np, pd = G.F, G.L, G.np, G.pd
from scipy.stats import binomtest  # noqa: E402

E63 = EXP / "E63_Lead_Time_Study"
E55B = EXP / "E55_Food_Insecurity_LightGBM" / "runs" / "baselines_20261017T154832Z" / "rows_baselines.csv"
E57 = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
OUT = HERE.parent / "out"
DEST = H.BACKEND / "data" / "thesis" / "final_evaluation.json"
E63_PROTOCOL_SHA = "5b3ee7e9cd64d40dcd874c37ef3158bb4d60bba31f9ebcdfc124415e218ba0f2"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_frozen():
    got = hashlib.sha256((E63 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == E63_PROTOCOL_SHA, "E63 protocol changed"
    for p in (E63 / "sealed" / "predictions.csv", E57):
        assert sha(p) == (p.parent / (p.name + ".sha256")).read_text().split()[0], f"{p} changed after sealing"


def metrics(y, p, dec=None):
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= 0.5).astype(int) if dec is None else np.asarray(dec, int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    n = len(y)
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else None
    lo, hi = H.wilson(tp + tn, n)
    auc = H.auc(y, p)
    return {"n": n, "positives": int(y.sum()), "accuracy": (tp + tn) / n, "accuracy_wilson95": [lo, hi],
            "precision_HIGH": prec, "recall_HIGH": rec, "recall_LOW": tn / (tn + fp) if tn + fp else None, "f1_HIGH": f1,
            "balanced_accuracy": 0.5 * ((rec or 0) + (tn / (tn + fp) if tn + fp else 0)),
            "auc_roc": None if not np.isfinite(auc) else auc, "brier": float(np.mean((p - y) ** 2)),
            "confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn}}


def paired_rule(R, ref, arm):
    p = H.paired(R.assign(HIGH=R["y"]), ref, arm, "HIGH", seed=63)
    w, l_ = p["quarter_wins"], p["quarter_losses"]
    p2 = binomtest(w, w + l_, 0.5, alternative="two-sided").pvalue if w + l_ else 1.0
    p["sign_p_two_sided"] = float(p2)
    p["holds"] = bool(p["ci95_hi"] < 0 and p2 < 0.05 and w > l_)
    return p


def lead_section():
    S = pd.read_csv(E63 / "sealed" / "predictions.csv", dtype={"province_code": str})
    Y = F.t43_labels(L.load())[["province_code", "quarter", "T43"]].rename(columns={"quarter": "target", "T43": "y"})
    S = S.merge(Y, on=["province_code", "target"], how="left")
    assert S["y"].notna().all()
    S["y"] = S["y"].astype(int)
    ref = pd.read_csv(E63 / "tables" / "lead_metrics.csv")
    out, tables = [], []
    for lead, R in S.groupby("lead"):
        R = R.copy()
        R["EW_dec"] = (R["E56_p_price"] >= 0.5).astype(int)
        arms = {"LightGBM E56-TUNED P(HIGH)": metrics(R["y"], R["E56_p"]),
                "LightGBM early-warning reading (price part >= 0.5)": metrics(R["y"], R["E56_p_price"], R["EW_dec"]),
                "Naive persistence": metrics(R["y"], R["PERSIST_p"]), "Majority class (always LOW)": metrics(R["y"], R["MAJORITY_p"]),
                "Climatology (training base rate)": metrics(R["y"], R["CLIM_p"])}
        r0 = ref[(ref["lead"] == lead) & (ref["set"] == "full") & (ref["arm"] == "E56")].iloc[0]
        assert abs(arms["LightGBM E56-TUNED P(HIGH)"]["accuracy"] - r0["accuracy"]) < 1e-5
        assert abs(arms["LightGBM E56-TUNED P(HIGH)"]["brier"] - r0["brier"]) < 1e-6
        rp, rc = paired_rule(R, "PERSIST_p", "E56_p"), paired_rule(R, "CLIM_p", "E56_p")
        reliable = rp["holds"] and rc["holds"]
        out.append({"lead": int(lead), "quarters": int(R["target"].nunique()), "rows": int(len(R)),
                    "targets": [R["target"].min(), R["target"].max()], "metrics": arms,
                    "vs_persistence": {k: rp[k] for k in ("mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins", "quarter_losses", "sign_p_two_sided", "holds")},
                    "vs_climatology": {k: rc[k] for k in ("mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins", "quarter_losses", "sign_p_two_sided", "holds")},
                    "reliable": reliable})
        for name, m in arms.items():
            tables.append({"lead": int(lead), "model": name, **{k: v for k, v in m.items() if k not in ("confusion", "accuracy_wilson95")},
                           "acc_lo": m["accuracy_wilson95"][0], "acc_hi": m["accuracy_wilson95"][1], **m["confusion"]})
    reliable = [x["lead"] for x in out if x["reliable"]]
    return out, (max(reliable) if reliable else None), pd.DataFrame(tables)


def baseline_section():
    B = pd.read_csv(E55B, dtype={"province_code": str})
    S = pd.read_csv(E57, dtype={"province_code": str})[["target", "province_code", "E56_p"]]
    R = B.merge(S, on=["target", "province_code"], how="inner")
    assert len(R) == 45 and R["E56_p"].notna().all()
    R = R.rename(columns={"y": "y"})
    R["y"] = R["y"].astype(int)
    R["MAJ_p"] = 0.0
    arms = {"LightGBM E56-TUNED (proposed)": "E56_p", "I. Naive persistence": "B1_PERSIST_p",
            "II. PSA-only indicator (logistic regression on government indicators)": "B2_LR_GOV_p",
            "III. NLP-only sentiment (logistic regression on news features)": "B4_LR_NLP_p",
            "IV. Logistic regression (combined government + news)": "B6_LR_COMB_p", "Majority class (always LOW)": "MAJ_p"}
    res, tab = {}, []
    for name, col in arms.items():
        m = metrics(R["y"], R[col])
        if col != "E56_p":
            pr = H.paired(R.assign(HIGH=R["y"]), col, "E56_p", "HIGH", seed=55)
            n01 = int(((R["E56_p"] >= .5).astype(int) == R["y"]).sum())
            a = (R["E56_p"] >= .5).astype(int) == R["y"]
            b = (R[col] >= .5).astype(int) == R["y"]
            w, l_ = int((a & ~b).sum()), int((~a & b).sum())
            mc = binomtest(w, w + l_, 0.5).pvalue if w + l_ else 1.0
            m["paired_vs_lightgbm"] = {"brier_diff_lightgbm_minus_baseline": pr["mean_brier_diff"], "ci95": [pr["ci95_lo"], pr["ci95_hi"]],
                                       "quarter_wins_lightgbm": pr["quarter_wins"], "quarter_losses_lightgbm": pr["quarter_losses"],
                                       "quarter_sign_p": pr["sign_p"],
                                       "brier_advantage_established": bool(pr["ci95_hi"] < 0 and pr["sign_p"] < 0.05),
                                       "mcnemar_rows_lightgbm_right_only": w, "mcnemar_rows_baseline_right_only": l_,
                                       "mcnemar_p": float(mc)}
        res[name] = m
        tab.append({"model": name, **{k: v for k, v in m.items() if k not in ("confusion", "accuracy_wilson95", "paired_vs_lightgbm")},
                    **m["confusion"], **({f"paired_{k}": v for k, v in m.get("paired_vs_lightgbm", {}).items()})})
    return {"rows": 45, "quarters": int(R["target"].nunique()), "targets": [R["target"].min(), R["target"].max()],
            "label": "T43", "models": res}, pd.DataFrame(tab)


def main():
    check_frozen()
    leads, furthest, LT = lead_section()
    base, BT = baseline_section()
    body = {
        "schema": "aipheed.thesis.final_evaluation/1",
        "evidenceStatus": ("Development evidence: every scored row was examined during model development (E56-E69). "
                           "No independent (unseen) quarter has been scored yet; the forecasts for 2026-Q4 and 2027-Q1 are "
                           "sealed (E68/E69) for that purpose."),
        "target": ("T43, an exploratory food-stress label: regional SWS hunger above 11.3% AND provincial food-price "
                   "pressure; on every evaluated row it equals provincial food-price pressure. Not a measure of household "
                   "food insecurity."),
        "objective2": {"leads": leads, "lead4": "not computable under the pre-registered information cutoffs",
                       "reliabilityCriterion": ("E63 section 8 (pre-registered 2026-10-19, protocol sha 5b3ee7e9): paired Brier "
                                                "better than naive persistence AND climatology, each with a quarter-cluster 95% "
                                                "CI below 0 and a two-sided quarter sign test p < 0.05"),
                       "furthestReliableLead": furthest,
                       "verdict": ("no lead meets the reliability criterion" if furthest is None else f"lead {furthest}")},
        "objective4": base,
        "goal75": ("Lead-2 accuracy 0.72 (36/50, E57 rolling origin) and 0.778 (35/45, the Objective 4 rows); neither is "
                   "distinguishable from always predicting LOW at the quarter level, and neither is on unseen quarters: the "
                   ">75% Lead-2 goal is not demonstrated."),
        "sources": {"e63_predictions_sha256": sha(E63 / "sealed" / "predictions.csv"), "e57_predictions_sha256": sha(E57),
                    "e55_baselines_sha256": sha(E55B)},
    }
    DEST.write_bytes(json.dumps(body, indent=1, default=float).encode("utf-8"))
    OUT.mkdir(exist_ok=True)
    H.write_csv(LT, OUT / "lead_time_table.csv")
    H.write_csv(BT, OUT / "baseline_table.csv")
    pd.set_option("display.width", 250)
    print(LT[["lead", "model", "n", "accuracy", "precision_HIGH", "recall_HIGH", "f1_HIGH", "auc_roc", "brier", "TP", "FP", "FN", "TN"]].round(3).to_string())
    for x in leads:
        print(x["lead"], x["vs_persistence"], x["vs_climatology"], x["reliable"])
    print("furthest", furthest)
    print(BT.round(3).to_string())


if __name__ == "__main__":
    main()
