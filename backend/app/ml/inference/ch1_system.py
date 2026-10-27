"""
app/ml/inference/ch1_system.py
------------------------------
The served Chapter I food-insecurity risk forecast (branch aiPHeed/lead2-optimization).

Chapter I §1.4 defines the dependent variable as "the binary food insecurity risk classification, either high or low,
of a CALABARZON province in a given quarter", and §1.7 says SWS hunger and PSA food prices determine it. The label
(T43c) is HIGH when Balance Luzon hunger is above 11.3% AND the province's food inflation (or food minus headline) is
above its 2021-22 60th percentile. The model (P0H4, LEAD2_OPTIMIZATION) gives P(HIGH) = P(hunger condition) x P(price
condition): the price part from ONE LightGBM trained on the rows of every lead (all 12 indicator families, the lead, and
World Bank world rice/cereal/oil/urea prices), refitted at each issue date (unchanged from UNI-FINAL); the hunger part
from the latest Balance Luzon SWS reading, its uncertainty taken from the 2021+ latest-reading errors of all four SWS
areas.

Evaluated walk-forward (LEAD2_OPTIMIZATION, protocol 88ee80bc + Addenda 1-4): Lead 1 passed every frozen reliability
criterion (accuracy 0.843 on 70 province-quarters); Leads 2-15 did not. This module serves the exported rows
(backend/data/ch1_engine/, written by LEAD2_OPTIMIZATION/runner/export_l2.py) and is active in thesis mode unless
AIPHEED_MAP_MODEL=firi.
"""
from __future__ import annotations

import csv
import functools
import json
import os
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data" / "ch1_engine"
# FORECAST_RESEARCH candidate P0H4-U (not the default): the same rows, with Lead-2+ forecasts re-issued after the SWS
# release. Served only when AIPHEED_CH1_ENGINE=fr and its export exists.
DATA_FR = DATA.parent / "ch1_engine_fr"


def data_dir() -> Path:
    if os.getenv("AIPHEED_CH1_ENGINE", "").lower() == "fr" and (DATA_FR / "rows.csv").exists():
        return DATA_FR
    return DATA
FIVE_GROUPS = {"market": ("A1", "A2", "A3"), "climate": ("C1", "C2", "C3"), "fish_kill": ("C4",),
               "employment": ("E1",), "ofw_remittance": ("E2",)}
# The dashboard shows the five trigger groups the thesis proposal presented (user decision 2026-10-27, reverting the
# eight-row display of FINAL_ARCHITECTURE section 4). Poverty and density, news and the regional hunger indicator stay
# model inputs; their share of the attribution is stated in the evidence note and in otherPct, never drawn as a bar.
SHOWN_GROUPS = dict(FIVE_GROUPS)
OTHER = ("V1", "N1", "H1")
GROUP_LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fisheries production",
                "employment": "Employment", "ofw_remittance": "OFW Remittance", "poverty": "Poverty & vulnerability",
                "news": "News signals", "hunger_indicator": "Regional hunger (indicator)"}
INDICATOR = {
    "id": "chapter1_food_insecurity_risk",
    "name": "Food-insecurity risk (Chapter I definition): probability that the province is HIGH risk",
    "definition": ("A province is HIGH risk in a quarter when SWS Balance Luzon hunger is above 11.3% AND the "
                   "province's food prices are rising unusually fast (PSA food inflation, or food inflation minus "
                   "headline inflation, above the province's 2021-22 60th percentile), as Chapter I (1.4, 1.7) "
                   "defines the risk from SWS hunger and PSA food prices. The number is the forecast probability of "
                   "HIGH: P(hunger condition) x P(price condition), the price part from one LightGBM, trained on every "
                   "forecast horizon together, on all 12 indicator families and world food prices; the hunger part from "
                   "the latest SWS reading and how much SWS hunger readings have moved over the same span. HIGH at 0.50."),
    "unit": "probability 0-1 (HIGH at 0.50)",
    "horizon": ("issued on the first day of a quarter; Lead 1 = that quarter (passed the reliability test), "
                "Lead 2 = the next quarter (not established as reliable)"),
    "source": ("SWS hunger (Balance Luzon, non-commissioned rounds); PSA provincial CPI; PSA rice, production, LFS, "
               "poverty and population; BSP remittances; PAGASA ENSO; IBTrACS; news (FSSI-v3, GDELT)"),
    "caveat": ("A risk class, not a measured provincial hunger rate: SWS reports hunger only for Balance Luzon, the same "
               "for all five provinces, so provinces differ only through food prices. The hunger part follows the newest "
               "SWS reading and cannot anticipate a new hunger surge before SWS publishes it."),
}
LGU_BASIS = ("Relative position within the province: the province's Chapter I risk probability re-weighted by PSA "
             "poverty incidence (60%) and population density (40%), as Objective 3 specifies. Not a measured or official "
             "municipal food-insecurity rate; the ranking itself has not been checked against municipal outcomes.")
