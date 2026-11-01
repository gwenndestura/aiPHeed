"""Y3 diagnosis (after the gate failed; descriptive): does each issue-time indicator LEAD the hunger change, or only
co-move with it? Over 1998-2020, all four areas, pairs (latest reading at q0 -> outcome at q0+3, the Lead-2 true horizon):

  leading     corr( feature at pseudo-issue O(q0+1),          H(q0+3) - H(q0) )   available at a Lead-2 issue
  concurrent  corr( feature at O(q0+3), i.e. target quarter,  H(q0+3) - H(q0) )   NOT available at issue

with quarter-cluster bootstrap 90% CIs, plus the onset table: every LOW->HIGH crossing at horizon 3 with its issue-time
rice inflation. Writes out/diagnose.json.

    python -B diagnose.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import cov  # noqa: E402
import p2lib as P  # noqa: E402

R = P.R
OUT = Path(__file__).resolve().parent / "out"
H = 3


def ci(d: pd.DataFrame, a: str, b: str) -> list[float]:
    rng = np.random.default_rng(P.SEED)
    qs = d["q0"].unique()
    by = {q: g for q, g in d.groupby("q0")}
    v = []
    for _ in range(2000):
        s = pd.concat([by[q] for q in rng.choice(qs, len(qs))])
        v.append(s[a].corr(s[b]))
    return [round(float(np.nanquantile(v, .05)), 3), round(float(np.nanquantile(v, .95)), 3)]


def main():
    obs = R.observed()
    rows = []
    for (a, q0), v0 in obs.items():
        if (a, q0 + H) in obs and q0 + H <= R.qi("2020-Q4"):
            lead = dict(zip(cov.FEATS, cov.feats(q0 + 1)))
            conc = dict(zip(cov.FEATS, cov.feats(q0 + H + 1)))
            rows.append({"area": a, "q0": q0, "H0": v0, "H1": obs[(a, q0 + H)], "dy": obs[(a, q0 + H)] - v0,
                         "onset": int(v0 <= R.H_LINE < obs[(a, q0 + H)]), "low0": int(v0 <= R.H_LINE),
                         **{f"L_{k}": x for k, x in lead.items()}, **{f"C_{k}": x for k, x in conc.items()}})
    d = pd.DataFrame(rows)
    res = {"pairs": len(d), "quarters": int(d["q0"].nunique()), "onsets": int(d["onset"].sum()),
           "lowStarts": int(d["low0"].sum()), "features": {}}
    for f in cov.FEATS:
        g = d.dropna(subset=[f"L_{f}", f"C_{f}"])
        res["features"][f] = {"n": len(g),
                              "leading_r": round(float(g[f"L_{f}"].corr(g["dy"])), 3), "leading_CI90": ci(g, f"L_{f}", "dy"),
                              "concurrent_r": round(float(g[f"C_{f}"].corr(g["dy"])), 3), "concurrent_CI90": ci(g, f"C_{f}", "dy")}
    low = d[d["low0"] == 1]
    res["onsetTable"] = low.assign(start=low["q0"].map(R.qs))[["area", "start", "H0", "H1", "onset", "L_rice_yoy", "L_rice_d3", "L_oni_last"]] \
        .round(2).to_dict("records")
    for f in ("rice_yoy", "rice_d3", "oni_last"):
        res[f"onsetVsNoOnset_{f}"] = {"onset_mean": round(float(low[low.onset == 1][f"L_{f}"].mean()), 2),
                                      "noOnset_mean": round(float(low[low.onset == 0][f"L_{f}"].mean()), 2)}
    OUT.mkdir(exist_ok=True)
    (OUT / "diagnose.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print({k: v for k, v in res.items() if k not in ("features", "onsetTable")})
    for f, v in res["features"].items():
        print(f"{f:10s} n {v['n']} leading r {v['leading_r']:+.3f} {v['leading_CI90']}  concurrent r {v['concurrent_r']:+.3f} {v['concurrent_CI90']}")
    print(pd.DataFrame(res["onsetTable"]).to_string(index=False))


if __name__ == "__main__":
    main()
