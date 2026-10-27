"""FORECAST_RESEARCH export: the candidate P0H4-U for the backend (served only with AIPHEED_CH1_ENGINE=fr) and the
prospective seal of PROTOCOL section 8.

P0H4-U = the served P0H4 unchanged (same LightGBM price part, same rows, same seal for every Lead-1 row), except that
the forecasts of Lead 2 and beyond are re-issued the day after SWS publishes the newest Balance Luzon reading (issue
schedule B): their hunger part uses that reading. Lead 1 keeps the quarter-start issue (schedule A), because a
schedule-B Lead-1 forecast is issued after its target quarter has begun and is not an advance warning.

    python export_fr.py    # backend/data/ch1_engine_fr/{rows.csv, evaluation.json}, out/PROSPECTIVE_SEAL.json
"""
from __future__ import annotations

import hashlib
import json
import shutil

import numpy as np
import pandas as pd

import fr_lib as F

SERVED = F.EXP.parents[1] / "backend" / "data" / "ch1_engine"
TARGET = F.EXP.parents[1] / "backend" / "data" / "ch1_engine_fr"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
MODEL = "P0H4-U"


def _sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prospective(t: int) -> pd.DataFrame:
    """Selected arms (Z1 under A, Z0 under B) and P0H4-U at the newest origin, every target quarter after 2026-Q3."""
    S = F.stack()
    out = []
    for arm, sch in (("Z1", "A"), ("Z0", "B")):
        P = F.attach_hunger(F.price_arm(arm, S, t), sch)
        P["probability"] = P["pi_H"] * P["pi_P"]
        out.append(P.assign(arm=f"{arm}{sch}"))
    D = pd.concat(out, ignore_index=True)
    D["target_quarter"] = D["target_q"].map(F.qs)
    return D[["arm", "province_code", "target_quarter", "lead", "issue_date", "warning_days", "pi_H", "pi_P",
              "probability", "sws_q", "h_last_iss"]]


