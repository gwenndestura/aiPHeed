"""E43 label diagnostics (no model is fitted): candidate SWS + PSA food-price targets (Chapter I section 1.7).

    backend/venv/Scripts/python.exe -B runner/e43_label_diagnostics.py  -> runs/labels/{label_diagnostics.json, labels.csv}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E43 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E43.parent / "E41_Lead2_Audit" / "runner"))
import e41_lib as L  # noqa: E402

np, pd = L.np, L.pd
OUT = E43 / "runs" / "labels"


def candidates(d: L.Data) -> pd.DataFrame:
    th = L.e40_spec()
    F, HL = L.quarter_F(d, "food"), L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
    q = F.merge(HL, on=["province_code", "q"])
    hq = L.h_quarters(d).set_index("q")["H"]
    q["H"] = q["q"].map(hq)
    q = q.dropna(subset=["H"]).copy()
    q["sws_hi"] = q["H"] > th["H"]
    q["cpi_hi"] = q["F"] > q["province_code"].map(th["food"])
    q["gap_hi"] = (q["F"] - q["HL"]) > q["province_code"].map(th["gap"])
    q["price_e40"] = q["cpi_hi"] | q["gap_hi"]
    q["fpp4"] = q["F"] > 4.0
    q["L3_E40_both"] = (q["sws_hi"] & q["price_e40"]).astype(int)
    q["L4_H113_and_F4"] = (q["sws_hi"] & q["fpp4"]).astype(int)
    q["L5_ordinal"] = q["sws_hi"].astype(int) + q["price_e40"].astype(int)          # 0 LOW, 1 WATCH, 2 HIGH
    q["Hunger_only"] = q["sws_hi"].astype(int)
    e40 = L.e40_labels(d).set_index(["province_code", "q"])["y"]
    q["L2_E40_sustain2"] = [e40.get((p, qq)) for p, qq in zip(q["province_code"], q["q"])]
    return q


def describe(q: pd.DataFrame, col: str, first_eval_origin: int) -> dict:
    g = q.dropna(subset=[col])
    y = (g[col] >= (2 if col == "L5_ordinal" else 1)).astype(int)
    byq = g.assign(y=y).groupby("q")["y"].agg(["mean", "nunique"])
    high_q = sorted(L.qs(int(x)) for x in byq.index[byq["mean"] > 0])
    pre = [x for x in byq.index[byq["mean"] > 0] if x + 2 <= first_eval_origin]
    return {"rows": int(len(g)), "HIGH_share": float(y.mean()),
            "by_year": {str(k): round(float(v), 3) for k, v in g.assign(y=y).groupby(g["q"] // 4)["y"].mean().items()},
            "by_province": {L.NAMES[p]: round(float(v), 3) for p, v in g.assign(y=y).groupby("province_code")["y"].mean().items()},
            "quarters_with_any_HIGH": high_q, "quarters_provinces_differ": int((byq["nunique"] > 1).sum()),
            "quarters": int(len(byq)), "HIGH_quarters_usable_for_training_before_2024": len(pre)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = L.load()
    q = candidates(d)
    res = {c: describe(q, c, L.qi("2024-Q1")) for c in
           ("L2_E40_sustain2", "L3_E40_both", "L4_H113_and_F4", "L5_ordinal", "Hunger_only")}
    res["note"] = ("L5_ordinal reported as HIGH (both signals); WATCH = one signal. All use SWS approved rounds "
                   "(regional) and PSA provincial food CPI. Quarters without an approved SWS round have no label.")
    res["L5_WATCH_share"] = float((q["L5_ordinal"] == 1).mean())
    q.to_csv(OUT / "labels.csv", index=False)
    (OUT / "label_diagnostics.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
