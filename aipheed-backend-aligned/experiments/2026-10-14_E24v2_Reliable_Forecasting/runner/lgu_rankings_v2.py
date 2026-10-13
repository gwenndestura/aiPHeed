"""E24 Objective 3: validate all 142 LGUs (codes, names, sources), build the v2 ranking table that labels province-mean
substitutes honestly, and confirm the approved formula reproduces E23 exactly. If an authorized PSA SAE workbook is
supplied (--sae <path> --sae-year 2021), it is ingested into data_v2/ as a new version (original untouched).
Usage: python -B runner/lgu_rankings_v2.py [--sae PATH --sae-year 2021]"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import pandas as pd  # noqa: E402

EXP = guard.EXP
sys.path.insert(0, str(EXP / "backend_dev"))
from app.quarterly.lgu_poverty import parse_sae_table, rank_lgus, validate_against_census  # noqa: E402

PROV = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
        "PH040500000": "Batangas"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sae", default=None)
    ap.add_argument("--sae-year", type=int, default=2021)
    a = ap.parse_args()
    cen = guard.read_allowed_parquet(guard.PROC / "lgu_census.parquet",
                                     ["province_code", "lgu_code", "lgu_name", "lgu_type", "population_2020",
                                      "land_area_km2", "density_per_km2", "population_source"])
    pov = guard.read_allowed_parquet(guard.PROC / "lgu_poverty.parquet",
                                     ["province_code", "lgu_code", "lgu_name", "year", "poverty_incidence_pct",
                                      "source_note", "source_url"])
    ref = pd.read_csv(guard.AL / "data" / "reference" / "calabarzon_lgus.csv", dtype=str)
    # ---- identity checks across the three LGU lists
    chk = {"census_rows": len(cen), "poverty_rows": len(pov), "reference_rows": len(ref),
           "codes_census_eq_poverty": set(cen.lgu_code) == set(pov.lgu_code),
           "codes_census_eq_reference": set(cen.lgu_code) == set(ref.lgu_psgc),
           "names_census_eq_poverty": bool((cen.set_index("lgu_code").lgu_name == pov.set_index("lgu_code").lgu_name
                                            .reindex(cen.lgu_code)).all()),
           "names_census_eq_reference": bool((cen.set_index("lgu_code").lgu_name ==
                                              ref.set_index("lgu_psgc").lgu_name.reindex(cen.lgu_code)).all()),
           "province_prefix_ok": bool((cen.lgu_code.str[:4].map({"0410": "PH040500000", "0421": "PH040100000",
                                                                 "0434": "PH040200000", "0456": "PH040300000",
                                                                 "0458": "PH040400000"}) == cen.province_code).all()),
           "population_matches_reference": bool((cen.set_index("lgu_code").population_2020.astype(int) ==
                                                 ref.set_index("lgu_psgc").population_2020.astype(int)
                                                 .reindex(cen.lgu_code)).all()),
           "density_recomputed_max_abs_diff": float((cen.population_2020 / cen.land_area_km2 - cen.density_per_km2)
                                                    .abs().max()),
           "lgus_per_province": cen.groupby("province_code").size().rename(index=PROV).to_dict()}
    # ---- poverty v1 (authorized file): municipal estimate only where the source note says so
    fallback = pov.source_note.str.contains("fallback", case=False)
    pv = pd.DataFrame({"lgu_code": pov.lgu_code,
                       "poverty_lgu_estimate": pov.poverty_incidence_pct.where(~fallback),
                       "poverty_province_value": pov.groupby("province_code").poverty_incidence_pct.transform(
                           lambda s: s[fallback.loc[s.index]].iloc[0] if fallback.loc[s.index].any() else float("nan")),
                       "poverty_source": pov.source_note})
    version = "v1 (authorized lgu_poverty.parquet; 16 municipal SAE values)"
    sae_report = None
    if a.sae:
        raw = pd.read_excel(a.sae, dtype=str)   # keep PSGC leading zeros                               # caller must have authorized this exact file
        sae = parse_sae_table(raw, a.sae_year)
        matched, sae_report = validate_against_census(sae, cen)
        sae_report["file_sha256"] = hashlib.sha256(Path(a.sae).read_bytes()).hexdigest()
        if sae_report["passes"]:
            pv = pv.drop(columns="poverty_lgu_estimate").merge(
                matched[["lgu_code", "poverty_incidence_pct"]].rename(columns={"poverty_incidence_pct": "poverty_lgu_estimate"}),
                on="lgu_code", how="left")
            pv["poverty_source"] = f"PSA {a.sae_year} SAE workbook sha256 {sae_report['file_sha256'][:16]}"
            version = f"v2 (PSA {a.sae_year} SAE workbook)"
            (EXP / "data_v2").mkdir(exist_ok=True)
            matched.to_csv(EXP / "data_v2" / f"lgu_poverty_sae{a.sae_year}_v2.csv", index=False, lineterminator="\n")
    # ---- probabilities: E23 sealed back-test (2026-Q1, lead 1) for illustration only
    e23 = guard.E23_DIR / "runs" / "20261013T152113Z"
    seal = json.loads((e23 / "SEAL_origin.json").read_text(encoding="utf-8"))["sha256"]
    assert hashlib.sha256((e23 / "predictions_origin.csv").read_bytes()).hexdigest() == seal
    P = pd.read_csv(e23 / "predictions_origin.csv", dtype={"province_code": str})
    p = P[(P.model == "PROPOSED_lgbm_combined") & (P.lead == 1) & (P.target_quarter == "2026-Q1")]
    probs = dict(zip(p.province_code, p.score))
    r = rank_lgus(cen[["province_code", "lgu_code", "lgu_name", "lgu_type", "population_2020", "land_area_km2"]], pv, probs)
    # ---- reproduction against E23 (same formula, same inputs) when no new workbook is used
    old = pd.read_csv(guard.E23_DIR / "rankings" / "lgu_rankings_backtest_2026Q1.csv", dtype={"lgu_code": str,
                                                                                           "province_code": str})
    cmp = r.merge(old[["lgu_code", "risk_index", "vulnerability_index"]], on="lgu_code", suffixes=("", "_e23"))
    chk["max_abs_diff_risk_vs_E23"] = float((cmp.risk_index - cmp.risk_index_e23).abs().max())
    chk["ties_in_risk_index"] = int(r.risk_index.duplicated(keep=False).sum())
    chk["lgus_with_municipal_estimate"] = int(r.poverty_lgu_estimate.notna().sum())
    chk["lgus_with_substitute"] = int(r.poverty_lgu_estimate.isna().sum())
    chk["version"] = version
    chk["sae_ingestion"] = sae_report or "not run: the PSA 2021 SAE workbook is not available in the project " \
        "(psa.gov.ph and foi.gov.ph returned HTTP 403 to automated access on 2026-10-14)"
    out = r.assign(province=r.province_code.map(PROV), ranking_quarter="2026-Q1 BACKTEST (illustration)",
                   rank_tie_rule="competition rank on risk_index rounded to 4 dp; listing order inside ties = lgu_code",
                   method="risk = province probability x (0.6 poverty_norm + 0.4 density_norm), within-province min-max",
                   label="Relative ordinal estimate; not an official food-insecurity measurement")
    cols = ["lgu_code", "lgu_name", "lgu_type", "province", "population_2020", "land_area_km2", "density",
            "poverty_lgu_estimate", "poverty_value_used", "poverty_value_kind", "poverty_source", "vulnerability_index",
            "vulnerability_rank_in_province", "province_probability", "risk_index", "rank_region", "rank_in_province",
            "ranking_quarter", "rank_tie_rule", "method", "limitation", "label"]
    (EXP / "data_v2").mkdir(exist_ok=True)   # E24v2: LGU input table; LGU_RANKING_VALIDATION.csv is built by lgu_analysis.py
    out[cols].to_csv(EXP / "data_v2" / "lgu_vulnerability_table.csv", index=False, lineterminator="\n")
    (EXP / "runs" / "lgu_validation.json").write_text(json.dumps(chk, indent=1, default=str), encoding="utf-8")
    print(json.dumps(chk, indent=1, default=str))


if __name__ == "__main__":
    main()
