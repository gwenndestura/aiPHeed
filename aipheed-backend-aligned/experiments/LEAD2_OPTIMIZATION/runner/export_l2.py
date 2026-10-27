"""Export the adopted LEAD2_OPTIMIZATION model (P0H4) for the backend (Addendum 3 adoption + PROTOCOL_LEAD2 serve rule,
out/serve_rule_addendum3.json).

P0H4 is the served unified LightGBM unchanged (UNI-FINAL's price part pi_P: one LightGBM across leads, all 12 families,
lead, world prices); only the hunger-condition probability changes: H4 = the latest Balance Luzon reading with its
uncertainty from the pooled 2021+ latest-reading errors of all four SWS areas at the same true horizon (fewer than 8
errors -> the previous pi_H).

    python export_l2.py

rows.csv           the served rows (walk-forward Lead 1 + Leads 1-4 issued 2026-10-01), same columns as before, with
                   pi_hunger = H4, probability = H4 x pi_P, and per-group input availability (avail_<group>)
evaluation.json    P0H4 verdicts per lead, horizon block, Lead-2 optimisation summary, new seal hash
out/sealed_prospective_P0H4.csv  P0H4 forecasts issued 2026-10-01 for every lead 1..K (+ .sha256)
"""
from __future__ import annotations

import json

import l2_lib as X
import run_l2 as RL
import a3 as A3

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
OUT = X.OUT
DEST = X.EXP.parents[1] / "backend" / "data" / "ch1_engine"
GROUPS = {"market": ["A1_food", "A1_gap", "A_mom", "A2", "A3", "W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy"],
          "climate": ["C1", "C2", "C3", "W_urea_yoy"], "fish_kill": ["C4"], "employment": ["E1"],
          "ofw_remittance": ["E2"]}
LEAD_KEYS = ("n", "n_quarters", "quarters", "high_share", "metrics", "accuracy_ci90", "baseline_accuracy",
             "baseline_balanced_accuracy", "criteria", "reliable", "reliable_strict", "loqo_min", "acc_thirds", "onsets",
             "onset_recall", "brier_vs_persist_si", "brier_vs_clim", "confusion", "average_precision",
             "false_negative_rate", "rising_acc", "falling_acc", "surge_block", "later_block", "later_check", "verdict")
WHY_NOT_LONGER = (
    "Every lead from 2 on fails the reliability rule. At Lead 2 the binding limit is the hunger condition: the 2023-Q4 "
    "and 2024-Q2 hunger surges were not visible in any SWS reading published before those forecasts, so 7 of the 17 "
    "HIGH cases cannot be reached and HIGH recall stays at 0.35. Even with the hunger condition known exactly, the "
    "price part would reach only accuracy 0.74 at Lead 2. Leads 1-5 meet the 10-quarter testability rule R1; Leads "
    "6-15 have 9 down to 1 target quarters; Leads 16+ have no labelled target in 2021-2026.")


