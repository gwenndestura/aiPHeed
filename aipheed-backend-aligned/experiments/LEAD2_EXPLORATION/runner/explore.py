"""LEAD2_EXPLORATION (EXPLORATION_PLAN.md): EXPLORATORY search over HIGH/LOW decision rules on the closed 2023-2026
Lead-2 rows, with a nested leave-one-quarter-out estimate. Read-only on every input; writes out/.

    python -B explore.py
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOTD = HERE.parent
EXP = ROOTD.parent
OUT = ROOTD / "out"
sys.path.insert(0, str(EXP / "LEAD2_RELIABILITY_RESEARCH" / "common"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import p2lib as P  # noqa: E402

ROWS = EXP / "LEAD2_POST_SWS_PRICE" / "out" / "eval_rows.csv"
F1 = [round(0.20 + 0.05 * i, 2) for i in range(9)]
F2 = [(a, round(0.30 + 0.05 * j, 2)) for a in (0.5, 0.6, 0.7, 0.8, 0.9) for j in range(7)]
FAMILIES = {"F1": F1, "F2": F2}


def plan_ok():
    b = (ROOTD / "EXPLORATION_PLAN.md").read_bytes()
    i = b.rfind(b"\nPLAN-SHA256:") + 1
    if hashlib.sha256(b[:i]).hexdigest() != b[i:].split(b":", 1)[1].strip().decode():
        raise SystemExit("EXPLORATION_PLAN.md changed after it was hashed")


def part_sets(g: pd.DataFrame) -> dict:
    return {"S0": (g["pi_H4"], g["P0_price"], "served"), "S1": (g["pi_H4_post"], g["P0_price"], "post"),
            "S2": (g["pi_H4_post"], g["P0_price_post"], "post"),
            "S3": (g["pi_H4_post"], (g["P0_price"] + g["P0_price_post"]) / 2, "post")}


def decide(fam: str, prm, h: np.ndarray, p: np.ndarray) -> np.ndarray:
    return ((h * p) >= prm).astype(int) if fam == "F1" else ((h >= prm[0]) & (p >= prm[1])).astype(int)


def bal(y, d):
    tp, fn = ((d == 1) & (y == 1)).sum(), ((d == 0) & (y == 1)).sum()
    tn, fp = ((d == 0) & (y == 0)).sum(), ((d == 1) & (y == 0)).sum()
    r = tp / (tp + fn) if tp + fn else 0.0
    s = tn / (tn + fp) if tn + fp else 0.0
    pr = tp / (tp + fp) if tp + fp else 0.0
    return (r + s) / 2, pr


def choose(fam, h, p, y):
    """Plan section 3: best balanced accuracy, then precision, then the grid order (smaller c / a, then smaller b)."""
    best, key = None, None
    for prm in FAMILIES[fam]:
        b, pr = bal(y, decide(fam, prm, h, p))
        k = (round(b, 12), round(pr, 12))
        if key is None or k > key:
            best, key = prm, k
    return best


def rules(g: pd.DataFrame, dcol: str, pcol: str, base: str) -> dict:
    """Frozen R1-R7: classification rules on the decisions (0/1), R5 on the product probability."""
    h = g.assign(**{"PERSIST-SI_p": g["PERSIST-SI_p" if base == "served" else "PERSIST_post"],
                    "CLIM_p": g["CLIM_p" if base == "served" else "CLIM_post"], "ALWAYS-LOW_p": 0.0})
    od, op = P.official_rules(h, dcol), P.official_rules(h, pcol)
    rr = {k.split()[0]: {"pass": v["pass"], "value": v["value"]} for k, v in od["rules"].items() if not k.startswith("R5")}
    rr.update({k.split()[0]: {"pass": v["pass"], "value": v["value"]} for k, v in op["rules"].items() if k.startswith("R5")})
    y, d = h["y"].to_numpy(int), h[dcol].to_numpy(int)
    tp, fp = int(((d == 1) & (y == 1)).sum()), int(((d == 1) & (y == 0)).sum())
    fn, tn = int(((d == 0) & (y == 1)).sum()), int(((d == 0) & (y == 0)).sum())
    b, pr = bal(y, d)
    return {"rules": dict(sorted(rr.items())), "passedR2toR7": sum(v["pass"] for k, v in rr.items() if k != "R1"),
            "failed": [k for k, v in sorted(rr.items()) if not v["pass"]], "cm": f"{tp}/{fp}/{fn}/{tn}",
            "accuracy": (tp + tn) / len(y), "balanced": b, "precision": pr, "recall": tp / (tp + fn) if tp + fn else 0.0,
            "brier": float(np.mean((h[pcol] - y) ** 2))}


def main():
    plan_ok()
    OUT.mkdir(exist_ok=True)
    g = pd.read_csv(ROWS, dtype={"province_code": str})
    y = g["y"].to_numpy(int)
    qs = g["q"].to_numpy(int)
    res = {"label": "EXPLORATORY: closed 2023-2026 rows; not evidence", "planSha256": hashlib.sha256(
        (ROOTD / "EXPLORATION_PLAN.md").read_bytes()).hexdigest(), "combos": {}}
    for (sid, (h, p, base)), fam in itertools.product(part_sets(g).items(), FAMILIES):
        h, p = h.to_numpy(float), p.to_numpy(float)
        prob = h * p
        # nested leave-one-quarter-out
        oos, picks = np.zeros(len(y), int), {}
        for u in np.unique(qs):
            tr = qs != u
            prm = choose(fam, h[tr], p[tr], y[tr])
            picks[P.R.qs(int(u))] = prm
            oos[~tr] = decide(fam, prm, h[~tr], p[~tr])
        full = choose(fam, h, p, y)
        gg = g.assign(_prob=prob, _oos=oos, _ins=decide(fam, full, h, p))
        key = f"{sid}x{fam}"
        res["combos"][key] = {"nested": {**rules(gg, "_oos", "_prob", base), "picksByHeldOutQuarter": picks},
                              "inSampleOptimistic": {"gridPoint": full, **rules(gg, "_ins", "_prob", base)}}
        n, i = res["combos"][key]["nested"], res["combos"][key]["inSampleOptimistic"]
        print(f"{key:7s} nested: pass {n['passedR2toR7']}/6 fails {n['failed']} CM {n['cm']} acc {n['accuracy']:.3f} "
              f"bal {n['balanced']:.3f} P {n['precision']:.3f} R {n['recall']:.3f} | in-sample {i['gridPoint']}: "
              f"pass {i['passedR2toR7']}/6 fails {i['failed']} bal {i['balanced']:.3f} R {i['recall']:.3f}", flush=True)
    # reference: the registered M0 under D0 (product >= 0.50), in-sample
    ref = rules(g.assign(_prob=g["pi_H4_post"] * g["P0_price"], _d=((g["pi_H4_post"] * g["P0_price"]) >= .5).astype(int)),
                "_d", "_prob", "post")
    res["reference_M0_D0"] = ref
    print(f"reference M0 D0 (in-sample): pass {ref['passedR2toR7']}/6 fails {ref['failed']} CM {ref['cm']}")
    # selection (plan section 4)
    rank = sorted(res["combos"], key=lambda k: (-res["combos"][k]["nested"]["passedR2toR7"],
                                                -res["combos"][k]["nested"]["balanced"], res["combos"][k]["nested"]["brier"]))
    top = rank[0]
    sel = [top]
    for k in rank[1:]:
        if k.split("x")[0] != top.split("x")[0] and \
                res["combos"][k]["nested"]["passedR2toR7"] >= res["combos"][top]["nested"]["passedR2toR7"]:
            sel.append(k)
            break
    improves = res["combos"][top]["nested"]["passedR2toR7"] > ref["passedR2toR7"]
    res["ranking"] = rank
    res["selected"] = [{"combo": k, "gridPoint": res["combos"][k]["inSampleOptimistic"]["gridPoint"],
                        "nestedPassedR2toR7": res["combos"][k]["nested"]["passedR2toR7"]} for k in sel]
    res["improvesOnM0D0AfterCrossValidation"] = bool(improves)
    print("ranking", rank)
    print("SELECTED", json.dumps(res["selected"]), "improves on M0/D0 after CV:", improves)
    (OUT / "exploration.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
