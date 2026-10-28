"""PROTOCOL_LEAD2_COMBINATION_SCREEN: dependence between the hunger and price conditions, and the Frechet bounds of
P0H4-U's two parts, on development data only (targets <= 2024-Q4).

    python comb_screen.py       # ../out/comb_screen.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F, M = T.F, T.M
SEED, DRAWS = 2031, 2000


def phi(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else float("nan")


def main():
    proto = T.LT / "PROTOCOL_LEAD2_COMBINATION_SCREEN.md"
    assert T.sha256(proto) == (T.HERE / "COMBINATION_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv", dtype={"province_code": str})
    r = F.rounds()
    bl = set(r.loc[r["area"] == "BL", "q"])
    L = lab[(lab["q"] <= F.DEV_LAST) & (lab["q"] >= 2021 * 4) & lab["q"].isin(bl)].drop_duplicates(["province_code", "q"])
    assert L["q"].max() <= F.DEV_LAST
    rng = np.random.default_rng(SEED)
    qs = np.array(sorted(L["q"].unique()))
    boot = []
    for _ in range(DRAWS):
        B = pd.concat([L[L["q"] == q] for q in rng.choice(qs, len(qs))])
        v = phi(B["hunger"], B["price"])
        if not np.isnan(v):
            boot.append(v)
    res = {"protocol_sha256": T.sha256(proto), "labels": int(len(L)), "quarters": int(len(qs)),
           "table": {f"hunger{h}_price{p}": int(((L["hunger"] == h) & (L["price"] == p)).sum()) for h in (0, 1) for p in (0, 1)},
           "phi": phi(L["hunger"], L["price"]), "phi_ci90": [float(x) for x in np.percentile(boot, [5, 95])]}
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    g = C[(C["lead"] == 2) & (C["q"] <= F.DEV_LAST)]
    assert g["q"].max() <= F.DEV_LAST
    comb = {"product": g["pi_H_AB"] * g["C0_price"], "upper_min": np.minimum(g["pi_H_AB"], g["C0_price"]),
            "lower_bound": np.maximum(0, g["pi_H_AB"] + g["C0_price"] - 1)}
    res["lead2_dev"] = {k: {"rows": int(len(g)), "auc": M.auc(g["y"], v), "brier": float(np.mean((v - g["y"]) ** 2)),
                            "recall_at_0.5": float(((v >= .5) & (g["y"] == 1)).sum() / g["y"].sum()),
                            "precision_at_0.5": float(((v >= .5) & (g["y"] == 1)).sum() / max(1, (v >= .5).sum()))}
                        for k, v in comb.items()}
    d = res["lead2_dev"]
    res["build_candidate"] = bool(res["phi"] > 0 and res["phi_ci90"][0] > 0
                                  and d["product"]["brier"] - d["upper_min"]["brier"] >= 0.005
                                  and d["upper_min"]["auc"] >= d["product"]["auc"])
    (T.OUT / "comb_screen.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
