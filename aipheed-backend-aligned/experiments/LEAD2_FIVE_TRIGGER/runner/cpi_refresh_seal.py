"""PROTOCOL_LEAD2_CPI_REFRESH, prospective test of candidate CR (not adopted, not served): its forecasts from origin
2026-Q3, Lead 1 issued 2026-10-01 and Leads 2-4 re-issued 2026-10-15, sealed before any of their outcomes exists.

    python cpi_refresh_seal.py  # ../sealed/cr_prospective.csv, ../sealed/cr_prospective.sha256
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

import lt_lib as T

F, KEY = T.F, T.KEY
CPI = ["A1_food", "A1_gap", "A_mom"]
ORIGIN = 2026 * 4 + 2                                          # 2026-Q3
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def main():
    assert T.sha256(T.LT / "PROTOCOL_LEAD2_CPI_REFRESH.md") == (T.HERE / "CPI_REFRESH_SHA256.txt").read_text().strip()
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv")
    assert int(lab["q"].max()) < ORIGIN + 1, "an outcome of a sealed target quarter already exists"
    S = T.stack().copy()
    R = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    S = S.merge(R[KEY + [f"{c}_r" for c in CPI]], on=KEY, how="left")
    hit = S["lead"] >= 2                                        # the same replacement as cpi_refresh.py
    for c in CPI:
        S.loc[hit, c] = S.loc[hit, f"{c}_r"]
    P = T.run(T.U2, [ORIGIN], S=S)
    P = P[P["lead"] <= 4].copy()
    out = []
    for x in P.itertuples():
        iss = F.issue(ORIGIN, "A" if x.lead == 1 else "B")
        h = F.pi_h(iss, ORIGIN + int(x.lead))
        p = h["pi_H"] * x.pi_P
        out.append({"province_code": x.province_code, "province": NAMES[x.province_code],
                    "target_quarter": F.qs(ORIGIN + int(x.lead)), "lead": int(x.lead), "issue_date": iss,
                    "sws_reading_used": h["sws_q"], "h_last": h["h_last_iss"], "pi_hunger": h["pi_H"], "pi_price": x.pi_P,
                    "probability": p, "class": "HIGH" if p >= .5 else "LOW",
                    "cpi_through": "2026-08" if x.lead == 1 else "2026-09",
                    "model": "CR (LEAD2_CPI_REFRESH, research candidate, not served)"})
    O = pd.DataFrame(out).sort_values(["lead", "province_code"])
    dst = T.LT / "sealed"
    dst.mkdir(exist_ok=True)
    path = dst / "cr_prospective.csv"
    O.to_csv(path, index=False, lineterminator="\n", float_format="%.6g")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (dst / "cr_prospective.sha256").write_text(json.dumps({"file": path.name, "sha256": sha,
                                                           "sealed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                           "targets": sorted(O["target_quarter"].unique())}, indent=1) + "\n")
    print(O.round(3).to_string(index=False))
    print(sha)


if __name__ == "__main__":
    main()
