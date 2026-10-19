"""E61 step C1 (PROTOCOL sections 2-3): candidate forecasts at the 10 E57 origins, SEALED before c2_score reads any
outcome, plus the same candidates at the operational origin 2026-Q3 (target 2027-Q1; never scored here).

C1's calibrator uses only earlier C0 forecasts whose PS outcome (as-of CPI vintage d.cut(t)) was published before O(t).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/c1_predict.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_cands as C  # noqa: E402

X, np, pd, L, F, G, E = C.X, C.np, C.pd, C.L, C.F, C.G, C.E
SEALED = X.SEALED_DIR / "candidates.csv"
OPERATIONAL = X.SEALED_DIR / "operational_2027Q1.json"


def verify_protocol():
    want = (X.E61 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((X.E61 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")


def c1_calibrator(d, S0: pd.DataFrame, t: int) -> dict:
    """Recalibration of logit P_price from earlier C0 forecasts with outcomes published before O(t)."""
    Y = F.t43_labels(d.cut(t))[["province_code", "q", "PS"]]
    prior = S0[S0["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(Y, on=["province_code", "q"])
    return E.fit_calibrator(prior["E56_p_price"].to_numpy(float), prior["PS"].to_numpy(float), "C2")


def b_now(te: pd.DataFrame) -> np.ndarray:
    return (te["ps_margin_now"] > 0).astype(float).to_numpy()


def main():
    verify_protocol()
    X.verify_sealed()
    if SEALED.exists():
        raise SystemExit("already sealed; candidates are written once")
    S0 = pd.read_csv(X.E57_SEALED, dtype={"province_code": str})
    d, Xf, B = E.load()
    space = G.search_space()
    rows, oper = [], {}
    origins = sorted(S0["t"].unique().tolist()) + [L.qi("2026-Q3")]
    for t in origins:
        t0 = time.time()
        res = {a: C.tuned(d, Xf, B, t, a, space) for a in C.ARMS}
        cal = c1_calibrator(d, S0, t)
        if t == L.qi("2026-Q3"):
            fz = json.loads(X.E56_FROZEN.read_text())
            rec = json.loads(X.E58_RECORD.read_text(encoding="utf-8"))
            p0 = np.array([rec["provinces"][p]["forecast"]["components"]["probabilityPricePressure"] for p in L.PROVS])
            ph0 = rec["provinces"][L.PROVS[0]]["forecast"]["components"]["probabilityHungerElevated"]
            te = res["C3"]["te"]
            oper = {"origin": "2026-Q3", "issue_date": "2026-10-01", "target": "2027-Q1",
                    "note": "operational forecasts of each candidate; NOT scored and NOT served",
                    "C1_calibrator": cal, "provinces": {}}
            for i, p in enumerate(L.PROVS):
                oper["provinces"][L.NAMES[p]] = {
                    "C0_p": float(fz["forecasts"][p]["p"]), "C0_p_price": float(p0[i]), "p_hunger": float(ph0),
                    "C1_p_price": float(E.apply_calibrator(cal, np.array([p0[i]]))[0]),
                    **{f"{a}_p_price": float(res[a]["p_price"][i]) for a in C.ARMS},
                    **{f"{a}_p": float(res[a]["p"][i]) for a in C.ARMS},
                    "ps_margin_now": float(te["ps_margin_now"].iloc[i]), "B_NOW": float(b_now(te)[i])}
            oper["configs"] = {a: res[a]["cfg"]["id"] for a in C.ARMS}
            oper["C2_mean_projection_error_food_gap"] = res["C2"]["mu"]
            print("operational 2027-Q1 done", round(time.time() - t0, 1), "s", flush=True)
            continue
        g = S0[S0["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        te = res["C3"]["te"]
        c1p = E.apply_calibrator(cal, g["E56_p_price"].to_numpy(float))
        for i, p in enumerate(L.PROVS):
            r = {"t": t, "origin_quarter": L.qs(t), "target": L.qs(t + 2), "province_code": p, "province": L.NAMES[p],
                 "p_hunger": float(g["E56_p_hunger"].iloc[i]),
                 "C0_p_price": float(g["E56_p_price"].iloc[i]), "C0_p": float(g["E56_p"].iloc[i]),
                 "C1_p_price": float(c1p[i]), "C1_p": float(g["E56_p_hunger"].iloc[i] * c1p[i]),
                 "C1_cal_a": cal["a"], "C1_cal_b": cal["b"], "C1_cal_n": cal["n"], "C1_cal_fitted": cal["fitted"],
                 "B_NOW": float(b_now(te)[i]), "ps_margin_now": float(te["ps_margin_now"].iloc[i])}
            for a in C.ARMS:
                assert abs(res[a]["p_hunger"] - r["p_hunger"]) < 1e-9
                r[f"{a}_p_price"] = float(res[a]["p_price"][i])
                r[f"{a}_p"] = float(res[a]["p"][i])
                r[f"{a}_cfg"] = int(res[a]["cfg"]["id"])
            rows.append(r)
        print("sealed origin", L.qs(t), {a: res[a]["cfg"]["id"] for a in C.ARMS}, "C1 n", cal["n"], cal["fitted"],
              round(time.time() - t0, 1), "s", flush=True)
    SEALED.parent.mkdir(exist_ok=True)
    SEALED.write_bytes(pd.DataFrame(rows).to_csv(index=False, float_format="%.12g").encode())
    (SEALED.parent / "candidates.csv.sha256").write_text(X.sha(SEALED) + "  candidates.csv\n")
    X.dump(oper, OPERATIONAL)
    (SEALED.parent / "operational_2027Q1.json.sha256").write_text(X.sha(OPERATIONAL) + "  operational_2027Q1.json\n")
    print("sealed", len(rows), "candidate rows")


if __name__ == "__main__":
    main()
