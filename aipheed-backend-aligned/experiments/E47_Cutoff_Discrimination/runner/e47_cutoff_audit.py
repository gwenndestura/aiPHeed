"""E47 publication-cutoff audit of every input used by E46 I7 (issue 00:00 on day 1 of quarter t+1) and I8 (issue
00:00 on the 15th of the first month of t+1), at every simulated origin 2021-Q3..2026-Q3.

For each source the script takes the LATEST observation the code actually uses at that origin (from the as-of cut),
adds the source's publication lag (exact dates where the repository has them, otherwise a documented conservative
upper bound) and checks that the estimated publication date precedes the issue time.

    backend/venv/Scripts/python.exe -B runner/e47_cutoff_audit.py   [i7|i8]   -> runs/cutoff_audit_<conv>.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E47 = HERE.parent
E46R = E47.parent / "E46_Rice_Policy" / "runner"
sys.path.insert(0, str(E46R))
CONV = sys.argv[1] if len(sys.argv) > 1 else "i7"
if CONV == "i8":
    import e46_i8  # noqa: F401,E402  (re-points m0_of / origin to the 15th-of-month convention)
import e46_lib as M  # noqa: E402

L, K, np, pd = M.L, M.K, M.np, M.pd
DAY = pd.Timedelta(days=1)

# Publication lag after the END of the reference period (conservative upper bounds unless exact).
LAGS = {
    "cpi_provincial": (13, "PSA national CPI on about the 5th-7th of the next month (e.g. Jul 2026 on 2026-08-05, Sep 2026 "
                           "on Tue 2026-10-06); RSSO IV-A provincial releases follow within days (Feb 2024 on 2024-03-07, "
                           "Mar 2024 on 2024-04-08). Upper bound used: 13 days after month end."),
    "lfs_national": (45, "PSA LFS about 5-6 weeks after the reference month. Upper bound: 45 days."),
    "production_quarterly": (60, "PSA palay/corn and fisheries quarterly reports about 45-60 days after the quarter. Upper bound: 60."),
    "remittances_quarterly": (50, "BSP cash remittances about 6-7 weeks after the last month of the quarter. Upper bound: 50."),
    "rice_wholesale_quarterly": (30, "PSA wholesale price bulletins about 2-4 weeks after the month. Upper bound: 30."),
    "enso_quarterly": (10, "NOAA ONI updated in the first days of the following month. Upper bound: 10."),
    "fx_quarterly": (1, "ECB daily reference rates, same day. Upper bound: 1."),
    "typhoons_quarter": (0, "PAGASA/JTWC advisories in real time: a storm in quarter t is known by midnight at its end "
                            "(counts within 300 km; later best-track intensity revisions are a vintage risk, not modelled)."),
    "news_quarter": (0, "Articles counted by publication date within quarter t: all published by midnight at its end."),
}


def month_end(ym: int) -> pd.Timestamp:
    y, m = ym // 12, ym % 12 + 1
    return (pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0))


def q_end(q: int) -> pd.Timestamp:
    return month_end((q // 4) * 12 + (q % 4) * 3 + 2)


def main():
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    rows = []
    for t in range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1):
        O = L.origin(t)
        c = d.cut(t)
        cx = K.cut_extra(x, t)
        used = {
            "cpi_provincial": (month_end(int(c.idx["ym"].max())), L.ym_s(int(c.idx["ym"].max()))),
            "lfs_national": (month_end(int(c.lfs["ym"].max())), L.ym_s(int(c.lfs["ym"].max()))),
            "production_quarterly": (q_end(int(c.prod["q"].max())), L.qs(int(c.prod["q"].max()))),
            "typhoons_quarter": (q_end(int(cx["tc"]["q"].max())), L.qs(int(cx["tc"]["q"].max()))),
            "enso_quarterly": (q_end(int(cx["enso"]["q"].max())), L.qs(int(cx["enso"]["q"].max()))),
            "rice_wholesale_quarterly": (q_end(int(cx["rice"]["q"].max())), L.qs(int(cx["rice"]["q"].max()))),
            "news_quarter": (q_end(int(c.news["q"].max())), L.qs(int(c.news["q"].max()))),
        }
        ofw = cx["ofw"].dropna(subset=["ofw_cash_remit_usd_bn"])
        if len(ofw):
            used["remittances_quarterly"] = (q_end(int(ofw["q"].max())), L.qs(int(ofw["q"].max())))
        used["fx_quarterly"] = (q_end(int(cx["ofw"]["q"].max())), L.qs(int(cx["ofw"]["q"].max())))
        r = {"origin_quarter": L.qs(t), "issue": str(O), "target": L.qs(t + 2), "sources": {}}
        for k, (end, label) in used.items():
            # lag 0 = known at midnight after the period's last day; otherwise published lag days after it
            pub = end + (LAGS[k][0] or 1) * DAY
            ok = pub <= O if LAGS[k][0] == 0 else pub < O
            r["sources"][k] = {"latest_observation": label, "publication_upper_bound": str(pub.date()),
                               "margin_days": int((O - pub).days), "available": bool(ok)}
        sws = c.sws.sort_values("published")
        r["sources"]["sws_rounds"] = {"latest_observation": L.qs(int(sws["q"].iloc[-1])),
                                      "publication_exact": str(sws["published"].iloc[-1].date()),
                                      "margin_days": int((O - sws["published"].iloc[-1]).days),
                                      "available": bool(sws["published"].iloc[-1] < O)}
        known = ev[ev["announcement_date"] < O]
        r["sources"]["rice_policy_events"] = {"events_known": list(known["event_id"]) if "event_id" in known else len(known),
                                              "available": bool((known["announcement_date"] < O).all())}
        lab = K.available_labels(d, t)
        r["training_labels"] = {"latest_label_quarter": L.qs(int(lab["q"].max())) if len(lab) else None,
                                "cpi_month3_publication_upper_bound": str((q_end(int(lab["q"].max())) + 13 * DAY).date())
                                if len(lab) else None}
        r["all_available"] = all(s["available"] for s in r["sources"].values())
        rows.append(r)
    out = {"convention": CONV, "lags": {k: {"days": v[0], "evidence": v[1]} for k, v in LAGS.items()},
           "origins": rows, "all_origins_available": all(r["all_available"] for r in rows),
           "min_margin_days": {k: min(r["sources"][k]["margin_days"] for r in rows if k in r["sources"]
                                      and "margin_days" in r["sources"][k])
                               for k in list(LAGS) + ["sws_rounds"]}}
    (E47 / "runs").mkdir(exist_ok=True)
    (E47 / "runs" / f"cutoff_audit_{CONV}.json").write_text(json.dumps(out, indent=1))
    print(CONV, "all available:", out["all_origins_available"], "min margins:", out["min_margin_days"])
    last = rows[-1]
    print("2027-Q1 issue", last["issue"], {k: (v.get("latest_observation"), v.get("margin_days")) for k, v in last["sources"].items()})


if __name__ == "__main__":
    main()
