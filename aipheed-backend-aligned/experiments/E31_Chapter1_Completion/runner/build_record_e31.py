"""E31 record: ONE JSON for the API (/api/v1/quarterly/e31/*), the main dashboard (E31 engine), the /da-brief and
/news pages and the PDF. Information cutoff 2026-10-14 23:59:59 PHT (data authorized by the researcher on 2026-10-14).

    python -B runner/build_record_e31.py

Sections
  meta / served_engine / target_definition    what is predicted, how, and what it is not
  regional_hunger                             SWS Balance Luzon rounds (one regional value, verified dates)
  quarters                                    one row per quarter: mode (BACKTEST / RETROSPECTIVE_BLIND / NOWCAST /
                                              FORECAST), origin, cutoff, lead, provenance, per-province estimate,
                                              exact drivers and, where released, the measured outcome
  provinces_now                               the DA-facing summary for the 2026-Q4 nowcast and 2027-Q1 forecast
  lgu_ranking                                 142 LGUs from the 2026-Q4 nowcast (Objective 3 method, unchanged)
  news                                        funnel per province-quarter and the admitted (validated) articles
  validation                                  relevance validation, development metrics, the unseen 2026-Q3 score,
                                              the 75% assessment
  limitations
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EXP = HERE.parent
BD = EXP / "backend_dev"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BD))
import guard31  # noqa: E402

guard31.install()
import pandas as pd  # noqa: E402

from app.news.alignment import evidence_window, select  # noqa: E402
from app.news.fssi_v2 import admitted_articles  # noqa: E402
from app.news.relevance import VERSION_DEPLOYED as RULE, classify_deployed as classify  # noqa: E402
from app.news.store import NewsStore  # noqa: E402
from app.quarterly.lgu_audit import build_ranking  # noqa: E402

CUTOFF = "2026-10-14T23:59:59+08:00"
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
ORDER = ["PH040100000", "PH040200000", "PH040500000", "PH040400000", "PH040300000"]
E25RUN = EXP.parent / "E25_Reliable_Forecasts_2021_2026" / "runs" / "20261014T002026Z"
DISCLAIMER = ("aiPHeed produces potential food-insecurity risk indicators for review. They are not official "
              "food-insecurity classifications and do not replace assessments by authorized government agencies.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def r4(x):
    return None if x is None or x != x else round(float(x), 4)


def signal(p: float) -> str:
    return "STRONG" if p >= .8 or p <= .2 else "MODERATE" if p >= .65 or p <= .35 else "UNCERTAIN"


def drivers_of(risk: dict, tau: float) -> dict:
    """Exact attribution of the estimate's margin over the threshold: (S1 - tau) = (H - tau) + 2D. These are the
    served engine's own inputs (no approximation), associations rather than causes."""
    comp = risk["components"]
    h, d2 = comp["regional_hunger_H"]["value"], comp["provincial_price_pressure_2D"]["contribution"]
    return {"S1_forecast": r4(risk["S1_forecast"]), "S1_80pct_interval": [r4(x) for x in risk["S1_80pct_interval"]],
            "drivers": [
                {"key": "regional_hunger", "factor": "Regional hunger (SWS Balance Luzon) relative to the threshold",
                 "value": r4(h), "contribution": r4(h - tau), "kind": "shared by all five provinces"},
                {"key": "price_pressure", "factor": "Provincial relative food-price pressure (2 x D)",
                 "value": r4(comp["provincial_price_pressure_2D"]["value"]), "contribution": r4(d2),
                 "kind": "province-specific"}],
            "driver_method": "exact additive decomposition of the estimate's margin over the threshold, "
                             "S1 - tau = (H - tau) + 2D; the model's inputs, not causes"}


