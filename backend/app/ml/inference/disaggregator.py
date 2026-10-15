"""
app/ml/inference/disaggregator.py
-----------------------------------
Municipal-level spatial disaggregation of province forecasts.

Formula (Equation 6, Section 3.4.2):
    y_hat(m, t+1) = y_hat(province, t+1) * (0.6 * poverty_m + 0.4 * density_m)

where:
    y_province  = the validated province-level LightGBM forecast probability
                  from Predictor.forecast_quarter()
    poverty_m   = PSA 2021 small area poverty incidence, min-max normalized
                  within the municipality's own province
    density_m   = PSA 2024 POPCEN population density, min-max normalized
                  within the municipality's own province

Outputs are relative within-province vulnerability rankings, NOT independent
municipal forecasts (Rule 4, Rule 8).

The output is a ranked DataFrame with 142 municipal risk indices per quarter.
Every output row MUST carry disaggregation_label (Backend Guide Rule 8).

KNOWN LIMITATION -- the poverty term is weaker than its 60% weight implies.
lgu_poverty.parquet resolves to only 3-5 distinct values per province across
142 LGUs, and its own source_note reads "province-mean fallback -- LGU SAE not
in table": most municipalities carry their province's mean rather than a real
Small Area Estimate. It still drives the ranking (correlation 0.740 with the
final score against 0.334 for density) because of that weight, so within-province
ordering rests largely on a variable that barely varies within a province.

PSA released genuine 2021 city and municipal poverty estimates in April 2024
covering 114 cities and 1,484 municipalities. Loading those would make this
disaggregation what the label claims it already is. Until then the label says
what the data actually is.

Usage:
    from app.ml.inference.disaggregator import Disaggregator
    lgu_df = Disaggregator().disaggregate(province_forecasts, quarter="2026-Q1")
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

E28_VULNERABILITY_PATH = Path("data/inputs/lgu_vulnerability.csv")   # authorized E25 export (142 LGUs)
LGU_CENSUS_PATH  = Path("data/processed/lgu_census.parquet")
LGU_POVERTY_PATH = Path("data/processed/lgu_poverty.parquet")

DISAGGREGATION_LABEL = (
    "Spatially disaggregated estimate derived from the province-level "
    "province food insecurity risk forecast, weighted by LGU poverty incidence (60%) "
    "and 2024 POPCEN population density (40%). Poverty values are PSA 2021 "
    "municipal Small Area Estimates (province value for Lucena City), and "
    "within-province ordering is indicative only. Municipal-level uncertainty "
    "is higher than province-level uncertainty. Not an independent municipal "
    "forecast."
)

# Vulnerability weight split (Backend Guide v3)
POVERTY_WEIGHT  = 0.6
DENSITY_WEIGHT  = 0.4


class Disaggregator:
    """
    Loads LGU census and poverty data once, then disaggregates on demand.
    """

    _lgu: pd.DataFrame | None = None
    _pov: pd.DataFrame | None = None

    def _load(self):
        if self._lgu is not None:
            return
        if not LGU_CENSUS_PATH.exists() or not LGU_POVERTY_PATH.exists():
            raise FileNotFoundError(
                "LGU census or poverty parquets missing. Run fix_primary_data.py."
            )
        self._lgu = pd.read_parquet(LGU_CENSUS_PATH)
        self._pov = pd.read_parquet(LGU_POVERTY_PATH)
        logger.info(
            "Disaggregator: loaded %d LGUs (census) + %d LGUs (poverty)",
            len(self._lgu), len(self._pov),
        )

    def disaggregate(
        self,
        province_forecasts: list[dict],
        quarter: str,
    ) -> pd.DataFrame:
        """
        Disaggregate province-level forecasts to 142 LGUs.

        Parameters
        ----------
        province_forecasts : list[dict]
            Output from Predictor.forecast_quarter() — one dict per province.
        quarter : str  e.g. "2026-Q1"

        Returns
        -------
        pd.DataFrame  — 142 rows (all CALABARZON LGUs), columns:
            quarter, province_code, lgu_code, municipality_name,
            risk_index, disaggregation_label, data_sufficiency_flag
        Sorted by risk_index descending.
        """
        # E28 fix: ONE ranking implementation. This method used to compute its own version of the formula, which
        # (a) filled a province with no poverty value with 0.0 -- a false measurement that ranked its LGUs as least
        # poor -- and (b) left the order of tied LGUs to the sort algorithm. The quarterly forecaster, the stored
        # record and the PDF use app.quarterly.lgu_poverty.rank_lgus (null-safe, labelled substitutes, competition
        # ranks with PSGC order inside ties), so the dashboard now uses it too, on the authorized input table.
        if E28_VULNERABILITY_PATH.exists():
            return self._disaggregate_e28(province_forecasts, quarter)
        self._load()

        # Build province → forecast lookup
        prov_map = {f["province_code"]: f for f in province_forecasts}

        lgu = self._lgu.copy()
        pcols = ["lgu_code", "poverty_incidence_pct"] + (["source_note"] if "source_note" in self._pov.columns else [])
        pov = self._pov[pcols].copy() if self._pov is not None else pd.DataFrame()

        # Merge census + poverty
        merged = lgu.merge(pov, on="lgu_code", how="left")
        merged["poverty_incidence_pct"] = merged["poverty_incidence_pct"].fillna(
            merged.groupby("province_code")["poverty_incidence_pct"].transform("mean")
        )
        if merged["poverty_incidence_pct"].isna().any():
            # E28 fix: was .fillna(0.0). A province without any poverty value cannot be weighted by poverty.
            raise ValueError("LGU poverty values missing for a whole province; refusing to substitute 0")

        # Compute population density (persons / km²)
        if "land_area_km2" in merged.columns and "population_2024" in merged.columns:
            merged["density"] = merged["population_2024"] / merged["land_area_km2"].replace(0, np.nan)
        elif "population_density" in merged.columns:
            merged["density"] = merged["population_density"]
        else:
            merged["density"] = 1.0
        merged["density"] = merged["density"].fillna(merged.groupby("province_code")["density"].transform("mean")).fillna(1.0)

        # Normalize within province (min-max scaling)
        for col in ["poverty_incidence_pct", "density"]:
            grp = merged.groupby("province_code")[col]
            mn = grp.transform("min")
            mx = grp.transform("max")
            rng = (mx - mn).replace(0, 1)
            merged[f"{col}_norm"] = (merged[col] - mn) / rng

        # Vulnerability weight
        merged["vulnerability"] = (
            POVERTY_WEIGHT  * merged["poverty_incidence_pct_norm"]
            + DENSITY_WEIGHT * merged["density_norm"]
        )

        # Apply province forecast
        rows = []
        for _, lgu_row in merged.iterrows():
            province_code = lgu_row["province_code"]
            forecast = prov_map.get(province_code)
            # E23 fix: a province WITHOUT a forecast is unavailable, not zero risk. The old default of
            # 0.0 ranked every LGU of that province as the safest in the region.
            prov_prob = None if forecast is None else forecast.get("risk_probability")
            data_flag = "NO_PROVINCE_FORECAST" if prov_prob is None else forecast.get("data_sufficiency_flag")

            if prov_prob is None:
                risk_index = None
            else:
                risk_index = float(prov_prob * lgu_row["vulnerability"])
                risk_index = round(min(max(risk_index, 0.0), 1.0), 4)
            note = str(lgu_row.get("source_note", "") or "")

            lgu_code = lgu_row.get("lgu_code", "")
            lgu_name = lgu_row.get("lgu_name", "")

            rows.append({
                "quarter":              quarter,
                "province_code":        province_code,
                "lgu_code":             lgu_code,
                "municipality_name":    lgu_name,
                "risk_index":           risk_index,
                "disaggregation_label": DISAGGREGATION_LABEL,
                "data_sufficiency_flag": data_flag,
                "vulnerability_index":  round(float(lgu_row["vulnerability"]), 6),
                # True when PSA publishes no LGU-specific estimate and the province mean is used.
                "poverty_is_province_fallback": "fallback" in note.lower(),
            })

        df = (pd.DataFrame(rows).sort_values(["risk_index", "lgu_code"], ascending=[False, True],
                                             na_position="last").reset_index(drop=True))
        logger.info(
            "disaggregate(%s): %d LGUs | risk_index range [%.4f, %.4f]",
            quarter, len(df),
            df["risk_index"].min() if len(df) else 0,
            df["risk_index"].max() if len(df) else 0,
        )
        return df

    def _disaggregate_e28(self, province_forecasts: list[dict], quarter: str) -> pd.DataFrame:
        from app.quarterly.forecaster_v2 import lgu_table

        lg = pd.read_csv(E28_VULNERABILITY_PATH, dtype={"lgu_code": str})
        lg["lgu_code"] = lg["lgu_code"].str.zfill(9)
        prov_map = {f["province_code"]: f for f in province_forecasts}
        prob = {p: f.get("risk_probability") for p, f in prov_map.items() if f.get("risk_probability") is not None}
        rk = lgu_table(lg, prob or None)
        rk["lgu_code"] = rk["lgu_code"].astype(str).str.zfill(9)
        ties = rk[rk["risk_index"].notna()].groupby("risk_index").size()
        out = pd.DataFrame({
            "quarter": quarter,
            "province_code": rk["province_code"],
            "lgu_code": rk["lgu_code"],
            "municipality_name": rk["lgu_name"],
            "risk_index": [None if pd.isna(x) else float(x) for x in rk["risk_index"]],
            "disaggregation_label": DISAGGREGATION_LABEL,
            "data_sufficiency_flag": [("NO_PROVINCE_FORECAST" if p not in prob
                                       else prov_map[p].get("data_sufficiency_flag")) for p in rk["province_code"]],
            "vulnerability_index": rk["vulnerability_index"].round(6),
            "poverty_is_province_fallback": rk["poverty_lgu_estimate"].isna(),
            "rank_region": [None if pd.isna(x) else int(x) for x in rk["rank_region"]],
            "rank_in_province": [None if pd.isna(x) else int(x) for x in rk["rank_in_province"]],
            "tied": [bool(pd.notna(x) and ties.get(x, 0) > 1) for x in rk["risk_index"]],
        })
        return out.reset_index(drop=True)
