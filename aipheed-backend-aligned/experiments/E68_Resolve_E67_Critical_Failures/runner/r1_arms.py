"""E68 r1 (PROTOCOL 2, 3): every pre-registered arm at the 10 evaluation origins and the 2 forward origins.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E68_Resolve_E67_Critical_Failures/runner/r1_arms.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e68_lib as R  # noqa: E402

H, L, E, P2, np, pd = R.H, R.L, R.E, R.P2, R.np, R.pd


def checks(d):
    assert P2.L is L, "threshold patch would not reach the offset"
    HLq = L.quarter_F(d, "all_items")
    HLq = HLq[HLq["q"].between(L.qi("2021-Q1"), L.qi("2022-Q4"))]
    got = HLq.groupby("province_code")["F"].apply(lambda s: float(np.percentile(s, 60))).to_dict()
    for p, v in R.HEADLINE_P60.items():
        assert abs(got[p] - v) < 1e-5, (p, got[p], v)
    Fq = L.quarter_F(d)
    Fq = Fq[Fq["q"].between(L.qi("2021-Q1"), L.qi("2022-Q4"))]
    for p, v in Fq.groupby("province_code")["F"].apply(lambda s: float(np.percentile(s, 60))).items():
        assert abs(L.e40_spec()["food"][p] - v) < 1e-9
    return got


def main():
    R.verify_protocol()
    H.verify_sealed()
    d, X, B = E.load()
    p60 = checks(d)
    rows, kinfo = [], []
    for arm, kw in R.ARMS.items():
        t0 = time.time()
        for t in R.EVAL_ORIGINS + R.FORWARD_ORIGINS:
            r = R.tuned_forecast(d, X, B, t, **kw)
            if r is None:
                raise SystemExit(f"{arm} {L.qs(t)} not eligible")
            assert list(r["te"]["province_code"]) == list(L.PROVS)
            for i, p in enumerate(L.PROVS):
                rows.append({"arm": arm, "t": t, "origin_quarter": L.qs(t), "issue_date": R.issue_date(t),
                             "target": L.qs(t + 2), "province_code": p, "p": float(r["p"][i]),
                             "p_price": float(r["p_price"][i]), "p_hunger": float(r["p_hunger"]),
                             "hunger_widen": float(r["widen"]), "config": int(r["cfg"]["id"])})
            if r["elnino"] is not None:
                kinfo.append({"arm": arm, "origin_quarter": L.qs(t), "issue_date": R.issue_date(t),
                              "in_force": r["elnino"]["in_force"], "n_past_rows": r["elnino"]["n_rows"],
                              "shift_food_m1": json.dumps(r["elnino"]["shift_food_m1"])})
        print(arm, f"{time.time() - t0:.0f}s", flush=True)
    A = pd.DataFrame(rows)
    S = pd.read_csv(H.SEALED["E57"], dtype={"province_code": str})
    a0 = A[A["arm"] == "A0"].merge(S[["t", "province_code", "E56_p"]], on=["t", "province_code"])
    err = float((a0["p"] - a0["E56_p"]).abs().max())
    print("A0 vs E57", err, len(a0))
    if len(a0) != 50 or err > 1e-9:
        raise SystemExit("A0 does not reproduce E57")
    H.write_csv(A, R.TABLES / "r1_arm_predictions.csv")
    H.write_csv(pd.DataFrame(kinfo), R.TABLES / "r1_elnino_shift.csv")
    H.dump({"protocol_sha256": R.verify_protocol(), "A0_vs_E57_max_abs_diff": err, "headline_p60": p60,
            "rows": int(len(A))}, R.OUT / "r1_arms.json")


if __name__ == "__main__":
    main()
