"""E45 model diagnostics (no new candidate, no selection): error cases of the E44 final candidate I2, temporal
windows, provinces, and missing-trigger sensitivity of the 2027-Q1 forecast.

    backend/venv/Scripts/python.exe -B aipheed-backend-aligned/experiments/E45_News_Map_Fix/e45_model_diagnostics.py
      -> evidence/model_diagnostics.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E44 = HERE.parent / "E44_Five_Trigger_Optimization"
sys.path.insert(0, str(E44 / "runner"))
import e44_components as P2  # noqa: E402

C, K, L, np, pd = P2.C, P2.K, P2.L, P2.np, P2.pd
RUN1 = E44 / "runs" / "20261015T150213Z"


def acc_block(g, arm):
    y, yh, p = g["y"].astype(int), g[f"{arm}_yhat"].astype(int), g[f"{arm}_p"]
    rh = float(((yh == 1) & (y == 1)).sum() / max(y.sum(), 1)) if y.sum() else None
    rl = float(((yh == 0) & (y == 0)).sum() / max((y == 0).sum(), 1)) if (y == 0).sum() else None
    return {"rows": int(len(g)), "HIGH": int(y.sum()), "accuracy": round(float((yh == y).mean()), 3),
            "recall_HIGH": None if rh is None else round(rh, 3), "recall_LOW": None if rl is None else round(rl, 3),
            "brier": round(float(((p - y) ** 2).mean()), 3)}


def main():
    d, x = L.load(), K.load_extra()
    P = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})
    for a in ("B-maj", "B-persist", "SIM-0", "E41-M1"):
        P[f"{a}_yhat"] = (P[f"{a}_p"] >= 0.5).astype(float)
    S = P[P["y"].notna() & P["I2_p"].notna() & (P["target_q"] <= L.qi("2026-Q3"))].copy()
    labs = K.label_frame(d, "T43").rename(columns={"q": "target_q"})
    S = S.merge(labs[["province_code", "target_q", "signals", "H", "F"]], on=["province_code", "target_q"], how="left")
    th = L.e40_spec()
    errors = []
    for r in S.itertuples():
        if int(r.I2_yhat) == int(r.y):
            continue
        errors.append({"target": L.qs(int(r.target_q)), "province": L.NAMES[r.province_code], "observed": int(r.y),
                       "predicted": int(r.I2_yhat), "p": round(float(r.I2_p), 3),
                       "p_hunger": round(float(r.I2_p_hunger), 3), "p_price": round(float(r.I2_p_price), 3),
                       "food_forecast": round(float(r.I2_F_hat), 2), "food_observed": round(float(r.F), 2),
                       "food_reference_p60": round(th["food"][r.province_code], 2), "H_observed": float(r.H),
                       "signals_observed": int(r.signals)})
    err = pd.DataFrame(errors)
    windows = {"2024-Q2..2025-Q1": (L.qi("2024-Q2"), L.qi("2025-Q1")), "2025-Q4..2026-Q3": (L.qi("2025-Q4"), L.qi("2026-Q3"))}
    win = {w: {a: acc_block(S[(S["target_q"] >= lo) & (S["target_q"] <= hi)], a)
               for a in ("I2", "B-maj", "B-persist", "SIM-0", "E41-M1")} for w, (lo, hi) in windows.items()}
    prov = {L.NAMES[p]: acc_block(g, "I2") for p, g in S.groupby("province_code")}

    # missing-trigger sensitivity of the 2027-Q1 forecast (same refit as the served record)
    t = L.qi("2026-Q3")
    origins = list(range(L.qi("2021-Q3"), t + 1))
    X = P2.features(d, x, origins)
    B = P2.bases(d, origins)
    f = P2.forecast(d, X, B, t, n_jobs=8)
    from scipy.stats import norm
    mult = f["price_cfg"]["mult"]
    HL = f["te"][f"hl_{mult}"].to_numpy()

    def p_raw(te, hte):
        F_hat = te[f"base_{mult}"].to_numpy() + f["price_model"].predict(te)
        H_hat = float(hte["H_base"].iloc[0] + f["hunger_model"].predict(hte)[0]) if f["hunger_model"] is not None else float(hte["H_base"].iloc[0])
        ph = 1 - norm.cdf((th["H"] - H_hat) / max(f["hunger_rmse"], 1e-6))
        return ph * P2.p_price(F_hat, HL, f["price_rmse"], te["province_code"])

    base = p_raw(f["te"], f["hte"])
    sens = {}
    for g in ("market", "climate", "fish_kill", "employment", "ofw_remittance", "news"):
        te, hte = f["te"].copy(), f["hte"].copy()
        te[[c for c in P2.PRICE_GROUPS[g] if c in te]] = np.nan
        hcols = [c for c in P2.HUNGER_GROUPS.get(g, []) if c in hte]
        hte[hcols] = np.nan
        pm = p_raw(te, hte)
        sens[g] = {L.NAMES[p]: round(float(pm[i] - base[i]), 4) for i, p in enumerate(L.PROVS)}
    out = {"S44_rows": int(len(S)), "errors": errors,
           "error_summary": {"false_positive": int((err["predicted"] == 1).sum()) if len(err) else 0,
                             "false_negative": int((err["predicted"] == 0).sum()) if len(err) else 0,
                             "fp_food_observed_below_reference": int(((err["predicted"] == 1) & (err["food_observed"] < err["food_reference_p60"])).sum()) if len(err) else 0},
           "temporal_windows": win, "by_province_I2": prov,
           "missing_trigger_sensitivity_raw_p_2027Q1": sens,
           "note": "Diagnostics of the pre-declared final candidate only; nothing here selects or tunes a model."}
    (HERE / "evidence").mkdir(exist_ok=True)
    (HERE / "evidence" / "model_diagnostics.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "errors"}, indent=1, default=float))
    print(err.to_string(index=False))


if __name__ == "__main__":
    main()
