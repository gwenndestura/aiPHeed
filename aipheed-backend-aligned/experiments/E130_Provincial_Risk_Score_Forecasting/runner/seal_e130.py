"""
E130 survey-year seal: forecasts of the next PSA provincial subsistence round after 2023, made from the 2021 and 2023
rounds only and frozen before E130 searches for any newer provincial release. Five provinces, one fold: descriptive
evidence, never a reliability or Lead-2 claim.

S1 persistence       the 2023 value
S2 two-round mean    (2021 + 2023) / 2
S3 EB-shrunk 2023    m + w (y2023 - m), w = tau2 / (tau2 + SE^2), tau2 = between-province variance net of sampling error

90 % prediction interval: pred +/- 1.645 sqrt(s2_change + SE_next^2), with s2_change = mean(change^2) - mean(SE_2021^2 +
SE_2023^2) from the 2021->2023 changes (true two-year change variance) and SE_next taken equal to the 2023 SE.
LightGBM, PSA-only, NLP-only and linear models are not fitted: one change per province (5 training rows) is below the
protocol's minimum of 20 training rows.

Run:  python runner/seal_e130.py      (refuses to overwrite an existing seal)
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e130_lib as L  # noqa: E402

SEAL = L.SEALED / "E130_SURVEY_YEAR_SEAL.csv"
SEAL_HASH = L.SEALED / "E130_SURVEY_YEAR_SEAL_SHA256.txt"


def forecasts(ref: pd.DataFrame) -> pd.DataFrame:
    a = ref[ref.survey_year == 2021].set_index("province").loc[list(L.PROVINCES)]
    b = ref[ref.survey_year == 2023].set_index("province").loc[list(L.PROVINCES)]
    s2_change = max(0.0, float(np.mean((b.pfdr_pct - a.pfdr_pct) ** 2) - np.mean(a.se_pp ** 2 + b.se_pp ** 2)))
    tau2 = max(0.0, float(np.var(b.pfdr_pct, ddof=1) - np.mean(b.se_pp ** 2)))
    m = float(b.pfdr_pct.mean())
    w = tau2 / (tau2 + b.se_pp ** 2)
    preds = {"S1_persistence": b.pfdr_pct, "S2_two_round_mean": (a.pfdr_pct + b.pfdr_pct) / 2,
             "S3_eb_shrunk_2023": m + w * (b.pfdr_pct - m)}
    half = L.Z90 * np.sqrt(s2_change + b.se_pp ** 2)
    rows = []
    for name, p in preds.items():
        for prov in L.PROVINCES:
            rows.append({"model": name, "province": prov, "target": "next PSA provincial subsistence round after 2023 (survey year 2025 expected)",
                         "pred_pct": round(float(p[prov]), 6), "pi90_lo": round(max(0.0, float(p[prov] - half[prov])), 6),
                         "pi90_hi": round(float(p[prov] + half[prov]), 6), "latest_value_2023": float(b.pfdr_pct[prov]),
                         "latest_se_2023": round(float(b.se_pp[prov]), 6),
                         "information_set": "PSA provincial subsistence 2021 and 2023 (published 2024-08-15) only",
                         "s2_change": round(s2_change, 6), "tau2_2023": round(tau2, 6)})
    return pd.DataFrame(rows)


def content_hash(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()


if __name__ == "__main__":
    if SEAL.exists():
        sys.exit(f"refusing to overwrite {SEAL} (sha256 {L.sha256(SEAL)})")
    df = forecasts(L.load_reference())
    df.insert(0, "sealed_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    SEAL.parent.mkdir(parents=True, exist_ok=True)
    SEAL.write_bytes(df.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    SEAL_HASH.write_text(L.sha256(SEAL) + "  E130_SURVEY_YEAR_SEAL.csv\n", encoding="utf-8")
    print(df[["model", "province", "pred_pct", "pi90_lo", "pi90_hi"]].to_string(index=False))
    print("sealed", L.sha256(SEAL))
