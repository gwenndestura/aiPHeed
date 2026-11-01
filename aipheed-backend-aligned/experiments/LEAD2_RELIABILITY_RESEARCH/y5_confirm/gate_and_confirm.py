"""Y5 (EXPERIMENT_PLAN_PHASE2.md sections 4-5). Step 1 applies the frozen gate to the Y2/Y3 development rows (2005-2020)
and records the decision. Step 2 scores the candidates on the official 65 Lead-2 (and 70 Lead-1) P0H4 rows, with the
candidate hunger term replacing pi_H4, times P0 (primary) and P4 (secondary), R1-R7 unchanged.
Writes out/gate.json, out/confirm.json, out/confirm_rows.csv.

    python -B gate_and_confirm.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import pandas as pd  # noqa: E402

import hmodels as H  # noqa: E402
import p2lib as P  # noqa: E402

R = P.R
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
RES = HERE.parent
CANDS = {"KAL": "Y2", "H3B": "Y3a", "LOG": "Y3b", "RDG": "Y3c"}
FN = {"KAL": H.kalman, "H3B": lambda a, t, k, fa: H.h3b(t, k), "LOG": H.logit, "RDG": H.ridge}


def dev_block(g: pd.DataFrame, c: str) -> dict:
    g = g[g[c].notna()]
    return {"cand": R.metrics(g["y"], g[c]), "RW": R.metrics(g["y"], g["RW"]), "vsRW": R.brier_vs(g, c, "RW")}


def gate() -> dict:
    d = pd.read_csv(RES / "y2_state_space" / "out" / "y2_dev_rows.csv").merge(
        pd.read_csv(RES / "y3_leading_indicators" / "out" / "y3_dev_rows.csv")[["lead", "area", "fit", "t", "q", "H3B", "LOG", "RDG"]],
        on=["lead", "area", "fit", "t", "q"], how="inner")
    out = {}
    for k in (1, 2):
        g = d[d["lead"] == k]
        for c in CANDS:
            all_ = g[g["fit"] == "pooled"] if c != "H3B" else g[(g["fit"] == "pooled") & (g["area"] == "BL")]
            blp = g[(g["fit"] == "pooled") & (g["area"] == "BL")]
            blh = g[g["fit"] == "heldout"] if c != "H3B" else blp
            b = {"natural": dev_block(all_, c), "BL_pooled": dev_block(blp, c), "BL_heldout": dev_block(blh, c)}
            if k == 2:
                n, h = b["natural"], b["BL_heldout"]
                b["gate"] = {"G1": n["vsRW"]["diff"] < 0 and n["vsRW"]["p_one_sided"] < 0.10,
                             "G2": h["cand"]["brier"] < h["RW"]["brier"],
                             "G3": (h["cand"]["balanced"] or 0) > (h["RW"]["balanced"] or 0)}
                b["passesGate"] = all(b["gate"].values())
            out[f"lead{k}_{c}"] = b
    passed = [c for c in CANDS if out[f"lead2_{c}"]["passesGate"]]
    confirm = min(passed, key=lambda c: out[f"lead2_{c}"]["BL_pooled"]["cand"]["brier"]) if passed else None
    return {"blocks": out, "passedGate": passed, "confirmatoryCandidate": confirm}


def confirm(gres: dict) -> tuple[dict, pd.DataFrame]:
    d = P.load_p0h4()
    cache = {}
    for t, k in d[["t", "lead"]].drop_duplicates().itertuples(index=False):
        for c in CANDS:
            cache[(c, int(t), int(k))] = FN[c]("BL", int(t), int(k), tuple(R.AREAS))
    res = {}
    for c in CANDS:
        d[f"pi_{c}"] = [cache[(c, int(t), int(k))] for t, k in zip(d["t"], d["lead"])]
        for price in ("P0_price", "P4_price"):
            col = f"{c}x{price[:2]}"
            d[col] = d[f"pi_{c}"] * d[price]
            for k in (1, 2):
                g = d[d["lead"] == k]
                if g[col].isna().any():
                    res[f"lead{k}_{col}"] = {"undefinedRows": int(g[col].isna().sum())}
                    continue
                o = P.official_rules(g, col)
                res[f"lead{k}_{col}"] = {"metrics": P.full_metrics(g, col), "failed": o["failed"],
                                         "passesAll": o["passesAll"], "rules": o["rules"],
                                         "designEffect": P.design_effect(g, col)}
    for k in (1, 2):
        g = d[d["lead"] == k]
        for col in (P.RV.P, "P4H4_p3"):
            o = P.official_rules(g, col)
            res[f"lead{k}_{col}(reference)"] = {"metrics": P.full_metrics(g, col), "failed": o["failed"],
                                                "passesAll": o["passesAll"]}
    res["confirmatoryCandidate"] = gres["confirmatoryCandidate"]
    res["status"] = ("confirmatory (single gate-passing candidate x P0); 2021-2026 already used by ~20 earlier configurations, "
                     "a pass requires prospective sealed quarters" if gres["confirmatoryCandidate"] else
                     "descriptive only: no candidate passed the frozen gate")
    return res, d


def main():
    P.plan2_ok()
    import l2_lib as X
    X.U.setup()
    OUT.mkdir(exist_ok=True)
    g = gate()
    (OUT / "gate.json").write_text(json.dumps(g, indent=1, default=str), encoding="utf-8")
    for key, b in g["blocks"].items():
        n, bp, bh = b["natural"], b["BL_pooled"], b["BL_heldout"]
        f = lambda m: f"acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f}"  # noqa: E731
        print(f"{key}: natural n {n['cand']['n']} {f(n['cand'])} | RW {f(n['RW'])} | diff {n['vsRW']}")
        print(f"      BL pooled {f(bp['cand'])} | RW {f(bp['RW'])};  BL heldout {f(bh['cand'])} | RW {f(bh['RW'])}"
              + (f"  GATE {b['gate']} -> {b['passesGate']}" if "gate" in b else ""))
    print("passed gate:", g["passedGate"], "confirmatory:", g["confirmatoryCandidate"])
    res, d = confirm(g)
    (OUT / "confirm.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    keep = ["t", "lead", "province_code", "q", "y", "hunger", "price", "pi_H4", "P0_price", "P4_price", P.RV.P] + \
           [c for c in d.columns if c.startswith("pi_") and c != "pi_H4" and c[3:] in CANDS] + \
           [c for c in d.columns if "xP" in c]
    d[[c for c in keep if c in d.columns]].to_csv(OUT / "confirm_rows.csv", index=False, lineterminator="\n", float_format="%.5f")
    for key, v in res.items():
        if isinstance(v, dict) and "metrics" in v:
            m = v["metrics"]
            print(f"{key}: acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision'] or 0:.2f} R {m['recall']:.2f} "
                  f"spec {m['specificity']:.2f} F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} "
                  f"CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} fails {v['failed']}")
        elif isinstance(v, dict):
            print(key, v)
    print(res["status"])


if __name__ == "__main__":
    main()
