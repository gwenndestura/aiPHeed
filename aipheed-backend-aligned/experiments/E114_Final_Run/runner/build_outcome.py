"""E114 Phase 1: assemble the full-history SWS area file in the E110 format.

  - 1998-07 .. 2020-12: SWS's own tables (collect_sws.py -> data/sws_rounds_1998_2026.csv).
    fieldwork = the SWS month label; published = last day of that month + LAG_DAYS (PROTOCOL_E114 §1: 60 primary,
    100 sensitivity), because exact pre-2021 release dates were not compiled for every round. Every verified release
    (data/sws_release_date_evidence.csv) came no later than 45 days after the label month.
    Area margins: +/-6 points (1,200 respondents, 300 per area), flagged as assumed.
  - 2021+: the E110 file unchanged (exact fieldwork and release dates; identical values, checked here).
The news cross-check table is re-verified against the extracted SWS values (the 'match' column is recomputed).

    python build_outcome.py [lag_days]
"""
from __future__ import annotations

import calendar
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
E114 = HERE.parent
DATA = E114 / "data"
E110 = E114.parent / "E110_Hunger_Generalization" / "data" / "sws_area_rounds.csv"
AREAS = ["metro_manila", "balance_luzon", "visayas", "mindanao"]


def build(lag_days: int = 60) -> pd.DataFrame:
    s = pd.read_csv(DATA / "sws_rounds_1998_2026.csv")
    pre = s[s["year"] <= 2020].copy()
    end = [date(y, m, calendar.monthrange(y, m)[1]) for y, m in zip(pre["year"], pre["month"])]
    pre["fieldwork"] = [f"{y}-{m:02d} (month label)" for y, m in zip(pre["year"], pre["month"])]
    pre["published"] = [(d + timedelta(days=lag_days)).isoformat() for d in end]
    pre["commissioned"] = False
    pre["bl_n"] = None
    pre["area_moe_bl"], pre["area_moe_other"] = 6.0, 6.0
    pre["source_type"] = f"SWS media release table; release date = label month end + {lag_days} days (rule)"
    pre["moe_assumed"] = True
    cols = ["quarter", "fieldwork", "published", "respondent_base", "commissioned", "national"] + AREAS + \
           ["bl_n", "area_moe_bl", "area_moe_other", "source_type", "source", "mode", "moe_assumed"]
    e = pd.read_csv(E110)
    e["mode"], e["moe_assumed"] = "face-to-face", False
    out = pd.concat([pre[cols], e[cols]], ignore_index=True)
    out["era"] = ["pre-2021" if p < "2021" else "2021+" for p in out["quarter"]]
    return out


def verify_2021(s: pd.DataFrame) -> int:
    e = pd.read_csv(E110)
    bad = 0
    for r in e.itertuples():
        c = s[(s["national"] - r.national).abs() < 0.05] if pd.notna(r.national) else s
        ok = any(all(abs(getattr(r, a) - x[a]) < 1e-9 for a in AREAS) for _, x in c.iterrows())
        bad += not ok
    return bad


def recheck_news(s: pd.DataFrame) -> pd.DataFrame:
    n = pd.read_csv(DATA / "sws_news_crosscheck.csv")
    lab = s.set_index("label")
    n["sws_table_value"] = [float(lab.loc[r, a]) for r, a in zip(n["round"], n["area"])]
    n["match"] = (n["news_value"] - n["sws_table_value"]).abs() < 1e-9
    n.to_csv(DATA / "sws_news_crosscheck.csv", index=False, lineterminator="\n")
    return n


def main() -> None:
    lag = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    s = pd.read_csv(DATA / "sws_rounds_1998_2026.csv")
    n = recheck_news(s)
    print("news cross-check:", int(n["match"].sum()), "of", len(n), "match")
    print("2021+ rounds not found in the SWS table:", verify_2021(s))
    out = build(lag)
    name = "sws_area_rounds_full.csv" if lag == 60 else f"sws_area_rounds_full_lag{lag}.csv"
    out.to_csv(DATA / name, index=False, lineterminator="\n")
    q = out.groupby("era")["quarter"].nunique()
    print(name, len(out), "rounds;", q.to_dict(), "quarters")


if __name__ == "__main__":
    main()
