"""
app/services/report_text.py
----------------------------
Formal sentences for the Visualization page's PDF reports.

Every function here takes data already produced by the model, the SHAP
explainer or the backend's reference tables, and returns plain-ASCII prose.
Sentence structures are fixed; every finding inside them (which province,
which driver, every number, every direction) is filled from the arguments.
Where a value is missing the sentence says so, or is omitted, rather than
falling back to generic text. A province-quarter withheld by a reviewer is
reported only as "withheld from publication" -- no score, share or driver.

Pure functions with no model or file access, so each is unit-tested directly
(tests/unit/test_report_text.py). report_data.py gathers the inputs.
"""

from __future__ import annotations

from app.services.dashboard import _ascii, _join_series

# Same tolerance the dashboard used to call a trend flat: changes smaller than
# this, at three decimals, are reported as approximately unchanged.
FLAT = 0.0005


def qlabel(quarter: str) -> str:
    """'2026-Q3' -> '2026 Q3'."""
    return quarter.replace("-", " ")


def score(value: float) -> str:
    """Risk Level scores are printed at three decimals throughout the report."""
    return f"{value:.3f}"


def signed(value: float) -> str:
    return f"{'+' if value >= 0 else '-'}{abs(value):.3f}"


def rounded_change(start: float, end: float) -> float:
    """Change between two scores as printed, so the stated arithmetic adds up."""
    return round(round(end, 3) - round(start, 3), 3)


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def effect(direction: str) -> str:
    return ("increases the predicted Risk Level score" if direction == "increases_risk"
            else "decreases the predicted Risk Level score")


def direction_word(direction: str) -> str:
    return "increases" if direction == "increases_risk" else "decreases"


def status(value: float, high: float, alert: float) -> str:
    """Status against the dashboard's two reference lines, on the unrounded score."""
    if value >= alert:
        return "at or above alert"
    if value >= high:
        return "high-risk"
    return "below high-risk line"


# ---------------------------------------------------------------------------
# Data vintage
# ---------------------------------------------------------------------------

def compose_vintage(latest: str, calendar: str, lag: int,
                    missing: dict[str, list[str]], n_provinces: int) -> str:
    """
    The newest quarter with published input data, its lag behind the calendar,
    and which model inputs are absent for that quarter.

    `missing` maps an input's display name to the provinces lacking it in
    `latest`, as read from the model panel.
    """
    if lag <= 0:
        lead = (f"The latest quarter with published input data is {qlabel(latest)}, "
                f"which is the current calendar quarter.")
    else:
        lead = (f"The latest quarter with published input data is {qlabel(latest)}, "
                f"{plural(lag, 'quarter')} behind the calendar quarter ({qlabel(calendar)}).")
    if not missing:
        return _ascii(lead + f" All model inputs are present for {qlabel(latest)}.")

    parts = []
    for name, provinces in missing.items():
        who = (f"all {n_provinces} provinces" if len(provinces) == n_provinces
               else _join_series(provinces))
        parts.append(f"{name} ({who})")
    return _ascii(
        f"{lead} In {qlabel(latest)}, the following model inputs are not yet available: "
        f"{_join_series(parts)}. The LightGBM component scores those province-quarters "
        f"with the inputs treated as missing, and the logistic-regression components "
        f"substitute zero for them."
    )


# ---------------------------------------------------------------------------
# Summary of findings
# ---------------------------------------------------------------------------

