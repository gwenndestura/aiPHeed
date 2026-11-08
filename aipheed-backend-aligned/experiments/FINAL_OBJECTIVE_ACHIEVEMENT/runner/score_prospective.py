"""Score the sealed FIL-OA forecasts (out/sealed_prospective.csv, issued 2026-10-01) once SWS publishes 2026-Q4+.

Add the new SWS rounds to ../FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv (same columns, with their publication dates), then run
    python score_prospective.py
The seal hash is checked first; the scores go to out/prospective_scores.json. Nothing is refitted.
"""
from __future__ import annotations

import oa_lib as O

M = O.M

np, pd = M.np, M.pd


def main():
    p = O.OUT / "sealed_prospective.csv"
    want = (O.OUT / "sealed_prospective.csv.sha256").read_text().strip()
    assert M.sha256(p) == want, "sealed file changed"
    S = pd.read_csv(p)
    M.rounds.cache_clear()
    M.final_values.cache_clear()
    rows = []
    for r in S.itertuples():
        q = M.qi(r.target_quarter)
        y, lab = M.outcome(r.area, q), M.label_final(r.area, q)
        if y is None or lab is None:
            continue
        rows.append({"model": r.model, "area": r.area, "lead": r.lead, "target": r.target_quarter, "y": y,
                     "label": lab, "correct": int((r.p_elevated > 0.5) == bool(lab)),
                     "persistence_correct": int(r.persistence_elevated == lab),
                     "abs_err": abs(r.forecast_level - y), "persistence_abs_err": abs(r.persistence_level - y)})
    D = pd.DataFrame(rows)
    out = {"seal_sha256": want, "n_scored": len(D)}
    if len(D):
        out["by_model_lead"] = D.groupby(["model", "lead"]).agg(
            n=("y", "size"), accuracy=("correct", "mean"), persistence_accuracy=("persistence_correct", "mean"),
            mae=("abs_err", "mean"), persistence_mae=("persistence_abs_err", "mean")).reset_index().to_dict("records")
        out["rows"] = D.to_dict("records")
    M.write_json(O.OUT / "prospective_scores.json", out)
    print(out if len(D) else "no sealed target has been published yet")


if __name__ == "__main__":
    main()