# ------------------------------------------------------------------------------------------------ pieces
def regional_hunger() -> dict:
    r = pd.read_csv(BD / "data" / "inputs" / "sws_rounds.csv")
    r = r[r["definition_A"].astype(str).str.lower() == "true"].copy()
    rows = [{"quarter": x.quarter, "round": x.round, "hunger_pct": float(x.H), "published": str(x.published_eff)[:10],
             "date_type": x.date_type} for x in r.itertuples()]
    return {"what": "SWS self-rated involuntary hunger, Balance Luzon (Luzon outside Metro Manila)", "kind": "MEASURED",
            "geographic_level": "regional: ONE value shared by all five provinces; not a provincial or municipal "
                                "measurement",
            "rounds": rows[-8:], "latest": rows[-1], "change_last_two_pp": round(rows[-1]["hunger_pct"] - rows[-2]["hunger_pct"], 1)}


def measured_outcomes() -> dict:
    s1 = pd.read_csv(BD / "data" / "inputs" / "s1_labels.csv", dtype={"province_code": str})
    d = pd.read_csv(BD / "data" / "inputs" / "d_quarterly_panel.csv", dtype={"province_code": str})
    out = {}
    for x in s1.itertuples():
        out.setdefault(x.quarter, {})[x.province_code] = {"S1": float(x.S1)}
    for x in d.itertuples():
        if x.quarter in out and x.province_code in out[x.quarter]:
            out[x.quarter][x.province_code]["D"] = float(x.D)
    return out


def backtests(outcomes: dict) -> list[dict]:
    """PCF21 lead-1 walk-forward forecasts of the frozen E25 run (development evidence: outcomes examined before)."""
    rows = list(csv.DictReader(open(E25RUN / "predictions_T1_A.csv", encoding="utf-8")))
    by = {}
    for r in rows:
        if r["lead"] == "1" and r["model"] in ("PCF21", "B1_naive_persistence"):
            by.setdefault(r["target_quarter"], {}).setdefault(r["model"], {})[r["province_code"]] = r
    from app.quarterly import pcf_engine as PE
    v1 = BD / "data" / "inputs_vintage1_e29"
    rr = pd.read_csv(v1 / "sws_rounds.csv")
    s1 = pd.read_csv(v1 / "s1_labels.csv", dtype={"province_code": str})
    Dm, Nm = PE.panels_from_tables(pd.read_csv(v1 / "d_quarterly_panel.csv", dtype={"province_code": str}),
                                   pd.read_csv(v1 / "dnow_panel.csv", dtype={"province_code": str}))
    out = []
    for q in sorted(by):
        pc = by[q]["PCF21"]
        o = next(iter(pc.values()))["origin"]
        fc = PE.forecast(pd.Timestamp(o), PE.qk(q) - 1, [1], rr, s1, Dm, Nm, {})["leads"]["1"]
        for c in ORDER:     # the served engine reproduces the frozen E25 backtest exactly
            assert abs(fc["provinces"][c]["risk"]["p_high"] - float(pc[c]["score"])) < 1e-6, (q, c)
        any_r = next(iter(pc.values()))
        tau = float(any_r["threshold"])
        prov = {}
        for c in ORDER:
            r = pc[c]
            prov[c] = {"province": NAMES[c], "p_high": r4(float(r["score"])), "signal": signal(float(r["score"])),
                       "observed_S1": r4(float(r["value"])), "observed_label": "HIGH" if int(r["y"]) else "LOW",
                       "persistence_p": float(by[q]["B1_naive_persistence"][c]["score"]),
                       **drivers_of(fc["provinces"][c]["risk"], tau)}
        out.append({"quarter": q, "mode": "BACKTEST", "lead": 1, "origin": any_r["origin"],
                    "information_cutoff": f"{any_r['origin']} 00:00 PHT (inputs published before the origin)",
                    "status": "development evidence: the outcome had been examined before the E25 protocol froze",
                    "threshold": r4(tau), "provinces": prov})
    return out


