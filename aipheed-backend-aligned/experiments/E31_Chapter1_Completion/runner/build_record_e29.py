"""E29 DA brief record (schema 4) and its PDF: the E28 record (rebuilt, unchanged content) plus what DA needs to tell
observed evidence from model estimates. ONE record for API, dashboard and PDF.

    python -B runner/build_record_e29.py

Added in E29 (section 7 of the E29 brief):
  * regional_observation: the official SWS Balance Luzon hunger rounds, shown ONCE, marked as one regional value shared
    by all five provinces (never five local measurements);
  * per province: observed price pressure (measured relative food inflation, last two quarters, direction);
    an evidence table where every item is MEASURED / ESTIMATED / EXPERIMENTAL / UNAVAILABLE with its geographic level;
    what official information would help validate the situation; suitability = MONITORING ONLY;
  * LGU rows: ordering_basis (density only when the poverty value is a province-mean substitute);
  * a wording check of every price-pressure and hunger text against app.quarterly.targets.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard29  # noqa: E402

guard29.install()
import pandas as pd  # noqa: E402

import build_record_e28 as B  # noqa: E402

EXP = guard29.EXP
BD = EXP / "backend_dev"
from app.quarterly.targets import TARGETS, wording_violations  # noqa: E402

SCHEMA = 4
VALIDATE_WITH = [
    "the next SWS hunger round (regional) and its sample size",
    "PSA provincial food CPI for the coming months (and DA Bantay Presyo market price monitoring)",
    "DA provincial agriculture office and LGU field reports (crop damage, market supply)",
    "DSWD/LGU assistance and evacuation reports after shocks",
    "CBMS household food-insecurity (FIES) results for the LGUs, when released",
]


def build() -> dict:
    base = B.build()
    rounds = pd.read_csv(BD / "data" / "inputs" / "sws_rounds.csv")
    prod = rounds[rounds["source"].str.startswith("production") & rounds["definition_A"].astype(str).str.lower().eq("true")]
    prod = prod.sort_values("published_eff")
    last3 = prod.tail(3)
    obs = [{"quarter": r.quarter, "round": r.round, "hunger_pct": float(r.H), "published": str(r.published_eff)[:10],
            "date_type": r.date_type} for r in last3.itertuples()]
    regional = {
        "what": "SWS self-rated involuntary hunger, Balance Luzon (Luzon outside Metro Manila)",
        "kind": "MEASURED", "geographic_level": "regional - ONE value shared by all five provinces; not a provincial "
                                                "or municipal measurement",
        "rounds": obs, "change_last_two_pp": round(obs[-1]["hunger_pct"] - obs[-2]["hunger_pct"], 1),
        "note": "2026 publication dates are unverified upper bounds (fetch time).",
        "target_registry": TARGETS["H"]["construct"],
    }
    D = pd.read_csv(BD / "data" / "inputs" / "d_quarterly_panel.csv", dtype={"province_code": str})
    cov = json.loads((B.NEWS / "coverage_audit.json").read_text(encoding="utf-8"))
    latest_q = max(r["quarter"] for r in cov)
    rank_rows = base["lgu_ranking"]["rows"]
    for code, b in base["forecast_quarter"]["provinces"].items():
        d = D[D["province_code"] == code].sort_values("quarter").tail(2)
        d1, d2 = d.iloc[0], d.iloc[1]
        ch = float(d2["D"] - d1["D"])
        direction = "rising" if ch > 0.5 else "falling" if ch < -0.5 else "little change"
        nrow = next(r for r in cov if r["province_code"] == code and r["quarter"] == latest_q)
        n_lgu = sum(1 for r in rank_rows if r["province_code"] == code)
        n_sub = sum(1 for r in rank_rows if r["province_code"] == code and r["poverty_lgu_estimate"] is None)
        b["observed_price_pressure"] = {
            "kind": "MEASURED (constructed from PSA CPI)", "geographic_level": "provincial",
            "quarters": [d1["quarter"], d2["quarter"]],
            "relative_food_inflation_pp": [round(float(d1["D"]), 2), round(float(d2["D"]), 2)],
            "direction": direction,
            "text": (f"Provincial food prices rose {abs(float(d2['D'])):.2f} pp {'faster' if d2['D'] > 0 else 'slower'} "
                     f"than the CALABARZON average in {d2['quarter']} ({direction} from {d1['quarter']}). This is "
                     "price pressure, not food insecurity."),
        }
        b["evidence_table"] = [
            {"item": "Regional hunger (SWS)", "kind": "MEASURED", "level": "regional (shared by all provinces)",
             "value": f"{obs[-1]['hunger_pct']}% ({obs[-1]['quarter']})"},
            {"item": "Price pressure (relative food inflation)", "kind": "MEASURED", "level": "provincial",
             "value": f"{float(d2['D']):+.2f} pp ({d2['quarter']}), {direction}"},
            {"item": "News evidence (FSSI)", "kind": "MEASURED coverage", "level": "provincial",
             "value": f"{nrow['coverage_status']} ({nrow.get('included_in_fssi', 0)} usable articles, {latest_q})"},
            {"item": "Food-stress estimate for " + b["target_quarter"], "kind": "EXPERIMENTAL", "level": "province (regional hunger + provincial prices)",
             "value": f"P {100 * b['estimate']['p_above_threshold']:.0f}% (not validated)"},
            {"item": "LGU positions", "kind": "EXPERIMENTAL", "level": "city/municipality (derived, not measured)",
             "value": f"{n_lgu} LGUs; {n_sub} use a province-mean poverty substitute (density-only order)"},
            {"item": "Measured local food insecurity", "kind": "UNAVAILABLE", "level": "city/municipality",
             "value": "no authorized CBMS FIES or provincial FIES"},
        ]
        b["would_help_validate"] = VALIDATE_WITH
        b["suitability"] = ("MONITORING ONLY: no forecast lead has passed a validation standard (C6 not evaluable; "
                            "no arm beats persistence or always-HIGH). Not a basis for allocating resources.")
    for r in rank_rows:
        r["ordering_basis"] = ("population density only (poverty is a province-mean substitute)"
                               if r["poverty_lgu_estimate"] is None else "PSA municipal poverty SAE (60%) + density (40%)")
    base["lgu_ranking"]["not_a_measured_ranking"] = (
        "For the 126 LGUs whose poverty value is a province-mean substitute, the order inside a province is the order "
        "of population density. That is not a measured local food-insecurity ranking.")
    rec = {k: v for k, v in base.items() if k != "content_sha256"}
    rec.update({
        "schema": SCHEMA, "title": "aiPHeed E29 DA brief - CALABARZON (monitoring, experimental estimates)",
        "regional_observation": regional,
        "e28_record_sha256": base["content_sha256"],
        "status_kinds": {"MEASURED": "an official or collected observation, shown as published",
                         "ESTIMATED": "a model estimate with a validated basis (none at present)",
                         "EXPERIMENTAL": "a model estimate that has not passed a validation standard",
                         "UNAVAILABLE": "no authorized data"},
        "targets": {k: {kk: TARGETS[k][kk] for kk in ("status", "construct", "geography", "measures_food_insecurity_directly")}
                    for k in TARGETS},
    })
    texts = [b["observed_price_pressure"]["text"] for b in rec["forecast_quarter"]["provinces"].values()]
    viol = {t: wording_violations("T2", t) for t in texts if wording_violations("T2", t)}
    viol |= {regional["geographic_level"]: wording_violations("H", regional["geographic_level"])} \
        if wording_violations("H", regional["geographic_level"]) else {}
    assert not viol, f"target wording violations: {viol}"
    rec["content_sha256"] = B.content_hash(rec)
    return rec


def write_pdf(rec: dict, path: Path):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

    st = getSampleStyleSheet()
    P = lambda t, s="Normal": Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), st[s])  # noqa: E731
    els = [P(rec["title"], "Title"), P(f"Record SHA-256: {rec['content_sha256']}"), P(rec["status_banner"])]
    ro = rec["regional_observation"]
    els += [P("Official regional hunger (measured, shared by all five provinces)", "Heading2"),
            Table([["Quarter", "Round", "Hunger %", "Published"]] +
                  [[o["quarter"], o["round"][:40], o["hunger_pct"], o["published"]] for o in ro["rounds"]]),
            P(f"{ro['what']}. {ro['geographic_level']}. {ro['note']}"), Spacer(1, 6)]
    for b in rec["forecast_quarter"]["provinces"].values():
        els.append(P(b["province"], "Heading3"))
        els.append(Table([["Item", "Kind", "Level", "Value"]] +
                         [[e["item"], e["kind"], e["level"][:40], e["value"][:70]] for e in b["evidence_table"]]))
        els.append(P(b["observed_price_pressure"]["text"]))
        els.append(P(f"{b['headline']} {b['suggested_use']}"))
        els.append(P("Suitability: " + b["suitability"]))
    els.append(P("Would help validate: " + "; ".join(VALIDATE_WITH)))
    els.append(P(rec["lgu_ranking"]["not_a_measured_ranking"]))
    els.append(P(rec["disclaimer"]))
    SimpleDocTemplate(str(path), pagesize=landscape(A4), title=rec["title"], subject=rec["content_sha256"],
                      invariant=1, pageCompression=0).build(els)


def main():
    rec = build()
    blob = json.dumps(rec, indent=1, sort_keys=True, default=str).encode("utf-8")
    for t in (BD / "data" / "e29" / "da_brief_record.json", EXP / "dashboard_dev" / "public" / "e29_da_brief_record.json",
              EXP / "runs" / "e29_da_brief_record.json"):
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(blob)
    for pdf in (BD / "data" / "e29" / "aiPHeed_E29_DA_brief.pdf", EXP / "dashboard_dev" / "public" / "aiPHeed_E29_DA_brief.pdf"):
        write_pdf(rec, pdf)
    print("record", rec["content_sha256"])


if __name__ == "__main__":
    main()
