"""
Geography with explicit status. All 142 CALABARZON LGUs and the 5 provinces are always present. The forecast is
measured/forecast only at SWS-area level (Balance Luzon contains CALABARZON), so every province and LGU carries the
Balance Luzon value as a BROADER_AREA_REFERENCE, never as its own measurement. No provincial or LGU hunger value is
invented: the provincial and LGU estimate fields are null with status AWAITING_GROUND_TRUTH until a provincial
measurement (e.g. CBMS FIES) exists.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.forecasting.evidence import CALABARZON_SWS_AREA, EvidenceStatus
from app.forecasting.validation import ValidationError, validate_lgus

LGUS = Path(__file__).resolve().parents[2] / "data" / "reference" / "popcen2024_calabarzon_municipal.csv"
# PSGC prefix of the LGU code -> (province code used by the served dashboard, data/ch1_engine/rows.csv; name)
PROVINCES = {"0421": ("PH040100000", "Cavite"), "0434": ("PH040200000", "Laguna"), "0456": ("PH040300000", "Quezon"),
             "0458": ("PH040400000", "Rizal"), "0410": ("PH040500000", "Batangas")}


def lgus() -> pd.DataFrame:
    d = pd.read_csv(LGUS, dtype={"lgu_code": str})
    problems = validate_lgus(d)
    if problems:
        raise ValidationError(problems)
    return d


def geography_view(records: list[dict], lead: int) -> dict:
    """Province and LGU rows for one lead: the Balance Luzon value as a labelled broader-area reference."""
    bl = [r for r in records if r["area"] == CALABARZON_SWS_AREA and r["lead"] == lead]
    if len(bl) != 1:
        raise ValueError(f"expected one Balance Luzon record for lead {lead}, found {len(bl)}")
    bl = bl[0]
    ref = {"value": bl["score"], "lo80": bl["lo80"], "hi80": bl["hi80"], "area": CALABARZON_SWS_AREA,
           "status": EvidenceStatus.BROADER_AREA_REFERENCE.value}
    prov = [{"province_code": code, "province": n, "broader_area_reference": ref, "provincial_estimate": None,
             "provincial_estimate_status": EvidenceStatus.AWAITING_GROUND_TRUTH.value} for code, n in PROVINCES.values()]
    l = lgus()
    lg = [{"lgu_code": r.lgu_code, "name": r.name_source, "province": r.province, "broader_area_reference": ref,
           "lgu_estimate": None, "lgu_estimate_status": EvidenceStatus.AWAITING_GROUND_TRUTH.value}
          for r in l.itertuples()]
    return {"target_quarter": bl["target_quarter"], "lead": lead, "provinces": prov, "lgus": lg,
            "note": "SWS measures hunger for Balance Luzon (7 regions incl. CALABARZON), not for provinces or LGUs."}