def compose_summary(rows: list[dict], region_top: dict | None, start: str, end: str,
                    high: float, alert: float) -> list[str]:
    """
    Three to five sentences for the top of a multi-province report.

    rows: one per province, {name, start, end, withheldLatest} where start/end
          are the first and last published scores in the range (None if none).
    region_top: the dominant pooled driver group in `end`
          ({label, pct, direction}), or None if no regional breakdown exists.
    """
    out = []
    latest = [r for r in rows if not r["withheldLatest"] and r["end"] is not None]
    withheld = [r["name"] for r in rows if r["withheldLatest"]]
    n = len(latest)

    if n == 0:
        out.append(f"No province has a published Risk Level score for {qlabel(end)}.")
    else:
        above = [r["name"] for r in latest if r["end"] >= alert]
        if above:
            out.append(
                f"In {qlabel(end)}, {len(above)} of {n} published provinces "
                f"{'is' if len(above) == 1 else 'are'} at or above the alert threshold of "
                f"{alert:.2f}: {_join_series(above)}."
            )
        else:
            out.append(f"In {qlabel(end)}, none of the {n} published provinces is at or "
                       f"above the alert threshold of {alert:.2f}.")
    if withheld:
        out.append(f"{_join_series(withheld)} {'is' if len(withheld) == 1 else 'are'} "
                   f"withheld from publication for {qlabel(end)} and excluded from these findings.")

    if n >= 2:
        hi = max(latest, key=lambda r: r["end"])
        lo = min(latest, key=lambda r: r["end"])
        out.append(f"The highest Risk Level score in {qlabel(end)} is recorded for {hi['name']} "
                   f"({score(hi['end'])}) and the lowest for {lo['name']} ({score(lo['end'])}).")

    moved = [r for r in rows if r["start"] is not None and r["end"] is not None
             and r.get("startQuarter") != r.get("endQuarter")]
    if moved and start != end:
        big = max(moved, key=lambda r: abs(rounded_change(r["start"], r["end"])))
        d = rounded_change(big["start"], big["end"])
        if abs(d) < FLAT:
            out.append(f"Between {qlabel(start)} and {qlabel(end)}, no province's Risk Level "
                       f"score changed by more than 0.001.")
        else:
            out.append(f"Between {qlabel(start)} and {qlabel(end)}, the largest change is "
                       f"observed for {big['name']} ({signed(d)}, from {score(big['start'])} in "
                       f"{qlabel(big['startQuarter'])} to {score(big['end'])} in "
                       f"{qlabel(big['endQuarter'])}).")

    if region_top is None:
        out.append(f"No regional SHAP breakdown is available for {qlabel(end)}.")
    else:
        out.append(f"Across the published provinces in {qlabel(end)}, the dominant SHAP driver "
                   f"group is {region_top['label']} ({region_top['pct']}% of the attributed "
                   f"share), which {effect(region_top['direction'])} on balance.")
    return [_ascii(s) for s in out]


def compose_province_summary(name: str, quarter: str, value: float | None, withheld: bool,
                             rank: int | None, n_published: int, top: dict | None,
                             article_count: int | None, high: float, alert: float) -> list[str]:
    """Summary of findings for a single-province, single-quarter report."""
    if withheld:
        return [_ascii(f"The {qlabel(quarter)} forecast for {name} is withheld from "
                       f"publication by a reviewer; no score or driver breakdown is reported.")]
    if value is None:
        return [_ascii(f"No Risk Level score is available for {name} in {qlabel(quarter)}.")]
    out = [f"In {qlabel(quarter)}, the Risk Level score for {name} is {score(value)}, "
           f"{_status_phrase(value, high, alert)}."]
    if rank is not None:
        out.append(f"{name} ranks {rank} of {n_published} published provinces in {qlabel(quarter)}.")
    if top is None:
        out.append(f"No SHAP breakdown is available for {name} in {qlabel(quarter)}.")
    else:
        out.append(f"The dominant SHAP driver group is {top['label']} ({top['pct']}% of the "
                   f"attributed share), which {effect(top['direction'])}.")
    if article_count is not None:
        out.append(f"{plural(article_count, 'relevant news article')} "
                   f"{'was' if article_count == 1 else 'were'} geocoded to {name} for the quarter.")
    return [_ascii(s) for s in out]


def _status_phrase(value: float, high: float, alert: float) -> str:
    if value >= alert:
        return f"at or above both the high-risk line ({high:.2f}) and the alert threshold ({alert:.2f})"
    if value >= high:
        return f"at or above the high-risk line ({high:.2f}) but below the alert threshold ({alert:.2f})"
    return f"below the high-risk line ({high:.2f})"


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------

