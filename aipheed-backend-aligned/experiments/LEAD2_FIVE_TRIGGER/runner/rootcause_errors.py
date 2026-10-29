"""LEAD2_ROOT_CAUSE, phase 1-2 (diagnostic; no model is selected): every Lead-2 error of CR (and of P0H4-U for
comparison) at row level, with the issue-time values of all 12 indicator families, the five trigger-group conditions,
the realised target components and a pattern class; plus the decomposition of each candidate's Lead-2 calls into the
hunger part and the price part.

Pattern classes (data-determined, so "supported"; "model behaviour" is a hypothesis):
- hunger_cap: pi_H <= 0.5 on a HIGH row (P = pi_H x pi_P < 0.5 for any price part);
- hunger_reversal: the hunger part sits on the wrong side of 0.5 for the realised hunger condition;
- price_rose_after_issue / price_fell_after_issue: the issue-time projected margin max(A1_food, A1_gap) and the
  realised margin max(m_food, m_gap) have opposite signs;
- model_behaviour: the projection's sign was right but pi_P sat on the wrong side of 0.5.

    python rootcause_errors.py  # ../out/rootcause_errors.csv, ../out/rootcause_errors.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import final as FN  # noqa: F401  (sys.path order)
import lt_lib as T
from cr_resolve import cr_stack

F, KEY = T.F, T.KEY
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
IND = ["A1_food", "A1_gap", "A_mom", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1", "G_pri_yoy",
       "NG_gap_price", "W_rice_yoy", "W_cereal_yoy", "W_crude_yoy", "W_urea_yoy"]
HIGH_DIR = {"A1_food": 1, "A1_gap": 1, "A_mom": 1, "A2": 1, "A3": 1, "V1": 1, "C1": 1, "C2": 1, "C3": 1, "C4": 1,
            "E1": 1, "E2": 1, "N1": 1, "H1": 1, "G_pri_yoy": 1, "NG_gap_price": 1, "W_rice_yoy": 1, "W_cereal_yoy": 1,
            "W_crude_yoy": 1, "W_urea_yoy": 1}


def trigger_flags(S, row) -> dict:
    """Group condition: any of its inputs beyond the 75th percentile of the training rows known at the origin, in the
    direction of higher pressure (descriptive; percentiles from training rows only)."""
    tr = T.train_rows(S, int(row["t"]))
    out = {}
    for g, cols in T.GROUPS.items():
        hit = []
        for c in cols:
            v, ref = row.get(c), tr[c].dropna()
            if pd.notna(v) and len(ref) >= 10 and (v - ref.quantile(.75)) * HIGH_DIR.get(c, 1) > 0:
                hit.append(c)
        out[g] = ",".join(hit) if hit else "-"
    return out


def classify(r) -> tuple[str, str]:
    proj = np.nanmax([r["A1_food"], r["A1_gap"]]) if pd.notna(r["A1_food"]) or pd.notna(r["A1_gap"]) else np.nan
    real = max(r["m_food"], r["m_gap"])
    if r["y"] == 1 and r["pi_H_AB"] <= 0.5 + 1e-9:
        return "hunger_cap", "supported"
    if (r["pi_H_AB"] >= 0.5) != (r["hunger"] == 1):
        return "hunger_reversal", "supported"
    if pd.notna(proj) and (proj >= 0) != (real > 0):
        return ("price_rose_after_issue" if real > 0 else "price_fell_after_issue"), "supported"
    if pd.isna(proj):
        return "missing_projection", "supported"
    return "model_behaviour", "hypothesis"


def main():
    E = pd.read_csv(T.OUT / "cpi_refresh_rows.csv", dtype={"province_code": str})
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv", dtype={"province_code": str})
    S2 = cr_stack()
    g = E[E["lead"] == 2].merge(S2[KEY + IND + ["issue_date", "h_last", "sws_newest_q", "psa_newest_month", "N1_articles"]], on=KEY)
    g = g.merge(lab[["province_code", "q", "H", "F", "HL", "m_food", "m_gap"]], on=["province_code", "q"], how="left")
    rows = []
    for c in ("CR", "B0"):
        k = (g[f"{c}_p"] >= .5).astype(int)
        for _, r in g[k != g["y"]].iterrows():
            pat, ev = classify(r)
            iss = F.issue(int(r["t"]), "B")
            h = F.pi_h(iss, int(r["q"]))
            rows.append({"candidate": c, "province": NAMES[r["province_code"]], "target_quarter": F.qs(int(r["q"])), "lead": 2,
                         "origin": F.qs(int(r["t"])), "issue_date_reissue": iss, "true": "HIGH" if r["y"] else "LOW",
                         "predicted": "LOW" if r["y"] else "HIGH", "probability": round(float(r[f"{c}_p"]), 4), "cut": 0.5,
                         "pi_hunger": round(float(r["pi_H_AB"]), 4), "pi_price": round(float(r[f"{c}_price"]), 4),
                         "sws_used_at_reissue": h["sws_q"], "h_last_at_reissue": h["h_last_iss"], "H_realised": r["H"],
                         "hunger_label": int(r["hunger"]), "price_label": int(r["price"]),
                         "projected_margin": float(np.nanmax([r["A1_food"], r["A1_gap"]])) if r[["A1_food", "A1_gap"]].notna().any() else None,
                         "realised_margin": float(max(r["m_food"], r["m_gap"])),
                         **{f"x_{c2}": (None if pd.isna(r[c2]) else round(float(r[c2]), 4)) for c2 in IND},
                         "N1_missing": bool(pd.isna(r["N1"])), "A3_missing": bool(pd.isna(r["A3"])),
                         **{f"trig_{k2}": v for k2, v in trigger_flags(S2, r).items()},
                         "pattern": pat, "evidence": ev})
    R = pd.DataFrame(rows)
    R.to_csv(T.OUT / "rootcause_errors.csv", index=False, lineterminator="\n")
    # component decomposition (all 65 Lead-2 rows)
    dec = {}
    for c in ("P0H4", "B0", "CR"):
        hp = g["pi_H_AB"] if c != "P0H4" else E[E["lead"] == 2].merge(g[KEY], on=KEY)["P0H4_p"] / E[E["lead"] == 2].merge(g[KEY], on=KEY)["P0H4_price"]
        pp = g[f"{c}_price"]
        dec[c] = {"hunger_part_accuracy": float(((hp >= .5).astype(int) == g["hunger"]).mean()),
                  "price_part_accuracy": float(((pp >= .5).astype(int) == g["price"]).mean()),
                  "price_part_accuracy_on_hunger_rows": float(((pp[g["hunger"] == 1] >= .5).astype(int) == g.loc[g["hunger"] == 1, "price"]).mean()),
                  "price_part_recall_on_price_high": float((pp[g["price"] == 1] >= .5).mean()),
                  "price_part_false_alarm_rate": float((pp[g["price"] == 0] >= .5).mean())}
    # oracle bounds: true hunger part x model price part, and model hunger part x true price part (CR)
    orc = {"true_hunger_x_CR_price": float((((g["hunger"] * g["CR_price"]) >= .5).astype(int) == g["y"]).mean()),
           "CR_hunger_x_true_price": float((((g["pi_H_AB"] * g["price"]) >= .5).astype(int) == g["y"]).mean())}
    res = {"errors_by_pattern": {c: R[R["candidate"] == c]["pattern"].value_counts().to_dict() for c in ("CR", "B0")},
           "n_errors": {c: int((R["candidate"] == c).sum()) for c in ("CR", "B0")},
           "decomposition_lead2": dec, "oracle_lead2_accuracy": orc,
           "cap_cases": R[(R["candidate"] == "CR") & (R["pattern"] == "hunger_cap")][["province", "target_quarter", "sws_used_at_reissue",
                                                                                        "h_last_at_reissue", "pi_hunger", "H_realised"]].to_dict("records")}
    (T.OUT / "rootcause_errors.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))
    cols = ["candidate", "province", "target_quarter", "issue_date_reissue", "true", "probability", "pi_hunger", "pi_price", "h_last_at_reissue",
            "H_realised", "projected_margin", "realised_margin", "N1_missing", "trig_market", "trig_climate", "pattern"]
    print(R[R["candidate"] == "CR"][cols].to_string(index=False))


if __name__ == "__main__":
    main()
