"""E54 tables from the committed run outputs (no model is fitted here).

    backend/venv/Scripts/python.exe -B runner/e54_tables.py <c12 run dir name> <c3 run dir name>
      -> tables/{metrics.csv, decisions.csv, poverty_selection_by_origin.csv, province_outcome_vs_poverty.csv}

province_outcome_vs_poverty.csv is DESCRIPTIVE (not a pre-registered test): the share of HIGH outcomes per province on
the evaluation rows next to the province's poverty values, to show whether poverty even orders the provinces' outcomes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e54_lib as V  # noqa: E402

KEYS = ["n", "accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "brier"]


def main(c12: str, c3: str):
    r12 = json.loads((V.E54 / "runs" / c12 / "results.json").read_text())
    r3 = json.loads((V.E54 / "runs" / c3 / "results.json").read_text())
    blocks = {"C1 PS (E52/E53)": r12["C1_PS"], "C2 T43 S44 (E46-I7)": r12["C2_T43"]["S44"],
              "C2 T43 EXT (E46-I7)": r12["C2_T43"]["EXT"], "C3 E38 label (E38)": r3}
    met, dec = [], []
    for name, b in blocks.items():
        for a, m in b["metrics"].items():
            met.append({"comparison": name, "arm": a, **{k: m.get(k) for k in KEYS},
                        "auc": m.get("auc", m.get("roc_auc")), "role": "E54 arm" if a in V.ARMS else "baseline/comparator"})
        for a, d in b["decision"].items():
            pb = b["paired_brier_vs_R"][a]
            dec.append({"comparison": name, "arm": a, "dBrier_vs_R": pb["diff"], "ci95_low": pb["ci95"][0],
                        "ci95_high": pb["ci95"][1], **d})
    out = V.E54 / "tables"
    out.mkdir(exist_ok=True)
    pd.DataFrame(met).to_csv(out / "metrics.csv", index=False, float_format="%.6g", lineterminator="\n")
    pd.DataFrame(dec).to_csv(out / "decisions.csv", index=False, float_format="%.6g", lineterminator="\n")

    sel = json.loads((V.E54 / "runs" / c12 / "selections.json").read_text())
    rows = []
    for q, v in sel.items():
        for a in V.ARMS:
            s = v[a]
            rows.append({"target": q, "origin": v["origin"], "arm": a,
                         "food_cfg": f"m{s['food_cfg']['mult']}/alpha{s['food_cfg']['alpha']}",
                         "gap_cfg": f"m{s['gap_cfg']['mult']}/alpha{s['gap_cfg']['alpha']}",
                         "train_rows": s["train_rows"], "train_rows_poverty_known": s["train_rows_poverty_known"],
                         "food_coef": json.dumps(s["food_coef"]), "gap_coef": json.dumps(s["gap_coef"])})
    pd.DataFrame(rows).to_csv(out / "poverty_selection_by_origin.csv", index=False, lineterminator="\n")

    pov, sub = V.pov_values(), V.sub_values()
    ps = pd.read_csv(V.E54 / "runs" / c12 / "rows_ps.csv", dtype={"province_code": str})
    t43 = pd.read_csv(V.E54 / "runs" / c12 / "rows_t43.csv", dtype={"province_code": str})
    e38 = pd.read_csv(V.E54 / "runs" / c3 / "predictions.csv", dtype={"province_code": str})
    e38 = e38[e38["arm"] == "R"]
    prov = []
    for p in V.PROVS:
        prov.append({"province": V.NAMES[p], "POV_sae2021_mean": round(pov[p], 2), "SUB_2021": sub[(p, 2021)],
                     "SUB_2023": sub[(p, 2023)],
                     "PS_HIGH_share": round(ps[ps["province_code"] == p]["y"].mean(), 3),
                     "T43_S44_HIGH_share": round(t43[t43["province_code"] == p]["y"].mean(), 3),
                     "E38_label_HIGH_share": round(e38[e38["province_code"] == p]["y"].mean(), 3)})
    P = pd.DataFrame(prov)
    P.to_csv(out / "province_outcome_vs_poverty.csv", index=False, lineterminator="\n")
    sp = {c: float(P["POV_sae2021_mean"].corr(P[c], method="spearman"))
          for c in ("PS_HIGH_share", "T43_S44_HIGH_share", "E38_label_HIGH_share")}
    print(P.to_string(index=False))
    print("Spearman(POV, HIGH share), 5 provinces:", {k: round(v, 2) for k, v in sp.items()})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
