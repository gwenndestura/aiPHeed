"""Y9 (post hoc, descriptive; no candidate): the two halves of the Lead-2 target on independent years together.
Joint regional analogue of T43c for 2002-2020: BL hunger > 11.3 (Phase 1 X2 rows, Lead 2, pooled fit) AND the Region
IV-A price condition (Y8 rows). Forecast = RW hunger probability x PERS_PROB price probability (the best validated
term on each side), plus one-side oracles. Scores the whole period and every 13-quarter window (the size of the official
Lead-2 test) against the classification parts of R2, R3, R4 and R6. Writes out/joint.json.

    python -B joint.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import p2lib as P  # noqa: E402

R = P.R
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
W = 13


def main():
    h = pd.read_csv(P.RES / "out" / "x2_rows.csv")
    h = h[(h["lead"] == 2) & (h["fit"] == "pooled") & (h["area"] == "BL")][["target", "y", "RW", "t"]] \
        .rename(columns={"y": "yh"})
    p = pd.read_csv(P.RES / "y8_price_condition" / "out" / "y8_dev_rows.csv")[["target", "y", "PERS_PROB", "pers_bin"]] \
        .rename(columns={"y": "yp"})
    d = h.merge(p, on="target").sort_values("target").reset_index(drop=True)
    d["y"] = d["yh"] * d["yp"]
    obs = R.observed()
    # same-information persistence (PERSIST-SI analogue): newest hunger reading above the line AND newest price condition
    d["persist_si"] = [float(max(R.known("BL", R.issue(int(t))).items())[1] > R.H_LINE) * pb
                       for t, pb in zip(d["t"], d["pers_bin"])]
    d["F_main"] = d["RW"] * d["PERS_PROB"]
    d["F_oracleH"] = d["yh"] * d["PERS_PROB"]
    d["F_oracleP"] = d["RW"] * d["yp"]
    res = {"rows": len(d), "period": f"{d['target'].min()}..{d['target'].max()}", "prevalence": float(d["y"].mean())}
    for c in ("F_main", "F_oracleH", "F_oracleP", "persist_si"):
        res[c] = R.metrics(d["y"], d[c])
    win = {}
    for c in ("F_main", "F_oracleH", "F_oracleP"):
        ok = {"R2": [], "R3": [], "R4": [], "R6": [], "R2R3R6": [], "two_class": 0}
        for i in range(len(d) - W + 1):
            w = d.iloc[i:i + W]
            if w["y"].nunique() < 2:
                continue
            m = R.metrics(w["y"], w[c])
            ok["two_class"] += 1
            r2, r3 = m["accuracy"] >= .75, m["balanced"] >= .70
            r6 = (m["precision"] or 0) >= .6 and (m["recall"] or 0) >= .6
            al = float((w["y"] == 0).mean())
            ps = float(((w["persist_si"] >= .5).astype(int) == w["y"]).mean())
            r4 = m["accuracy"] > al and m["accuracy"] > ps
            for k, v in (("R2", r2), ("R3", r3), ("R4", r4), ("R6", r6), ("R2R3R6", r2 and r3 and r6)):
                ok[k].append(v)
        win[c] = {"windows": ok["two_class"], **{k: round(float(np.mean(v)), 3) for k, v in ok.items() if k != "two_class"}}
    res["windows13"] = win
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "joint.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    d.to_csv(OUT / "joint_rows.csv", index=False, lineterminator="\n", float_format="%.5f")
    print({k: res[k] for k in ("rows", "period", "prevalence")})
    for c in ("F_main", "F_oracleH", "F_oracleP", "persist_si"):
        m = res[c]
        print(f"{c:10s} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} "
              f"AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f} CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']}")
    for c, v in win.items():
        print("13-quarter windows", c, v)


if __name__ == "__main__":
    main()
