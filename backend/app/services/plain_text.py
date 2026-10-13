"""
app/services/plain_text.py
---------------------------
Plain-language wording for the Visualization page's PDF reports, written for
DA Region IV-A agriculture officers rather than data scientists.

Same rule as report_text.py: sentence structures are fixed, every finding in
them is filled from model results passed in by the caller. Only the wording
is simpler. The technical wording in report_text.py and
dashboard.compose_formal_interpretation() is kept for other uses; these PDFs
no longer call it.

Conventions used throughout:
* risk scores at two decimals; changes computed from those rounded values so
  the arithmetic a reader does in their head agrees with the text;
* percentages as whole numbers;
* one risk scale (risk_level) built from the dashboard's own thresholds;
* plain factor names (PLAIN_FACTORS) in place of driver-group labels.

Plain ASCII only, for the same reason as compose_narrative().
"""

from __future__ import annotations

from app.services.dashboard import _ascii, _join_series

# One place for the factor names readers see. Keys are the driver-group keys
# the explainer returns.
PLAIN_FACTORS: dict[str, str] = {
    "market": "Food prices",
    "employment": "Jobs and employment",
    "climate": "Weather and climate",
    "fish_kill": "Fish kills",
    "ofw_remittance": "Remittances from OFWs",
}

LEVEL_ALERT, LEVEL_HIGH, LEVEL_NONE = "Alert", "High", "Not elevated"

# Factors measured only from news reports (every feature in their driver group
# is a news trigger; see THESIS_DRIVER_GROUP_FEATURES). When a quarter's news
# inputs are incomplete, their share reflects missing data, not "no effect".
NEWS_ONLY_FACTORS: frozenset[str] = frozenset({"climate", "fish_kill", "ofw_remittance"})

# What the score measures, in plain words. Checked against the training label
# in app/ml/features/label_generator.py::_build_cpi_labels: food CPI above its
# 24-quarter rolling mean plus one standard deviation for two consecutive
# quarters.
SCORE_EXPLAINER = (
    "The risk score ranges from 0 to 1. It estimates how likely it is that food prices "
    "in the province have been unusually high, compared with their usual level over the "
    "past six years, for two quarters in a row. A higher score means food prices are "
    "more likely to be under unusual pressure. It is not a measure of hunger."
)

_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
          7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def qlabel(quarter: str) -> str:
    return quarter.replace("-", " ")


def num(n: int) -> str:
    return _WORDS.get(n, str(n))


def count_lead(n: int, noun: str, plural_noun: str | None = None) -> str:
    """A count at the start of a sentence, spelled out: 'Four news reports'."""
    word = num(n) if n in _WORDS else str(n)
    word = "No" if n == 0 else word[:1].upper() + word[1:]
    return f"{word} {noun if n == 1 else (plural_noun or noun + 's')}"


def score(value: float) -> str:
    return f"{value:.2f}"


def r2(value: float) -> float:
    return round(value, 2)


def factor(key: str, label: str | None = None) -> str:
    return PLAIN_FACTORS.get(key, label or key)


def lower_first(text: str) -> str:
    """'Food prices' -> 'food prices', keeping acronyms such as 'OFWs'."""
    return text[:1].lower() + text[1:] if text and not text[:2].isupper() else text


def risk_level(value: float, high: float, alert: float) -> str:
    """The report's single risk scale, judged on the score as printed."""
    v = r2(value)
    if v >= alert:
        return LEVEL_ALERT
    if v >= high:
        return LEVEL_HIGH
    return LEVEL_NONE


def level_scale(high: float, alert: float) -> str:
    return _ascii(f"This report uses three risk levels: {LEVEL_ALERT} ({alert:.2f} and above), "
                  f"{LEVEL_HIGH} ({high:.2f} to below {alert:.2f}) and {LEVEL_NONE} "
                  f"(below {high:.2f}).")


def change_amount(start: float, end: float) -> float:
    return round(r2(end) - r2(start), 2)


def describe_change(start: float, end: float) -> str:
    """'decreased by 0.05 (from 0.78 to 0.73)' or 'stayed the same (0.73)'."""
    d = change_amount(start, end)
    if d == 0:
        return f"stayed the same ({score(end)})"
    word = "increased" if d > 0 else "decreased"
    return f"{word} by {abs(d):.2f} (from {score(start)} to {score(end)})"