def main():
    F.check_protocol()
    res = json.loads((F.OUT / "results.json").read_text())
    ev = json.loads((SERVED / "evaluation.json").read_text(encoding="utf-8"))
    assert ev["seal_sha256"] == SERVED_SEAL, "served seal changed"
    R = pd.read_csv(SERVED / "rows.csv", dtype=str, keep_default_na=False)
    t_new = max(F.stack()["t"])
    iss_a, iss_b = F.issue(t_new, "A"), F.issue(t_new, "B")
    assert iss_a == "2026-10-01" and (R["issue_date"] == iss_a).any()
    R["issue_schedule"] = "A"
    m = (R["issue_date"] == iss_a) & (R["lead"].astype(int) >= 2)
    for i in R.index[m]:
        q = R.at[i, "quarter"]
        tq = int(q[:4]) * 4 + int(q[-1]) - 1
        h = F.pi_h(iss_b, tq)
        assert not np.isnan(h["pi_H"])
        pp = float(R.at[i, "pi_price"])
        p = h["pi_H"] * pp
        rb = F.rounds()
        rb = rb[(rb["area"] == "BL") & (rb["published"] < iss_b)]
        R.at[i, "issue_date"] = iss_b
        R.at[i, "issue_schedule"] = "B"
        R.at[i, "pi_hunger"] = f"{h['pi_H']:.6g}"
        R.at[i, "probability"] = f"{p:.6g}"
        R.at[i, "class"] = "HIGH" if p >= 0.5 else "LOW"
        R.at[i, "sws_newest_q"] = h["sws_q"]
        R.at[i, "sws_newest_published"] = rb[rb["q"] == int(h["sws_q"][:4]) * 4 + int(h["sws_q"][-1]) - 1]["published"].max()
        R.at[i, "h_last"] = f"{h['h_last_iss']:.6g}"
        R.at[i, "val_H1"] = f"{h['pi_H']:.6g}"
        R.at[i, "lead_days"] = str((F.quarter_start(tq + 1) - pd.Timestamp(iss_b)).days)
    R["model"] = np.where(R["issue_schedule"] == "B", MODEL, R["model"])
    TARGET.mkdir(exist_ok=True)
    seal_rows = R[m].copy()
    seal_path = F.OUT / "sealed_prospective_P0H4U.csv"
    seal_rows.to_csv(seal_path, index=False, lineterminator="\n")
    seal = _sha(seal_path)
    R.loc[m, "seal_sha256"] = seal
    R.to_csv(TARGET / "rows.csv", index=False, lineterminator="\n")

    b2, a2 = res["arms"]["P0H4B"]["leads"]["2"], res["arms"]["P0H4A"]["leads"]["2"]
    ev_fr = dict(ev)
    ev_fr["model"] = MODEL
    ev_fr["sws_update"] = {
        "definition": ("Leads 2 and beyond are re-issued the day after SWS publishes the newest Balance Luzon hunger "
                       "reading (no later than day 1 of the quarter's third month). Only the hunger part changes; every "
                       "other input keeps its quarter-start cut-off. Lead 1 keeps the quarter-start issue."),
        "issue_date": iss_b, "sws_quarter_used": F.pi_h(iss_b, t_new + 2)["sws_q"],
        "lead2": {"n": b2["metrics"]["n"], "metrics": b2["metrics"], "failed": b2["failed"], "reliable": b2["reliable"],
                  "acc_ci90": b2["acc_ci90"], "warning_days_median": b2["warning_days_median"],
                  "quarter_start_issue": {"metrics": a2["metrics"], "failed": a2["failed"]}},
        "lead2_brier_vs_quarter_start": b2["vs_served_P0H4"],
        "structural_benchmark": {k: {"lead1_accuracy": res["arms"][k]["leads"]["1"]["metrics"]["accuracy"],
                                     "lead2_accuracy": res["arms"][k]["leads"]["2"]["metrics"]["accuracy"],
                                     "max_reliable_lead": res["arms"][k]["max_reliable_lead"]} for k in ("Z1A", "Z0B")},
        "research": "aipheed-backend-aligned/experiments/FORECAST_RESEARCH/FORECAST_RESEARCH_REPORT.md",
        "protocol_sha256": res["protocol_sha256"], "seal_sha256": seal, "seal_issue_date": iss_b}
    ev_fr["serve_note"] = (ev["serve_note"] + " Candidate P0H4-U (AIPHEED_CH1_ENGINE=fr): Lead-2+ forecasts re-issued after "
                           "the SWS release; Lead 2 still not reliable (fails " + ", ".join(b2["failed"]) + ").")
    (TARGET / "evaluation.json").write_text(json.dumps(ev_fr, indent=1, default=float), encoding="utf-8")

    P = prospective(t_new)
    p_path = F.OUT / "prospective_selected_arms.csv"
    P.to_csv(p_path, index=False, lineterminator="\n", float_format="%.6g")
    seal_doc = {"protocol_sha256": res["protocol_sha256"], "origin": F.qs(t_new), "issue_A": iss_a, "issue_B": iss_b,
                "selected_arms_file": p_path.name, "selected_arms_sha256": _sha(p_path),
                "p0h4u_file": seal_path.name, "p0h4u_sha256": seal, "served_seal_unchanged": SERVED_SEAL,
                "note": "Score only after SWS publishes 2026-Q4 and later quarters; never edit these files."}
    (F.OUT / "PROSPECTIVE_SEAL.json").write_text(json.dumps(seal_doc, indent=1))
    print(json.dumps(seal_doc, indent=1))
    print(R[m][["province", "quarter", "lead", "issue_date", "pi_hunger", "pi_price", "probability", "class",
                "sws_newest_q", "h_last"]].to_string())
    print(P[P["arm"] == "Z1A"].pivot(index="province_code", columns="target_quarter", values="probability").round(3))


if __name__ == "__main__":
    main()
