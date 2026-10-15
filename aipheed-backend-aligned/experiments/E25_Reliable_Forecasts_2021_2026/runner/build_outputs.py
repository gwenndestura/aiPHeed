"""E25 deliverables from the frozen run: BASELINE_COMPARISON.csv, PREDICTIONS_BY_QUARTER.csv,
FEATURE_ABLATION_RESULTS.csv, and ONE timeline forecast record (2025-Q1..2027-Q1) that the API, the dashboard and the
PDF all read (byte-identical copies, content SHA-256 inside). Then the PDF is rendered from that record.
Usage: python -B runner/build_outputs.py <run_id>"""
from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e25lib as E  # noqa: E402

EXP = guard.EXP
qk, qs = E.qk, E.qs
ROLE = {"B1_naive_persistence": "required (Obj 4-I, H3)", "B2_lr_combined": "required (Obj 4-IV, H3)",
        "B3_lr_gov_only": "required (Obj 4-II, H3)", "B4_lr_nlp_only": "required (Obj 4-III, H3)",
        "B5_lgbm_gov_only": "required (H3)", "B6_lgbm_nlp_only": "required (H3)",
        "PROPOSED_lgbm_combined": "required: proposed model (Chapter I)", "B1p_calibrated_persistence": "reference",
        "CLIM_training_rate": "reference (no skill)", "REF_always_HIGH": "diagnostic (no data)",
        "MAJ_training_majority": "diagnostic", "DIAG_ORACLE_H": "diagnostic (uses the outcome; not a forecast)",
        "DIAG_ORACLE_D": "diagnostic (uses the outcome; not a forecast)", "PCF21": "FINAL_T1 (E25 candidate)",
        "M4_21": "FINAL_T2 (E25 candidate)"}
SIGNAL = lambda p: "STRONG" if (p >= .8 or p <= .2) else ("MODERATE" if (p >= .65 or p <= .35) else "UNCERTAIN")  # noqa: E731
IN_SCOPE_E24V2 = {("T1", "B1_naive_persistence"), ("T1", "B1p_calibrated_persistence"), ("T1", "M2_lgbm_P_E24frozen"),
                  ("T2", "B1_naive_persistence")}


def role(m):
    if m in ROLE:
        return ROLE[m]
    if m.startswith("ABL_"):
        return "ablation of PROPOSED (H1)"
    return "E25 candidate"


def baseline_comparison(res, metrics):
    rows = []
    for key, tag, fin in (("T1_A", "T1 (approved label)", "PCF21"), ("T2", "T2 (exploratory, D > 0)", "M4_21")):
        for rs in ("R_A", "R_P"):
            rr = res[key][rs]
            for k, r in list(rr["by_lead"].items()) + [("pooled", rr["pooled"])]:
                tests = r["tests"].get(fin, {})
                mm = r["metrics"] if k != "pooled" else r["metrics_rows_pooled"]
                for m, x in mm.items():
                    t = tests.get(m, {})
                    rows.append({"target": tag, "row_set": rs, "lead": k, "model": m, "role": role(m),
                                 "n_dates": r["n_dates"], "HIGH": x["HIGH"], "LOW": x["LOW"],
                                 "evaluable": r.get("evaluable"), "accuracy": x["accuracy"],
                                 "balanced_accuracy": x["balanced_accuracy"], "precision": x["precision"],
                                 "recall": x["recall"], "F1": x["F1"], "ROC_AUC": x["ROC_AUC"], "Brier": x["Brier"],
                                 "log_score": x["log_score"],
                                 "per_date_brier_pooled": rr["pooled"]["per_date_brier"].get(m) if k == "pooled" else None,
                                 f"FINAL_minus_model_accuracy": t.get("acc_diff"),
                                 "FINAL_vs_model_accuracy_p_one_sided": t.get("acc_p_one_sided"),
                                 "FINAL_vs_model_accuracy_p_holm_B1_B6": t.get("acc_p_holm_B1_B6"),
                                 "FINAL_minus_model_brier_per_date": t.get("brier_diff_per_date_mean"),
                                 "FINAL_vs_model_brier_p_one_sided": t.get("brier_p_one_sided"),
                                 "FINAL_vs_model_brier_p_holm_B1_B6_B1p": t.get("brier_p_holm_B1_B6_B1p"),
                                 "dates_FINAL_better_brier": t.get("dates_better_brier"),
                                 "dates_FINAL_worse_brier": t.get("dates_worse_brier"),
                                 "FINAL_vs_model_auc_p": t.get("auc_p_one_sided"),
                                 "evidence": "development (all quarters examined before E25)"})
    return pd.DataFrame(rows)


