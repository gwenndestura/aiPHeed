"""E59 audit step 2: forecast timing and leakage.

(a) Truncation test at ALL 10 rolling origins: every input (CPI, SWS, production, LFS, news, climate, OFW, rice,
    FSSI, policy orders) truncated to what was published before the issue date, features rebuilt from the truncated
    data, the frozen E56 procedure re-run; the forecast must equal the sealed one.
(b) Per-origin timing table: latest period used per source, the rule, and the observed posting date where the data
    carry one (SWS, policy orders).
(c) Lead time: months between the issue date and the date the target outcome became observable (SWS round of the
    target quarter posted; last CPI month of the target quarter, conservatively the 10th of the following month).

    backend/venv/Scripts/python.exe -B runner/a2_timing.py  -> out/timing.json, out/timing_by_origin.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A = Path(__file__).resolve().parents[1]
EXP = A.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, K, L, M, np, pd = G.E, G.F, G.F.K, G.L, G.M, G.np, G.pd
S57 = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"


def truncated_inputs(d, t):
    x = K.load_extra()
    O = L.origin(t)
    xc = {"climate": x["climate"][x["climate"]["q"] <= t], "ofw": x["ofw"][x["ofw"]["q"] <= t - 1],
          "rice": x["rice"][x["rice"]["q"] <= t - 1], "fssi": x["fssi"][x["fssi"]["q"] <= t]}
    ev = M.load_events()
    ev = ev[ev["announcement_date"] < O]
    dc = d.cut(t)
    allo = list(range(L.qi("2021-Q3"), t + 1))
    return dc, M.features(dc, xc, allo, ev), F.P2.bases(dc, allo)


def main():
    s57 = pd.read_csv(S57, dtype={"province_code": str})
    d, X, B = E.load()
    space = G.search_space()
    sws = pd.read_csv(L.SWS_FILE)
    sws["q"], sws["published"] = sws["quarter"].map(L.qi), pd.to_datetime(sws["published"])
    x = K.load_extra()
    ev = M.load_events()
    rows, trunc = [], []
    for t, g in s57.groupby("t"):
        t = int(t)
        O = L.origin(t)
        dc, Xc, Bc = truncated_inputs(d, t)
        fx = G.tuned_forecast(dc, Xc, Bc, t, space)
        sp = g.set_index("province_code")["E56_p"]
        diff = float(np.max(np.abs(np.array([sp[p] for p in L.PROVS]) - fx["p"])))
        trunc.append({"origin": L.qs(t), "issue_date": str(O.date()), "max_abs_diff_truncated_vs_sealed": diff,
                      "same_config": int(fx["cfg"]["id"]) == int(g["E56_config"].iloc[0])})
        c = d.cut(t)
        used_sws = c.sws.sort_values("published").iloc[-1]
        tq = t + 2
        tgt_sws = sws[sws["q"] == tq]
        cpi_obs = pd.Timestamp(year=(tq // 4) + (1 if tq % 4 == 3 else 0), month=((tq % 4) * 3 + 3) % 12 + 1, day=10)
        observable = max(tgt_sws["published"].max(), cpi_obs)
        rows.append({
            "origin_quarter": L.qs(t), "issue_date": str(O.date()), "target": L.qs(tq),
            "cpi_latest_month_used": L.ym_s(int(c.idx["ym"].max())), "cpi_rule": "month 2 of quarter t (month 3 published after O(t))",
            "sws_latest_round_used": L.qs(int(used_sws["q"])), "sws_round_posted": str(used_sws["published"].date()),
            "sws_posted_before_issue": bool(used_sws["published"] < O),
            "next_sws_round_posted": str(sws[sws["published"] >= O]["published"].min().date()),
            "production_latest_quarter": L.qs(int(c.prod["q"].max())), "lfs_latest_month": L.ym_s(int(c.lfs["ym"].max())),
            "typhoon_latest_quarter": L.qs(int(x["climate"][x["climate"]["q"] <= t]["q"].max())),
            "ofw_latest_quarter_with_value": L.qs(int(x["ofw"][(x["ofw"]["q"] <= t - 1)].dropna(subset=["ofw_cash_remit_usd_bn"])["q"].max())),
            "rice_latest_quarter": L.qs(int(x["rice"][x["rice"]["q"] <= t - 1]["q"].max())),
            "news_latest_quarter": L.qs(int(c.news["q"].max())),
            "policy_latest_announcement_used": str(ev[ev["announcement_date"] < O]["announcement_date"].max().date()),
            "target_outcome_observable_from": str(observable.date()),
            "lead_months_issue_to_target_start": round(((tq // 4 - O.year) * 12 + (tq % 4) * 3 + 1 - O.month), 1),
            "lead_months_issue_to_outcome_observable": round((observable - O).days / 30.44, 1)})
    T = pd.DataFrame(rows)
    (A / "out").mkdir(exist_ok=True)
    T.to_csv(A / "out" / "timing_by_origin.csv", index=False)
    res = {"truncation_test": trunc,
           "truncation_all_identical": all(r["max_abs_diff_truncated_vs_sealed"] < 1e-9 and r["same_config"] for r in trunc),
           "all_sws_used_posted_before_issue": bool(T["sws_posted_before_issue"].all()),
           "lead_months_to_outcome": {"min": float(T["lead_months_issue_to_outcome_observable"].min()),
                                      "median": float(T["lead_months_issue_to_outcome_observable"].median()),
                                      "max": float(T["lead_months_issue_to_outcome_observable"].max())}}
    (A / "out" / "timing.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))
    print(T.drop(columns=["cpi_rule"]).to_string())


if __name__ == "__main__":
    main()
