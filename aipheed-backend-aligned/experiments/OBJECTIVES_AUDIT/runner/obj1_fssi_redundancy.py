"""Objective 1: is the FSSI anomaly (z_N1R) related to the target, and is it redundant with C-E2's other inputs?
Read only (Lead-1 rows of the C-E2 table where z_N1R exists and the label is known).

    python obj1_fssi_redundancy.py   # -> ../out/obj1_fssi_redundancy.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
import warnings
from pathlib import Path

from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

N, V, H = CE.N, CE.V, CE.H


def main():
    warnings.simplefilter("ignore")
    CE._init()
    T = N._G["T"]
    T = T[(T["area"] == "BL") & (T["lead"] == 1)].copy()
    lab = V.area_labels(H.load())
    lb = lab[lab["area"] == "BL"].set_index("q")
    T["y"], T["H"] = T["q"].map(lb["y"]), T["q"].map(lb["H"])
    x = T[T["z_N1R"].notna() & T["y"].notna()]
    r = spearmanr(x["z_N1R"], x["H"])
    cols = [c for c in CE.CE if c not in ("z_N1R", "lead")]
    cor = {c: float(spearmanr(x["z_N1R"], x[c], nan_policy="omit")[0]) for c in cols if x[c].notna().sum() > 5
           and x[c].nunique() > 1}
    res = {"origins_total": int(T["t"].nunique()), "origins_with_anomaly": int(T["z_N1R"].notna().sum()),
           "labelled_quarters_with_anomaly": int(len(x)), "span": [H.qs(int(x["q"].min())), H.qs(int(x["q"].max()))],
           "spearman_vs_hunger_next": {"rho": float(r[0]), "p": float(r[1])},
           "spearman_with_other_inputs_top5": dict(sorted(cor.items(), key=lambda kv: -abs(kv[1]))[:5])}
    (HERE / "out" / "obj1_fssi_redundancy.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