def ablation(res):
    rows = []
    r1, pr = res["T1_A"]["R_A"]["by_lead"]["1"], res["T1_A"]["R_A"]["pooled"]
    pairs = [("PROPOSED_lgbm_combined", a, f"drop {a[4:]}") for a in ("ABL_no_FSSI", "ABL_no_FSSI_group", "ABL_no_cpi_dev")]
    pairs += [("PROPOSED_lgbm_combined", "B5_lgbm_gov_only", "drop all news features (= B5)"),
              ("PROPOSED_lgbm_combined", "B6_lgbm_nlp_only", "drop all government features (= B6)"),
              ("PCF21_NOW", "PCF21", "add Dnow (CPI months 1-2) to the D part"),
              ("PCF21_SUPP", "PCF21", "add supplementary SWS rounds as H inputs"),
              ("PCF21_HIER", "PCF21", "hierarchical D part (shrinkage + Dnow update)"),
              ("PCF21_MR", "PCF21", "mean-reverting H part instead of local level"),
              ("PCF21_LI", "PCF21", "leading indicator (regional food inflation change) in the H part"),
              ("CAL_PCF21", "PCF21", "temperature calibration"),
              ("ENS_PCF21_B1p", "PCF21", "average with calibrated persistence"),
              ("GATE_PCF21_B1p", "PCF21", "persistence gate")]
    for a, b, what in pairs:
        for k, rr in (("1", r1), ("pooled", pr)):
            # tests are stored as tests[a][b] when a is FINAL/PROPOSED/candidate and b a baseline; recompute view
            t = rr["tests"].get(a, {}).get(b) or {}
            mm = rr["metrics"] if k == "1" else rr["metrics_rows_pooled"]
            rows.append({"target": "T1", "lead": k, "variant": a, "reference": b, "change": what,
                         "brier_variant": mm[a]["Brier"], "brier_reference": mm[b]["Brier"],
                         "accuracy_variant": mm[a]["accuracy"], "accuracy_reference": mm[b]["accuracy"],
                         "brier_diff_per_date": t.get("brier_diff_per_date_mean"),
                         "brier_p_one_sided_variant_better": t.get("brier_p_one_sided"),
                         "evidence": "development; descriptive (not used to select)"})
    h = res["T1_A"]["hypotheses"]
    for f in ("FSSI", "cpi_dev"):
        rows.append({"target": "T1", "lead": "1", "variant": f"SHAP rank of {f} (PROPOSED)", "reference": "top 5 = strongest",
                     "change": f"pooled mean |SHAP| rank {h['shap_lead1']['pooled_rank'][f]}; in top 5 on "
                               f"{h['shap_lead1']['top5_share_of_dates'][f]:.0%} of dates; permutation dBrier "
                               f"{h['permutation_lead1'][f]['mean_dBrier']:+.4f} (95% CI {h['permutation_lead1'][f]['ci_low']:+.4f} "
                               f"to {h['permutation_lead1'][f]['ci_high']:+.4f})",
                     "evidence": "descriptive; H1 not testable (no evaluable lead)"})
    for k in ("1",):
        mm = res["T1_A"]["R_A"]["by_lead"][k]["metrics"]
        for m in ("DIAG_ORACLE_H", "DIAG_ORACLE_D"):
            rows.append({"target": "T1", "lead": k, "variant": m, "reference": "PCF21",
                         "change": "realized H (or D) inserted: shows where the difficulty lies",
                         "brier_variant": mm[m]["Brier"], "brier_reference": mm["PCF21"]["Brier"],
                         "accuracy_variant": mm[m]["accuracy"], "accuracy_reference": mm["PCF21"]["accuracy"],
                         "evidence": "diagnostic only (uses the outcome)"})
    return pd.DataFrame(rows)


def approx_ci(h, n=600):
    se = np.sqrt(h * (100 - h) / n)
    return [round(h - 1.96 * se, 1), round(h + 1.96 * se, 1)]


