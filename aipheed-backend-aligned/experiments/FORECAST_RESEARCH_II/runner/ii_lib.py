"""FORECAST_RESEARCH_II shared helpers (PROTOCOL_FORECAST_RESEARCH_II.md). Reuses the FORECAST_RESEARCH library
(fr_lib: stack, rounds, issue schedules, pi_H, R1-R7) and its metrics; adds the monthly CPI index, the SWS sampling
error and the protocol check of this study."""
from __future__ import annotations

import functools
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
II = HERE.parent
EXP = II.parent
FR_RUNNER = EXP / "FORECAST_RESEARCH" / "runner"
sys.path.insert(0, str(FR_RUNNER))
import fr_lib as F  # noqa: E402
import metrics as M  # noqa: E402

DATA, OUT = II / "data", II / "out"
OUT.mkdir(exist_ok=True)
SEED = 2031
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
BY_NAME = {v: k for k, v in NAMES.items()}
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
FIRST_YM = 2021 * 12
CPI_INDEX = EXP / "E41_Lead2_Audit" / "data_acquired" / "cpi_index_ACP22.csv"
CPI_YOY = EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
KEY = ["t", "lead", "province_code"]


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_protocol():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert sha256(II / "PROTOCOL_FORECAST_RESEARCH_II.md") == want, "protocol changed after freezing"


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, indent=1, default=float))


# ================================================================================================ CPI
@functools.lru_cache(maxsize=1)
def index_wide() -> dict:
    """{'food': DataFrame ym x province, 'all': ...} of the PSA monthly index (2021-01..2026-09)."""
    a = pd.read_csv(CPI_INDEX)
    a = a[a["Period"].isin(MONTHS) & a["value"].notna()].copy()
    a["province_code"] = a["Geolocation"].str.strip(". ").map(BY_NAME)
    a["series"] = a["Commodity Description"].map({"0 - ALL ITEMS": "all", "01.1 - FOOD": "food"})
    a["ym"] = a["Year"].astype(int) * 12 + a["Period"].map(MONTHS)
    assert a["ym"].min() >= FIRST_YM and a["ym"].max() <= 2026 * 12 + 8
    return {s: g.pivot(index="ym", columns="province_code", values="value").sort_index()[PROVS].astype(float)
            for s, g in a.groupby("series")}


@functools.lru_cache(maxsize=1)
def yoy_published() -> pd.DataFrame:
    y = pd.read_csv(CPI_YOY, dtype={"province_code": str})
    y["ym"] = y["reference_month"].str[:4].astype(int) * 12 + y["reference_month"].str[5:7].astype(int) - 1
    return y


def m0_of(t: int) -> int:
    return (t // 4) * 12 + (t % 4) * 3 + 1


# ================================================================================================ SWS noise
def round_se(H: float, moe: float) -> float:
    p = H / 100.0
    return 100.0 * (moe / 100.0 / 1.96) * np.sqrt(p * (1 - p)) / 0.5


@functools.lru_cache(maxsize=1)
def bl_quarters() -> pd.DataFrame:
    r = F.rounds()
    r = r[r["area"] == "BL"].copy()
    r["se_r"] = [round_se(h, m) for h, m in zip(r["H"], r["moe"])]
    g = r.groupby("q").agg(H=("H", "mean"), n_rounds=("H", "size"), se_sum=("se_r", lambda s: float(np.sqrt((s ** 2).sum()))),
                           published=("published", "max"))
    g["se_q"] = g["se_sum"] / g["n_rounds"]
    return g.drop(columns="se_sum").reset_index()
