"""
The Visualization page's PDF (GET /api/v1/report/data) when FINAL is served: the same numbers and words as the dashboard.

  trend   the food insecurity risk of each province for the served quarters (the on-screen trend chart), class, rank, the forecast
          period, the method table and limitations
  shap    one province-quarter: headline (share, class, rank, population), the "Why is this at risk?" bars
          (top five + Poverty and Vulnerability + time since the last survey) and every card, word for word with the dashboard

The page lays the blocks out (frontend/src/lib/chartReport.ts); nothing here is a new number: shares and classes come from
the served issue (hcw_system rows), explanations from app.final.shap_api, towns from app.services.dashboard.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.final import period as PD
from app.final import report as FR
from app.final import shap_api as SA
from app.services import dashboard as svc
from app.services import reference as ref

MODEL = "final-rate-mind-1.0"
INTRO = ("The number in this report is the food insecurity risk "
         "(FNRI Household Food Insecurity Access Scale, HFIAS) in the quarter shown. 50% or more is High risk. The forecast starts "
         "from the province's latest FNRI survey and adds a LightGBM forecast of the change, using only data published before the "
         "issue date. It is a forecast, not a measured food-insecurity rate or an official statistic.")
SECTIONS = FR.SECTIONS


def _ql(q: str) -> str:
    return f"{q[5:]} {q[:4]}"


def _pct(v) -> str:
    return FR._pct(v)


def _today() -> str:
    return datetime.now(ZoneInfo("Asia/Manila")).strftime("%d %B %Y").lstrip("0")


def _row(slug: str, quarter: str) -> dict:
    from app.ml.inference import hcw_system as HS
    return HS.row(ref.PROVINCES[slug]["code"], quarter) or {}


def _served(quarter: str | None = None) -> tuple[str, list[dict]]:
    from app.final import serving as FS
    issue = FS.current_issue()
    if issue is None:
        raise KeyError("No FINAL forecast is being served.")
    return issue, PD.targets(issue)


def _metadata(area: str, period: str, issue: str) -> list[list[str]]:
    return [["Area", area], ["Period", period], ["Date prepared", _today()], ["Prepared for", "DA Region IV-A"],
            ["Data", f"FINAL forecast issued {PD.issue_label(issue)}, using data for periods before "
                     f"{FR._day(PD.issue_datetime(issue).isoformat())}"
                     + (f" as published by {FR._day(PD.published_by(issue) + 'T00:00:00+08:00')}" if PD.issue_note(issue) else "")],
            ["Model", "FINAL (RATE + MIND): LightGBM, starting from the latest FNRI provincial survey"]]


def _period_blocks(issue: str) -> list[dict]:
    from app.final import cycle as CY
    st = CY.status()
    items = [f"Now: {_ql(st['current_quarter'])}.",
             f"Forecast issued: {PD.issue_label(issue)}, with data for periods before {FR._day(PD.issue_datetime(issue).isoformat())}"
             + (f" as published by {FR._day(PD.published_by(issue) + 'T00:00:00+08:00')}." if PD.issue_note(issue) else "."),
             "Quarters forecast: " + ", ".join(f"{_ql(t['quarter'])} ({t['lead']} quarter{'s' if t['lead'] > 1 else ''} ahead)"
                                               for t in PD.targets(issue)) + ".",
             f"Next forecast: {FR._day(st['next_issue_date'])} (a new forecast is issued automatically on the 10th of every month)."]
    if PD.issue_note(issue):
        items.append("About the data: " + PD.issue_note(issue))
    if st.get("stale") and st.get("stale_reason"):
        items.append("Not yet updated: " + st["stale_reason"][0].upper() + st["stale_reason"][1:] + ".")
    return [{"kind": "heading", "level": 1, "text": "Forecast Period"}, {"kind": "bullets", "items": items}]


def _method_blocks() -> list[dict]:
    import json

    from app.paths import BACKEND_DIR
    meta = BACKEND_DIR / "data" / "final" / "meta"
    H = json.loads((meta / "lead_horizon.json").read_text(encoding="utf-8"))["leads"]
    T = json.loads((meta / "thesis_metrics.json").read_text(encoding="utf-8"))
    served = PD.max_lead()
    rows = []
    for L in range(1, 6):
        m, h = T[str(L)]["HCW"], H[str(L)]
        rows.append([str(L), _pct(100 * h["accuracy"]), _pct(100 * m["precision_high"]), _pct(100 * m["recall_high"]),
                     _pct(100 * m["f1_high"]), f"{m['auc_roc']:.3f}", "yes" if L <= served else "no"])
    cols = [{"label": x, "align": "center", "width": w} for x, w in
            (("Quarters ahead", 0.16), ("Accuracy", 0.14), ("Precision", 0.14), ("Recall", 0.14), ("F1", 0.14), ("AUC", 0.14), ("Shown", 0.14))]
    return [{"kind": "heading", "level": 1, "text": "Method"},
            {"kind": "paragraph", "style": "body",
             "text": "FINAL (RATE + MIND): one LightGBM model per seed (5 seeds, averaged). It starts from each province's latest FNRI "
                     "survey level and forecasts the change per quarter since that survey. A figure that was not yet published is filled "
                     "with its typical value and flagged as missing. Every input may only push the forecast in its known direction."},
            {"kind": "table", "label": "Table M1", "title": "How Well FINAL Did on Past Surveys, by Quarters Ahead", "columns": cols,
             "rows": rows, "note": PD.serving().get("lead_basis", "") + " Results are from 72 past provincial forecasts (FNRI rounds "
             "2018, 2019 and 2021), which were also examined during development. Only quarters marked \"yes\" are shown on the dashboard."}]


def _limitations(limited: bool, articles: int) -> list[dict]:
    items = [f"{t}. {b}" for t, b in (
        ("A forecast, not a measurement", "The number is FINAL's food insecurity risk. "
         "It is not a measured rate, an official statistic or an official classification."),
        ("Tested on few survey rounds", "72 provincial forecasts from three FNRI rounds (2018, 2019, 2021). Only 5 were CALABARZON "
         "provinces, all observed Low. In 2021 only 1 of 4 High provinces was found."),
        ("El Nino and La Nina are not model inputs", "The climate note is context from NOAA. When a strong El Nino is under way, the "
         "actual risk may be higher than forecast."),
        ("Towns and cities are ranked, not forecast", "Their priority is the province forecast weighted by poverty (60%) and population "
         "density (40%). It ranks need within the province; it is not a forecast for each town."),
        ("Missing data is not low risk", "A figure not yet published at the issue date is filled with its typical value and flagged."))]
    if limited:
        items.append(f"Limited news signal. Only {articles} relevant news reports were about this area itself, so its forecast relies "
                     "less on local news. It does not mean the risk is low.")
    return [{"kind": "heading", "level": 1, "text": "Limitations"}, {"kind": "bullets", "items": items}]


def _why_blocks(d: dict, subject: str, quarter: str, label: str) -> list[dict]:
    """The dashboard's left bars (top five + other factors) and its right cards; Poverty and Vulnerability only when the forecast used it."""
    out = [{"kind": "heading", "level": 1, "text": "Why Is This at Risk?"}]
    if not d.get("available"):
        return out + [{"kind": "paragraph", "style": "body", "text": d.get("reason") or "No explanation is available for this quarter."}]
    groups = d.get("groups", [])
    shown = groups[:5]
    word = {"increases_risk": "raises the risk", "protective": "lowers the risk", "no_effect": "almost no effect"}
    bars = [{"label": g["label"], "pct": int(g["pct"]), "direction": g["direction"],
             "text": f"{g['pct']}%, {word[g['direction']]}"}
            for g in shown]
    rest = 100 - sum(int(g["pct"]) for g in shown)
    if rest > 0:
        bars.append({"label": "Other factors", "pct": rest, "direction": "no_effect", "text": f"{rest}%"})
    out += [{"kind": "paragraph", "style": "body",
             "text": f"Figure {label} shows what moved the forecast for {subject} in {_ql(quarter)}. Each bar is a factor group's share "
                     "of what moved the model's forecast (exact LightGBM contributions). It shows what moved the forecast, not proof of cause."},
            {"kind": "figure", "label": f"Figure {label}", "title": f"Why Is {subject} at Risk? {_ql(quarter)}",
             "chart": {"type": "bars", "bars": bars},
             "note": "Red bars raised the risk, green bars lowered it, grey bars had almost no effect. Other factors include "
                     "the time since the last survey."}]
    for key, head in SECTIONS:
        gs = [g for g in groups if g["direction"] == key]
        if not gs:
            continue
        out.append({"kind": "heading", "level": 2, "text": head})
        out.append({"kind": "bullets", "items": [f"{g['label']} ({g['pct']}%): {g['plainEvidence']}" for g in gs]})
    return out


