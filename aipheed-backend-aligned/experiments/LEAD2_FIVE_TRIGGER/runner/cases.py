"""Case-by-case analysis of the Lead-2 HIGH cases that the final model (C0 = P0H4-U) missed: origin, issue date,
target, observed label and its two parts with their margins, the forecast parts, the inputs known at the cut-off,
the SHAP push of each trigger group, missing inputs, the failure cause and whether any tested variant caught it.

    python cases.py             # ../out/missed_high_lead2.csv, ../out/missed_high_lead2.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F = T.F
BLOCKS = {**T.GROUPS, **T.OTHER_INPUTS}


def main():
    T.check_protocol(addendum=True)
    E = pd.read_csv(T.OUT / "threshold_rows.csv", dtype={"province_code": str})
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    E = E.merge(C[T.KEY + [f"C{i}_p" for i in range(1, 6)] + ["warn_days_B"]], on=T.KEY, how="left")
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv", dtype={"province_code": str})
    E = E.merge(lab[["province_code", "q", "H", "F", "HL", "m_food", "m_gap"]], on=["province_code", "q"], how="left")
    miss = E[(E["lead"] == 2) & (E["y"] == 1) & (E["p"] < .5)].copy()
    S = T.stack()
    shap = T.run(T.U2, sorted(miss["t"].unique()), S, explain=True)
    rows = []
    for _, r in miss.iterrows():
        s = S[(S["t"] == r["t"]) & (S["lead"] == 2) & (S["province_code"] == r["province_code"])].iloc[0]
        sh = shap[(shap["t"] == r["t"]) & (shap["lead"] == 2) & (shap["province_code"] == r["province_code"])].iloc[0]
        iss = F.issue(int(r["t"]), "B")
        kn = F.known(iss, "BL")
        h_used, q_used = kn[-1][1], F.qs(kn[-1][0])
        proj = max(s["A1_food"], s["A1_gap"])
        realised = max(r["m_food"], r["m_gap"])
        now = max(s["F_ex"], s["G_ex"]) if pd.notna(s["F_ex"]) else np.nan
        missing = [c for c in T.U2 if c != "lead" and pd.isna(s[c])]
        if r["pi_H_AB"] <= 0.5 + 1e-9:
            cause = (f"Hunger part capped the probability: the newest SWS reading at the issue date ({q_used}, {h_used:.1f}) "
                     f"was not above 11.3, so P(HIGH) <= 0.5 x price part. The target quarter's reading was {r['H']:.1f}.")
            kind = "hunger reading at the threshold (SWS lag / sampling noise)"
        elif proj < 0 <= realised:
            cause = (f"Price condition was below its threshold when projected ({proj:+.1f} pts) and above it when realised "
                     f"({realised:+.1f} pts): the price rise came after the issue date and no input anticipated it.")
            kind = "price rise after the issue date (insufficient predictive signal)"
        else:
            cause = f"Price part under 0.5 although the projection was {proj:+.1f} pts (model behaviour)."
            kind = "model under-weighted a projected price excess"
        if 0 <= realised < 0.5:
            kind += "; borderline label (realised margin < 0.5 pt)"
        caught = [c for c in ("C1", "C2", "C4", "C5") if r[f"{c}_p"] >= .5] + (["C0-T"] if r["cls_T"] == 1 else [])
        rows.append({"province": T.F.qs(0) if False else {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
                                                            "PH040400000": "Rizal", "PH040500000": "Batangas"}[r["province_code"]],
                     "origin": F.qs(int(r["t"])), "issue_date": iss, "warning_days": int(r["warn_days_B"]), "target": F.qs(int(r["q"])),
                     "observed": "HIGH", "observed_hunger_H": float(r["H"]), "realised_food_margin": float(r["m_food"]),
                     "realised_gap_margin": float(r["m_gap"]), "sws_reading_used": f"{q_used} {h_used:.1f}",
                     "pi_H": float(r["pi_H_AB"]), "pi_P": float(r["C0_price"]), "probability": float(r["p"]),
                     "class_at_0.50": "LOW", "validation_threshold": float(r["thr"]), "class_C0T": "HIGH" if r["cls_T"] else "LOW",
                     "price_now_margin_at_issue": float(now), "projected_margin_A1": float(proj), "CPI_through": s["psa_newest_month"],
                     **{f"shap_{b}": float(sum(sh[f"shap_{c}"] for c in cols)) for b, cols in BLOCKS.items()},
                     "missing_inputs": ", ".join(missing) or "none", "failure_type": kind, "explanation": cause,
                     "caught_by_any_tested_variant": ", ".join(caught) or "none"})
    D = pd.DataFrame(rows)
    D.to_csv(T.OUT / "missed_high_lead2.csv", index=False, lineterminator="\n", float_format="%.4g")
    T.OUT.joinpath("missed_high_lead2.json").write_text(json.dumps(rows, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(D[["province", "origin", "issue_date", "target", "observed_hunger_H", "sws_reading_used", "pi_H", "pi_P", "probability",
             "projected_margin_A1", "realised_food_margin", "realised_gap_margin", "missing_inputs", "caught_by_any_tested_variant"]].to_string(index=False))
    print(D[["province", "target"] + [f"shap_{b}" for b in BLOCKS]].round(3).to_string(index=False))
    for r in rows:
        print(r["province"], r["target"], "|", r["failure_type"], "|", r["explanation"])


if __name__ == "__main__":
    main()