def main():
    U.setup()
    K = RL._K()
    S = U.stack(K)
    old = pd.read_csv(UNI_ROWS, dtype={"province_code": str})
    seal_old = pd.read_csv(U.OUT / "sealed_prospective.csv", dtype={"province_code": str})
    R = pd.concat([old[old["issue_date"] < "2026-10-01"], seal_old], ignore_index=True)
    R["t"] = R["quarter"].map(L.qi) - R["lead"]
    h4 = {}
    for t, k in R[["t", "lead"]].drop_duplicates().itertuples(index=False):
        h4[(int(t), int(k))] = A3.h4(int(t), int(k))
    new_h = [h4[(int(t), int(k))] for t, k in zip(R["t"], R["lead"])]
    R["pi_hunger"] = [h if not np.isnan(h) else o for h, o in zip(new_h, R["pi_hunger"])]
    R["probability"] = R["pi_hunger"] * R["pi_price"]
    R["class"] = np.where(R["probability"] >= 0.5, "HIGH", "LOW")
    Si = S.set_index(["t", "lead", "province_code"])
    for g, cs in GROUPS.items():
        R[f"avail_{g}"] = [int(bool(Si.loc[(int(t), int(k), p), cs].notna().any()))
                           for t, k, p in zip(R["t"], R["lead"], R["province_code"])]
    # the export must reproduce the evaluated P0H4 probabilities exactly
    P = pd.read_csv(OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    chk = R.assign(q=R["quarter"].map(L.qi)).merge(P[["province_code", "q", "lead", "P0H4_p3", "P0_price"]],
                                                    on=["province_code", "q", "lead"])
    lead1 = P[P["lead"] == 1]
    assert len(chk[chk["lead"] == 1]) == len(lead1), "export rows != evaluated Lead-1 rows"
    assert np.allclose(chk["pi_price"], chk["P0_price"], atol=1e-5), "served price part != evaluated P0"
    assert np.allclose(chk["probability"], chk["P0H4_p3"], atol=1e-5), "export != evaluated P0H4"
    R = R.drop(columns=["t"])
    seal = R[R["issue_date"] >= "2026-10-01"].copy()
    seal.to_csv(OUT / "sealed_prospective_P0H4.csv", index=False, lineterminator="\n", float_format="%.6g")
    sha = FM.sha256(OUT / "sealed_prospective_P0H4.csv")
    (OUT / "sealed_prospective_P0H4.csv.sha256").write_text(sha + "\n", encoding="utf-8", newline="\n")
    served = R[(R["issue_date"] < "2026-10-01") | (R["lead"] <= 4)]
    served.to_csv(DEST / "rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    write_evaluation(S, K, sha)
    print("exported", len(served), "rows", served.groupby("lead").size().to_dict(), "| sealed", len(seal), sha[:8])


UNI_ROWS = OUT / "previous_served" / "served_rows_UNI_FINAL.csv"


def write_evaluation(S, K, sha):
    r3 = json.loads((OUT / "results_addendum3.json").read_text())
    A = r3["candidates"]["P0H4"]
    rule = json.loads((OUT / "serve_rule_addendum3.json").read_text())["rule"]
    r4 = json.loads((OUT / "results_addendum4.json").read_text())
    leads = {k: {x: v[x] for x in LEAD_KEYS if x in v} for k, v in A["leads"].items()}
    P = pd.read_csv(OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    tq = S.drop_duplicates(["t", "lead"]).set_index(["t", "lead"])["sws_newest_q"]
    horizon = {"leads_evaluated": sorted(int(k) for k in A["leads"]),
               "testable_horizon_R1": max(int(k) for k, v in A["leads"].items() if v["criteria"]["R1"]),
               "max_reliable_lead": A["max_r1_r7_lead"] or None,
               "individually_passing_leads": sorted(int(k) for k, v in A["leads"].items() if v["reliable"]),
               "generated_up_to": K, "why_not_longer": WHY_NOT_LONGER, "leads": {}}
    for k, v in A["leads"].items():
        d = P[P["lead"] == int(k)].drop_duplicates(["t"])
        tru = sorted({int(t + int(k) - L.qi(tq[(t, int(k))])) for t in d["t"]})
        horizon["leads"][k] = {"n": v["n"], "n_quarters": v["n_quarters"], "accuracy": v["metrics"]["accuracy"],
                               "always_low_accuracy": v["baseline_accuracy"]["ALWAYS-LOW"], "reliable": v["reliable"],
                               "criteria": v["criteria"], "quarters_after_issue": int(k), "quarters_after_newest_sws": tru}
    P1 = P[P["lead"] == 1]
    b = pd.cut(P1["P0H4_p3"], [0, .1, .3, .5, .7, .9, 1.0], include_lowest=True)
    g = P1.groupby(b, observed=True).agg(n=("y", "size"), mean_p=("P0H4_p3", "mean"), observed=("y", "mean"))
    ev = {"model": ("P0H4: the unified LightGBM of UNI-FINAL (one model across all leads; all 12 FIRI v2 families + "
                    "lead + World Bank world prices, monotone food-price terms) for the price condition, times the "
                    "hunger-condition probability from the latest Balance Luzon SWS reading with its uncertainty pooled "
                    "over all four SWS areas (2021+); HIGH at 0.50"),
          "protocol_sha256": FM.sha256(X.L2 / "PROTOCOL_LEAD2.md"),
          "addenda_sha256": {n: FM.sha256(X.L2 / f) for n, f in (
              ("1", "ADDENDUM_1_STRUCTURAL_PRIOR.md"), ("2", "ADDENDUM_2_CONTROLLED_COMPARISON.md"),
              ("3", "ADDENDUM_3_HUNGER_ONSET.md"), ("4", "ADDENDUM_4_ONE_MODEL.md"))},
          "price_model_protocol_sha256": json.loads((U.OUT / "results.json").read_text())["protocol_sha256"],
          "selection": r3["selection"], "serve_rule": rule,
          "max_reliable_lead": A["max_r1_r7_lead"] or None, "max_reliable_lead_strict": A["max_r1_r7_lead"] or None,
          "leads": leads, "horizon": horizon, "seal_sha256": sha, "seal_issue_date": "2026-10-01",
          "previous_seal_sha256": FM.sha256(U.OUT / "sealed_prospective.csv"),
          "calibration_lead1": {"bins": [{"bin": str(i), "n": int(r.n), "mean_p": float(r.mean_p),
                                          "observed": float(r.observed)} for i, r in g.iterrows()],
                                "mean_p": float(P1["P0H4_p3"].mean()), "observed_rate": float(P1["y"].mean())},
          "serve_note": ("Replaces UNI-FINAL under the frozen LEAD2_OPTIMIZATION serve rule: same LightGBM, hunger-"
                         "condition uncertainty from all four SWS areas. Lead 1 accuracy 0.843 (UNI-FINAL 0.829), Lead-2 "
                         "Brier 0.194 (0.206); Lead-2 classifications unchanged. Lead 2 remains not reliable."),
          "one_model_candidate": {"name": r4["selection"]["chosen"], "served": r4["serve_rule"]["serve"],
                                  "lead1_accuracy": r4["models"][r4["selection"]["chosen"]]["leads"]["1"]["metrics"]["accuracy"],
                                  "lead1_recall": r4["models"][r4["selection"]["chosen"]]["leads"]["1"]["metrics"]["recall"],
                                  "max_reliable_lead": r4["models"][r4["selection"]["chosen"]]["max_r1_r7_lead"] or None,
                                  "note": "hunger information inside the one LightGBM (trained on T43c); fails HIGH recall at Lead 1"},
          "post_hoc_improved": None}
    FM.write_json(DEST / "evaluation.json", ev)


if __name__ == "__main__":
    main()
