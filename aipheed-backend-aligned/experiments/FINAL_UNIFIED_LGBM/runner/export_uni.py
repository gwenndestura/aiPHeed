"""Export the unified model (UNI-FINAL: one LightGBM across leads, U2 columns + pi_H) for the backend, replacing the
per-lead CH1-LGBM rows in backend/data/ch1_engine/ (the user's directive of 2026-10-27: one unified LightGBM is the final
methodology; CH1-LGBM stays in FINAL_THESIS_OBJECTIVES for comparison).

rows.csv          walk-forward Lead-1 forecast for every quarter it can be issued, and the Lead 2-4 forecasts issued
                  2026-10-01; same columns as before (pi_hunger, pi_price, probability, class at 0.50, observed, SHAP)
evaluation.json   frozen UNI-FINAL verdicts per lead (1..K), horizon block (generated / testable / reliable), news
                  ablation, comparison with CH1-LGBM, post-hoc UNI-IMPROVED summary, seal hash
out/sealed_prospective.csv   UNI-FINAL forecasts issued 2026-10-01 for every lead 1..K (+ .sha256)

    python export_uni.py
"""
from __future__ import annotations

import json

import uni_lib as U

C, FM, B, E, L, np, pd = U.C, U.FM, U.B, U.E, U.L, U.np, U.pd
OUT = U.OUT
DEST = U.EXP.parents[1] / "backend" / "data" / "ch1_engine"
FAMS = ("A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1")
WHY_NOT_LONGER = (
    "The unified model pools the rows of every lead, so more leads have evaluable quarters than with one model per lead "
    "(Leads 1-5 meet the 10-quarter rule R1; 6-15 have 9 down to 1). Leads 16+ have no labelled target in 2021-2026. "
    "Every lead from 2 on fails the reliability rule: the model cannot tell in advance which provinces' food inflation "
    "will exceed its threshold two or more quarters ahead (AUC 0.59 at Lead 2), even with world rice and cereal prices.")
LEAD_KEYS = ("n", "n_quarters", "quarters", "high_share", "metrics", "accuracy_ci90", "baseline_accuracy",
             "baseline_balanced_accuracy", "criteria", "reliable", "reliable_strict", "loqo_min", "acc_thirds", "onsets",
             "onset_recall", "brier_vs_persist_si", "brier_vs_clim", "news_ablation", "vs_ch1_per_lead",
             "confirmation_block", "hunger_condition_quarters")


def _qi(s):
    return L.qi(s) if isinstance(s, str) and "-Q" in s else None


def rows_for(S, t, leads, lab) -> list[dict]:
    p = U.fit_predict(S, t, "U2", True, explain=True)
    if p is None:
        return []
    te = S[(S["t"] == t)].set_index(["lead", "province_code"])
    out = []
    for r in p[p["lead"].isin(leads)].to_dict("records"):
        x = te.loc[(r["lead"], r["province_code"])]
        q = int(r["target_q"])
        obs = lab["y"].get((r["province_code"], q))
        prob = float(r["H1"] * r["pi_price"])
        row = {"province_code": r["province_code"], "province": C.PROV_NAME[r["province_code"]], "quarter": L.qs(q),
               "issue_date": x["issue_date"], "lead": int(r["lead"]), "pi_hunger": float(r["H1"]),
               "pi_price": float(r["pi_price"]), "probability": prob, "class": "HIGH" if prob >= 0.5 else "LOW",
               "observed": None if obs is None else ("HIGH" if obs == 1 else "LOW"),
               "observed_hunger_condition": None if obs is None else int(lab["hunger"].get((r["province_code"], q))),
               "observed_price_condition": None if obs is None else int(lab["price"].get((r["province_code"], q))),
               **{c: x[c] for c in ("sws_newest_q", "sws_newest_published", "h_last", "psa_newest_month",
                                    "news_latest_published", "lead_days", "A1_food", "A1_gap", "A_mom")}}
        fam = {}
        for c in U.cols("U2", True):
            f = U.FAMILY_OF.get(c, c)
            if f in FAMS:
                fam[f] = fam.get(f, 0.0) + float(r.get(f"shap_{c}", 0.0))
        for f in FAMS:
            row[f"shap_{f}"] = fam.get(f, 0.0)
        out.append(row)
    return out