def _window(quarters: list[str], from_: str | None, to: str | None) -> list[str]:
    lo, hi = from_ or quarters[0], to or quarters[-1]
    win = [q for q in quarters if lo <= q <= hi]
    if not win:
        raise KeyError(f"The FINAL forecast covers {quarters[0]} to {quarters[-1]} only.")
    return win


def trend(scope: str, pid: str | None, from_: str | None, to: str | None, municipality: str | None = None) -> dict:
    issue, T = _served()
    win = _window([t["quarter"] for t in T], from_, to)
    lead = {t["quarter"]: t["lead"] for t in T}
    slugs = [pid.lower()] if scope == "province" and pid else list(ref.PROVINCES)
    for s in slugs:
        if s not in ref.PROVINCES:
            raise KeyError(f"Unknown province id '{s}'.")
    rows = {s: {q: _row(s, q) for q in win} for s in slugs}
    last = win[-1]
    share = lambda s, q: rows[s][q].get("risk_pct")
    order = sorted(slugs, key=lambda s: -float(share(s, last) or 0))
    names = {s: ref.PROVINCES[s]["name"] for s in slugs}
    area = names[slugs[0]] if len(slugs) == 1 else "All provinces (" + ", ".join(names[s] for s in ref.PROVINCES) + ")"
    period = _ql(win[0]) if len(win) == 1 else f"{_ql(win[0])} to {_ql(win[-1])}"

    all_last = {s: float(_row(s, last).get("risk_pct") or 0) for s in ref.PROVINCES}
    rank_all = {s: i for i, s in enumerate(sorted(all_last, key=lambda s: -all_last[s]), 1)}
    key = []
    for q in win:
        hs = [s for s in slugs if str(rows[s][q].get("class", "")).upper() == "HIGH"]
        vals = [float(share(s, q)) for s in slugs if share(s, q) is not None]
        if len(slugs) > 1:
            top = max(slugs, key=lambda s: float(share(s, q) or 0))
            low = min(slugs, key=lambda s: float(share(s, q) or 0))
            key.append(f"{_ql(q)} ({lead[q]} quarter{'s' if lead[q] > 1 else ''} ahead): {len(hs)} of {len(slugs)} provinces are at High risk. "
                       f"The CALABARZON average food insecurity risk is {_pct(sum(vals) / len(vals))}. {names[top]} is highest "
                       f"({_pct(share(top, q))}) and {names[low]} lowest ({_pct(share(low, q))}).")
        else:
            s = slugs[0]
            key.append(f"{_ql(q)} ({lead[q]} quarter{'s' if lead[q] > 1 else ''} ahead): {names[s]} food insecurity risk "
                       f"{_pct(share(s, q))} ({str(rows[s][q].get('class', '')).capitalize()} risk).")
    key.append("These are forecasts; their outcomes are not yet known.")

    cols = ([{"label": "Province", "align": "center", "width": 0.22}]
            + [{"label": _ql(q), "align": "center", "width": round(0.48 / len(win), 3)} for q in win]
            + [{"label": "Risk class", "align": "center", "width": 0.15}, {"label": "Rank", "align": "center", "width": 0.15}])
    trows = [[names[s]] + [_pct(share(s, q)) for q in win] + [str(rows[s][last].get("class", "--")).upper(), f"{rank_all[s]} of 5"]
             for s in order]
    if len(slugs) > 1:
        trows.append(["CALABARZON (average)"] + [_pct(sum(float(share(s, q) or 0) for s in slugs) / len(slugs)) for q in win] + ["--", "--"])

    vals = [float(share(s, q)) / 100 for s in slugs for q in win if share(s, q) is not None]
    lo = max(0.0, (int(min(vals) * 20) - 1) / 20) if vals else 0.0
    hi = min(1.0, max(0.55, (int(max(vals) * 20) + 2) / 20)) if vals else 1.0
    chart = {"type": "line", "quarters": [_ql(q) for q in win], "yFormat": "percent", "yTitle": "Food insecurity risk",
             "series": [{"name": names[s], "values": [None if share(s, q) is None else round(float(share(s, q)) / 100, 4) for q in win]}
                        for s in order],
             "yMin": lo, "yMax": hi, "yStep": 0.05, "lines": [{"value": 0.5, "label": "High risk (50%)"}]}

    blocks = [{"kind": "paragraph", "style": "body", "text": INTRO}, *_period_blocks(issue),
              {"kind": "heading", "level": 1, "text": "Key Points"}, {"kind": "bullets", "items": key}]
    if municipality:
        m = next((x for x in svc.municipality_summary(last, province_id=slugs[0]) if x.get("id") == municipality), None)
        if m:
            blocks.append({"kind": "paragraph", "style": "body",
                           "text": f"{m['name']} has no forecast of its own: it moves with {names[slugs[0]]}. Its priority within the province "
                                   f"is rank {m.get('rankInProvince') or '--'} ({_pct(100 * float(m['riskIndex'])) if m.get('riskIndex') is not None else '--'}), "
                                   "from the province forecast weighted by poverty (60%) and population density (40%)."})
    blocks += [{"kind": "heading", "level": 1, "text": "Forecast by Province"},
               {"kind": "table", "label": "Table 1", "title": f"Food Insecurity Risk, {period}", "columns": cols,
                "rows": trows, "note": f"High risk at 50% or more. Risk class and rank are for {_ql(last)}; rank 1 is the highest of the five provinces."},
               {"kind": "figure", "label": "Figure 1", "title": f"Food Insecurity Risk, {period}", "chart": chart,
                "note": "The dashed line marks High risk (50%)."},
               *_method_blocks(), *_limitations(False, 0)]
    return {"type": "trend", "scope": scope, "title": "aiPHeed Food Insecurity Forecast Report", "subtitle": "Food Insecurity Risk Over Time",
            "generatedDate": _today(), "metadata": _metadata(area, period, issue), "blocks": blocks}


