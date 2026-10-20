"""Objective 3 audit, in-process (FastAPI TestClient) against the thesis-mode backend of final-system-v2.

Recomputes every LGU index from data/inputs/lgu_vulnerability.csv and the served province estimate, checks
completeness, finiteness, ranks, map ids, the province estimate's agreement with FIRI v2 history, the display band,
and the PDF / report-data numbers. Run with cwd = backend and the thesis env vars set.
"""
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, ".")
from app.main import app  # noqa: E402

OUT = Path(sys.argv[1])
FRONT = Path("../frontend/public/calabarzon-municities.json")
c = TestClient(app)
res = {}


def get(url):
    r = c.get(url)
    assert r.status_code == 200, (url, r.status_code, r.text[:300])
    return r.json()


cfg = get("/api/v1/config")
res["servingModel"] = cfg["servingModel"]
vul = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
vul["lgu_code"] = vul["lgu_code"].str.zfill(9)
vul["density"] = vul["population_2024"] / vul["land_area_km2"]
for col in ("poverty_value_used", "density"):
    g = vul.groupby("province")[col]
    vul[col + "_n"] = (vul[col] - g.transform("min")) / (g.transform("max") - g.transform("min"))
vul["vul"] = 0.6 * vul["poverty_value_used_n"] + 0.4 * vul["density_n"]
geo = json.loads(FRONT.read_text(encoding="utf-8"))
geo_ids = {f["properties"]["id"] for f in geo["features"]}
hist = pd.read_csv("data/thesis/firi2_history.csv", dtype={"province_code": str})

for q in ("2027-Q1", "2026-Q3", "2025-Q2"):
    prov = get(f"/api/v1/provinces?quarter={q}")["data"]
    rows = []
    for p in prov:
        rows += get(f"/api/v1/provinces/{p['id']}/municipalities?quarter={q}")["data"]
    M = pd.DataFrame(rows)
    M = M.merge(vul[["lgu_code", "vul", "province", "poverty_lgu_estimate"]], left_on="lguCode", right_on="lgu_code", how="left")
    pscore = {p["id"]: p["riskScore"] for p in prov}
    M["prov_served"] = M["provinceId"].map(pscore)
    M["idx_recomputed"] = np.clip(M["provinceEstimate"].astype(float) * M["vul"], 0, 1)
    ranks_ok = True
    for pid, g in M.groupby("provinceId"):
        g = g.sort_values("rankInProvince")
        ranks_ok &= bool((np.diff(g["riskIndex"].astype(float).to_numpy()) <= 1e-9).all())
    hq = hist[hist["target"] == q].set_index("province_code")["FIRI"]
    code_of = {"cavite": "PH040100000", "laguna": "PH040200000", "quezon": "PH040300000", "rizal": "PH040400000",
               "batangas": "PH040500000"}
    res[q] = {
        "province_scores_served": pscore,
        "province_levels": {p["id"]: p.get("riskLevel") for p in prov},
        "firi2_history": {k: (None if code_of[k] not in hq.index or pd.isna(hq.get(code_of[k])) else round(float(hq[code_of[k]]), 6)) for k in code_of},
        "n_lgus": len(M), "unique_ids": int(M["id"].nunique()), "unique_codes": int(M["lguCode"].nunique()),
        "per_province": M.groupby("provinceId").size().to_dict(),
        "all_finite": bool(M["riskIndex"].apply(lambda v: v is not None and math.isfinite(v)).all()),
        "in_vulnerability_file": int(M["vul"].notna().sum()),
        "ids_in_map_geojson": int(M["id"].isin(geo_ids).sum()), "geojson_features": len(geo_ids),
        "max_abs_index_minus_recomputed": float((M["riskIndex"].astype(float) - M["idx_recomputed"]).abs().max()),
        "max_abs_provEstimate_minus_served": float((M["provinceEstimate"].astype(float) - M["prov_served"].astype(float)).abs().max()),
        "ranks_monotone_within_province": ranks_ok,
        "lgus_index_zero": int((M["riskIndex"].astype(float) == 0).sum()),
        "lgu_band_high": int((M["riskLevel"] == "high").sum()),
        "lgu_band_high_by_province": M[M["riskLevel"] == "high"].groupby("provinceId").size().to_dict(),
        "provinces_high": int(sum(1 for p in prov if p.get("riskLevel") == "high")),
        "substitute_poverty_lgus": M.loc[M["poverty_lgu_estimate"].isna(), "name"].tolist(),
        "labels_say_relative": bool(M["disaggregationLabel"].str.contains("relative", case=False).all()),
        "spearman_index_vs_vul_within_province_min": float(min(g["riskIndex"].rank().corr(g["vul"].rank()) for _, g in M.groupby("provinceId"))),
    }
    print(q, json.dumps(res[q]), flush=True)

# PDF and report data agree with the API?
try:
    from pdfminer.high_level import extract_text
    r = c.get("/api/v1/report?scope=region&id=calabarzon&quarter=2027-Q1")
    res["pdf_region_status"] = r.status_code
    if r.status_code == 200:
        txt = extract_text(io.BytesIO(r.content))
        (OUT.parent / "region_report_2027Q1.txt").write_text(txt, encoding="utf-8")
        pscore = res["2027-Q1"]["province_scores_served"]
        res["pdf_contains_province_scores"] = {k: (f"{v:.2f}" in txt) for k, v in pscore.items()}
        res["pdf_mentions"] = {w: (w.lower() in txt.lower()) for w in ("FIRI", "not a probability", "relative prioritization",
                                                                      "not validated", "75%", "SHAP")}
    r = c.get("/api/v1/report?scope=province&id=batangas&quarter=2027-Q1")
    res["pdf_province_status"] = r.status_code
    if r.status_code == 200:
        txt = extract_text(io.BytesIO(r.content))
        (OUT.parent / "batangas_report_2027Q1.txt").write_text(txt, encoding="utf-8")
        mb = get("/api/v1/provinces/batangas/municipalities?quarter=2027-Q1")["data"]
        res["pdf_batangas_lgu_values_found"] = int(sum(1 for m in mb if f"{m['riskIndex']:.2f}" in txt))
        res["pdf_batangas_lgus"] = len(mb)
except Exception as e:  # noqa: BLE001
    res["pdf_error"] = repr(e)
OUT.write_text(json.dumps(res, indent=1, default=str))
print("PDF", {k: v for k, v in res.items() if k.startswith("pdf")})
