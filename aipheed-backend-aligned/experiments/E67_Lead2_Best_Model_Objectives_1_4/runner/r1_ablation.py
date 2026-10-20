"""E67 r1 (PROTOCOL 2, 3): five-trigger-group ablation of the E56-TUNED procedure at Lead-2, A0 reproduction of the
sealed E57 forecasts, per-group TreeSHAP / splits, and the D-E66-5 typhoon sensitivity at the 2027-Q1 origin.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E67_Lead2_Best_Model_Objectives_1_4/runner/r1_ablation.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e67_lib as K  # noqa: E402

H, L, E, np, pd = K.H, K.L, K.E, K.np, K.pd


def main():
    K.verify_protocol()
    H.verify_sealed()
    d, X, B = E.load()
    S = pd.read_csv(H.SEALED["E57"], dtype={"province_code": str})
    rows, attr = [], []
    for arm, drop in K.ARMS.items():
        t0 = time.time()
        for t in K.EVAL_ORIGINS + K.FORWARD_ORIGINS:
            r = K.tuned_forecast(d, X, B, t, drop)
            if r is None:
                raise SystemExit(f"{arm} origin {L.qs(t)} not eligible")
            assert list(r["te"]["province_code"]) == list(L.PROVS)
            for i, p in enumerate(L.PROVS):
                rows.append({"arm": arm, "t": t, "origin_quarter": L.qs(t), "target": L.qs(t + 2), "province_code": p,
                             "p": float(r["p"][i]), "p_price": float(r["p_price"][i]), "p_hunger": float(r["p_hunger"]),
                             "config": int(r["cfg"]["id"]), "feat": r["cfg"]["feat"], "n_cols": len(r["cols"])})
            if arm == "A0":
                for g, v in K.group_attribution(r).items():
                    attr.append({"origin_quarter": L.qs(t), "target": L.qs(t + 2), "config": int(r["cfg"]["id"]),
                                 "group": g, **v})
        print(arm, f"{time.time() - t0:.0f}s", flush=True)
    R = pd.DataFrame(rows)
    a0 = R[R["arm"] == "A0"].merge(S[["t", "province_code", "E56_p", "E56_p_price"]], on=["t", "province_code"])
    err = float((a0["p"] - a0["E56_p"]).abs().max())
    print("A0 vs sealed E57 max abs diff", err, "rows", len(a0))
    if len(a0) != 50 or err > 1e-9:
        raise SystemExit("A0 does not reproduce the sealed E57 forecasts")
    # D-E66-5 sensitivity: the incomplete 2026-Q3 typhoon count read as unknown (NaN) instead of 0
    t = L.qi("2026-Q3")
    X2 = X.copy()
    n_set = int(((X2["t"] == t)).sum())
    X2.loc[X2["t"] == t, "tc_count"] = np.nan
    r2 = K.tuned_forecast(d, X2, B, t, ())
    base = R[(R["arm"] == "A0") & (R["t"] == t)].set_index("province_code")
    sens = [{"province_code": p, "province": L.NAMES[p], "A0_p": float(base.loc[p, "p"]),
             "A0_p_price": float(base.loc[p, "p_price"]), "tcNaN_p": float(r2["p"][i]),
             "tcNaN_p_price": float(r2["p_price"][i]), "tcNaN_config": int(r2["cfg"]["id"]),
             "A0_config": int(base.loc[p, "config"])} for i, p in enumerate(L.PROVS)]
    H.write_csv(R, K.TABLES / "r1_ablation_predictions.csv")
    H.write_csv(pd.DataFrame(attr), K.TABLES / "r1_A0_group_attribution.csv")
    H.write_csv(pd.DataFrame(sens), K.TABLES / "r1_typhoon_nan_sensitivity_2027Q1.csv")
    H.dump({"protocol_sha256": K.verify_protocol(), "A0_vs_E57_max_abs_diff": err, "rows": int(len(R)),
            "typhoon_rows_set_nan": n_set, "arms": {a: list(v) for a, v in K.ARMS.items()}}, K.OUT / "r1_ablation.json")


if __name__ == "__main__":
    main()
