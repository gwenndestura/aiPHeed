"""
app/ml/inference/ch1_system.py
------------------------------
The served Chapter I food-insecurity risk forecast (branch aiPHeed/final-thesis-objectives).

Chapter I §1.4 defines the dependent variable as "the binary food insecurity risk classification, either high or low,
of a CALABARZON province in a given quarter", and §1.7 says SWS hunger and PSA food prices determine it. The label
(T43c) is HIGH when Balance Luzon hunger is above 11.3% AND the province's food inflation (or food minus headline) is
above its 2021-22 60th percentile. The model (CH1-LGBM) gives P(HIGH) = P(hunger condition) x P(price condition), the
price part from one LightGBM on all 12 indicator families.

Evaluated walk-forward (FINAL_THESIS_OBJECTIVES, protocol dd9ab815): Lead 1 passed every frozen reliability
criterion (accuracy 0.914 on 70 province-quarters); Leads 2-4 did not. This module serves the exported rows
(backend/data/ch1_engine/, written by export_ch1.py) and is active in thesis mode unless AIPHEED_MAP_MODEL=firi.
"""
from __future__ import annotations

import csv
import functools
import json
import os
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data" / "ch1_engine"
FIVE_GROUPS = {"market": ("A1", "A2", "A3"), "climate": ("C1", "C2", "C3"), "fish_kill": ("C4",),
               "employment": ("E1",), "ofw_remittance": ("E2",)}
OTHER = ("V1", "N1", "H1")
GROUP_LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
                "employment": "Employment", "ofw_remittance": "OFW Remittance"}
INDICATOR = {
    "id": "chapter1_food_insecurity_risk",
    "name": "Food-insecurity risk (Chapter I definition): probability that the province is HIGH risk",
    "definition": ("A province is HIGH risk in a quarter when SWS Balance Luzon hunger is above 11.3% AND the "
                   "province's food prices are rising unusually fast (PSA food inflation, or food inflation minus "
                   "headline inflation, above the province's 2021-22 60th percentile), as Chapter I (1.4, 1.7) "
                   "defines the risk from SWS hunger and PSA food prices. The number is the forecast probability of "
                   "HIGH: P(hunger condition) x P(price condition), the price part from one LightGBM on all 12 "
                   "indicator families. HIGH at 0.50."),
    "unit": "probability 0-1 (HIGH at 0.50)",
    "horizon": ("issued on the first day of a quarter; Lead 1 = that quarter (passed the reliability test), "
                "Lead 2 = the next quarter (not established as reliable)"),
    "source": ("SWS hunger (Balance Luzon, non-commissioned rounds); PSA provincial CPI; PSA rice, production, LFS, "
               "poverty and population; BSP remittances; PAGASA ENSO; IBTrACS; news (FSSI-v3, GDELT)"),
    "caveat": ("A risk class, not a measured provincial hunger rate: SWS reports hunger only for Balance Luzon, the same "
               "for all five provinces, so provinces differ only through food prices. Probabilities run slightly high "
               "(mean 0.30 vs an observed HIGH rate of 0.24 in testing)."),
}
LGU_BASIS = ("Relative position within the province: the province's Chapter I risk probability re-weighted by PSA "
             "poverty incidence (60%) and population density (40%), as Objective 3 specifies. Not a measured or official "
             "municipal food-insecurity rate; the ranking itself has not been checked against municipal outcomes.")


def active() -> bool:
    return os.getenv("AIPHEED_MAP_MODEL", "ch1").lower() == "ch1" and (DATA / "rows.csv").exists()


