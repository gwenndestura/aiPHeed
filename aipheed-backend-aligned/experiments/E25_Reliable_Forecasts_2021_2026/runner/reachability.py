"""E25 step 1 (BEFORE any model is fitted): which acceptance criteria can be met at all on this data.

Uses baselines only: naive persistence (B1), calibrated persistence (B1p: a Laplace rate, no model fitting
beyond counting), always-HIGH. For each target and lead it reports the forecast dates (origins), class counts,
evaluability, and the BEST-CASE exact one-sided sign-flip p-value that a PERFECT forecaster could reach against
each baseline:
  * vs B1 (0/1 forecasts): on a date where B1 is right its loss is 0 under ANY scoring rule, so a perfect model
    can only tie there. With m dates on which B1 errs, the best p is exactly 2^-m, whatever the metric.
  * vs B1p (probabilities strictly between 0 and 1): its Brier loss is > 0 on every date, so the best Brier p is
    2^-n over all n dates; the best accuracy p is 2^-m' with m' = dates on which B1p misclassifies.
Pooled leads (idea 3): per date, the mean difference over all evaluated leads, so each date counts once.
Writes runs/reachability.json and docs/REACHABILITY.md."""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e25lib as E  # noqa: E402

EXP = guard.EXP
qk, qs = E.qk, E.qs


def exact_p(d: np.ndarray) -> float:
    """Exact one-sided sign-flip p for mean(d) > 0 (all 2^n assignments)."""
    d = np.asarray(d, float)
    n = len(d)
    if n == 0:
        return 1.0
    S = np.array(list(itertools.product([1.0, -1.0], repeat=n)))
    null = (S * d[None, :]).mean(1)
    return float((null >= d.mean() - 1e-12).mean())


def baseline_rows(T: E.Target, k: int, tmax: int):
    rows = []
    for t in range(qk(E.FIRST_Q), tmax + 1):
        if t + k > qk(E.LAST_Q):
            continue
        tau = T.tau(t)
        te = E.test_rows(T, t, k, tau)
        if te is None:
            continue
        tr = E.training_pairs(T, t, k, tau, {})
        if tr.empty or tr["target_q"].nunique() < E.MIN_TRAIN_QUARTERS:
            continue
        te = te.assign(origin=E.origin(t).date().isoformat(), lead=k, tau=tau,
                       B1=te["y_last"].to_numpy(float),
                       B1p=E.calibrated_persistence(tr, te["y_last"].to_numpy()),
                       ALWAYS_HIGH=1.0, n_train_quarters=int(tr["target_q"].nunique()))
        rows.append(te)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def summarize(R: pd.DataFrame) -> dict:
    if R.empty:
        return {"n_origins": 0}
    out = {"n_origins": int(R["origin"].nunique()), "rows": int(len(R)), "HIGH": int(R["y"].sum()),
           "LOW": int((1 - R["y"]).sum()), "target_quarters": sorted(R["target_quarter"].unique(), key=qk),
           "origins": sorted(R["origin"].unique())}
    out["evaluable_E23_rule"] = bool(out["n_origins"] >= 8 and out["HIGH"] >= 5 and out["LOW"] >= 5)
    for b in ("B1", "B1p", "ALWAYS_HIGH"):
        err = ((R[b] >= .5).astype(int) != R["y"]).astype(float)
        bri = (R[b] - R["y"]) ** 2
        per_acc = err.groupby(R["origin"]).mean()
        per_bri = bri.groupby(R["origin"]).mean()
        m_acc = int((per_acc > 0).sum())
        m_bri = int((per_bri > 1e-15).sum())
        out[b] = {"accuracy": float(1 - err.mean()), "brier": float(bri.mean()), "errors": int(err.sum()),
                  "dates_with_error": m_acc, "dates_with_positive_brier": m_bri,
                  "best_case_p_accuracy": exact_p(per_acc.to_numpy()) if len(per_acc) <= 16 else 2.0 ** -m_acc,
                  "best_case_p_brier": exact_p(per_bri.to_numpy()) if len(per_bri) <= 16 else 2.0 ** -m_bri,
                  "best_case_p_accuracy_holm6": min(1.0, 6 * 2.0 ** -m_acc)}
    out["label_change_rows"] = int((R["y"] != R["y_last"]).sum())
    return out


