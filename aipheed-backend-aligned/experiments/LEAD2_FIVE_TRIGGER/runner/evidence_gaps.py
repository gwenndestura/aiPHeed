"""LEAD2_EVIDENCE_GAPS: close what can be closed of the Lead-2 evidence gaps, without new model candidates.

1. CPI release timing: for every CR Lead-2 issue, the refreshed provincial CPI months, the assumed (day-10) release date,
   the margin, and the verified release date from data/psa_cpi_release_evidence.csv (UNKNOWN where not established).
2. Target meaning: the T43c formula split into its observed and proxy parts, with the existing target audit
   (FORECAST_RESEARCH_II out/target_audit.json) and the Lead-2 evaluation rows.
3. Prospective test: the sealed CR forecasts verified (hash, contents, reproduction from the committed snapshot without
   writing), no sealed outcome present in the data, and the outcomes required before scoring.

    python evidence_gaps.py     # ../out/evidence_gaps.json
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

import final as FN  # noqa: F401  (sys.path order)
import lt_lib as T
import cpi_refresh_features as CF  # noqa: I001

F, KEY = T.F, T.KEY
CPI = ["A1_food", "A1_gap", "A_mom"]
ORIGIN = 2026 * 4 + 2                                          # 2026-Q3, origin of the sealed forecasts
ym = lambda m: f"{m // 12}-{m % 12 + 1:02d}"  # noqa: E731


def timing() -> dict:
    R = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    E = pd.read_csv(T.OUT / "cpi_refresh_rows.csv", dtype={"province_code": str})
    R = R.merge(E[E["lead"] == 2][KEY], on=KEY)
    ev = pd.read_csv(T.DATA / "psa_cpi_release_evidence.csv", dtype=str)
    verified = ev[ev["status"] == "VERIFIED"].set_index("reference_month")["publication_date"].to_dict()
    rows = []
    for (t, iss, m0, m0r), g in R.groupby(["t", "issue_B", "m0", "m0r"]):
        for m in range(int(m0) + 1, int(m0r) + 1):
            assumed = date((m + 1) // 12, (m + 1) % 12 + 1, CF.RELEASE_DAY)
            v = verified.get(ym(m))
            rows.append({"origin": F.qs(int(t)), "issue_date": iss, "refreshed_month": ym(m), "rows": int(len(g)),
                         "assumed_release_day10": str(assumed), "margin_days_assumed": (date.fromisoformat(iss) - assumed).days,
                         "verified_release": v or "UNKNOWN",
                         "available_at_issue": ("yes" if v and v < iss else "no" if v else "UNKNOWN")})
    T_ = pd.DataFrame(rows)
    return {"series": "PSA OpenSTAT 0012M4ACP22, CPI for all income households by province and commodity group (2018=100), "
                      "food and all items, monthly; Batangas, Cavite, Laguna, Quezon, Rizal",
            "repository_snapshot": "aipheed-backend-aligned/experiments/E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv "
                                   "(single undated download; no release-date metadata; values through 2026-09)",
            "snapshot_sha256": T.sha256(T.EXP / "E41_Lead2_Audit" / "data_acquired" / "cpi_index_ACP22.csv"),
            "rows": rows, "months_checked": int(len(T_)), "months_verified": int((T_["verified_release"] != "UNKNOWN").sum()),
            "months_unknown": int((T_["verified_release"] == "UNKNOWN").sum()),
            "months_margin_le_14_days": int((T_["margin_days_assumed"] <= 14).sum()),
            "evidence_rows": int(len(ev)), "recalculation": "not triggered: no evidence establishes that the day-10 rule was violated",
            "sensitivity_if_later": json.loads((T.OUT / "cr_release_sensitivity.json").read_text())}


def target() -> dict:
    a = json.loads((T.EXP / "FORECAST_RESEARCH_II" / "out" / "target_audit.json").read_text())
    E = pd.read_csv(T.OUT / "cpi_refresh_rows.csv", dtype={"province_code": str})
    g = E[E["lead"] == 2]
    lab = g.groupby("q").agg(h=("hunger", "first"), hn=("hunger", "nunique"), p=("price", "sum"), y=("y", "sum"))
    return {
        "formula": "y = 1[H_BL(q) > 11.3] x 1[m_food(p,q) > 0 or m_gap(p,q) > 0]; H_BL = mean of the SWS Balance Luzon "
                   "involuntary-hunger rounds of quarter q; m_food = quarterly mean of published food CPI YoY - province P60 "
                   "of 2021-Q1..2022-Q4; m_gap = (food YoY - all-items YoY) - province P60 of the same window",
        "components": {
            "regional_observed_hunger": {"source": "SWS Social Weather Survey, Balance Luzon involuntary hunger (%)", "observed": True,
                                         "geography": "Balance Luzon (all of Luzon outside Metro Manila); not CALABARZON, not province",
                                         "sampling_se_pp": a["T2_noise"]["se_range_pp"]},
            "province_food_price_pressure": {"source": "PSA provincial CPI (food, all items)", "observed": True,
                                             "is_food_insecurity_measure": False,
                                             "role": "proxy: affordability pressure relative to the province's own 2021-22 level"},
            "predictors_not_outcomes": ["V1 poverty/density (PSA SAE 2021, POPCEN 2024)", "E1 unemployment (national LFS)",
                                        "E2 OFW remittances (national BSP)", "C1-C3 climate", "C4 fisheries", "A2 headline", "A3 rice",
                                        "N1/GDELT news", "H1 regional hunger outlook", "world prices"]},
        "thresholds": a["T1_rebuild"]["thresholds"],
        "labels_rebuild_mismatch": a["T1_rebuild"]["y_mismatch"],
        "label_equals_price_share_overall": a["T1_rebuild"]["overall"]["label_equals_price_share"],
        "label_equals_price_share_since_2023Q4": a["T1_rebuild"]["since_2023Q4"]["label_equals_price_share"],
        "lead2_rows": {"quarters": int(len(lab)), "hunger_identical_across_provinces": bool((lab["hn"] == 1).all()),
                       "hunger_quarters": int(lab["h"].sum()),
                       "high_rows_in_hunger_quarters_equal_price_rows": bool((lab.loc[lab["h"] == 1, "p"] == lab.loc[lab["h"] == 1, "y"]).all())},
        "price_hunger_association": a["T3_validity"]["price_hunger_level"], "price_hunger_supported": a["T3_validity"]["T3_supported"],
        "provincial_fies_points": a["T3_validity"]["fnri_annual"],
        "supports_province_specific_food_insecurity_claims": False}


def prospective() -> dict:
    s = json.loads((T.LT / "sealed" / "cr_prospective.sha256").read_text())
    path = T.LT / "sealed" / s["file"]
    P = pd.read_csv(path, dtype={"province_code": str})
    # reproduce the sealed values from the committed snapshot (same code path as cpi_refresh_seal.py; nothing written)
    S = T.stack().copy()
    R = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    S = S.merge(R[KEY + [f"{c}_r" for c in CPI]], on=KEY, how="left")
    hit = S["lead"] >= 2
    for c in CPI:
        S.loc[hit, c] = S.loc[hit, f"{c}_r"]
    Q = T.run(T.U2, [ORIGIN], S=S)
    Q = Q[Q["lead"] <= 4]
    rp = []
    for x in Q.itertuples():
        iss = F.issue(ORIGIN, "A" if x.lead == 1 else "B")
        h = F.pi_h(iss, ORIGIN + int(x.lead))
        rp.append({"province_code": x.province_code, "lead": int(x.lead), "p_re": h["pi_H"] * x.pi_P, "iss_re": iss})
    M = P.merge(pd.DataFrame(rp), on=["province_code", "lead"])
    labels = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv")
    sws = pd.read_csv(T.EXP / "FORECAST_RESEARCH" / "data" / "sws_rounds_primary.csv")
    cpi = pd.read_csv(T.EXP / "E41_Lead2_Audit" / "data_acquired" / "cpi_index_ACP22.csv")
    v = pd.to_numeric(cpi["value"], errors="coerce")
    cpi_last = cpi[v.notna() & (cpi["Period"] != "Ave")].assign(m=lambda d: d["Year"] * 12 + pd.to_datetime(d["Period"], format="%b").dt.month - 1)["m"].max()
    return {"file": s["file"], "sha256_recorded": s["sha256"], "sha256_now": T.sha256(path), "intact": T.sha256(path) == s["sha256"],
            "sealed_at": s["sealed_at"], "seal_commit": "80bbe98", "targets": s["targets"], "rows": int(len(P)),
            "issue_dates": sorted(P["issue_date"].unique()), "leads": sorted(P["lead"].unique().tolist()),
            "reproduced_from_snapshot_max_abs": float((M["probability"] - M["p_re"]).abs().max()),
            "issue_dates_reproduced": bool((M["issue_date"] == M["iss_re"]).all()),
            "input_snapshot_sha256": {p: T.sha256(T.DATA / p) for p in ("stack_l2.csv", "known_price_l2.csv", "cpi_refresh.csv")}
                                     | {"sws_rounds_primary.csv": T.sha256(T.EXP / "FORECAST_RESEARCH" / "data" / "sws_rounds_primary.csv"),
                                        "cpi_index_ACP22.csv": T.sha256(T.EXP / "E41_Lead2_Audit" / "data_acquired" / "cpi_index_ACP22.csv")},
            "model_configuration": {"recipe": "lt_lib U2 unified LightGBM, refit at origin 2026-Q3", "columns": T.U2, "grid": T.GRID,
                                    "seed": T.SEED_UNI, "monotone": T.MONO_UP, "cpi_rule": "day 10 of month m+1",
                                    "hunger": "pi_H = Phi((h_last - 11.3)/max(sigma_h, 0.5)), S-AB schedule", "cut": 0.5},
            "no_sealed_outcome_in_data": {"labels_last_quarter": F.qs(int(labels["q"].max())),
                                          "sws_last_quarter": F.qs(int(sws["q"].max())), "cpi_last_month": ym(int(cpi_last)),
                                          "ok": bool(labels["q"].max() < 2026 * 4 + 3 and sws["q"].max() < 2026 * 4 + 3 and cpi_last < 2026 * 12 + 9)},
            "required_outcomes": [
                {"target": q, "sws": f"SWS Balance Luzon involuntary hunger, every {q} round (average of rounds)",
                 "cpi": f"PSA provincial CPI food and all items, all 3 months of {q}, five provinces",
                 "label_rule": "y = 1[H > 11.3] x 1[m_food > 0 or m_gap > 0] with the frozen 2021-22 P60 thresholds"}
                for q in s["targets"]],
            "scoring_rules": "per target quarter: the 5 sealed calls and probabilities vs the T43c label; descriptive (TP/FP/FN/TN, "
                             "Brier) until R1 can hold (>= 10 quarters, >= 40 rows); never refit, re-threshold or re-seal"}


def main():
    out = {"timing": timing(), "target": target(), "prospective": prospective()}
    (T.OUT / "evidence_gaps.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    t, p = out["timing"], out["prospective"]
    print("timing months", t["months_checked"], "verified", t["months_verified"], "unknown", t["months_unknown"], "tight", t["months_margin_le_14_days"])
    print("seal intact", p["intact"], "reproduced", p["reproduced_from_snapshot_max_abs"], p["issue_dates_reproduced"], p["no_sealed_outcome_in_data"])
    print(json.dumps({k: out["target"][k] for k in ("label_equals_price_share_overall", "label_equals_price_share_since_2023Q4", "lead2_rows",
                                                    "price_hunger_supported")}, indent=1))


if __name__ == "__main__":
    main()