def q3_unseen(outcomes: dict) -> dict:
    fr = jload(EXP / "frozen" / "E31_FROZEN_Q3.json")
    sc = jload(EXP / "runs" / "e31_q3_scores.json")
    blk = fr["leads"]["1"]
    prov = {}
    for c in ORDER:
        p = blk["arms_p_high"]["PCF21"][c]
        S1 = outcomes["2026-Q3"][c]["S1"]
        tau = blk["threshold_tau"]
        h = blk["H_forecast"]["mu_H"]
        d2 = blk["S1_forecast"][c] - h
        prov[c] = {"province": NAMES[c], "p_high": r4(p), "signal": signal(p), "S1_forecast": r4(blk["S1_forecast"][c]),
                   "S1_80pct_interval": [r4(v) for v in blk["S1_80pct_interval"][c]], "observed_S1": r4(S1),
                   "drivers": [{"key": "regional_hunger", "factor": "Regional hunger (SWS Balance Luzon) relative to the threshold",
                                "value": r4(h), "contribution": r4(h - tau), "kind": "shared by all five provinces"},
                               {"key": "price_pressure", "factor": "Provincial relative food-price pressure (2 x D)",
                                "value": r4(d2 / 2), "contribution": r4(d2), "kind": "province-specific"}],
                   "driver_method": "exact additive decomposition, S1 - tau = (H - tau) + 2D",
                   "observed_D": r4(outcomes["2026-Q3"][c]["D"]),
                   "observed_label": "HIGH" if S1 > blk["threshold_tau"] else "LOW",
                   "persistence_p": blk["arms_p_high"]["B1_persistence"][c]}
    return {"quarter": "2026-Q3", "mode": "RETROSPECTIVE_BLIND", "lead": 1, "origin": blk["origin"],
            "information_cutoff": blk["information_cutoff"], "frozen_record_sha256": sha(EXP / "frozen" / "E31_FROZEN_Q3.json"),
            "frozen_git_commit": "70d8770 (2026-10-14T23:31:58+08:00), before the outcome was retrieved",
            "status": "first quarter scored on an outcome the project had not seen when the forecast was frozen",
            "threshold": r4(blk["threshold_tau"]), "provinces": prov,
            "scores": [s for s in sc["scores"] if s["lead"] in (1, 2)],
            "outcome_sources": {"H": "SWS September 21-27, 2026 round, Balance Luzon 23.6% (posted 2026-10-14)",
                                "D": "PSA OpenStat 0012M4ACP23, 01.1 Food YoY, July-September 2026"}}


def operational() -> list[dict]:
    op = jload(BD / "data" / "e31" / "operational_outputs.json")
    out = []
    for o in op["outputs"]:
        prov = {}
        for c in ORDER:
            v = o["provinces"][c]["risk"]
            prov[c] = {"province": NAMES[c], "p_high": r4(v["p_high"]), "signal": v["signal"],
                       **drivers_of(v, op["threshold"]),
                       "persistence_p": o["references"]["persistence"][c]}
        out.append({"quarter": o["target_quarter"], "mode": o["mode"], "lead": o["lead"], "origin": op["origin"],
                    "information_cutoff": op["information_cutoff"], "provenance": o["provenance"],
                    "status": ("same-quarter estimate; lead 0 was never evaluated" if o["mode"] == "NOWCAST" else
                               "forecast; lead 1 has no established reliability (development evidence only)"),
                    "threshold": r4(op["threshold"]), "H_forecast": r4(o["H"]["mu_H"]),
                    "H_80pct_interval": [r4(x) for x in o["layers"]["regional_risk"]["H_80pct_interval"]],
                    "p_regional_H_above_threshold": r4(o["layers"]["regional_risk"]["p_H_above_threshold"]),
                    "provinces": prov})
    return out