def change_cell(start: float | None, end: float | None) -> str:
    """Short form for a table cell: 'Down 0.05', 'Up 0.02', 'No change'."""
    if start is None or end is None:
        return "Not available"
    d = change_amount(start, end)
    if d == 0:
        return "No change"
    return f"{'Up' if d > 0 else 'Down'} {abs(d):.2f}"


def effect_verb(direction: str, plural: bool = True) -> str:
    raise_, lower = ("raise", "lower") if plural else ("raises", "lowers")
    return raise_ if direction == "increases_risk" else lower


def withheld_sentence(names: list[str], quarter: str) -> str:
    return _ascii(f"Results for {_join_series(names)} in {qlabel(quarter)} are withheld by "
                  f"the reviewing team and are not shown in this report.")


def every(n: int, noun: str = "provinces") -> str:
    """'both provinces' / 'all five provinces'; callers handle n == 1 themselves."""
    return f"both {noun}" if n == 2 else f"all {num(n)} {noun}"


# ---------------------------------------------------------------------------
# Key points
# ---------------------------------------------------------------------------

def compose_key_points(rows: list[dict], end: str, compare_from: str | None,
                       high: float, alert: float) -> list[str]:
    """
    Three to five bullets for the top of the report.

    rows: {name, value (latest score or None), withheld, start (score at
           compare_from or None), mainKey, mainPct, mainDirection}
    compare_from: the quarter the change is measured from (the first quarter
           of a multi-quarter range, or the previous quarter otherwise).
    """
    out: list[str] = []
    shown = [r for r in rows if not r["withheld"] and r["value"] is not None]
    held = [r["name"] for r in rows if r["withheld"]]
    q = qlabel(end)

    if not shown:
        out.append(f"No risk scores are available for {q}.")
    elif len(rows) == 1:
        r = shown[0]
        level = risk_level(r["value"], high, alert)
        out.append(f"In {q}, the risk score for {r['name']} is {score(r['value'])}, which is "
                   + ("not elevated." if level == LEVEL_NONE else f"at the {level} level."))
    else:
        by_level = {lv: [r["name"] for r in shown if risk_level(r["value"], high, alert) == lv]
                    for lv in (LEVEL_ALERT, LEVEL_HIGH, LEVEL_NONE)}
        alert_names = by_level[LEVEL_ALERT]
        group = "provinces with results" if held else "provinces"
        if len(shown) == 1:
            r = shown[0]
            level = risk_level(r["value"], high, alert)
            out.append(f"In {q}, the risk score for {r['name']} is {score(r['value'])}, which is "
                       + ("not elevated." if level == LEVEL_NONE else f"at the {level} level."))
        elif len(alert_names) == len(shown):
            out.append(f"In {q}, {every(len(shown), group)} are at the Alert level.")
        else:
            lead = (f"In {q}, {num(len(alert_names))} of the {num(len(shown))} {group} "
                    f"{'is' if len(alert_names) == 1 else 'are'} at the Alert level"
                    + (f" ({_join_series(alert_names)})" if alert_names else "") + ".")
            rest = []
            if by_level[LEVEL_HIGH]:
                rest.append(f"{_join_series(by_level[LEVEL_HIGH])} "
                            f"{'is' if len(by_level[LEVEL_HIGH]) == 1 else 'are'} at the High level")
            if by_level[LEVEL_NONE]:
                rest.append(f"{_join_series(by_level[LEVEL_NONE])} "
                            f"{'is' if len(by_level[LEVEL_NONE]) == 1 else 'are'} not elevated")
            out.append(lead + (" " + "; ".join(rest) + "." if rest else ""))
        hi = max(shown, key=lambda r: r["value"])
        lo = min(shown, key=lambda r: r["value"])
        if r2(hi["value"]) != r2(lo["value"]):
            out.append(f"{hi['name']} has the highest risk score ({score(hi['value'])}) and "
                       f"{lo['name']} the lowest ({score(lo['value'])}).")

    with_factor = [r for r in shown if r.get("mainKey")]
    if with_factor:
        keys = {(r["mainKey"], r["mainDirection"]) for r in with_factor}
        if len(rows) == 1:
            r = with_factor[0]
            out.append(f"{factor(r['mainKey'])} are the main factor behind the score, accounting "
                       f"for about {r['mainPct']}% of the factors, and they "
                       f"{effect_verb(r['mainDirection'])} the risk.")
        elif len(keys) == 1:
            key, direction = keys.pop()
            where = "every province" if len(with_factor) == len(shown) else _join_series(
                [r["name"] for r in with_factor])
            out.append(f"{factor(key)} are the main factor behind the risk in {where}, and they "
                       f"{effect_verb(direction)} the risk.")
        else:
            groups: dict[str, list[str]] = {}
            for r in with_factor:
                groups.setdefault(factor(r["mainKey"]), []).append(r["name"])
            parts = [f"{lower_first(lab)} in {_join_series(names)}" for lab, names in groups.items()]
            out.append(f"The main factor differs by province: {_join_series(parts)}.")

    if compare_from:
        moved = [r for r in shown if r["start"] is not None]
        c = qlabel(compare_from)
        if len(rows) == 1 and moved:
            r = moved[0]
            out.append(f"Compared with {c}, the risk score {describe_change(r['start'], r['value'])}.")
        elif moved:
            ups = [r["name"] for r in moved if change_amount(r["start"], r["value"]) > 0]
            downs = [r["name"] for r in moved if change_amount(r["start"], r["value"]) < 0]
            same = [r["name"] for r in moved if change_amount(r["start"], r["value"]) == 0]
            parts = []
            for names, word in ((downs, "decreased"), (ups, "increased"), (same, "stayed the same")):
                if not names:
                    continue
                if len(names) == len(moved) and len(moved) > 1:
                    parts.append(f"{word} in {every(len(names))}")
                elif len(names) > len(moved) / 2 and len(names) > 1:
                    parts.append(f"{word} in {num(len(names))} provinces")
                else:
                    parts.append(f"{word} in {_join_series(names)}")
            out.append(f"Compared with {c}, the risk score {_join_series(parts)}.")
    if held:
        out.append(withheld_sentence(held, end))
    return [_ascii(s) for s in out]


