"""E28 DA brief record (schema 3) and its PDF: ONE record that the API, the dashboard and the PDF read.

    python -B runner/build_record_e28.py

Sources (each verified before use):
  * the E25 seal (SHA-256 of prospective_forecasts.csv equals SEAL.json) -> the sealed PCF21 province estimates;
  * the E27 timeline record (content hash) -> referenced by hash, not changed;
  * the 2027-Q1 pipeline record -> missing dependencies of the operational quarter;
  * runs/e28_eval/E28_DETERMINATION.json + results.json -> horizon determination and baseline comparison;
  * runs/e28_target_audit.json -> what the target can and cannot support;
  * the E28 news store (coverage_audit.json, fssi_manifest.json) -> news coverage and FSSI status;
  * data/inputs/lgu_vulnerability.csv + data/reference/calabarzon_lgus.csv -> the 142-LGU ranking and audit.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard28  # noqa: E402

guard28.install()
import pandas as pd  # noqa: E402

EXP = guard28.EXP
BD = EXP / "backend_dev"
sys.path.insert(0, str(BD))
from app.quarterly.da_brief import SIGNAL_RULE, province_brief  # noqa: E402
from app.quarterly.lgu_audit import build_ranking  # noqa: E402

SEAL = guard28.E25 / "runs" / "SEAL_E25_20261014T002548Z"
NEWS = BD / "data" / "news_e28"
SCHEMA = 3
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def content_hash(rec: dict) -> str:
    return sha(json.dumps({k: v for k, v in rec.items() if k != "content_sha256"}, sort_keys=True,
                          default=str).encode("utf-8"))


def load():
    meta = json.loads((SEAL / "SEAL.json").read_text(encoding="utf-8"))
    sb = (SEAL / "prospective_forecasts.csv").read_bytes()
    assert sha(sb) == meta["sha256_forecasts"], "E25 seal failed its hash check"
    seal = pd.read_csv(SEAL / "prospective_forecasts.csv", dtype={"province_code": str})
    e27 = json.loads((EXP / "runs" / "e27_timeline_record.json").read_text(encoding="utf-8"))
    assert content_hash(e27) == e27["content_sha256"], "E27 record failed its integrity check"
    pipe = json.loads((BD / "data" / "quarterly_runs" / "2027-Q1" / "forecast_record.json").read_text(encoding="utf-8"))
    det = json.loads((EXP / "runs" / "e28_eval" / "E28_DETERMINATION.json").read_text(encoding="utf-8"))
    res = json.loads((EXP / "runs" / "e28_eval" / "results.json").read_text(encoding="utf-8"))
    aud = json.loads((EXP / "runs" / "e28_target_audit.json").read_text(encoding="utf-8"))
    cov = json.loads((NEWS / "coverage_audit.json").read_text(encoding="utf-8"))
    fman = json.loads((NEWS / "fssi_manifest.json").read_text(encoding="utf-8"))
    assert sha((NEWS / "fssi_panel.csv").read_bytes()) == fman["panel_sha256"], "FSSI panel does not match its manifest"
    rounds = pd.read_csv(BD / "data" / "inputs" / "sws_rounds.csv")
    D = pd.read_csv(BD / "data" / "inputs" / "d_quarterly_panel.csv", dtype={"province_code": str})
    vul = pd.read_csv(BD / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    ros = pd.read_csv(BD / "data" / "reference" / "calabarzon_lgus.csv", dtype={"lgu_psgc": str})
    return meta, seal, e27, pipe, det, res, aud, cov, fman, rounds, D, vul, ros


def eval_table(res: dict, det: dict) -> dict:
    keep = ["PROPOSED", "PROPOSED_NESTED", "PROPOSED_PERSIST", "LR_STRUCT", "B1", "PSA_LR", "PSA_LGBM", "NLP_LR",
            "NLP_LGBM", "LR_COMB", "ALWAYS_HIGH", "CLIM", "PCF21_E25", "PROPOSED_E25"]
    out = {}
    for tg in ("T1_A", "T2"):
        S = res["summary"][tg]
        rows = []
        for a in keep:
            if a not in S:
                continue
            l1 = S[a]["by_lead"].get("1") or S[a]["by_lead"].get(1)
            po = S[a]["pooled"]
            rows.append({"arm": a, "lead1_accuracy": l1["accuracy"], "lead1_brier": l1["brier"],
                         "lead1_auc": l1["roc_auc"], "lead1_auc_flag": l1["flags"]["roc_auc"],
                         "pooled_accuracy": po["accuracy"], "pooled_brier": po["brier"],
                         "furthest_reliable_horizon": det[tg]["furthest_reliable_horizon"].get(a),
                         "qualifies": det[tg]["qualifies_E27_rule_pooled"].get(a)})
        out[tg] = {"rows": rows, "reachability_by_lead": det[tg]["reachability_by_lead"]}
    return out


def build() -> dict:
    meta, seal, e27, pipe, det, res, aud, cov, fman, rounds, D, vul, ros = load()
    t1 = seal[(seal["target"] == "T1_A") & (seal["arm"] == "PCF21")]
    hz = det["T1_A"]["furthest_reliable_horizon"].get("PCF21_E25", "not determinable on the available outcomes")
    hz_text = (f"furthest reliable lead: {hz}" if isinstance(hz, int) else
               "furthest reliable lead: not determinable (no lead has >= 5 LOW outcomes and >= 8 dates)")
    lastD = D.sort_values("quarter").groupby("province_code").tail(1).set_index("province_code")
    prod = rounds[rounds["source"].str.startswith("production") & rounds["definition_A"].astype(str).str.lower().eq("true")]
    last_round = prod.sort_values("published_eff").iloc[-1]
    cov_df = pd.DataFrame([r for r in cov if r["province"] != "REGION"])
    latest_news_q = cov_df["quarter"].max()
    briefs = {}
    for lead, q in ((1, "2026-Q4"),):
        for r in t1[t1["lead"] == lead].sort_values("province_code").itertuples():
            nrow = cov_df[(cov_df["province_code"] == r.province_code) & (cov_df["quarter"] == latest_news_q)].iloc[0]
            briefs[r.province_code] = province_brief({
                "province": r.province, "target_quarter": r.target_quarter, "lead": int(r.lead),
                "origin": str(r.origin)[:10], "info_cutoff": r.info_cutoff, "p": float(r.p), "tau": float(r.tau),
                "mu_H": float(r.mu_H), "mu_D": float(r.mu_D), "sd_S1": float(r.sd_S1), "lo80_S1": float(r.lo80_S1),
                "hi80_S1": float(r.hi80_S1), "evidence_status": "EXPERIMENTAL",
                "previous_D": float(lastD.loc[r.province_code, "D"]),
                "last_round": last_round["round"], "last_round_published": str(last_round["published_eff"])[:10],
                "last_cpi_month": "2026-06", "news_quarter": latest_news_q, "news_status": nrow["coverage_status"],
                "news_articles_in_fssi": int(nrow.get("included_in_fssi") or 0), "gov_missing": [],
                "horizon_determination": hz_text})
            briefs[r.province_code]["sealed"] = {"seal": meta.get("seal_id", "SEAL_E25_20261014T002548Z"),
                                                 "arm": "PCF21", "sha256_forecasts": meta["sha256_forecasts"]}
    op = {}
    for c, n in NAMES.items():
        op[c] = province_brief({"province": n, "target_quarter": "2027-Q1", "lead": 1, "origin": "2027-01-01",
                                "info_cutoff": "2026-12-31T23:59:59+08:00", "p": None, "evidence_status": "EXPERIMENTAL",
                                "last_round": last_round["round"],
                                "last_round_published": str(last_round["published_eff"])[:10],
                                "last_cpi_month": "2026-06", "news_quarter": "2026-Q4", "news_status": "NOT_AUTHORIZED",
                                "gov_missing": list(pipe["missing"]), "horizon_determination": hz_text})
    prob = {r.province_code: float(r.p) for r in t1[t1["lead"] == 1].itertuples()}
    ranking = build_ranking(vul, ros, prob, {"source": "E25 seal SEAL_E25_20261014T002548Z, PCF21, lead 1, 2026-Q4",
                                             "sha256_forecasts": meta["sha256_forecasts"],
                                             "evidence_status": "EXPERIMENTAL"})
    # representative scenarios from real data
    # change in relative food inflation: expected D for 2026-Q4 minus the last measured D (2026-Q2)
    dch = {r.province_code: float(r.mu_D) - float(lastD.loc[r.province_code, "D"]) for r in t1[t1["lead"] == 1].itertuples()}
    rising = briefs[max(dch, key=dch.get)]
    flat = briefs[min(dch, key=lambda c: abs(dch[c]))]
    thin = cov_df[cov_df["coverage_status"].isin(["COMPLETE_NO_USABLE_EVIDENCE", "COMPLETE_LIMITED_EVIDENCE"])]
    thin_case = None
    if len(thin):
        x = thin.sort_values(["quarter", "province"]).iloc[-1]
        thin_case = {"province": x["province"], "quarter": x["quarter"], "coverage_status": x["coverage_status"],
                     "included_in_fssi": int(x.get("included_in_fssi") or 0),
                     "brief_news_line": province_brief({"province": x["province"], "p": None,
                                                        "news_quarter": x["quarter"],
                                                        "news_status": x["coverage_status"]})["data_coverage"]["news"],
                     "fssi": "null (no usable evidence)" if x["coverage_status"] == "COMPLETE_NO_USABLE_EVIDENCE" else "limited signal"}
    scenarios = {
        "increasing_pressure": {"province": rising["province"], "headline": rising["headline"],
                                "attention": rising["attention"], "price_trend": rising.get("price_trend"),
                                "price_trend_detail": rising.get("price_trend_detail"),
                                "reading": ("Relative food inflation is expected to rise, but the province is still "
                                            "below the regional average, so the price term lowers the estimate; the "
                                            "result stays uncertain.") if 2 * float(t1[(t1["lead"] == 1)].set_index(
                                                "province_code").loc[max(dch, key=dch.get), "mu_D"]) < 0 else None,
                                "suggested_use": rising["suggested_use"]},
        "little_change": {"province": flat["province"], "headline": flat["headline"], "attention": flat["attention"],
                          "price_trend": flat.get("price_trend"), "suggested_use": flat["suggested_use"]},
        "insufficient_news": thin_case,
        "missing_government_indicators": {"quarter": "2027-Q1", "headline": op["PH040500000"]["headline"],
                                          "missing_inputs": op["PH040500000"]["missing_inputs"],
                                          "suggested_use": op["PH040500000"]["suggested_use"]},
    }
    cov_summary = (cov_df.groupby("coverage_status").size().to_dict())
    rec = {
        "schema": SCHEMA, "title": "aiPHeed E28 DA brief - CALABARZON (experimental)",
        "status_banner": ("EXPERIMENTAL. No forecast lead time is validated: the approved label has fewer than 5 LOW "
                          "outcomes at every lead, so the furthest reliable horizon cannot be determined, and no sealed "
                          "forecast has an authorized outcome yet. Figures are indicators for planning attention, "
                          "not official assessments."),
        "sources": {"e25_seal": {"id": "SEAL_E25_20261014T002548Z", "sha256_forecasts": meta["sha256_forecasts"]},
                    "e27_timeline_record_sha256": e27["content_sha256"],
                    "e28_protocol_sha256": det.get("protocol_sha256") or res["inputs"]["protocol"],
                    "fssi_manifest": fman, "lgu_rows_sha256": ranking["rows_sha256"]},
        "signal_rule": SIGNAL_RULE,
        "forecast_quarter": {"quarter": "2026-Q4", "kind": "sealed experimental estimate (lead 1, origin 2026-10-01)",
                             "provinces": briefs},
        "operational_quarter": {"quarter": "2027-Q1", "status": pipe["status"], "missing": pipe["missing"],
                                "provinces": op},
        "target_validity": {k: aud[k] for k in ("what_the_target_can_support", "what_it_cannot_support",
                                                "what_would_be_needed")} | {
            "share_of_label_variance_regional": aud["components"]["share_of_S1_variance_from_regional_H"],
            "LOW_test_labels_within_sampling_error": aud["survey_uncertainty"]["share_of_LOW_test_labels_within_1.96_SE_of_tau"]},
        "evaluation": eval_table(res, det),
        "news_coverage": {"quarters": [cov_df["quarter"].min(), cov_df["quarter"].max()],
                          "province_quarters": int(len(cov_df)), "coverage_status_counts": cov_summary,
                          "latest_quarter": latest_news_q, "note": "zero retrieved articles is never zero food insecurity",
                          "rows": cov_df[["province", "quarter", "coverage_status", "collection_status",
                                          "evidence_status", "included_in_fssi", "retained_title_geocoded",
                                          "requests", "failed_requests"]].to_dict("records")},
        "lgu_ranking": ranking,
        "scenarios": scenarios,
        "disclaimer": ("aiPHeed provides food-insecurity risk indicators only and does not replace official government "
                       "assessments, classifications or DA decisions."),
    }
    rec["content_sha256"] = content_hash(rec)
    return rec


def write_pdf(rec: dict, path: Path):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table
    st = getSampleStyleSheet()
    P = lambda t, s="Normal": Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), st[s])  # noqa: E731
    pc = lambda x: "-" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    els = [P(rec["title"], "Title"), P(f"Record SHA-256: {rec['content_sha256']}"), P(rec["status_banner"]), Spacer(1, 6)]
    fq = rec["forecast_quarter"]
    els.append(P(f"{fq['quarter']}: {fq['kind']}", "Heading2"))
    rows = [["Province", "P(above threshold)", "80% S1 interval", "Signal", "Category", "Largest driver", "Attention"]]
    for b in fq["provinces"].values():
        d = b["drivers"][0]
        rows.append([b["province"], pc(b["estimate"]["p_above_threshold"]), str(b["estimate"]["S1_80pct_interval"]),
                     b["signal"], b["category"] or "withheld", f"{d['factor'][:40]} ({d['contribution']:+.2f})",
                     b["attention"]])
    els.append(Table(rows, repeatRows=1))
    for b in fq["provinces"].values():
        els.append(P(f"{b['province']}: {b['headline']} {b['suggested_use']}"))
        els.append(P("Data: " + "; ".join(f"{k}: {v}" for k, v in b["data_coverage"].items()
                                          if k in ("hunger", "prices", "news"))))
    els.append(P(f"{rec['operational_quarter']['quarter']}: {rec['operational_quarter']['status']}", "Heading2"))
    for m in rec["operational_quarter"]["missing"]:
        els.append(P("- " + m))
    els.append(P("Forecast reliability and baselines (development evidence)", "Heading2"))
    rows = [["Arm", "Lead-1 acc", "Lead-1 Brier", "Lead-1 AUC", "Pooled acc", "Pooled Brier", "Reliable horizon"]]
    for r in rec["evaluation"]["T1_A"]["rows"]:
        f = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
        rows.append([r["arm"], f(r["lead1_accuracy"]), f(r["lead1_brier"]),
                     f(r["lead1_auc"]) + ("" if r["lead1_auc_flag"] == "OK" else f" ({r['lead1_auc_flag']})"),
                     f(r["pooled_accuracy"]), f(r["pooled_brier"]), str(r["furthest_reliable_horizon"])[:30]])
    els.append(Table(rows, repeatRows=1))
    for x in rec["target_validity"]["what_it_cannot_support"]:
        els.append(P("Cannot support: " + x))
    els.append(P("News coverage 2021-Q1..2026-Q2: " + json.dumps(rec["news_coverage"]["coverage_status_counts"])))
    els.append(PageBreak())
    lr = rec["lgu_ranking"]
    els.append(P("City and municipal ranking (142 LGUs, EXPERIMENTAL)", "Heading2"))
    els.append(P(lr["meaning"]))
    for x in lr["does_not_mean"]:
        els.append(P("- " + x))
    rows = [["Rank", "LGU", "Province", "Risk index", "Rank in prov.", "Poverty used (kind)", "Density/km2", "Tied"]]
    for r in lr["rows"]:
        rows.append([r["rank_region"] if r["rank_region"] is not None else "-", r["lgu_name"], r["province"],
                     "-" if r["risk_index"] is None else f"{r['risk_index']:.4f}", r["rank_in_province"] or "-",
                     f"{r['poverty_value_used']} ({'SAE' if r['poverty_lgu_estimate'] is not None else 'substitute'})",
                     f"{r['density_per_km2']:.0f}", "yes" if r["tied"] else ""])
    els.append(Table(rows, repeatRows=1))
    els.append(P(rec["disclaimer"]))
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), title=rec["title"], subject=rec["content_sha256"],
                            invariant=1, pageCompression=0)
    doc.build(els)


def main():
    rec = build()
    blob = json.dumps(rec, indent=1, sort_keys=True, default=str).encode("utf-8")
    for t in (BD / "data" / "e28" / "da_brief_record.json", EXP / "dashboard_dev" / "public" / "e28_da_brief_record.json",
              EXP / "runs" / "e28_da_brief_record.json"):
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(blob)
    for pdf in (BD / "data" / "e28" / "aiPHeed_E28_DA_brief.pdf", EXP / "dashboard_dev" / "public" / "aiPHeed_E28_DA_brief.pdf"):
        write_pdf(rec, pdf)
    print("record", rec["content_sha256"], "bytes", sha(blob))


if __name__ == "__main__":
    main()