def news(store: NewsStore) -> dict:
    v2 = pd.read_csv(store.root / "fssi_v2_panel.csv")
    v2m = jload(store.root / "fssi_v2_panel_manifest.json")
    v1 = pd.read_csv(store.root / "fssi_panel.csv")
    arts = list(store.articles.values())
    kept, funnel_all = admitted_articles(store)
    kept_keys = {a["article_key"] for a in kept}
    # collected per province-quarter = articles first retrieved by that province's queries
    rows = []
    v1i = {(r.province_code, r.quarter): r for r in v1.itertuples()}
    for r in v2.itertuples():
        col = sum(1 for a in arts if a["quarter"] == r.quarter and a.get("first_query_province") == r.province)
        rel = [a for a in arts if a["quarter"] == r.quarter and a.get("geo_province_code") == r.province_code
               and classify(a["title"]) != "NONE"]
        o = v1i.get((r.province_code, r.quarter))
        rows.append({"province": r.province, "province_code": r.province_code, "quarter": r.quarter,
                     "collected_by_province_queries": col, "province_attributed": int(r.n_province_attributed),
                     "relevant_R1": len(rel), "admitted_after_dedup": int(r.n_admitted),
                     "direct": int(r.n_direct), "indirect": int(r.n_indirect),
                     "FSSI_v2": None if pd.isna(r.FSSI_v2) else r4(r.FSSI_v2), "evidence_status_v2": r.evidence_status,
                     "in_FSSI_v1": int(o.n_in_fssi) if o is not None else 0,
                     "evidence_status_v1": o.evidence_status if o is not None else None})
    alist = []
    for a in sorted(kept, key=lambda a: a["published_ph"], reverse=True):
        alist.append({"article_key": a["article_key"], "title": a["title"], "outlet": a["source_domain"],
                      "published_ph": a["published_ph"], "quarter": a["quarter"], "province_code": a["geo_province_code"],
                      "province": NAMES[a["geo_province_code"]], "relevance": classify(a["title"]), "link": a["link"],
                      "description": None, "description_note": "title only (Google News RSS supplies no lead text)"})
    tot = {"collected": len(arts), "province_attributed": funnel_all["province_attributed"],
           "relevant_R1": funnel_all["relevant_R1"], "syndicated_copies_removed": funnel_all["syndicated_copies_removed"],
           "admitted_to_FSSI_v2": len(kept),
           "province_quarters_sufficient_v2": int((v2.evidence_status == "SUFFICIENT").sum()),
           "province_quarters_limited_v2": int((v2.evidence_status == "LIMITED_SIGNAL").sum()),
           "province_quarters_none_v2": int((v2.evidence_status == "NO_USABLE_EVIDENCE").sum()),
           "in_FSSI_v1": int(v1.n_in_fssi.sum()),
           "province_quarters_sufficient_v1": int((v1.evidence_status == "SUFFICIENT").sum())}
    return {"source": "Google News RSS (titles; publisher pubDate), credible-domain policy v1, 2021-01-01..2026-10-14",
            "relevance_rule": RULE, "fssi_v2_manifest": v2m, "totals": tot, "by_province_quarter": rows,
            "articles": alist, "articles_jsonl_sha256": sha(store.path("articles")),
            "windows": {"nowcast_2026Q4": evidence_window("2026-Q4", "nowcast", CUTOFF).to_dict(),
                        "forecast_2027Q1": evidence_window("2027-Q1", "forecast", CUTOFF).to_dict()},
            "admitted_keys_sha256": hashlib.sha256(json.dumps(sorted(kept_keys)).encode()).hexdigest()}


EVAL_ARMS = {"B1": "Naive persistence (Objective 4-I)", "ALWAYS_HIGH": "Always HIGH (majority class)",
             "PSA_LR": "PSA-only indicator baseline (Objective 4-II)", "NLP_LR": "NLP-only sentiment baseline (4-III)",
             "LR_COMB": "Logistic regression baseline (4-IV)", "PROPOSED": "Proposed LightGBM, E28 inputs",
             "PROPOSED_E25": "P45: proposed LightGBM, 45 candidates (researcher's primary model)",
             "PCF21_E25": "PCF21 (served engine)"}
