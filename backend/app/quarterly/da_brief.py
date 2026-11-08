"""
app/quarterly/da_brief.py  (E28)
--------------------------------
The province brief DA Region IV-A reads: one place that turns a forecast's numbers into a statement that says what
was forecast, for where and when, how strongly, why, on what data, with what validation, and what a DA officer can
reasonably do with it. Pure functions: the inputs are the stored forecast row and the coverage/freshness facts, so the
API, the dashboard and the PDF show the same brief and the scenario tests can exercise every branch.

Rules (fixed by the E25-E28 evidence; see FINAL_REPORT):
  * No HIGH/LOW category unless the lead is VALIDATED (no lead is; E28 determination). The probability is shown with
    its interval and a signal strength (STRONG p <= .20 or >= .80; MODERATE; UNCERTAIN .35-.65).
  * Drivers are the forecast's own exact additive decomposition: margin = (mu_H - tau) + 2 mu_D, i.e. the regional
    hunger term and the provincial price term. They are attributions of THIS forecast, not proven causes.
  * Zero or insufficient news is reported as missing evidence, never as low risk; missing government data removes
    the estimate it feeds instead of being treated as zero.
  * Suggested uses are proportionate to the evidence: an EXPERIMENTAL estimate can prompt review and checking with
    field offices and official releases; it never prompts allocation decisions on its own, and aiPHeed never replaces
    official assessment.
"""
from __future__ import annotations

import math

SIGNAL_RULE = "STRONG if p <= 0.20 or p >= 0.80; UNCERTAIN if 0.35 <= p <= 0.65; otherwise MODERATE"


def signal(p: float | None) -> str | None:
    if p is None:
        return None
    if p <= 0.20 or p >= 0.80:
        return "STRONG"
    if 0.35 <= p <= 0.65:
        return "UNCERTAIN"
    return "MODERATE"


def _fmt(x, d=1):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}"


