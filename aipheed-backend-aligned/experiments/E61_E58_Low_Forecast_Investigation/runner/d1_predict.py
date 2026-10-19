"""E61 addendum-1 step 1: candidate forecasts for the drift (D1-D3), combination (K1, K2) and feature-ablation (FA-*)
arms, the hunger variants (H0-H2) and a C0 refit with split counts, at the 10 E57 origins plus 2026-Q3 (operational,
never scored). SEALED (write-once) before d2_score reads outcomes.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/d1_predict.py
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e61_cands2 as D  # noqa: E402

X, np, pd, L, F, G, E = D.X, D.np, D.pd, D.L, D.F, D.G, D.E
sys.path.insert(0, str(X.EXP / "E57_E56_Rolling_Origin_Test" / "runner"))
import e57_predict as E57P  # noqa: E402  (known_labels; main() guarded)

SEALED = X.SEALED_DIR / "addendum1.csv"
OPER = X.SEALED_DIR / "addendum1_operational_2027Q1.csv"
SPLITS = X.SEALED_DIR / "addendum1_c0_split_counts.csv"
ARMS = ["D1", "D2", "D3", "K1", "FA-rice", "FA-emp", "FA-ofw"]


def verify():
    want = (X.E61 / "runner" / "ADDENDUM_1_SHA256.txt").read_text().split()[0]
    if hashlib.sha256((X.E61 / "PROTOCOL_ADDENDUM_1.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() != want:
        raise SystemExit("PROTOCOL_ADDENDUM_1.md changed after freezing")
    X.verify_sealed()


def main():
    verify()
    if SEALED.exists():
        raise SystemExit("already sealed")
    S0 = pd.read_csv(X.E57_SEALED, dtype={"province_code": str})
    d, Xf, B = E.load()
    origins = sorted(S0["t"].unique().tolist()) + [L.qi("2026-Q3")]
    B6 = D.bases_recent(d, list(range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1)))
    space = G.search_space()
    rows, oper, splits = [], [], []
    for t in origins:
        t0 = time.time()
        res = {a: D.tuned(d, Xf, B, B6, t, a, space) for a in ARMS}
        fx = G.tuned_forecast(d, Xf, B, t, space)                         # C0 refit (split counts)
        imp = dict(zip(fx["model"].model.booster_.feature_name(), fx["model"].model.booster_.feature_importance("split")))
        for f_, n_ in imp.items():
            splits.append({"origin": L.qs(t), "config": int(fx["cfg"]["id"]), "feature": f_, "splits": int(n_)})
        hv = {h: D.hunger_variant(d, Xf, t, h) for h in ("H0", "H1", "H2")}
        # K2: earlier C0 forecasts with T43 outcomes published before O(t)
        kl = E57P.known_labels(d, t)[["province_code", "q", "T43"]]
        prior = S0[S0["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(kl, on=["province_code", "q"])
        if len(prior) >= 10 and prior["T43"].nunique() == 2:
            k2 = D.k2_fit(D.zlogit(prior["E56_p_price"]), D.zlogit(prior["E56_p_hunger"]), prior["T43"])
            k2["n"], k2["fitted"] = int(len(prior)), True
        else:
            k2 = {"b": 0.0, "a1": 1.0, "a2": 1.0, "n": int(len(prior)), "fitted": False}
        op = t == L.qi("2026-Q3")
        if op:
            import json
            rec = json.loads(X.E58_RECORD.read_text(encoding="utf-8"))
            served = np.array([rec["provinces"][p]["forecast"]["probability"] for p in L.PROVS])
            c0p, c0h = np.asarray(fx["p_price"], float), float(fx["p_hunger"])   # the record rounds components to 4 dp
            assert np.allclose(c0h * c0p, served, atol=1e-6), "C0 refit differs from the served 2027-Q1 forecast"
        else:
            g = S0[S0["t"] == t].set_index("province_code").loc[L.PROVS]
            c0p, c0h = g["E56_p_price"].to_numpy(float), float(g["E56_p_hunger"].iloc[0])
            assert np.allclose(fx["p_price"], c0p, atol=1e-9), "C0 refit differs from sealed E57"
        s = k2["b"] + k2["a1"] * D.zlogit(c0p) + k2["a2"] * D.zlogit(np.full(5, c0h))
        k2p = 1 / (1 + np.exp(-s))
        for i, p in enumerate(L.PROVS):
            r = {"t": t, "origin_quarter": L.qs(t), "target": L.qs(t + 2), "province_code": p, "province": L.NAMES[p],
                 "C0_p_price": float(c0p[i]), "p_hunger": float(c0h), "C0_p": float(c0h * c0p[i]),
                 "K2_p": float(k2p[i]), "K2_n": k2["n"], "K2_fitted": k2["fitted"], "K2_a1": k2["a1"], "K2_a2": k2["a2"],
                 "K2_b": k2["b"]}
            for a in ARMS:
                v = res[a]
                if v is None or v.get("fallback"):
                    r[f"{a}_p_price"], r[f"{a}_p"], r[f"{a}_cfg"] = float(c0p[i]), float(c0h * c0p[i]), -1
                    r[f"{a}_fallback"] = True
                else:
                    assert abs(v["p_hunger"] - c0h) < 1e-9
                    r[f"{a}_p_price"], r[f"{a}_p"] = float(v["p_price"][i]), float(v["p"][i])
                    r[f"{a}_cfg"], r[f"{a}_fallback"] = int(v["cfg"]["id"]), False
            for h, v in hv.items():
                r[f"{h}_H_hat"] = None if v is None else v["H_hat"]
                r[f"{h}_p_hunger"] = None if v is None else v["p"]
                r[f"{h}_H_base"] = None if v is None else v["H_base"]
            r["K1_hunger_high_quarters"] = res["K1"].get("K1_hunger_high_quarters") if res["K1"] else None
            (oper if op else rows).append(r)
        print(L.qs(t), {a: (res[a] or {}).get("cfg", {}).get("id", "fb") for a in ARMS}, "K2 n", k2["n"],
              {h: round(v["H_hat"], 1) for h, v in hv.items() if v}, round(time.time() - t0, 1), "s", flush=True)
    SEALED.parent.mkdir(exist_ok=True)
    for path, df in ((SEALED, pd.DataFrame(rows)), (OPER, pd.DataFrame(oper)), (SPLITS, pd.DataFrame(splits))):
        path.write_bytes(df.to_csv(index=False, float_format="%.12g").encode())
        (path.parent / (path.name + ".sha256")).write_text(X.sha(path) + "  " + path.name + "\n")
    print("sealed", len(rows), "rows;", len(oper), "operational")


if __name__ == "__main__":
    main()
