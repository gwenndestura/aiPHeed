"""Addendum 3: score every evaluable lead (0-8) with the unchanged CH1-LGBM code on the audited inputs, then derive
the testable horizon, the maximum reliable lead (frozen consecutive rule), every individually passing lead, the
operational horizon and per-quarter results.

    python horizon.py      # out/horizon_predictions_lead{k}.csv, out/horizon_results.json
"""
from __future__ import annotations

from common import C, CH1, FM, L, OUT, np, pd, setup
from horizon_rule import select_horizon

LEADS = tuple(range(0, 9))           # testability.json: lead 9+ has no evaluable quarter


def _check():
    want = (CH1 / "runner" / "ADDENDUM_3_SHA256.txt").read_text().strip()
    assert FM.sha256(CH1 / "ADDENDUM_3_HORIZON_EXTENSION.md") == want, "Addendum 3 changed after freezing"


def per_quarter(D: pd.DataFrame) -> list[dict]:
    rows = []
    for q, g in D.groupby("q"):
        c = ((g["CH1_p"] >= .5).astype(int) == g["y"])
        rows.append({"target_quarter": L.qs(int(q)), "issue_date": g["issue_date"].iloc[0],
                     "sws_newest_q": g["sws_newest_q"].iloc[0], "true_sws_horizon": int(g["true_horizon"].iloc[0]),
                     "hunger_BL": float(g["H"].iloc[0]), "hunger_condition": int(g["hunger"].iloc[0]),
                     "pi_hunger": round(float(g["H1"].iloc[0]), 4), "high": int(g["y"].sum()), "rows": int(len(g)),
                     "correct": int(c.sum()),
                     "persist_si_correct": int(((g["PERSIST-SI_p"] >= .5).astype(int) == g["y"]).sum()),
                     "always_low_correct": int((g["y"] == 0).sum())})
    return rows


def quarter_level(D: pd.DataFrame) -> dict:
    """Separates the regional hunger condition (one value per quarter) from the provincial price condition."""
    g = D.groupby("q").first()
    hung_ok = ((g["H1"] >= .5).astype(int) == g["hunger"])
    pr_ok = ((D["CH1_price"] >= .5).astype(int) == D["price"])
    allc = D.assign(c=((D["CH1_p"] >= .5).astype(int) == D["y"])).groupby("q")["c"].all()
    return {"quarters": int(len(g)),
            "hunger_condition_correct_quarters": int(hung_ok.sum()),
            "price_condition_accuracy_rows": float(pr_ok.mean()),
            "quarters_all_five_correct": int(allc.sum()),
            "quarters_hunger_condition_false": int((g["hunger"] == 0).sum()),
            "accuracy_rows_where_hunger_condition_true": float(
                ((D["CH1_p"] >= .5).astype(int) == D["y"])[D["hunger"] == 1].mean()) if (D["hunger"] == 1).any() else None}


def blocks(D: pd.DataFrame) -> dict:
    qs = sorted(D["q"].unique())
    last = D[D["q"].isin(qs[-4:])]
    acc = lambda x, col: float(((x[col] >= .5).astype(int) == x["y"]).mean())  # noqa: E731
    h = C.bl_quarters()
    surge = [q for q in qs if (q - 1) in h.index and h[q] - h[q - 1] >= 5]
    S = D[D["q"].isin(surge)]
    return {"latest_block": {"quarters": [L.qs(int(q)) for q in qs[-4:]], "rows": int(len(last)),
                             "accuracy": acc(last, "CH1_p"), "persist_si": acc(last, "PERSIST-SI_p"),
                             "always_low": acc(last, "ALWAYS-LOW_p"), "high": int(last["y"].sum())},
            "hunger_surge_quarters": {"rule": "Balance Luzon hunger up >= 5 points on the previous quarter",
                                      "quarters": [L.qs(int(q)) for q in surge], "rows": int(len(S)),
                                      "accuracy": acc(S, "CH1_p") if len(S) else None,
                                      "persist_si": acc(S, "PERSIST-SI_p") if len(S) else None,
                                      "high": int(S["y"].sum())}}


def main():
    _check()
    setup()
    res = {"addendum3_sha256": FM.sha256(CH1 / "ADDENDUM_3_HORIZON_EXTENSION.md"), "leads": {}}
    for k in LEADS:
        D = C.run_lead(k)
        D.to_csv(OUT / f"horizon_predictions_lead{k}.csv", index=False, lineterminator="\n", float_format="%.6g")
        dec = C.decide(D)
        y = D["y"].astype(int).to_numpy()
        nb = FM.boot_diff(D, (D["CH1_p"] - y) ** 2, (D["LGBM-GOV_p"] - y) ** 2)
        lead_days = sorted({int(v) for v in D["lead_days"]})
        dec.update(superiority=C.superiority(D), per_quarter=per_quarter(D), quarter_level=quarter_level(D),
                   **blocks(D),
                   news_ablation={"acc_with": dec["metrics"]["accuracy"],
                                  "acc_without": float(((D["LGBM-GOV_p"] >= .5).astype(int) == y).mean()),
                                  "brier_diff": nb},
                   operational={"quarters_after_issue_quarter": k,
                                "target_quarter_ends_days_after_issue": lead_days,
                                "true_sws_horizon": sorted({int(v) for v in D["true_horizon"]})})
        res["leads"][k] = dec
        print(f"lead {k}: n {dec['n']} q {dec['n_quarters']} acc {dec['metrics']['accuracy']:.3f} "
              f"fail {[c for c, v in dec['criteria'].items() if not v]}", flush=True)
    fl = [k for k in LEADS if k >= 1]
    hp = FM.holm({k: res["leads"][k]["news_ablation"]["brier_diff"]["p_two"] for k in fl})
    for k in fl:
        res["leads"][k]["news_ablation"]["holm_p_leads_1_8"] = hp[k]
    res.update(select_horizon(res["leads"]))
    strict = select_horizon({k: {**d, "reliable": d["reliable_strict"]} for k, d in res["leads"].items()})
    res["max_reliable_lead_strict"] = strict["max_reliable_lead"]
    FM.write_json(OUT / "horizon_results.json", res)
    print("testable (R1):", res["testable_horizon_R1"], "max reliable:", res["max_reliable_lead"],
          "individually passing:", res["individually_passing_leads"])


if __name__ == "__main__":
    main()
