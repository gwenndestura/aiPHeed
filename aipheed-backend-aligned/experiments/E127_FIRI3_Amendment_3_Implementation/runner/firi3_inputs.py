"""FIRI3 v1.3 input builder: the E120 inputs, the E125 source refreshes (NASA POWER 2026, IBTrACS 2026-Q3 local
counts) and the Amendment 3 PAR series. One place for the data-preparation layer; firi3 itself is unchanged.

    obs, ann, provenance = build()          # v1.3 inputs
    obs12, ann, _ = build(amendment_3=False)   # the v1.2 / E125 state, for comparison
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
REPO = EXP.parent.parent
sys.path.insert(0, str(REPO / "backend"))
for p in (EXP / "E120_FIRI_Consolidated_Design" / "runner", EXP / "E125_FIRI3_Pre_Issuance" / "runner", HERE):
    sys.path.insert(0, str(p))
from app.ml.inference import firi3 as F3      # noqa: E402
import e120 as E120                           # noqa: E402
import run_e125 as R125                       # noqa: E402
import par_counts as PC                       # noqa: E402

IBTRACS_WP = EXP / "E114_Final_Run" / "data" / "raw" / "ibtracs.WP.list.v04r01.csv"
LAST_Q = 2026 * 4 + 3                                   # 2026-Q4: the builder decides coverage itself


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(amendment_3: bool = True, ibtracs: Path = IBTRACS_WP):
    L, ann = E120.load()
    obs = L.assign(source=L["feature"] + " @ " + L["unit"])
    ann = ann.assign(source=ann["feature"] + " @ " + ann["unit"] + " (" + ann["ref"] + ")")
    # E125 refreshes (unchanged): NASA POWER 2021-2026 features; IBTrACS 2026-Q3 local 100 km counts
    nasa = R125.nasa_features(R125.nasa_monthly_refreshed()).assign(source=lambda d: d["feature"] + " @ " + d["unit"])
    obs = pd.concat([obs[~obs["feature"].isin(R125.NASA_SERIES)], nasa], ignore_index=True)
    loc_new, par_new, _, _ = R125.cyclones(R125.RAW / "ibtracs.last3years.list.v04r01.csv")
    addq = 2026 * 4 + 2
    add = []
    for u in R125.PF_CENTROIDS:
        if not ((obs["feature"] == "typhoons_local_100km") & (obs["unit"] == u) & (obs["period"] == addq)).any():
            n = loc_new[(loc_new["unit"] == u) & (loc_new["period"] == addq)]
            add.append({"feature": "typhoons_local_100km", "unit": u, "period": addq, "value": float(n["count"].iloc[0]) if len(n) else 0.0,
                        "avail": F3.issue_date(addq), "status": "verified", "resolution": "province", "source": f"typhoons_local_100km @ {u} (IBTrACS refreshed 2026-10-31)"})
    obs = pd.concat([obs, pd.DataFrame(add)], ignore_index=True)
    prov = {"ibtracs_wp_sha256": sha(ibtracs), "ibtracs_last3years_sha256": sha(R125.RAW / "ibtracs.last3years.list.v04r01.csv"), "amendment_3": amendment_3}
    if amendment_3:
        pq = PC.par_quarterly(PC.load_tracks(ibtracs), F3.START_Q, LAST_Q, source=Path(ibtracs).name)
        obs = pd.concat([obs[obs["feature"] != "typhoons_PAR"], PC.as_firi3_rows(pq, lambda q: F3.issue_date(q))], ignore_index=True)
        prov["par_quarterly"] = pq
    else:                                                                       # v1.2 / E125 state: E114 series + E125 2026-Q3
        if not ((obs["feature"] == "typhoons_PAR") & (obs["period"] == addq)).any():
            n = par_new[(par_new["unit"] == "PHILIPPINES") & (par_new["period"] == addq)]
            obs = pd.concat([obs, pd.DataFrame([{"feature": "typhoons_PAR", "unit": "PHILIPPINES", "period": addq, "value": float(n["count"].iloc[0]) if len(n) else 0.0,
                                                 "avail": F3.issue_date(addq), "status": "verified", "resolution": "national",
                                                 "source": "typhoons_PAR @ PHILIPPINES (IBTrACS refreshed 2026-10-31)"}])], ignore_index=True)
    return obs, ann, prov
