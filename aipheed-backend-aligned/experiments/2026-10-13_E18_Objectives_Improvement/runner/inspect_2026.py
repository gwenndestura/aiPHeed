"""E18: inspect the authorized Jan-Jun 2026 sources (structure + values needed for timing verification)."""
import sys, io, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard
guard.install()
import pandas as pd
cpi = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.COLL / "provincial_food_cpi_yoy_2026H1_raw.csv")))
rel = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.COLL / "cpi_2026_release_dates.csv")))
sws = guard.read_allowed_parquet(guard.PROD_SWS, ["quarter", "province_code", "survey_quarter_label", "pct_total_hunger", "stratum", "source_url", "verified"])
print(cpi.columns.tolist()); print(cpi.head(8).to_string()); print(len(cpi))
print(rel.to_string())
print(sws.drop_duplicates("quarter").to_string()); print(len(sws), sws["province_code"].nunique())
print(guard.ACCESS_LOG)