KEYS = ("n", "n_dates", "HIGH", "LOW", "accuracy", "accuracy_ci95", "balanced_accuracy", "precision", "recall", "f1",
        "roc_auc", "pr_auc", "brier", "brier_ci95", "ece_3bin", "TP", "FP", "TN", "FN", "flags")


def validation() -> dict:
    res = jload(EXP / "runs" / "e28_eval" / "results.json")["summary"]["T1_A"]
    dev = {}
    for arm, label in EVAL_ARMS.items():
        if arm not in res:
            continue
        dev[arm] = {"label": label, "by_lead": {L: {k: res[arm]["by_lead"][L].get(k) for k in KEYS}
                                                for L in ("1", "2", "3") if L in res[arm]["by_lead"]}}
    rel_dev = jload(EXP / "validation" / "relevance_metrics_dev.json")
    rel_ho = jload(EXP / "validation" / "holdout" / "relevance_metrics_holdout.json")
    q3 = jload(EXP / "runs" / "e31_q3_scores.json")
    ev = {}
    for w in ("v1", "v2"):
        p = EXP / "runs" / f"e31_eval_{w}" / "results.json"
        if p.exists():
            s = jload(p)["summary"]["T1_A"]
            ev[w] = {a: {k: s[a]["by_lead"]["1"].get(k) for k in ("accuracy", "brier", "roc_auc", "n")}
                     for a in ("NLP_LR", "NLP_LGBM", "PROPOSED", "LR_COMB") if a in s and "1" in s[a]["by_lead"]}
    thr = []
    for arm, v in dev.items():
        m = v["by_lead"].get("1")
        if m:
            thr.append({"arm": v["label"], "accuracy_lead1": r4(m["accuracy"]), "above_75pct": bool(m["accuracy"] > .75),
                        "beats_persistence_accuracy": bool(m["accuracy"] > dev["B1"]["by_lead"]["1"]["accuracy"]),
                        "beats_always_high_accuracy": bool(m["accuracy"] > dev["ALWAYS_HIGH"]["by_lead"]["1"]["accuracy"])})
    return {
        "news_relevance": {
            "rule": RULE, "annotator": "AI assistant (Claude), blind to classifier scores; researcher re-review recommended",
            "development_sample": {"n": 355, "e28_gate": rel_dev["gates"][next(k for k in rel_dev["gates"] if k.startswith("E28 gate"))]["relevant"]},
            "holdout": {k: rel_ho[k] for k in ("sample", "n", "n_relevant", "n_direct", "gates", "geography")},
            "deployed_rule": "R1.1 = R1 + corrections of the holdout's false-positive patterns (fuel/fare prices, "
                             "non-food 'relief', end-of-outbreak); R1.1 holdout figures are optimistic",
            "r11_vs_r1": jload(EXP / "validation" / "r11_metrics.json"),
        },
        "development_metrics_T1": {"basis": "E28 frozen protocol d897f56d; walk-forward expanding window; every quarter "
                                            "had been examined before (development evidence)", "arms": dev},
        "fssi_v2_effect_development": ev or "pending",
        "unseen_quarter_2026Q3": {"rows": 5, "dates": 1, "outcome": q3["outcome_2026Q3"], "scores": q3["scores"],
                                  "caveat": q3["caveat"]},
        "threshold_75pct": {
            "source": "the researcher's brief (E31); Chapter I itself states no numeric threshold",
            "rows": thr,
            "verdict": ("Several arms exceed 75% accuracy at lead 1, but so does always-HIGH (0.911) because 91% of "
                        "test labels are HIGH. No arm beats persistence AND always-HIGH on accuracy or Brier, so "
                        "accuracy above 75% does not show forecasting skill here; the requirement is met only in a "
                        "form that a constant forecast also meets.")},
    }


