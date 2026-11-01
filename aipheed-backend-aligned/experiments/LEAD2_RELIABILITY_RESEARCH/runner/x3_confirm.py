"""X3 (EXPERIMENT_PLAN section 4): the X2-selected hunger model scored once on 2021-2026. X3a: BL hunger condition alone
on the 17 FIRI Lead-2 targets. X3b: P0H4 with the hunger term replaced, R1-R7 as frozen. Reproduces the baselines first.
Writes out/x3_results.json, out/x3a_rows.csv, out/x3b_rows.csv.

    python x3_confirm.py
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import importlib.util  # noqa: E402
import json  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rlib as R  # noqa: E402

sys.path.insert(0, str(R.EXP / "FIRI_LEAD2_FEASIBILITY" / "runner"))
sys.path.insert(0, str(R.EXP / "LEAD2_OPTIMIZATION" / "runner"))
import score_firi_l2 as F  # noqa: E402
import l2_lib as X  # noqa: E402
import a3  # noqa: E402

_spec = importlib.util.spec_from_file_location("p0h4_review", R.EXP / "P0H4_LEAD12_REVIEW" / "runner" / "reproduce.py")
RV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RV)
ALL = tuple(R.AREAS)


def cm_of(s: dict) -> str:
    return f"{s['TP']}/{s['FP']}/{s['FN']}/{s['TN']}"


def main():
    R.frozen_ok()
    x2 = json.loads((R.OUT / "x2_results.json").read_text())
    model = x2["selection"]["chosen"]
    X.U.setup()

    # ---- reproduction of the baselines
    d = RV.load()
    base = {f"lead{k}": RV.scores(d[d["lead"] == k]) for k in (1, 2)}
    assert cm_of(base["lead1"]) == "11/5/6/48" and cm_of(base["lead2"]) == "6/4/11/44", base
    fr = pd.read_csv(R.EXP / "FIRI_LEAD2_FEASIBILITY" / "out" / "firi_l2_rows.csv")
    fs = R.metrics(fr["y"], fr["F2"])
    assert cm_of(fs) == "11/0/1/5", fs

    # ---- X3a: BL hunger condition, 17 Lead-2 targets
    fr["q"] = fr["target"].map(R.qi)
    fr["t"] = fr["q"] - 2
    new, rw, h4 = [], [], []
    for t in fr["t"]:
        f = R.forecast("BL", int(t), 2, ALL)
        new.append(f[model])
        rw.append(f["RW"])
        h4.append(a3.h4(int(t), 2))
    fr["NEW"], fr["RW"], fr["H4"] = new, rw, h4
    srv = d[d["lead"] == 2].drop_duplicates("t").set_index("t")["pi_H4"]
    ov = fr[fr["t"].isin(srv.index)]
    h4_check = float((ov["H4"] - ov["t"].map(srv)).abs().max())
    assert h4_check < 1e-5, f"a3.h4 does not reproduce the served pi_H4 ({h4_check})"
    fr["ALWAYS-HIGH"], fr["ALWAYS-LOW"] = 1.0, 0.0
    x3a = {}
    for col in ("NEW", "RW", "H4", "F2", "H1"):
        g = fr[fr[col].notna()].copy()                        # H4 is undefined before enough 2021+ errors exist
        g["F2"] = g[col]
        x3a[col] = {"metrics": R.metrics(g["y"], g[col]), "rules": F.rules(g)["rules"],
                    "rowsScored": f"{len(g)}/{len(fr)}"}
    x3a["NEW_vs_H4_brier"] = R.brier_vs(fr[fr["H4"].notna()], "NEW", "H4")
    x3a["NEW_vs_RW_brier"] = R.brier_vs(fr, "NEW", "RW")

    # ---- X3b: P0H4 with the hunger term replaced
    cache = {}
    for t, k in d[["t", "lead"]].drop_duplicates().itertuples(index=False):
        cache[(int(t), int(k))] = R.forecast("BL", int(t), int(k), ALL)[model]
    d["pi_new"] = [cache[(int(t), int(k))] for t, k in zip(d["t"], d["lead"])]
    d["P_new"] = d["pi_new"] * d["P0_price"]
    x3b = {}
    for k in (1, 2):
        g = d[d["lead"] == k].copy()
        g[RV.P] = g["P_new"]
        s = RV.scores(g)
        s["rules"] = RV.rules(g)
        s["passesAll"] = all(v["pass"] for v in s["rules"].values())
        x3b[f"lead{k}"] = s
    x3b["recommended"] = x3b["lead1"]["passesAll"] and x3b["lead2"]["passesAll"]

    res = {"model": model, "x2GatePassed": x2["selection"]["passesGate"],
           "reproduction": {"P0H4": {k: cm_of(v) for k, v in base.items()}, "FIRI": cm_of(fs),
                            "a3.h4_vs_served_pi_H4_maxAbs": h4_check},
           "x3a": x3a, "x3b": x3b,
           "status": "development evidence; uses pre-2021 SWS data (needs a scope revision to adopt)"}
    (R.OUT / "x3_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    fr.to_csv(R.OUT / "x3a_rows.csv", index=False, lineterminator="\n", float_format="%.4f")
    d[["t", "lead", "province_code", "q", "y", "pi_H4", "pi_new", "P0_price", RV.P, "P_new"]].to_csv(
        R.OUT / "x3b_rows.csv", index=False, lineterminator="\n", float_format="%.5f")

    print("model", model, "| X2 gate passed:", res["x2GatePassed"], "| reproduction", res["reproduction"])
    print(fr[["target", "issue_date", "y", "H_obs", "NEW", "RW", "H4", "H1", "F2"]].round(3).to_string(index=False))
    for col in ("NEW", "RW", "H4", "F2", "H1"):
        m = x3a[col]["metrics"]
        print(f"X3a {col:4s} rows {x3a[col]['rowsScored']} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision'] or 0:.2f} R {m['recall']:.2f} "
              f"spec {m['specificity']:.2f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} CM {cm_of(m)} | fails "
              f"{[r.split()[0] for r, v in x3a[col]['rules'].items() if not v['pass']]}")
    print("X3a NEW vs H4", x3a["NEW_vs_H4_brier"], "NEW vs RW", x3a["NEW_vs_RW_brier"])
    for k in (1, 2):
        s = x3b[f"lead{k}"]
        print(f"X3b L{k}: acc {s['accuracy']:.3f} bal {s['balanced']:.3f} P {s['precision'] or 0:.2f} R {s['recall']:.2f} "
              f"spec {s['specificity']:.2f} F1 {s['f1']:.3f} AUC {s['auc']:.3f} Brier {s['brier']:.4f} CM {cm_of(s)} | "
              f"fails {[r.split()[0] for r, v in s['rules'].items() if not v['pass']]}")
        print(f"   baseline P0H4 L{k}: acc {base[f'lead{k}']['accuracy']:.3f} Brier {base[f'lead{k}']['brier']:.4f}")
    print("recommended:", x3b["recommended"])


if __name__ == "__main__":
    main()
