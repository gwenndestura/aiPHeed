"""
app/services/report_data.py
----------------------------
Structured payload behind the Visualization page's PDF reports.

The frontend lays this out with jsPDF; it adds no findings of its own. The
payload is an ordered list of blocks (headings, paragraphs, tables, figure
data), every number in which comes from the dashboard services:
province_summary(), explainability(), explainability_region(), news(),
model_performance() and the quarter timeline. Prose comes from
report_text.py and dashboard.compose_formal_interpretation().

Withheld province-quarters (the admin review list) are blanked before any
text is composed: no score, share, driver or article from a withheld
province-quarter reaches the payload, and the text says "withheld from
publication" instead.
"""

from __future__ import annotations

import functools
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import pandas as pd

from app.ml.inference.disaggregator import DENSITY_WEIGHT, POVERTY_WEIGHT
from app.ml.inference.thesis_explainer import THESIS_DISPLAY_MAP
from app.ml.inference.thesis_predictor import MODEL_PATH, ThesisPredictor
from app.ml.nlp.trigger_classifier import classify_triggers
from app.services import dashboard as svc
from app.services import reference as ref
from app.services import report_text as txt
from app.services.dashboard import _ascii
from app.services.report import ACTIONS_PLACEHOLDER

PST = timezone(timedelta(hours=8))
RICE_PATH = Path("data/processed/psa_rice_prices.parquet")

REPORT_TITLE = "aiPHeed Food Insecurity Forecast Report"
PREPARED_FOR = "DA Region IV-A"
TREND, SHAP = "trend", "shap"
SUBTITLES = {TREND: "Risk Level Trend", SHAP: "SHAP Explainability of Driver Groups"}

# The training label, as implemented in
# app/ml/features/label_generator.py::_build_cpi_labels (thesis Eq. 4).
LABEL_RULE = (
    "the province's food consumer price index is above its 24-quarter rolling mean plus "
    "one standard deviation in two consecutive quarters (thesis Equation 4)."
)


class ReportRequestError(ValueError):
    """Bad combination of report parameters."""


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def _quarter_window(start: str, end: str) -> list[str]:
    start = svc.resolve_quarter(start)
    end = svc.resolve_quarter(end)
    lo, hi = sorted((ref.quarter_index(start), ref.quarter_index(end)))
    # Reports describe the nowcast indicator; the E20 forecast quarter is a
    # different target and is left out rather than worded as a nowcast.
    window = [q for q in svc.available_quarters()
              if lo <= ref.quarter_index(q) <= hi and not svc.is_forecast_quarter(q)]
    if not window:
        raise ReportRequestError(
            "Reports cover nowcast quarters only; the selected range holds only the "
            "E20 forecast quarter. See the Forecast Period banner on the dashboard."
        )
    return window


def _calendar() -> tuple[str, int, str]:
    now = datetime.now(PST)
    calendar = f"{now.year}-Q{(now.month - 1) // 3 + 1}"
    latest = svc.latest_quarter()
    return calendar, max(ref.quarter_index(calendar) - ref.quarter_index(latest), 0), latest


def _missing_inputs(quarter: str) -> dict[str, list[str]]:
    """Model inputs absent from the panel for `quarter`, by province."""
    tp = ThesisPredictor()
    tp.load()
    rows = tp._panel[tp._panel["quarter"] == quarter]
    groups: dict[str, list[str]] = {}
    for _, r in rows.iterrows():
        name = ref.province_name(ref.province_slug(r["province_code"]) or "") or r["province_code"]
        for col in tp._lgbm_feature_cols:
            if pd.isna(r.get(col)):
                if col.startswith("FSSI"):
                    label = "the Food Stress Sentiment Index features"
                elif col.startswith("trigger_"):
                    label = "the news trigger proportions"
                else:
                    label = THESIS_DISPLAY_MAP.get(col, {}).get("display_name", col)
                bucket = groups.setdefault(label, [])
                if name not in bucket:
                    bucket.append(name)
    return groups


