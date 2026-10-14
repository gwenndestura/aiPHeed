"""E25: inspect the structure of the authorized inputs (through the guard). Prints only what the data-completeness
matrix needs: coverage, columns, the 2026 rows that are authorized, and the SWS round metadata.
Usage: python -B runner/inspect_inputs.py > runs/inspect_inputs.txt"""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import pandas as pd  # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)

print("== allowlist verification")
for r in guard.verify_allowlist():
    print(r["match"], r["authorized_2026_source"], r["read_time_filter"], r["read_path"].split("aipheed")[-1])

c26 = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.CPI_2026H1)), dtype=str)
print("\n== CPI 2026 H1 (authorized)", c26.shape)
print(c26.to_string())
rel = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.CPI_2026_RELEASES)), dtype=str)
print("\n== CPI 2026 release dates (authorized)")
print(rel.to_string())
sws = guard.read_allowed_parquet(guard.PROD_SWS, ["quarter", "province_code", "survey_quarter_label",
                                                  "pct_total_hunger", "stratum", "source_url", "verified"])
print("\n== production SWS rows 2026-Q1..2026-Q2 (authorized)")
print(sws.drop_duplicates(["quarter", "survey_quarter_label"]).to_string())
print(len(sws), "rows;", sws["province_code"].nunique(), "provinces")

gov = json.loads(guard.read_allowed_text(guard.GOVERNING))
cand = gov["feature_set"]["candidates_section_3_3_2_6"]
print("\n== governing_model candidates:", len(cand))
print(cand)
ff = guard.read_allowed_parquet(guard.FEATURES_FUSED, ["province_code", "quarter"] + cand + ["cpi_dev"])
print("\n== features_fused (read-time filter 2021-Q1..2025-Q4)", ff.shape, ff["quarter"].min(), ff["quarter"].max())
nn = ff.notna().groupby(ff["quarter"].str[:4]).mean().T
print(nn.round(2).to_string())

cpi = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.CPI_INDEX_2021_2025)), dtype=str)
print("\n== CPI index 2021-2025 (E24v2 acquisition)", cpi.shape)
print(cpi.head(5).to_string())
print(cpi["Commodity Description"].unique(), cpi["Geolocation"].unique(), cpi["Year"].unique())

lc = guard.read_allowed_parquet(guard.LGU_CENSUS, ["lgu_code", "province_code"] if False else None) if False else None
print("\n== access log")
for a in guard.ACCESS_LOG:
    print(a)