def provinces_now(quarters: list[dict], news_rows: list[dict]) -> dict:
    now = next(q for q in quarters if q["mode"] == "NOWCAST")
    fc = next(q for q in quarters if q["mode"] == "FORECAST")
    D = pd.read_csv(BD / "data" / "inputs" / "d_quarterly_panel.csv", dtype={"province_code": str})
    out = {}
    for c in ORDER:
        dd = D[D.province_code == c].sort_values("quarter").tail(3)
        nq = next((r for r in news_rows if r["province_code"] == c and r["quarter"] == "2026-Q4"), None)
        pn, pf = now["provinces"][c], fc["provinces"][c]
        d_last = float(dd.D.iloc[-1])
        ppress = ("above" if d_last > 0.25 else "below" if d_last < -0.25 else "close to")
        out[c] = {
            "province": NAMES[c],
            "nowcast_2026Q4": pn, "forecast_2027Q1": pf,
            "measured_relative_food_inflation_pp": {r.quarter: r4(r.D) for r in dd.itertuples()},
            "price_pressure_text": f"Food inflation in {NAMES[c]} was {abs(d_last):.2f} pp {ppress} the five-province "
                                   f"average in 2026-Q3 (PSA, measured).",
            "news_2026Q4_to_cutoff": nq,
            "attention": ("Review: the estimate is high mainly because regional hunger is high; check provincial "
                          "market prices and field reports" if pn["p_high"] >= .8 else
                          "Monitor: the estimate is above the threshold with less certainty"),
            "suggested_use": "Prioritise for review by DA Region IV-A; do not allocate resources on this estimate alone.",
            "evidence_status": "EXPERIMENTAL",
            "disclaimer": DISCLAIMER}
    return out


def _clean(o):
    import math

    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):      # numpy scalars
        return _clean(o.item())
    return o


