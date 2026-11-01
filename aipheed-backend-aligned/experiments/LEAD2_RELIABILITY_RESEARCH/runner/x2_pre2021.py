"""X2 (EXPERIMENT_PLAN section 3): hunger forecasting at the Lead-1/2 true horizons on 2005-2020 targets, four SWS areas,
pooled and area-held-out fits; then the frozen selection rule. No 2021+ outcome is used. Writes out/x2_results.json,
out/x2_rows.csv.

    python x2_pre2021.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import rlib as R

T_FIRST, T_LAST = R.qi("2005-Q1"), R.qi("2020-Q4")
MODELS = ("RW", "CLIM", "MR", "MRF")


def build() -> pd.DataFrame:
    obs = R.observed()
    rows = []
    for k in (1, 2):
        for area in R.AREAS:
            fits = {"pooled": tuple(R.AREAS)}
            if area == "BL":
                fits["heldout"] = ("NCR", "VIS", "MIN")
            for tgt in range(T_FIRST, T_LAST + 1):
                if (area, tgt) not in obs:
                    continue
                t = tgt - k
                prev = obs.get((area, tgt - 1))
                for fit, fa in fits.items():
                    f = R.forecast(area, t, k, fa)
                    if f is None:
                        continue
                    assert R.issue(t) > R.rounds()[(R.rounds()["area"] == area) &
                                                   (R.rounds()["q"] == f["q_last"])]["published"].min()
                    rows.append({"lead": k, "area": area, "fit": fit, "t": t, "target": R.qs(tgt), "level": obs[(area, tgt)],
                                 "y": int(obs[(area, tgt)] > R.H_LINE),
                                 "onset": bool(prev is not None and prev <= R.H_LINE < obs[(area, tgt)]),
                                 **{m: f[m] for m in MODELS}, "RW_mu": f["RW_mu"], "MR_mu": f["MR_mu"], "MRF_mu": f["MRF_mu"],
                                 "h": f["h"], "pairs": f["pairs"], "beta": f["beta"], "gamma": f["gamma"],
                                 "MRF_fallback": f["MRF_fallback"]})
    d = pd.DataFrame(rows)
    assert d["target"].max() <= "2020-Q4", "a 2021+ outcome entered X2"
    return d


def block(g: pd.DataFrame) -> dict:
    out = {}
    for m in MODELS:
        mu = g[f"{m}_mu"] if f"{m}_mu" in g else None
        out[m] = R.metrics(g["y"], g[m], mu, g["level"] if mu is not None else None, g["onset"])
    for m in ("MR", "MRF", "CLIM"):
        out[f"{m}_vs_RW_brier"] = R.brier_vs(g, m, "RW")
    return out


def main():
    R.frozen_ok()
    d = build()
    res = {"rows": {f"lead{k}": {"pooledFit_allAreas": int(((d.lead == k) & (d.fit == "pooled")).sum()),
                                 "BL_heldout": int(((d.lead == k) & (d.fit == "heldout")).sum())} for k in (1, 2)},
           "MRF_fallback_share": float(d["MRF_fallback"].mean())}
    for k in (1, 2):
        g = d[d["lead"] == k]
        res[f"lead{k}"] = {"allAreas_pooledFit": block(g[g.fit == "pooled"]),
                           "BL_pooledFit": block(g[(g.fit == "pooled") & (g.area == "BL")]),
                           "BL_areaHeldOut": block(g[g.fit == "heldout"]),
                           "byArea_pooledFit": {a: {m: R.metrics(gg["y"], gg[m])["brier"] for m in MODELS}
                                                for a, gg in g[g.fit == "pooled"].groupby("area")},
                           "trueHorizons": g["h"].value_counts().sort_index().to_dict()}
    l2 = res["lead2"]
    a = l2["allAreas_pooledFit"]
    chosen = "MR" if a["MR"]["brier"] <= a["MRF"]["brier"] else "MRF"
    gate = {"beatsRW_allAreas_p<0.10": a[f"{chosen}_vs_RW_brier"]["diff"] < 0 and a[f"{chosen}_vs_RW_brier"]["p_one_sided"] < .10,
            "beatsRW_BL_areaHeldOut": l2["BL_areaHeldOut"][chosen]["brier"] < l2["BL_areaHeldOut"]["RW"]["brier"]}
    res["selection"] = {"chosen": chosen, "gate": gate, "passesGate": all(gate.values())}
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / "x2_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    d.to_csv(R.OUT / "x2_rows.csv", index=False, lineterminator="\n", float_format="%.5f")
    print(json.dumps(res["rows"]), "MRF fallback share", round(res["MRF_fallback_share"], 3))
    for k in (1, 2):
        for blk in ("allAreas_pooledFit", "BL_pooledFit", "BL_areaHeldOut"):
            b = res[f"lead{k}"][blk]
            print(f"L{k} {blk}")
            for m in MODELS:
                s = b[m]
                print(f"   {m:5s} n {s['n']} pos {s['pos']} acc {s['accuracy']:.3f} bal {s['balanced'] or 0:.3f} "
                      f"P {s['precision'] or 0:.2f} R {s['recall'] or 0:.2f} spec {s['specificity'] or 0:.2f} "
                      f"AUC {s['auc'] or 0:.3f} Brier {s['brier']:.4f} MAE {s.get('mae', float('nan')):.2f} onsets {s['onsets']}")
            print("   vs RW:", {m: b[f"{m}_vs_RW_brier"] for m in ("MR", "MRF", "CLIM")})
        print(f"L{k} horizons", res[f"lead{k}"]["trueHorizons"], "by area", res[f"lead{k}"]["byArea_pooledFit"])
    print("selection:", res["selection"])


if __name__ == "__main__":
    main()
