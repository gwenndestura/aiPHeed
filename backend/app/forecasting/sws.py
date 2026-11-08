"""
The forecasting target: SWS involuntary hunger (% of families) for the 4 SWS areas, 2021+, with each round's binomial
sampling SE derived from its published 95 % margin and the frozen primary tolerance 1.645 x SE
(docs/aipheed/PROTOCOL_LOCK.md T1-T4). Faithful port of E131 runner/e131_x1.py rounds() / quarter_table() / asof();
tests/unit/test_forecasting_core.py checks equality with that implementation.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from app.forecasting.as_of import as_of
from app.forecasting.evidence import AREAS
from app.forecasting.validation import ValidationError, validate_sws_rounds

DATA = Path(__file__).resolve().parents[2] / "data" / "forecasting"
SWS_ROUNDS = DATA / "sws_area_rounds.csv"
Z90 = float(stats.norm.ppf(0.95))          # 1.6448536...: the frozen tolerance multiplier
DEFAULT_MOE = 6.0                           # used when a round publishes no area margin (protocol T1)


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def load_rounds(path: Path = SWS_ROUNDS) -> pd.DataFrame:
    raw = pd.read_csv(path)
    problems = validate_sws_rounds(raw)
    if problems:
        raise ValidationError(problems)
    r = raw[~raw["commissioned"].astype(str).str.lower().eq("true")].copy()
    r["published"] = pd.to_datetime(r["published"]).dt.date
    rows = []
    for x in r.itertuples():
        for a in AREAS:
            moe = x.area_moe_bl if a == "balance_luzon" else x.area_moe_other
            moe = DEFAULT_MOE if moe != moe else float(moe)
            n = 0.9604 / (moe / 100) ** 2
            p = getattr(x, a) / 100
            rows.append({"quarter": x.quarter, "published": x.published, "area": a, "value": getattr(x, a),
                         "se": 100 * np.sqrt(p * (1 - p) / n), "se_pub": moe / 1.96})
    return pd.DataFrame(rows)


def quarter_table(rr: pd.DataFrame) -> pd.DataFrame:
    g = rr.groupby(["area", "quarter"])
    q = g.agg(y=("value", "mean"), published=("published", "max"), k=("value", "size")).reset_index()
    q["se"] = g["se"].apply(lambda s: np.sqrt((s ** 2).sum()) / len(s)).values
    q["se_pub"] = g["se_pub"].apply(lambda s: np.sqrt((s ** 2).sum()) / len(s)).values
    q["tol"] = Z90 * q["se"]
    q["qi"] = q["quarter"].map(qi)
    return q


def known_at(rr: pd.DataFrame, issue: date) -> pd.DataFrame:
    """Quarter values as known on the issue date: only rounds published strictly before it (via as_of)."""
    k = as_of(rr, issue)
    if k.empty:
        return k.assign(y=[], se=[], qi=[])
    return quarter_table(k)


def within_tolerance(forecast, y, se) -> np.ndarray:
    return np.abs(np.asarray(forecast, float) - np.asarray(y, float)) <= Z90 * np.asarray(se, float)
