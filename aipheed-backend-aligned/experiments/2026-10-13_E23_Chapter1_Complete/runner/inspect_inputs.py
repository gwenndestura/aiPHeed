"""Structure check of allowlisted inputs (columns, coverage). Prints no 2026-H2 data (none is allowlisted)."""
import sys, io, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard
guard.install()
import pandas as pd
v = guard.verify_allowlist()
for r in v: print(r["match"], r["pinned_by"], Path(r["path"]).name, r["read_time_filter"])
comp = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.E12_RUN / "realized_components_2021_2025.csv")), dtype={"province_code": str})
print(comp.columns.tolist(), comp.shape, comp["quarter"].min(), comp["quarter"].max())
print(comp.groupby("quarter")["S1"].count().to_dict())
det = json.loads(guard.read_allowed_text(guard.E12_RUN / "details.json"))
r = pd.DataFrame(det["two_layer"]["regional_layer_rounds"]); print(r.columns.tolist()); print(r.to_string())
pov = guard.read_allowed_parquet(guard.PROC / "lgu_poverty.parquet", ["province_code","lgu_code","lgu_name","year","poverty_incidence_pct"])
cen = guard.read_allowed_parquet(guard.PROC / "lgu_census.parquet", ["province_code","lgu_code","lgu_name","population_2020","density_per_km2"])
print(pov.shape, pov["year"].unique(), pov.groupby("province_code").size().to_dict(), cen.shape, cen.groupby("province_code").size().to_dict())
fies = guard.read_allowed_parquet(guard.PROC / "nns_fies.parquet", ["survey_cycle","year","region_name","fies_moderate_severe_pct","geographic_level","provenance"])
print(fies.drop_duplicates(["survey_cycle","year","fies_moderate_severe_pct"]).to_string())
