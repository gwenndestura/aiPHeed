"""Export the Chapter I risk engine (CH1-LGBM) for the backend: backend/data/ch1_engine/.

rows.csv     one row per province and quarter: the walk-forward Lead-1 forecast for every quarter it can be issued
             (the same model and rule as the evaluation), and the Lead 2-4 forecasts issued 2026-10-01 (the seal),
             with pi_hunger, pi_price, probability, class, observed T43c label (if any) and signed SHAP per family
evaluation.json   per-lead metrics, baselines, verdicts, news ablation and the seal hash, copied from out/

Nothing is refitted differently from run_ch1.py; the Lead-1 rows for labelled quarters equal predictions_lead1.csv.

    python export_ch1.py
"""
from __future__ import annotations

import json

import ch1_lib as C

FM, B, E, L, np, pd = C.FM, C.B, C.E, C.L, C.np, C.pd
DEST = C.EXP.parents[1] / "backend" / "data" / "ch1_engine"


def _rows(k: int, origins) -> list[dict]:
    X = C.build_X(k)
    lab = C.labels().set_index(["province_code", "q"])
    out = []
    for t in origins:
        tr = B.price_rows(X, t, k)
        te = X[X["t"] == t]
        if not B.eligible(tr) or not len(te) or te["H1"].isna().any():
            continue
        pp, mdl, cfg = C._price(tr, te, C.COLS, k)
        sv = mdl.shap(te)
        for i, r in enumerate(te.itertuples()):
            q = t + k
            obs = lab["y"].get((r.province_code, q))
            row = {"province_code": r.province_code, "province": C.PROV_NAME[r.province_code], "quarter": L.qs(q),
                   "issue_date": r.issue_date, "lead": k, "pi_hunger": float(r.H1), "pi_price": float(pp[i]),
                   "probability": float(r.H1 * pp[i]), "class": "HIGH" if r.H1 * pp[i] >= 0.5 else "LOW",
                   "observed": None if obs is None else ("HIGH" if obs == 1 else "LOW"),
                   "observed_hunger_condition": None if obs is None else int(lab["hunger"].get((r.province_code, q))),
                   "observed_price_condition": None if obs is None else int(lab["price"].get((r.province_code, q))),
                   "sws_newest_q": r.sws_newest_q, "sws_newest_published": r.sws_newest_published,
                   "h_last": r.h_last, "psa_newest_month": r.psa_newest_month,
                   "news_latest_published": r.news_latest_published, "lead_days": r.lead_days,
                   "A1_food": r.A1_food, "A1_gap": r.A1_gap, "A_mom": r.A_mom}
            fam = {}
            if sv is not None:
                for j, c in enumerate(C.COLS):
                    fam[C.FAMILY_OF[c]] = fam.get(C.FAMILY_OF[c], 0.0) + float(sv[i, j])
            for f in ("A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"):
                row[f"shap_{f}"] = fam.get(f, 0.0)
            out.append(row)
    return out


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    first, last = E.FIRST_ORIGIN, E.LAST_ORIGIN
    rows = _rows(1, range(first, last + 1))
    for k in (2, 3, 4):
        rows += _rows(k, [last])
    R = pd.DataFrame(rows)
    # the Lead-1 rows of labelled quarters must equal the evaluated predictions
    P = pd.read_csv(C.OUT / "predictions_lead1.csv", dtype={"province_code": str})
    chk = R[R["lead"] == 1].assign(q=lambda d: d["quarter"].map(L.qi)).merge(P[["province_code", "q", "CH1_p"]],
                                                                             on=["province_code", "q"])
    assert len(chk) == len(P) and np.allclose(chk["probability"], chk["CH1_p"], atol=1e-5), "export != evaluation"
    R.to_csv(DEST / "rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    res = json.loads((C.OUT / "results.json").read_text())
    plac = json.loads((C.OUT / "results_placebo.json").read_text()) if (C.OUT / "results_placebo.json").exists() else None
    ev = {"protocol_sha256": res["protocol_sha256"], "max_reliable_lead": res["max_reliable_lead"],
          "max_reliable_lead_strict": res["max_reliable_lead_strict"],
          "leads": {k: {x: v[x] for x in ("n", "n_quarters", "quarters", "high_share", "metrics", "accuracy_ci90",
                                          "baseline_accuracy", "baseline_balanced_accuracy", "criteria", "reliable",
                                          "reliable_strict", "loqo_min", "acc_thirds", "onsets", "onset_recall")}
                    for k, v in res["leads"].items()},
          "superiority": res["superiority"], "news_ablation": res["news_ablation"], "news_placebo": plac,
          "never_scored_rows_2025Q2_Q3": res["never_scored_rows_2025Q2_Q3"],
          "shap_family_share_price_model": res["shap_family_share_price_model"],
          "seal_sha256": (C.OUT / "sealed_prospective.csv.sha256").read_text().strip(),
          "calibration_lead1": calibration(P)}
    FM.write_json(DEST / "evaluation.json", ev)
    print("exported", len(R), "rows;", R.groupby("lead").size().to_dict())


def calibration(P: pd.DataFrame) -> dict:
    b = pd.cut(P["CH1_p"], [0, .1, .3, .5, .7, .9, 1.0], include_lowest=True)
    g = P.groupby(b, observed=True).agg(n=("y", "size"), mean_p=("CH1_p", "mean"), observed=("y", "mean"))
    return {"bins": [{"bin": str(i), "n": int(r.n), "mean_p": float(r.mean_p), "observed": float(r.observed)}
                     for i, r in g.iterrows()], "mean_p": float(P["CH1_p"].mean()), "observed_rate": float(P["y"].mean())}


if __name__ == "__main__":
    main()
