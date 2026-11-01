"""Y15 Investigation A: the climate-domain warm-up in the served FIRI v2 (Lead 2), audited on a read-only copy of
backend/data/thesis/firi2_history.csv. This is a sensitivity audit of the served index on its 17 evaluation targets.
It does not select or propose a model.

Steps:
  1. Reproduce the served regional FIRI (mean of the 5 provinces' stored FIRI) and the 17-row confusion matrix
     (11/0/1/5), and recompute FIRI from the stored domain scores and weights (parity check).
  2. Trace the climate domain at every target: which C indicators were scored, and why the others were not
     ("insufficient_history" = fewer than 8 earlier origins; "missing" = no input).
  3. Recompute the index under missing-data treatments that never turn "unavailable" into a score:
       T1 domain abstention: C counts only if >= 3 of its 4 indicators are scored, else C is unavailable
       T2 consistent coverage: C uses only the indicators scored at every one of the 17 targets
       T3 equal domain weights (no walk-forward evidence weights), stored domains
       T4 = T1 + equal weights
       T5 climate domain excluded at every target (stored weights renormalised)
       T6 DESCRIPTIVE ONLY: as T1, but the index is computed over the remaining 3 domains (breaks the >= 4 rule) to
          measure what the warm-up zero did to the three earliest LOW targets
     FIRI keeps its own rule: it needs >= 4 available domains. Where that fails, FIRI abstains: no forecast for that
     target. Rows with a forecast are scored with the unchanged rules; abstentions are counted, never imputed.

Writes out/warmup_audit.json and out/warmup_rows.csv.

    python -B warmup_audit.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
Y15 = HERE.parent
EXP = Y15.parents[1]
ROOT = EXP.parents[1]
sys.path.insert(0, str(EXP / "FIRI_LEAD2_FEASIBILITY" / "runner"))
import score_firi_l2 as F  # noqa: E402

DOMS = ["A", "V", "C", "E", "N", "H"]
CIND = ["C1", "C2", "C3", "C4"]


def index(dom: dict, w: dict | None, min_dom: int = 4) -> float | None:
    av = {d: v for d, v in dom.items() if v is not None and not (isinstance(v, float) and np.isnan(v))}
    if len(av) < min_dom:
        return None
    ww = {d: (w or {}).get(d, 1.0) if w else 1.0 for d in av}
    tot = sum(ww.values())
    return float(sum(ww[d] * av[d] for d in av) / tot)


def main():
    h = pd.read_csv(ROOT / "backend" / "data" / "thesis" / "firi2_history.csv")
    h = h[h["kind"] == "backtest"].copy()
    fr = pd.read_csv(EXP / "FIRI_LEAD2_FEASIBILITY" / "out" / "firi_l2_rows.csv")
    tg = set(fr["target"])
    h = h[h["target"].isin(tg)]
    ind = [json.loads(s) for s in h["indicators_json"]]
    wts = [json.loads(s) if isinstance(s, str) else None for s in h["weights_json"]]
    scored = lambda i, k: i[k]["score"] is not None  # noqa: E731
    always = [k for k in CIND if all(scored(i, k) for i in ind)]
    rows = []
    for (_, r), i, w in zip(h.iterrows(), ind, wts):
        dom = {d: (None if pd.isna(r[f"dom_{d}"]) else float(r[f"dom_{d}"])) for d in DOMS}
        cs = [i[k]["score"] for k in CIND if scored(i, k)]
        c_t1 = dom["C"] if len(cs) >= 3 else None
        c_t2 = float(np.mean([i[k]["score"] for k in always])) if always else None
        rec = {"target": r["target"], "province": r["province_code"], "stored": r["FIRI"],
               "T0r": index(dom, w), "T1": index({**dom, "C": c_t1}, w), "T2": index({**dom, "C": c_t2}, w),
               "T3": index(dom, None), "T4": index({**dom, "C": c_t1}, None),
               "T5": index({**dom, "C": None}, {k: v for k, v in (w or {}).items() if k != "C"} or None),
               # T6 DESCRIPTIVE ONLY (breaks FIRI's >= 4-domain rule): C treated as unavailable where fewer than 3 of
               # its indicators are scored, index over the remaining domains; measures what the warm-up zero did
               "T6": index({**dom, "C": c_t1}, {k: v for k, v in (w or {}).items() if k != "C" or c_t1 is not None} or None, 3),
               "C_scored": len(cs), "C_value": dom["C"],
               "C_status": {k: i[k]["status"] for k in CIND}}
        rows.append(rec)
    d = pd.DataFrame(rows)
    parity = float((d["T0r"] - d["stored"]).abs().max())
    reg = d.groupby("target").agg(**{c: (c, lambda s: float(s.mean()) if s.notna().all() else np.nan)
                                     for c in ["stored", "T0r", "T1", "T2", "T3", "T4", "T5", "T6"]},
                                  C_scored_min=("C_scored", "min"), C_value=("C_value", "mean"))
    g = fr.merge(reg, left_on="target", right_index=True)
    assert np.allclose(g["stored"], g["F2"], atol=1e-4), "stored regional FIRI differs from the scored F2 column"
    g["q"] = g["target"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    g["ALWAYS-HIGH"], g["ALWAYS-LOW"] = 1.0, 0.0
    res = {"parity_maxAbs_storedVsRecomputed": parity, "C_indicators_scored_at_all_17_targets": always,
           "trace": g[["target", "y", "H_obs", "stored", "C_value", "C_scored_min"]].round(3).to_dict("records"),
           "C_status_by_target": d.groupby("target")["C_status"].first().to_dict()}
    for c in ["stored", "T1", "T2", "T3", "T4", "T5", "T6"]:
        k = g[g[c].notna()].copy()
        k["F2"] = k[c]
        r = F.rules(k)["rules"]
        yh = (k[c] >= .5).astype(int)
        cm = [int(((yh == a) & (k["y"] == b)).sum()) for a, b in ((1, 1), (1, 0), (0, 1), (0, 0))]
        res[c] = {"rowsWithForecast": len(k), "abstained": int(g[c].isna().sum()),
                  "abstainedTargets": g.loc[g[c].isna(), "target"].tolist(),
                  "cm_TP_FP_FN_TN": cm, "accuracy": float((yh == k["y"]).mean()),
                  "rules": {kk.split()[0]: v["pass"] for kk, v in r.items()},
                  "failed": [kk.split()[0] for kk, v in r.items() if not v["pass"]]}
    out = Y15 / "out"
    out.mkdir(exist_ok=True)
    (out / "warmup_audit.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    g.drop(columns=["ALWAYS-HIGH", "ALWAYS-LOW"]).to_csv(out / "warmup_rows.csv", index=False, lineterminator="\n", float_format="%.4f")
    print("parity", parity, "| C indicators scored at all 17 targets:", always)
    print(g[["target", "y", "H_obs", "stored", "T1", "T2", "T3", "T4", "T5", "T6", "C_value", "C_scored_min"]].round(3).to_string(index=False))
    for c in ["stored", "T1", "T2", "T3", "T4", "T5", "T6"]:
        v = res[c]
        print(f"{c:6s} rows {v['rowsWithForecast']:2d} abstained {v['abstained']} {v['abstainedTargets']} CM {v['cm_TP_FP_FN_TN']} "
              f"acc {v['accuracy']:.3f} fails {v['failed']}")


if __name__ == "__main__":
    main()