def build() -> dict:
    store = NewsStore(BD / "data" / "news_e31")
    outc = measured_outcomes()
    quarters = backtests(outc) + [q3_unseen(outc)] + operational()
    nw = news(store)
    now = next(q for q in quarters if q["mode"] == "NOWCAST")
    vul = pd.read_csv(BD / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    ros = pd.read_csv(BD / "data" / "reference" / "calabarzon_lgus.csv", dtype={"lgu_psgc": str})
    rk = build_ranking(vul, ros, {c: now["provinces"][c]["p_high"] for c in ORDER},
                       {"source": "E31 NOWCAST 2026-Q4 (PCF21, cutoff 2026-10-14)", "evidence_status": "EXPERIMENTAL"})
    rec = {
        "schema": "e31/1",
        "title": "aiPHeed: food-insecurity risk indicators for CALABARZON (DA Region IV-A)",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "information_cutoff": CUTOFF,
        "data_authorization": "2021-01-01..2026-10-14 (researcher, 2026-10-14); nothing before 2021 is used",
        "served_engine": {"name": "PCF21", "file": "app/quarterly/pcf_engine.py",
                          "sha256": sha(BD / "app" / "quarterly" / "pcf_engine.py"),
                          "why_served": "the only candidate that can issue 2026-Q4/2027-Q1 estimates from released data "
                                        "and the best model-based Brier score on development quarters; P45 (the "
                                        "researcher's primary candidate) needs 2026 government features that do not "
                                        "exist and did not do better on the unseen quarter",
                          "evidence_status": "EXPERIMENTAL (no lead validated against persistence and always-HIGH)"},
        "target_definition": {
            "label": "T1: S1 = H + 2D > tau, HIGH or LOW (the approved Chapter I composite food-stress label)",
            "H": "SWS Balance Luzon self-rated hunger (%), one regional value for all five provinces (measured)",
            "D": "province food inflation minus the five-province mean (pp), PSA provincial CPI (measured)",
            "tau": "median S1 of the published labelled quarters before the origin (trailing median)",
            "observable": "after the quarter's SWS round is posted and its last CPI month is released (2026-Q3: 14 Oct 2026)",
            "is_not": "an official or measured food-insecurity prevalence; provincial differences come only from prices",
        },
        "regional_hunger": regional_hunger(),
        "quarters": quarters,
        "provinces_now": provinces_now(quarters, nw["by_province_quarter"]),
        "lgu_ranking": rk,
        "news": nw,
        "validation": validation(),
        "limitations": [
            "The label is 68% regional SWS hunger: one survey value drives all five provinces, so most quarters "
            "(and 2026-Q3) are HIGH everywhere. Provincial differences come only from relative food prices.",
            "No lead time is validated: on development quarters no model beats persistence and always-HIGH; the "
            "unseen 2026-Q3 is one regional observation (five rows that share one H).",
            "News evidence is title-only. The relevance rule R1 has precision 0.85 and estimated recall 0.40 on a blind "
            "holdout (deployed R1.1 fixes its false-positive patterns; not yet re-validated on fresh data), so most "
            "province-quarters still have limited or no news evidence.",
            "126 of 142 LGUs use a province-mean poverty substitute (2021 municipal SAE extract not available "
            "without loading pre-2021 values); their order inside a province comes from population density.",
            "Annotation of the relevance samples was done by the AI assistant, not by the researchers; a researcher "
            "re-review of validation/*/annotation_sheet_blind.json is recommended before thesis use.",
            "Google News robots.txt disallows automated access to /rss for generic crawlers; continued use of this "
            "source needs the researcher's decision (see E31 FINAL_REPORT).",
        ],
        "disclaimer": DISCLAIMER,
    }
    rec = _clean(rec)                       # NaN / inf are not JSON: an undefined metric is null
    body = {k: v for k, v in rec.items()}
    rec["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return rec


def write_pdf(rec: dict, path: Path):
    """Chapter I 1.7: forecast scores, driver breakdowns, performance metrics and data-sufficiency disclosures for
    each province and CALABARZON. The record hash is the PDF Subject; the API refuses a PDF that does not match."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table

    st = getSampleStyleSheet()
    P = lambda t, s="Normal": Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), st[s])  # noqa: E731
    pct = lambda x: "-" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    els = [P(rec["title"], "Title"), P(f"Information cutoff {rec['information_cutoff']}. Record SHA-256 {rec['content_sha256']}."),
           P(rec["disclaimer"]), P("What is estimated", "Heading2")]
    td = rec["target_definition"]
    els += [P(td["label"]), P("H: " + td["H"]), P("D: " + td["D"]), P("Not: " + td["is_not"])]
    rh = rec["regional_hunger"]
    els += [P("CALABARZON: official regional hunger (measured)", "Heading2"),
            Table([["Quarter", "Round", "Hunger %", "Posted"]] + [[o["quarter"], o["round"][:45], o["hunger_pct"], o["published"]]
                                                               for o in rh["rounds"]]), P(rh["geographic_level"])]
    q3 = next(q for q in rec["quarters"] if q["mode"] == "RETROSPECTIVE_BLIND")
    els += [P("2026-Q3: first unseen quarter (frozen forecast vs released outcome)", "Heading2"),
            Table([["Province", "P(HIGH) frozen 1 Jul", "Observed S1", "Observed label"]] +
                  [[v["province"], pct(v["p_high"]), v["observed_S1"], v["observed_label"]] for v in q3["provinces"].values()]),
            Table([["Source", "Arm", "Lead", "Accuracy", "Brier"]] +
                  [[s["source"][:30], s["arm"], s["lead"], s["accuracy"], s["brier"]] for s in q3["scores"]]),
            P(rec["validation"]["unseen_quarter_2026Q3"]["caveat"]), PageBreak()]
    for c, b in rec["provinces_now"].items():
        n, f = b["nowcast_2026Q4"], b["forecast_2027Q1"]
        nq = b["news_2026Q4_to_cutoff"] or {}
        els += [P(b["province"], "Heading2"),
                Table([["", "2026-Q4 NOWCAST (lead 0)", "2027-Q1 FORECAST (lead 1)"],
                       ["P(S1 above threshold)", pct(n["p_high"]), pct(f["p_high"])],
                       ["Signal", n["signal"], f["signal"]],
                       ["S1 80% interval", str(n["S1_80pct_interval"]), str(f["S1_80pct_interval"])]] +
                      [[d["factor"], f"{d['contribution']:+.2f}", f"{f['drivers'][i]['contribution']:+.2f}"]
                       for i, d in enumerate(n["drivers"])]),
                P(n["driver_method"]), P(b["price_pressure_text"]),
                P(f"News 2026-Q4 (1-14 Oct): {nq.get('admitted_after_dedup', 0)} validated article(s) of "
                  f"{nq.get('province_attributed', 0)} province-attributed; status {nq.get('evidence_status_v2', 'n/a')}."),
                P(b["attention"] + ". " + b["suggested_use"]), Spacer(1, 4)]
        top = sorted([r for r in rec["lgu_ranking"]["rows"] if r["province_code"] == c and r["rank_in_province"]],
                     key=lambda r: r["rank_in_province"])[:5]
        els.append(Table([["Top LGUs (indicative)", "Risk index", "Poverty value kind"]] +
                         [[r["lgu_name"], r["risk_index"], r["poverty_value_kind"][:40]] for r in top]))
    els += [PageBreak(), P("Performance metrics (development quarters, lead 1)", "Heading2")]
    rows = [["Arm", "n", "HIGH/LOW", "Acc", "Bal.acc", "Prec", "Recall", "F1", "ROC-AUC", "Brier"]]
    for a in rec["validation"]["development_metrics_T1"]["arms"].values():
        m = a["by_lead"].get("1")
        if m:
            f2 = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
            rows.append([a["label"][:44], m["n"], f"{m['HIGH']}/{m['LOW']}", f2(m["accuracy"]), f2(m["balanced_accuracy"]),
                         f2(m["precision"]), f2(m["recall"]), f2(m["f1"]), f2(m["roc_auc"]), f2(m["brier"])])
    els += [Table(rows), P(rec["validation"]["threshold_75pct"]["verdict"])]
    ho = rec["validation"]["news_relevance"]["holdout"]["gates"]["R1"]
    els += [P("News relevance validation (blind holdout)", "Heading2"),
            P(f"Rule R1: precision {ho['precision']} (95% CI {ho['ci95_precision_recall_f1'][0]}), recall {ho['recall']} "
              f"(95% CI {ho['ci95_precision_recall_f1'][1]}), F1 {ho['f1']}."),
            P("Data sufficiency (news, FSSI-v2): " + json.dumps(rec["news"]["totals"])),
            P("Limitations", "Heading2")] + [P("- " + t) for t in rec["limitations"]] + [P(rec["disclaimer"])]
    SimpleDocTemplate(str(path), pagesize=landscape(A4), title=rec["title"], subject=rec["content_sha256"],
                      invariant=1, pageCompression=0).build(els)


def main():
    rec = build()
    blob = json.dumps(rec, indent=1, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
    for p in (BD / "data" / "e31" / "e31_record.json", EXP / "dashboard_dev" / "public" / "e31_record.json",
              EXP / "runs" / "e31_record.json"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)
    for pdf in (BD / "data" / "e31" / "aiPHeed_E31_assessment_report.pdf",
                EXP / "dashboard_dev" / "public" / "aiPHeed_E31_assessment_report.pdf"):
        write_pdf(rec, pdf)
    print(rec["content_sha256"], len(blob), "bytes;", len(rec["quarters"]), "quarters;",
          len(rec["news"]["articles"]), "articles;", len(rec["lgu_ranking"]["rows"]), "LGUs")


if __name__ == "__main__":
    main()
