"""E111 step 2: per issue date, the newest SWS observation, its age, the true horizon of each lead and the predictor
cutoffs actually used (E107/E110 rules). Writes ../out/horizon_table.csv and ../out/horizon_summary.json."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E111 = HERE.parent
sys.path.insert(0, str(E111.parent / "E110_Hunger_Generalization" / "runner"))
import e110_lib as F  # noqa: E402

E, np, pd = F.E, F.np, F.pd
L = E.L


def month_name(ym: int) -> str:
    return f"{ym // 12}-{ym % 12 + 1:02d}"


def main() -> None:
    a = pd.read_csv(F.AREA_FILE)
    rows = []
    for t in range(E.FIRST_ORIGIN, E.LAST_ORIGIN + 1):
        issue = E.issue(t)
        kn = F.known(issue, "BL")
        if kn:
            q_new = kn[-1][0]
            g = a[(a["quarter"] == E.qs(q_new)) & (a["published"].astype(str).str[:10] < issue)]   # rounds known at issue
            pub = str(g["published"].max())[:10]
            fw = "; ".join(g["fieldwork"])
        else:
            q_new, pub, fw = None, None, None
        ym0 = L.m0_of(t)
        r = {"origin": E.qs(t), "issue_date": issue, "issue_quarter": E.qs(t + 1),
             "newest_sws_quarter": E.qs(q_new) if q_new is not None else None, "newest_sws_fieldwork": fw,
             "newest_sws_published": pub,
             "days_since_publication": (pd.Timestamp(issue) - pd.Timestamp(pub)).days if pub else None,
             "observation_age_quarters": (t + 1 - q_new) if q_new is not None else None,
             "cpi_through": month_name(ym0), "lfs_through": f"months of {E.qs(t - 1)}",
             "production_rice_remittances_through": E.qs(t - 1) + (" (remittances end 2025-Q4)" if t - 1 > E.qi("2025-Q4") else ""),
             "typhoons_through": E.qs(t), "enso_oni_through": E.qs(t - 1),
             "pagasa_items": f"issued before {issue}", "news_headlines": f"quarter {E.qs(t)}, published before {issue}"}
        for k in (1, 2, 3, 4):
            r[f"lead{k}_target"] = E.qs(t + k)
            r[f"lead{k}_true_horizon_quarters"] = (t + k - q_new) if q_new is not None else None
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(E111 / "out" / "horizon_table.csv", index=False, lineterminator="\n")
    s = df.dropna(subset=["observation_age_quarters"])
    summ = {"origins": len(df), "origins_with_sws": len(s),
            "observation_age_quarters_counts": s["observation_age_quarters"].value_counts().sort_index().to_dict(),
            "lead1_true_horizon_counts": s["lead1_true_horizon_quarters"].value_counts().sort_index().to_dict(),
            "median_days_since_publication": float(s["days_since_publication"].median()),
            "definition": ("observation_age = issue quarter - newest SWS fieldwork quarter; true horizon = target quarter - "
                           "newest SWS fieldwork quarter; lead k = target quarter - origin quarter (issue on day 1 of origin+1)")}
    E.write_json(E111 / "out" / "horizon_summary.json", F._plain(summ))
    print(df[["origin", "issue_date", "newest_sws_quarter", "newest_sws_published", "observation_age_quarters",
              "lead1_target", "lead1_true_horizon_quarters", "lead2_true_horizon_quarters", "cpi_through"]].to_string(index=False))
    print(summ)


if __name__ == "__main__":
    main()
