"""Measured outputs for Objective 1 (news pipeline) and Objective 5 (FNRI face-validity context). Read-only; no model.

    python measure.py     # -> out/obj1_news_measures.json, out/obj5_fnri_context.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

OC = Path(__file__).resolve().parents[1]
OUT = OC / "out"
EXP = OC.parent
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402

H = V.H
QUARTERS = list(range(H.qi("2021-Q1"), H.qi("2026-Q3") + 1))


def obj1() -> dict:
    P = V._pipeline()
    corpus, adm, sc = P.corpus(), P.admitted(), V.intensities()
    by_q = {}
    prov_status = Counter()
    for t in QUARTERS:
        a = P.asof(t)
        st = [P.fssi_v3(p, t, a)["status"] for p in P.PROVINCE_CODES]
        prov_status.update(st)
        by_q[H.qs(t)] = {"admitted_asof": len(a), "province_tagged": sum(1 for x in a if x["province_code"]),
                         "provinces_sufficient": st.count("SUFFICIENT"), "N1R": V.n1r(t)}
    n1r = [v["N1R"] for v in by_q.values()]
    man = json.loads((V.BACKEND / "data" / "news_v3" / "topics_manifest.json").read_text())
    at = pd.read_csv(V.BACKEND / "data" / "news_v3" / "article_topics.csv")
    pq = at[at["province_code"].notna() & (at["topic_id"] >= 0)].groupby(["province_code", "quarter"]).size()
    return {"corpus_articles": len(corpus), "admitted_relevant_dedup": len(adm),
            "admitted_with_province": sum(1 for x in adm if x["province_code"]),
            "xlmr_scored_admitted": sum(1 for x in adm if x["article_key"] in sc),
            "province_quarters": int(sum(prov_status.values())), "province_quarter_status": dict(prov_status),
            "n1r_quarters_available": int(np.isfinite(n1r).sum()), "n1r_quarters": len(n1r),
            "n1r_mean": float(np.nanmean(n1r)), "n1r_min": float(np.nanmin(n1r)), "n1r_max": float(np.nanmax(n1r)),
            "bertopic_manifest": man, "bertopic_province_quarters_with_topic": int(len(pq)),
            "by_quarter": by_q}


def obj5() -> dict:
    s = pd.read_csv(H.LONG / "sws_area_rounds_full.csv")
    s = s[~s["commissioned"].astype(bool)]
    y = s[s["quarter"].str.startswith(("2023", "2025"))]
    out = {}
    for yr in ("2023", "2025"):
        g = y[y["quarter"].str.startswith(yr)]
        out[yr] = {"sws_rounds": g[["quarter", "fieldwork", "national", "balance_luzon", "metro_manila", "visayas",
                                    "mindanao"]].to_dict("records"),
                   "sws_bl_mean": float(g["balance_luzon"].mean()), "sws_national_mean": float(g["national"].mean())}
    rows = []
    for k in (1, 2):
        r = pd.read_csv(EXP / "IMPROVE_V2" / "out" / f"rows_lead{k}.csv")
        r = r[r["q"].between(H.qi("2023-Q1"), H.qi("2023-Q4")) | r["q"].between(H.qi("2025-Q1"), H.qi("2025-Q4"))]
        rows += [{"lead": k, "target": H.qs(int(q)), "REF_p": float(p), "observed_y": int(yy)}
                 for q, p, yy in zip(r["q"], r["REF"], r["y"])]
    out["IMPROVE_V2_REF_forecasts"] = rows
    out["fnri"] = {
        "NNS_2023": {"CALABARZON_pct": 19.1, "ci95": [17.0, 21.1], "Philippines_pct": 31.4,
                     "measure": "households with moderate to severe food insecurity (FIES)",
                     "source": "DOST-FNRI 2023 National Nutrition Survey, Household and Food Security, regional map: "
                               "https://enutrition.fnri.dost.gov.ph/images/nns-2023/2.%20Household%20&%20Food%20Security%20.pdf",
                     "verified_by": "user, reading the official regional map (decision 2, 2026-11-03)"},
        "NNS_2025": {"CALABARZON_pct": 22.6, "Philippines_pct": 32.6,
                     "source": "secondary reporting (explained.ph) of the DOST-FNRI 2025 update, released 17 June 2026; "
                               "backend/data/processed/nns_fies.parquet provenance 'secondary_reporting'",
                     "status": "documented but secondary; replace with the FNRI primary publication when obtained"},
        "NNS_2019": "not used: 2018-2019 food-insecurity component used HFIAS, a different scale (user decision 2)"}
    return out


def main():
    OUT.mkdir(exist_ok=True)
    a, b = obj1(), obj5()
    (OUT / "obj1_news_measures.json").write_text(json.dumps(a, indent=1, default=str))
    (OUT / "obj5_fnri_context.json").write_text(json.dumps(b, indent=1, default=str))
    print(json.dumps({k: v for k, v in a.items() if k != "by_quarter"}, indent=1, default=str))
    print(json.dumps({k: v for k, v in b.items() if k != "IMPROVE_V2_REF_forecasts"}, indent=1, default=str))
    print(pd.DataFrame(b["IMPROVE_V2_REF_forecasts"]).to_string())


if __name__ == "__main__":
    main()
