"""
app/services/report_data_e31.py
-------------------------------
GET /api/v1/report/data for the Visualization page, built from the served E31-family record (the same numbers as the
map, the ranking and the explainability panel). The frontend lays the blocks out (frontend/src/lib/chartReport.ts
renderReportPdf); every number and sentence comes from here.

Layout: the plain-language findings report for DA Region IV-A staff (the same section order as plain_report.py,
which was written for the legacy engine): title, metadata, what the score means, Key Points, Risk at a Glance, How
Risk Changed (trend only), What Is Driving the Risk, Province Profile, News Reports, Important Notes. The wording that
describes the label, the news and the evidence is written here for the served label; the label-neutral sentence
builders of plain_text.py are reused.

Layout contract with chartReport.ts:
  * a table column's `width` is a FRACTION of the text width (chartReport multiplies it by contentW); widths sum to 1.
  * a line chart's `quarters` is the x axis; a quarter without an estimate stays on it with null values and the
    figure note says why. yMin/yMax/yStep set the drawn range (zoomed to the data, on a 0.05 grid).
  * bar charts list the drivers with a non-zero share only (a 0% driver is never shown as raising risk).
ASCII only (jsPDF).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from app.ml.inference import e31_engine as E31
from app.services import plain_text as pt
from app.services import reference as ref
from app.services.dashboard import _ascii, _join_series

REPORT_TITLE = "aiPHeed Food Insecurity Forecast Report"
PREPARED_FOR = "DA Region IV-A"
SUBTITLES = {"trend": "Province Risk Level Trend", "shap": "What Is Driving the Risk"}
MODE_SHORT = {"BACKTEST": "backtest", "RETROSPECTIVE_BLIND": "frozen forecast, scored", "NOWCAST": "nowcast",
              "FORECAST": "forecast"}
PH = timezone(timedelta(hours=8))


# --------------------------------------------------------------------------------------------- served rows
def _qkey(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def _qstr(k: int) -> str:
    return f"{k // 4}-Q{k % 4 + 1}"


def _served_quarters() -> list[str]:
    return sorted({r["quarter"] for r in E31.served_rows()}, key=_qkey)


def _row(quarter: str) -> dict | None:
    return E31.quarter_row(quarter, "nowcast")


def mode_label(r: dict) -> str:
    """The served row's mode in words, with its lead and (for a forecast) its issue date."""
    lead, origin = r.get("lead", 1), str(r.get("origin") or "")[:10]
    if r["mode"] == "FORECAST" and lead >= 2:
        return f"lead-{lead} preview, issued {origin}"
    if r["mode"] == "FORECAST":
        return f"forecast, lead {lead}, issued {origin}"
    return f"{MODE_SHORT.get(r['mode'], r['mode'].lower())}, lead {lead}"


def _gap_reason(quarter: str) -> str:
    from app.services import dashboard as svc

    try:
        return svc._e31_unavailable_reason(quarter, "nowcast")
    except Exception:                                      # noqa: BLE001 - a reason is optional text
        return f"No estimate for {quarter}."


def _gap_sentence(gaps: list[str]) -> str:
    """Quarters sharing one reason, named together."""
    grouped: dict[str, list[str]] = {}
    for q in gaps:
        grouped.setdefault(_gap_reason(q).replace(q, "{Q}"), []).append(q)
    out = []
    for reason, qs in grouped.items():
        if len(qs) > 1:
            reason = reason.replace(": its ", ": their ").replace("so the quarter has", "so these quarters have")
        out.append(reason.replace("{Q}", _join_series([pt.qlabel(x) for x in qs])))
    return " ".join(out)


# --------------------------------------------------------------------------------------------- blocks
def _h(text: str) -> dict:
    return {"kind": "heading", "level": 1, "text": _ascii(text)}


def _p(text: str) -> dict:
    return {"kind": "paragraph", "style": "body", "text": _ascii(text)}


def _bullets(items: list[str]) -> dict:
    return {"kind": "bullets", "items": [_ascii(i) for i in items if i]}


def _table(label: str, title: str, columns: list[tuple[str, str, float]], rows: list[list[str]],
           note: str | None) -> dict:
    return {"kind": "table", "label": label, "title": _ascii(title),
            "columns": [{"label": _ascii(c), "align": a, "width": w} for c, a, w in columns],
            "rows": [[_ascii(str(c)) for c in r] for r in rows], "note": _ascii(note) if note else None}


