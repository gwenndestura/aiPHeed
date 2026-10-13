"""E24 step 1: reproduce E23 from its sealed predictions, audit row identity, decompose the label, analyse errors.
No model is fitted here. Usage: python -B runner/reproduce_and_audit.py"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e23_lib as L  # noqa: E402
import run_e23 as R  # noqa: E402

EXP = guard.EXP
E23 = guard.E23_DIR
RUN, RUNB = "20261013T152113Z", "20261013T152838Z_E23B"
qk, qs = L.qk, L.qs
PROV = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
        "PH040500000": "Batangas"}


def sealed(path: Path, seal: Path) -> pd.DataFrame:
    want = json.loads(seal.read_text(encoding="utf-8"))["sha256"]
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    assert got == want, f"seal mismatch {path}"
    return pd.read_csv(path, dtype={"province_code": str})


def main():
    out = {}
    P = sealed(E23 / "runs" / RUN / "predictions_origin.csv", E23 / "runs" / RUN / "SEAL_origin.json")
    PF = sealed(E23 / "runs" / RUN / "predictions_fixed.csv", E23 / "runs" / RUN / "SEAL_fixed.json")
    IMP = sealed(E23 / "runs" / RUNB / "predictions_imp_origin.csv", E23 / "runs" / RUNB / "SEAL_imp_origin.json")
    res = json.loads((E23 / "runs" / RUN / "results.json").read_text(encoding="utf-8"))
    resb = json.loads((E23 / "runs" / RUNB / "results_e23b.json").read_text(encoding="utf-8"))

    # ---------------- 1. reproduce every reported metric
    rep, maxdiff = [], 0.0
    for mode, D in (("origin", P), ("fixed", PF)):
        for k in sorted(D["lead"].unique()):
            dk = D[D["lead"] == k]
            keys = None
            for m in L.BASELINES + [L.PROPOSED] + L.SUPPLEMENTARY:
                dm = dk[dk["model"] == m].sort_values(["origin", "province_code"])
                kk = list(zip(dm["origin"], dm["province_code"], dm["y"]))
                keys = kk if keys is None else keys
                assert kk == keys, f"rows differ for {m} lead {k}"          # identical observations
                got = L.cls_metrics(dm["y"], dm["score"])
                want = res[mode]["by_lead"][str(k)]["metrics"][m]
                for q in ("accuracy", "ROC_AUC", "Brier", "TP", "FP", "FN", "TN", "HIGH", "LOW"):
                    a, b = got[q], want[q]
                    if a is None or b is None:
                        assert a == b
                    else:
                        maxdiff = max(maxdiff, abs(a - b))
                rep.append({"target": mode, "lead": int(k), "model": m, "n_rows": got["n"],
                            "n_test_quarters": int(dm["origin"].nunique()), "HIGH": got["HIGH"], "LOW": got["LOW"],
                            **{q: got[q] for q in ("accuracy", "precision", "recall", "F1", "specificity",
                                                   "ROC_AUC", "Brier")},
                            "balanced_accuracy": (None if got["recall"] is None or got["specificity"] is None
                                                  else (got["recall"] + got["specificity"]) / 2)})
    imp1 = IMP[IMP["lead"] == 1]
    out["reproduced"] = {
        "max_abs_diff_vs_E23_results": maxdiff,
        "E23B_accuracy_lead1": float((imp1["pred"] == imp1["y"]).mean()),
        "E23B_reported": resb["origin"]["1"]["accuracy"]["IMP_lgbm_selected"],
        "persistence_accuracy_lead1": res["origin"]["by_lead"]["1"]["metrics"]["B1_naive_persistence"]["accuracy"],
        "always_HIGH_lead1": float(imp1["y"].mean()),
        "rows_lead1": int(len(imp1)), "test_quarters_lead1": int(imp1["origin"].nunique())}
    assert abs(out["reproduced"]["E23B_accuracy_lead1"] - out["reproduced"]["E23B_reported"]) < 1e-12
    pd.DataFrame(rep).to_csv(EXP / "runs" / "e23_reproduced_metrics.csv", index=False, lineterminator="\n")

    # ---------------- 2. label decomposition (approved composite target S1 = H + 2D)
    log = []
    comp, rounds, ff, gov_cols, S = R.load(log)
    c = comp[comp["S1"].notna()].copy()
    vS, vH, v2D = c["S1"].var(), c["H"].var(), (2 * c["D"]).var()
    cov = 2 * np.cov(c["H"], 2 * c["D"])[0, 1]
    within = c.groupby("quarter")["S1"].transform(lambda x: x - x.mean())
    out["label_decomposition_2021_2025"] = {
        "formula": "S1 = H(region, quarter) + 2 x D(province, quarter); D = provincial food CPI YoY - five-province mean",
        "n_province_quarters": int(len(c)), "var_S1": float(vS), "share_var_H": float(vH / vS),
        "share_var_2D": float(v2D / vS), "share_cov": float(cov / vS),
        "between_quarter_share": float(1 - within.var() / vS),
        "measured_or_proxy": "constructed proxy (regional SWS hunger + provincial relative food inflation); "
                             "not a measured provincial food-insecurity outcome",
        "D_sums_to_zero_each_quarter": bool(c.groupby("quarter")["D"].sum().abs().max() < 1e-9),
        "D_range": [float(c["D"].min()), float(c["D"].max())], "H_range": [float(c["H"].min()), float(c["H"].max())]}
    # unanimity of labels within a quarter under each origin's training threshold
    meta = json.loads((E23 / "runs" / RUN / "fold_meta_origin.json").read_text(encoding="utf-8"))
    taus = {m["target_quarter"]: m["threshold"] for k, m in meta.items() if k.startswith("k1_")}
    un = []
    for q, tau in taus.items():
        g = S[S["quarter"] == q]
        y = (g["S1"] > tau).astype(int)
        un.append({"target_quarter": q, "tau": tau, "H": float(comp.loc[comp["quarter"] == q, "H"].mean())
                   if q in set(comp["quarter"]) else None, "n_HIGH": int(y.sum()),
                   "unanimous": bool(y.nunique() == 1), "min_S1": float(g["S1"].min()), "max_S1": float(g["S1"].max()),
                   "H_minus_tau": None})
    out["test_quarter_label_unanimity_lead1"] = un

    # ---------------- 3. error analysis, lead 1, primary target
    d = P[P["lead"] == 1].copy()
    wide = d.pivot_table(index=["origin", "target_quarter", "province_code", "y", "S1", "threshold", "feature_quarter"],
                         columns="model", values="score").reset_index()
    i1 = imp1[["origin", "province_code", "score", "pred", "decision_threshold"]].rename(
        columns={"score": "E23B_score", "pred": "E23B_pred", "decision_threshold": "E23B_threshold"})
    wide = wide.merge(i1, on=["origin", "province_code"])
    # last published label per row (the persistence information)
    lastS = []
    for r in wide.itertuples():
        t = qk(r.feature_quarter)
        pubq = [q for q in S["quarter"].unique() if L.label_published(rounds, q, t)]
        g = S[(S["province_code"] == r.province_code) & S["quarter"].isin(pubq)].sort_values("tq")
        lastS.append((g["quarter"].iloc[-1], float(g["S1"].iloc[-1])))
    wide["last_published_quarter"] = [a for a, _ in lastS]
    wide["last_published_S1"] = [b for _, b in lastS]
    wide["province"] = wide["province_code"].map(PROV)
    wide["label_changed_vs_last_published"] = ((wide["last_published_S1"] > wide["threshold"]).astype(int) != wide["y"])
    wide["margin_true"] = wide["S1"] - wide["threshold"]
    for m, col in (("persistence", "B1_naive_persistence"), ("proposed", L.PROPOSED)):
        wide[f"{m}_pred"] = (wide[col] >= 0.5).astype(int)
        wide[f"{m}_error"] = np.where(wide[f"{m}_pred"] == wide["y"], "", np.where(wide["y"] == 1, "FN", "FP"))
    wide["E23B_error"] = np.where(wide["E23B_pred"] == wide["y"], "", np.where(wide["y"] == 1, "FN", "FP"))
    cols = ["target_quarter", "origin", "feature_quarter", "province", "province_code", "S1", "threshold", "margin_true", "y",
            "last_published_quarter", "last_published_S1", "label_changed_vs_last_published",
            "B1_naive_persistence", "persistence_error", L.PROPOSED, "proposed_error", "E23B_score", "E23B_threshold",
            "E23B_pred", "E23B_error", "B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only", "B5_lgbm_gov_only",
            "B6_lgbm_nlp_only", "S_lr_psa_only"]
    wide[cols].sort_values(["target_quarter", "province"]).to_csv(EXP / "PREDICTIONS_BY_QUARTER.csv", index=False,
                                                                  lineterminator="\n")
    ch = wide["label_changed_vs_last_published"]
    out["error_analysis_lead1_primary"] = {
        "rows": int(len(wide)), "label_changes_vs_last_published": int(ch.sum()),
        "persistence_errors": int((wide["persistence_error"] != "").sum()),
        "persistence_errors_are_exactly_the_label_changes": bool(((wide["persistence_error"] != "") == ch).all()),
        "proposed_errors": int((wide["proposed_error"] != "").sum()),
        "proposed_errors_on_changed_rows": int(((wide["proposed_error"] != "") & ch).sum()),
        "proposed_errors_on_unchanged_rows": int(((wide["proposed_error"] != "") & ~ch).sum()),
        "E23B_errors": int((wide["E23B_error"] != "").sum()),
        "E23B_errors_on_changed_rows": int(((wide["E23B_error"] != "") & ch).sum()),
        "E23B_errors_on_unchanged_rows": int(((wide["E23B_error"] != "") & ~ch).sum()),
        "changed_rows": wide.loc[ch, ["target_quarter", "province", "y", "S1", "threshold", "last_published_S1"]]
        .to_dict("records"),
        "abs_margin_median_changed": float(wide.loc[ch, "margin_true"].abs().median()),
        "abs_margin_median_unchanged": float(wide.loc[~ch, "margin_true"].abs().median()),
        "proposed_predicts_all_HIGH_quarters": int(wide.groupby("origin")["proposed_pred"].min().sum()),
        "proposed_within_quarter_prob_sd_median": float(wide.groupby("origin")[L.PROPOSED].std().median()),
        "quarters": int(wide["origin"].nunique())}
    (EXP / "runs" / "reproduction_and_audit.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "test_quarter_label_unanimity_lead1"}, indent=1, default=str)[:6000])
    print(pd.DataFrame(un).to_string())


if __name__ == "__main__":
    main()
