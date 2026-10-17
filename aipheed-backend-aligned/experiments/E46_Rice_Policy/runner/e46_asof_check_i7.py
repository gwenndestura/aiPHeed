"""E46 as-of check for the corrected model I7 (the served e46 record): at the 2027-Q1 issue origin (t = 2026-Q3,
O = 2026-10-01), at the 2026-Q4 earlier-forecast origin and at three backtest origins, delete every observation
published on or after the origin, rebuild features, bases and the forecast from the truncated data, and compare with
the committed I7 run / frozen forecast.

    backend/venv/Scripts/python.exe -B runner/e46_asof_check_i7.py  -> runs/asof_check_i7.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e46_i7 as I7  # noqa: E402

M, L, K, P2, np, pd = I7.M, I7.L, I7.K, I7.P2, I7.np, I7.pd
RUN = M.E46 / "runs" / "i7_20261017T000111Z"
FZ = M.E46 / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json"
CHECK = ["2024-Q2", "2025-Q2", "2026-Q1", "2026-Q2", "2026-Q3"]


def main():
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    P = pd.read_csv(RUN / "predictions_i7.csv", dtype={"province_code": str})
    frozen = json.loads(FZ.read_text())
    res = {"frozen_sha256": hashlib.sha256(FZ.read_bytes()).hexdigest(), "checks": {}}
    for q in CHECK:
        t = L.qi(q)
        dt = d.cut(t)
        xt = {k: v[v["q"] <= t].copy() for k, v in x.items()}
        et = ev[ev["announcement_date"] < L.origin(t)]
        o = list(range(L.qi("2021-Q3"), t + 1))
        f = I7.forecast(dt, M.features(dt, xt, o, et), P2.bases(dt, o), t)
        ref = P[P["t"] == t].set_index("province_code").loc[L.PROVS, "I7_p"].to_numpy()
        r = {"origin": str(L.origin(t).date()), "target_quarter": L.qs(t + 2),
             "cpi_through": L.ym_s(int(dt.idx["ym"].max())), "sws_rounds_posted_before": str(dt.sws["published"].max().date()),
             "max_abs_diff_vs_run": float(np.max(np.abs(f["p"] - ref)))}
        if q == "2026-Q3":
            fr = np.array([frozen["provinces"][L.NAMES[p]]["I7_p"] for p in L.PROVS])
            r["max_abs_diff_vs_frozen_2027Q1"] = float(np.max(np.abs(f["p"] - fr)))
        res["checks"][q] = r
        print(q, r)
    (M.E46 / "runs" / "asof_check_i7.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
