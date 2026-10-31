"""
E130 seal scoring (protocol section 7): scores the sealed survey-year forecasts against the next PSA provincial
subsistence round once the owner supplies it. Nothing is scored until that file exists.

Expected input (owner-supplied; values copied from the PSA 2025 Full Year Poverty Statistics provincial tables):
    data/owner_supplied/psa_subsistence_population_2025.csv
    columns: province, survey_year, subsistence_incidence_pct, cv_pct, source, publication_date
Only 2021+ rows are accepted; the file is hashed before any value is read.

Run:  python runner/score_e130.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e130_lib as L  # noqa: E402

SEAL = L.SEALED / "E130_SURVEY_YEAR_SEAL.csv"
SEAL_SHA = "94a08cd1d4b4497effbf95340f091eca46d2cc087d562a37ed134eb1b38593ed"
NEXT = L.ROOT / "data" / "owner_supplied" / "psa_subsistence_population_2025.csv"


def load_next(path: Path = NEXT) -> tuple[pd.DataFrame, str]:
    digest = L.sha256(path)                                # hashed before any value is read
    d = pd.read_csv(path)
    need = {"province", "survey_year", "subsistence_incidence_pct", "cv_pct"}
    assert need <= set(d.columns), f"missing columns {need - set(d.columns)}"
    assert (d["survey_year"] >= 2021).all(), "pre-2021 row in the owner-supplied file"
    assert set(d["province"]) == set(L.PROVINCES) and not d.duplicated("province").any()
    d["se_pp"] = d["subsistence_incidence_pct"] * d["cv_pct"] / 100.0
    return d.set_index("province"), digest


def score(seal: pd.DataFrame, nxt: pd.DataFrame) -> dict:
    out = {"models": {}}
    y = nxt.loc[list(L.PROVINCES), "subsistence_incidence_pct"].to_numpy(float)
    se = nxt.loc[list(L.PROVINCES), "se_pp"].to_numpy(float)
    ref = L.load_reference()
    r23 = ref[ref.survey_year == 2023].set_index("province").loc[list(L.PROVINCES)]
    real = np.abs(y - r23["pfdr_pct"].to_numpy()) / np.sqrt(se ** 2 + r23["se_pp"].to_numpy() ** 2) > L.Z90
    for m, g in seal.groupby("model"):
        g = g.set_index("province").loc[list(L.PROVINCES)]
        f = g["pred_pct"].to_numpy(float)
        met = L.numeric_metrics(y, f, se, prev=r23["pfdr_pct"].to_numpy(float))
        met["pi90_coverage"] = float(np.mean((y >= g["pi90_lo"]) & (y <= g["pi90_hi"])))
        met["direction_on_real_changes"] = (float(np.mean(np.sign(f[real] - r23["pfdr_pct"].to_numpy()[real]) ==
                                                          np.sign(y[real] - r23["pfdr_pct"].to_numpy()[real])))
                                            if real.any() else None)
        met["spearman"] = float(stats.spearmanr(f, y)[0]) if np.ptp(f) > 0 else None
        out["models"][m] = met
    out["n_provinces"] = 5
    out["real_changes_2023_to_next"] = int(real.sum())
    out["note"] = "five provinces, one fold: descriptive only; cannot establish reliability or Lead 2"
    return out


if __name__ == "__main__":
    assert L.sha256(SEAL) == SEAL_SHA, "seal changed since the freeze"
    if not NEXT.exists():
        sys.exit(f"not scored: {NEXT.relative_to(L.ROOT)} not supplied yet (PSA PDF behind a bot check; OpenSTAT not updated)")
    nxt, digest = load_next()
    res = score(pd.read_csv(SEAL), nxt)
    res["input_sha256"] = digest
    L.dump(res, L.OUT / "seal_scores.json")
    print(pd.DataFrame(res["models"]).T.round(3).to_string())
