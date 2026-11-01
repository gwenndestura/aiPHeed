"""Y7 (diagnostic, not a forecast): which of R1-R7 can Lead 2 pass if one term were known perfectly? Oracle values are
the observed hunger or price condition plugged in. Official 65 Lead-2 rows, rules unchanged. Writes out/headroom.json.

    python -B headroom.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import p2lib as P  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
PRICE = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P0c"]


def main():
    d = P.load_p0h4()
    g = d[d["lead"] == 2].copy()
    cols = {}
    for p in PRICE:
        g[f"oracleH x {p}"] = g["hunger"] * g[f"{p}_price"]
        cols[f"oracleH x {p}"] = "perfect hunger, real price term"
    g["H4 x oracleP"] = g["pi_H4"] * g["price"]
    cols["H4 x oracleP"] = "served hunger term, perfect price"
    g["H3b x oracleP"] = g["pi_H3b"] * g["price"] if "pi_H3b" in g and g["pi_H3b"].notna().all() else float("nan")
    cols["H3b x oracleP"] = "sample-b hunger term, perfect price"
    res = {}
    for c, why in cols.items():
        if g[c].isna().any():
            continue
        o = P.official_rules(g, c)
        m = P.full_metrics(g, c)
        res[c] = {"what": why, "failed": o["failed"], "metrics": m}
        print(f"{c:16s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision'] or 0:.2f} R {m['recall']:.2f} "
              f"Brier {m['brier']:.4f} CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} fails {o['failed']}")
    OUT.mkdir(exist_ok=True)
    (OUT / "headroom.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
