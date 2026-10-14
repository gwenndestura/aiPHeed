"""E25 Objective 3: rebuild all 142 LGU rankings with the approved formula, label every province-mean substitute,
disclose where density runs opposite to poverty, and check determinism.

risk = province probability x (0.6 poverty_norm + 0.4 density_norm), min-max within province, clamp [0, 1].
Province probabilities: the E25 sealed FINAL_T1 (PCF21) forecast for 2026-Q4 (lead 1 from O(2026-Q3)), hash-verified;
INDICATIVE ONLY (the lead is not validated). Within-province order does not depend on the province probability.
The PSA municipal SAE workbook is ingested only if the researcher supplies it (--sae PATH --sae-sha256 HASH).
Usage: python -B runner/lgu_rankings.py [--sae PATH --sae-sha256 HASH --sae-year 2021]"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

import e25lib as E  # noqa: E402

EXP = guard.EXP
sys.path.insert(0, str(EXP / "backend_dev"))
from app.quarterly.lgu_poverty import parse_sae_table, rank_lgus, validate_against_census  # noqa: E402

PREFIX = {"0410": "PH040500000", "0421": "PH040100000", "0434": "PH040200000", "0456": "PH040300000",
          "0458": "PH040400000"}


def sealed_probabilities():
    sd = sorted((EXP / "runs").glob("SEAL_E25_*"))[-1]
    seal = json.loads((sd / "SEAL.json").read_text(encoding="utf-8"))
    b = (sd / "prospective_forecasts.csv").read_bytes()
    assert hashlib.sha256(b).hexdigest() == seal["sha256_forecasts"], "seal bytes changed"
    P = pd.read_csv(io.BytesIO(b), dtype={"province_code": str})
    p = P[(P["target"] == "T1_A") & (P["arm"] == "PCF21") & (P["target_quarter"] == "2026-Q4")]
    assert len(p) == 5
    return dict(zip(p["province_code"], p["p"])), sd.name, seal["sha256_forecasts"]


def build(cen, pov, probs):
    fallback = pov["source_note"].str.contains("fallback", case=False)
    pv = pd.DataFrame({"lgu_code": pov["lgu_code"],
                       "poverty_lgu_estimate": pov["poverty_incidence_pct"].where(~fallback),
                       "poverty_province_value": pov.groupby("province_code")["poverty_incidence_pct"].transform(
                           lambda s: s[fallback.loc[s.index]].iloc[0] if fallback.loc[s.index].any() else float("nan")),
                       "poverty_source": pov["source_note"]})
    return rank_lgus(cen[["province_code", "lgu_code", "lgu_name", "lgu_type", "population_2020", "land_area_km2"]],
                     pv, probs), pv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sae", default=None)
    ap.add_argument("--sae-sha256", default=None)
    ap.add_argument("--sae-year", type=int, default=2021)
    a = ap.parse_args()
    cen = guard.read_allowed_parquet(guard.LGU_CENSUS, ["province_code", "lgu_code", "lgu_name", "lgu_type",
                                                        "population_2020", "land_area_km2", "density_per_km2",
                                                        "population_source"])
    pov = guard.read_allowed_parquet(guard.LGU_POVERTY, ["province_code", "lgu_code", "lgu_name", "year",
                                                         "poverty_incidence_pct", "source_note", "source_url"])
    ref = pd.read_csv(guard.REFERENCE_DIR / "calabarzon_lgus.csv", dtype=str)
    chk = {"census_rows": len(cen), "poverty_rows": len(pov), "reference_rows": len(ref),
           "codes_census_eq_poverty": set(cen.lgu_code) == set(pov.lgu_code),
           "codes_census_eq_reference": set(cen.lgu_code) == set(ref.lgu_psgc),
           "names_census_eq_reference": bool((cen.set_index("lgu_code").lgu_name ==
                                              ref.set_index("lgu_psgc").lgu_name.reindex(cen.lgu_code)).all()),
           "province_prefix_ok": bool((cen.lgu_code.str[:4].map(PREFIX) == cen.province_code).all()),
           "population_matches_reference": bool((cen.set_index("lgu_code").population_2020.astype(int) ==
                                                 ref.set_index("lgu_psgc").population_2020.astype(int)
                                                 .reindex(cen.lgu_code)).all()),
           "density_recomputed_max_abs_diff": float((cen.population_2020 / cen.land_area_km2 - cen.density_per_km2)
                                                    .abs().max()),
           "lgus_per_province": cen.groupby("province_code").size().rename(index=E.PNAME).to_dict()}
    probs, seal_name, seal_sha = sealed_probabilities()
    r, pv = build(cen, pov, probs)
    version = "v1 (authorized lgu_poverty.parquet: municipal estimates only where the source is municipal)"
    sae_report = None
    if a.sae:
        if not a.sae_sha256 or hashlib.sha256(Path(a.sae).read_bytes()).hexdigest() != a.sae_sha256.lower():
            raise SystemExit("PSA SAE workbook refused: its SHA-256 must be supplied by the researcher and must match")
        raw = pd.read_excel(a.sae, dtype=str)
        sae = parse_sae_table(raw, a.sae_year)
        matched, sae_report = validate_against_census(sae, cen)
        if sae_report["passes"]:
            pv2 = pv.drop(columns="poverty_lgu_estimate").merge(
                matched[["lgu_code", "poverty_incidence_pct"]].rename(columns={"poverty_incidence_pct": "poverty_lgu_estimate"}),
                on="lgu_code", how="left")
            r = rank_lgus(cen[["province_code", "lgu_code", "lgu_name", "lgu_type", "population_2020", "land_area_km2"]],
                          pv2, probs)
            version = f"v2 (PSA {a.sae_year} SAE workbook)"
    # determinism: same output from shuffled input order
    r2, _ = build(cen.sample(frac=1, random_state=7).reset_index(drop=True),
                  pov.sample(frac=1, random_state=11).reset_index(drop=True), probs)
    cols_cmp = ["lgu_code", "risk_index", "rank_region", "rank_in_province", "vulnerability_index"]
    chk["deterministic_under_shuffled_input"] = bool(r[cols_cmp].reset_index(drop=True).equals(
        r2[cols_cmp].reset_index(drop=True)))
    both = r[r["poverty_lgu_estimate"].notna()]
    rho = spearmanr(both["density"], both["poverty_lgu_estimate"])
    chk["density_vs_poverty_where_both_exist"] = {
        "n_lgus": int(len(both)), "spearman_rho": float(rho.statistic), "p_two_sided": float(rho.pvalue),
        "reading": "density runs OPPOSITE to poverty (denser LGUs are less poor)" if rho.statistic < 0 else
                   "density runs with poverty",
        "by_province": {E.PNAME[p]: int(n) for p, n in both.groupby("province_code").size().items()}}
    chk["lgus_with_municipal_estimate"] = int(r["poverty_lgu_estimate"].notna().sum())
    chk["lgus_with_substitute"] = int(r["poverty_lgu_estimate"].isna().sum())
    chk["ties_in_risk_index"] = int(r["risk_index"].duplicated(keep=False).sum())
    chk["version"] = version
    chk["province_probabilities"] = {"source": f"{seal_name} (sha256 {seal_sha})", "arm": "PCF21 = FINAL_T1",
                                     "target_quarter": "2026-Q4", "lead": 1, "status": "INDICATIVE ONLY (lead not validated)",
                                     "values": {E.PNAME[p]: v for p, v in probs.items()}}
    chk["sae_ingestion"] = sae_report or ("not run: the PSA municipal SAE workbook has not been supplied "
                                          "(psa.gov.ph/foi.gov.ph returned HTTP 403 to automated access in E24; "
                                          "never bypassed)")
    out = r.assign(province=r["province_code"].map(E.PNAME), ranking_quarter="2026-Q4 (sealed forecast, indicative)",
                   rank_tie_rule="competition rank on risk_index rounded to 4 dp; listing order inside ties = lgu_code",
                   method="risk = province probability x (0.6 poverty_norm + 0.4 density_norm), within-province min-max",
                   density_poverty_note=("where both exist, density runs opposite to poverty (Spearman "
                                         f"{rho.statistic:.2f}, n = {len(both)}): the 0.4 density weight pushes dense, "
                                         "less-poor LGUs up"),
                   label="Relative ordinal estimate; not an official food-insecurity measurement")
    cols = ["lgu_code", "lgu_name", "lgu_type", "province_code", "province", "population_2020", "land_area_km2", "density",
            "poverty_lgu_estimate", "poverty_value_used", "poverty_value_kind", "poverty_source", "vulnerability_index",
            "vulnerability_rank_in_province", "province_probability", "risk_index", "rank_region", "rank_in_province",
            "ranking_quarter", "rank_tie_rule", "method", "limitation", "density_poverty_note", "label"]
    out[cols].to_csv(EXP / "LGU_RANKING_VALIDATION.csv", index=False, lineterminator="\n")
    (EXP / "runs" / "lgu_validation.json").write_text(json.dumps(chk, indent=1, default=str), encoding="utf-8")
    print(json.dumps(chk, indent=1, default=str))


if __name__ == "__main__":
    main()