def compose_trend_interpretation(series: list[dict], start: str, end: str,
                                 high: float, alert: float) -> str:
    """
    Third-person reading of the trend figure.

    series: [{name, points: [{quarter, value | None, withheld}]}]. Each series
    is read from its own first and last published quarter, so a withheld or
    missing quarter is never read as zero.
    """
    stats = []
    gaps = []
    for s in series:
        pts = [p for p in s["points"] if p["value"] is not None]
        held = [p["quarter"] for p in s["points"] if p.get("withheld")]
        if held:
            gaps.append(f"{s['name']} ({_join_series([qlabel(q) for q in held])})")
        if not pts:
            continue
        first, last = pts[0], pts[-1]
        stats.append({
            "name": s["name"], "pts": pts, "first": first, "last": last,
            "delta": rounded_change(first["value"], last["value"]),
            "peak": max(pts, key=lambda p: p["value"]),
            "trough": min(pts, key=lambda p: p["value"]),
            "alerts": sum(1 for p in pts if p["value"] >= alert),
        })

    if not stats:
        return _ascii(f"No published Risk Level scores are available between {qlabel(start)} "
                      f"and {qlabel(end)}; consequently, no trend can be interpreted.")

    def move(s: dict) -> str:
        return (f"{score(s['first']['value'])} in {qlabel(s['first']['quarter'])} to "
                f"{score(s['last']['value'])} in {qlabel(s['last']['quarter'])}")

    out = []
    if len(stats) == 1:
        s = stats[0]
        if len(s["pts"]) < 2:
            out.append(f"Only one published quarter ({qlabel(s['first']['quarter'])}) is "
                       f"available for {s['name']}, at a Risk Level score of "
                       f"{score(s['first']['value'])}; no trend can therefore be established.")
        else:
            verb = ("increased" if s["delta"] >= FLAT else
                    "decreased" if s["delta"] <= -FLAT else "remained approximately unchanged")
            out.append(f"The Risk Level score for {s['name']} {verb} from {move(s)}, a net "
                       f"change of {signed(s['delta'])} across {plural(len(s['pts']), 'published quarter')}.")
            if s["peak"]["value"] != s["trough"]["value"]:
                out.append(f"It reached its highest value of {score(s['peak']['value'])} in "
                           f"{qlabel(s['peak']['quarter'])} and its lowest value of "
                           f"{score(s['trough']['value'])} in {qlabel(s['trough']['quarter'])}.")
            out.append(f"The score was at or above the alert threshold of {alert:.2f} in "
                       f"{s['alerts']} of {len(s['pts'])} published quarters.")
    else:
        groups = {"increased": [], "decreased": [], "flat": []}
        for s in stats:
            key = "increased" if s["delta"] >= FLAT else "decreased" if s["delta"] <= -FLAT else "flat"
            span = ""
            if (s["first"]["quarter"], s["last"]["quarter"]) != (start, end):
                # A withheld or missing end point: say which quarters the change spans.
                span = f", {qlabel(s['first']['quarter'])} to {qlabel(s['last']['quarter'])}"
            groups[key].append(f"{s['name']} ({signed(s['delta'])}{span})")
        clauses = []
        if groups["increased"]:
            clauses.append(f"increased for {_join_series(groups['increased'])}")
        if groups["decreased"]:
            clauses.append(f"decreased for {_join_series(groups['decreased'])}")
        if groups["flat"]:
            clauses.append(f"remained approximately unchanged for {_join_series(groups['flat'])}")
        joined = clauses[0] if len(clauses) == 1 else f"{'; '.join(clauses[:-1])}; and {clauses[-1]}"
        out.append(f"Between {qlabel(start)} and {qlabel(end)}, the Risk Level score {joined}.")
        peak = max(stats, key=lambda s: s["peak"]["value"])
        out.append(f"The highest score in the period is {score(peak['peak']['value'])}, recorded "
                   f"for {peak['name']} in {qlabel(peak['peak']['quarter'])}.")
        always = [s["name"] for s in stats if s["alerts"] == len(s["pts"])]
        if always and len(always) == len(stats):
            out.append(f"Every province remained at or above the alert threshold of {alert:.2f} "
                       f"in each of its published quarters.")
        elif always:
            out.append(f"{_join_series(always)} remained at or above the alert threshold of "
                       f"{alert:.2f} in every published quarter.")

    if gaps:
        out.append(f"Quarters withheld from publication are omitted from the series: {_join_series(gaps)}.")
    return _ascii(" ".join(out))


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

