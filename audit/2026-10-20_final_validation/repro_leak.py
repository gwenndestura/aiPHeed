"""(1) Refit the frozen E56-TUNED procedure at selected origins and compare with the sealed E57 forecasts.
(2) Leakage test: at each test origin, corrupt every raw value that is NOT available at the issue date (CPI after the
cut month, SWS rounds posted on/after the issue date, production/LFS/news/typhoons/ENSO/remittances/rice beyond their
cuts, events announced on/after the issue date), rebuild features and bases from the corrupted data, refit and
compare. Identical forecasts mean no future information reaches the forecast.
Read-only use of the project code; nothing is written outside this folder.
"""
import copy
import json
import sys
from pathlib import Path

EXP = Path(r"C:\Users\admin\aipheed\aipheed-backend-aligned\experiments")
sys.dont_write_bytecode = True
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
I7 = E.I7
M, K, P2 = I7.M, I7.K, I7.P2
HERE = Path(__file__).resolve().parent
SEALED = Path(r"C:\Users\admin\aipheed_final\aipheed-backend-aligned\experiments\E57_E56_Rolling_Origin_Test\sealed\predictions.csv")


def corrupt(d, x, ev, t, rng):
    O, m0 = L.origin(t), L.m0_of(t)
    d2 = copy.deepcopy(d)
    fut = d2.idx["ym"] > m0
    d2.idx.loc[fut, "index"] = d2.idx.loc[fut, "index"] * rng.uniform(0.7, 1.4, fut.sum())
    fut = d2.yoy["ym"] > m0
    d2.yoy.loc[fut, "yoy"] = rng.uniform(-10, 25, fut.sum())
    fut = d2.sws["published"] >= O
    d2.sws.loc[fut, "H"] = rng.uniform(1, 40, fut.sum())
    fut = d2.prod["q"] > t - 1
    d2.prod.loc[fut, "value"] = d2.prod.loc[fut, "value"] * rng.uniform(0.2, 3, fut.sum())
    lfs_cut = (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2
    fut = d2.lfs["ym"] > lfs_cut
    d2.lfs.loc[fut, "value"] = rng.uniform(1, 30, fut.sum())
    fut = d2.news["q"] > t
    for c in [c for c in d2.news.columns if c.startswith("hits_") or c == "news_n"]:
        d2.news.loc[fut, c] = rng.integers(0, 500, fut.sum())
    x2 = copy.deepcopy(x)
    c = x2["climate"]
    for col, cut in (("tc_count", t), ("tc_max_signal", t), ("tc_severe_flag", t), ("enso_phase", t - 1)):
        fut = c["q"] > cut
        if col == "enso_phase":
            c.loc[fut, col] = rng.choice(c[col].dropna().unique(), fut.sum())
        else:
            c.loc[fut, col] = rng.integers(0, 9, fut.sum()) if col != "tc_severe_flag" else rng.integers(0, 2, fut.sum())
    for k, cut in (("ofw", t - 1), ("rice", t - 1), ("fssi", t)):
        D = x2[k]
        fut = D["q"] > cut
        for col in D.columns:
            if col not in ("q", "quarter", "province_code") and pd.api.types.is_float_dtype(D[col]):
                D.loc[fut, col] = rng.uniform(-50, 50, fut.sum())
    ev2 = ev.copy()
    late = ev2["announcement_date"] >= O
    ev2 = ev2[~late]                                     # events announced on/after the issue date removed
    return d2, x2, ev2


def main():
    which = [L.qi(q) for q in sys.argv[1:]] or [L.qi("2023-Q4"), L.qi("2025-Q1"), L.qi("2026-Q1")]
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    allo = list(range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1))
    X, B = M.features(d, x, allo, ev), P2.bases(d, allo)
    space = G.search_space()
    S = pd.read_csv(SEALED, dtype={"province_code": str})
    res = []
    rng = np.random.default_rng(7)
    for t in which:
        fx = G.tuned_forecast(d, X, B, t, space)
        sealed = S[S["t"] == t].set_index("province_code").loc[L.PROVS, "E56_p"].to_numpy()
        d2, x2, ev2 = corrupt(d, x, ev, t, rng)
        X2, B2 = M.features(d2, x2, allo, ev2), P2.bases(d2, allo)
        fz = G.tuned_forecast(d2, X2, B2, t, space)
        row = {"origin": L.qs(t), "target": L.qs(t + 2), "config_refit": int(fx["cfg"]["id"]),
               "config_corrupted": int(fz["cfg"]["id"]),
               "max_abs_refit_minus_sealed": float(np.max(np.abs(fx["p"] - sealed))),
               "max_abs_corrupted_minus_refit": float(np.max(np.abs(fz["p"] - fx["p"]))),
               "n_train_rows": fx["n_train_rows"], "n_train_q": fx["n_train_q"], "n_train_HIGH": fx["n_train_HIGH"],
               "n_features": len(fx["cols"]), "sealed": sealed.round(4).tolist(), "refit": np.round(fx["p"], 4).tolist(),
               "corrupted": np.round(fz["p"], 4).tolist()}
        res.append(row)
        print(json.dumps(row), flush=True)
    (HERE / f"repro_leak_{'_'.join(L.qs(t) for t in which)}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
