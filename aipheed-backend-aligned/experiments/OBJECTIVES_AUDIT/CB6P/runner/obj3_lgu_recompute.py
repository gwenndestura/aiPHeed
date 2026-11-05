"""Objective 3 audit: independent recomputation of the 142 LGU indices served by the food-insecurity mode (C-B6 export,
the default data). No model is run and no file is changed; the API is called in-process against a temporary database.

    python obj3_lgu_recompute.py <scratch_dir>     # -> prints the check and writes <scratch_dir>/obj3_lgu_audit.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BACK = ROOT / "backend"
scratch = Path(sys.argv[1])
os.environ.update({"AIPHEED_MAP_MODEL": "foodinsecurity", "AIPHEED_ENABLE_SCHEDULER": "0", "AIPHEED_STRICT_MODEL": "1",
                   "AIPHEED_LEAD2_MODEL": "thesis",
                   "DATABASE_URL": "sqlite+aiosqlite:///" + str(scratch / "obj3_audit.db").replace("\\", "/")})
os.environ.pop("AIPHEED_FI_DATA_DIR", None)
os.chdir(BACK)
sys.path.insert(0, str(BACK))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.database import Base  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

_db = scratch / "obj3_audit.db"
if _db.exists():
    _db.unlink()
Base.metadata.create_all(create_engine("sqlite:///" + str(_db).replace("\\", "/")))

PROV = {"cavite": "PH040100000", "laguna": "PH040200000", "quezon": "PH040300000", "rizal": "PH040400000",
        "batangas": "PH040500000"}

with TestClient(app) as c:
    quarter = c.get("/api/v1/config").json()["servingModel"]["targetQuarter"]
    model = c.get("/api/v1/config").json()["servingModel"]["model"]
    api = []
    for slug in PROV:
        r = c.get(f"/api/v1/provinces/{slug}/municipalities", params={"quarter": quarter})
        r.raise_for_status()
        body = r.json()
        api += [{**x, "slug": slug} for x in (body.get("data") or body.get("municipalities") or [])]
A = pd.DataFrame(api)

rows = pd.read_csv(BACK / "data" / "foodinsecurity_engine_cb6" / "rows.csv", dtype={"province_code": str})
rq = rows[rows["quarter"] == quarter].set_index("province_code")
vul = pd.read_csv(BACK / "data" / "foodinsecurity_engine_cb6" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
vul["density"] = vul["population_2024"] / vul["land_area_km2"]
mm = lambda s: (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0  # noqa: E731
vul["pov_n"] = vul.groupby("province")["poverty_value_used"].transform(mm)
vul["den_n"] = vul.groupby("province")["density"].transform(mm)
vul["vuln"] = 0.6 * vul["pov_n"] + 0.4 * vul["den_n"]
name2code = {"Batangas": "PH040500000", "Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000",
             "Rizal": "PH040400000"}
vul["pc"] = vul["province"].map(name2code)
vul["idx_score"] = (vul["pc"].map(rq["score"]).astype(float) * vul["vuln"]).clip(0, 1).round(4)
vul["idx_prob"] = (vul["pc"].map(rq["probability"]).astype(float) * vul["vuln"]).clip(0, 1).round(4)
vul["code9"] = vul["lgu_code"].str.zfill(9)
A["code9"] = A["lguCode"].astype(str).str.zfill(9)
J = A.merge(vul, on="code9", how="left")
out = {
    "model_served": model, "quarter": quarter, "lgus_returned": int(len(A)), "lgus_matched_to_inputs": int(J["vuln"].notna().sum()),
    "max_abs_diff_vs_score_times_vulnerability": float((J["riskIndex"] - J["idx_score"]).abs().max()),
    "max_abs_diff_vs_regional_probability_times_vulnerability": float((J["riskIndex"] - J["idx_prob"]).abs().max()),
    "province_score_check_max_abs_diff": float((rq["score"] - rq["probability"] * rq["pov_weight"]).abs().max()),
    "pov_weight_check_max_abs_diff": float((rq["pov_weight"] - rq["pov_families_2023"] / rq["pov_families_2023"].max()).abs().max()),
    "lgus_per_province": A["slug"].value_counts().to_dict(),
    "missing_inputs": int(vul[["poverty_value_used", "population_2024", "land_area_km2"]].isna().sum().sum()),
    "low_precision_poverty_cv_gt_20": int((vul["poverty_cv"] > 20).sum()),
    "risk_level_values": A["riskLevel"].value_counts(dropna=False).to_dict(),
    "largest_differences": J.assign(d=(J["riskIndex"] - J["idx_score"]).abs()).nlargest(6, "d")[
        ["lgu_name_y", "province", "riskIndex", "idx_score", "d", "poverty_lgu_estimate", "poverty_value_used",
         "povertyRate"]].to_dict("records") if "lgu_name_y" in J else
    J.assign(d=(J["riskIndex"] - J["idx_score"]).abs()).nlargest(6, "d")[
        ["lgu_name", "province", "riskIndex", "idx_score", "d", "poverty_lgu_estimate", "poverty_value_used"]].to_dict("records"),
    "lgus_differing_gt_1e-4": int(((J["riskIndex"] - J["idx_score"]).abs() > 1e-4).sum()),
    "rank_in_province_consistent": bool(all(
        (g.sort_values("rankInProvince")["riskIndex"].diff().dropna() <= 1e-12).all() for _, g in A.groupby("slug"))),
}
(scratch / "obj3_lgu_audit.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps(out, indent=1, default=str))
