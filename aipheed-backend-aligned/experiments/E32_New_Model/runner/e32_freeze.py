"""E32 final test, part 1: retrain every arm at the operational origin O(2026-Q3) = 2026-10-01 on all eligible history
and FREEZE its predictions for 2026-Q4 (lead 1) and 2027-Q1 (lead 2) before either outcome exists.

Saved: models/E32-PCFN_O2026-10-01.json (parameters, feature definitions, training configuration, dataset version),
models/E32-LR_*.joblib, models/E32-LGBM_*.txt, frozen/E32_PROSPECTIVE.json (+ .sha256). Score later with
runner/e32_score_prospective.py once the SWS December 2026 round and the October-December 2026 CPI are released.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e32_common as C  # noqa: E402
import e32_lib as L  # noqa: E402

np, pd = C.np, C.pd
T = C.qk("2026-Q3")
MODELS, FROZEN = C.E32 / "models", C.E32 / "frozen"


def save_artifacts(d: "L.Data", k: int) -> dict:
    import joblib
    import lightgbm as lgb
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    MODELS.mkdir(exist_ok=True)
    tr = d.training_pairs(T, k)
    X, y = L._xy(tr)
    sc = StandardScaler().fit(X)
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X), y)
    joblib.dump({"scaler": sc, "model": lr, "features": L.FEATURES}, MODELS / f"E32-LR_O2026-10-01_lead{k}.joblib")
    gb = lgb.LGBMClassifier(**L.LGBM_PARAMS).fit(pd.DataFrame(X, columns=L.FEATURES), y)
    gb.booster_.save_model(str(MODELS / f"E32-LGBM_O2026-10-01_lead{k}.txt"))
    return {"training_rows": int(len(y)), "training_HIGH_share": float(y.mean()),
            "training_target_quarters": sorted(set(tr.dropna(subset=["D_last", "Dnow", "y_last"])["target_q"].map(C.qs))),
            "LR_coefficients_standardized": dict(zip(L.FEATURES, map(float, lr.coef_[0]))),
            "LR_intercept": float(lr.intercept_[0])}


def main():
    d = L.Data()
    o = L.origin(T)
    out = {"record": "E32 prospective forecasts (final test), frozen before the outcomes exist",
           "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "origin": str(o.date()), "information_cutoff": "2026-09-30T23:59:59+08:00",
           "protocol_sha256": (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0],
           "selected_model": "E32-PCFN (PROTOCOL section 5); not served: acceptance A1/A2 failed on development data",
           "inputs": C.inputs_manifest(), "rice_sha256": C.sha(L.RICE), "leads": {}}
    pcfn_card = {"model_id": "E32-PCFN", "version": "E32.1-candidate", "origin": str(o.date()),
                 "definition": "PCF21 local-level H filter + news shift beta*(news_reg - mean); D = OLS(no intercept) "
                               "of D(t+k) on [D_last, Dnow, rice_rel, news_n]; P = 1 - Phi((tau - (mu_H + 2 mu_D)) / "
                               "sqrt(V_H + 4 sigma_D^2))",
                 "feature_definitions": {
                     "H_last": "mean Balance Luzon hunger of the latest quarter whose rounds were posted before the origin",
                     "D_last": "province food YoY minus five-province mean, quarter t-1 (PSA)",
                     "Dnow": "same, months 1-2 of quarter t", "rice_rel": "province rice CPI YoY minus five-province mean, months 1-2 of t",
                     "news_n": "log1p(validated R1.1 articles, province, quarter t)",
                     "news_reg": "log1p(validated R1.1 articles, five provinces, quarter t)"},
                 "dataset_version": C.inputs_manifest(), "leads": {}}
    for k in (1, 2):
        info = {}
        arms = {"E32-PCFN": L.pcfn(d, T, k, info), "E32-LR": L.lr(d, T, k), "E32-LGBM": L.lgbm(d, T, k),
                "E32-ENS": L.ens(d, T, k), "PCF21": L.pcf21(d, T, k), **L.references(d, T, k)}
        X = d.features(T, k)
        out["leads"][str(k)] = {"target_quarter": C.qs(T + k), "tau": d.tau(T),
                                "H_last_quarter": X["H_last_quarter"].iloc[0],
                                "last_label_quarter": X["last_label_quarter"].iloc[0],
                                "news_evidence_quarter": C.qs(T),
                                "features": C.clean(X.drop(columns=["H_last_quarter", "last_label_quarter"]).to_dict("records")),
                                "arms_p_high": {a: {p: float(v[p]) for p in C.PROVS} for a, v in arms.items()}}
        pcfn_card["leads"][str(k)] = {**C.clean(info), "artifacts": save_artifacts(d, k)}
    (MODELS / "E32-PCFN_O2026-10-01.json").write_bytes(json.dumps(C.clean(pcfn_card), indent=1).encode())
    body = json.dumps(C.clean(out), indent=1).encode("utf-8")
    FROZEN.mkdir(exist_ok=True)
    (FROZEN / "E32_PROSPECTIVE.json").write_bytes(body)
    h = hashlib.sha256(body).hexdigest()
    (FROZEN / "E32_PROSPECTIVE.sha256").write_bytes(f"{h}  E32_PROSPECTIVE.json\n".encode())
    print(h)
    for k, blk in out["leads"].items():
        print(blk["target_quarter"], "tau", round(blk["tau"], 3), "H_last", blk["H_last_quarter"],
              {a: {C.NAMES[p][:3]: round(v, 3) for p, v in pr.items()} for a, pr in blk["arms_p_high"].items()
               if a in ("E32-PCFN", "E32-ENS", "PCF21", "B1")})


if __name__ == "__main__":
    main()
