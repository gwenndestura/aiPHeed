"""
scripts/build_cb6_seed.py
-------------------------
ONE-TIME development step: copy what the quarterly job needs out of aipheed-backend-aligned/experiments (outside the
Docker build context) into backend/data/cb6_auto/seed/. Values are copied unchanged; rows for other areas are dropped only
where the C-B6 regional inputs never read them.

    cd backend && python -m scripts.build_cb6_seed
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
EXP = BACKEND.parent / "aipheed-backend-aligned" / "experiments"
SEED = BACKEND / "data" / "cb6_auto" / "seed"
REGION = "PH040000000"
HR = EXP / "HISTORY_RETRAIN" / "data"
LONG = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "long"
OA = EXP / "OBJECTIVES_AUDIT"


def main() -> int:
    SEED.mkdir(parents=True, exist_ok=True)
    for f in ("cpi_backcast_ACP28.csv", "cpi_ACP22.csv", "palay_corn_EVCP0.csv", "fisheries_GVFP1.csv"):
        d = pd.read_csv(HR / f, dtype={"geo_code": str})
        d[d["geo_code"] == REGION].to_csv(SEED / f, index=False)
    c = pd.read_csv(LONG / "cov_cpi.csv")
    r = c[(c["geolocation"] == "Region IV-A (CALABARZON)") & c["commodity_description"].str.contains("Rice")]
    r[["year", "month", "ym", "value"]].to_csv(SEED / "cpi_rice_region.csv", index=False)
    shutil.copyfile(LONG / "sws_area_rounds_full.csv", SEED / "sws_area_rounds_full.csv")
    shutil.copyfile(LONG / "cov_oni.csv", SEED / "cov_oni.csv")
    shutil.copyfile(HR / "pinksheet_monthly_1960.csv", SEED / "pinksheet_monthly_1960.csv")
    shutil.copyfile(HR / "typhoons_province_quarter.csv", SEED / "typhoons_province_quarter.csv")
    shutil.copyfile(EXP / "LEAD2_RELIABILITY_RESEARCH" / "y12_domestic_rice_supply" / "data_acquired" /
                    "tidy_stocks_national.csv", SEED / "tidy_stocks_national.csv")

    # the stored table and news anomaly: N1R history for the anomaly window, and the reference for the parity test
    T = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "table_pooled.csv", dtype={"area": str})
    T = T[(T["area"] == "BL") & T["lead"].isin([1, 2])]
    z = pd.read_csv(EXP / "NEW_MODEL" / "NEWS_V2" / "out" / "news_anomalies.csv")[["t", "z_N1R"]]
    st = pd.read_csv(OA / "out" / "ce6_features.csv")
    ref = T.merge(z, on="t", how="left").merge(st, on="t", how="left")
    cols = ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L", "R_food_yoy", "R_head_yoy", "R_rice_yoy", "R_food_mom",
            "ONI_last", "ONI_max12", "tc_mean", "R_C3", "R_C4", "W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy",
            "W_urea_yoy", "z_N1R", "lead", "ST1", "ST2"]
    ref[["t", "q", "sws_newest_published"] + cols].sort_values(["t", "lead"]).to_csv(SEED / "parity_reference.csv", index=False)
    T[T["lead"] == 1][["t", "N1R"]].sort_values("t").to_csv(SEED / "n1r_history.csv", index=False)

    F = pd.read_csv(OA / "out" / "cb6_fits.csv")
    F = F[(F["name"] == "C-B6") & F["lead"].isin([1, 2])]
    F[["t", "lead", "q", "p", "fallback"] + [c for c in F.columns if c.startswith("shap_")]].to_csv(
        SEED / "shap_history.csv", index=False)

    sys.path.insert(0, str(EXP / "FIRI_V2_DATA_AUDIT" / "runner"))
    import typhoons as TY

    cen = {TY.PROVS[n]: list(v) for n, v in TY.centroids().items()}
    (SEED / "province_centroids.json").write_text(json.dumps(cen, indent=1), encoding="utf-8", newline="\n")

    man = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
           for p in sorted(SEED.iterdir()) if p.name != "seed_manifest.json"}
    (SEED / "seed_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: v["bytes"] for k, v in man.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