# ---------------------------------------------------------------------------
# Risk at a glance / how risk changed
# ---------------------------------------------------------------------------

def compose_glance_lead(rows: list[dict], end: str, table_label: str,
                        high: float, alert: float) -> str:
    shown = [r for r in rows if not r["withheld"] and r["value"] is not None]
    q = qlabel(end)
    if not shown:
        return _ascii(f"{table_label} would list risk scores for {q}, but none are available.")
    if len(rows) == 1:
        r = shown[0]
        return _ascii(f"{table_label} shows the risk score, risk level and main factor for "
                      f"{r['name']} in {q}.")
    alert_n = sum(1 for r in shown if risk_level(r["value"], high, alert) == LEVEL_ALERT)
    if len(shown) == 1:
        level = risk_level(shown[0]["value"], high, alert)
        tail = (f"{shown[0]['name']} is " + ("not elevated" if level == LEVEL_NONE
                                             else f"at the {level} level"))
    elif alert_n == len(shown):
        tail = f"{every(len(shown))} are at the Alert level"
    else:
        tail = f"{num(alert_n)} of the {num(len(shown))} provinces are at the Alert level"
    return _ascii(f"As shown in {table_label}, {tail} in {q}. The table lists the provinces "
                  f"from the highest risk score to the lowest.")


