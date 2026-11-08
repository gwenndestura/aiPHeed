"""LEAD2_CAUSES: audit of every Lead-2 error of P0H4-U (7 missed HIGH, 6 false alarms) using only information
available at each forecast cut-off (diagnostic; nothing is fitted or scored).

Per case: cut-off (S-AB Lead-2 issue date), newest CPI month, SWS reading used (quarter, value, publication date,
distance from 11.3 in round standard errors), the next SWS reading and when it was published, the label parts, the
price margin now / projected / realised, the model's hunger and price parts, the analog vote (limits.py), and the
cross-province spread of the province-varying inputs in that quarter.

One primary cause, by this precedence:
  H  missing or delayed hunger observation: pi_H <= 0.5 while the target reading was HIGH (or pi_H >= 0.5 while LOW)
  L  uncertain target label: realised price margin within +-0.10 point (CPI rounding), or the target SWS reading
     within 1 round SE of 11.3
  R  incorrect model ranking despite useful inputs: the flat projection, or the analog vote, was on the realised side
  V  insufficient provincial variation: another province in the same quarter had the opposite label but its
     province-varying inputs were within 0.5 SD of this one's (the inputs could not separate them)
  P  price change that could not be anticipated: none of the above
A case is 'realistically improvable at the time' only for R (the information was there).

    python case_audit.py        # ../out/case_audit.csv, ../out/case_audit.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import lt_lib as T

sys.path.insert(0, str(T.EXP / "FORECAST_RESEARCH_II" / "runner"))
import ii_lib as II  # noqa: E402

F, KEY = T.F, T.KEY
PROV_COLS = ["A1_food", "A1_gap", "A_mom", "A2", "A3", "V1", "C3", "C4"]
NATIONAL = ["C1", "E1", "E2", "H1", "G_pri_yoy", "NG_gap_price"] + T.WORLD
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
CAUSE = {"H": "missing or delayed hunger observation", "L": "uncertain target label",
         "R": "incorrect model ranking despite useful inputs", "V": "insufficient provincial variation",
         "P": "price change that could not be anticipated"}


def main():
    S = T.stack()
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv", dtype={"province_code": str})
    lim = pd.read_csv(T.OUT / "limits_errors.csv", dtype={"province_code": str})
    E = C[C["lead"] == 2][KEY + ["q", "y", "price", "hunger", "H", "pi_H_AB", "C0_price", "C0_p"]].copy()
    E = E.merge(lab[["province_code", "q", "m_food", "m_gap"]], on=["province_code", "q"], how="left")
    E = E.merge(S[KEY + PROV_COLS + NATIONAL + ["F_ex", "G_ex", "psa_newest_month"]], on=KEY, how="left")
    E["proj"], E["real"] = E[["A1_food", "A1_gap"]].max(axis=1), E[["m_food", "m_gap"]].max(axis=1)
    E["now"] = E[["F_ex", "G_ex"]].max(axis=1)
    E["target"] = E["q"].map(F.qs)
    E = E.merge(lim[["province_code", "target", "analog"]], on=["province_code", "target"], how="left")
    r = F.rounds()
    bl = r[r["area"] == "BL"].groupby("q").agg(H=("H", "mean"), moe=("moe", "mean"), published=("published", "max"))
    sd = S[S["t"] >= 8091].drop_duplicates(["t", "province_code"])[PROV_COLS].std()
    err = E[(E["C0_p"] >= .5).astype(int) != E["y"]].copy()
    rows = []
    for x in err.itertuples():
        iss = F.issue(int(x.t), "B")
        kn = F.known(iss, "BL")
        q_used, h_used = kn[-1][0], kn[-1][1]
        se_used = II.round_se(h_used, float(bl.loc[q_used, "moe"]))
        nxt = bl[bl.index > q_used].iloc[0]
        h_tgt = float(bl.loc[x.q, "H"]) if x.q in bl.index else np.nan
        se_tgt = II.round_se(h_tgt, float(bl.loc[x.q, "moe"])) if x.q in bl.index else np.nan
        same = E[(E["t"] == x.t) & (E["province_code"] != x.province_code)]
        dist = ((same[PROV_COLS] - pd.Series({c: getattr(x, c) for c in PROV_COLS})).abs() / sd).max(axis=1)
        twins = same[(dist <= .5) & (same["y"] != x.y)]
        side = x.real >= 0
        hunger_wrong = (x.pi_H_AB <= .5 + 1e-9 and x.hunger == 1) or (x.pi_H_AB >= .5 and x.hunger == 0)
        if hunger_wrong:
            cause = "H"
        elif abs(x.real) <= .10 or (pd.notna(se_tgt) and abs(h_tgt - F.H_LINE) <= se_tgt):
            cause = "L"
        elif (x.proj >= 0) == side or (pd.notna(x.analog) and (x.analog >= .5) == side):
            cause = "R"
        elif len(twins):
            cause = "V"
        else:
            cause = "P"
        rows.append({
            "province": NAMES[x.province_code], "target": x.target, "type": "FN (missed HIGH)" if x.y else "FP (false alarm)",
            "cutoff_issue_date": iss, "cpi_through": x.psa_newest_month,
            "sws_used": f"{F.qs(q_used)} = {h_used:.1f} (published {kn[-1][2]})",
            "sws_used_minus_11.3_in_SE": round((h_used - F.H_LINE) / se_used, 2),
            "next_sws": f"{F.qs(int(nxt.name))} = {nxt['H']:.1f} (published {nxt['published']})",
            "target_sws": h_tgt, "target_sws_minus_11.3_in_SE": round((h_tgt - F.H_LINE) / se_tgt, 2) if pd.notna(se_tgt) else np.nan,
            "label": "HIGH" if x.y else "LOW", "price_condition": int(x.price), "hunger_condition": int(x.hunger),
            "price_margin_now": x.now, "price_margin_projected": x.proj, "price_margin_realised": x.real,
            "pi_H": x.pi_H_AB, "pi_P": x.C0_price, "P": x.C0_p, "analog_vote": x.analog,
            "opposite_label_twins_same_quarter": ", ".join(NAMES[p] for p in twins["province_code"]),
            "cause": cause, "cause_label": CAUSE[cause], "realistically_improvable": cause == "R",
            "secondary": "; ".join(s for s, ok in (("borderline |margin|<0.5", abs(x.real) < .5),
                                                   ("opposite-label twin", len(twins) > 0),
                                                   ("projection right side", (x.proj >= 0) == side)) if ok),
        })
    A = pd.DataFrame(rows).sort_values(["type", "target", "province"])
    A.to_csv(T.OUT / "case_audit.csv", index=False, lineterminator="\n", float_format="%.3f")
    g = E.drop_duplicates(["t", "province_code"])
    res = {"cases": int(len(A)), "by_cause": A.groupby(["cause_label", "type"]).size().rename(None).to_dict(),
           "improvable": int(A["realistically_improvable"].sum()),
           "province_varying_inputs": PROV_COLS, "national_or_regional_only_inputs": NATIONAL,
           "national_inputs_distinct_values_per_origin_max": {c: int(g.groupby("t")[c].nunique().max()) for c in NATIONAL},
           "lead2_quarters_with_mixed_labels": int((E.groupby("q")["y"].nunique() == 2).sum()),
           "lead2_quarters": int(E["q"].nunique())}
    res["by_cause"] = {f"{a}|{b}": int(v) for (a, b), v in res["by_cause"].items()}
    (T.OUT / "case_audit.json").write_text(json.dumps(res, indent=1, default=float))
    pd.set_option("display.width", 300)
    pd.set_option("display.max_colwidth", 60)
    print(A.drop(columns=["cause_label"]).round(2).to_string(index=False))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
