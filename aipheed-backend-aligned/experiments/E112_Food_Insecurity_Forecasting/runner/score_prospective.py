"""Score the sealed SWS hunger forecasts of E109, E110, E111 and E112 once their target quarters are published
(PROTOCOL.md section 6). Never modifies a sealed file; refuses to score one whose hash changed.

    python score_prospective.py            # writes ../out/prospective_scores.json

A target quarter is scored only when a non-commissioned SWS round for it is entered in E110 data/sws_area_rounds.csv
(all areas) and, for Balance Luzon, in E109 data/outcome_rounds.csv, with a publication date on or before today.
The E107 and E108 seals forecast the T43 composite, not hunger; only their hashes are verified here.
"""
from __future__ import annotations

from datetime import date

import e112_lib as L

E, F, H9, pd = L.E, L.F, L.H9, L.pd
SEALS = ("E109_Hunger_Forecasting", "E110_Hunger_Generalization", "E111_Hunger_Forecast_Audit",
         "E112_Food_Insecurity_Forecasting")
AREA = {"Balance Luzon (SWS)": "BL"}


def observed(q: int, area: str, today: str):
    if area == "BL":
        r = H9.rule_rounds("primary")
        r = r[(r["q"] == q) & (r["published"].str[:10] <= today)]
    else:
        r = F.rounds()
        r = r[(r["area"] == area) & (r["q"] == q) & (r["published"].str[:10] <= today)]
    return (float(r["H"].mean()), str(r["published"].str[:10].max())) if len(r) else (None, None)


def main() -> None:
    today = date.today().isoformat()
    out = {"scored_on": today, "seals": {}}
    for e in ("E107_Twelve_Indicator_LightGBM", "E108_Best_Defensible_Forecasting") + SEALS:
        p = L.E112.parent / e / "out" / "sealed_prospective.csv"
        want = (p.parent / "sealed_prospective.csv.sha256").read_text().strip()
        ok = L.sha256(p) == want
        rec = {"sha256": want, "unchanged": ok}
        if e in SEALS and ok:
            rows = []
            for r in pd.read_csv(p).to_dict("records"):
                area = AREA.get(r.get("area"), r.get("area"))
                y, pub = observed(E.qi(r["target_quarter"]), area, today)
                row = {"area": area, "method": r["method"], "lead": int(r["lead"]), "target_quarter": r["target_quarter"]}
                if y is None:
                    rows.append({**row, "status": "pending"})
                    continue
                rows.append({**row, "status": "scored", "observed": y, "forecast": r["forecast_pct"],
                             "abs_error": abs(r["forecast_pct"] - y), "rw_abs_error": abs(r["h_last"] - y),
                             "inside_pi80": bool(r["pi80_low"] <= y <= r["pi80_high"]), "outcome_published": pub})
            rec.update(rows=rows, n_scored=sum(x["status"] == "scored" for x in rows),
                       n_pending=sum(x["status"] == "pending" for x in rows))
        out["seals"][e] = rec
    L.write_json(L.OUT / "prospective_scores.json", out)
    for e, v in out["seals"].items():
        print(e, "unchanged" if v["unchanged"] else "CHANGED", v.get("n_scored", "-"), "scored,", v.get("n_pending", "-"), "pending")


if __name__ == "__main__":
    main()