def pooled(Rs: list[pd.DataFrame]) -> dict:
    R = pd.concat([r for r in Rs if not r.empty], ignore_index=True)
    if R.empty:
        return {}
    out = {"n_origins": int(R["origin"].nunique()), "rows": int(len(R)), "HIGH": int(R["y"].sum()),
           "LOW": int((1 - R["y"]).sum())}
    for b in ("B1", "B1p"):
        err = ((R[b] >= .5).astype(int) != R["y"]).astype(float)
        bri = (R[b] - R["y"]) ** 2
        # per date: mean over leads of the per-lead mean loss (each date counts once)
        pa = err.groupby([R["origin"], R["lead"]]).mean().groupby(level=0).mean()
        pb = bri.groupby([R["origin"], R["lead"]]).mean().groupby(level=0).mean()
        out[b] = {"dates_with_error": int((pa > 0).sum()), "dates_with_positive_brier": int((pb > 1e-15).sum()),
                  "best_case_p_accuracy": exact_p(pa.to_numpy()) if len(pa) <= 16 else 2.0 ** -int((pa > 0).sum()),
                  "best_case_p_brier": exact_p(pb.to_numpy()) if len(pb) <= 16 else 2.0 ** -int((pb > 0).sum())}
    return out


def main():
    rounds = E.load_rounds()
    comp, c26, D = E.load_components()
    targets = {"T1_A": E.Target("T1", "A", rounds, D), "T1_B": E.Target("T1", "B", rounds, D),
               "T1_C": E.Target("T1", "C", rounds, D), "T1_A_fixed14.6": E.Target("T1", "A", rounds, D, 14.6),
               "T2": E.Target("T2", "-", rounds, D)}
    res = {}
    for name, T in targets.items():
        res[name] = {}
        for rs, tmax in (("R_A_feature_origins", qk(E.LAST_FEATURE_Q)), ("R_P_label_history_origins", qk("2026-Q1"))):
            per, Rs = {}, []
            for k in E.LEADS:
                R = baseline_rows(T, k, tmax)
                Rs.append(R)
                per[str(k)] = summarize(R)
            res[name][rs] = {"by_lead": per, "pooled_leads": pooled(Rs)}
            if name == "T1_A" and rs == "R_A_feature_origins":
                R1 = Rs[0]
                res[name]["lead1_rows"] = R1[["origin", "target_quarter", "province_code", "v", "tau", "y", "y_last",
                                              "B1p"]].to_dict("records")
    (EXP / "runs" / "reachability.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    # ---- markdown
    L = ["# Reachability analysis (baselines only, computed before any model was fitted)", "",
         "`runner/reachability.py` -> `runs/reachability.json`. A PERFECT forecaster is assumed (every row right, "
         "probability 1 on the true class). The p-values are exact one-sided sign-flip p-values over forecast dates.",
         "", "**Why scoring probabilities cannot rescue the comparison with 0/1 persistence.** On a date where "
         "naive persistence is right, its loss is 0 under accuracy, Brier, log score or any other proper rule. A "
         "perfect model can only tie there. With m dates on which persistence errs, the best p is 2^-m whatever "
         "the metric: 0.0625 for m = 4, 0.031 for m = 5.", ""]
    for name in ("T1_A", "T1_B", "T1_C", "T1_A_fixed14.6", "T2"):
        for rs in ("R_A_feature_origins", "R_P_label_history_origins"):
            L += [f"## {name}, {rs}", "",
                  "| Lead | Dates | Rows | HIGH | LOW | Evaluable (E23) | B1 acc | B1 dates wrong | Best p vs B1 (any metric) | B1p Brier | Best Brier p vs B1p | Best acc p vs B1p | Always-HIGH acc |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for k, s in res[name][rs]["by_lead"].items():
                if not s.get("n_origins"):
                    L.append(f"| {k} | 0 | – | – | – | no | – | – | – | – | – | – | – |")
                    continue
                L.append(f"| {k} | {s['n_origins']} | {s['rows']} | {s['HIGH']} | {s['LOW']} | "
                         f"{'yes' if s['evaluable_E23_rule'] else 'no'} | {s['B1']['accuracy']:.3f} | "
                         f"{s['B1']['dates_with_error']} | {s['B1']['best_case_p_accuracy']:.4f} | "
                         f"{s['B1p']['brier']:.3f} | {s['B1p']['best_case_p_brier']:.4f} | "
                         f"{s['B1p']['best_case_p_accuracy']:.4f} | {s['ALWAYS_HIGH']['accuracy']:.3f} |")
            pl = res[name][rs]["pooled_leads"]
            if pl:
                L.append(f"| pooled 1-8 | {pl['n_origins']} | {pl['rows']} | {pl['HIGH']} | {pl['LOW']} | – | – | "
                         f"{pl['B1']['dates_with_error']} | {pl['B1']['best_case_p_accuracy']:.4f} | – | "
                         f"{pl['B1p']['best_case_p_brier']:.4f} | {pl['B1p']['best_case_p_accuracy']:.4f} | – |")
            L.append("")
    (EXP / "docs" / "REACHABILITY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