def _figure(label: str, title: str, chart: dict, note: str | None) -> dict:
    return {"kind": "figure", "label": label, "title": _ascii(title), "chart": chart,
            "note": _ascii(note) if note else None}


def _axis(values: list[float]) -> tuple[float, float, float]:
    """The y-axis zoomed to the data with 0.05 padding, on a 0.05 grid, within 0-1."""
    lo = max(0.0, math.floor((min(values) - 0.05) * 20) / 20)
    hi = min(1.0, math.ceil((max(values) + 0.05) * 20) / 20)
    return round(lo, 2), round(hi, 2), (0.05 if hi - lo <= 0.4 else 0.1)


# --------------------------------------------------------------------------------------------- wording
def _score_explainer(rec: dict) -> str:
    td = rec.get("target_definition") or {}
    if "H + 2D" in (td.get("label") or "") and "trailing median" in (td.get("tau") or ""):
        what = ("It is the estimated chance that the province's hunger-and-food-price score -- regional hunger from "
                "the SWS survey plus twice the gap between the province's food inflation and the five-province "
                "average -- is above its usual level, the median of the past published quarters.")
    else:
        what = f"It is the estimated chance of the HIGH class of the label {td.get('label', 'used by the model')}."
    return ("The risk score ranges from 0 to 1. " + what + " A higher score means this combined pressure is more "
            "likely to be above its usual level. It is not a measure of how many families lack food.")


def _split(attr: dict | None) -> tuple[int, int, int] | None:
    """(hunger survey and last label, news tone and unmatched news, the five factors) in whole percent."""
    from app.services import dashboard as svc

    if not attr:
        return None
    s, n, f = svc._integer_shares([attr["survey"], attr["news_other"] + attr.get("rest", 0.0), attr["five"]])
    return (s, n, f) if s + n + f else None


def _split_sentence(split: tuple[int, int, int] | None, whose: str) -> str:
    if not split:
        return ""
    s, n, f = split
    return (f"Of everything behind {whose}, about {s}% comes from the regional hunger survey and the last published "
            f"result, about {n}% from the tone of the news and news reports that match none of the five factors, "
            f"and about {f}% from the five factors shown in the figure.")


def _lead_note(rec: dict) -> str:
    from app.quarterly.target import max_lead
    from app.quarterly.verdicts import max_reliable_lead

    v = rec.get("validation") or {}
    mr = max_reliable_lead(v)
    me = {r.get("key"): r for r in (v.get("model_evaluation") or {}).get("rows", [])}
    nq = {r.get("key"): r for r in (v.get("next_quarter_evaluation") or {}).get("rows", [])}
    acc1 = (me.get("E36-LGBM") or {}).get("accuracy_lead1")
    acc2 = next((nq[k]["accuracy"] for k in ("E55", "E38-LGBM") if k in nq), None)
    if mr["lead"] != 1 or acc1 is None:
        return "No forecast horizon has been shown to be reliable; treat every value as indicative."
    out = (f"By the study's rule (at least 75% correct on past quarters), results one quarter ahead are the reliable "
           f"horizon: {acc1:.0%} were correct on development data.")
    from app.quarterly.verdicts import verdict_from_record

    ver = verdict_from_record(v) or {}
    ci = (me.get("E36-LGBM") or {}).get("accuracy_ci95")
    if ci and ver.get("demonstrated") is False:          # the point estimate passes; the interval does not
        out += (f" The 95% interval ({ci[0]:.3f} to {ci[1]:.3f}) reaches below 75%, so the target is not "
                f"demonstrated with confidence.")
    if acc2 is not None:
        out += (f" Results two quarters ahead were correct {acc2:.0%} of the time, "
                + ("so the two-quarter-ahead value shown here is an experimental preview."
                   if max_lead() >= 2 else "so they are not shown."))
    return out


# --------------------------------------------------------------------------------------------- data
def _province_rows(quarters: list[str], slugs: list[str]):
    from app.services import dashboard as svc

    summ = {q: {p["id"]: p for p in svc.province_summary(q)} for q in quarters}

    def value(s, q):
        p = summ.get(q, {}).get(s)
        return None if p is None else p["riskScore"]

    return summ, value