def _unemployment_note(quarter: str) -> str | None:
    """Said only when the panel shows one shared value across provinces."""
    tp = ThesisPredictor()
    tp.load()
    vals = tp._panel.loc[tp._panel["quarter"] == quarter, "unemployment_rate"].dropna()
    if len(vals) < 2 or vals.nunique() != 1:
        return None
    return (f"In {txt.qlabel(quarter)}, every province carries the same unemployment rate "
            f"({vals.iloc[0]:.3f}%), the national Labor Force Survey figure applied to each "
            f"province. This input therefore does not distinguish between provinces.")


@functools.lru_cache(maxsize=1)
def _model_meta() -> dict:
    bundle = joblib.load(MODEL_PATH)
    tp = ThesisPredictor()
    tp.load()
    return {
        "components": [
            ("a LightGBM classifier", bundle.get("blend_weight_lgbm", 0.0)),
            ("a logistic regression on the government indicators", bundle.get("blend_weight_lr", 0.0)),
            ("a logistic regression on the climate, fish kill and OFW news triggers",
             bundle.get("blend_weight_weak", 0.0)),
        ],
        "featureCount": len(bundle.get("feature_cols", tp._lgbm_feature_cols or [])),
        "label": str(bundle.get("label", "label_cpi")),
        "trainedThrough": str(bundle.get("trained_through", "")),
        "trainRows": int(bundle.get("n_train_rows", 0)),
        "decisionThreshold": float(bundle.get("threshold", tp._threshold)),
    }


@functools.lru_cache(maxsize=1)
def _sources() -> list[str]:
    out = [
        "PSA OpenStat, food consumer price index by province (2018=100): the training label "
        "and the food CPI deviation feature.",
        "PSA Labor Force Survey via OpenStat, national unemployment rate applied to each "
        "province: the unemployment feature.",
    ]
    if RICE_PATH.exists():
        note = str(pd.read_parquet(RICE_PATH, columns=["source_note"])["source_note"].iloc[0])
        out.append(note.split(". ")[0].rstrip(".") + ": the rice price change feature.")
    corpus = svc._corpus()
    if not corpus.empty:
        dates = corpus["_date"].dropna()
        out.append(
            f"News corpus of {len(corpus)} relevance-filtered articles"
            + (f" published {dates.min()} to {dates.max()}" if len(dates) else "")
            + ": scored into the Food Stress Sentiment Index and the five driver-group "
            "trigger proportions."
        )
    out.append("PSA 2020 Census of Population and Housing: provincial population.")
    out.append("PSA 2021 poverty incidence, averaged over each province's LGU estimates: "
               "provincial poverty incidence.")
    return out


# ---------------------------------------------------------------------------
# Block helpers
# ---------------------------------------------------------------------------

def _h(text: str, level: int = 1) -> dict:
    return {"kind": "heading", "level": level, "text": _ascii(text)}


def _p(text: str, style: str = "body") -> dict:
    return {"kind": "paragraph", "style": style, "text": _ascii(text)}


def _table(number: int, caption: str, columns: list[tuple[str, str, float]],
           rows: list[list[str]], note: str | None = None) -> dict:
    return {
        "kind": "table", "number": number, "caption": _ascii(caption),
        "columns": [{"label": _ascii(c), "align": a, "width": w} for c, a, w in columns],
        "rows": [[_ascii(str(c)) for c in r] for r in rows],
        "note": _ascii(note) if note else None,
    }


def _bars(triggers: list[dict]) -> dict:
    return {
        "type": "bars",
        "cutoff": ref.TRIGGER_RED_CUTOFF,
        "bars": [{"label": _ascii(t["label"]), "pct": t["pct"], "direction": t["direction"]}
                 for t in triggers],
    }


def _axis(values: list[float]) -> tuple[float, float, float]:
    """Fit the y-axis to the data with 0.05 padding, on a 0.05 grid, within 0-1."""
    lo = max(0.0, math.floor((min(values) - 0.05) * 20) / 20)
    hi = min(1.0, math.ceil((max(values) + 0.05) * 20) / 20)
    step = 0.05 if hi - lo <= 0.4 else 0.1
    return round(lo, 2), round(hi, 2), step


