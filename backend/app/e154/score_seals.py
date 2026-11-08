"""
Score sealed forecasts by docs/e154/SCORING_PROTOCOL.md. Checks every seal's hash first. Prints only outcomes already published; scores nothing that is missing.

    python -m app.e154.score_seals [province_outcomes.csv]
province_outcomes.csv, if given: province, year, instrument, measure, pct (instrument HFIAS and measure moderate_or_severe are the only rows scored)
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
SEALS = {"sws_e151": (D / "e151/out/sealed_sws_2026-Q4.json", "1a1c34bf"), "prov_e151": (D / "e151/out/issue/sealed_forecast_2027-Q1.json", "b397c40f"), "prov_d5": (D / "e151/out/issue/sealed_attempt_2027-Q1.json", "0f430203"), "prov_e152": (D / "e152/out/sealed_2027-Q1.json", "f6c07789"), "prov_e154": (D / "e154/out/sealed_2027-Q1.json", "d724c454"), "prov_e158": (D / "e158/out/sealed_2027-Q1.json", "f69e7a02"), "prov_e163": (D / "e163/out/sealed_2027-Q1.json", "343d1f06"), "prov_e164": (D / "e164/out/sealed_2027-Q1.json", "cbfb61dc")}
logit = lambda p: np.log(p / (100 - p))


def check():
    ok = {}
    for k, (p, h) in SEALS.items():
        ok[k] = hashlib.sha256(p.read_bytes()).hexdigest().startswith(h)
        print(k, "intact" if ok[k] else "HASH CHANGED, not scored")
    return ok


def sws(ok):
    if not ok["sws_e151"]:
        return
    from app.e144 import data as Dd
    from app.fi5.target import qlabel
    s = Dd.sws_quarterly()
    s["T_label"] = s["qi"].map(lambda q: qlabel(int(q)))
    f = pd.DataFrame(json.loads(SEALS["sws_e151"][0].read_text())["forecasts"])
    m = f.merge(s[["area", "T_label", "hunger"]], on=["area", "T_label"], how="inner")
    if m.empty:
        print("SWS: no sealed target quarter published yet")
        return
    arms = [c for c in f.columns if c.startswith("pct_")]
    rows = []
    for _, r in m.iterrows():
        o = {"area": r["area"], "quarter": r["T_label"], "lead": r["lead"], "actual": r["hunger"]}
        for a in arms:
            o[a[4:] + "_sqerr_logit"] = round(float((logit(r[a]) - logit(r["hunger"])) ** 2), 4)
        rows.append(o)
    R = pd.DataFrame(rows)
    print(R.to_string(index=False))
    l1 = R[R["lead"] == 1]
    print("Lead 1 scored quarters:", l1["quarter"].nunique(), "(claims need 4)")


def provinces(ok, path):
    if not path:
        print("Provinces: no outcome file given")
        return
    o = pd.read_csv(path)
    o = o[(o["instrument"] == "HFIAS") & (o["measure"] == "moderate_or_severe") & (o["year"] == 2027)]
    if o.empty:
        print("Provinces: no scorable HFIAS moderate-or-severe 2027 rows")
        return
    for k in [x for x in SEALS if x.startswith("prov") and ok[x]]:
        f = pd.DataFrame(json.loads(SEALS[k][0].read_text())["forecasts"])
        if "lead" in f:
            f = f[f["lead"] == 1]
        m = f.merge(o, on="province")
        m["class_right"] = (m["score"] >= 50) == (m["pct"] >= 50)
        m["error_points"] = (m["score"] - m["pct"]).round(1)
        m["inside_range"] = (m["pct"] >= m["low90"]) & (m["pct"] <= m["high90"])
        print(k)
        print(m[[c for c in ("arm",) if c in m] + ["province", "score", "low90", "high90", "pct", "class_right", "error_points", "inside_range"]].to_string(index=False))


if __name__ == "__main__":
    ok = check()
    sws(ok)
    provinces(ok, sys.argv[1] if len(sys.argv) > 1 else None)
