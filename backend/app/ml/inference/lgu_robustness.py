"""E73 (Objective 3): how stable each LGU's within-province priority is under reasonable alternative vulnerability
weightings (E73 WS3). Static: depends only on data/inputs/lgu_vulnerability.csv, not on the quarter or the model.

For every LGU: the priority third (top / middle / bottom within its province) under the approved 0.6 poverty + 0.4
density (min-max within province), and how many of the seven E73 alternatives give the same third."""
from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd

VULN = Path("data/inputs/lgu_vulnerability.csv")
ALTERNATIVES = {"0.5/0.5": (0.5, "minmax", "density"), "0.7/0.3": (0.7, "minmax", "density"),
                "0.8/0.2": (0.8, "minmax", "density"), "poverty only": (1.0, "minmax", "density"),
                "density only": (0.0, "minmax", "density"), "rank 0.6/0.4": (0.6, "rank", "density"),
                "log-density 0.6/0.4": (0.6, "minmax", "log_density")}
THIRD = {0: "bottom third", 1: "middle third", 2: "top third"}


def _mm(s):
    return (s - s.min()) / (s.max() - s.min())


def _score(g, wp, norm="minmax", dens="density"):
    if norm == "rank":
        p, d = g["poverty_value_used"].rank(pct=True), g[dens].rank(pct=True)
    else:
        p, d = _mm(g["poverty_value_used"]), _mm(g[dens])
    return wp * p + (1 - wp) * d


def _third(s):
    return pd.qcut(s.rank(method="first"), 3, labels=False)


@functools.lru_cache(maxsize=1)
def table() -> dict[str, dict]:
    v = pd.read_csv(VULN, dtype={"lgu_code": str})
    v["lgu_code"] = v["lgu_code"].str.zfill(9)
    v["density"] = v["population_2024"] / v["land_area_km2"]
    v["log_density"] = np.log(v["density"])
    out = {}
    for _, g in v.groupby("province"):
        base = _third(_score(g, 0.6))
        alts = {k: _third(_score(g, *a)) for k, a in ALTERNATIVES.items()}
        for i in g.index:
            same = sum(int(alts[k][i] == base[i]) for k in ALTERNATIVES)
            out[g.at[i, "lgu_code"]] = {"third": THIRD[int(base[i])], "same": same, "of": len(ALTERNATIVES)}
    return out


def sentence(lgu_code: str) -> str | None:
    r = table().get(str(lgu_code).zfill(9))
    if r is None:
        return None
    return (f"Priority: {r['third']} of its province; the same third under {r['same']} of {r['of']} alternative "
            "poverty/density weightings.")