# SYSTEM_FIXES item 2: an LGU's colour is its province's class; the index only orders LGUs within the province (it is
# the province probability scaled down by vulnerability, so a 0.50 cut-off on it showed HIGH provinces as all-LOW towns).
LGU_LEVEL_BASIS = ("Colour = the province's Chapter I risk class (HIGH when the province probability is 0.50 or more). "
                   "The number and rank are this city's or municipality's priority within the province: the province "
                   "probability re-weighted by PSA poverty incidence (60%) and population density (40%), as Objective 3 "
                   "specifies. Not a measured or official municipal food-insecurity rate; the ranking has not been "
                   "checked against municipal outcomes.")


def active() -> bool:
    return os.getenv("AIPHEED_MAP_MODEL", "ch1").lower() == "ch1" and (data_dir() / "rows.csv").exists()


@functools.lru_cache(maxsize=2)
def _rows(path: str, mtime: int) -> dict[tuple[str, str], dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return {(r["province_code"], r["quarter"]): r for r in csv.DictReader(f)}


def rows() -> dict[tuple[str, str], dict]:
    p = data_dir() / "rows.csv"
    return _rows(str(p), p.stat().st_mtime_ns)


@functools.lru_cache(maxsize=2)
def _evaluation(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluation() -> dict:
    return _evaluation(str(data_dir() / "evaluation.json"))


def sws_update_text(r: dict) -> str:
    """The candidate's note for a row re-issued after the SWS release (empty for quarter-start rows)."""
    u = evaluation().get("sws_update")
    if not u or r.get("issue_schedule") != "B":
        return ""
    m, a = u["lead2"]["metrics"], u["lead2"]["quarter_start_issue"]["metrics"]
    return (f" Re-issued {r['issue_date']}, the day after SWS published its {r.get('sws_newest_q')} hunger reading. At "
            f"Lead 2 this update scored accuracy {m['accuracy']:.2f} with HIGH recall {m['recall']:.2f} (quarter-start "
            f"issue: {a['accuracy']:.2f}, recall {a['recall']:.2f}), but it still fails "
            f"{', '.join(u['lead2']['failed'])}, so it remains experimental.")


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
    text = (f"Lead-{lead} forecast: experimental. Only Lead {rl or 0} passed the reliability test; this horizon was "
            f"tested and failed, so it is not a validated forecast")
    upd = sws_update_text(r)
    return text + ("." + upd).rstrip(".") if upd else text


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
        "horizon_label": what, "origin": r["issue_date"], "verification_date": r["issue_date"],
        # SYSTEM_FIXES: this row's own source label (the copied FIRI base row said "THESIS_LEAD2_...")
        "mode": f"{r.get('model') or 'P0H4'}_LEAD{int(r['lead'])}_{'FORECAST' if k == 'forecast' else 'BACKTEST'}",
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


GROUP_KEYS = tuple(SHOWN_GROUPS)


def group_status(code: str | None, quarter: str, key: str, pct: int) -> str | None:
    """Status of a trigger group for THIS model (LEAD2_OPTIMIZATION contributor audit: the FIRI record's statuses said
    "no published value" for 135 groups whose inputs the served model had). insufficient_data only when none of the
    group's inputs had a published value at the issue date; region scope: when no province had one."""
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    if not rs or f"avail_{key}" not in rs[0]:
        return None
    if not any(str(r[f"avail_{key}"]) == "1" for r in rs):
        return "insufficient_data"
    return "contributes" if pct > 0 else "no_effect"


# SYSTEM_FIXES item 5: what two of the bars really are (BIAS_AUDIT; FINAL_SYSTEM_SELECTION section 6).
EMPLOYMENT_CAUTION = ("Caution: the employment input is a national figure that mostly follows the calendar trend "
                      "(correlation +0.95 with time), so the direction of this bar is not a reliable reading of job "
                      "conditions.")
NEWS_BASIS = ("This bar reflects GDELT's national count of price-related food news; the Food Stress Sentiment Index "
              "(FSSI-v3) built from the articles in the News panel is also an input, but tests found it does not change "
              "the forecast.")
GROUP_NOTES = {"employment": EMPLOYMENT_CAUTION, "news": NEWS_BASIS}


def evidence_note(code: str | None, quarter: str, other_pct: float | None = None, group: str | None = None) -> str:
    """What the bars measure, in this forecast's own numbers: the push of each group on the price part only."""
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    h = float(rs[0]["pi_hunger"]) if rs else None
    hunger = f" (here {h:.0%})" if h is not None else ""
    if other_pct is None:
        other_pct = other_share(rs)
    other = (f" Poverty and density, news (GDELT's national count of price-related food news; the FSSI-v3 index from "
             f"the News panel's articles has no measured effect) and the regional hunger indicator inside the price "
             f"model account for another {other_pct:.0f}% of its attribution, not shown in the bars."
             if other_pct else "")
    note = ("The bars show each of the five trigger groups' relative push (SHAP, log-odds, rescaled to 100%) on the "
            "LightGBM's estimate that food prices rise unusually fast. They are model influence, not shares of hunger "
            f"caused by each factor, and they leave out the regional hunger condition{hunger}, which multiplies that "
            f"estimate into the risk probability, and the forecast horizon itself.{other}")
    return f"{note} {GROUP_NOTES[group]}" if group in GROUP_NOTES else note


def other_share(rs: list[dict]) -> float:
    """Percent of the absolute SHAP attribution of the given rows that falls on the families not drawn as bars."""
    def shap(r, f):
        return abs(_f(r.get(f"shap_{f}")) or 0.0)
    fams = [f for g in FIVE_GROUPS.values() for f in g] + list(OTHER)
    total = sum(shap(r, f) for r in rs for f in fams)
    return 100 * sum(shap(r, f) for r in rs for f in OTHER) / total if total else 0.0


QUARTER_MONTHS = {1: "Jan-Mar", 2: "Apr-Jun", 3: "Jul-Sep", 4: "Oct-Dec"}


def _period(issue_date: str, back: int) -> str:
    """Months of the quarter `back` quarters before the issue date's quarter ('Apr-Jun 2026' for 2026-10-01, back=2):
    the origin quarter t is the quarter before the issue date (back=1); t-1 is back=2."""
    i = int(issue_date[:4]) * 4 + (int(issue_date[5:7]) - 1) // 3 - back
    return f"{QUARTER_MONTHS[i % 4 + 1]} {i // 4}"


def _change(v: float, unit: str) -> str:
    return f"{abs(v):.1f}{unit} {'higher' if v > 0 else 'lower'}" if round(v, 1) else "about the same"


def plain_evidence(code: str | None, quarter: str, group: str) -> str | None:
    """The card sentence for a group, from the values THIS forecast used at its issue date (rows.csv val_<column>,
    LEAD2_OPTIMIZATION family_inventory: periods and signs), never another model's record. None at region scope."""
    if group == "market":
        return market_evidence(code, quarter)
    if code is None:                      # region: no single value, but the two cautions still apply
        return GROUP_NOTES.get(group)
    r = row(code, quarter)
    if r is None:
        return None
    d = r["issue_date"]
    v = {c: _f(r.get(f"val_{c}")) for c in ("A3", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "G_pri_yoy", "H1")}
    none = "No published value was available at this forecast's issue date; missing data is not a sign of low risk."
    if group == "employment":
        fact = (none if v["E1"] is None else
                f"National unemployment in {_period(d, 2)} was {_change(v['E1'], ' points')} than a year earlier.")
        return f"{fact} {EMPLOYMENT_CAUTION}"
    if group == "news":
        g = ("" if v["G_pri_yoy"] is None else
             f" In {_period(d, 1)}, the share of the country's food-security news about prices was "
             f"{_change(100 * v['G_pri_yoy'], ' points')} than a year earlier.")
        fssi = ("" if v["N1"] is not None else
                " This quarter the province had too few articles for an FSSI-v3 value, so it is left blank, not zero.")
        return f"{NEWS_BASIS}{g}{fssi}"
    if group == "climate":
        parts = [("A PAGASA El Nino alert or advisory was in force at the issue date." if v["C1"] else
                  "No PAGASA El Nino alert or advisory was in force at the issue date.") if v["C1"] is not None else None,
                 None if v["C2"] is None else f"{int(v['C2'])} typhoon(s) passed within 300 km in {_period(d, 1)}.",
                 None if v["C3"] is None else
                 f"The weaker of the rice and corn harvests in {_period(d, 2)} was {_change(-v['C3'], '%')} than a "
                 "year earlier."]
        return " ".join(p for p in parts if p) or none
    if group == "fish_kill":
        return none if v["C4"] is None else (f"Fisheries production in {_period(d, 2)} was "
                                             f"{_change(-v['C4'], '%')} than a year earlier.")
    if group == "ofw_remittance":
        return none if v["E2"] is None else (f"OFW cash remittances (national) in {_period(d, 2)} were "
                                             f"{_change(-v['E2'], '%')} than a year earlier.")
    if group == "poverty":
        return ("The province's poverty and population-density profile (PSA 2021 poverty estimates, 2024 census) is "
                "fixed; it shifts this province's estimate relative to the other provinces.")
    if group == "hunger_indicator":
        return None if v["H1"] is None else (
            f"Inside the price model, the regional hunger outlook is an input: {v['H1']:.0%} chance that Balance Luzon "
            f"hunger is above 11.3% (latest SWS reading {float(r['h_last']):.1f}%, {r['sws_newest_q']}). The hunger "
            f"condition that multiplies the forecast ({float(r['pi_hunger']):.0%}) is computed separately, with a wider "
            "uncertainty.")
    return None


def drivers(code: str, quarter: str, base: dict) -> dict:
    """The driver bars from the LightGBM price part's SHAP values (log-odds): the five approved trigger groups, plus the
    share of the other families (poverty, news, regional hunger indicator) as otherPct."""
    r = row(code, quarter)
    if r is None:
        return base
    sh = {f: _f(r.get(f"shap_{f}")) or 0.0 for f in ("A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2",
                                                       "N1", "H1")}
    news = {d["driver_group"]: d.get("trigger_proportion") for d in base.get("drivers", [])}
    ds = []
    for g, fams in SHOWN_GROUPS.items():
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


# ---------------------------------------------------------------------------------------------- reports (SYSTEM_FIXES 1)
# The downloadable reports (report_data_e31.py for /report/data, report.py for /report) describe THIS forecast; with the
# Chapter I engine served they used to describe FIRI v2 ("a proxy composite, not a probability") beside its numbers.
REPORT_COVER = ("<b>The number below is the forecast probability that the province is HIGH food-insecurity risk</b> "
                "under the study's Chapter I definition, from 0 to 1, HIGH at 0.50: regional SWS hunger (Balance Luzon) "
                "above 11.3% AND the province's food prices rising unusually fast. It multiplies the chance of the "
                "hunger condition (from the latest SWS reading) by the chance of the food-price condition (one LightGBM "
                "on all 12 indicator families, trained on every forecast horizon). SWS reports hunger only for Balance "
                "Luzon, so the provinces differ only through food prices. <b>It is a risk class under a proxy "
                "definition, not a measured food-insecurity rate</b>.")
REPORT_FOOTER = ("Forecast probability of HIGH food-insecurity risk (Chapter I proxy definition) -- not an official food "
                 "insecurity classification.")
REPORT_BARS_NOTE = ("Red bars pushed the model's estimate that food prices rise unusually fast up, green bars pulled it "
                    "down; groups with no effect are not shown. Relative model influence, not causes.")


def model_line() -> str:
    """The served model in one line, with its reliability verdict (report metadata)."""
    ev = evaluation()
    m = ev["leads"]["1"]["metrics"]
    rl = reliable_lead()
    name = "P0H4-U" if ev.get("sws_update") else "P0H4"
    upd = (" Lead-2+ forecasts are re-issued the day after each SWS release (hunger part only)."
           if ev.get("sws_update") else "")
    return (f"{name}: P(HIGH) = P(regional hunger above 11.3%, from the latest SWS Balance Luzon reading) x P(food-price "
            f"condition, one LightGBM across forecast horizons on 12 indicator families). Lead {rl or 0} reliable "
            f"(development accuracy {m['accuracy']:.3f}, {m['tp'] + m['tn']}/{m['n']} province-quarters); longer leads "
            f"experimental.{upd}")


def driver_text(triggers: list[dict], hunger: float | None = None, other_pct: float | None = None) -> str:
    """The report paragraph beside the driver bars (plain text; the caller escapes it)."""
    up = [f"{t['label']} {t['pct']}%" for t in triggers if t["pct"] > 0 and t["direction"] == "increases_risk"]
    down = [f"{t['label']} {t['pct']}%" for t in triggers if t["pct"] > 0 and t["direction"] == "protective"]
    shown = {t["key"] for t in triggers if t["pct"] > 0}
    h = f" ({hunger:.0%})" if hunger is not None else ""
    other = (f" Poverty and density, news and the regional hunger indicator, which are not among the five trigger "
             f"groups, account for another {other_pct:.0f}% of that influence." if other_pct else "")
    return ("Each bar is a trigger group's relative influence (SHAP, rescaled to 100%) on the model's estimate that "
            "food prices rise unusually fast. "
            + ("Pushing it up: " + ", ".join(up) + ". " if up else "")
            + ("Pulling it down: " + ", ".join(down) + ". " if down else "")
            + f"The regional hunger condition{h}, which multiplies that estimate into the probability, is not part of "
              "the bars. They show what moved the model, not causes." + other
            + "".join(f" {GROUP_NOTES[g]}" for g in ("employment", "news") if g in shown))


def reliability_sentences() -> list[str]:
    """The evidence behind the forecast, for the reports' notes and method sections."""
    ev = evaluation()
    rl = reliable_lead()
    l1, l2 = ev["leads"]["1"], ev["leads"].get("2")
    m1 = l1["metrics"]
    out = [f"Reliability rule (fixed before scoring, LEAD2_OPTIMIZATION protocol): criteria R1-R7 on walk-forward "
           f"forecasts. Lead {rl or 0} passed: accuracy {m1['accuracy']:.3f} ({m1['tp'] + m1['tn']}/{m1['n']} "
           f"province-quarters over {l1['n_quarters']} quarters; always-LOW {l1['baseline_accuracy']['ALWAYS-LOW']:.3f}), "
           f"precision {m1['precision']:.2f}, recall {m1['recall']:.2f}, AUC {m1['auc']:.2f}, Brier {m1['brier']:.3f}."]
    if l2:
        m2 = l2["metrics"]
        out.append(f"Lead 2 failed the rule (accuracy {m2['accuracy']:.3f}, {m2['tp'] + m2['tn']}/{m2['n']}; HIGH recall "
                   f"{m2['recall']:.2f}): a Lead-2 value is an experimental forecast, not a validated one.")
    u = ev.get("sws_update")
    if u:
        mu = u["lead2"]["metrics"]
        out.append(f"SWS-update issue (candidate {ev.get('model')}): Lead-2 forecasts re-issued the day after SWS publishes "
                   f"the newest hunger reading (median {u['lead2']['warning_days_median']:.0f} days before the target "
                   f"quarter starts) scored accuracy {mu['accuracy']:.3f} ({mu['tp'] + mu['tn']}/{mu['n']}), HIGH recall "
                   f"{mu['recall']:.2f}, Brier {mu['brier']:.3f}; still failing {', '.join(u['lead2']['failed'])}. "
                   f"These re-issued forecasts are sealed separately (SHA-256 {u['seal_sha256'][:8]}).")
    out.append(f"Development evidence: every scored quarter was examined while the model was built. The forecasts issued "
               f"{ev['seal_issue_date']} are sealed (SHA-256 {ev['seal_sha256'][:8]}) and will be scored when SWS "
               "publishes those quarters.")
    return out


def method_rows() -> tuple[list[str], list[list[str]]]:
    """Per-lead evaluation table for the server PDF's method section (Objective 2 metrics)."""
    head = ["Lead", "Rows", "Accuracy", "Precision", "Recall", "F1", "AUC", "Brier", "Reliable"]
    rows = []
    for k, v in sorted(evaluation()["leads"].items(), key=lambda kv: int(kv[0])):
        if int(k) > 4:
            continue
        m = v["metrics"]
        rows.append([k, str(m["n"]), f"{m['accuracy']:.3f}", f"{m['precision']:.2f}", f"{m['recall']:.2f}",
                     f"{m['f1']:.2f}", f"{m['auc']:.2f}", f"{m['brier']:.3f}", "yes" if v["reliable"] else "no"])
    return head, rows


# ---------------------------------------------------------------------------------------------- summary (SYSTEM_FIXES 1, 6)
EVENT = "food-insecurity risk under the Chapter I definition (probability of HIGH)"
VALUE_LABELS = {"A3": "wholesale rice price change", "C1": "PAGASA El Nino status", "C2": "typhoon count",
                "C3": "rice and corn harvest change", "C4": "fisheries production change", "E1": "unemployment change",
                "E2": "OFW remittance change", "N1": "FSSI-v3 news index (too few articles)",
                "G_pri_yoy": "GDELT price-news share", "H1": "regional hunger outlook"}


def data_status(code: str | None, quarter: str) -> tuple[str, str]:
    """(status, note) from the forecast's own input values at the issue date (rows.csv val_<column>): which inputs had
    no published value. Region scope: an input missing in any province."""
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    if not rs or not any(k.startswith("val_") for k in rs[0]):
        return "unavailable", "The input values of this forecast were not recorded."
    missing = [lab for col, lab in VALUE_LABELS.items() if any(_f(r.get(f"val_{col}")) is None for r in rs)]
    if not missing:
        return "sufficient", "Every input had a published value at the issue date."
    return "limited", ("No published value at the issue date for: " + ", ".join(missing) + ". Missing data is left "
                       "blank, never counted as low risk.")


def identity(code: str | None, quarter: str) -> dict | None:
    """The served model's identity for the summary's modelIdentity field."""
    r = next((r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)), None)
    if r is None:
        return None
    return {"servingMode": "thesis", "servedModel": r.get("model") or "P0H4", "modelVersion": model_line(),
            "lead": int(r["lead"]), "issued": r["issue_date"], "targetQuarter": quarter,
            "evidenceStatus": ("reliable horizon (development evidence)" if status(r) == "reliable" else
                               "experimental horizon (failed the reliability test)"),
            "lead2Accuracy": next((s for s in reliability_sentences() if s.startswith("Lead 2")), ""),
            "seal": r.get("seal_sha256") or None}
