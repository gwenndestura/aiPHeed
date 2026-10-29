"""PROTOCOL_LEAD2_ROOT_CAUSE, prospective test of candidate CR-ANC (not eligible, not served): its forecasts from origin
2026-Q3, Lead 1 issued 2026-10-01 and Leads 2-4 re-issued 2026-10-15 (day-10 CPI rule, as pre-registered), sealed
before any of their outcomes exists. Same procedure as cpi_refresh_seal.py.

    python cr_anc_seal.py       # ../sealed/cranc_prospective.csv, ../sealed/cranc_prospective.sha256
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

import final as FN  # noqa: F401  (sys.path order)
import lt_lib as T
import root_cause as RC
from cr_resolve import cr_stack

F = T.F
ORIGIN = 2026 * 4 + 2                                          # 2026-Q3
NAMES = RC.NAMES


def main():
    assert T.sha256(T.LT / "PROTOCOL_LEAD2_ROOT_CAUSE.md") == (T.HERE / "ROOT_CAUSE_SHA256.txt").read_text().strip()
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv")
    assert int(lab["q"].max()) < ORIGIN + 1, "an outcome of a sealed target quarter already exists"
    T.MONO_UP = T.MONO_UP + RC.ANC
    S = cr_stack()
    S["A1_food_anc"], S["A1_gap_anc"] = RC.anchored_at(S, RC.G_ANCHOR)
    P = T.run(RC.COLS_ANC, [ORIGIN], S=S)
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
                    "model": "CR-ANC (LEAD2_ROOT_CAUSE, research candidate, not eligible, not served)"})
    O = pd.DataFrame(out).sort_values(["lead", "province_code"])
    path = T.LT / "sealed" / "cranc_prospective.csv"
    O.to_csv(path, index=False, lineterminator="\n", float_format="%.6g")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (T.LT / "sealed" / "cranc_prospective.sha256").write_text(json.dumps(
        {"file": path.name, "sha256": sha, "sealed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "targets": sorted(O["target_quarter"].unique()), "protocol_sha256": T.sha256(T.LT / "PROTOCOL_LEAD2_ROOT_CAUSE.md"),
         "input_sha256": {p: T.sha256(T.DATA / p) for p in ("stack_l2.csv", "known_price_l2.csv", "cpi_refresh.csv")}}, indent=1) + "\n")
    print(O.round(3).to_string(index=False))
    print(sha)


if __name__ == "__main__":
    main()
