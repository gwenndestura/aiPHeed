"""Baseline record: served P0H4, single-model S3, the structural price prior and the reference baselines on the
FINAL_ARCHITECTURE evaluation rows (recomputed from out/predictions.csv), plus effective sample sizes.

    python baseline.py      # out/baseline_record.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import metrics as M

HERE = Path(__file__).resolve().parent
FR = HERE.parent
EXP = FR.parent
D = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
MODELS = {"P0H4 (served)": "P0H4_p3", "S3 single LightGBM": "S3_p", "STRUCT price prior x pi_H": "P5H0_p",
          "Persistence (same information)": "PERSIST-SI_p", "Climatology": "CLIM_p", "Always LOW": "ALWAYS-LOW_p"}


def main():
    out = {"rows_by_lead": {}, "models": {}, "price_component": {}, "n_eff": {}}
    for k, g in D.groupby("lead"):
        if k > 4:
            continue
        out["rows_by_lead"][int(k)] = {"n": len(g), "quarters": int(g["q"].nunique()), "high": int(g["y"].sum())}
        out["n_eff"][int(k)] = M.n_eff(g["q"], g["y"])
        for name, col in MODELS.items():
            if col not in g:
                continue
            m = M.cls(g["y"], g[col])
            m["acc_ci90"] = M.acc_ci(g["q"], g["y"], g[col])
            out["models"].setdefault(name, {})[int(k)] = m
        for name, col in {"P0 price (UNI)": "P0_price", "STRUCT price": "P5_price", "S3/C": "C_p"}.items():
            out["price_component"].setdefault(name, {})[int(k)] = M.cls(g["price"], g[col])
        out["hunger_component_pi_H4"] = out.get("hunger_component_pi_H4", {})
        out["hunger_component_pi_H4"][int(k)] = M.cls(g["hunger"], g["pi_H4"])
    (FR / "out" / "baseline_record.json").write_text(json.dumps(out, indent=1))
    for name, r in out["models"].items():
        print(f"{name:32s}", " | ".join(f"L{k} acc {v['accuracy']:.3f} bal {v['balanced_accuracy']:.3f} "
                                        f"R {v['recall']:.2f} Br {v['brier']:.3f} AUC {v['auc']:.2f}" for k, v in r.items()))
    print("price component (target = price condition)")
    for name, r in out["price_component"].items():
        print(f"{name:32s}", " | ".join(f"L{k} acc {v['accuracy']:.3f} bal {v['balanced_accuracy']:.3f} "
                                        f"Br {v['brier']:.3f} AUC {v['auc']:.2f}" for k, v in r.items()))
    print("hunger component pi_H4 (target = BL > 11.3)")
    print(" | ".join(f"L{k} acc {v['accuracy']:.3f} R {v['recall']:.2f} Br {v['brier']:.3f}" for k, v in out["hunger_component_pi_H4"].items()))
    print("rows", out["rows_by_lead"])
    print("n_eff", {k: (round(v["icc"], 2), round(v["n_eff"], 1), v["high_quarters"]) for k, v in out["n_eff"].items()})


if __name__ == "__main__":
    main()
