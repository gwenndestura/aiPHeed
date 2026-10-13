"""
app/services/plain_report.py
-----------------------------
The plain-language PDF report behind both Visualization tabs, written for
DA Region IV-A staff.

Same data as report_data.py (province_summary, explainability,
explainability_region, news, the quarter timeline) and the same withheld
rule, but laid out as a short findings report: key points, a risk table, the
trend, the main factors, a province profile, news and short notes. The
technical sections (model reliability, method appendix, data-vintage detail)
are not included. Prose comes from plain_text.py.

Tables and figures follow APA 7: each block carries its label ("Table 1"), an
italic Title Case title and an optional note; the frontend draws them that way.
"""

from __future__ import annotations

import functools
from datetime import datetime

from app.ml.inference.thesis_explainer import ThesisExplainer
from app.ml.nlp.trigger_classifier import classify_triggers
from app.services import dashboard as svc
from app.services import plain_text as pt
from app.services import reference as ref
from app.services.dashboard import _ascii
from app.services.report_data import PST, ReportRequestError, _axis, _calendar, _quarter_window

REPORT_TITLE = "aiPHeed Food Insecurity Forecast Report"
PREPARED_FOR = "DA Region IV-A"
SUBTITLES = {"trend": "Province Risk Level Trend", "shap": "Factors Behind the Risk"}


def _h(text: str) -> dict:
    return {"kind": "heading", "level": 1, "text": _ascii(text)}


def _p(text: str) -> dict:
    return {"kind": "paragraph", "style": "body", "text": _ascii(text)}


def _table(label: str, title: str, columns: list[tuple[str, str, float]],
           rows: list[list[str]], note: str | None = None) -> dict:
    return {
        "kind": "table", "label": label, "title": _ascii(title),
        "columns": [{"label": _ascii(c), "align": a, "width": w} for c, a, w in columns],
        "rows": [[_ascii(str(c)) for c in r] for r in rows],
        "note": _ascii(note) if note else None,
    }


@functools.lru_cache(maxsize=256)
def _news_share(province_code: str, quarter: str) -> int | None:
    """
    Whole-number percent of the score's explained factors that come from
    news-based inputs (the sentiment index and the news trigger shares), read
    from the same per-input breakdown the factor chart is built from.
    """
    try:
        records = ThesisExplainer().explain_province_quarter(province_code, quarter)
    except Exception:
        return None
    total = sum(abs(r["shap_value"]) for r in records)
    if not total:
        return None
    news = sum(abs(r["shap_value"]) for r in records
               if r["feature_name"].startswith(("FSSI", "trigger_")))
    return round(news / total * 100)


def _figure(label: str, title: str, chart: dict, note: str | None = None) -> dict:
    return {"kind": "figure", "label": label, "title": _ascii(title), "chart": chart,
            "note": _ascii(note) if note else None}


def _factor_cell(t: dict | None, news_incomplete: bool = False) -> str:
    if t is None:
        return "--"
    if not t["pct"] and news_incomplete and t["key"] in pt.NEWS_ONLY_FACTORS:
        return "Not yet measured"
    if not t["pct"]:
        return "0%"
    return f"{t['pct']}% {'raises' if t['direction'] == 'increases_risk' else 'lowers'}"


