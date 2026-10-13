"""Data inventory + completeness (guarded). Every data file: size, mtime, SHA-256 (hash/metadata only for files that
are not allowlisted). Allowlisted files: content coverage against the expected 5 provinces x 2021-Q1..2026-Q4 and
142 LGUs. Writes data_inventory/*.json|csv. Usage: python -B runner/data_inventory.py"""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import pandas as pd  # noqa: E402

sys.path.insert(0, str(guard.AL))
from app.quarterly.completeness import province_quarter_matrix, quarters_between, summarize  # noqa: E402

PROV = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
EXPECT = quarters_between("2021-Q1", "2026-Q4")
USES = {"features_fused.parquet": "45 governing candidates + cpi_dev (news + government features); Obj 1, 2, 4; H1-H3",
        "realized_components_2021_2025.csv": "Label components H, D, S1 (target); Obj 2, 4; H1-H3",
        "details.json": "SWS rounds with verified publication dates (label timing, SWS feature)",
        "provincial_food_cpi_yoy_2026H1_raw.csv": "2026-Q1/Q2 provincial food CPI (labels; authorized)",
        "cpi_2026_release_dates.csv": "National CPI release dates Jan-Jun 2026",
        "sws_hunger.parquet": "SWS 2026-Q1/Q2 rounds (labels; authorized rows only)",
        "lgu_poverty.parquet": "PSA 2021 SAE poverty (Obj 3 vulnerability weight)",
        "lgu_census.parquet": "2020 census population and land area (Obj 3 density)",
        "nns_fies.parquet": "Regional FIES anchor (Obj 5) - secondary 2025 value only",
        "topic_proportions.parquet": "BERTopic topic shares (Obj 1)",
        "governing_model.json": "Feature list of the governing configuration"}


def main():
    out = Path(guard.EXP) / "data_inventory"
    out.mkdir(exist_ok=True)
    allow = {str(p) for p in guard.ALLOW}
    files = []
    roots = [guard.AL / "data" / "processed", guard.AL / "data" / "supplementary", guard.AL / "data" / "reference",
             guard.ROOT / "backend" / "data" / "processed"]
    for r in roots:
        for p in sorted(r.rglob("*")):
            if p.is_file() and p.suffix.lower() in guard.DATA_SUFFIXES:
                st = p.stat()
                files.append({"path": str(p.relative_to(guard.ROOT)), "bytes": st.st_size,
                              "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                              "sha256": guard.sha256_file(p),
                              "access": "content read (allowlisted, hash-verified)" if str(p.resolve()) in allow
                              else "hash and metadata only (not authorized / not needed)",
                              "used_for": USES.get(p.name, "")})
    pd.DataFrame(files).to_csv(out / "file_inventory.csv", index=False, lineterminator="\n")
    rep = {"generated_utc": datetime.now(timezone.utc).isoformat(), "n_files": len(files), "datasets": {}}
    ff = guard.read_allowed_parquet(guard.PROC / "features_fused.parquet", ["province_code", "quarter", "FSSI", "cpi_dev",
                                                                             "food_cpi_yoy", "unemployment_rate"])
    for col in ("FSSI", "cpi_dev", "food_cpi_yoy"):
        m = province_quarter_matrix(ff, col, PROV, EXPECT)
        rep["datasets"][f"features_fused.{col}"] = summarize(m)
    rep["datasets"]["features_fused.unemployment_rate"] = {
        "note": "identical across provinces in every quarter (national series; no provincial LFS table exists)",
        "provinces_differ_in_any_quarter": bool(ff.groupby("quarter")["unemployment_rate"].nunique().gt(1).any())}
    comp = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.E12_RUN / "realized_components_2021_2025.csv")),
                       dtype={"province_code": str})
    cpi26 = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.COLL / "provincial_food_cpi_yoy_2026H1_raw.csv")),
                        dtype={"province_code": str})
    cpi26["quarter"] = cpi26["reference_month"].map(lambda m: f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}")
    lab = pd.concat([comp[["province_code", "quarter", "S1"]],
                     cpi26.groupby(["province_code", "quarter"])["food_cpi_yoy_pct_raw"].mean().reset_index()
                     .rename(columns={"food_cpi_yoy_pct_raw": "S1"})], ignore_index=True)
    m = province_quarter_matrix(lab, "S1", PROV, EXPECT)
    s = summarize(m)
    s["note"] = ("2026-Q1/Q2 cells marked PRESENT carry the CPI component (S1 also needs the authorized SWS rounds). "
                 "2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3 lack a production SWS round (no label). 2026-Q3/Q4 are protected "
                 "(not authorized) - absent here by design, not by data loss.")
    rep["datasets"]["label_S1"] = s
    det = json.loads(guard.read_allowed_text(guard.E12_RUN / "details.json"))
    rr = pd.DataFrame(det["two_layer"]["regional_layer_rounds"])
    rep["datasets"]["sws_rounds"] = {"rounds": len(rr), "production_rounds": int(rr["definition_A"].sum()),
                                     "date_types": rr["date_type"].value_counts().to_dict(),
                                     "quarters_without_production_round": sorted(set(quarters_between("2021-Q1", "2025-Q4"))
                                                                                  - set(rr.loc[rr["definition_A"], "quarter"]))}
    pov = guard.read_allowed_parquet(guard.PROC / "lgu_poverty.parquet", ["province_code", "lgu_code", "source_note"])
    cen = guard.read_allowed_parquet(guard.PROC / "lgu_census.parquet", ["province_code", "lgu_code", "population_2020",
                                                                         "land_area_km2"])
    rep["datasets"]["lgu"] = {"poverty_rows": len(pov), "census_rows": len(cen),
                              "codes_match": set(pov["lgu_code"]) == set(cen["lgu_code"]),
                              "poverty_province_mean_fallback": int(pov["source_note"].str.contains("fallback").sum()),
                              "zero_or_missing_land_area": int((cen["land_area_km2"].fillna(0) <= 0).sum())}
    (out / "completeness_report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: (v if k != "datasets" else {d: {kk: vv for kk, vv in x.items() if kk != "non_present_cells"}
                                                      for d, x in v.items()}) for k, v in rep.items()}, indent=1, default=str))


if __name__ == "__main__":
    main()