def main():
    U.setup()
    K = int(json.loads((OUT / "testability_unified.json").read_text())["K"])
    S = U.stack(K)
    lab = C.labels().set_index(["province_code", "q"])
    origins = [L.qi(q) for q in json.loads((OUT / "testability_unified.json").read_text())["eligible_origins"]]
    rows = []
    for t in origins:
        rows += rows_for(S, t, [1] if t < E.LAST_ORIGIN else list(range(1, K + 1)), lab)
    R = pd.DataFrame(rows)
    P = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    chk = R.assign(q=R["quarter"].map(L.qi)).merge(P[["province_code", "q", "lead", "UNI_p"]], on=["province_code", "q", "lead"])
    assert len(chk) == len(P[P["lead"] == 1]) and np.allclose(
        chk["probability"], chk["UNI_p"], atol=1e-5), "export != evaluated predictions"
    seal = R[R["issue_date"] >= "2026-10-01"].copy()
    seal.to_csv(OUT / "sealed_prospective.csv", index=False, lineterminator="\n", float_format="%.6g")
    sha = FM.sha256(OUT / "sealed_prospective.csv")
    (OUT / "sealed_prospective.csv.sha256").write_text(sha + "\n", encoding="utf-8", newline="\n")
    served = R[(R["issue_date"] < "2026-10-01") | (R["lead"] <= 4)]
    DEST.mkdir(parents=True, exist_ok=True)
    served.to_csv(DEST / "rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    res = json.loads((OUT / "results.json").read_text())
    imp = json.loads((OUT / "improved_results.json").read_text()) if (OUT / "improved_results.json").exists() else None
    leads = {k: {x: v[x] for x in LEAD_KEYS if x in v} for k, v in res["leads"].items()}
    strict = None
    for k in sorted(res["leads"], key=int):
        if res["leads"][k]["reliable_strict"]:
            strict = int(k)
        else:
            break
    horizon = {"leads_evaluated": [int(k) for k in res["leads"]], "testable_horizon_R1": res["testable_horizon_R1"],
               "max_reliable_lead": res["max_reliable_lead"], "individually_passing_leads": res["individually_passing_leads"],
               "generated_up_to": K, "why_not_longer": WHY_NOT_LONGER, "leads": {}}
    tq = S.drop_duplicates(["t", "lead"]).set_index(["t", "lead"])["sws_newest_q"]
    for k, v in res["leads"].items():
        d = P[P["lead"] == int(k)].drop_duplicates(["t"])
        tru = sorted({int(t + int(k) - L.qi(tq[(t, int(k))])) for t in d["t"]})
        horizon["leads"][k] = {"n": v["n"], "n_quarters": v["n_quarters"], "accuracy": v["metrics"]["accuracy"],
                               "always_low_accuracy": v["baseline_accuracy"]["ALWAYS-LOW"], "reliable": v["reliable"],
                               "criteria": v["criteria"], "quarters_after_issue": int(k), "quarters_after_newest_sws": tru}
    P1 = P[P["lead"] == 1]
    b = pd.cut(P1["UNI_p"], [0, .1, .3, .5, .7, .9, 1.0], include_lowest=True)
    g = P1.groupby(b, observed=True).agg(n=("y", "size"), mean_p=("UNI_p", "mean"), observed=("y", "mean"))
    ev = {"model": "UNI-FINAL: one LightGBM across all leads (all 12 FIRI v2 families + lead + World Bank world prices, "
                   "monotone food-price terms) times the hunger-condition probability pi_H; HIGH at 0.50",
          "protocol_sha256": res["protocol_sha256"], "selection": res["selection"],
          "max_reliable_lead": res["max_reliable_lead"], "max_reliable_lead_strict": strict,
          "leads": leads, "horizon": horizon, "seal_sha256": sha, "seal_issue_date": "2026-10-01",
          "calibration_lead1": {"bins": [{"bin": str(i), "n": int(r.n), "mean_p": float(r.mean_p), "observed": float(r.observed)}
                                         for i, r in g.iterrows()], "mean_p": float(P1["UNI_p"].mean()),
                                "observed_rate": float(P1["y"].mean())},
          "serve_note": ("Served instead of the per-lead CH1-LGBM because the user's directive (2026-10-27) requires one "
                         "unified LightGBM. CH1-LGBM scored 0.914 at Lead 1 on the same 70 rows (Brier significantly "
                         "better, p = .022); UNI-FINAL 0.829. Both are reliable at Lead 1 only."),
          "post_hoc_improved": None if imp is None else {
              "status": imp["status"], "chosen": imp["UNI_IMPROVED"], "addendum_sha256": imp["addendum_sha256"],
              "accuracy_by_lead": {k: v["metrics"]["accuracy"] for k, v in imp["leads"].items()},
              "reliable_by_lead": {k: v["reliable"] for k, v in imp["leads"].items()},
              "max_reliable_lead": imp["max_reliable_lead"],
              "not_served_because": "its cut-off varies by issue date; the dashboard's approved display calls HIGH at 0.50"}}
    FM.write_json(DEST / "evaluation.json", ev)
    print("exported", len(served), "rows", served.groupby("lead").size().to_dict(), "| sealed", len(seal), sha[:8])


if __name__ == "__main__":
    main()
