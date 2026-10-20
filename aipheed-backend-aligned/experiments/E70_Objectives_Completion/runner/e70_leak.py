"""E70 leakage test (PROTOCOL section 7): at origins 2023-Q4, 2025-Q1 and 2026-Q1 (Lead 2), randomise every raw value
NOT available at the issue date (the corruption scheme of audit/2026-10-20_final_validation/repro_leak.py, copied
unchanged), rebuild features and bases, re-run R0, A1, A2 and S0 (A1 with its corrupted same-lead history) and compare
with the sealed E70 forecasts. Pass = max |difference| <= 1e-12 for every arm.

    set AIPHEED_EXP=<clean export>\\aipheed-backend-aligned\\experiments
    python -B runner/e70_leak.py        -> out/leak.json
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e70_lib as X  # noqa: E402

H, L, M, np, pd = X.H, X.L, X.M, X.np, X.pd
ORIGINS = ["2023-Q4", "2025-Q1", "2026-Q1"]


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
    ev2 = ev2[~(ev2["announcement_date"] >= O)]
    return d2, x2, ev2


def main():
    raw = H.load_raw()
    space = H.G.search_space()
    S = pd.read_csv(X.E70 / "sealed" / "predictions.csv", dtype={"province_code": str})
    S = S[S["lead"] == 2]
    rng = np.random.default_rng(7)
    res = []
    for oq in ORIGINS:
        t = L.qi(oq)
        d2, x2, ev2 = corrupt(*raw, t, rng)
        _, X2, B2 = H.inputs_h((d2, x2, ev2), 2)
        hist, r = [], None
        for tp in [o for o in X.eligible_origins(2) if o <= t]:
            r = X.main_arms(d2, X2, B2, tp, 2, space, hist, 12)
        s = S[S["t"] == t].set_index("province_code").loc[L.PROVS]
        row = {"origin": oq, "target": L.qs(t + 2), "history_origins": len(hist)}
        for a in X.MAIN_ARMS:
            row[f"{a}_max_abs_diff"] = float(np.max(np.abs(np.asarray(r[a]["p"]) - s[f"{a}_p"].to_numpy())))
            row[f"{a}_cfg_equal"] = str(r[a]["cfg"]) == str(s[f"{a}_cfg"].iloc[0])
        row["pass"] = all(row[f"{a}_max_abs_diff"] <= 1e-12 and row[f"{a}_cfg_equal"] for a in X.MAIN_ARMS)
        res.append(row)
        print(json.dumps(row), flush=True)
    (X.E70 / "out").mkdir(exist_ok=True)
    (X.E70 / "out" / "leak.json").write_text(json.dumps({"rows": res, "all_pass": all(r["pass"] for r in res)}, indent=1))


if __name__ == "__main__":
    main()
