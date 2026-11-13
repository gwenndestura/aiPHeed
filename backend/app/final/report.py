"""
PDF report of the served FINAL forecast (province or CALABARZON), built from the same sources as the dashboard:

  forecast period        app.final.cycle.status       issue, cut-off, when made, next issue, stale warning
  headline               app.ml.inference.hcw_system  forecast share and class of the served issue (as the left card)
  why is this at risk?   app.final.shap_api           the same groups, shares and plain sentences as the left bars and right cards
                                                      (El Nino note; Poverty and Vulnerability only when the forecast used it)
  towns and cities       app.services.dashboard       the dashboard's priority ranking (rank in province)
  method                 data/final/meta              FINAL's walk-forward evaluation; served leads from data/final/serving.json

Layout, fonts and colours are those of app.services.report (no new design). Used by app.services.report whenever FINAL is served.
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, SimpleDocTemplate, Spacer

from app.final import cycle as CY
from app.final import period as PD
from app.final import shap_api as SA
from app.paths import BACKEND_DIR
from app.services import dashboard as svc
from app.services import reference as ref
from app.services import report as R

FOOTER = "Forecast share of food-insecure households (FNRI HFIAS; High risk at 50%). A forecast, not an official classification."
COVER = ("<b>The number in this report is the forecast share of households that will be moderately or severely food insecure</b> "
         "(FNRI Household Food Insecurity Access Scale, HFIAS), for the quarter shown. 50% or more is High risk. The forecast starts "
         "from the province's latest FNRI survey and adds a LightGBM forecast of the change, using only data published before the "
         "issue date. <b>It is a forecast, not a measured food-insecurity rate or an official statistic.</b>")
SECTIONS = (("increases_risk", "What is raising the risk"), ("protective", "What is lowering the risk"), ("no_effect", "No effect this time"))


class _Canvas(R._Canvas):
    def __call__(self, canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setFont("Helvetica-Bold", 7.2)
        canvas.setFillColor(R.MUTED)
        canvas.drawString(18 * mm, height - 12 * mm, "aiPHeed")
        canvas.setFont("Helvetica", 7.2)
        canvas.drawString(32 * mm, height - 12 * mm, f"{self.subject}  |  {self.quarter}")
        canvas.setStrokeColor(R.RULE)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, height - 14.5 * mm, width - 18 * mm, height - 14.5 * mm)
        canvas.setFont("Helvetica", 6.6)
        canvas.drawString(18 * mm, 11 * mm, FOOTER)
        canvas.drawRightString(width - 18 * mm, 11 * mm, f"Page {doc.page}")
        canvas.restoreState()


def _pct(v, digits: int = 1) -> str:
    if v is None:
        return "--"
    s = f"{float(v):.{digits}f}".rstrip("0").rstrip(".") if digits else f"{float(v):.0f}"
    return f"{s}%"


def _day(iso: str | None) -> str:
    if not iso:
        return "--"
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(iso).astimezone(ZoneInfo("Asia/Manila")).strftime("%d %B %Y").lstrip("0")


def _ql(q: str) -> str:
    return f"{q[5:]} {q[:4]}"


def _doc(buf, title: str):
    return SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
                             title=title, author="aiPHeed", subject="Food insecurity risk forecast (FINAL)")


def _cover(title: str, subject: str, quarter: str) -> list:
    generated = datetime.now(timezone.utc).astimezone().strftime("%d %B %Y").lstrip("0")
    return [R._p("DEPARTMENT OF AGRICULTURE REGION IV-A", "eyebrow"), Spacer(1, 2 * mm), R._p(title, "title"),
            R._p(f"{subject} · {R._quarter_label(quarter)}", "subtitle"), Spacer(1, 3 * mm), R._rule(1.2, R.INK, 0, 4),
            R._p(f"Report generated {generated} from aiPHeed model output.", "small"), Spacer(1, 5 * mm),
            R._callout("What this forecast is", COVER)]


def _period_block() -> list:
    st = CY.status()
    served = st.get("served_issue_quarter")
    lines = [f"<b>Now:</b> {_ql(st['current_quarter'])}"]
    if served:
        lines.append(f"<b>Forecast issued:</b> {_ql(served)}, with data published before {_day(PD.issue_datetime(served).isoformat())}; "
                     f"made {_day(st.get('served_generated_utc'))}")
        lines.append("<b>Quarters forecast:</b> " + ", ".join(f"{_ql(t['quarter'])} ({t['lead']} quarter{'s' if t['lead'] > 1 else ''} ahead)"
                                                           for t in PD.targets(served)))
    lines.append(f"<b>Next forecast:</b> {_day(st['next_issue_date'])} (a new forecast is issued automatically every quarter)")
    flow = [R._callout("Forecast period", "<br/>".join(lines))]
    if st.get("stale") and st.get("stale_reason"):
        flow += [Spacer(1, 2 * mm), R._callout("Not yet updated", R._escape(st["stale_reason"][0].upper() + st["stale_reason"][1:]) + ".", R.WARN_BG)]
    return flow


def _why_block(d: dict, width: float) -> list:
    """The left bars (top five + Poverty and Vulnerability + Other) and the right cards, as on the dashboard."""
    if not d.get("available"):
        return [R._p(R._escape(d.get("reason") or "No explanation is available for this quarter."), "body")]
    groups = d.get("groups", [])
    shown = groups[:5]
    other = max(0, 100 - sum(g["pct"] for g in shown))
    word = {"increases_risk": "raises", "protective": "lowers", "no_effect": "no effect"}
    rows = [(g["label"], int(g["pct"]), f"{g['pct']}%  {word[g['direction']]}",
             R.RAISING if g["direction"] == "increases_risk" else R.LOWERING if g["direction"] == "protective" else R.MUTED) for g in shown]
    if other > 0:
        rows.append(("Other factors", int(other), f"{other}%", R.MUTED))
    flow = [R._bar_table(rows, width), Spacer(1, 2 * mm),
            R._p("Each bar is a factor group's share of what moved the model's forecast (exact LightGBM contributions). "
                 "It shows what moved the forecast, not proof of cause.", "small"), Spacer(1, 4 * mm)]
    for key, head in SECTIONS:
        gs = [g for g in groups if g["direction"] == key]
        if not gs:
            continue
        flow.append(R._p(f"<b>{head}</b>", "h3"))
        for g in gs:
            flow.append(KeepTogether([R._p(f"<b>{R._escape(g['label'])}</b> · {g['pct']}%", "body"),
                                      R._p(R._escape(g["plainEvidence"]), "small"), Spacer(1, 2 * mm)]))
    return flow


def _method_block() -> list:
    meta = BACKEND_DIR / "data" / "final" / "meta"
    H = json.loads((meta / "lead_horizon.json").read_text(encoding="utf-8"))["leads"]
    T = json.loads((meta / "thesis_metrics.json").read_text(encoding="utf-8"))
    served = PD.max_lead()
    rows = []
    for L in range(1, 6):
        m, h = T[str(L)]["HCW"], H[str(L)]
        rows.append([str(L), _pct(100 * h["accuracy"]), _pct(100 * m["precision_high"]), _pct(100 * m["recall_high"]),
                     _pct(100 * m["f1_high"]), f"{m['auc_roc']:.3f}", "yes" if L <= served else "no"])
    w = 170 * mm / 7
    return [R._p("FINAL (RATE + MIND): one LightGBM model per seed (5 seeds, averaged). It starts from each province's latest FNRI "
                 "survey level and forecasts the change per quarter since that survey. A figure that was not yet published is filled "
                 "with its typical value and flagged as missing. Every input may only push the forecast in its known direction. "
                 "A new forecast is issued automatically every quarter from data published before the issue date.", "body"),
            Spacer(1, 3 * mm),
            R._data_table(["Quarters ahead", "Accuracy", "Precision", "Recall", "F1", "AUC", "Shown"], rows, [w] * 7,
                          {i: "RIGHT" for i in range(1, 6)}),
            Spacer(1, 2 * mm),
            R._p(R._escape(PD.serving().get("lead_basis", "")) + " Results are from 72 past provincial forecasts (FNRI rounds 2018, 2019 "
                 "and 2021), which were also examined during development.", "small")]


def _limitations_block(limited: bool, articles: int) -> list:
    items = [
        ("A forecast, not a measurement", "The number is FINAL's forecast share of households moderately or severely food insecure. "
         "It is not a measured food-insecurity rate, an official statistic or an official classification."),
        ("Tested on few survey rounds", "72 provincial forecasts from three FNRI rounds (2018, 2019, 2021), also examined during "
         "development. Only 5 were CALABARZON provinces, all observed Low. In 2021 only 1 of 4 High provinces was found."),
        ("El Niño and La Niña are not model inputs", "The climate note in the explanation is context from NOAA. When a strong El Niño "
         "is under way, the actual risk may be higher than forecast."),
        ("Towns and cities are ranked, not forecast", "Their priority is the province forecast weighted by poverty (60%) and population "
         "density (40%). It ranks need within the province; it is not a forecast for each town."),
        ("Missing data is not low risk", "A figure not yet published at the issue date is filled with its typical value and flagged."),
    ]
    if limited:
        items.append(("Limited news signal", f"Only {articles} relevant news reports were about this area itself, so its forecast "
                      "relies less on local news. It does not mean the risk is low."))
    flow = []
    for t, b in items:
        flow += [R._p(f"<b>{t}</b>", "h3"), R._p(b, "small"), Spacer(1, 1.5 * mm)]
    return flow


def _code_of(slug: str) -> str:
    return ref.PROVINCES[slug]["code"]


def build_province_report(province_id: str, quarter: str, withheld: frozenset[str] = frozenset()) -> bytes:
    from app.ml.inference import hcw_system as HS
    slug = province_id.lower()
    if slug not in ref.PROVINCES:
        raise svc.SubjectNotFound(f"Unknown province id '{province_id}'.")
    if slug in withheld:
        raise svc.ForecastWithheld(f"The {quarter} assessment for this province has been withheld from publication by a reviewer.")
    provinces = svc.province_summary(quarter, withheld)
    pv = next((p for p in provinces if p["id"] == slug), None)
    if pv is None:
        raise svc.SubjectNotFound(f"Unknown province id '{province_id}'.")
    name, code = pv["name"], pv["provinceCode"]
    r = HS.row(code, quarter) or {}
    shap = SA.province(slug, quarter)
    lead = shap.get("lead") or 1
    fig = SA._vulnerability_figures([name], SA._cutoff_of(quarter, lead)).get(name, {})
    published = [p for p in provinces if not p["withheld"]]
    share_of = {p["id"]: float((HS.row(p["provinceCode"], quarter) or {}).get("score_pct") or 0) for p in published}
    published.sort(key=lambda p: -share_of[p["id"]])                     # rank by the number the report shows
    rank = next((i for i, p in enumerate(published, 1) if p["id"] == slug), None)

    buf = io.BytesIO()
    doc = _doc(buf, f"aiPHeed {name} {quarter}")
    width = doc.width
    flow = _cover("Food Insecurity Risk Forecast", name, quarter) + [Spacer(1, 3 * mm)] + _period_block()
    flow += R._section("Headline")
    share = r.get("score_pct")
    flow += [R._data_table([], [
        [R._p("Food insecurity risk", "small"), R._p(f"<b>{_pct(share)}</b> of households (forecast)", "cell")],
        [R._p("Risk class", "small"), R._p(f"<b>{str(r.get('class') or pv.get('riskLabel') or '--').upper()}</b> (High risk at 50%)", "cell")],
        [R._p("Rank in CALABARZON", "small"), R._p(f"<b>{rank} of {len(published)}</b> (highest risk first)" if rank else "--", "cell")],
        [R._p(f"Population ({fig.get('census_year', '')} census)", "small"), R._p(f"<b>{fig['population']:,}</b>" if "population" in fig else "--", "cell")],
        [R._p("News reports used", "small"), R._p(f"<b>{pv['articleCount']}</b>", "cell")],
    ], [55 * mm, width - 55 * mm])]
    if pv.get("limitedSignal"):
        flow += [Spacer(1, 3 * mm), R._callout("Limited news signal", f"Only {pv['articleCount']} relevant news reports were about this "
                                               "province itself. Its forecast relies less on local news; this does not mean the risk is low.", R.WARN_BG)]
    flow.append(PageBreak())
    flow += R._section(f"Why is this at risk? {name}, {_ql(quarter)}")
    flow += _why_block(shap, width)
    flow.append(PageBreak())
    flow += R._section("Towns and cities")
    flow += [R._p("Ranked by priority within the province: the province forecast weighted by poverty (60%) and population density "
                  "(40%). <b>These are not separate forecasts for each town or city</b>; every town rises and falls with its province.",
                  "body"), Spacer(1, 3 * mm)]
    munis = sorted(svc.municipality_summary(quarter, province_id=slug), key=lambda m: (m.get("rankInProvince") or 999, m["name"]))
    rows = [[R._p(str(m.get("rankInProvince") or "--"), "cell"), R._p(R._escape(m["name"]), "cellb"), R._p(m["classification"], "cell"),
             R._p(f"{m['population']:,}", "cell"), R._p(_pct(m["povertyRate"]) if m.get("povertyRate") is not None else "n/a", "cell"),
             R._p(_pct(100 * float(m["riskIndex"])) if m.get("riskIndex") is not None else "--", "cell")] for m in munis]
    flow.append(R._data_table(["Rank", "City / Municipality", "Class", "Population", "Poverty", "Priority"], rows,
                              [12 * mm, width - 106 * mm, 24 * mm, 26 * mm, 22 * mm, 22 * mm], {3: "RIGHT", 4: "RIGHT", 5: "RIGHT"}))
    flow.append(PageBreak())
    flow += R._section("News evidence")
    flow += R._news_block(svc.news(code, quarter, 1, 60), width)
    flow += R._section("Method")
    flow += _method_block()
    flow += R._section("Limitations")
    flow += _limitations_block(bool(pv.get("limitedSignal")), int(pv["articleCount"]))
    flow += [Spacer(1, 3 * mm), R._callout("Scope of this assessment", R.ACTIONS_PLACEHOLDER)]
    doc.build(flow, onFirstPage=_Canvas(name, quarter), onLaterPages=_Canvas(name, quarter))
    return buf.getvalue()


def build_region_report(quarter: str, withheld: frozenset[str] = frozenset()) -> bytes:
    from app.ml.inference import hcw_system as HS
    provinces = svc.province_summary(quarter, withheld)
    published = [p for p in provinces if not p["withheld"]]
    rows_hs = {p["id"]: (HS.row(p["provinceCode"], quarter) or {}) for p in published}
    published.sort(key=lambda p: -float(rows_hs[p["id"]].get("score_pct") or 0))
    shares = [float(rows_hs[p["id"]]["score_pct"]) for p in published if rows_hs[p["id"]].get("score_pct") is not None]
    shap = SA.province("calabarzon", quarter)
    news = svc.news(None, quarter, 1, 60)

    buf = io.BytesIO()
    doc = _doc(buf, f"aiPHeed CALABARZON {quarter}")
    width = doc.width
    flow = _cover("Regional Food Insecurity Risk Forecast", ref.REGION_NAME, quarter) + [Spacer(1, 3 * mm)] + _period_block()
    flow += R._section("Headline")
    high = sum(1 for p in published if str(rows_hs[p["id"]].get("class", "")).upper() == "HIGH")
    flow += [R._data_table([], [
        [R._p("Food insecurity risk", "small"), R._p(f"<b>{_pct(sum(shares) / len(shares)) if shares else '--'}</b> of households "
                                                     f"(average of the {len(shares)} provinces)", "cell")],
        [R._p("Provinces at High risk", "small"), R._p(f"<b>{high} of {len(published)}</b>", "cell")],
        [R._p("Provinces withheld", "small"), R._p(f"<b>{len(provinces) - len(published)}</b>", "cell")],
        [R._p("News reports used", "small"), R._p(f"<b>{news['articleCount']}</b> ({news['provinceAttributed']} about a specific province)", "cell")],
    ], [55 * mm, width - 55 * mm])]
    flow += R._section("Provinces from highest to lowest risk")
    top = max(shares, default=1) or 1
    flow.append(R._bar_table([(p["name"], int(round(float(rows_hs[p["id"]].get("score_pct") or 0) / top * 100)),
                               f"{_pct(rows_hs[p['id']].get('score_pct'))}  {str(rows_hs[p['id']].get('class', '')).capitalize()}",
                               R.RAISING if str(rows_hs[p["id"]].get("class", "")).upper() == "HIGH" else R.ACCENT) for p in published], width))
    flow.append(Spacer(1, 3 * mm))
    rows = [[R._p(R._escape(p["name"]), "cellb"), R._p(_pct(rows_hs[p["id"]].get("score_pct")), "cell"),
             R._p(str(rows_hs[p["id"]].get("class", "--")).upper(), "cell"),
             R._p(str(p["articleCount"]), "cell")] for p in published]
    flow.append(R._data_table(["Province", "Risk", "Class", "News"], rows,
                              [width - 70 * mm, 25 * mm, 25 * mm, 20 * mm], {1: "RIGHT", 3: "RIGHT"}))
    flow.append(PageBreak())
    flow += R._section(f"Why is CALABARZON at risk? {_ql(quarter)}")
    flow += _why_block(shap, width)
    flow.append(PageBreak())
    flow += R._section("News evidence")
    flow += R._news_block(news, width)
    flow += R._section("Method")
    flow += _method_block()
    flow += R._section("Limitations")
    flow += _limitations_block(all(p["limitedSignal"] for p in published) if published else True, int(news["articleCount"]))
    flow += [Spacer(1, 3 * mm), R._callout("Scope of this assessment", R.ACTIONS_PLACEHOLDER)]
    doc.build(flow, onFirstPage=_Canvas(ref.REGION_NAME, quarter), onLaterPages=_Canvas(ref.REGION_NAME, quarter))
    return buf.getvalue()