def _explain(code: str | None, q: str) -> dict | None:
    from app.services import dashboard as svc

    try:
        e = svc.explainability_region(q) if code is None else svc.explainability(code, q)
    except Exception:                                      # noqa: BLE001
        return None
    e = dict(e)
    # all five, as the dashboard shows them; none when no driver has any share (e.g. 2023-Q1): no breakdown to report
    e["shown"] = list(e["triggers"]) if any(t["pct"] > 0 for t in e["triggers"]) else []
    return e


def _calibration_note() -> str:
    """A calibrated record (E49, E53): the dashboard note's before-calibration sentence, for the driver figures."""
    try:
        from app.api.v1.insights import CALIBRATION_SENTENCE
        from app.quarterly import self_description as SD

        return " " + CALIBRATION_SENTENCE if SD.is_calibrated(SD.active_record_key()) else ""
    except Exception:                                      # noqa: BLE001 - a legacy engine has no record key
        return ""


def _bars(triggers: list[dict]) -> dict:
    # The renderer (frontend chartReport.ts) labels a bar "N%, raises/lowers risk", so a 0% driver would read as
    # raising or lowering risk; the figure lists the drivers with an effect, and the text and tables name the rest.
    return {"type": "bars", "bars": [{"label": pt.factor(t["key"], t.get("label")), "pct": t["pct"],
                                      "direction": t["direction"]} for t in triggers if t["pct"] > 0]}


def _news_topics(code: str | None, q: str) -> tuple[int, dict[str, int]]:
    from app.ml.nlp.trigger_classifier import classify_triggers
    from app.services import dashboard as svc

    arts = svc._e31_quarter_articles(code, q)
    counts: dict[str, int] = {}
    for a in arts:
        for g in classify_triggers(a.get("title") or ""):
            if g in pt.PLAIN_FACTORS:
                counts[g] = counts.get(g, 0) + 1
    return len(arts), counts


def _quarter_running(q: str) -> bool:
    from app.quarterly.target import forecast_target

    return _qkey(q) >= _qkey(forecast_target()["calendar_quarter"])