def compose_trend_paragraph(series: list[dict], start: str, end: str, figure_label: str) -> str:
    """
    Short reading of the trend figure, placed before it.

    series: [{name, points: [{quarter, value | None}]}]; each series is read
    from its own first and last available quarter.
    """
    stats = []
    for s in series:
        pts = [p for p in s["points"] if p["value"] is not None]
        if len(pts) >= 2:
            stats.append((s["name"], pts))
    if not stats:
        return _ascii(f"{figure_label} cannot be drawn: fewer than two quarters of results "
                      f"are available between {qlabel(start)} and {qlabel(end)}.")
    span = f"between {qlabel(start)} and {qlabel(end)}"
    if len(stats) == 1:
        name, pts = stats[0]
        return _ascii(f"As shown in {figure_label}, {span} the risk score for {name} "
                      f"{describe_change(pts[0]['value'], pts[-1]['value'])}.")
    ups = [n for n, p in stats if change_amount(p[0]["value"], p[-1]["value"]) > 0]
    downs = [n for n, p in stats if change_amount(p[0]["value"], p[-1]["value"]) < 0]
    if len(downs) == len(stats):
        lead = f"the risk score decreased in {every(len(stats))}"
    elif len(ups) == len(stats):
        lead = f"the risk score increased in {every(len(stats))}"
    else:
        parts = []
        if downs:
            parts.append(f"decreased in {_join_series(downs)}")
        if ups:
            parts.append(f"increased in {_join_series(ups)}")
        lead = "the risk score " + " and ".join(parts)
    big_name, big = max(stats, key=lambda s: abs(change_amount(s[1][0]["value"], s[1][-1]["value"])))
    out = [f"As shown in {figure_label}, {span} {lead}."]
    if change_amount(big[0]["value"], big[-1]["value"]) != 0:
        out.append(f"The largest change was in {big_name}, where the score "
                   f"{describe_change(big[0]['value'], big[-1]['value'])}.")
    peak_name, peak = max(((n, p) for n, pts in stats for p in pts), key=lambda x: x[1]["value"])
    out.append(f"The highest score in the period was {score(peak['value'])}, in {peak_name} "
               f"in {qlabel(peak['quarter'])}.")
    return _ascii(" ".join(out))


# ---------------------------------------------------------------------------
# What is driving the risk
# ---------------------------------------------------------------------------

def _share(t: dict) -> str:
    return f"about {t['pct']}%"


def compose_factors_province(name: str, quarter: str, triggers: list[dict],
                             previous: list[dict] | None = None,
                             previous_quarter: str | None = None,
                             figure_label: str | None = None,
                             news_incomplete: bool = False) -> str:
    """Plain reading of one province's factor breakdown, optionally opening
    with a reference to the figure that shows it."""
    if not triggers:
        return _ascii(f"No breakdown of the factors is available for {name} in {qlabel(quarter)}.")
    ranked = sorted(triggers, key=lambda t: t["pct"], reverse=True)
    main = ranked[0]
    main_label = factor(main["key"], main.get("label"))
    opening = (f"As shown in {figure_label}, {lower_first(main_label)}" if figure_label
               else main_label)
    out = [f"{opening} account for {_share(main)} of the factors behind {name}'s risk score "
           f"in {qlabel(quarter)} and {effect_verb(main['direction'])} the risk."]
    for t in ranked[1:]:
        if t["pct"] <= 0:
            continue
        also = " also" if t["direction"] == main["direction"] else ""
        out.append(f"{factor(t['key'], t.get('label'))} account for {_share(t)} and{also} "
                   f"{effect_verb(t['direction'])} the risk.")
    unmeasured = [factor(t["key"], t.get("label")) for t in ranked
                  if t["pct"] <= 0 and news_incomplete and t["key"] in NEWS_ONLY_FACTORS]
    zero = [factor(t["key"], t.get("label")) for t in ranked
            if t["pct"] <= 0 and factor(t["key"], t.get("label")) not in unmeasured]
    if zero:
        listed = _join_series([zero[0]] + [lower_first(z) for z in zero[1:]])
        out.append(f"{listed} had no noticeable effect this quarter.")
    if unmeasured:
        listed = _join_series([unmeasured[0]] + [lower_first(z) for z in unmeasured[1:]])
        out.append(f"{listed} {'is' if len(unmeasured) == 1 else 'are'} measured only from news "
                   f"reports, which are not yet complete for this quarter, so "
                   f"{'its' if len(unmeasured) == 1 else 'their'} effect cannot yet be judged.")
    if previous and previous_quarter:
        before = next((t for t in previous if t["key"] == main["key"]), None)
        if before is not None:
            label = lower_first(factor(main["key"], main.get("label")))
            if before["pct"] == main["pct"]:
                out.append(f"Compared with {qlabel(previous_quarter)}, the share of {label} "
                           f"stayed at {main['pct']}%.")
            else:
                word = "rose" if main["pct"] > before["pct"] else "fell"
                out.append(f"Compared with {qlabel(previous_quarter)}, the share of {label} "
                           f"{word} from {before['pct']}% to {main['pct']}%.")
    return _ascii(" ".join(out))