def build_record(run_id, res, P1, D1, P2, pipe):
    rounds = E.load_rounds()
    comp, c26, D = E.load_components()
    T = E.Target("T1", "A", rounds, D)
    proto = (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0]
    seal_dir = sorted((EXP / "runs").glob("SEAL_E25_*"))[-1]
    seal = json.loads((seal_dir / "SEAL.json").read_text(encoding="utf-8"))
    sb = (seal_dir / "prospective_forecasts.csv").read_bytes()
    assert hashlib.sha256(sb).hexdigest() == seal["sha256_forecasts"]
    S25 = pd.read_csv(io.BytesIO(sb), dtype={"province_code": str})
    v2d = EXP / "inputs" / "e24v2" / "runs" / "SEAL_20261013T164218Z"
    v2b = guard.read_allowed_text(v2d / "prospective_forecasts.csv").encode("utf-8")
    v2meta = json.loads(guard.read_allowed_text(v2d / "SEAL_PROSPECTIVE.json"))
    assert hashlib.sha256(v2b).hexdigest() == v2meta["sha256"]
    S24 = pd.read_csv(io.BytesIO(v2b), dtype={"province_code": str})
    S24 = S24[[(t, m) in IN_SCOPE_E24V2 for t, m in zip(S24["target"], S24["model"])]]
    quarters = [qs(i) for i in range(qk("2025-Q1"), qk("2027-Q1") + 1)]
    out = []
    fin = P1[(P1["model"] == "PCF21") & (P1["lead"] == 1)]
    b1 = P1[(P1["model"] == "B1_naive_persistence") & (P1["lead"] == 1)].set_index(["target_quarter", "province_code"])
    prop = P1[(P1["model"] == "PROPOSED_lgbm_combined") & (P1["lead"] == 1)].set_index(["target_quarter", "province_code"])
    det = D1[(D1["model"] == "PCF21") & (D1["lead"] == 1)].set_index(["t", "province_code"])
    m4 = P2[(P2["model"] == "M4_21") & (P2["lead"] == 1)].set_index(["target_quarter", "province_code"])
    for q in quarters:
        rq = rounds[rounds["quarter"] == q]
        Dq = D[D["quarter"] == q].set_index("province_code")
        e = {"quarter": q, "display": f"Q{q[-1]} {q[:4]}"}
        if q <= "2026-Q2":
            e["kind"] = "BACKTEST (development evidence: outcomes examined before E25)"
            prodH = rq[rq["definition_A"]]["H"]
            e["measured_regional"] = {
                "sws_hunger_balance_luzon_pct": round(float(prodH.mean()), 2) if len(prodH) else None,
                "approx_95ci_n600_srs": approx_ci(float(prodH.mean())) if len(prodH) else None,
                "ci_note": "approximate sampling interval assuming n = 600 simple random sampling; SWS publishes its own margin",
                "rounds": rq[["round", "H", "definition_A", "source"]].to_dict("records"),
                "status": ("measured (production round)" if len(prodH) else
                           ("DISPUTED: supplementary round(s) only; no label under the approved reading A" if len(rq)
                            else "MISSING: no SWS round in this quarter"))}
            fo = fin[fin["target_quarter"] == q]
            prov = {}
            for p in E.PROVS:
                d = {"province": E.PNAME[p],
                     "measured": {"food_cpi_yoy_pct": round(float(Dq.loc[p, "F"]), 3) if p in Dq.index else None,
                                  "D_relative_food_inflation_pp": round(float(Dq.loc[p, "D"]), 3) if p in Dq.index else None,
                                  "ci": "PSA publishes no confidence interval for provincial CPI"}}
                row = fo[fo["province_code"] == p]
                if len(row):
                    r = row.iloc[0]
                    dd = det.loc[(r["t"], p)]
                    d["actual_label"] = "HIGH" if r["y"] == 1 else "LOW"
                    d["S1_measured"] = round(float(r["value"]), 3)
                    d["threshold"] = round(float(r["threshold"]), 3)
                    d["forecast"] = {"model": "PCF21 (FINAL_T1)", "lead_quarters": 1, "origin": r["origin"],
                                     "information_cutoff": (pd.Timestamp(r["origin"]) - pd.Timedelta(seconds=1)).isoformat() + "+08:00",
                                     "p_high": round(float(r["score"]), 4), "decision": "HIGH" if r["score"] >= .5 else "LOW",
                                     "signal": SIGNAL(float(r["score"])), "z": round(float(dd["z"]), 3),
                                     "S1_forecast": round(float(dd["mu_S1"]), 2),
                                     "S1_80pct_interval": [round(float(dd["mu_S1"] - E.Z80 * dd["sd_S1"]), 2),
                                                           round(float(dd["mu_S1"] + E.Z80 * dd["sd_S1"]), 2)],
                                     "regional_part_H_minus_tau": round(float(dd["regional_part"]), 2),
                                     "provincial_part_2D": round(float(dd["provincial_part"]), 2),
                                     "variance_share_regional": round(float(dd["var_share_regional"]), 3),
                                     "indicative_only": True, "correct": bool((r["score"] >= .5) == (r["y"] == 1))}
                    d["persistence"] = int(b1.loc[(q, p), "score"]) if (q, p) in b1.index else None
                    d["proposed_lgbm_p_high"] = round(float(prop.loc[(q, p), "score"]), 4) if (q, p) in prop.index else None
                else:
                    d["actual_label"] = None
                    d["forecast"] = None
                    d["state"] = ("NO LABEL under the approved reading (no production SWS round)" if q in ("2025-Q2", "2025-Q3")
                                  else "NO LEAD-1 FORECAST (fewer than 8 labelled training quarters)")
                if (q, p) in m4.index:
                    d["price_pressure_forecast"] = {"model": "M4_21 (FINAL_T2, exploratory)",
                                                    "p_above_regional_mean": round(float(m4.loc[(q, p), "score"]), 4),
                                                    "actual": "ABOVE" if m4.loc[(q, p), "y"] == 1 else "BELOW",
                                                    "indicative_only": True}
                prov[p] = d
            e["provinces"] = prov
        elif q in ("2026-Q3", "2026-Q4"):
            e["kind"] = "SEALED FORECAST, OUTCOME PENDING"
            e["measured_regional"] = {"status": "PROTECTED: not authorized; never opened" if q == "2026-Q3"
                                      else "NOT YET PUBLISHED"}
            prov = {p: {"province": E.PNAME[p], "sealed": []} for p in E.PROVS}
            for _, r in S24[(S24["target_quarter"] == q)].iterrows():
                prov[r["province_code"]]["sealed"].append(
                    {"seal": f"E24v2 SEAL_20261013T164218Z (sha256 {v2meta['sha256']})", "origin": "2026-07-01",
                     "information_cutoff": "2026-06-30T23:59:59+08:00",
                     "target": r["target"], "arm": r["model"], "lead": int(r["lead"]), "p": round(float(r["score"]), 4),
                     "in_scope_note": "in-scope arm (2021+ inputs only)", "indicative_only": True,
                     "outcome": "PENDING (score only after authorization)"})
            for _, r in S25[(S25["target_quarter"] == q) & S25["arm"].isin(["PCF21", "B1_naive_persistence",
                                                                            "B1p_calibrated_persistence", "M3_21"])].iterrows():
                x = {"seal": f"E25 {seal_dir.name} (sha256 {seal['sha256_forecasts']})", "origin": r["origin"],
                     "information_cutoff": r["info_cutoff"], "target": r["target"], "arm": r["arm"], "lead": int(r["lead"]),
                     "p": round(float(r["p"]), 4), "signal": SIGNAL(float(r["p"])), "indicative_only": True,
                     "outcome": "PENDING (score only after authorization)"}
                if r["arm"] == "PCF21":
                    x.update({"FINAL_T1": True, "S1_forecast": round(float(r["mu_S1"]), 2),
                              "S1_80pct_interval": [round(float(r["lo80_S1"]), 2), round(float(r["hi80_S1"]), 2)],
                              "threshold": round(float(r["tau"]), 3), "z": round(float(r["z"]), 3),
                              "regional_part_H_minus_tau": round(float(r["regional_part"]), 2),
                              "provincial_part_2D": round(float(r["provincial_part"]), 2),
                              "variance_share_regional": round(float(r["var_share_regional"]), 3)})
                prov[r["province_code"]]["sealed"].append(x)
            e["provinces"] = prov
            e["missing_arms"] = json.loads((seal_dir / "seal_info.json").read_text(encoding="utf-8"))["missing_input_arms"] \
                if q == "2026-Q4" else None
        else:
            e["kind"] = "OPERATIONAL FORECAST"
            e["status"] = pipe["status"]
            e["missing_inputs"] = pipe["missing"]
            e["information_cutoff"] = pipe["period"]["cutoff"]
            e["who_supplies"] = {
                "SWS September 2026 round (Balance Luzon) and its publication date": "researcher authorizes; source SWS",
                "Provincial food CPI YoY, July-November 2026, with RSSO IV-A release dates": "researcher authorizes; source PSA",
                "2026-Q4 news articles (Oct-Dec 2026) with publication times": "researcher authorizes; aiPHeed news fetchers",
                "Cutoff 2026-12-31 23:59:59 PHT": "time (cannot be produced earlier)"}
            e["pipeline_record_sha256"] = pipe["content_sha256"]
            prov = {p: {"province": E.PNAME[p], "state": "MISSING INPUTS - no forecast (this is not a low-risk state)",
                        "sealed_evaluation_forecasts": []} for p in E.PROVS}
            for _, r in S25[(S25["target_quarter"] == q) & (S25["arm"] == "PCF21")].iterrows():
                prov[r["province_code"]]["sealed_evaluation_forecasts"].append(
                    {"seal": f"E25 {seal_dir.name}", "arm": "PCF21", "lead": int(r["lead"]), "p": round(float(r["p"]), 4),
                     "note": "earlier-information sealed forecast for evaluation; not the operational forecast; indicative only"})
            e["provinces"] = prov
        out.append(e)
    rec = {"title": "aiPHeed E25 forecast timeline, 2025-Q1 to 2027-Q1",
           "run_id": run_id, "protocol_sha256": proto, "prediction_seal_T1": res.get("_seal_T1"),
           "label_definition": "S1 = H + 2D; HIGH if S1 > tau (median of the S1 labels published before the origin)",
           "score_is_constructed": ("The score is a constructed composite of regional SWS hunger and provincial relative food "
                                    "inflation. It is NOT a measured food-insecurity rate."),
           "indicative_only_reason": ("No lead is validated: on the approved label no lead has 5 LOW test rows, and no sealed "
                                      "forecast has been scored. Every forecast is indicative only."),
           "fnri_anchor": {"value": "22.6% moderate+severe FIES, CALABARZON, NNS 2025 (secondary reporting, regional)",
                           "ci": "not available in the authorized file"},
           "signal_rule": "STRONG p <= 0.20 or >= 0.80; MODERATE 0.20-0.35 or 0.65-0.80; UNCERTAIN 0.35-0.65",
           "criteria_T1": res["T1_A"]["criteria_C1_C9"], "proposed_criteria_T1": {
               k: v for k, v in res["T1_A"]["proposed_P1_P9"].items() if k != "P6_reliable_leads"},
           "criteria_T2_exploratory": res["T2"]["criteria_C1_C9"], "quarters": out}
    content = json.dumps(rec, sort_keys=True, default=str).encode("utf-8")
    rec["content_sha256"] = hashlib.sha256(content).hexdigest()
    return rec