def _trigger_cell(t: dict | None) -> str:
    if t is None:
        return "--"
    if not t["pct"]:
        return "0%"
    return f"{t['pct']}% {'+' if t['direction'] == 'increases_risk' else '-'}"


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------

def build_report(kind: str, scope: str, province_id: str | None,
                 start: str, end: str, rejected: set[tuple[str, str]],
                 municipality_id: str | None = None) -> dict:
    if kind not in (TREND, SHAP):
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
    if kind == SHAP and scope != "province":
        raise ReportRequestError("The SHAP report covers one province.")

    window = _quarter_window(start, end) if kind == TREND else [svc.resolve_quarter(end)]
    if not window:
        raise svc.QuarterNotAvailable("No scorable quarter lies in the requested range.")
    first_q, last_q = window[0], window[-1]

    withheld = {q: frozenset(pid for pid, rq in rejected if rq == q) for q in window}
    summaries = {q: {p["id"]: p for p in svc.province_summary(q, withheld[q])} for q in window}
    names = {s: ref.PROVINCES[s]["name"] for s in slugs}
    codes = {s: ref.province_code(s) for s in slugs}

    calendar, lag, latest_published = _calendar()
    high, alert = ref.RISK_DISPLAY_CUTOFF, ref.ALERT_THRESHOLD
    generated = datetime.now(PST)

    # Province series, blanked where withheld.
    series = []
    for s in slugs:
        pts = []
        for q in window:
            row = summaries[q].get(s)
            held = s in withheld[q]
            pts.append({"quarter": q, "withheld": held,
                        "value": None if held or row is None else row["riskScore"]})
        series.append({"id": s, "name": names[s], "points": pts})

    municipal = None
    if municipality_id and scope == "province":
        mrow = ref.municipality_row(municipality_id)
        if mrow is None or mrow["provinceId"] != slugs[0]:
            raise svc.SubjectNotFound(f"Unknown municipality id '{municipality_id}'.")
        mpts = []
        for q in window:
            held = slugs[0] in withheld[q]
            val = None
            if not held:
                hit = [m for m in svc.municipality_summary(q, slugs[0]) if m["id"] == municipality_id.lower()]
                val = hit[0]["riskIndex"] if hit else None
            mpts.append({"quarter": q, "withheld": held, "value": val})
        municipal = {"id": municipality_id.lower(), "name": f"{mrow['lgu_name']} (municipal, reweighted)",
                     "points": mpts}

    # SHAP for the latest quarter, and for the comparison quarter.
    compare_q = first_q if kind == TREND else svc._previous_quarter(last_q)

    def explain(s: str, q: str | None) -> dict | None:
        if q is None or s in withheld.get(q, frozenset()) or s in _withheld_at(rejected, q):
            return None
        try:
            return svc.explainability(codes[s], q)
        except Exception:
            return None

    latest_explain = {s: explain(s, last_q) for s in slugs}
    compare_explain = {s: explain(s, compare_q) for s in slugs} if compare_q != last_q else {}

    # ---- Table 1 rows / summary inputs
    rank_pool = sorted(
        [p for p in summaries[last_q].values() if not p["withheld"] and p["riskScore"] is not None],
        key=lambda p: p["riskScore"], reverse=True)
    ranks = {p["id"]: i + 1 for i, p in enumerate(rank_pool)}

    prov_rows = []
    for srs in series:
        pub = [p for p in srs["points"] if p["value"] is not None]
        e = latest_explain[srs["id"]]
        top = e["triggers"][0] if e and e["triggers"] else None
        prov_rows.append({
            "id": srs["id"], "name": srs["name"],
            "start": pub[0]["value"] if pub else None,
            "startQuarter": pub[0]["quarter"] if pub else None,
            "end": pub[-1]["value"] if pub and pub[-1]["quarter"] == last_q else None,
            "endQuarter": last_q,
            "withheldLatest": srs["id"] in withheld[last_q],
            "alerts": sum(1 for p in pub if p["value"] >= alert),
            "published": len(pub),
            "top": top,
        })

    blocks: list[dict] = []

    # ---- Data vintage
    vintage_text = txt.compose_vintage(latest_published, calendar, lag,
                                       _missing_inputs(latest_published), len(ref.PROVINCES))

    # ---- 1. Summary of findings
    blocks.append(_h("1. Summary of Findings"))
    if kind == TREND and scope == "region":
        region = svc.explainability_region(last_q, withheld[last_q])
        region_top = region["triggers"][0] if region["triggers"] else None
        summary = txt.compose_summary(prov_rows, region_top, first_q, last_q, high, alert)
    else:
        r = prov_rows[0]
        region = None
        summary = txt.compose_province_summary(
            r["name"], last_q, r["end"], r["withheldLatest"], ranks.get(r["id"]),
            len(rank_pool), r["top"],
            None if r["withheldLatest"] else summaries[last_q][r["id"]]["articleCount"],
            high, alert)
        if kind == TREND and r["start"] is not None and r["end"] is not None and first_q != last_q:
            d = txt.rounded_change(r["start"], r["end"])
            summary.append(_ascii(
                f"Between {txt.qlabel(r['startQuarter'])} and {txt.qlabel(last_q)}, the score "
                f"changed by {txt.signed(d)}, from {txt.score(r['start'])} to {txt.score(r['end'])}."))
    blocks.append({"kind": "bullets", "items": summary})

    fig_n, tab_n = 0, 0
    sec = 1

    # ---- Trend figure + Table 1
    if kind == TREND:
        sec += 1
        blocks.append(_h(f"{sec}. Risk Level Trend"))
        plotted = series + ([municipal] if municipal else [])
        values = [p["value"] for s in plotted for p in s["points"] if p["value"] is not None]
        fig_n += 1
        if values:
            y_min, y_max, step = _axis(values)
            lines = [{"value": v, "label": lab} for v, lab in
                     ((alert, f"Alert threshold ({alert:.2f})"), (high, f"High-risk line ({high:.2f})"))
                     if y_min <= v <= y_max]
            outside = [lab for v, lab in ((alert, f"the alert threshold ({alert:.2f})"),
                                           (high, f"the high-risk line ({high:.2f})"))
                       if not (y_min <= v <= y_max)]
            subject = ("the published CALABARZON provinces" if scope == "region"
                       else names[slugs[0]] + (" and " + municipal["name"] if municipal else ""))
            caption = (f"Figure {fig_n}. Risk Level score for {subject}, {txt.qlabel(first_q)} to "
                       f"{txt.qlabel(last_q)}. The vertical axis spans {y_min:.2f} to {y_max:.2f}, "
                       f"not 0 to 1.")
            if lines:
                caption += " Dashed horizontal lines mark " + txt._join_series(
                    [ln["label"].lower().replace("(", "at ").replace(")", "") for ln in lines]) + "."
            if outside:
                caption += f" {txt._join_series(outside).capitalize()} {'lies' if len(outside) == 1 else 'lie'} outside the plotted range."
            blocks.append({
                "kind": "figure", "number": fig_n, "caption": _ascii(caption),
                "chart": {"type": "line", "quarters": [txt.qlabel(q) for q in window],
                          "series": [{"name": _ascii(s["name"]), "values": [p["value"] for p in s["points"]]}
                                     for s in plotted],
                          "yMin": y_min, "yMax": y_max, "yStep": step, "lines": lines},
            })
        else:
            blocks.append(_p(f"Figure {fig_n} is not shown: no published Risk Level score lies in the range."))
        blocks.append(_p(txt.compose_trend_interpretation(
            [{"name": s["name"], "points": s["points"]} for s in plotted], first_q, last_q, high, alert)))

        sec += 1
        blocks.append(_h(f"{sec}. Provincial Summary"))
        tab_n += 1
        rows = []
        for r in prov_rows:
            if r["withheldLatest"]:
                rows.append([r["name"], txt.score(r["start"]) if r["start"] is not None else "--",
                             "Withheld", "--", "--", "Withheld from publication",
                             f"{r['alerts']} of {r['published']}", "--"])
                continue
            end_v = r["end"]
            rows.append([
                r["name"],
                txt.score(r["start"]) if r["start"] is not None else "--",
                txt.score(end_v) if end_v is not None else "--",
                txt.signed(txt.rounded_change(r["start"], end_v)) if r["start"] is not None and end_v is not None else "--",
                f"{ranks[r['id']]} of {len(rank_pool)}" if r["id"] in ranks else "--",
                txt.status(end_v, high, alert) if end_v is not None else "--",
                f"{r['alerts']} of {r['published']}",
                f"{r['top']['label']} ({r['top']['pct']}%, {txt.direction_word(r['top']['direction'])})"
                if r["top"] else "No SHAP breakdown",
            ])
        if municipal:
            mp = [p for p in municipal["points"] if p["value"] is not None]
            rows.append([municipal["name"],
                         txt.score(mp[0]["value"]) if mp else "--",
                         txt.score(mp[-1]["value"]) if mp else "--",
                         txt.signed(txt.rounded_change(mp[0]["value"], mp[-1]["value"])) if len(mp) > 1 else "--",
                         "--", txt.status(mp[-1]["value"], high, alert) if mp else "--",
                         f"{sum(1 for p in mp if p['value'] >= alert)} of {len(mp)}", "As province"])
        blocks.append(_table(
            tab_n,
            f"Table {tab_n}. Provincial summary, {txt.qlabel(first_q)} to {txt.qlabel(last_q)}. "
            f"Start and end are each province's first and last published scores in the range; "
            f"rank and status refer to {txt.qlabel(last_q)}.",
            [("Province", "left", 0.14), ("Start", "right", 0.08), ("End", "right", 0.08),
             ("Change", "right", 0.09), ("Rank", "center", 0.08), ("Status", "left", 0.16),
             ("Quarters at or above alert", "center", 0.13), ("Top SHAP driver", "left", 0.24)],
            rows,
            note=(f"Status uses the unrounded score against the high-risk line ({high:.2f}) and "
                  f"the alert threshold ({alert:.2f})."),
        ))

    # ---- Drivers
    sec += 1
    blocks.append(_h(f"{sec}. Drivers of the {'Latest ' if kind == TREND else ''}Forecast (SHAP)"))
    fig_n += 1
    if kind == TREND and scope == "region":
        if region and region["triggers"]:
            excluded = [names[s] for s in slugs if s in withheld[last_q]]
            cap = (f"Figure {fig_n}. SHAP contribution of driver groups to the Risk Level score, pooled "
                   f"across {region['provincesIncluded']} published provinces, {txt.qlabel(last_q)}.")
            if excluded:
                cap += f" {txt._join_series(excluded)} {'is' if len(excluded) == 1 else 'are'} withheld from publication and excluded."
            blocks.append({"kind": "figure", "number": fig_n, "caption": _ascii(cap + _bar_key()),
                           "chart": _bars(region["triggers"])})
        else:
            blocks.append(_p(f"No regional SHAP breakdown is available for {txt.qlabel(last_q)}."))
    else:
        s0 = slugs[0]
        e = latest_explain[s0]
        if e and e["triggers"]:
            blocks.append({"kind": "figure", "number": fig_n,
                           "caption": _ascii(f"Figure {fig_n}. SHAP contribution of driver groups to the "
                                             f"Risk Level score for {names[s0]}, {txt.qlabel(last_q)}."
                                             + _bar_key()),
                           "chart": _bars(e["triggers"])})
        elif s0 in withheld[last_q]:
            blocks.append(_p(f"The SHAP breakdown for {names[s0]} in {txt.qlabel(last_q)} is withheld from publication."))
        else:
            blocks.append(_p(f"No SHAP breakdown is available for {names[s0]} in {txt.qlabel(last_q)}."))

    # Table 2: per-province shares and directions.
    labels: list[str] = []
    for s in slugs:
        e = latest_explain[s]
        for t in (e["triggers"] if e else []):
            if t["label"] not in labels:
                labels.append(t["label"])
    tab_n += 1
    if labels:
        rows = []
        for s in slugs:
            e = latest_explain[s]
            if s in withheld[last_q]:
                rows.append([names[s]] + ["Withheld"] + ["--"] * (len(labels) - 1) + ["--"])
            elif not e or not e["triggers"]:
                rows.append([names[s]] + ["n/a"] * len(labels) + ["n/a"])
            else:
                by = {t["label"]: t for t in e["triggers"]}
                rows.append([names[s]] + [_trigger_cell(by.get(lab)) for lab in labels]
                            + [f"{e['otherPct']}%"])
        width = 0.76 / (len(labels) + 1)
        blocks.append(_table(
            tab_n,
            f"Table {tab_n}. Driver-group shares of the attributed SHAP output, {txt.qlabel(last_q)}. "
            f"'+' marks a group that increases the predicted Risk Level score and '-' one that "
            f"decreases it. Group shares sum to 100%; 'Other' is the share of the total explained "
            f"output from the Food Stress Sentiment Index features, outside the five groups.",
            [("Province", "left", 0.24)] + [(lab, "center", width) for lab in labels]
            + [("Other", "center", width)],
            rows,
        ))
    else:
        blocks.append(_p(f"No SHAP breakdown is available for any covered province in {txt.qlabel(last_q)}."))

    blocks.append(_h("Interpretation by province" if len(slugs) > 1 else "Interpretation", 2))
    for s in slugs:
        e = latest_explain[s]
        if len(slugs) > 1:
            blocks.append(_h(names[s], 3))
        blocks.append(_p(svc.compose_formal_interpretation(
            names[s], last_q, e["triggers"] if e else [], e["otherPct"] if e else 0.0,
            withheld=s in withheld[last_q], brief=len(slugs) > 1)))

    if compare_q and compare_q != last_q:
        blocks.append(_h(f"Change in drivers, {txt.qlabel(compare_q)} to {txt.qlabel(last_q)}", 2))
        for s in slugs:
            ce = compare_explain.get(s)
            le = latest_explain[s]
            blocks.append(_p(txt.compose_driver_change(
                names[s], compare_q, last_q,
                ce["triggers"] if ce else None, le["triggers"] if le else None,
                withheld_first=_is_withheld(rejected, s, compare_q),
                withheld_last=s in withheld[last_q])))

    # ---- News evidence
    sec += 1
    blocks.append(_h(f"{sec}. Supporting News Evidence"))
    article_rows = []
    news_rows = []
    flagged: list[tuple[str, int]] = []
    single = len(slugs) == 1
    for s in slugs:
        held = s in withheld[last_q]
        e = latest_explain[s]
        top = e["triggers"][0] if e and e["triggers"] else None
        row = summaries[last_q].get(s) or {}
        matched = []
        count = 0
        if not held:
            news = svc.news(codes[s], last_q, 1, 1000)
            count = news["articleCount"]
            if top is not None:
                for a in news["data"]:
                    if top["key"] in classify_triggers(f"{a['title']} {a['excerpt']}"):
                        matched.append(a)
                    if len(matched) == 3:
                        break
            if row.get("limitedSignal"):
                flagged.append((names[s], count))
        for a in matched:
            article_rows.append([names[s], top["label"], a["title"], a["source"], a["date"] or "--"])
        if single:
            blocks.append(_p(txt.compose_news_evidence(
                names[s], last_q, count, e["triggerMatchedArticles"] if e else 0, top, matched,
                bool(row.get("limitedSignal")) and not held, withheld=held)))
        elif held:
            news_rows.append([names[s], "Withheld", "--", "--", "--", "--"])
        else:
            news_rows.append([
                names[s], str(count), str(e["triggerMatchedArticles"]) if e else "n/a",
                top["label"] if top else "No SHAP breakdown",
                str(len(matched)) if top else "--",
                "Yes" if row.get("limitedSignal") else "No",
            ])
    if not single:
        tab_n += 1
        blocks.append(_table(
            tab_n,
            f"Table {tab_n}. News evidence by province, {txt.qlabel(last_q)}. Articles: relevant "
            f"articles geocoded to the province (articleCount). Trigger tally: keyword-matched "
            f"articles recorded behind the model's news inputs (triggerMatchedArticles). Matching "
            f"top driver: articles, of the province's own, on which the top driver group's keyword "
            f"classifier fires.",
            [("Province", "left", 0.17), ("Articles", "center", 0.12), ("Trigger tally", "center", 0.14),
             ("Top driver group", "left", 0.25), ("Matching top driver", "center", 0.16),
             ("Limited signal", "center", 0.16)],
            news_rows,
        ))
        note = txt.compose_limited_signal_note(last_q, flagged)
        if note:
            blocks.append(_p(note))
        if not article_rows:
            blocks.append(_p(f"No article geocoded to a covered province in {txt.qlabel(last_q)} "
                             f"matches that province's top driver group, so no articles are listed."))
    if article_rows:
        tab_n += 1
        blocks.append(_table(
            tab_n,
            f"Table {tab_n}. News articles matching each province's top driver group, "
            f"{txt.qlabel(last_q)}, most recent first (up to three per province). An article "
            f"matches when the driver group's keyword classifier, the one that produced the "
            f"model's trigger inputs, fires on its title and lead.",
            [("Province", "left", 0.12), ("Driver group", "left", 0.15), ("Title", "left", 0.45),
             ("Source", "left", 0.16), ("Date", "left", 0.12)],
            article_rows,
            note="The corpus is machine-selected and not hand-verified; treat individual headlines as leads.",
        ))

    # ---- Provincial context
    sec += 1
    blocks.append(_h(f"{sec}. Provincial Context"))
    tab_n += 1
    ctx_rows = []
    for s in slugs:
        row = summaries[last_q].get(s) or {}
        held = s in withheld[last_q]
        ctx_rows.append([
            names[s],
            f"{row['population']:,}" if row.get("population") is not None else "n/a",
            f"{row['povertyRate']}%" if row.get("povertyRate") is not None else "n/a",
            "Withheld" if held else (
                f"{row['seriesAtRisk']} of {row['seriesMonitored']}"
                if row.get("seriesMonitored") is not None else "n/a"),
        ])
    monitored = {(summaries[last_q].get(s) or {}).get("seriesMonitored") for s in slugs}
    note = None
    if monitored == {1}:
        note = (f"The served model predicts at province level and monitors one series per "
                f"province, so 'at risk' is 1 when the province's score reaches the model's "
                f"decision threshold ({_model_meta()['decisionThreshold']:.3f}) and 0 otherwise.")
    blocks.append(_table(
        tab_n,
        f"Table {tab_n}. Provincial context, {txt.qlabel(last_q)}. Population: PSA 2020 Census "
        f"of Population and Housing. Poverty incidence: PSA 2021, mean of the province's LGU "
        f"estimates. Series at risk: model output (province_summary).",
        [("Province", "left", 0.25), ("Population (2020 CPH)", "right", 0.25),
         ("Poverty incidence (PSA 2021)", "right", 0.25), ("Series at risk / monitored", "center", 0.25)],
        ctx_rows, note=note,
    ))

    # ---- Model reliability
    sec += 1
    blocks.append(_h(f"{sec}. Model Reliability"))
    perf = svc.model_performance()
    for sentence in txt.compose_reliability(perf):
        blocks.append(_p(sentence))
    if perf:
        tab_n += 1
        base, skill = perf.get("baselines", {}), perf.get("skill", {})

        def m(v):
            return "Not reported" if v is None else f"{v:.4f}"
        blocks.append(_table(
            tab_n, f"Table {tab_n}. Model performance as reported by the backend "
                   f"(evaluation set of {perf.get('n', 'n/a')} province-quarters).",
            [("Measure", "left", 0.6), ("Value", "right", 0.4)],
            [["Accuracy", m(perf.get("accuracy"))],
             ["Precision (shock class)", m(perf.get("precision"))],
             ["Recall (shock class)", m(perf.get("recall"))],
             ["F1 (shock class)", m(perf.get("f1"))],
             ["ROC AUC", m(perf.get("rocAuc"))],
             ["Majority-class baseline", m(base.get("majorityClass"))],
             ["Seasonal-persistence baseline", m(base.get("seasonalPersistence"))],
             ["Margin over majority class",
              "Not reported" if skill.get("vsMajority") is None else f"{skill['vsMajority']:+.4f}"],
             ["Margin over seasonal persistence",
              "Not reported" if skill.get("vsSeasonal") is None else f"{skill['vsSeasonal']:+.4f}"]],
        ))

    # ---- Scope and limitations
    sec += 1
    blocks.append(_h(f"{sec}. Scope and Limitations"))
    for item in txt.compose_limitations(latest_published, lag, _unemployment_note(latest_published),
                                        POVERTY_WEIGHT, DENSITY_WEIGHT, ACTIONS_PLACEHOLDER,
                                        municipal is not None):
        blocks.append({"kind": "item", "title": item["title"], "text": item["text"]})

    # ---- Appendix
    method = txt.compose_method(_model_meta(), _sources(),
                                {"high": high, "alert": alert, "evenShare": ref.TRIGGER_RED_CUTOFF},
                                LABEL_RULE)
    blocks.append(_h("Appendix A. Data Sources and Method"))
    blocks.append(_h("Data sources", 2))
    blocks.append({"kind": "bullets", "items": method["sources"]})
    blocks.append(_h("Model", 2))
    blocks.append(_p(method["model"]))
    blocks.append(_h("Explanation method", 2))
    blocks.append(_p(method["explanation"]))
    blocks.append(_h("Definition of the Risk Level score", 2))
    blocks.append(_p(method["definition"]))

    area = ("All provinces (" + ", ".join(names[s] for s in slugs) + ")" if scope == "region"
            else names[slugs[0]] + (f" / {municipal['name'].split(' (')[0]}" if municipal else ""))
    period = (txt.qlabel(last_q) if kind == SHAP
              else f"{txt.qlabel(first_q)} to {txt.qlabel(last_q)}")
    return {
        "type": kind,
        "scope": scope,
        "title": REPORT_TITLE,
        "subtitle": SUBTITLES[kind],
        "generated": _ascii(f"{generated.day} {generated:%B %Y}, {generated:%H:%M} (UTC+08:00)"),
        "generatedDate": _ascii(f"{generated.day} {generated:%B %Y}"),
        "metadata": [
            ["Area", _ascii(area)],
            ["Quarter" if kind == SHAP else "Date range", period],
            ["Data vintage", _ascii(f"{txt.qlabel(latest_published)} (latest quarter with published "
                                    f"input data); {txt.plural(lag, 'quarter')} behind the calendar "
                                    f"quarter {txt.qlabel(calendar)}")],
            ["Generated", _ascii(f"{generated.day} {generated:%B %Y}, {generated:%H:%M} (UTC+08:00)")],
            ["Prepared for", PREPARED_FOR],
        ],
        "vintage": vintage_text,
        "blocks": blocks,
    }


def _bar_key() -> str:
    return (f" Bars above the {ref.TRIGGER_RED_CUTOFF}% even-share line (dashed) are red where the "
            f"group increases the predicted Risk Level score and yellow where it decreases it; bars "
            f"at or below the line are orange. Each bar is labelled with its share and direction.")


def _withheld_at(rejected: set[tuple[str, str]], quarter: str | None) -> frozenset[str]:
    return frozenset(pid for pid, rq in rejected if rq == quarter)


def _is_withheld(rejected: set[tuple[str, str]], slug: str, quarter: str | None) -> bool:
    return quarter is not None and (slug, quarter) in rejected