def compose_factors_region(provinces: list[dict], quarter: str,
                           news_incomplete: bool = False) -> list[str]:
    """
    Plain reading across several provinces, said once for the region where
    every province agrees, with province sentences only where one differs.

    provinces: [{name, triggers (list) or None, withheld}]
    """
    have = [p for p in provinces if not p["withheld"] and p["triggers"]]
    out: list[str] = []
    if not have:
        return [_ascii(f"No breakdown of the factors is available for {qlabel(quarter)}.")]

    ranked = {p["name"]: sorted(p["triggers"], key=lambda t: t["pct"], reverse=True) for p in have}
    mains = {n: r[0] for n, r in ranked.items()}
    common = max({(t["key"], t["direction"]) for t in mains.values()},
                 key=lambda k: sum(1 for t in mains.values() if (t["key"], t["direction"]) == k))
    agree = [n for n, t in mains.items() if (t["key"], t["direction"]) == common]
    pcts = [mains[n]["pct"] for n in agree]
    rng = f"about {pcts[0]}%" if min(pcts) == max(pcts) else f"{min(pcts)}% to {max(pcts)}%"
    where = "In every province" if len(agree) == len(have) else f"In {_join_series(agree)}"
    out.append(f"{where}, {lower_first(factor(common[0]))} are the main factor, accounting for "
               f"{rng} of the factors behind the score, and they {effect_verb(common[1])} the risk.")
    for n, t in mains.items():
        if n not in agree:
            out.append(f"In {n}, the main factor is {lower_first(factor(t['key'], t.get('label')))} "
                       f"({t['pct']}%), which {effect_verb(t['direction'], plural=False)} the risk.")

    # Second-ranked factor, said once if it is the same everywhere.
    seconds = {n: r[1] for n, r in ranked.items() if len(r) > 1 and r[1]["pct"] > 0}
    second_keys = {(t["key"], t["direction"]) for t in seconds.values()}
    if len(seconds) == len(have) and len(second_keys) == 1:
        key, direction = second_keys.pop()
        sp = [t["pct"] for t in seconds.values()]
        srng = f"about {sp[0]}%" if min(sp) == max(sp) else f"{min(sp)}% to {max(sp)}%"
        out.append(f"{factor(key)} come second everywhere, at {srng}, and "
                   f"{effect_verb(direction)} the risk.")
        handled = {common[0], key}
    else:
        handled = {common[0]}

    # Remaining factors: small effects grouped by direction; zero everywhere said once.
    keys = []
    for r in ranked.values():
        for t in r:
            if t["key"] not in keys:
                keys.append(t["key"])
    none_anywhere = []
    for key in keys:
        if key in handled:
            continue
        entries = [(n, next((t for t in r if t["key"] == key), None)) for n, r in ranked.items()]
        nonzero = [(n, t) for n, t in entries if t and t["pct"] > 0]
        if not nonzero:
            if not (news_incomplete and key in NEWS_ONLY_FACTORS):
                none_anywhere.append(factor(key))
            continue
        for direction in ("increases_risk", "protective"):
            group = [(n, t) for n, t in nonzero if t["direction"] == direction]
            if not group:
                continue
            gp = [t["pct"] for _, t in group]
            amount = f"{gp[0]}%" if min(gp) == max(gp) else f"{min(gp)}% to {max(gp)}%"
            out.append(f"{factor(key)} had a small effect ({amount}) and "
                       f"{'raised' if direction == 'increases_risk' else 'lowered'} the risk in "
                       f"{_join_series([n for n, _ in group])}.")
    if none_anywhere:
        listed = _join_series([none_anywhere[0]] + [lower_first(z) for z in none_anywhere[1:]])
        out.append(f"{listed} had no noticeable effect this quarter in any province.")
    if news_incomplete:
        news_keys = [k for k in keys if k in NEWS_ONLY_FACTORS]
        if news_keys:
            labels = [factor(k) for k in news_keys]
            listed = _join_series([labels[0]] + [lower_first(z) for z in labels[1:]])
            out.append(f"{listed} {'is' if len(labels) == 1 else 'are'} measured only from news "
                       f"reports, which are not yet complete for this quarter, so "
                       f"{'its' if len(labels) == 1 else 'their'} effect cannot yet be fully judged.")
    held = [p["name"] for p in provinces if p["withheld"]]
    if held:
        out.append(withheld_sentence(held, quarter))
    return [_ascii(s) for s in out]