def compose_driver_change(name: str, from_q: str, to_q: str,
                          first: list[dict] | None, last: list[dict] | None,
                          withheld_first: bool = False, withheld_last: bool = False) -> str:
    """
    Which driver groups gained or lost the most share between two quarters,
    and any group whose direction reversed.
    """
    if withheld_first or withheld_last:
        held = _join_series([qlabel(q) for q, w in ((from_q, withheld_first), (to_q, withheld_last)) if w])
        return _ascii(f"The driver comparison for {name} is not reported because the {held} "
                      f"forecast is withheld from publication.")
    if not first or not last:
        missing = _join_series([qlabel(q) for q, t in ((from_q, first), (to_q, last)) if not t])
        return _ascii(f"No SHAP breakdown is available for {name} in {missing}, so the change "
                      f"in drivers cannot be assessed.")

    before = {t["label"]: t for t in first}
    after = {t["label"]: t for t in last}
    labels = [lab for lab in after if lab in before]
    deltas = {lab: after[lab]["pct"] - before[lab]["pct"] for lab in labels}
    if not deltas:
        return _ascii(f"The driver groups for {name} in {qlabel(from_q)} and {qlabel(to_q)} "
                      f"do not overlap, so no comparison can be made.")

    gain = max(deltas, key=lambda k: deltas[k])
    loss = min(deltas, key=lambda k: deltas[k])
    out = []
    if deltas[gain] <= 0 and deltas[loss] >= 0:
        out.append(f"Between {qlabel(from_q)} and {qlabel(to_q)}, the driver-group shares for "
                   f"{name} are unchanged.")
    else:
        if deltas[gain] > 0:
            out.append(f"Between {qlabel(from_q)} and {qlabel(to_q)}, {gain} gained the most "
                       f"share for {name} (+{deltas[gain]} percentage points, from "
                       f"{before[gain]['pct']}% to {after[gain]['pct']}%).")
        if deltas[loss] < 0:
            out.append(f"{loss} lost the most ({deltas[loss]} percentage points, from "
                       f"{before[loss]['pct']}% to {after[loss]['pct']}%).")
    flipped = [lab for lab in labels if before[lab]["direction"] != after[lab]["direction"]
               and (before[lab]["pct"] or after[lab]["pct"])]
    for lab in flipped:
        out.append(f"{lab} changed from {direction_word(before[lab]['direction'])} to "
                   f"{direction_word(after[lab]['direction'])} the predicted Risk Level score.")
    return _ascii(" ".join(out))


# ---------------------------------------------------------------------------
# News evidence
# ---------------------------------------------------------------------------

def compose_news_evidence(name: str, quarter: str, article_count: int,
                          matched_count: int, top: dict | None, articles: list[dict],
                          limited_signal: bool, withheld: bool = False) -> str:
    """
    Article counts for a province-quarter, the articles matching its top
    driver, and the limited-signal note when the model flags one.
    """
    if withheld:
        return _ascii(f"News evidence for {name} in {qlabel(quarter)} is not reported because "
                      f"the forecast is withheld from publication.")
    out = [f"{plural(article_count, 'relevant article')} "
           f"{'was' if article_count == 1 else 'were'} geocoded to {name} for {qlabel(quarter)}; "
           f"the trigger tally behind the model's news inputs records {matched_count} "
           f"keyword-matched {'article' if matched_count == 1 else 'articles'} for this province-quarter."]
    if top is None:
        out.append(f"No SHAP breakdown is available for {name} in {qlabel(quarter)}, so no "
                   f"articles are matched to a top driver.")
    elif articles:
        out.append(f"{plural(len(articles), 'article')} matching the top driver group, "
                   f"{top['label']}, {'is' if len(articles) == 1 else 'are'} listed below.")
    else:
        out.append(f"None of these articles matches the top driver group, {top['label']}.")
    if limited_signal:
        out.append(f"{name} is flagged as limited signal for {qlabel(quarter)}: at least one "
                   f"news-derived model input is missing for this province-quarter, and "
                   f"{plural(article_count, 'relevant article')} "
                   f"{'was' if article_count == 1 else 'were'} geocoded to it. News-derived "
                   f"drivers should be treated as weak evidence.")
    return _ascii(" ".join(out))