@functools.lru_cache(maxsize=2)
def _rows(path: str, mtime: int) -> dict[tuple[str, str], dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return {(r["province_code"], r["quarter"]): r for r in csv.DictReader(f)}


def rows() -> dict[tuple[str, str], dict]:
    p = DATA / "rows.csv"
    return _rows(str(p), p.stat().st_mtime_ns)


@functools.lru_cache(maxsize=1)
def evaluation() -> dict:
    return json.loads((DATA / "evaluation.json").read_text(encoding="utf-8"))


def reliable_lead() -> int | None:
    return evaluation().get("max_reliable_lead")


def horizon() -> dict:
    """Addendum 3 (FINAL_VERIFICATION): the three horizons the dashboard must keep apart - the longest lead the model
    generates, the longest lead with enough evidence to test (rule R1) and the longest that passes R1-R7."""
    h = evaluation().get("horizon") or {}
    generated = max((int(r["lead"]) for r in rows().values()), default=None)
    return {"generated_max_lead": generated, "evaluated_leads": h.get("leads_evaluated", []),
            "testable_max_lead": h.get("testable_horizon_R1"), "reliable_max_lead": reliable_lead(),
            "individually_passing_leads": h.get("individually_passing_leads", []),
            "why_not_longer": h.get("why_not_longer"),
            "reliable_quarters_after_newest_sws": (h.get("leads", {}).get(str(reliable_lead()), {})
                                                   .get("quarters_after_newest_sws") if reliable_lead() else None)}


def status(r: dict) -> str:
    """reliable when the row's lead is within the maximum reliable lead, else experimental (generated, not validated)."""
    return "reliable" if (reliable_lead() or 0) >= int(r["lead"]) else "experimental"


def covers(quarter: str) -> bool:
    return any(q == quarter for _, q in rows())


def row(code: str, quarter: str) -> dict | None:
    return rows().get((code, quarter))


def _f(x) -> float | None:
    return None if x in (None, "", "nan") else float(x)


def kind(r: dict) -> str:
    """retrospective (walk-forward, outcome known or quarter past) or forecast (issued 2026-10-01 or later)."""
    return "forecast" if r["issue_date"] >= "2026-10-01" else "retrospective"


def reliability_text(r: dict) -> str:
    lead = int(r["lead"])
    rl = reliable_lead()
    ev = evaluation()["leads"]["1"]
    if rl is not None and lead <= rl:
        return (f"Lead-{lead} forecast: this horizon passed the reliability test (accuracy {ev['metrics']['accuracy']:.2f}"
                f" on {ev['n']} past province-quarters)")
    return (f"Lead-{lead} forecast: experimental. Only Lead {rl or 0} passed the reliability test; this horizon was "
            f"tested and failed, so it is not a validated forecast")


def province_row(code: str, name: str, quarter: str, base: dict | None) -> dict | None:
    r = row(code, quarter)
    if r is None:
        return None
    p = float(r["probability"])
    k = kind(r)
    obs = r["observed"] or None
    if k == "forecast":
        what = f"{reliability_text(r)}; issued {r['issue_date']}; the outcome is not yet published."
    else:
        what = (f"Walk-forward Lead-{r['lead']} forecast made as of {r['issue_date']} with information published "
                f"before it (development evidence). Observed: {obs or 'no label (no regular SWS round)'}.")
    out = dict(base or {})
    out.update({
        "province_code": code, "province_name": name, "quarter": quarter,
        "risk_probability": round(p, 6), "risk_label": None, "observed_label": obs, "observed_S1": None,
        "data_sufficiency_flag": "SUFFICIENT", "forecast_horizon_quarters": int(r["lead"]),
        "horizon_label": what, "origin": r["issue_date"],
        "estimate_kind": "forecast" if k == "forecast" else "backtest",
        "price_pressure_score": float(r["pi_price"]), "hunger_condition_probability": float(r["pi_hunger"]),
        "score_type": "chapter1_risk_probability", "score_definition": INDICATOR["definition"],
        "band": "High" if p >= 0.5 else "Low",
        "confidence_statement": (f"{name}, {quarter}: {'HIGH' if p >= 0.5 else 'LOW'} food-insecurity risk "
                                 f"(probability {p:.2f}). {what}")})
    return out


def province_rows(base_rows: list[dict], quarter: str, names: dict[str, str]) -> list[dict]:
    by = {r["province_code"]: r for r in base_rows}
    out = []
    for code, name in names.items():
        r = province_row(code, name, quarter, by.get(code))
        if r is not None:
            out.append(r)
    out.sort(key=lambda r: r["risk_probability"], reverse=True)
    return out


def drivers(code: str, quarter: str, base: dict) -> dict:
    """The five approved driver bars from the LightGBM price part's SHAP values (log-odds), plus the share of the other
    families (poverty, news, regional hunger) as otherPct."""
    r = row(code, quarter)
    if r is None:
        return base
    sh = {f: _f(r.get(f"shap_{f}")) or 0.0 for f in ("A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2",
                                                       "N1", "H1")}
    news = {d["driver_group"]: d.get("trigger_proportion") for d in base.get("drivers", [])}
    ds = []
    for g, fams in FIVE_GROUPS.items():
        c = sum(sh[f] for f in fams)
        ds.append({"driver_group": g, "driver_label": GROUP_LABELS[g], "group_shap": round(c, 6),
                   "direction": "increases_risk" if c > 0 else "protective" if c < 0 else "no_effect",
                   "trigger_proportion": news.get(g)})
    total = sum(abs(v) for v in sh.values()) or 1.0
    return {**base, "drivers": ds, "other_pct": round(100 * sum(abs(sh[f]) for f in OTHER) / total, 1), "ch1": r}


def sentence(code: str | None, name: str, quarter: str, mean_p: float | None = None) -> str | None:
    """One sentence for the approved summary line (only the first sentence is shown)."""
    if code is None:
        if mean_p is None:
            return None
        rs = [rows()[k] for k in rows() if k[1] == quarter]
        if not rs:
            return None
        high = sum(float(r["probability"]) >= 0.5 for r in rs)
        h = float(rs[0]["pi_hunger"])
        return (f"FOOD-INSECURITY RISK for CALABARZON, {quarter}: {high} of {len(rs)} provinces HIGH (regional hunger "
                f"above 11.3% with probability {h:.0%}; HIGH also needs unusually fast food-price rises); "
                f"{reliability_text(rs[0])}.")
    r = row(code, quarter)
    if r is None:
        return None
    p, h, pp = float(r["probability"]), float(r["pi_hunger"]), float(r["pi_price"])
    why = ("regional hunger is likely above 11.3% and food prices are likely rising unusually fast" if p >= 0.5 else
           "food prices are not likely to rise unusually fast" if h >= 0.5 else "regional hunger is likely below 11.3%")
    return (f"FOOD-INSECURITY RISK for {name}, {quarter}: {'HIGH' if p >= 0.5 else 'LOW'} (probability {p:.2f}; "
            f"hunger condition {h:.0%}, food-price condition {pp:.0%}), because {why}; {reliability_text(r)}.")


def market_evidence(code: str | None, quarter: str) -> str | None:
    """The food-price card for the served Chapter I forecast: its own price-condition probability and the CPI facts
    it starts from (no other model's number)."""
    if code is None:
        return None
    r = row(code, quarter)
    if r is None:
        return None
    pp = float(r["pi_price"])
    gap = _f(r.get("A1_food"))
    fact = ("" if gap is None else
            f" Projected food inflation is {abs(gap):.1f} points {'above' if gap > 0 else 'below'} this province's "
            f"usual level (PSA CPI through {r['psa_newest_month']}).")
    return (f"The model gives a {pp:.0%} chance that food prices in {quarter} rise faster than usual in this "
            f"province.{fact}")
