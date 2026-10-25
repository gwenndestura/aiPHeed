"""Score the sealed SWS hunger forecasts of E109-E113 once their target quarters are published (PROTOCOL_E113 §11).
Never modifies a sealed file; refuses to score one whose hash changed.

    python score_prospective.py            # writes ../out/prospective_scores.json

Enter each new non-commissioned SWS round, with its publication date, in E110 data/sws_area_rounds.csv (all areas)
and E109 data/outcome_rounds.csv (Balance Luzon). E107/E108 seals forecast the T43 composite; only their hashes
are verified here.
"""
from __future__ import annotations

from datetime import date

import e113_lib as L

E, F, H9, pd = L.E, L.F, L.H9, L.pd
HUNGER_SEALS = {"E109_Hunger_Forecasting": ["sealed_prospective.csv"], "E110_Hunger_Generalization": ["sealed_prospective.csv"],
                "E111_Hunger_Forecast_Audit": ["sealed_prospective.csv"],
                "E112_Food_Insecurity_Forecasting": ["sealed_prospective.csv"],
                "E113_Final_Model": ["sealed_prospective_A.csv", "sealed_prospective_B.csv"]}
HASH_ONLY = {"E107_Twelve_Indicator_LightGBM": ["sealed_prospective.csv"], "E108_Best_Defensible_Forecasting": ["sealed_prospective.csv"]}
AREA = {"Balance Luzon (SWS)": "BL"}


def observed(q: int, area: str, today: str):
    r = F.rounds()
    r = r[(r["area"] == area) & (r["q"] == q) & (r["published"].str[:10] <= today)]
    return (float(r["H"].mean()), str(r["published"].str[:10].max())) if len(r) else (None, None)


def main() -> None:
    today = date.today().isoformat()
    out = {"scored_on": today, "seals": {}}
    for e, files in {**HASH_ONLY, **HUNGER_SEALS}.items():
        for fn in files:
            p = L.EXP / e / "out" / fn
            want = (p.parent / f"{fn}.sha256").read_text().strip()
            ok = L.sha256(p) == want
            rec = {"sha256": want, "unchanged": ok}
            if e in HUNGER_SEALS and ok:
                rows = []
                for r in pd.read_csv(p).to_dict("records"):
                    area = AREA.get(r.get("area"), r.get("area"))
                    model = r.get("model", r.get("method"))
                    y, pub = observed(E.qi(r["target_quarter"]), area, today)
                    row = {"area": area, "model": model, "lead": int(r["lead"]), "target_quarter": r["target_quarter"]}
                    if y is None:
                        rows.append({**row, "status": "pending"})
                        continue
                    rows.append({**row, "status": "scored", "observed": y, "forecast": r["forecast_pct"],
                                 "abs_error": abs(r["forecast_pct"] - y), "rw_abs_error": abs(r["h_last"] - y),
                                 "inside_pi80": bool(r["pi80_low"] <= y <= r["pi80_high"]), "outcome_published": pub})
                rec.update(n_scored=sum(x["status"] == "scored" for x in rows),
                           n_pending=sum(x["status"] == "pending" for x in rows), rows=rows)
            out["seals"][f"{e}/{fn}"] = rec
    L.write_json(L.OUT / "prospective_scores.json", out)
    for e, v in out["seals"].items():
        print(e, "unchanged" if v["unchanged"] else "CHANGED", v.get("n_scored", "-"), "scored,", v.get("n_pending", "-"), "pending")


if __name__ == "__main__":
    main()
