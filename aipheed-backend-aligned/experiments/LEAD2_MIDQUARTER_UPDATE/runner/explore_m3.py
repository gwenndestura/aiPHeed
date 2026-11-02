"""EXPLORATION_PLAN_M3.md: nested leave-one-quarter-out search over HIGH/LOW rules for the M3 parts (EXPLORATORY).
Reuses LEAD2_EXPLORATION/runner/explore.py (grids, choice rule, frozen R1-R7 scoring) read-only. Writes out/ only.

    python -B explore_m3.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOTD = HERE.parent
EXP = ROOTD.parent
_spec = importlib.util.spec_from_file_location("explore_lib", EXP / "LEAD2_EXPLORATION" / "runner" / "explore.py")
X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(X)
np, pd, P = X.np, X.pd, X.P


def plan_ok():
    b = (ROOTD / "EXPLORATION_PLAN_M3.md").read_bytes()
    i = b.rfind(b"\nPLAN-SHA256:") + 1
    if hashlib.sha256(b[:i]).hexdigest() != b[i:].split(b":", 1)[1].strip().decode():
        raise SystemExit("EXPLORATION_PLAN_M3.md changed after it was hashed")


def main():
    plan_ok()
    g = pd.read_csv(ROOTD / "out" / "rows.csv", dtype={"province_code": str})
    g = g.assign(target=g["q"].map(P.R.qs), PERSIST_post=g["PERSIST_m3"], CLIM_post=g["CLIM_m3"])
    h, p, y, qs = (g["pi_H4_m3"].to_numpy(float), g["P0_price_m3"].to_numpy(float), g["y"].to_numpy(int),
                   g["q"].to_numpy(int))
    prob = h * p
    res = {"label": "EXPLORATORY (closed 2023-2026 rows)", "planSha256": hashlib.sha256(
        (ROOTD / "EXPLORATION_PLAN_M3.md").read_bytes()).hexdigest(), "families": {}}
    for fam in X.FAMILIES:
        oos, picks = np.zeros(len(y), int), {}
        for u in np.unique(qs):
            tr = qs != u
            prm = X.choose(fam, h[tr], p[tr], y[tr])
            picks[P.R.qs(int(u))] = prm
            oos[~tr] = X.decide(fam, prm, h[~tr], p[~tr])
        full = X.choose(fam, h, p, y)
        gg = g.assign(_prob=prob, _oos=oos, _ins=X.decide(fam, full, h, p))
        res["families"][fam] = {"nested": {**X.rules(gg, "_oos", "_prob", "post"), "picksByHeldOutQuarter": picks},
                                "inSampleOptimistic": {"gridPoint": full, **X.rules(gg, "_ins", "_prob", "post")}}
        n, i = res["families"][fam]["nested"], res["families"][fam]["inSampleOptimistic"]
        print(f"M3x{fam} nested: pass {n['passedR2toR7']}/6 fails {n['failed']} CM {n['cm']} acc {n['accuracy']:.3f} "
              f"bal {n['balanced']:.3f} P {n['precision']:.3f} R {n['recall']:.3f} | in-sample {i['gridPoint']}: pass "
              f"{i['passedR2toR7']}/6 fails {i['failed']} CM {i['cm']} P {i['precision']:.3f} R {i['recall']:.3f}", flush=True)
    ref = X.rules(g.assign(_prob=prob, _d=(prob >= .5).astype(int)), "_d", "_prob", "post")
    res["reference_M3_product_050"] = ref
    rank = sorted(res["families"], key=lambda k: (-res["families"][k]["nested"]["passedR2toR7"],
                                                  -res["families"][k]["nested"]["balanced"], res["families"][k]["nested"]["brier"]))
    top = rank[0]
    res["selected"] = {"family": top, "gridPoint": res["families"][top]["inSampleOptimistic"]["gridPoint"],
                       "nestedPassedR2toR7": res["families"][top]["nested"]["passedR2toR7"]}
    res["improvesAfterCrossValidation"] = res["selected"]["nestedPassedR2toR7"] > ref["passedR2toR7"]
    print(f"reference M3 h x p >= 0.50 (in-sample): pass {ref['passedR2toR7']}/6 fails {ref['failed']} CM {ref['cm']}")
    print("SELECTED", json.dumps(res["selected"]), "improves after CV:", res["improvesAfterCrossValidation"])
    (ROOTD / "out" / "exploration_m3.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