# ---------------------------------------------------------------------------
# Province profile, news, notes
# ---------------------------------------------------------------------------

def compose_profile_lead(rows: list[dict], table_label: str) -> str:
    """rows: [{name, population, poverty}] (values may be None)."""
    pop = [r for r in rows if r["population"] is not None]
    pov = [r for r in rows if r["poverty"] is not None]
    if len(rows) == 1:
        r = rows[0]
        return _ascii(f"{table_label} gives basic facts about {r['name']}.")
    out = [f"{table_label} gives basic facts about each province."]
    if pop and pov:
        big = max(pop, key=lambda r: r["population"])
        poor = max(pov, key=lambda r: r["poverty"])
        out.append(f"{big['name']} has the largest population ({big['population']:,}), and "
                   f"{poor['name']} has the highest poverty incidence ({round(poor['poverty'])}%).")
    return _ascii(" ".join(out))


def compose_news(rows: list[dict], quarter: str, table_label: str | None) -> list[str]:
    """
    rows: [{name, count, incomplete (bool), withheld, mainKey, matched (int),
            newsShare (int percent of the factors behind the score that come
            from news-based inputs, or None)}]
    `incomplete` is the backend's limitedSignal flag: some news-based inputs
    for the quarter are missing.
    """
    q = qlabel(quarter)
    out: list[str] = []
    shown = [r for r in rows if not r["withheld"]]
    if len(rows) == 1 and shown:
        r = shown[0]
        out.append(f"{count_lead(r['count'], 'news report')} about food conditions in "
                   f"{r['name']} {'was' if r['count'] == 1 else 'were'} found for {q}.")
    elif shown:
        listed = _join_series([f"{r['name']} ({r['count']})" for r in shown])
        out.append(f"The number of news reports about food conditions found for {q} was: {listed}.")
    incomplete = [r["name"] for r in shown if r["incomplete"]]
    if incomplete:
        if len(rows) == 1:
            out.append("News-based information for this quarter is not yet complete.")
        else:
            who = (every(len(shown)) if len(incomplete) == len(shown) and len(shown) > 1
                   else _join_series(incomplete))
            out.append(f"For {who}, news-based information for this quarter is not yet complete.")
    shares = [r["newsShare"] for r in shown if r.get("newsShare") is not None]
    if shares:
        amount = (f"about {shares[0]}%" if min(shares) == max(shares)
                  else f"between {min(shares)}% and {max(shares)}%")
        whose = "the score" if len(rows) == 1 else "each province's score"
        out.append(f"Information from news reports accounts for {amount} of the factors behind "
                   f"{whose}, so the score depends mainly on price and employment data.")
    with_match = [r for r in shown if r["matched"]]
    if table_label and with_match:
        out.append(f"{table_label} lists up to three reports per province that relate to the "
                   f"province's main factor.")
    elif shown and any(r["mainKey"] for r in shown):
        labels = {lower_first(factor(r["mainKey"])) for r in shown if r["mainKey"]}
        about = labels.pop() if len(labels) == 1 else "each province's main factor"
        out.append(f"None of these reports was specifically about {about}.")
    held = [r["name"] for r in rows if r["withheld"]]
    if held:
        out.append(withheld_sentence(held, quarter))
    return [_ascii(s) for s in out]


def compose_notes(latest: str, calendar: str, lag: int, any_withheld: bool) -> list[str]:
    timing = (f"Results are based on the latest available data ({qlabel(latest)}), "
              + (f"which is {num(lag)} {'quarter' if lag == 1 else 'quarters'} behind the current "
                 f"quarter ({qlabel(calendar)})." if lag > 0 else "which is the current quarter."))
    out = [
        "The risk score is about pressure on food prices. It is not a measure of hunger or of "
        "how many families lack food.",
        timing,
        "City and municipal figures follow their province's score. They are not separate "
        "estimates for each city or municipality.",
    ]
    if any_withheld:
        out.append("Results withheld by the reviewing team are left out of every table, figure "
                   "and statement in this report.")
    out.append("This report presents findings only. It does not recommend actions and should be "
               "used alongside the Department's own guidance.")
    return [_ascii(s) for s in out]