def drivers(pid: str, quarter: str) -> dict:
    issue, T = _served()
    slug = pid.lower()
    if slug not in ref.PROVINCES:
        raise KeyError(f"Unknown province id '{pid}'.")
    if quarter not in {t["quarter"] for t in T}:
        raise KeyError(f"The FINAL forecast covers {T[0]['quarter']} to {T[-1]['quarter']} only.")
    name = ref.PROVINCES[slug]["name"]
    r = _row(slug, quarter)
    d = SA.province(slug, quarter)
    lead = d.get("lead") or 1
    fig = SA._vulnerability_figures([name], SA._cutoff_of(quarter, lead)).get(name, {})
    summary = svc.province_summary(quarter)
    pv = next((p for p in summary if p["id"] == slug), {})
    # the API's competition rank (ties share a rank) out of the published provinces, as on the map
    rank, tied = pv.get("rank"), bool(pv.get("rankTied"))
    n_pub = sum(1 for p in summary if not p.get("withheld"))

    head = [["Food insecurity risk", f"{_pct(r.get('risk_pct'))} (forecast)"],
            ["Risk class", f"{str(r.get('class') or '--').upper()} (High risk at 50%)"],
            ["Rank in CALABARZON", f"{rank} of {n_pub}{' (tied)' if tied else ''} (highest risk first)" if rank else "--"],
            [f"Population ({fig.get('census_year', '')} census)", f"{pv['population']:,}" if pv.get("population") else "--"],   # as on the dashboard
            ["News reports used", str(pv.get("articleCount", "--"))]]
    blocks = [{"kind": "paragraph", "style": "body", "text": INTRO}, *_period_blocks(issue),
              {"kind": "heading", "level": 1, "text": "Key Points"},
              {"kind": "bullets", "items": list(d.get("summary") or []) + [
                  f"This is a forecast {lead} quarter{'s' if lead > 1 else ''} ahead; its outcome is not yet known."]},
              {"kind": "heading", "level": 1, "text": "Headline"},
              {"kind": "table", "label": "Table 1", "title": f"{name}, {_ql(quarter)}",
               "columns": [{"label": "Item", "align": "left", "width": 0.4}, {"label": "Value", "align": "left", "width": 0.6}],
               "rows": head, "note": "High risk at 50% or more. Rank 1 is the highest of the five provinces."}]
    blocks += _why_blocks(d, name, quarter, "1")
    munis = sorted(svc.municipality_summary(quarter, province_id=slug), key=lambda m: (m.get("rankInProvince") or 999, m["name"]))
    if munis:
        blocks += [{"kind": "heading", "level": 1, "text": "Towns and Cities"},
                   {"kind": "table", "label": "Table 2", "title": f"Towns and Cities of {name} by Priority, {_ql(quarter)}",
                    "columns": [{"label": "Rank", "align": "center", "width": 0.1}, {"label": "City / Municipality", "align": "left", "width": 0.38},
                                {"label": "Population", "align": "right", "width": 0.18}, {"label": "Poverty", "align": "right", "width": 0.16},
                                {"label": "Priority", "align": "right", "width": 0.18}],
                    "rows": [[str(m.get("rankInProvince") or "--"), m["name"], f"{m['population']:,}",
                              _pct(m["povertyRate"]) if m.get("povertyRate") is not None else "n/a",
                              _pct(100 * float(m["riskIndex"])) if m.get("riskIndex") is not None else "--"] for m in munis],
                    "note": "Priority is the province forecast weighted by poverty (60%) and population density (40%). These are not separate "
                            "forecasts for each town or city; every town rises and falls with its province."}]
    blocks += _method_blocks() + _limitations(bool(pv.get("limitedSignal")), int(pv.get("articleCount") or 0))
    return {"type": "shap", "scope": "province", "title": "aiPHeed Food Insecurity Forecast Report", "subtitle": "Why Is This at Risk?",
            "generatedDate": _today(), "metadata": _metadata(name, _ql(quarter), issue), "blocks": blocks}