# --------------------------------------------------------------------------------------------- report
def _build(kind: str, scope: str, pid: str | None, window: list[str]) -> dict:
    from app.services import dashboard as svc

    rec = E31.record()
    if scope == "province":
        slug = (pid or "").lower()
        if slug not in ref.PROVINCES:
            raise KeyError(f"unknown province '{pid}'")
        slugs = [slug]
    else:
        slugs = list(ref.PROVINCES)
    names = {s: ref.PROVINCES[s]["name"] for s in slugs}
    codes = {s: ref.province_code(s) for s in slugs}
    single = len(slugs) == 1
    high, alert = ref.RISK_DISPLAY_CUTOFF, ref.ALERT_THRESHOLD

    rows_by_q = {q: r for q in window if (r := _row(q)) is not None}
    estimated = [q for q in window if q in rows_by_q]
    if not estimated:
        raise KeyError("no estimate in the requested range")
    gaps = [q for q in window if q not in rows_by_q]
    last_q = estimated[-1]
    served = _served_quarters()
    prev_q = next((q for q in reversed(served) if _qkey(q) < _qkey(last_q) and _row(q)), None)
    first_q = estimated[0]
    multi = kind == "trend" and len(estimated) > 1
    compare_from = first_q if multi else prev_q

    summ, value = _province_rows(sorted(set(estimated) | ({prev_q} if prev_q else set()), key=_qkey), slugs)
    expl = {s: _explain(codes[s], last_q) for s in slugs}
    prev_expl = {s: (_explain(codes[s], prev_q) if prev_q else None) for s in slugs}
    rows = []
    for s in slugs:
        e = expl[s]
        main = e["shown"][0] if e and e["shown"] else None
        rows.append({"id": s, "name": names[s], "withheld": False, "value": value(s, last_q),
                     "start": value(s, compare_from) if compare_from else None, "prev": value(s, prev_q),
                     "mainKey": main["key"] if main else None, "mainPct": main["pct"] if main else None,
                     "mainDirection": main["direction"] if main else None, "triggers": e["shown"] if e else None})

    tables = figures = 0
    blocks: list[dict] = [_p(_score_explainer(rec) + " " + pt.level_scale(high, alert))]

    # ---- Key points
    blocks.append(_h("Key Points"))
    kp = pt.compose_key_points(rows, last_q, compare_from, high, alert)
    if not single:
        reg = svc.region_forecast(last_q)
        kp.insert(1, f"The CALABARZON index, the mean of the five provinces, is {pt.score(reg['riskScore'])} "
                     f"({pt.risk_level(reg['riskScore'], high, alert)}).")
    row_last = rows_by_q[last_q]
    if row_last["mode"] == "FORECAST":
        kp.append(f"The {pt.qlabel(last_q)} value is a {'two-quarter-ahead experimental preview' if row_last.get('lead', 1) >= 2 else 'forecast'} "
                  f"issued {str(row_last.get('origin'))[:10]}; its outcome is not yet known.")
    blocks.append(_bullets(kp))

    # ---- Risk at a glance
    blocks.append(_h("Risk at a Glance"))
    tables += 1
    t1 = f"Table {tables}"
    blocks.append(_p(pt.compose_glance_lead(rows, last_q, t1, high, alert)))
    glance = []
    for r in sorted(rows, key=lambda r: (r["value"] is None, -(r["value"] or 0))):
        if r["value"] is None:
            glance.append([r["name"], "Not available", "Not available", "Not available", "Not available"])
            continue
        glance.append([r["name"], pt.score(r["value"]), pt.risk_level(r["value"], high, alert),
                       pt.change_cell(r["prev"], r["value"]),
                       f"{pt.factor(r['mainKey'])} ({r['mainPct']}%)" if r["mainKey"] else "Not available"])
    if not single:
        reg_now = svc.region_forecast(last_q)["riskScore"]
        reg_prev = svc.region_forecast(prev_q)["riskScore"] if prev_q else None
        rx = _explain(None, last_q)
        rmain = rx["shown"][0] if rx and rx["shown"] else None
        glance.append(["CALABARZON (mean)", pt.score(reg_now), pt.risk_level(reg_now, high, alert),
                       pt.change_cell(reg_prev, reg_now),
                       f"{pt.factor(rmain['key'])} ({rmain['pct']}%)" if rmain else "Not available"])
    change_head = f"Change from {pt.qlabel(prev_q)}" if prev_q else "Change from previous quarter"
    blocks.append(_table(
        t1, (f"Risk Score and Risk Level for {names[slugs[0]]}, {pt.qlabel(last_q)}" if single
             else f"Risk Scores and Risk Levels by Province, {pt.qlabel(last_q)}"),
        [("Province", "center", 0.20), ("Risk score", "center", 0.15), ("Risk level", "center", 0.17),
         (change_head, "center", 0.22), ("Main factor", "center", 0.26)], glance,
        f"Risk levels: {pt.LEVEL_ALERT} is {alert:.2f} and above, {pt.LEVEL_HIGH} is {high:.2f} to below {alert:.2f}, "
        f"and {pt.LEVEL_NONE} is below {high:.2f}. The main factor is the largest of the five factors behind each "
        f"score. {pt.qlabel(last_q)}: {mode_label(row_last)}."))

    # ---- How risk changed (trend with more than one estimated quarter)
    if multi:
        blocks.append(_h("How Risk Changed"))
        figures += 1
        f1 = f"Figure {figures}"
        series = [{"name": names[s], "points": [{"quarter": q, "value": value(s, q) if q in rows_by_q else None}
                                                for q in window]} for s in slugs]
        blocks.append(_p(pt.compose_trend_paragraph(series, first_q, last_q, f1)))
        vals = [p["value"] for s in series for p in s["points"] if p["value"] is not None]
        y_min, y_max, step = _axis(vals)
        lines = [{"value": v, "label": lab} for v, lab in ((alert, f"Alert level ({alert:.2f})"),
                                                            (high, f"High level ({high:.2f})")) if y_min <= v <= y_max]
        note = []
        if (y_min, y_max) != (0.0, 1.0):
            note.append(f"The scale runs from {y_min:.2f} to {y_max:.2f} instead of 0 to 1, so that changes are easier "
                        f"to see.")
        inside = [f"the {lab} level ({v:.2f})" for v, lab in ((alert, "Alert"), (high, "High")) if y_min <= v <= y_max]
        outside = [(v, lab) for v, lab in ((alert, "Alert"), (high, "High")) if not y_min <= v <= y_max]
        if inside:
            note.append(f"Dashed {'lines mark' if len(inside) > 1 else 'line marks'} {_join_series(inside)}.")
        for v, lab in outside:
            note.append(f"The {lab} level ({v:.2f}) is {'below' if v < y_min else 'above'} the range shown.")
        back = [q for q in estimated if rows_by_q[q]["mode"] in ("BACKTEST", "RETROSPECTIVE_BLIND")]
        if back:
            note.append(f"{pt.qlabel(back[0])} to {pt.qlabel(back[-1])} are backtests on past quarters.")
        for q in estimated:
            if rows_by_q[q]["mode"] == "FORECAST":
                note.append(f"{pt.qlabel(q)} is a {mode_label(rows_by_q[q])}.")
        if gaps:
            note.append("A gap in a line marks a quarter without a result. " + _gap_sentence(gaps))
        blocks.append(_figure(
            f1, f"Risk Scores for {'All Provinces' if not single else names[slugs[0]]}, {pt.qlabel(first_q)} to "
                f"{pt.qlabel(last_q)}",
            {"type": "line", "quarters": [pt.qlabel(q) for q in window],
             "series": [{"name": _ascii(s["name"]), "values": [p["value"] for p in s["points"]]} for s in series],
             "yMin": y_min, "yMax": y_max, "yStep": step, "lines": lines},
            " ".join(note)))

    # ---- What is driving the risk
    blocks.append(_h("What Is Driving the Risk"))
    figures += 1
    fN = f"Figure {figures}"
    if single:
        r, e = rows[0], expl[slugs[0]]
        if not e or not e["shown"]:
            blocks.append(_p(f"No breakdown of the factors is available for {r['name']} in {pt.qlabel(last_q)}."))
        else:
            pe = prev_expl[slugs[0]]
            blocks.append(_p(pt.compose_factors_province(r["name"], last_q, e["shown"], pe["shown"] if pe else None,
                                                          prev_q, figure_label=fN)
                             + " " + _split_sentence(_split(e.get("attribution")), f"{r['name']}'s score")))
            blocks.append(_figure(fN, f"Factors Behind the Risk Score in {r['name']}, {pt.qlabel(last_q)}",
                                  _bars(e["shown"]),
                                  "Each bar shows a factor's share of the five factors behind the risk score; factors "
                                  "with no noticeable effect are not shown. Red bars raise the risk and green bars "
                                  "lower it. These are the model's associations, not causes." + _calibration_note()))
    else:
        rx = _explain(None, last_q)
        if rx and rx["shown"]:
            tables += 1
            lead = (f"{fN} combines the factors behind the five provinces' risk scores in {pt.qlabel(last_q)}, and "
                    f"Table {tables} shows them province by province. ")
            blocks.append(_p(lead + " ".join(pt.compose_factors_region(
                [{"name": r["name"], "triggers": r["triggers"], "withheld": False} for r in rows], last_q))
                + " " + _split_sentence(_split(rx.get("attribution")), "the CALABARZON index")))
            blocks.append(_figure(fN, f"Factors Behind the Risk Across the Provinces, {pt.qlabel(last_q)}",
                                  _bars(rx["shown"]),
                                  "Shares are combined across the five provinces on the scale of the regional index. "
                                  "Red bars raise the risk and green bars lower it; factors with no noticeable effect "
                                  "are not shown." + _calibration_note()))
            keys = [t["key"] for t in rx["shown"]]
            cells = []
            for r in rows:
                by = {t["key"]: t for t in (r["triggers"] or [])}
                cells.append([r["name"]] + [(f"{by[k]['pct']}% {'raises' if by[k]['direction'] == 'increases_risk' else 'lowers'}"
                                             if k in by and by[k]["pct"] > 0 else "No noticeable effect") for k in keys])
            width = round(0.80 / len(keys), 4)
            blocks.append(_table(f"Table {tables}", f"Share of Each Factor by Province, {pt.qlabel(last_q)}",
                                 [("Province", "center", 0.20)] + [(pt.factor(k), "center", width) for k in keys],
                                 cells, "Each row adds up to about 100% of the five factors. 'Raises' and 'lowers' "
                                        "show whether the factor pushes the province's risk score up or down."))
        else:
            figures -= 1
            blocks.append(_p(f"No breakdown of the factors is available for {pt.qlabel(last_q)}."))

    # ---- Driver report: the model's inputs behind the score
    if kind == "shap":
        v = rows_by_q[last_q]["provinces"][codes[slugs[0]]]
        ds = sorted(v.get("drivers") or [], key=lambda d: -abs(d.get("contribution") or 0))[:10]
        if ds:
            tables += 1
            blocks.append(_p(f"Table {tables} lists the {len(ds)} model inputs with the largest effect on the score."))
            blocks.append(_table(
                f"Table {tables}", f"Model Inputs Behind the Score in {names[slugs[0]]}, {pt.qlabel(last_q)}",
                [("Input", "left", 0.55), ("Value", "center", 0.15), ("Effect", "center", 0.30)],
                [[d["factor"], (f"{d['value']:.2f}" if isinstance(d.get("value"), (int, float)) else "Not available"),
                  ("Raises" if (d.get("contribution") or 0) > 0 else "Lowers")
                  + f" ({abs(d.get('contribution') or 0):.2f})"] for d in ds],
                "Effect is the input's contribution in the model's own units (log-odds, before calibration). "
                "These are associations the model learned, not causes."))

    # ---- Province profile
    blocks.append(_h("Province Profile"))
    tables += 1
    prof = [{"name": names[s], "population": (summ[last_q].get(s) or {}).get("population"),
             "poverty": (summ[last_q].get(s) or {}).get("povertyRate")} for s in slugs]
    basis = (summ[last_q].get(slugs[0]) or {}).get("povertyRateBasis") or ""
    blocks.append(_p(pt.compose_profile_lead(prof, f"Table {tables}")))
    blocks.append(_table(
        f"Table {tables}", (f"Population and Poverty Incidence of {names[slugs[0]]}" if single
                            else "Population and Poverty Incidence by Province"),
        [("Province", "center", 0.34), ("Population", "center", 0.33), ("Poverty incidence", "center", 0.33)],
        [[p["name"], f"{p['population']:,}" if p["population"] is not None else "Not available",
          f"{p['poverty']:.1f}%" if p["poverty"] is not None else "Not available"] for p in prof],
        "Population is the total of the province's cities and municipalities in the PSA 2024 Census of Population "
        "(POPCEN). Poverty incidence is the share of people below the poverty line: " + basis))

    # ---- News reports
    blocks.append(_h("News Reports"))
    news_lines = []
    total, topic_counts = 0, {}
    for s in slugs:
        n, tc = _news_topics(codes[s], last_q)
        total += n
        for k, c in tc.items():
            topic_counts[k] = topic_counts.get(k, 0) + c
    where = names[slugs[0]] if single else "the five provinces"
    news_lines.append(f"{pt.count_lead(total, 'validated news report')} about food conditions in {where} "
                      f"{'was' if total == 1 else 'were'} published in {pt.qlabel(last_q)}.")
    if topic_counts:
        ranked = sorted(topic_counts.items(), key=lambda kv: -kv[1])
        news_lines.append(("It was about " if total == 1 else "By topic, they were about ") + _join_series(
            [pt.lower_first(pt.factor(k)) + (f" ({c} {'report' if c == 1 else 'reports'})" if total > 1 else "")
             for k, c in ranked[:3]]) + ".")
    elif total:
        news_lines.append("None of them matched one of the five factors.")
    split = _split(((expl[slugs[0]] if single else _explain(None, last_q)) or {}).get("attribution"))
    if split:
        news_lines.append(f"The tone of the news and news reports that match none of the five factors account for "
                          f"about {split[1]}% of everything behind the score; news matched to a factor is counted "
                          f"within that factor.")
    if _quarter_running(last_q):
        ev = ((row_last.get("provenance") or {}).get("news_evidence_window") or {}).get("evidence_quarter")
        built = ""
        if ev and ev != last_q:
            n_ev = sum(_news_topics(codes[s], ev)[0] for s in slugs)
            built = (f" The {pt.qlabel(last_q)} forecast was built from the news of {pt.qlabel(ev)}: "
                     f"{pt.count_lead(n_ev, 'validated news report').lower()}.")
        state = ("the quarter has not started yet" if svc._quarter_not_started(last_q)
                 else "the quarter is still running and reports are still being collected")
        news_lines.append(f"The news for {pt.qlabel(last_q)} is not complete: {state}." + built)
    for line in news_lines:
        blocks.append(_p(line))

    # ---- Important notes
    blocks.append(_h("Important Notes"))
    notes = ["The risk score is the estimated chance that the combined hunger-and-food-price score is above its usual "
             "level. It is not a measure of hunger or of how many families lack food.",
             _lead_note(rec)]
    back_all = [q for q in estimated if rows_by_q[q]["mode"] in ("BACKTEST", "RETROSPECTIVE_BLIND")]
    if back_all:
        notes.append(f"Results for {pt.qlabel(back_all[0])} to {pt.qlabel(back_all[-1])} are backtests: each was "
                     f"estimated with only the data available before that quarter, but these quarters were also "
                     f"used while the model was being developed.")
    if gaps:
        notes.append(_gap_sentence(gaps))
    notes += ["City and municipal figures follow their province's score. They are not separate estimates for each "
              "city or municipality.",
              "This is not an official food insecurity classification. The report presents findings only; it does "
              "not recommend actions and should be used alongside DA Region IV-A's own guidance."]
    blocks.append(_bullets(notes))

    generated = datetime.now(PH)
    area = ("All provinces (" + ", ".join(names[s] for s in slugs) + ")") if not single else names[slugs[0]]
    period = pt.qlabel(last_q) if not multi else f"{pt.qlabel(first_q)} to {pt.qlabel(last_q)}"
    return {
        "type": kind, "scope": scope, "title": REPORT_TITLE, "subtitle": SUBTITLES[kind],
        "generatedDate": _ascii(f"{generated.day} {generated:%B %Y}"),
        "metadata": [["Area", _ascii(area)], ["Period", period],
                     ["Date prepared", _ascii(f"{generated.day} {generated:%B %Y}")],
                     ["Prepared for", PREPARED_FOR],
                     ["Data", _ascii(f"{pt.qlabel(last_q)} {mode_label(row_last)}")],
                     *_model_metadata(rec, row_last)],
        "blocks": blocks,
    }