def province_brief(f: dict) -> dict:
    """f keys: province, target_quarter, lead, origin, info_cutoff, p, tau, mu_H, mu_D, sd_S1, lo80_S1, hi80_S1,
    evidence_status ('EXPERIMENTAL'|'VALIDATED'), previous_D (last measured D or None), last_round (label),
    last_round_published, last_cpi_month, news_quarter, news_status (coverage_status or 'NOT_AUTHORIZED'),
    news_articles_in_fssi, gov_missing (list of missing inputs), horizon_determination (text)."""
    p = f.get("p")
    validated = f.get("evidence_status") == "VALIDATED"
    out = {"province": f["province"], "target": "approved composite label S1 = H + 2D above its trailing median tau",
           "geographic_scope": (f"{f['province']} province; the hunger part H is the SWS Balance Luzon value shared by "
                                "all five provinces, the price part 2D is provincial"),
           "target_quarter": f.get("target_quarter"), "origin": f.get("origin"), "lead_quarters": f.get("lead"),
           "information_cutoff": f.get("info_cutoff"),
           "evidence_status": f.get("evidence_status", "EXPERIMENTAL"),
           "horizon_determination": f.get("horizon_determination")}
    missing = list(f.get("gov_missing") or [])
    if p is None:
        out.update({"estimate": None, "signal": None, "category": None,
                    "headline": f"No estimate for {f['province']}: required inputs are missing.",
                    "drivers": [], "missing_inputs": missing})
    else:
        sig = signal(p)
        out.update({
            "estimate": {"p_above_threshold": round(p, 4), "S1_80pct_interval": [round(f["lo80_S1"], 2), round(f["hi80_S1"], 2)]
                         if f.get("lo80_S1") is not None else None, "tau": round(f["tau"], 3)},
            "signal": sig,
            "category": ("HIGH" if p >= 0.5 else "LOW") if validated else None,
            "category_withheld_reason": None if validated else (
                "No HIGH/LOW category is shown: no lead time has been validated against the baselines, so a "
                "category would claim more than the evidence supports."),
            "headline": (f"{f['province']}, {f.get('target_quarter')}: estimated {100 * p:.0f}% chance that the food "
                         f"stress label is above its recent median ({sig.lower()} signal; "
                         f"{f.get('evidence_status', 'EXPERIMENTAL').lower()} estimate)."),
            "missing_inputs": missing,
        })
        reg = f["mu_H"] - f["tau"]
        prov = 2 * f["mu_D"]
        drivers = [
            {"factor": "Regional hunger (SWS Balance Luzon, forecast)", "contribution": round(reg, 3),
             "direction": "raises" if reg > 0 else "lowers",
             "explanation": (f"Expected Balance Luzon hunger {_fmt(f['mu_H'])}% versus the threshold {_fmt(f['tau'])}: "
                             f"{'above' if reg > 0 else 'below'} by {_fmt(abs(reg), 2)} points. Shared by all provinces.")},
            {"factor": "Provincial food-price pressure (2 x relative food inflation, constructed)",
             "contribution": round(prov, 3), "direction": "raises" if prov > 0 else "lowers",
             "explanation": (f"Expected relative food inflation {_fmt(f['mu_D'], 2)} pp "
                             f"({'above' if f['mu_D'] > 0 else 'below'} the CALABARZON average).")},
        ]
        drivers.sort(key=lambda d: -abs(d["contribution"]))
        out["drivers"] = drivers
        out["driver_method"] = ("exact additive decomposition of this forecast's margin (mu_S1 - tau = regional + "
                                "provincial); attribution, not proof of cause")
        prev = f.get("previous_D")
        if prev is not None:
            ch = f["mu_D"] - prev
            out["price_trend"] = ("rising" if ch > 0.5 else "falling" if ch < -0.5 else "little change")
            out["price_trend_detail"] = f"expected D {_fmt(f['mu_D'], 2)} vs last measured {_fmt(prev, 2)} pp"
    # data coverage and freshness
    ns = f.get("news_status")
    news_text = {
        "COMPLETE": "news collection complete and sufficient",
        "COMPLETE_LIMITED_EVIDENCE": "news collected but fewer than 5 usable articles (limited signal)",
        "COMPLETE_NO_USABLE_EVIDENCE": "news collected but no usable article; this is missing evidence, not low risk",
        "PARTIALLY_COVERED": "news collection incomplete for the quarter",
        "NO_USABLE_EVIDENCE_COLLECTION_FAILED": "news collection failed for the quarter",
        "NOT_ATTEMPTED": "news not collected for the quarter",
        "NOT_AUTHORIZED": "news after the authorized period is not used",
    }.get(ns, str(ns))
    out["data_coverage"] = {
        "hunger": f"last SWS round used: {f.get('last_round')} (published by {f.get('last_round_published')})",
        "prices": f"last provincial CPI month used: {f.get('last_cpi_month')}",
        "news": f"{f.get('news_quarter')}: {news_text}",
        "news_articles_in_fssi": f.get("news_articles_in_fssi"),
        "news_in_this_forecast": "not an input of the forecast shown (PCF21 uses SWS and CPI); shown for context",
    }
    insufficient = []
    if p is None:
        insufficient.append("no estimate")
    if ns not in ("COMPLETE",):
        insufficient.append("news evidence " + ("not authorized" if ns == "NOT_AUTHORIZED" else "insufficient"))
    if missing:
        insufficient.append("missing: " + ", ".join(missing))
    out["evidence_sufficiency"] = "SUFFICIENT" if not insufficient else "LIMITED: " + "; ".join(insufficient)
    lim = ["The hunger part is a regional survey value; provincial differences come only from food prices.",
           "No lead time is validated (fewer than 5 LOW outcomes at every lead), so the probability is indicative.",
           "Survey sampling error of the hunger rate (about 1.5-2 points) is comparable to the distance to the "
           "threshold in many quarters."]
    if p is not None and signal(p) == "UNCERTAIN":
        lim.append("The estimate cannot distinguish above from below the threshold.")
    out["limitations"] = lim
    # proportionate interpretation
    if p is None:
        use = ("Use the latest official PSA and SWS releases directly; aiPHeed has no estimate for this quarter until "
               "the missing inputs are released.")
        attention = "NO_ESTIMATE"
    elif not validated:
        # Province-specific pressure needs a meaningful price term: D at least 0.5 pp above the CALABARZON average
        # (2D >= 1.0), or a rising D that is above average. (Fixed before any record was published; the 0.5 pp
        # step is the same one used for the trend wording. A +0.1 pp term is not province-specific pressure.)
        prov_pressure = 2 * f["mu_D"] >= 1.0 or (out.get("price_trend") == "rising" and f["mu_D"] > 0)
        if p >= 0.65 and prov_pressure:
            attention = "REVIEW_RECOMMENDED"
            use = ("Indicative only. Consider prioritising this province for a closer look: check current market "
                   "prices and field reports with the provincial agriculture office and the LGUs. Do not allocate "
                   "resources on this estimate alone.")
        elif p >= 0.65:
            attention = "MONITOR"
            use = ("Indicative only. The regional hunger level drives this estimate; monitor the next SWS and PSA "
                   "releases. No province-specific price pressure is indicated.")
        elif p <= 0.35:
            attention = "ROUTINE"
            use = ("Indicative only. No elevated signal; routine monitoring. A low estimate is not evidence that "
                   "households are food secure.")
        else:
            attention = "UNCERTAIN"
            use = "Indicative only and uncertain; rely on official releases and field information."
    else:
        attention = "VALIDATED_FORECAST"
        use = "Validated forecast; use alongside official assessments."
    out["attention"] = attention
    out["suggested_use"] = use
    out["disclaimer"] = ("aiPHeed provides food-insecurity risk indicators only; it does not replace official "
                         "government assessments, classifications or DA decisions (Chapter I, 1.7).")
    return out
