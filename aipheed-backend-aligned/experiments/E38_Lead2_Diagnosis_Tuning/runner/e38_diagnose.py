"""E38 step 1-2: verify the E37 lead-2 evaluation and diagnose its weak result. Descriptive only: nothing here selects
a model, a threshold or a feature set.

    python -B runner/e38_diagnose.py   -> runs/e38_verification_diagnosis.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E38 = HERE.parent
sys.path.insert(0, str(E38.parent / "E37_Next_Quarter_Forecast" / "runner"))
import e37_lib as L  # noqa: E402

L.L6.guard32.EXP = E38
C, np, pd = L.C, L.np, L.pd
K = 2
E37RUN = E38.parent / "E37_Next_Quarter_Forecast" / "runs" / "20261015T031545Z"
ROOT = E38.parents[2]


def auc(y, s):
    y, s = np.asarray(y), np.asarray(s, float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def main():
    out = {}
    d = L.Data()
    Pr = pd.read_csv(E37RUN / "predictions.csv", dtype={"province_code": str})
    res = json.loads((E37RUN / "results.json").read_text(encoding="utf-8"))
    # ---------------- 1. the select() reporting fix: does it change any evaluated sample or choice?
    dates = L.eval_dates(d, K)
    preds = {t: {a: dict(zip(g["province_code"], g["p"])) for a, g in Pr[Pr["t"] == C.qs(t)].groupby("arm")} for t in dates}
    labels = {t: {p: d.label(p, t + K, t) for p in C.PROVS} for t in dates}
    same, rows = True, []
    for t in dates:
        prior = L.eligible_prior(d, t, K, dates)
        raw_choice, raw_info = L.L6.select("E36-LGBM", prior, preds, labels)          # E36 select, unpatched labels
        fixed_choice, fixed_info = L.select("E36-LGBM", prior, preds, labels, K)        # E37 wrapper
        same &= raw_choice == fixed_choice and raw_info.get("scores") == fixed_info.get("scores")
        rows.append({"target": C.qs(t + K), "prior_origins": [C.qs(x) for x in prior],
                     "unpatched_label_of_prior": raw_info["prior_dates"], "corrected_label": fixed_info["prior_dates"],
                     "chosen": L.cfg_name(*fixed_choice),
                     "stored_choice": res["selections"]["E36-LGBM"][C.qs(t + K)]["chosen"]})
    out["select_fix"] = {"choices_and_scores_identical": bool(same),
                         "stored_choices_match": all(r["chosen"] == r["stored_choice"] for r in rows),
                         "effect": "display only: the prior dates were named origin+1 instead of origin+2; the "
                                   "selection is keyed by origin and uses the same predictions and labels",
                         "rows": rows}
    # ---------------- 2. alignment and comparability
    e, b = Pr[Pr["arm"] == "E36-LGBM"], Pr[Pr["arm"] == "B1_PERSISTENCE"]
    key = ["t", "target_quarter", "province_code"]
    chk = {"rows_per_date_5": bool((e.groupby("t").size() == 5).all()),
           "no_duplicates": not e.duplicated(key).any(),
           "target_is_origin_plus_2": bool(((e["target_quarter"].map(C.qk) - e["t"].map(C.qk)) == K).all()),
           "origin_before_target_start": bool((pd.to_datetime(e["origin"]) <
                                               e["target_quarter"].map(lambda q: pd.Timestamp(int(q[:4]), 3 * int(q[-1]) - 2, 1))).all()),
           "lgbm_and_persistence_identical_rows": e[key + ["y"]].reset_index(drop=True).equals(b[key + ["y"]].reset_index(drop=True)),
           "labels_recomputed_equal": all(int(r.y) == d.label(r.province_code, C.qk(r.target_quarter), C.qk(r.t)) for r in e.itertuples())}
    acc = lambda g: int(((g["p"] >= .5).astype(int) == g["y"]).sum())  # noqa: E731
    chk["recomputed_counts"] = {"E36-LGBM": f"{acc(e)}/{len(e)}", "B1_PERSISTENCE": f"{acc(b)}/{len(b)}"}
    low = e[e["y"] == 0]
    chk["low_rows"] = [{"target": r.target_quarter, "province": C.NAMES[r.province_code], "p_lgbm": round(r.p, 3),
                        "S1": round(d.Sv[(r.province_code, C.qk(r.target_quarter))], 3), "tau": round(d.tau(C.qk(r.t)), 3),
                        "persistence": float(b[(b.t == r.t) & (b.province_code == r.province_code)]["p"].iloc[0])}
                       for r in low.itertuples()]
    out["alignment"] = chk
    # ---------------- 3. A. labels and sample
    per = e.groupby("target_quarter")["y"].agg(["size", "sum"]).rename(columns={"size": "n", "sum": "HIGH"})
    out["labels"] = {"dates": len(per), "rows": int(per["n"].sum()), "HIGH": int(per["HIGH"].sum()),
                     "LOW": int((per["n"] - per["HIGH"]).sum()),
                     "dates_with_any_LOW": per[per["HIGH"] < 5].index.tolist(),
                     "independent_regional_observations": len(per),
                     "per_date": per.astype(int).to_dict(orient="index"),
                     "excluded_targets_no_label": ["2022-Q1", "2025-Q2", "2025-Q3"],
                     "note": "the 5 rows of a date share one SWS Balance Luzon value; only D (prices) differs"}
    # ---------------- 3. B. features (training data only, at the operational origin; no outer outcome)
    tr = d.train(L.OPERATIONAL_T, K)
    feat = {}
    for f in L.L6.COMB:
        x = tr[f].astype(float)
        feat[f] = {"train_auc": auc(tr["y"], x), "missing_share": float(x.isna().mean()),
                   "zero_share": float((x == 0).mean()), "n": int(len(x))}
    out["features_training_only"] = {"origin": "2026-10-01", "rows": int(len(tr)), "HIGH": int(tr["y"].sum()),
                                     "univariate": feat,
                                     "corr_H_last_H_margin": float(tr["H_last"].corr(tr["H_margin"])),
                                     "corr_D_last_Dnow": float(tr["D_last"].corr(tr["Dnow"]))}
    # five triggers from the in-window validated news store (titles; existing classifier)
    sys.path.insert(0, str(ROOT / "backend"))
    from app.ml.nlp.trigger_classifier import ALL_TRIGGERS, classify_triggers
    arts = [json.loads(x) for x in open(L.C.STORE / "articles.jsonl", encoding="utf-8")]
    a = pd.DataFrame(arts)
    a = a[a["geo_province_code"].notna()].copy()
    a["tr"] = a["title"].fillna("").map(classify_triggers)
    out["five_triggers_news"] = {"attributed_titles": int(len(a)), "any_trigger": int((a["tr"].map(len) > 0).sum()),
                                 "by_trigger": {c: int(a["tr"].map(lambda t: c in t).sum()) for c in ALL_TRIGGERS},
                                 "province_quarters_with_any": int(a[a["tr"].map(len) > 0].groupby(
                                     ["geo_province_code", "quarter"]).ngroups),
                                 "province_quarters_total": 5 * 23}
    # ---------------- 3. C. model behaviour (on the E37 outer rows: DIAGNOSTIC ONLY, never used to choose)
    out["selection_path"] = {q: v["chosen"] for q, v in res["selections"]["E36-LGBM"].items()}
    out["calibration_in_the_large"] = float(e["p"].mean() - e["y"].mean())
    sweep = []
    for thr in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        yh = (e["p"] >= thr).astype(int)
        sweep.append({"threshold": thr, "accuracy": float((yh == e["y"]).mean()),
                      "low_recall": float(((yh == 0) & (e["y"] == 0)).sum() / max((e["y"] == 0).sum(), 1)),
                      "high_recall": float(((yh == 1) & (e["y"] == 1)).sum() / max((e["y"] == 1).sum(), 1))})
    out["threshold_sweep_DIAGNOSTIC_ONLY"] = {"warning": "computed on already-examined outer outcomes to explain the "
                                                         "mechanism; not used for any selection", "rows": sweep}
    e2 = e.assign(tq=e["target_quarter"].map(C.qk))
    out["by_period"] = {"targets_2023Q3_2024Q4": f"{acc(e2[e2.tq <= C.qk('2024-Q4')])}/{int((e2.tq <= C.qk('2024-Q4')).sum())}",
                        "targets_2025Q1_2026Q3": f"{acc(e2[e2.tq > C.qk('2024-Q4')])}/{int((e2.tq > C.qk('2024-Q4')).sum())}"}
    out["lead1_vs_lead2_training_label_agreement"] = (
        "at lead 2 the latest label is two quarters older; persistence keeps 0.80 because 49/55 labels are HIGH")
    (E38 / "runs").mkdir(exist_ok=True)
    (E38 / "runs" / "e38_verification_diagnosis.json").write_bytes(json.dumps(C.clean(out), indent=1).encode())
    print(json.dumps({k: out[k] for k in ("select_fix", "alignment", "labels", "five_triggers_news", "by_period",
                                          "calibration_in_the_large")}, indent=1, default=str)[:6000])
    print(json.dumps(out["threshold_sweep_DIAGNOSTIC_ONLY"]["rows"]))
    print({f: (None if v["train_auc"] is None else round(v["train_auc"], 3), round(v["zero_share"], 2))
           for f, v in feat.items()})


if __name__ == "__main__":
    main()