# ---------------------------------------------------------------------------
# Model reliability
# ---------------------------------------------------------------------------

def _m(value: float | None) -> str | None:
    return None if value is None else f"{value:.4f}"


def compose_reliability(perf: dict) -> list[str]:
    """Headline metrics quoted against the baselines the backend reports."""
    if perf and "leads" in perf:                      # thesis system
        from app.ml.inference import thesis_system as THESIS
        return THESIS.performance_tables(perf)["sentences"]
    if not perf or perf.get("accuracy") is None:
        return ["Model performance figures are not available from the results file."]
    base = perf.get("baselines", {})
    skill = perf.get("skill", {})
    out = []
    n = perf.get("n")
    lead = f"On the evaluation set of {n} province-quarters" if n else "On the evaluation set"
    acc = f"{lead}, the model's accuracy is {_m(perf['accuracy'])}"
    if base.get("majorityClass") is not None:
        acc += (f", against a majority-class baseline of {_m(base['majorityClass'])}"
                + (f" (a margin of {skill['vsMajority']:+.4f})" if skill.get("vsMajority") is not None else ""))
    out.append(acc + ".")
    if base.get("seasonalPersistence") is not None:
        out.append(f"A seasonal-persistence baseline scores {_m(base['seasonalPersistence'])}"
                   + (f" (a margin of {skill['vsSeasonal']:+.4f})." if skill.get("vsSeasonal") is not None else "."))
    else:
        out.append("A seasonal-persistence baseline is not reported in the results file for "
                   "this model, so no comparison against it can be made.")
    pr = [f"precision {_m(perf['precision'])}" if perf.get("precision") is not None else None,
          f"recall {_m(perf['recall'])}" if perf.get("recall") is not None else None,
          f"F1 {_m(perf['f1'])}" if perf.get("f1") is not None else None]
    pr = [x for x in pr if x]
    if pr:
        out.append(f"For the shock (positive) class, the model reports {_join_series(pr)}.")
    if perf.get("rocAuc") is not None:
        out.append(f"The ROC AUC is {_m(perf['rocAuc'])}.")
    if base.get("majorityClass") is not None and skill.get("vsMajority") is not None:
        out.append(f"Because the majority class alone already reaches {_m(base['majorityClass'])}, "
                   f"accuracy should be read together with the class-specific figures above.")
    return [_ascii(s) for s in out]


# ---------------------------------------------------------------------------
# Scope and limitations
# ---------------------------------------------------------------------------

def compose_limitations(latest: str, lag: int, unemployment_note: str | None,
                        poverty_weight: float, density_weight: float,
                        actions_statement: str, includes_municipal: bool) -> list[dict]:
    """
    The limits of the report, reusing report.py's reasoning. `actions_statement`
    is report.ACTIONS_PLACEHOLDER, passed in so the position stays in one place.
    """
    items = [
        {"title": "Same-quarter nowcast",
         "text": (f"Scores describe quarters for which input data have been published. "
                  f"The latest such quarter is {qlabel(latest)}"
                  + (f", {plural(lag, 'quarter')} behind the calendar quarter" if lag > 0 else "")
                  + ". The report does not project beyond it.")},
        {"title": "A food-price stress signal, not a hunger estimate",
         "text": ("The Risk Level score is a model probability for a food-price stress label "
                  "derived from the food consumer price index. It does not measure whether "
                  "households went hungry and should not be read as a hunger estimate.")},
    ]
    if unemployment_note:
        items.append({"title": "Shared regional inputs", "text": unemployment_note})
    items.append({
        "title": "Municipal values are disaggregated, not modelled",
        "text": (f"Municipal values reweight the province figure by poverty incidence "
                 f"({poverty_weight:.0%}) and population density ({density_weight:.0%}). "
                 f"They are not independent municipal forecasts: every municipality in a "
                 f"province rises and falls with it."
                 + (" The municipal series in this report should be read on that basis."
                    if includes_municipal else "")),
    })
    items.append({
        "title": "Reviewed before publication",
        "text": ("Province-quarter figures pass through analyst review. A figure withheld "
                 "from publication is excluded from every table, figure and finding in this "
                 "report, and from the regional SHAP breakdown."),
    })
    items.append({"title": "Findings only", "text": actions_statement})
    return [{"title": _ascii(i["title"]), "text": _ascii(i["text"])} for i in items]