def write_pdf(rec, path: Path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
    st = getSampleStyleSheet()
    els = [Paragraph("aiPHeed forecast timeline (E25), 2025-Q1 to 2027-Q1", st["Title"]),
           Paragraph(rec["score_is_constructed"], st["Normal"]), Paragraph(rec["indicative_only_reason"], st["Normal"]),
           Paragraph(f"Record SHA-256: {rec['content_sha256']}", st["Normal"]), Spacer(1, 8)]
    for q in rec["quarters"]:
        els.append(Paragraph(f"{q['display']} - {q['kind']}", st["Heading3"]))
        if q["kind"].startswith("BACKTEST"):
            mr = q["measured_regional"]
            els.append(Paragraph(f"Measured SWS hunger (Balance Luzon): {mr['sws_hunger_balance_luzon_pct']} "
                                 f"({mr['status']})", st["Normal"]))
            rows = [["Province", "Food CPI YoY", "D", "P(HIGH)", "80% S1 interval", "Signal", "Actual"]]
            for p, d in q["provinces"].items():
                f = d.get("forecast")
                rows.append([d["province"], d["measured"]["food_cpi_yoy_pct"], d["measured"]["D_relative_food_inflation_pp"],
                             f["p_high"] if f else "MISSING", f"{f['S1_80pct_interval']}" if f else "-",
                             f["signal"] if f else "-", d.get("actual_label") or "no label"])
            els.append(Table(rows))
        elif q["kind"].startswith("SEALED"):
            rows = [["Province", "Seal", "Arm", "Lead", "P"]]
            for p, d in q["provinces"].items():
                for s in d["sealed"]:
                    rows.append([d["province"], s["seal"][:22], s["arm"], s["lead"], s["p"]])
            els.append(Table(rows))
            els.append(Paragraph("Outcome pending: scored only after the researcher authorizes the outcomes.", st["Normal"]))
        else:
            els.append(Paragraph(f"Status: {q['status']} - no forecast is shown. Missing inputs:", st["Normal"]))
            for m in q["missing_inputs"]:
                els.append(Paragraph("- " + m, st["Normal"]))
        els.append(Spacer(1, 6))
    SimpleDocTemplate(str(path), pagesize=A4).build(els)


def main(run_id):
    rd = EXP / "runs" / run_id
    res = json.loads((rd / "results.json").read_text(encoding="utf-8"))
    seals = json.loads((rd / "SEALS.json").read_text(encoding="utf-8"))
    P1 = pd.read_csv(rd / "predictions_T1_A.csv", dtype={"province_code": str})
    assert hashlib.sha256((rd / "predictions_T1_A.csv").read_bytes()).hexdigest() == seals["T1_A"]
    P2 = pd.read_csv(rd / "predictions_T2.csv", dtype={"province_code": str})
    D1 = pd.read_csv(rd / "details_T1_A.csv", dtype={"province_code": str})
    res["_seal_T1"] = seals["T1_A"]
    baseline_comparison(res, None).to_csv(EXP / "BASELINE_COMPARISON.csv", index=False, lineterminator="\n",
                                          float_format="%.6g")
    ablation(res).to_csv(EXP / "FEATURE_ABLATION_RESULTS.csv", index=False, lineterminator="\n", float_format="%.6g")
    # predictions by quarter: every model, lead 1, both targets + sealed forecasts
    keep = ["target", "lead", "t", "origin", "target_quarter", "province_code", "model", "score", "y", "y_last", "value",
            "threshold"]
    pq = pd.concat([P1[P1["lead"] == 1][keep], P2[P2["lead"] == 1][keep]], ignore_index=True)
    pq["province"] = pq["province_code"].map(E.PNAME)
    pq["status"] = "backtest (development evidence)"
    sd = sorted((EXP / "runs").glob("SEAL_E25_*"))[-1]
    S = pd.read_csv(sd / "prospective_forecasts.csv", dtype={"province_code": str})
    S = S.rename(columns={"arm": "model", "p": "score", "tau": "threshold"})
    S["status"] = f"sealed {sd.name}; outcome pending"
    S["origin"] = S["origin"].str[:10]
    pq = pd.concat([pq, S[["target", "lead", "origin", "target_quarter", "province_code", "province", "model", "score",
                           "threshold", "status"]]], ignore_index=True)
    pq.to_csv(EXP / "PREDICTIONS_BY_QUARTER.csv", index=False, lineterminator="\n", float_format="%.6g")
    pipe = json.loads((EXP / "backend_dev" / "data" / "quarterly_runs" / "2027-Q1" / "forecast_record.json").read_text(encoding="utf-8"))
    rec = build_record(run_id, res, P1, D1, P2, pipe)
    blob = json.dumps(rec, indent=1, default=str).encode("utf-8")
    for p in (rd / "e25_forecast_record.json", EXP / "backend_dev" / "data" / "e25" / "e25_forecast_record.json",
              EXP / "dashboard_dev" / "public" / "e25_forecast_record.json"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)
    write_pdf(rec, EXP / "dashboard_dev" / "public" / "aiPHeed_E25_forecast_report.pdf")
    print("record", rec["content_sha256"], "bytes", hashlib.sha256(blob).hexdigest())


if __name__ == "__main__":
    main(sys.argv[1])
