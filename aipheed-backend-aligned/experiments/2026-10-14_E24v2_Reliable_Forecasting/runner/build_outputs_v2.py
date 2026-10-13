"""E24v2 deliverable tables, pipeline evidence status, pipeline cycles, dashboard JSON and PDF, all from single
sources (no typed numbers).  Usage: python -B runner/build_outputs_v2.py <BX run> <DEV run>

Order: (1) evidence_status.json from the frozen results -> (2) quarterly pipeline cycles (live 2027-Q1 and the
REPLAY of the 2026-Q3 cycle) -> (3) CSV deliverables -> (4) dashboard JSON + PDF from the same records."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

EXP = Path(__file__).resolve().parents[1]
BD = EXP / "backend_dev"
sys.path.insert(0, str(BD))
from app.quarterly.config import load_period  # noqa: E402
from app.quarterly.forecaster_v2 import make_pcf_forecaster  # noqa: E402
from app.quarterly.registry import Registry, SnapshotStore  # noqa: E402
from app.quarterly.update import load_latest, run_update  # noqa: E402

PROV = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
        "PH040500000": "Batangas"}
NAMES = {"B1_naive_persistence": "B1 Naive persistence (Obj. 4-I)", "B2_lr_combined": "B2 LR combined (Obj. 4-IV)",
         "B3_lr_gov_only": "B3 LR government (Obj. 4-II)", "B4_lr_nlp_only": "B4 LR news (Obj. 4-III)",
         "B5_lgbm_gov_only": "B5 LightGBM government (SOP Q3)", "B6_lgbm_nlp_only": "B6 LightGBM news (SOP Q3)",
         "PROPOSED_lgbm_combined": "Proposed LightGBM (news + government)",
         "MAJ_training_majority": "Training majority (diagnostic)", "FINAL_E24F": "E24-F persistence-gated (E24)",
         "B1p_calibrated_persistence": "B1p Calibrated persistence (E24v2, stricter baseline)",
         "FINAL_V2_PCF": "E24v2 FINAL: probabilistic component forecaster (PCF)",
         "PCF_NOW_A3": "PCF with D nowcast (amendment A3; exploratory)",
         "PCF_S_supplementary": "PCF + supplementary SWS rounds (exploratory; conceived after E24 errors)",
         "PCF_n300_sensitivity": "PCF, SWS n = 300 (sensitivity)",
         "FINAL_V2_M4_pcf_D_now": "E24v2 FINAL (T2): D nowcast model M4", "M3_pcf_D": "M3 D model (latest D only)",
         "M1_lr_P_E24frozen": "M1 LR on label history (E24-frozen)", "M2_lgbm_P_E24frozen": "M2 LightGBM on label history (E24-frozen)",
         "M4_pcf_D_now": "M4 D nowcast model", "CLIM_province_rate": "Province climatology (descriptive)",
         "ABL_lr_P": "LR on label history (E24 ablation)", "ABL_lgbm_P": "LightGBM on label history (E24 ablation)",
         "M1_lr_P_1995window": "M1 LR on label history, 1995+ window"}
METRICS = ["accuracy", "balanced_accuracy", "precision", "recall", "F1", "specificity", "ROC_AUC", "Brier",
           "TP", "FP", "FN", "TN"]


def j(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------ (1) evidence status
def evidence(BX: dict, DEV: dict) -> dict:
    lt = BX["lead_time"]
    ev = {"T1": {}, "T2": {}, "_rule": "T2 lead k is SUPPORTED when the frozen back-cast (1997-2020, never examined "
          "before) meets the E23 reliability rule for M4 against persistence at every lead <= k; STRICT when it also "
          "beats calibrated persistence. T1 is NOT_ESTABLISHED at every lead: its only evaluations are development "
          "quarters (C9 not assessable) until the prospective seals are scored or the A2 back-cast runs."}
    for k in map(str, range(1, 9)):
        ok, strict = lt["B1_naive_persistence"]["per_lead_pass"][k], lt["B1p_calibrated_persistence"]["per_lead_pass"][k]
        ok = ok and k_le(k, lt["B1_naive_persistence"]["furthest_reliable_lead"])
        strict = strict and k_le(k, lt["B1p_calibrated_persistence"]["furthest_reliable_lead"])
        ev["T2"][k] = {"status": "SUPPORTED_STRICT" if strict else ("SUPPORTED" if ok else "NOT_ESTABLISHED"),
                       "basis": "back-cast 1997-2020 (class A, unseen); provincial relative food-price pressure only"}
        d = DEV["T1"].get(k)
        ev["T1"][k] = {"status": "NOT_ESTABLISHED",
                       "basis": ("development quarters only" + (f"; {d['n_test_quarters']} quarters, LOW rows {d['LOW']}"
                                                                if d else "") +
                                 "; prospective seals pending outcome authorization; A2 back-cast awaits SWS history")}
    return ev


def k_le(k: str, furthest: int) -> bool:
    return int(k) <= furthest


# ------------------------------------------------------------------------------------------ (2) pipeline cycles
def cycles(ev: dict):
    (BD / "config" / "evidence_status.json").write_text(json.dumps(ev, indent=1), encoding="utf-8")
    reg = Registry(BD / "config" / "quarterly_sources.json")
    f = make_pcf_forecaster(ev)
    rec_runs = BD / "data" / "quarterly_runs"
    store = SnapshotStore(BD / "data" / "quarterly_store")
    live = run_update(load_period(BD / "config" / "forecast_period.json"), reg, rec_runs, store=store, forecaster=f)
    rep = run_update(load_period(BD / "config" / "replay_2026Q3.json"), reg, rec_runs, store=store, forecaster=f,
                     replay=True)
    live = load_latest(rec_runs)
    rep = j(rec_runs / "replays" / "2026-Q3" / "forecast_record.json")
    return live, rep


# ------------------------------------------------------------------------------------------ (3) tables
def metric_rows(res: dict, target: str, cls: str, final: str, nested: bool) -> list[dict]:
    """nested=True: res[k]["tests"][model][baseline] (back-cast); else res[k]["tests"][baseline] for the final model."""
    rows = []
    for k, r in res.items():
        for m, mm in r["metrics"].items():
            row = {"evidence_class": cls, "target": target, "lead": int(k), "model": m, "model_name": NAMES.get(m, m),
                   "n_test_quarters": r["n_test_quarters"], "HIGH": r["HIGH"], "LOW": r["LOW"],
                   "evaluable": r.get("evaluable"), **{q: mm.get(q) for q in METRICS}}
            src = r["tests"].get(m) if nested else (r["tests"] if m == final else None)
            for b, sfx in (("B1_naive_persistence", "B1"), ("B1p_calibrated_persistence", "B1p")):
                tb = (src or {}).get(b)
                if tb:
                    row.update({f"acc_diff_vs_{sfx}": tb["acc_diff"], f"acc_p_vs_{sfx}": tb["acc_p_one_sided"],
                                f"brier_diff_vs_{sfx}": tb["brier_diff"], f"brier_p_vs_{sfx}": tb["brier_p_one_sided"]})
            rows.append(row)
    return rows


def tables(BX, DEV, bxrun: Path, devrun: Path):
    rows = metric_rows(DEV["T1"], "T1", "C development (E24 rows)", "FINAL_V2_PCF", False)
    rows += metric_rows(DEV["T2"], "T2", "C development (E24 rows)", "FINAL_V2_M4_pcf_D_now", False)
    rows += metric_rows(BX["by_lead"], "T2_BX", "A confirmatory back-cast 1997-2020 (unseen)", "M4_pcf_D_now", True)
    late = DEV["late_2026"]
    for key, v in late.items():
        tg, k = key.split("_k")
        for m, mm in v.items():
            rows.append({"evidence_class": "C 2026-Q1/Q2 targets (viewed in E18; never used to select)", "target": tg,
                         "lead": int(k), "model": m, "model_name": NAMES.get(m, m), "accuracy": mm["accuracy"],
                         "Brier": mm["brier"], "n_rows": mm["rows"]})
    # always-HIGH reference on each development row set
    for t in ("T1", "T2"):
        pr = pd.read_csv(devrun / f"predictions_{t}_dev.csv", dtype={"province_code": str})
        for k, g in pr[pr["model"] == "B1_naive_persistence"].groupby("lead"):
            rows.append({"evidence_class": "C development (E24 rows)", "target": t, "lead": int(k),
                         "model": "REF_always_HIGH", "model_name": "Always HIGH (reference; not a forecaster)",
                         "n_test_quarters": int(g["origin"].nunique()), "HIGH": int(g["y"].sum()),
                         "LOW": int((1 - g["y"]).sum()), "accuracy": float(g["y"].mean()), "balanced_accuracy": 0.5})
    B = pd.DataFrame(rows).sort_values(["evidence_class", "target", "lead", "model"])
    B.to_csv(EXP / "BASELINE_COMPARISON.csv", index=False, lineterminator="\n")
    # PREDICTIONS_BY_QUARTER: lead-1 development rows, every arm side by side, plus PCF components and noise z
    pq = []
    comp = pd.read_csv(devrun / "pcf_T1_components.csv", dtype={"province_code": str})
    for t in ("T1", "T2"):
        pr = pd.read_csv(devrun / f"predictions_{t}_dev.csv", dtype={"province_code": str})
        pr = pr[pr["lead"] == 1]
        w = pr.pivot_table(index=["target_quarter", "feature_quarter", "origin", "province_code", "y", "y_last",
                                  "value", "threshold"],
                           columns="model", values="score").reset_index()
        w.insert(0, "target", t)
        w.insert(4, "province", w["province_code"].map(PROV))
        w["label_changed"] = (w["y"] != w["y_last"]).astype(int)
        if t == "T1":
            c = comp[comp["lead"] == 1][["feature_quarter", "province_code", "mu_H", "V_H", "sigma_eta", "gap", "mu_D",
                                         "sigma_D", "mu_S1"]]
            w = w.merge(c, on=["feature_quarter", "province_code"], how="left")
        pq.append(w)
    pd.concat(pq, ignore_index=True).to_csv(EXP / "PREDICTIONS_BY_QUARTER.csv", index=False, lineterminator="\n")
    # FEATURE_ABLATION_RESULTS: information-set ablations
    ab = []
    for k, r in BX["by_lead"].items():
        base = r["metrics"]["B1_naive_persistence"]
        for m, info in (("M3_pcf_D", "latest published quarterly D"), ("M4_pcf_D_now", "D nowcast (months 1-2 of the reference quarter) + latest D"),
                        ("M1_lr_P_E24frozen", "label-history block P (5 features)"), ("M2_lgbm_P_E24frozen", "label-history block P, LightGBM"),
                        ("B1p_calibrated_persistence", "last label only, calibrated"), ("CLIM_province_rate", "province identity only")):
            mm = r["metrics"][m]
            tb = r["tests"].get(m, {}).get("B1p_calibrated_persistence", {}) if m.startswith("M") else {}
            ab.append({"evidence_class": "A back-cast 1997-2020", "target": "T2 (D > 0)", "lead": int(k), "arm": m,
                       "information_set": info, "accuracy": mm["accuracy"], "Brier": mm["Brier"], "ROC_AUC": mm["ROC_AUC"],
                       "accuracy_minus_persistence": mm["accuracy"] - base["accuracy"],
                       "Brier_minus_calibrated_persistence": mm["Brier"] - r["metrics"]["B1p_calibrated_persistence"]["Brier"],
                       "brier_p_vs_calibrated_persistence": tb.get("brier_p_one_sided")})
    for k, r in DEV["T1"].items():
        base = r["metrics"]["B1_naive_persistence"]
        for m, info in (("FINAL_V2_PCF", "H local level + D (latest)"), ("PCF_NOW_A3", "H local level + D nowcast"),
                        ("PCF_S_supplementary", "H with supplementary SWS rounds + D (latest)"),
                        ("PCF_n300_sensitivity", "as PCF, SWS n = 300"), ("ABL_lgbm_P", "label history, LightGBM (E24)"),
                        ("ABL_lr_P", "label history, LR (E24)"), ("PROPOSED_lgbm_combined", "news + government (E23/E24)"),
                        ("B6_lgbm_nlp_only", "news only (E23/E24)"), ("B5_lgbm_gov_only", "government only (E23/E24)")):
            if m not in r["metrics"]:
                continue
            mm = r["metrics"][m]
            ab.append({"evidence_class": "C development", "target": "T1 (approved)", "lead": int(k), "arm": m,
                       "information_set": info, "accuracy": mm["accuracy"], "Brier": mm["Brier"], "ROC_AUC": mm["ROC_AUC"],
                       "accuracy_minus_persistence": mm["accuracy"] - base["accuracy"],
                       "Brier_minus_calibrated_persistence": mm["Brier"] - r["metrics"]["B1p_calibrated_persistence"]["Brier"]})
    pd.DataFrame(ab).to_csv(EXP / "FEATURE_ABLATION_RESULTS.csv", index=False, lineterminator="\n")
    return B


# ------------------------------------------------------------------------------------------ provincial validity
def provincial_validity(devrun: Path) -> dict:
    out = {}
    for f, key in (("subsistence_pop_prov_huc_2018_2023.csv", "Subsistence Incidence"),
                   ("poverty_pop_prov_huc_2018_2023.csv", "Poverty Incidence")):
        d = pd.read_csv(EXP / "acquisition" / f)
        g = [c for c in d.columns if c.startswith("Geolocation") and not c.endswith("_code")][0]
        m = [c for c in d.columns if c.startswith("Threshold") and not c.endswith("_code")][0]
        rows = []
        for name in PROV.values():
            pat = "Quezon (w/o" if name == "Quezon" else name
            s = d[d[g].str.contains(pat, regex=False) & ~d[g].str.contains("Quezon City")]
            for y, gy in s.groupby("Year"):
                val = lambda k: float(gy[gy[m].str.contains(k, regex=False)]["value"].iloc[0])  # noqa: E731
                rows.append({"province": name, "year": int(y), "value": val(key), "ci_low": val("Lower"),
                             "ci_high": val("Upper"), "cv": val("Coefficient")})
        out[key] = rows
    pr = pd.read_csv(devrun / "predictions_T1_dev.csv", dtype={"province_code": str})
    p1 = pr[(pr["lead"] == 1) & (pr["model"] == "FINAL_V2_PCF")]
    t2 = pd.read_csv(devrun / "predictions_T2_dev.csv", dtype={"province_code": str})
    t2 = t2[(t2["lead"] == 1) & (t2["model"] == "B1_naive_persistence")]
    summ = []
    for c, n in PROV.items():
        sub = [r for r in out["Subsistence Incidence"] if r["province"] == n]
        pov = [r for r in out["Poverty Incidence"] if r["province"] == n]
        summ.append({"province": n, "mean_D_2021_2026": float(t2[t2["province_code"] == c]["value"].mean()),
                     "mean_PCF_p_high_dev": float(p1[p1["province_code"] == c]["score"].mean()),
                     "subsistence_2023": next(r["value"] for r in sub if r["year"] == 2023),
                     "poverty_2023": next(r["value"] for r in pov if r["year"] == 2023),
                     "poverty_mean_2018_2023": float(np.mean([r["value"] for r in pov]))})
    S = pd.DataFrame(summ)
    out["summary"] = summ
    out["spearman_n5_descriptive"] = {
        "mean_D_vs_poverty_mean": float(spearmanr(S["mean_D_2021_2026"], S["poverty_mean_2018_2023"]).statistic),
        "mean_D_vs_subsistence_2023": float(spearmanr(S["mean_D_2021_2026"], S["subsistence_2023"]).statistic),
        "pcf_p_vs_poverty_mean": float(spearmanr(S["mean_PCF_p_high_dev"], S["poverty_mean_2018_2023"]).statistic)}
    return out


# ------------------------------------------------------------------------------------------ (4) dashboard + PDF
def dashboard(live, rep, ev, BX, DEV, bxrun, devrun, pv):
    seals = []
    for d in sorted((EXP / "runs").glob("SEAL_*")):
        s = j(d / "SEAL_PROSPECTIVE.json")
        f = pd.read_csv(d / "prospective_forecasts.csv", dtype={"province_code": str})
        assert sha(d / "prospective_forecasts.csv") == s["sha256"]
        keep = f[f["model"].isin(["FINAL_V2_PCF", "PCF_NOW_A3", "B1_naive_persistence", "FINAL_V2_M4_pcf_D_now"])]
        seals.append({"seal_id": d.name, "sha256": s["sha256"], "created_utc": s["created_utc"], "origin": s["origin"],
                      "targets": s["targets"], "threshold_T1": s["threshold_T1"], "status": "PENDING_OUTCOME_AUTHORIZATION",
                      "rows": json.loads(keep.assign(province=keep["province_code"].map(PROV)).to_json(orient="records"))})
    lgu = j(EXP / "runs" / "lgu_analysis.json")
    t1 = DEV["T1"]["1"]
    goal = {"target": "T1 approved composite, lead 1 (FINAL_V2 = PCF)", "criteria": t1["criteria"],
            "goal_met": all(v is True for v in t1["criteria"].values()),
            "metrics": {m: {q: t1["metrics"][m].get(q) for q in ("accuracy", "balanced_accuracy", "Brier", "ROC_AUC")}
                        for m in ("FINAL_V2_PCF", "B1_naive_persistence", "B1p_calibrated_persistence",
                                  "PROPOSED_lgbm_combined", "FINAL_E24F")},
            "always_HIGH_accuracy": t1["HIGH"] / (t1["HIGH"] + t1["LOW"]), "n_test_quarters": t1["n_test_quarters"],
            "HIGH": t1["HIGH"], "LOW": t1["LOW"]}
    bx1 = BX["by_lead"]["1"]
    data = {"generated_from": {"bx_run": bxrun.name, "dev_run": devrun.name, "live_record_sha256": live["content_sha256"],
                               "replay_record_sha256": rep["content_sha256"],
                               "protocol_sha256": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]},
            "live": {k: live[k] for k in ("period", "status", "missing", "context_missing", "labels", "cutoff_reached",
                                          "mode", "forecast", "content_sha256")},
            "replay": {k: rep[k] for k in ("period", "status", "missing", "context_missing", "labels", "mode", "forecast",
                                           "content_sha256")},
            "seals": seals, "evidence": ev, "goal": goal,
            "confirmatory": BX["confirmatory"],
            "backcast_lead1": {m: {q: bx1["metrics"][m][q] for q in ("accuracy", "balanced_accuracy", "Brier", "ROC_AUC")}
                               for m in bx1["metrics"]},
            "backcast_lead_time": BX["lead_time"], "backcast_quarters": bx1["n_test_quarters"],
            "noise_ceiling": DEV["noise_ceiling"]["n600"], "provincial_validity": pv, "lgu_analysis": lgu,
            "caveats": ["Development copy. Nothing here is deployed or published.",
                        "Forecasts are model estimates of the approved composite label (regional SWS hunger + 2 x "
                        "provincial relative food inflation); they are not measured or official food-insecurity status.",
                        f"{lgu['province_mean_substitute']} of 142 LGUs have no PSA municipal poverty estimate in the "
                        "authorized data; their order within the province reflects population density only.",
                        "Among the LGUs that do have municipal estimates, density and poverty move in opposite "
                        "directions, so a high density-driven rank does not indicate higher poverty.",
                        "The provincial price-pressure indicator is validated on 1997-2020 back-cast quarters; the "
                        "approved composite forecast is not yet validated on unseen quarters."]}
    pub = EXP / "dashboard_dev" / "public"
    (pub / "e24v2_dashboard.json").write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str),
                                              encoding="utf-8")
    build_pdf(data, pub / f"aiPHeed_forecast_report_{live['period']['target_quarter']}_v2.pdf")
    build_pdf(data, pub / f"aiPHeed_forecast_report_{rep['period']['target_quarter']}_replay.pdf", replay=True)
    return data


def build_pdf(d, path, replay=False):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    st = getSampleStyleSheet()
    s = []
    P = lambda t, k="BodyText": s.append(Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;")  # noqa
                                                   .replace("–", "-").replace("—", "-"), st[k]))
    f = lambda x, n=3: "-" if x is None else f"{x:.{n}f}"  # noqa: E731
    T = lambda rows: (s.append(Table(rows, repeatRows=1)), s[-1].setStyle(TableStyle(  # noqa: E731
        [("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 7)])), s.append(Spacer(1, 6)))
    r = d["replay"] if replay else d["live"]
    P("aiPHeed quarterly forecast report - DA Region IV-A (development copy)", "Title")
    for k in ("target", "news", "cutoff", "mode"):
        P(r["labels"][k])
    P(f"Status: {r['status']}" + ("" if r["forecast"] else " - no forecast is shown for this period."))
    for m in r["missing"]:
        P("- missing: " + m)
    for m in r.get("context_missing", []):
        P("- " + m)
    if r["forecast"]:
        k1 = r["forecast"]["leads"]["1"]
        P(f"Composite risk forecast for {k1['target_quarter']} (model estimate)", "Heading2")
        P(f"Threshold {f(r['forecast']['threshold'], 2)}. Regional hunger component (SWS level, filtered): "
          f"{f(k1['H']['mu_H'], 1)} (latest round {k1['H']['last_round_quarter']}, {int(k1['H']['gap_quarters'])} "
          "quarters before the target).")
        rows = [["Province", "P(HIGH)", "Signal", "80% interval of S1", "Price pressure P(above mean)", "Signal",
                 "Evidence (risk / price)"]]
        for v in k1["provinces"].values():
            ri, pp = v["risk"], v["price_pressure"]
            rows.append([v["province"], f(ri["p_high"], 2), ri["signal"],
                         f"{f(ri['S1_80pct_interval'][0], 1)} to {f(ri['S1_80pct_interval'][1], 1)}",
                         f(pp["p_above_regional_mean"], 2), pp["signal"],
                         f"{ri['evidence']['status']} / {pp['evidence']['status']}"])
        T(rows)
        P("NOT_ESTABLISHED means the forecast is indicative only: its lead has not been validated on unseen quarters.")
        P("Top 10 cities and municipalities (relative ordinal estimate)", "Heading2")
        rows = [["Rank", "LGU", "Province", "Risk index", "Poverty value", "Basis"]]
        for x in r["forecast"]["lgu_ranking"][:10]:
            rows.append([int(x["rank_region"]), x["lgu_name"], x["province"], f(x["risk_index"], 4),
                         f(x["poverty_value_used"], 1), x["poverty_value_kind"][:30]])
        T(rows)
    P("Validation evidence", "Heading2")
    g = d["goal"]
    P(f"Approved target, lead 1 (development quarters: {g['n_test_quarters']}, HIGH {g['HIGH']} / LOW {g['LOW']}): "
      f"PCF accuracy {f(g['metrics']['FINAL_V2_PCF']['accuracy'])}, persistence "
      f"{f(g['metrics']['B1_naive_persistence']['accuracy'])}, always-HIGH {f(g['always_HIGH_accuracy'])}. "
      f"Forecasting goal met: {'yes' if g['goal_met'] else 'NO'}.")
    rows = [["Criterion", "Result"]] + [[k, "met" if v is True else ("not met" if v is False else str(v))]
                                        for k, v in g["criteria"].items()]
    T(rows)
    b = d["backcast_lead1"]
    P(f"Provincial price-pressure component, back-cast on {d['backcast_quarters']} unseen quarters (1997-2020), lead 1: "
      f"nowcast model accuracy {f(b['M4_pcf_D_now']['accuracy'])} vs persistence {f(b['B1_naive_persistence']['accuracy'])}; "
      f"Brier {f(b['M4_pcf_D_now']['Brier'])} vs calibrated persistence {f(b['B1p_calibrated_persistence']['Brier'])}. "
      f"Reliable lead (E23 rule): up to {d['backcast_lead_time']['B1_naive_persistence']['furthest_reliable_lead']} "
      f"quarters; stricter rule: up to {d['backcast_lead_time']['B1p_calibrated_persistence']['furthest_reliable_lead']}.")
    P("Prospective sealed forecasts (outcomes protected; scored only after authorization)", "Heading2")
    for sl in d["seals"]:
        P(f"{sl['seal_id']}: SHA-256 {sl['sha256'][:16]}..., origin {sl['origin']}, targets {', '.join(sl['targets'])}; "
          f"{sl['status']}")
    P("Limitations", "Heading2")
    for c in d["caveats"]:
        P("- " + c)
    P(f"Generated from record {r['content_sha256'][:16]}, back-cast {d['generated_from']['bx_run']}, development run "
      f"{d['generated_from']['dev_run']}.", "Italic")
    SimpleDocTemplate(str(path), pagesize=A4, title="aiPHeed forecast report").build(s)


def main():
    bxrun, devrun = EXP / "runs" / sys.argv[1], EXP / "runs" / sys.argv[2]
    BX = j(bxrun / "results_BX.json")
    DEV = j(devrun / "results_dev.json")
    ev = evidence(BX, DEV)
    live, rep = cycles(ev)
    tables(BX, DEV, bxrun, devrun)
    pv = provincial_validity(devrun)
    (EXP / "runs" / "provincial_validity.json").write_text(json.dumps(pv, indent=1), encoding="utf-8")
    d = dashboard(live, rep, ev, BX, DEV, bxrun, devrun, pv)
    pub = EXP / "dashboard_dev" / "public"
    print(json.dumps({"live_status": live["status"], "replay_status": rep["status"],
                      "json_sha256": sha(pub / "e24v2_dashboard.json"), "goal_met": d["goal"]["goal_met"],
                      "T2_evidence": {k: v["status"] for k, v in ev["T2"].items()},
                      "provincial_spearman": pv["spearman_n5_descriptive"]}, indent=1))


if __name__ == "__main__":
    main()