# ---------------------------------------------------------------------------
# Data sources and method
# ---------------------------------------------------------------------------

def compose_method(model: dict, sources: list[str], thresholds: dict,
                   label_rule: str) -> dict:
    """
    The appendix: sources, model, explanation method and the score definition.

    model: {components: [(name, weight)], featureCount, label, trainedThrough,
            trainRows, decisionThreshold}
    thresholds: {high, alert, evenShare, limitedSignalMinArticles}
    """
    comps = _join_series([f"{name} ({weight:.0%})" for name, weight in model["components"]])
    model_text = (
        f"The served nowcast model is a weighted blend of {comps}, using "
        f"{model['featureCount']} province-quarter features. It was trained on "
        f"{model['trainRows']} province-quarter rows through {qlabel(model['trainedThrough'])} "
        f"with {model['label']} as the target."
    )
    shap_text = (
        "Driver contributions are SHAP values: a TreeExplainer for the LightGBM component and "
        "an exact Shapley decomposition for each logistic-regression component, each scaled by "
        "its blend weight and summed, so that the baseline plus all contributions equals the "
        "blended Risk Level score. Feature contributions are grouped into five driver groups; "
        "the shares shown are each group's absolute contribution as a percentage of the five "
        "groups' total, and the Food Stress Sentiment Index features are reported separately "
        "as the 'other' share."
    )
    definition = (
        f"The Risk Level score is the served model's predicted probability, from 0 to 1, that "
        f"a province-quarter carries the training label: {label_rule} "
        f"The dashboard draws two reference lines: the high-risk line at {thresholds['high']:.2f} "
        f"(scores at or above it are treated as high risk in this report) and the alert "
        f"threshold at {thresholds['alert']:.2f} (scores at or above it raise an alert). "
        f"Separately, the model classifies a province-quarter as HIGH on the dashboard map "
        f"when its score reaches the model's own decision threshold of "
        f"{model['decisionThreshold']:.3f}. A driver group whose share exceeds "
        f"{thresholds['evenShare']}% (an even share among five groups) is treated as a major "
        f"driver, and a province-quarter is flagged as limited signal when a news-derived "
        f"input is missing."
    )
    return {
        "sources": [_ascii(s) for s in sources],
        "model": _ascii(model_text),
        "explanation": _ascii(shap_text),
        "definition": _ascii(definition),
    }


def compose_limited_signal_note(quarter: str, flagged: list[tuple[str, int]]) -> str | None:
    """
    One sentence for the provinces the model flags as limited signal, with
    each province's actual article count. None when no province is flagged.
    """
    if not flagged:
        return None
    names = _join_series([n for n, _ in flagged])
    counts = _join_series([str(c) for _, c in flagged])
    if len(flagged) == 1:
        (name, count), = flagged
        return _ascii(f"{name} is flagged as limited signal for {qlabel(quarter)}: at least one "
                      f"news-derived model input is missing for this province-quarter, and "
                      f"{plural(count, 'relevant article')} {'was' if count == 1 else 'were'} "
                      f"geocoded to it. Its news-derived drivers should be treated as weak evidence.")
    return _ascii(f"{names} are flagged as limited signal for {qlabel(quarter)}: at least one "
                  f"news-derived model input is missing for each of these province-quarters, and "
                  f"{counts} relevant articles respectively were geocoded to them. Their "
                  f"news-derived drivers should be treated as weak evidence.")
