"""Y14 post hoc, descriptive (after run.py; no model selection): does the domain that carries the served FIRI v2's
2021+ accuracy (climate and production, AUC 0.95 against TFI-2) show the same relation with observed hunger on
independent years? AUC of each analog domain score at O(t) against TFI-2 (BL hunger > 11.3 at t+2), on 1999-2020
targets and on 2021+ targets, with quarter-bootstrap 90% CIs. Reads out/dev_rows.csv inputs via run.frame().
Writes out/domain_replication.json.

    python -B domain_replication.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

import run as Y  # noqa: E402

R = Y.R


def auc_ci(y, x):
    y, x = np.asarray(y, int), np.asarray(x, float)
    rng = np.random.default_rng(Y.SEED)
    v = []
    for _ in range(2000):
        i = rng.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(i):
            v.append(roc_auc_score(y[i], x[i]))
    return [round(float(np.quantile(v, .05)), 3), round(float(np.quantile(v, .95)), 3)]


def main():
    d = Y.frame()
    res = {}
    for lab, lo, hi in (("1999-2020 (independent)", "1999-Q1", "2020-Q4"), ("2021-2026 (FIRI test period)", "2021-Q1", "2026-Q3")):
        g = d[(d.index + 2 >= R.qi(lo)) & (d.index + 2 <= R.qi(hi)) & d["y"].notna()]
        out = {}
        for c in ("dom_A", "dom_C", "dom_E", "dom_H", "F1"):
            h = g[[c, "y"]].dropna()
            if h["y"].nunique() == 2 and len(h) >= 8:
                out[c] = {"n": len(h), "lowQuarters": int((h["y"] == 0).sum()), "auc": round(float(roc_auc_score(h["y"], h[c])), 3),
                          "CI90": auc_ci(h["y"], h[c])}
        res[lab] = out
    p = Path(__file__).resolve().parents[1] / "out" / "domain_replication.json"
    p.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
