"""E46 as-of check: a past forecast must not change when every observation published after its origin is deleted.

For each checked origin t the whole data set is physically truncated to what was published before O(t) (CPI to month 2
of t, SWS rounds posted before O(t), production/LFS to t-1, typhoons/news to t, ENSO/remittances/rice to t-1, policy
events announced before O(t)); features, bases and the I6 forecast are rebuilt from the truncated data only and compared
with the forecast in the committed run (which was built from the full data with the code's own as-of cuts).

    backend/venv/Scripts/python.exe -B runner/e46_asof_check.py  -> runs/asof_check.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e46_lib as M  # noqa: E402

L, K, P2, np, pd = M.L, M.K, M.P2, M.np, M.pd
RUN = M.E46 / "runs" / "20261016T225203Z"
CHECK = ["2023-Q4", "2024-Q2", "2025-Q2", "2026-Q1", "2026-Q3"]


def truncate_extra(x: dict, t: int) -> dict:
    out = {k: v[v["q"] <= t].copy() for k, v in x.items()}
    return out


def main():
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    P = pd.read_csv(RUN / "predictions.csv", dtype={"province_code": str})
    res = {}
    for q in CHECK:
        t = L.qi(q)
        dt = d.cut(t)
        xt = truncate_extra(x, t)
        et = ev[ev["announcement_date"] < L.origin(t)]
        origins = list(range(L.qi("2021-Q3"), t + 1))
        X = M.features(dt, xt, origins, et)
        B = P2.bases(dt, origins)
        f = M.forecast(dt, X, B, t)
        ref = P[P["t"] == t].set_index("province_code").loc[L.PROVS]
        if f is None:
            res[q] = {"truncated_forecast": None, "committed_has_value": bool(ref["I6_p"].notna().any())}
            continue
        diff = np.abs(f["p"] - ref["I6_p"].to_numpy())
        res[q] = {"target_quarter": L.qs(t + 2), "max_abs_diff_p": float(np.max(diff)),
                  "decisions_identical": bool(((f["p"] >= f["threshold"]).astype(int) == ref["I6_yhat"].to_numpy()).all()),
                  "truncated_p": [round(float(v), 4) for v in f["p"]],
                  "committed_p": [round(float(v), 4) for v in ref["I6_p"]]}
        print(q, res[q]["max_abs_diff_p"], res[q]["decisions_identical"])
    (M.E46 / "runs" / "asof_check.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