def _model_metadata(rec: dict, row_last: dict) -> list:
    """The served model's name and its development accuracy, composed from the record (E53 port: the Visualization
    PDFs state the model and its accuracy as the backend PDF does). A period ending on the lead-2 preview quarter also
    carries that quarter's own model and accuracy note."""
    from app.quarterly import preview as PV
    from app.quarterly import self_description as SD
    from app.quarterly.verdicts import TARGET, verdict_from_record

    name = SD.served_engine(rec, SD.active_record_key()).get("name", "the served model")
    rows = {r.get("key"): r for r in ((rec.get("validation") or {}).get("model_evaluation") or {}).get("rows", [])}
    m, v = rows.get("E36-LGBM"), verdict_from_record(rec.get("validation") or {})
    out = []
    if m and v:
        lo, hi = m["accuracy_ci95"]
        acc = m["accuracy_lead1"]
        verdict = ("demonstrated" if v["demonstrated"] else
                   "met by the point estimate but not demonstrated" if acc >= TARGET else "not met")
        out.append(["Model", _ascii(f"{name}. One quarter ahead: development accuracy {acc:.3f} ({m['correct']}/{m['n']}, "
                                    f"95% interval {lo:.3f} to {hi:.3f}); the 75% target is {verdict}. ROC-AUC "
                                    f"{m['roc_auc']:.3f}, F1 {m['f1']:.3f}.")])
    else:
        out.append(["Model", _ascii(name)])
    if row_last.get("lead", 1) >= 2 and PV.preview_row(row_last["quarter"]) is not None:
        lead2 = row_last.get("model_name") or (rec.get("next_quarter_model") or {}).get("name") or "lead-2 model"
        out.append([f"{pt.qlabel(row_last['quarter'])} model", _ascii(f"{lead2}. {PV.compose_note(rec)[0]}")])
    return out


def _window(q_from: str | None, q_to: str | None) -> list[str]:
    from app.quarterly.target import lead2_preview

    served = _served_quarters()
    lo = max(_qkey(served[0]), _qkey(q_from)) if q_from else _qkey(served[0])
    hi = min(_qkey(served[-1]), _qkey(q_to)) if q_to else _qkey(served[-1])
    if lead2_preview() and not q_to:               # the default report ends on the lead-1 quarter, not the preview
        lead1 = [q for q in E31.served_rows() if q.get("lead", 1) == 1]
        hi = min(hi, max(_qkey(q["quarter"]) for q in lead1))
    return [_qstr(k) for k in range(lo, hi + 1)]


def trend(scope: str, pid: str | None, q_from: str | None, q_to: str | None) -> dict:
    return _build("trend", scope, pid, _window(q_from, q_to))


def drivers(pid: str, quarter: str) -> dict:
    if _row(quarter) is None:
        raise KeyError(f"no estimate for {pid} in {quarter}")
    return _build("shap", "province", pid, [quarter])
