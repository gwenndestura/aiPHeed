import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard; guard.install()
import pyarrow.dataset as ds
for f in ("lgu_census.parquet", "lgu_poverty.parquet"):
    p = guard.PROC / f; guard._check(p)
    print(f, guard._ORIG_DATASET(str(p), format="parquet").schema.names)
pov = guard.read_allowed_parquet(guard.PROC / "lgu_poverty.parquet", ["province_code", "lgu_code", "poverty_incidence_pct", "source_note"])
print(pov.groupby("province_code")["poverty_incidence_pct"].nunique().to_dict()); print(pov["source_note"].value_counts().head())
cen = guard.read_allowed_parquet(guard.PROC / "lgu_census.parquet", ["province_code", "lgu_code", "population_2020", "density_per_km2"])
print(cen.isna().sum().to_dict(), (cen["density_per_km2"] <= 0).sum())
