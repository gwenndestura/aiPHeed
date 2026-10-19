"""E60 step C3: rising-stress case review. One row per (onset or any warning issued by E58-EW or the E60 final candidate)
with issue date, target, province, probabilities, warning levels, latest government observations at issue, the relevant
v2 news articles attributed to the province and published in quarter t (before the issue date), data sufficiency,
outcome and lead time.

    backend/venv/Scripts/python.exe -B runner/c3_cases.py  -> RISING_STRESS_CASE_REVIEW.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E60 = Path(__file__).resolve().parents[1]
EXP = E60.parent
sys.path.insert(0, str(EXP / "E55_Food_Insecurity_LightGBM" / "runner"))
import e55_lib as F  # noqa: E402

L, np, pd = F.L, F.np, F.pd


def main():
    res = json.loads((E60 / "out" / "score.json").read_text())
    final = res["final_candidate"]
    fcol = {"A gov-only": "A", "C gov+news": "C", "D gov+news+history": "D"}[final]
    D = pd.read_csv(E60 / "out" / "scored_rows.csv", dtype={"province_code": str})
    art = pd.read_csv(E60 / "data" / "classified_articles.csv", dtype={"geo_province_code": str})
    art = art[art["relevant"] == 1]
    art["q"] = art["quarter"].map(L.qi)
    timing = pd.read_csv(EXP / "E59_E58_Validation_Audit" / "out" / "timing_by_origin.csv").set_index("origin_quarter")
    diag = pd.read_csv(EXP / "E58_Rising_Stress_Early_Warning" / "tables" / "diagnosis_rows.csv").set_index(["target", "province"])
    D["EW_level"] = np.where(D["E56_p"] >= 0.5, "ALERT", np.where(D["E56_p_price"] >= 0.5, "EMERGING", "NONE"))
    D["final_level"] = np.where(D[f"{fcol}_p"] >= 0.5, "ALERT", np.where(D[f"{fcol}_p_price"] >= 0.5, "EMERGING", "NONE"))
    keep = D[(D["onset"] == 1) | (D["EW_level"] != "NONE") | (D["final_level"] != "NONE")]
    rows = []
    for r in keep.itertuples():
        t = L.qi(r.origin_quarter)
        a = art[(art["geo_province_code"] == r.province_code) & (art["q"] == t)].sort_values("ph_date")
        dg = diag.loc[(r.target, r.province)] if (r.target, r.province) in diag.index else None
        rows.append({
            "issue_date": timing.loc[r.origin_quarter, "issue_date"], "origin_quarter": r.origin_quarter, "target": r.target,
            "province": r.province, "outcome_T43": int(r.y), "onset": int(r.onset),
            "latest_known_label": r.latest_known_T43, "E58_EW_level": r.EW_level, "E58_P_HIGH": round(r.E56_p, 3),
            "E58_P_price": round(r.E56_p_price, 3), f"E60_{fcol}_level": r.final_level,
            f"E60_{fcol}_P_HIGH": round(getattr(r, f"{fcol}_p"), 3), f"E60_{fcol}_P_price": round(getattr(r, f"{fcol}_p_price"), 3),
            "warning_followed_by_HIGH": (int(r.y) if r.final_level != "NONE" else None),
            "latest_food_yoy_at_issue": None if dg is None else dg["F_now"], "latest_gap_at_issue": None if dg is None else dg["gap_now"],
            "latest_hunger_at_issue": r.H_last_known, "cpi_through": timing.loc[r.origin_quarter, "cpi_latest_month_used"],
            "news_relevant_articles_q_t": int(len(a)),
            "news_by_trigger": json.dumps(a["trigger"].value_counts().to_dict()),
            "news_examples": " || ".join(f"{x.ph_date} {x.source_domain}: {x.title}" for x in a.head(4).itertuples()),
            "data_sufficiency": "sufficient" if len(a) >= 3 else ("thin news" if len(a) else "no attributed relevant news"),
            "lead_months_to_observable_outcome": timing.loc[r.origin_quarter, "lead_months_issue_to_outcome_observable"]})
    pd.DataFrame(rows).sort_values(["target", "province"]).to_csv(E60 / "RISING_STRESS_CASE_REVIEW.csv", index=False)
    print(len(rows), "case rows")


if __name__ == "__main__":
    main()
