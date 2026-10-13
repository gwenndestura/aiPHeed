"""
scripts/face_validity.py

Objective 5's face-validity anchor (PROPOSAL_CONFORMANCE 2.6).

Objective 5 asks that the forecasts be validated "against DOST-FNRI NNS 2019
and 2023 CALABARZON prevalence figures as a face-validity anchor". This script
does what the verified data allows, and says plainly what it cannot do yet.

1. NNS anchors. Only rows marked verified in nns_fies.parquet are used. The
   2019 and 2023 CALABARZON values were withdrawn on 2026-09-01 as unverifiable
   (enns_fetcher.REMOVED_UNVERIFIED) and are reported as missing, with the
   reason, until the DOST-FNRI regional tables are obtained. No value is
   estimated or typed in to fill them.

2. Regional level over time. The model's mean probability across the five
   provinces, per year, set beside every verified NNS cycle, so the direction
   of change can be compared as soon as a second cycle is verified.

3. Structural check, independent of the label. PSA provincial poverty
   incidence (2021 and 2023 releases) is not a model input and not part of
   Equation 3. The Spearman correlation between it and each province's mean
   predicted risk in the same year shows whether the model's ordering tracks
   structural poverty. It is reported whatever its sign.

Writes data/processed/face_validity.json.

    python -m scripts.face_validity
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

from app.ml.inference.predictor import Predictor

OUT = Path("data/processed/face_validity.json")
NNS = Path("data/processed/nns_fies.parquet")
FEATURES = Path("data/processed/features_fused.parquet")
POVERTY_YEARS = ["2021", "2023"]   # PSA provincial poverty release years in the window
REQUIRED_CYCLES = ["NNS_2019", "NNS_2023"]


def main() -> dict:
    fc = pd.DataFrame(Predictor().forecast_all_quarters())
    fc["year"] = fc["quarter"].str[:4]
    regional = fc.groupby("year")["risk_probability"].mean().round(4).to_dict()

    anchors, missing = [], []
    if NNS.exists():
        nns = pd.read_parquet(NNS)
        ver = nns[nns["verified"] == True]  # noqa: E712
        for cycle, g in ver.groupby("survey_cycle"):
            row = g.iloc[0]
            anchors.append({
                "cycle": cycle, "year": int(row["year"]),
                "calabarzon_moderate_severe_pct": float(row["fies_moderate_severe_pct"]),
                "geographic_level": row["geographic_level"],
                "source": row["source_url"],
                "model_mean_risk_that_year": regional.get(str(int(row["year"]))),
            })
    have = {a["cycle"] for a in anchors}
    try:
        from app.ml.corpus.enns_fetcher import REMOVED_UNVERIFIED
        removed = {str(r.get("survey_cycle", r)) if isinstance(r, dict) else str(r)
                   for r in REMOVED_UNVERIFIED}
    except Exception:
        removed = set()
    for cycle in REQUIRED_CYCLES:
        if cycle not in have:
            missing.append({
                "cycle": cycle,
                "reason": ("withdrawn 2026-09-01 as unverifiable; awaiting the DOST-FNRI "
                           "regional table" if any(cycle in r for r in removed)
                           else "no verified CALABARZON value on file"),
            })

    feats = pd.read_parquet(FEATURES)
    feats["year"] = feats["quarter"].str[:4]
    structural = []
    for y in POVERTY_YEARS:
        risk = fc[fc["year"] == y].groupby("province_code")["risk_probability"].mean()
        pov = feats[feats["year"] == y].groupby("province_code")["poverty_incidence"].mean()
        common = risk.index.intersection(pov.index)
        rho = float(spearmanr(risk[common], pov[common])[0]) if len(common) > 2 else None
        structural.append({
            "year": y, "n_provinces": int(len(common)),
            "spearman_risk_vs_poverty": round(rho, 3) if rho is not None else None,
            "mean_risk": risk[common].round(4).to_dict(),
            "poverty_incidence_pct": pov[common].round(1).to_dict(),
        })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "objective": "Objective 5 face-validity anchor",
        "nns_anchors": anchors,
        "nns_cycles_missing": missing,
        "regional_mean_risk_by_year": regional,
        "structural_poverty_check": structural,
        "interpretation": (
            "The model's probability measures food-price stress relative to the "
            "region (Equation 3), not structural poverty. A weak or negative "
            "correlation with PSA poverty incidence is therefore not a failure of "
            "the model; it is the reason Algorithm 5 weights municipal rankings "
            "by poverty incidence. The NNS comparison of direction over time can "
            "only be made once at least two CALABARZON cycles are verified."
        ),
    }
    OUT.write_text(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    print(json.dumps(main(), indent=2, default=str))
