"""E119-R2 validation: nothing lost, geography preserved, no pre-2021 observation, nothing trained or changed in production.

    python validate.py    (after analyze.py)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

import analyze as A
import framework as F

ROOT, E119, P, FI = A.ROOT, A.E119, A.P, A.FI
REPO = A.EXP.parent.parent
ROLES = ["forecasting_predictor", "provincial_profiling", "regional_context", "supporting_variable", "validation_only", "excluded"]


def checks() -> list[dict]:
    res = []

    def ok(name, cond, detail=""):
        res.append({"check": name, "result": "PASS" if cond else "FAIL", "detail": detail})

    ids = {d[0] for d in F.DATASETS}
    codes = [i["code"] for i in F.INDICATORS]
    inv = pd.read_csv(ROOT / "E119R2_COMPLETE_DATASET_INVENTORY.csv")
    ex = pd.read_csv(ROOT / "E119R2_EXISTING_12_INDICATOR_REVIEW.csv")
    # ---- completeness
    ok("every FIRI v2 indicator reviewed", set(ex["indicator"]) == set(FI.LABELS) and (ex["label"] == ex["indicator"].map(FI.LABELS)).all(), f"{len(ex)} of 12")
    ok("every FIRI v2 indicator assigned to a proposed indicator", ex["proposed_indicator"].isin(codes).all())
    e118 = pd.read_csv(A.EXP / "E118_FAO_Data_Discovery" / "FAO_FOOD_SECURITY_DATA_INVENTORY.csv")
    miss = sorted(set(e118["id"]) - set(F.E118_ID_TO_D))
    ok("every E118 inventory dataset mapped", not miss and all(set(v) <= ids for v in F.E118_ID_TO_D.values()), f"{len(e118)} E118 rows; unmapped: {miss}")
    tabs = {p.stem for p in A.E118C.glob("*.csv")}
    ok("every E118 acquired clean table mapped", tabs == set(F.E118_TABLE_TO_D), f"{len(tabs)} tables")
    meta = set(pd.read_csv(E119 / "out" / "feature_meta.csv")["feature"])
    ann = set(pd.read_csv(E119 / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv")["feature"])
    cols = [*pd.read_csv(E119 / "E119_REGIONAL_MODELING_DATASET.csv").columns, *pd.read_csv(E119 / "E119_PROVINCIAL_VULNERABILITY_DATASET.csv").columns]
    skip = {"origin", "t", "issue_date", "lead", "target_quarter", "target_q", "y_published", "H1_status", "H1_bl_latest_quarter", "province", "province_code",
            "A_status", "A_cpi_month"}
    e119f = meta | ann | {c for c in cols if not c.endswith(("__status", "__period")) and c not in skip}
    unm = sorted(e119f - set(F.E119_FEATURE_TO_D))
    ok("every E119 feature mapped to a dataset", not unm, f"{len(e119f)} features; unmapped: {unm}")
    ok("all mapped dataset ids exist", all(set(v.split("+")) <= ids for v in F.E119_FEATURE_TO_D.values()))
    ok("every dataset has an indicator, a role and a reason", inv["proposed_indicator"].isin(codes).all() and inv["role"].isin(ROLES).all()
       and inv["reason"].str.len().gt(20).all(), f"{len(inv)} datasets")
    ok("every proposed indicator has at least one acquired dataset", all((inv.loc[inv["proposed_indicator"] == c, "acquired"] == "yes").any() for c in codes))
    fao = pd.read_csv(ROOT / "E119R2_FAO_DIMENSION_MAPPING.csv")
    ok("all four FAO dimensions represented", all(fao[d].fillna("").ne("").any() for d in ("Availability", "Access", "Utilization", "Stability")))
    # ---- geography
    L = pd.concat([A.e119_long(), A.extra_series()])
    pu = set(L.loc[L["resolution"] == "province", "unit"])
    ok("provincial units are exactly the five provinces", pu == set(P.PROVS), str(sorted(pu)))
    ok("Quezon City and Lucena never appear as province units", not any(("Quezon City" in u or "Lucena" in u) for u in L["unit"].unique()))
    nat = L[L["resolution"].isin(["national", "region", "global/national", "region proxy"])]
    ok("national / regional values carry their own unit, never a province name", not nat["unit"].isin(P.PROVS).any())
    geo = pd.read_csv(ROOT / "E119R2_GEOGRAPHIC_AND_TEMPORAL_COVERAGE.csv")
    ok("no national/regional value copied to provinces; no annual value spread to quarters",
       not geo["national_or_regional_copied_to_provinces"].any() and not geo["annual_spread_to_quarters"].any())
    fp = inv.loc[inv["role"] == "forecasting_predictor", "dataset_id"]
    regional = {"D03", "D07", "D20", "D21", "D22", "D24", "D31", "D34", "D35", "D40", "D62", "D70"}
    ok("regional forecasting predictors all have a regional or national series", set(fp) <= regional, " ".join(fp))
    ok("no supervised provincial food-insecurity label claimed", not ((inv["proposed_indicator"] == "EH") & (inv["role"] == "forecasting_predictor")
                                                                      & inv["geography"].str.startswith("province")).any())
    # ---- time
    ok("no pre-2021 observation in any analysed series", bool((L["period"] >= P.START_Q).all()), f"min {P.qs(int(L['period'].min()))}")
    pub = ["cpi_food_yoy_pct", "cpi_headline_yoy_pct", "cpi_bottom30_food_yoy_pct"]
    chg = L[L["feature"].str.endswith(("_yoy_pct", "_drop", "_change_pp", "_decline_pct")) & ~L["feature"].isin(pub)]
    ok("computed changes start 2022-Q1 or later (2021+ base only)", bool((chg["period"] >= P.START_Q + 4).all()), f"min {P.qs(int(chg['period'].min()))}")
    qstart = pd.to_datetime(L["period"].map(lambda q: P.qstart(int(q)).isoformat()))
    ok("every value becomes available after its period starts", bool((pd.to_datetime(L["avail"]) > qstart).all()))
    # ---- nothing trained or changed
    diff = subprocess.run(["git", "status", "--porcelain", "--", "backend/app", "frontend/src", "backend/data",
                           "aipheed-backend-aligned/experiments/E118_FAO_Data_Discovery", "aipheed-backend-aligned/experiments/E119_Preprocessing"],
                          cwd=REPO, capture_output=True, text=True).stdout.strip()
    ok("production code, dashboard, E118 and E119 files unchanged", diff == "", diff[:200])
    man = json.loads((ROOT / "out" / "manifest.json").read_text())
    same = all(A.sha(Path(k) if Path(k).is_absolute() else REPO / k) == v for k, v in man["inputs_sha256"].items())
    ok("inputs read only (hashes equal before and after)", same, f"{len(man['inputs_sha256'])} files")
    src = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "runner").glob("*.py") if p.name != "validate.py")
    ok("no model fitted in this phase", not any(t in src for t in ("lightgbm", "LGBM", ".fit(", "sklearn")))
    return res


if __name__ == "__main__":
    r = checks()
    pd.DataFrame(r).to_csv(ROOT / "out" / "validation_results.csv", index=False, lineterminator="\n")
    for x in r:
        print(x["result"], x["check"], "|", x["detail"])
    assert all(x["result"] == "PASS" for x in r)