def build_plain_report(kind: str, scope: str, province_id: str | None,
                       start: str, end: str, rejected: set[tuple[str, str]],
                       municipality_id: str | None = None) -> dict:
    if kind not in SUBTITLES:
        raise ReportRequestError("type must be 'trend' or 'shap'.")
    if scope == "region":
        slugs = list(ref.PROVINCES)
    elif scope == "province":
        slug = (province_id or "").lower()
        if slug not in ref.PROVINCES:
            raise svc.SubjectNotFound(f"Unknown province id '{province_id}'.")
        slugs = [slug]
    else:
        raise ReportRequestError("scope must be 'region' or 'province'.")
    if kind == "shap" and scope != "province":
        raise ReportRequestError("The factors report covers one province.")

    window = _quarter_window(start, end) if kind == "trend" else [svc.resolve_quarter(end)]
    if not window:
        raise svc.QuarterNotAvailable("No scorable quarter lies in the requested range.")
    first_q, last_q = window[0], window[-1]
    prev_q = svc._previous_quarter(last_q)
    multi_quarter = len(window) > 1

    quarters = sorted(set(window) | ({prev_q} if prev_q else set()), key=ref.quarter_index)
    held_at = {q: frozenset(pid for pid, rq in rejected if rq == q) for q in quarters}
    summaries = {q: {p["id"]: p for p in svc.province_summary(q, held_at[q])} for q in quarters}
    names = {s: ref.PROVINCES[s]["name"] for s in slugs}
    codes = {s: ref.province_code(s) for s in slugs}
    high, alert = ref.RISK_DISPLAY_CUTOFF, ref.ALERT_THRESHOLD
    calendar, lag, latest_available = _calendar()
    single = len(slugs) == 1

    def value(s: str, q: str | None) -> float | None:
        if q is None or s in held_at.get(q, frozenset()):
            return None
        row = summaries.get(q, {}).get(s)
        return None if row is None else row["riskScore"]

    def explain(s: str, q: str | None) -> dict | None:
        if q is None or s in held_at.get(q, frozenset()):
            return None
        try:
            return svc.explainability(codes[s], q)
        except Exception:
            return None

    latest_explain = {s: explain(s, last_q) for s in slugs}
    compare_from = first_q if multi_quarter else prev_q

    rows = []
    for s in slugs:
        e = latest_explain[s]
        main = e["triggers"][0] if e and e["triggers"] else None
        rows.append({
            "id": s, "name": names[s], "withheld": s in held_at[last_q],
            "value": value(s, last_q), "start": value(s, compare_from),
            "prev": value(s, prev_q),
            "mainKey": main["key"] if main else None, "mainPct": main["pct"] if main else None,
            "mainDirection": main["direction"] if main else None, "triggers": e["triggers"] if e else None,
            "incomplete": bool((summaries[last_q].get(s) or {}).get("limitedSignal")),
        })

    municipal = None
    if municipality_id and single:
        mrow = ref.municipality_row(municipality_id)
        if mrow is None or mrow["provinceId"] != slugs[0]:
            raise svc.SubjectNotFound(f"Unknown municipality id '{municipality_id}'.")

        def mvalue(q: str | None) -> float | None:
            if q is None or slugs[0] in held_at.get(q, frozenset()):
                return None
            hit = [m for m in svc.municipality_summary(q, slugs[0]) if m["id"] == municipality_id.lower()]
            return hit[0]["riskIndex"] if hit else None

        municipal = {"name": f"{mrow['lgu_name']} (follows {names[slugs[0]]})",
                     "short": str(mrow["lgu_name"]),
                     "points": [{"quarter": q, "value": mvalue(q)} for q in window],
                     "value": mvalue(last_q), "prev": mvalue(prev_q)}

    tables = figures = 0
    blocks: list[dict] = []
    blocks.append(_p(pt.SCORE_EXPLAINER + " " + pt.level_scale(high, alert)))

    # ---- Key points
    blocks.append(_h("Key Points"))
    blocks.append({"kind": "bullets",
                   "items": pt.compose_key_points(rows, last_q, compare_from, high, alert)})

    # ---- Risk at a glance
    blocks.append(_h("Risk at a Glance"))
    tables += 1
    t1 = f"Table {tables}"
    blocks.append(_p(pt.compose_glance_lead(rows, last_q, t1, high, alert)))
    ordered = sorted(rows, key=lambda r: (r["withheld"] or r["value"] is None,
                                          -(r["value"] or 0)))
    glance = []
    for r in ordered:
        if r["withheld"]:
            glance.append([r["name"], "Withheld", "Withheld", "--", "--"])
            continue
        if r["value"] is None:
            glance.append([r["name"], "Not available", "--", "--", "--"])
            continue
        glance.append([
            r["name"], pt.score(r["value"]), pt.risk_level(r["value"], high, alert),
            pt.change_cell(r["prev"], r["value"]),
            f"{pt.factor(r['mainKey'])} ({r['mainPct']}%)" if r["mainKey"] else "Not available",
        ])
    if municipal and municipal["value"] is not None:
        glance.append([municipal["name"], pt.score(municipal["value"]),
                       pt.risk_level(municipal["value"], high, alert),
                       pt.change_cell(municipal["prev"], municipal["value"]),
                       f"Same as {names[slugs[0]]}"])
    change_head = f"Change from {pt.qlabel(prev_q)}" if prev_q else "Change from previous quarter"
    note = (f"Risk levels: {pt.LEVEL_ALERT} is {alert:.2f} and above, {pt.LEVEL_HIGH} is "
            f"{high:.2f} to below {alert:.2f}, and {pt.LEVEL_NONE} is below {high:.2f}. "
            f"The main factor is the largest of the factors behind each score.")
    if any(r["withheld"] for r in rows):
        note += " Withheld results are not shown."
    blocks.append(_table(
        t1, (f"Risk Score and Risk Level for {names[slugs[0]]}, {pt.qlabel(last_q)}" if single
             else f"Risk Scores and Risk Levels by Province, {pt.qlabel(last_q)}"),
        [("Province", "center", 0.20), ("Risk score", "center", 0.16), ("Risk level", "center", 0.16),
         (change_head, "center", 0.24), ("Main factor", "center", 0.24)],
        glance, note))

    # ---- How risk changed (only when the period has more than one quarter)
    if multi_quarter:
        blocks.append(_h("How Risk Changed"))
        figures += 1
        f1 = f"Figure {figures}"
        series = [{"name": names[s], "points": [{"quarter": q, "value": value(s, q)} for q in window]}
                  for s in slugs]
        if municipal:
            series.append({"name": municipal["name"], "points": municipal["points"]})
        blocks.append(_p(pt.compose_trend_paragraph(series, first_q, last_q, f1)))
        vals = [p["value"] for s in series for p in s["points"] if p["value"] is not None]
        if vals:
            y_min, y_max, step = _axis(vals)
            lines = [{"value": v, "label": lab} for v, lab in
                     ((alert, f"Alert level ({alert:.2f})"), (high, f"High level ({high:.2f})"))
                     if y_min <= v <= y_max]
            note = (f"The scale runs from {y_min:.2f} to {y_max:.2f} instead of 0 to 1, so that "
                    f"changes are easier to see.")
            shown_lines = [f"the {lab} level ({v:.2f})" for v, lab in ((alert, "Alert"), (high, "High"))
                           if y_min <= v <= y_max]
            outside = [f"the {lab} level ({v:.2f})" for v, lab in ((alert, "Alert"), (high, "High"))
                       if not y_min <= v <= y_max]
            if shown_lines:
                note += (f" Dashed {'lines mark' if len(shown_lines) > 1 else 'line marks'} "
                         f"{svc._join_series(shown_lines)}.")
            if outside:
                text = svc._join_series(outside)
                note += (f" {text[0].upper()}{text[1:]} {'is' if len(outside) == 1 else 'are'} "
                         f"below the range shown.")
            if any(p["value"] is None for s in series for p in s["points"]):
                note += " A gap in a line marks a quarter whose result is withheld or not available."
            subject = "All Provinces" if scope == "region" else names[slugs[0]]
            blocks.append(_figure(
                f1, f"Risk Scores for {subject}, {pt.qlabel(first_q)} to {pt.qlabel(last_q)}",
                {"type": "line", "quarters": [pt.qlabel(q) for q in window],
                 "series": [{"name": _ascii(s["name"]), "values": [p["value"] for p in s["points"]]}
                            for s in series],
                 "yMin": y_min, "yMax": y_max, "yStep": step, "lines": lines},
                note))

    # ---- What is driving the risk
    blocks.append(_h("What Is Driving the Risk"))
    figures += 1
    fN = f"Figure {figures}"
    if single:
        r = rows[0]
        if r["withheld"]:
            blocks.append(_p(pt.withheld_sentence([r["name"]], last_q)))
            figures -= 1
        elif not r["triggers"]:
            blocks.append(_p(f"No breakdown of the factors is available for {r['name']} in "
                             f"{pt.qlabel(last_q)}."))
            figures -= 1
        else:
            prev_e = explain(slugs[0], prev_q)
            blocks.append(_p(pt.compose_factors_province(
                r["name"], last_q, r["triggers"], prev_e["triggers"] if prev_e else None,
                prev_q, figure_label=fN, news_incomplete=r["incomplete"])))
            blocks.append(_figure(
                fN, f"Factors Behind the Risk Score in {r['name']}, {pt.qlabel(last_q)}",
                _bars(r["triggers"], r["incomplete"]),
                "Each bar shows a factor's share of all the factors behind the risk score. "
                "Red bars raise the risk and green bars lower it."
                + (" Factors marked 'not yet measured' come only from news reports, which are not "
                   "yet complete for this quarter." if r["incomplete"] else "")))
    else:
        region = svc.explainability_region(last_q, held_at[last_q])
        if region["triggers"]:
            included = region["provincesIncluded"]
            some_held = any(r["withheld"] for r in rows)
            who = ("the one province with results" if included == 1
                   else f"the {pt.num(included)} provinces" + (" with results" if some_held else ""))
            lead = (f"{fN} combines the factors behind the risk scores of "
                    f"{who} in {pt.qlabel(last_q)}, and "
                    f"Table {tables + 1} shows them province by province. ")
            all_incomplete = all(r["incomplete"] for r in rows if not r["withheld"])
            blocks.append(_p(lead + " ".join(pt.compose_factors_region(
                [{"name": r["name"], "triggers": r["triggers"], "withheld": r["withheld"]} for r in rows],
                last_q, news_incomplete=all_incomplete))))
            blocks.append(_figure(
                fN, f"Factors Behind the Risk Across the Provinces, {pt.qlabel(last_q)}",
                _bars(region["triggers"], all_incomplete),
                f"Shares are combined across {who}. Each "
                f"bar shows a factor's share of all the factors behind the risk scores. Red bars "
                f"raise the risk and green bars lower it."
                + (" Factors marked 'not yet measured' come only from news reports, which are not "
                   "yet complete for this quarter." if all_incomplete else "")))
            tables += 1
            keys = [t["key"] for t in region["triggers"]]
            cells = []
            for r in rows:
                if r["withheld"]:
                    cells.append([r["name"]] + ["Withheld"] + ["--"] * (len(keys) - 1))
                elif not r["triggers"]:
                    cells.append([r["name"]] + ["Not available"] * len(keys))
                else:
                    by = {t["key"]: t for t in r["triggers"]}
                    cells.append([r["name"]] + [_factor_cell(by.get(k), r["incomplete"]) for k in keys])
            width = 0.80 / len(keys)
            blocks.append(_table(
                f"Table {tables}", f"Share of Each Factor by Province, {pt.qlabel(last_q)}",
                [("Province", "center", 0.20)] + [(pt.factor(k), "center", width) for k in keys],
                cells,
                "Each row adds up to 100%. 'Raises' and 'lowers' show whether the factor "
                "pushes the province's risk score up or down."
                + (" 'Not yet measured' marks factors that come only from news reports, which are "
                   "not yet complete for this quarter." if any(r["incomplete"] for r in rows) else "")))
        else:
            figures -= 1
            blocks.append(_p(f"No breakdown of the factors is available for {pt.qlabel(last_q)}."))

    # ---- Province profile
    blocks.append(_h("Province Profile"))
    tables += 1
    profile = []
    for s in slugs:
        row = summaries[last_q].get(s) or {}
        profile.append({"name": names[s], "population": row.get("population"),
                        "poverty": row.get("povertyRate")})
    blocks.append(_p(pt.compose_profile_lead(profile, f"Table {tables}")))
    blocks.append(_table(
        f"Table {tables}", (f"Population and Poverty Incidence of {names[slugs[0]]}" if single
                            else "Population and Poverty Incidence by Province"),
        [("Province", "center", 1 / 3), ("Population", "center", 1 / 3),
         ("Poverty incidence", "center", 1 / 3)],
        [[r["name"],
          f"{r['population']:,}" if r["population"] is not None else "Not available",
          f"{round(r['poverty'])}%" if r["poverty"] is not None else "Not available"] for r in profile],
        "Population is from the PSA 2020 Census of Population and Housing. Poverty incidence is "
        "the share of people living below the poverty line, from PSA 2021 estimates averaged "
        "over each province's cities and municipalities."))

    # ---- News reports
    blocks.append(_h("News Reports"))
    news_rows, articles = [], []
    for r in rows:
        if r["withheld"]:
            news_rows.append({"name": r["name"], "withheld": True, "count": 0,
                              "incomplete": False, "mainKey": None, "matched": 0})
            continue
        s = r["id"]
        news = svc.news(codes[s], last_q, 1, 1000)
        matched = []
        if r["mainKey"]:
            for a in news["data"]:
                if r["mainKey"] in classify_triggers(f"{a['title']} {a['excerpt']}"):
                    matched.append(a)
                if len(matched) == 3:
                    break
        for a in matched:
            articles.append([r["name"], a["title"], a["source"], a["date"] or "--"])
        row = summaries[last_q].get(s) or {}
        news_rows.append({"name": r["name"], "withheld": False, "count": news["articleCount"],
                          "incomplete": bool(row.get("limitedSignal")), "mainKey": r["mainKey"],
                          "matched": len(matched), "newsShare": _news_share(codes[s], last_q)})
    news_label = f"Table {tables + 1}" if articles else None
    for sentence in pt.compose_news(news_rows, last_q, news_label):
        blocks.append(_p(sentence))
    if articles:
        tables += 1
        blocks.append(_table(
            f"Table {tables}", f"News Reports Related to the Main Factor, {pt.qlabel(last_q)}",
            # Headlines wrap over several lines, so that one column stays left-aligned.
            [("Province", "center", 0.14), ("Title", "left", 0.52), ("Source", "center", 0.20),
             ("Date", "center", 0.14)],
            articles,
            "Reports were collected automatically and have not been checked by hand. Treat them "
            "as leads rather than confirmed facts."))

    # ---- Important notes
    blocks.append(_h("Important Notes"))
    any_held = any(r["withheld"] for r in rows) or any(
        s in held_at[q] for s in slugs for q in window)
    blocks.append({"kind": "bullets",
                   "items": pt.compose_notes(latest_available, calendar, lag, any_held)})

    generated = datetime.now(PST)
    area = ("All provinces (" + ", ".join(names[s] for s in slugs) + ")" if scope == "region"
            else names[slugs[0]] + (f" ({municipal['short']})" if municipal else ""))
    period = (pt.qlabel(last_q) if not multi_quarter
              else f"{pt.qlabel(first_q)} to {pt.qlabel(last_q)}")
    return {
        "type": kind,
        "scope": scope,
        "title": REPORT_TITLE,
        "subtitle": SUBTITLES[kind],
        "generatedDate": _ascii(f"{generated.day} {generated:%B %Y}"),
        "metadata": [
            ["Area", _ascii(area)],
            ["Period", period],
            ["Date prepared", _ascii(f"{generated.day} {generated:%B %Y}")],
            ["Prepared for", PREPARED_FOR],
            ["Data", f"Based on the latest available data ({pt.qlabel(latest_available)})."],
        ],
        "blocks": blocks,
    }


def _bars(triggers: list[dict], news_incomplete: bool = False) -> dict:
    return {"type": "bars",
            "bars": [{"label": pt.factor(t["key"], t.get("label")), "pct": t["pct"],
                      "direction": t["direction"],
                      "unmeasured": bool(news_incomplete and not t["pct"]
                                         and t["key"] in pt.NEWS_ONLY_FACTORS)}
                     for t in triggers]}
