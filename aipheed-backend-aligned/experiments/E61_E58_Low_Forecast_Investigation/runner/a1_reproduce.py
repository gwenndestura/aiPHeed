"""E61 A1: reproduce the served E58 2027-Q1 forecast four independent ways and decompose it.

  (1) served   : the backend API with AIPHEED_LEAD2_MODEL=e58 (exact production-serving code path)
  (2) artifacts: backend/data/e56/model alone (booster text, offset and hunger parameters, feature rows), computed here
                 with an independent implementation of the documented formula
  (3) frozen   : E56 frozen prospective file (sealed 2026-10-18)
  (4) retrain  : the E56 training procedure re-run at origin 2026-Q3 from the raw inputs (e56_lib.tuned_forecast)
Then: the decomposition logit P_price = projection offset + trees, the inputs with their observation periods, and a
DIAGNOSTIC (not a forecast) of the projection under the other drift multipliers in E56's search space.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/a1_reproduce.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_lib as X  # noqa: E402

np, pd, L, F, G, E = X.np, X.pd, X.L, X.F, X.G, X.E


def served() -> dict:
    os.environ["AIPHEED_LEAD2_MODEL"] = "e58"
    os.environ["AIPHEED_NOW"] = "2026-10-19T09:00:00"
    sys.path.insert(0, str(X.BACKEND))
    os.chdir(X.BACKEND)
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    prov = c.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()
    reg = c.get("/api/v1/forecast?scope=region&id=calabarzon&quarter=2027-Q1&horizon=nowcast").json()
    out = {"provinces": {r["id"]: r["riskScore"] for r in prov["data"]}, "region": reg.get("riskScore", reg),
           "indicator": prov["indicator"], "summaries": {}}
    for slug in ("cavite", "laguna", "quezon", "rizal", "batangas"):
        e = c.get(f"/api/v1/explainability?scope=province&id={slug}&quarter=2027-Q1").json()
        out["summaries"][slug] = {"probability": e["summary"]["probability"], "sentence": e["summary"]["sentence"],
                                  "riskScore": e["riskScore"]}
    return out


def from_artifacts() -> dict:
    import lightgbm as lgb
    from scipy.stats import multivariate_normal, norm
    off = json.loads((X.ART / "offset.json").read_text())
    hun = json.loads((X.ART / "hunger.json").read_text())
    schema = [f["name"] for f in json.loads((X.ART / "feature_schema.json").read_text())["features"]]
    rows = pd.read_csv(X.ART / "features_2027Q1.csv", dtype={"province_code": str})
    bst = lgb.Booster(model_str=(X.ART / "booster.txt").read_text(encoding="utf-8").replace("\r\n", "\n"))
    h_hat = hun["H_base"] + hun["intercept"] + sum(hun["z_row"][k] * hun["coef"][k] for k in hun["coef"])
    p_h = 1 - norm.cdf((hun["threshold_H"] - h_hat) / hun["rmse"])
    hunger_terms = {k: hun["z_row"][k] * hun["coef"][k] for k in hun["coef"]}
    m, rho = off["drift_multiplier"], off["error_correlation"]
    bvn = multivariate_normal(mean=[0, 0], cov=[[1, rho], [rho, 1]])
    raw = bst.predict(rows[schema].astype(float), raw_score=True)
    out = {"H_hat": h_hat, "p_hunger": p_h, "hunger_terms": hunger_terms, "provinces": {}}
    for i, r in rows.iterrows():
        code = r["province_code"]
        zf = (off["threshold_food"][code] - r[f"base_{m}"]) / off["food_rmse"]
        zg = (off["threshold_gap"][code] - r[f"gbase_{m}"]) / off["gap_rmse"]
        ps = min(max(1 - float(bvn.cdf([zf, zg])), 1e-12), 1 - 1e-12)
        init = float(np.clip(math.log(ps / (1 - ps)), -off["logit_clip"], off["logit_clip"]))
        trees = float(raw[i] - off["tree_mean_constant"])
        pp = 1 / (1 + math.exp(-(init + trees)))
        out["provinces"][code] = {
            "name": L.NAMES[code], "projected_food_yoy": float(r[f"base_{m}"]), "projected_gap": float(r[f"gbase_{m}"]),
            "threshold_food": off["threshold_food"][code], "threshold_gap": off["threshold_gap"][code],
            "z_food": zf, "z_gap": zg, "p_projection_only": ps, "logit_projection": init, "logit_trees": trees,
            "p_price": pp, "p_final": p_h * pp,
            "inputs": {k: (None if pd.isna(r[k]) else float(r[k])) for k in schema}}
    out["offset"] = {k: v for k, v in off.items() if not k.startswith("threshold")}
    return out


def frozen() -> dict:
    f = json.loads(X.E56_FROZEN.read_text())
    return {"sha256": X.sha(X.E56_FROZEN), "issued": f.get("issueDate") or f.get("origin"),
            "forecasts": {k: v["p"] for k, v in f["forecasts"].items()}}


def retrain() -> dict:
    d, Xf, B = E.load()
    t = L.qi("2026-Q3")
    fx = G.tuned_forecast(d, Xf, B, t, G.search_space())
    tr, te = F.frame(d, Xf, B, t, "AS")
    fit = tr.dropna(subset=["F_true", "G_true"])
    diag = {}
    for m in (0.0, 0.5, 1.0):        # projection under each drift multiplier of the search space (diagnostic only)
        f_m = fit.dropna(subset=[f"base_{m}", f"gbase_{m}"])
        sc = F.struct_scale(f_m, m)
        p = F._sig(F.struct_logit(te, m, sc))
        bias_F = float((f_m["F_true"] - f_m[f"base_{m}"]).mean())
        bias_G = float((f_m["G_true"] - f_m[f"gbase_{m}"]).mean())
        diag[str(m)] = {"p_projection_only": dict(zip(L.PROVS, map(float, p))),
                        "projected_food_yoy": dict(zip(L.PROVS, map(float, te[f"base_{m}"]))),
                        "projected_gap": dict(zip(L.PROVS, map(float, te[f"gbase_{m}"]))),
                        "train_rmse_food_gap_rho": sc, "train_mean_error_food": bias_F, "train_mean_error_gap": bias_G,
                        "n_train_rows": int(len(f_m))}
    cut = d.cut(t)
    Fq = L.quarter_F(cut).set_index(["province_code", "q"])["F"]
    Hq = L.quarter_F(cut, "all_items").set_index(["province_code", "q"])["F"]
    hist = {L.NAMES[p]: {L.qs(q): {"food_yoy": round(float(Fq[(p, q)]), 2), "gap": round(float(Fq[(p, q)] - Hq[(p, q)]), 2)}
                         for q in range(t - 5, t) if (p, q) in Fq.index} for p in L.PROVS}
    return {"config": fx["cfg"], "p": dict(zip(L.PROVS, map(float, fx["p"]))),
            "p_price": dict(zip(L.PROVS, map(float, fx["p_price"]))), "p_hunger": float(fx["p_hunger"]),
            "H_hat": float(fx["H_hat"]), "n_train_rows": fx["n_train_rows"], "n_train_HIGH_PS": fx["n_train_HIGH"],
            "drift_diagnostic": diag, "quarterly_food_yoy_and_gap_known_at_issue": hist,
            "latest_cpi_month_used": L.ym_s(L.m0_of(t)), "sws_rounds_used": cut.sws.assign(q=cut.sws["q"].map(L.qs))
            .tail(4).astype(str).to_dict("records")}


def main():
    seals = X.verify_sealed()
    a = from_artifacts()
    fz = frozen()
    rt = retrain()
    sv = served()
    rec = json.loads(X.E58_RECORD.read_text(encoding="utf-8"))
    slug = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
            "PH040500000": "batangas"}
    table, maxdiff = [], 0.0
    for code, v in a["provinces"].items():
        r = {"province": v["name"], "served_api": sv["provinces"][slug[code]],
             "served_summary": sv["summaries"][slug[code]]["probability"],
             "record": rec["provinces"][code]["forecast"]["probability"], "artifacts": v["p_final"],
             "frozen_E56": fz["forecasts"][code], "retrained": rt["p"][code],
             "p_hunger": a["p_hunger"], "p_price": v["p_price"], "p_projection_only": v["p_projection_only"],
             "logit_projection": v["logit_projection"], "logit_trees": v["logit_trees"],
             "projected_food_yoy": v["projected_food_yoy"], "threshold_food": v["threshold_food"],
             "projected_gap": v["projected_gap"], "threshold_gap": v["threshold_gap"]}
        maxdiff = max(maxdiff, *(abs(r[k] - r["artifacts"]) for k in ("served_api", "record", "frozen_E56", "retrained")))
        maxdiff = max(maxdiff, abs(round(r["served_summary"], 4) - round(r["artifacts"], 4)))
        table.append(r)
    T = pd.DataFrame(table)
    X.write_csv(T, X.TABLES / "a1_reproduction_2027Q1.csv")
    region_mean = float(np.mean([r["artifacts"] for r in table]))
    X.dump({"sealed_inputs_verified": seals, "max_abs_difference_between_paths": maxdiff,
            "region_served": sv["region"], "region_mean_of_provinces": region_mean,
            "artifacts": a, "frozen": fz, "retrain": rt, "served": sv,
            "record_dataFreshness": rec["dataFreshness"], "record_issue": rec["origin"],
            "record_model": rec["modelVersion"] if "modelVersion" in rec else None}, X.OUT / "a1_reproduce.json")
    print(T.round(4).to_string())
    print("max abs difference between paths:", maxdiff, "| region served", sv["region"], "mean", round(region_mean, 4))
    print("H_hat", round(a["H_hat"], 2), "p_hunger", round(a["p_hunger"], 4), "retrain cfg", rt["config"]["id"])
    for m, v in rt["drift_diagnostic"].items():
        print("m", m, {L.NAMES[k]: round(x, 3) for k, x in v["p_projection_only"].items()},
              "train mean err food", round(v["train_mean_error_food"], 2), "gap", round(v["train_mean_error_gap"], 2))


if __name__ == "__main__":
    main()
