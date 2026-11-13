"""Read-only API for the exact SHAP explanation of the official FINAL forecasts (preview only).
  GET /api/v1/final/shap/province?id=<slug>&quarter=<YYYY-Qn>   province explanation (or scope=region for the five-province average)
  GET /api/v1/final/shap/global                                  overall model importance (walk-forward test rows)
Everything is read from ../evidence (final_shap.py -> build_tables.py). Nothing is computed from feature values here except
formatting, and a quarter without an exact explanation returns available=false instead of a substitute."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from app.paths import BACKEND_DIR as _BD
META = _BD / "data" / "final" / "meta"            # fixed reference tables (input inventory, walk-forward importance)


def _issue_dir() -> Path:
    """The served issue (app.final.serving); its live SHAP tables explain exactly the forecasts on the dashboard."""
    from app.final import serving as SVG
    d = SVG.served_issue_dir()
    if d is None:
        raise FileNotFoundError("no served FINAL issue")
    return d


def _max_lead() -> int:
    from app.final import period as PD
    return PD.max_lead()
NEAR_ZERO = 0.01          # |SHAP| below this many log-odds = "little influence" (about 0.2 share points around a 25 % forecast)
SLUG = {"batangas": "Batangas", "cavite": "Cavite", "laguna": "Laguna", "quezon": "Quezon", "rizal": "Rizal"}
ANCHOR_TEXT = {"RSS": "the province's latest FNRI survey level, combined with the level shared by all provinces in the latest survey round "
                      "(regional shared-level anchor)",
               "OH": "the province's own FNRI survey history (own-history anchor)",
               "H": "a survey-level estimate pooled across provinces (hierarchical anchor)"}
OUTPUT = ("forecast log-odds of the share of households moderately or severely food insecure (FNRI HFIAS). 0 log-odds = a 50 % share = "
          "the HIGH cut-off. Positive SHAP pushes this output up (toward HIGH), negative pushes it down.")
RATE_MIND = ("FINAL is one LightGBM model per seed (5 seeds, averaged), not two models. RATE is how its target is defined: the model learns the "
             "change per unit of elapsed time since the province's anchor survey, and the forecast is anchor + elapsed-time scale x model output. "
             "MIND is how missing inputs are handled: a missing value is filled with the training median and a 0/1 'missing' input is added. "
             "So RATE and MIND have no separate outputs to explain: every input below, including the 'missing' inputs (MIND), is explained "
             "inside the same RATE model. The anchor is not a LightGBM contribution and is shown as the starting point.")
PROB_NOTE = ("The probability of HIGH is Phi(forecast log-odds / uncertainty) in each seed, averaged over 5 seeds. That step is not additive, so the "
             "SHAP values explain the forecast log-odds and the forecast share, not the probability directly. The order is the same: a higher "
             "forecast log-odds always means a higher probability of HIGH.")


def _load():
    D = _issue_dir()
    F = pd.read_csv(D / "shap_live_features.csv"); S = pd.read_csv(D / "shap_live_summary.csv"); I = pd.read_csv(META / "feature_inventory.csv")
    S["inputs_shap_logit"] = S["inputs_shap_logit"] if "inputs_shap_logit" in S else 0.0
    for c in [c for c in F.feature.unique() if c not in I.feature.values]:          # an input new in this issue: minimal metadata
        I = pd.concat([I, pd.DataFrame([{"feature": c, "name": c, "group_label": "Other", "period": "", "source": "", "kind": "", "component": "RATE input",
                                         "measures": c, "coverage": "", "parent": "", "status": "U: used in this issue"}])], ignore_index=True)
    G = pd.read_csv(META / "shap_global.csv") if (META / "shap_global.csv").exists() else None
    chk = {"global": json.loads((META / "shap_global_checks.json").read_text())} if (META / "shap_global_checks.json").exists() else {}
    man = json.loads((D / "manifest.json").read_text(encoding="utf-8"))
    chk["live"] = {"issue": man["issue_quarter"], "model_sha256": man.get("model_sha256"), "max_additivity_error_logit": float(S["additivity_error"].max())}
    return F, S, I.set_index("feature"), G, chk


def _fmt(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "no published value"
    a = abs(v)
    return f"{v:.0f}" if a >= 100 else f"{v:.1f}" if a >= 10 else f"{v:.2f}" if a >= 0.1 else f"{v:.3f}"


def _direction(s):
    return "near zero" if abs(s) < NEAR_ZERO else "raises" if s > 0 else "lowers"


def _sentence(m, x):
    d = _direction(x.shap_logit)
    eff = ("It had little influence on this forecast." if d == "near zero" else
           f"In this forecast it pushed the model's estimated food-insecurity share {'higher' if d == 'raises' else 'lower'}.")
    if m["kind"] == "MIND missing flag":
        what = (f"{m['name'][:-9]} had no published value for this forecast, so the model used the typical training value and this 'missing' input "
                f"is on." if x.value_used >= 0.5 else f"{m['name'][:-9]} was available for this forecast, so this 'missing' input is off.")
        return f"{what} {eff}"
    if x.missing:
        return (f"{m['name']} had no published value for this forecast; the model used the typical training value ({_fmt(x.reference_median)}). {eff}")
    rel = ("about the same as" if abs(x.value_raw - x.reference_median) <= 1e-9 + 0.02 * max(abs(x.reference_median), 1e-6)
           else "higher than" if x.value_raw > x.reference_median else "lower than")
    return f"{m['name']} was {_fmt(x.value_raw)}, {rel} the typical value in the training data ({_fmt(x.reference_median)}). {eff}"


MONTHS = {"1": "January–March", "2": "April–June", "3": "July–September", "4": "October–December"}


def _period(q):
    return f"{MONTHS[q[-1]]} {q[:4]}"


PUBLIC = {  # plain phrases for the public summary, by input (prefix match on the part after mi_)
    "cpi_": "food prices", "l_rice": "local rice prices", "l_fg": "palay farmgate prices", "l_fish": "fish prices", "l_terms": "farm prices",
    "ag_palay": "rice harvests", "ag_corn": "corn harvests", "ag_": "rice and corn harvests", "c_agri": "farm harvests", "agri_since": "farm harvests",
    "soil": "soil moisture", "rain": "rainfall", "c_rain": "rainfall", "c_soil": "soil moisture", "c_tc": "typhoons", "tc_rate": "typhoons",
    "vu_tc": "typhoon exposure", "vu_dry": "dry spells", "vu_rain": "rainfall", "oni": "El Niño / La Niña", "unemp": "unemployment",
    "income": "household spending", "hh_grdp": "the regional economy", "p_poverty": "poverty levels", "p_subsistence": "poverty levels",
    "p_density": "population density", "gap_q": "the time since the last survey", "h2": "hunger surveys",
}
NEWS_TOPIC = {"hunger": "hunger", "market": "food prices", "climate": "weather and disasters", "employment": "jobs and income",
              "poverty": "poverty", "remittance": "remittances", "response": "government help", "net": "food stress"}


def _plain(feature: str) -> str:
    """Public wording of an input (no model jargon). A MIND flag reads 'missing recent figures on ...'."""
    b = feature[3:] if feature.startswith("mi_") else feature
    if b[:2] in ("p_", "a_", "n_", "r_") and ("_e_" in b or "net_since" in b or "_tp_" in b or "_tg_" in b):
        topic = next((v for k, v in NEWS_TOPIC.items() if k in b.split("_", 2)[-1]), "food stress")
        txt = f"news about {topic}"
    else:
        txt = next((v for k, v in sorted(PUBLIC.items(), key=lambda kv: -len(kv[0])) if b.startswith(k)), b.replace("_", " "))
    return f"missing recent figures on {txt}" if feature.startswith("mi_") else txt


def _list(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _top(contrib, direction, exclude=()):
    out = []
    for c in contrib:
        t = _plain(c["feature"])
        if c["direction"] == direction and t not in out and t not in exclude:
            out.append(t)
    return out[:2]


def _drivers_sentence(contrib, inputs_pts):
    up = _top(contrib, "raises")
    down = _top(contrib, "lowers", exclude=up)
    size = "slightly " if abs(inputs_pts) < 2 else ""
    parts = []
    if up:
        parts.append(f"{_list(up)} pushed the estimate {size}up")
    if down:
        parts.append(f"{_list(down)} pulled it {size}down")
    if not parts:
        return "No recent figure moved the estimate much."
    s = "; ".join(parts)
    return s[0].upper() + s[1:] + "."


def plain_summary(d: dict) -> list[str]:
    """2-3 plain sentences for the public, built only from the exact SHAP result (no causal claims)."""
    import math
    lg = lambda p: math.log(p / (100 - p)); sg = lambda z: 100 / (1 + math.exp(-z))
    w, c, q = d["waterfall"], d["contributors"], d["quarter"]
    if d["scope"] == "region":
        sh = [p["sharePct"] for p in d["provinces"]]
        hi = [p["province"] for p in d["provinces"] if p["class"] == "HIGH"]
        s1 = (f"For {_period(q)}, all five CALABARZON provinces are forecast at low risk: about {min(sh):.0f}% to {max(sh):.0f}% of households "
              f"are expected to have moderate or severe food insecurity, below the 50% line for high risk." if not hi else
              f"For {_period(q)}, {_list(hi)} {'is' if len(hi) == 1 else 'are'} forecast at high risk (50% or more of households moderately or "
              f"severely food insecure).")
        s2 = ("Each forecast starts from the province's last food survey and comes down, because in past surveys food insecurity usually "
              "fell over a similar length of time." if w["expectedLogOdds"] < 0 else
              "Each forecast starts from the province's last food survey and goes up, because in past surveys food insecurity usually rose "
              "over a similar length of time.")
        return [s1, s2, _drivers_sentence(c, 0.0)]
    o = d["official"]; start = w["anchorSharePct"]; after = sg(lg(start) + w["expectedLogOdds"])
    s1 = (f"{d['name']} is forecast at {'high' if o['class'] == 'HIGH' else 'low'} risk for {_period(q)}: about {o['sharePct']:.0f}% of "
          f"households are expected to have moderate or severe food insecurity, {'at or above' if o['class'] == 'HIGH' else 'below'} the 50% "
          f"line for high risk.")
    s2 = (f"The forecast starts from {d['name']}'s last food survey ({start:.0f}%) and "
          + ("comes down, because in past surveys food insecurity usually fell over a similar length of time." if after < start else
             "goes up, because in past surveys food insecurity usually rose over a similar length of time."))
    return [s1, s2, _drivers_sentence(c, w["forecastSharePct"] - after)]


def _per(p):
    return p.replace(" (issue quarter)", "").replace("anchor survey to ", "up to ")


def value_text(feature: str, v) -> str:
    """The value the model used, in readable units; a whole-number percentage has no '.0' (owner 2026-11-13)."""
    import re as _re
    return _re.sub(r"(\d)\.0(?=%| percentage)", r"\1", _value_text(feature, v))


def _value_text(feature: str, v) -> str:
    """The value the model used, in readable units (the inputs' own scales, checked against the live rows 2026-11-13)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "no published figure"
    b = feature
    if NEWS_RE.match(b):
        return f"{100 * v:+.1f}"                                             # news score: 100 x the stored signal; above 0 = more food-stress reporting
    if b in ("cpi_food_yoy", "cpi_rice_yoy", "cpi_food_3m", "cpi_since", "unemp_rate", "unemp_region"):
        return f"{v:.1f}%"
    if b in ("cpi_food_rel_nat", "cpi_food_accel", "unemp_yoy", "unemp_chg_since"):
        return f"{v:+.1f} percentage points"
    if b.startswith(("ag_", "l_", "c_agri", "agri_since", "income", "hh_grdp_g")):
        return f"{100 * v:+.1f}%"
    if b in ("soil_since", "rain_since", "c_rain_anom_6m", "c_soil_anom_3m", "vu_rain12"):
        return f"{v:+.2f}"
    if b == "vu_tc_clim":
        return f"{v:.1f} typhoons a year"
    if b == "c_tc_4q":
        return f"{v:.0f} typhoons"
    if b == "tc_rate_since":
        return f"{v:.2f} typhoons per quarter"
    if b == "vu_dry6":
        return f"{v:.0f} dry months"
    if b == "gap_q":
        return f"{v:.0f} quarters"
    if b == "oni":
        return f"{v:+.1f} °C"
    return _fmt(v)


def _news_unit(feature):
    """One unit note per sentence, for inputs whose numbers have no everyday unit."""
    if NEWS_RE.match(feature):
        return " (news score: above 0 means more reporting of food stress on this topic)"
    if feature in ("soil_since", "rain_since", "c_rain_anom_6m", "c_soil_anom_3m", "vu_rain12"):
        return " (moisture index: 0 is normal, above 0 is wetter)"
    return ""


def _public_name(c):
    """'News: food stress since the last survey (national)' -> 'The national news score on food stress since the last survey'."""
    n = c["name"]
    if n.startswith("News: "):
        topic, _, where = n[6:].partition(" (")
        where = where.rstrip(")")
        where = {"national": "national", "sws area": "Balance Luzon", "province": "provincial", "calabarzon": "CALABARZON"}.get(where.lower(), where)
        return f"The {where} news score on {topic}"
    return n


def _live_values(feature, quarter):
    """Province values of one input for a region card, from the exact inference rows."""
    F = pd.read_csv(_issue_dir() / "shap_live_features.csv")
    z = F[(F.feature == feature) & (F.quarter == quarter)]
    return z.value_raw.tolist(), float(z.reference_median.iloc[0]) if len(z) else None


def _card_text(title, items, d):
    """2-3 plain sentences for one factor card: the specific value the model used against the usual value, which way it moved the
    forecast, and a caution. 'Usual' = the median of the model's training rows (also the value MIND fills in for a missing figure)."""
    top = max(items, key=lambda c: abs(c["shapLogOdds"]))
    tot = sum(c["shapLogOdds"] for c in items)
    f = top["feature"]
    who = f"{d['name']}'s forecast" if d["scope"] == "province" else "the forecasts"
    if f.startswith("mi_"):
        topic = _plain(f[3:])
        if d["scope"] == "province":
            v, m = top["valueUsed"], top["referenceMedian"]
        else:
            vals, m = _live_values(f, d["quarter"]); v = sum(vals) / len(vals)
        now = "were missing" if v >= 0.5 else "were available"
        usual = "usually missing" if m >= 0.5 else "usually available"
        s1 = f"Recent figures on {topic} {now} for this forecast ({usual} in past data)."
    elif d["scope"] == "region":
        vals, m = _live_values(f, d["quarter"])
        vals = [x for x in vals if x == x]
        span = (f"was {value_text(f, vals[0])}" if max(vals) - min(vals) < 1e-9 else
                f"ranged from {value_text(f, min(vals))} to {value_text(f, max(vals))} across the five provinces")
        s1 = f"{_public_name(top)} {span} ({_per(top['period'])}), against a usual {value_text(f, m)}{_news_unit(f)}."
    elif top.get("value") is None:
        s1 = (f"{_public_name(top)} had no published figure for this forecast ({_per(top['period'])}), so the model used the usual "
              f"{value_text(f, top['referenceMedian'])}.")
    else:
        v, m = top["value"], top["referenceMedian"]
        rel = ("about the same as" if abs(v - m) <= 0.02 * max(abs(m), 1e-6) + 1e-9 else "higher than" if v > m else "lower than")
        s1 = (f"{_public_name(top)} was {value_text(f, v)} ({_per(top['period'])}), {rel} the usual {value_text(f, m)}{_news_unit(f)}.")
    s1 = s1[0].upper() + s1[1:]
    s2 = (f"This pushed {who} up." if tot > 0 else f"This pulled {who} down.") if abs(tot) >= NEAR_ZERO else f"It barely changed {who}."
    return f"{s1} {s2} It shows what moved the forecast, not proof of cause."


# ---------- plain-language card text (2026-11-13, owner: "much simpler") ----------
# Each card: one sentence on what happened (no index numbers; a number only when it is a plain percentage), one on how much it moved
# the risk. expect = which way a HIGHER value is normally expected to move food-insecurity risk (+1 up, -1 down, 0 no fixed expectation);
# when the model moved the risk the other way, the card says so instead of hiding it.
NEWS_WHERE = {"p": "provincial", "a": "Balance Luzon", "n": "national", "r": "regional"}
NEWS_TOPIC_PLAIN = {"e_hunger": "hunger", "e_net": "food insecurity", "e_market": "food prices", "e_climate": "weather and disasters",
                    "e_employment": "employment and income", "e_response": "food assistance", "net_since": "food insecurity since the last survey"}
PLAIN = {  # feature: (higher, lower, about the same, expect)
    "soil_since": ("Soils have been wetter than usual since the last survey", "Soils have been drier than usual since the last survey",
                   "Soil moisture has been about normal since the last survey", 0),
    "vu_tc_clim": ("This area usually gets more typhoons than most of the country", "This area usually gets fewer typhoons than most of the country",
                   "This area usually gets an average number of typhoons", 1),
    "cpi_food_yoy": ("Food prices rose faster than usual over the past year", "Food prices rose more slowly than usual over the past year",
                     "Food prices rose at about the usual pace over the past year", 1),
    "cpi_food_3m": ("Food prices rose faster than usual in the last three months", "Food prices rose more slowly than usual in the last three months",
                    "Food prices rose at about the usual pace in the last three months", 1),
    "cpi_since": ("Food prices have risen faster than usual since the last survey", "Food prices have risen more slowly than usual since the last survey",
                  "Food prices have risen at about the usual pace since the last survey", 1),
    "cpi_food_rel_nat": ("Food prices here rose faster than in the rest of the country", "Food prices here rose more slowly than in the rest of the country",
                         "Food prices here rose at about the same pace as the rest of the country", 1),
    "l_rice_rel": ("Local rice is pricier than usual compared with other areas", "Local rice is cheaper than usual compared with other areas",
                   "Local rice prices are about as usual compared with other areas", 1),
    "l_fish_yoy": ("Local fish prices rose more than usual", "Local fish prices rose less than usual", "Local fish prices rose about as usual", 1),
    "ag_palay_yoy": ("The rice harvest did better than usual", "The rice harvest did worse than usual", "The rice harvest was about as usual", -1),
}


def _rel(v, m, floor=0.1):
    """+1 higher than usual, -1 lower, 0 about the same (within 5 % of the usual value, never less than the input's own floor)."""
    if v is None or m is None or v != v or m != m:
        return 0
    return 0 if abs(v - m) <= 0.05 * max(abs(m), floor) else (1 if v > m else -1)


def _floor(f):
    return 0.001 if NEWS_RE.match(f) else 0.01 if f.startswith(("ag_", "l_")) else 0.1


def _pct0(x):
    r = round(x, 1)
    return f"{int(r)}%" if r == int(r) else f"{r}%"


def _what_happened(f, v, m, d, vals):
    """One plain sentence about the input's value against its usual value. Returns (sentence, rel, expect)."""
    if f.startswith("mi_"):
        topic = _plain(f[3:])
        miss = (v if v is not None else 0) >= 0.5
        return ((f"Some recent figures on {topic} were not published yet, so typical values were used" if miss
                 else f"Recent figures on {topic} were available"), 0, 0)
    r = _rel(v, m, _floor(f))
    if f == "ag_dev3y":                                   # stored as a fraction of the 3-year average
        lo = 100 * min(vals) if vals else None
        if d["scope"] == "region" and lo is not None and lo < -5:
            return f"Rice and corn harvests fell well below their recent average in one or more provinces (down to {_pct0(int(abs(lo) + 0.5))} below)", -1, -1
        pv = None if v is None else 100 * v
        if pv is not None and abs(pv) >= 2:
            return f"Rice and corn harvests were about {_pct0(int(abs(pv) + 0.5))} {'below' if pv < 0 else 'above'} their recent average", (-1 if pv < 0 else 1), -1
        return "Rice and corn harvests were close to their recent average", 0, -1
    if f == "unemp_rate" and v is not None and m is not None:
        word = "higher than" if r > 0 else "lower than" if r < 0 else "about the same as"
        return f"Unemployment was {_pct0(v)}, {word} the usual {_pct0(m)}", r, 1
    if NEWS_RE.match(f):
        where = NEWS_WHERE.get(f[0], "")
        key = f[2:]
        topic = NEWS_TOPIC_PLAIN.get(key, _plain(f))
        if r == 0:
            return f"{where} news about {topic} was about as usual", 0, 1
        return f"{where} news reported {'more' if r > 0 else 'less'} about {topic} than usual", r, 1
    if f in PLAIN:
        hi, lo_, same, exp = PLAIN[f]
        return (hi if r > 0 else lo_ if r < 0 else same), r, exp
    name = _plain(f)
    name = name[0].upper() + name[1:]
    return f"{name} was {'higher than' if r > 0 else 'lower than' if r < 0 else 'about the same as'} usual", r, 0


FIG = {  # feature: (formal indicator name, formatter of the stored value, reading guide)
    "soil_since": ("Soil moisture anomaly since the last survey", lambda x: f"{x:+.2f}", "0 = long-term normal"),
    "vu_tc_clim": ("Average annual tropical cyclone exposure", lambda x: f"{x:.1f} per year", ""),
    "cpi_food_yoy": ("Food inflation, year-on-year", lambda x: f"{x:.1f}%", ""),
    "cpi_food_3m": ("Food inflation, three-month", lambda x: f"{x:.1f}%", ""),
    "cpi_since": ("Food inflation since the last survey", lambda x: f"{x:.1f}%", ""),
    "cpi_food_rel_nat": ("Food inflation relative to the national rate", lambda x: f"{x:+.1f} percentage points", ""),
    "l_rice_rel": ("Local rice price relative to other areas", lambda x: f"{100 * x:+.0f}%", ""),
    "l_fish_yoy": ("Local fish price change, year-on-year", lambda x: f"{100 * x:+.0f}%", ""),
    "ag_palay_yoy": ("Palay production change, year-on-year", lambda x: f"{100 * x:+.0f}%", ""),
    "ag_dev3y": ("Palay and corn production relative to the three-year average", lambda x: f"{100 * x:+.0f}%", ""),
    "unemp_rate": ("Unemployment rate (national)", lambda x: _pct0(round(x, 1)), ""),
}


def _figure(f, v, m, vals, scope):
    """'<label> <value> (usual <value>[; hint])' -- the input's own figure, short."""
    if f.startswith("mi_"):
        miss = (v if v is not None else 0) >= 0.5
        return f"Recent data on {_plain(f[3:])}: {'not yet published; historical median used' if miss else 'available'}"
    if NEWS_RE.match(f):
        topic = NEWS_TOPIC_PLAIN.get(f[2:], _plain(f)).replace(" since the last survey", "")
        label, fmt, hint = f"News coverage index on {topic} ({NEWS_WHERE.get(f[0], '')})", (lambda x: f"{100 * x:+.1f}"), "0 = average coverage"
    elif f in FIG:
        label, fmt, hint = FIG[f]
    else:
        label, fmt, hint = _plain(f)[0].upper() + _plain(f)[1:], (lambda x: value_text(f, x)), ""
    if scope == "region" and vals and max(vals) - min(vals) > 1e-9:
        val = f"{fmt(min(vals))} to {fmt(max(vals))} across provinces"
    elif v is None or v != v:
        return f"{label}: not yet published (historical median {fmt(m)} used)" if m is not None else f"{label}: not yet published"
    else:
        val = fmt(v)
    usual = f"historical median {fmt(m)}".replace("+0%", "0%").replace("+0.0", "0.0") if m is not None and m == m else ""
    tail = "; ".join(x for x in (usual, hint) if x)
    return f"{label}: {val}" + (f" ({tail})" if tail else "")


NEWS_SOURCE = {"p": "local news", "a": "Luzon news", "n": "national news", "r": "regional news"}
NEWS_TOPIC_PUBLIC = {"e_hunger": "hunger", "e_net": "food shortages", "e_market": "food prices", "e_climate": "bad weather and disasters",
                     "e_employment": "jobs and income", "e_response": "food aid", "net_since": "food shortages"}


def _n1(x):
    return f"{abs(x):.1f}".rstrip("0").rstrip(".")


def _public_line(f, v, m, vals, scope, r):
    """One plain sentence for the public, with the figure in everyday terms (no 'index', 'anomaly' or 'median')."""
    reg = scope == "region"
    if f.startswith("mi_"):
        miss = (v if v is not None else 0) >= 0.5
        return (f"Recent data on {_plain(f[3:])} were not yet available, so past averages were used" if miss
                else f"Recent data on {_plain(f[3:])} were available")
    if v is None or v != v:
        return f"Recent data on {_plain(f)} were not yet available, so past averages were used"
    if NEWS_RE.match(f):
        topic, src = NEWS_TOPIC_PUBLIC.get(f[2:], _plain(f)), NEWS_SOURCE.get(f[0], "the news")
        if r == 0:
            return f"There were about as many {src} reports on {topic} as usual"
        return f"There were {'more' if r > 0 else 'fewer'} {src} reports on {topic} than usual"
    if f == "soil_since":
        word = "wetter" if v > 0.05 else "drier" if v < -0.05 else "about as moist"
        return f"The soil has been {word} than normal since the last survey" if word != "about as moist" else "Soil moisture has been about normal since the last survey"
    if f == "ag_dev3y":
        if reg and vals and max(vals) - min(vals) > 0.02:
            lo, hi = 100 * min(vals), 100 * max(vals)
            def w(x):
                return f"{int(abs(x) + 0.5)}% {'below' if x < 0 else 'above'}"
            return f"Palay and corn harvests ranged from {w(lo)} to {w(hi)} their 3-year average across the provinces"
        pv = 100 * v
        if abs(pv) < 2:
            return "Palay and corn harvests were close to their 3-year average"
        return f"Palay and corn harvests were {int(abs(pv) + 0.5)}% {'lower' if pv < 0 else 'higher'} than their 3-year average"
    if f == "ag_palay_yoy":
        pv = 100 * v
        return f"The palay harvest was {int(abs(pv) + 0.5)}% {'lower' if pv < 0 else 'higher'} than a year earlier"
    if f == "cpi_food_rel_nat":
        where = "in most provinces" if reg else "here"
        if abs(v) < 0.3:
            return f"Food prices {where} rose at about the same pace as the national average"
        return f"Food prices {where} rose {'more slowly' if v < 0 else 'faster'} than the national average (by {_n1(v)} percentage points)"
    if f in ("cpi_food_yoy", "cpi_food_3m", "cpi_since"):
        span = {"cpi_food_yoy": "over the past year", "cpi_food_3m": "over the past three months", "cpi_since": "since the last survey"}[f]
        return f"Food prices rose {_n1(v)}% {span} (usually {_n1(m)}%)" if m is not None else f"Food prices rose {_n1(v)}% {span}"
    if f == "l_rice_rel":
        return f"Local rice prices were {int(abs(100 * v) + 0.5)}% {'higher' if v > 0 else 'lower'} than in other areas"
    if f == "l_fish_yoy":
        return f"Local fish prices were {int(abs(100 * v) + 0.5)}% {'higher' if v > 0 else 'lower'} than a year earlier"
    if f == "vu_tc_clim":
        return f"This area is usually hit by about {_n1(v)} typhoons a year"
    if f == "unemp_rate":
        near = "close to" if r == 0 else "above" if r > 0 else "below"
        return f"The national unemployment rate was {_n1(v)}%, {near} its usual level of {_n1(m)}%" if m is not None else f"The national unemployment rate was {_n1(v)}%"
    name = _plain(f)
    return f"{name[0].upper() + name[1:]} was {'higher than' if r > 0 else 'lower than' if r < 0 else 'about the same as'} usual"


def _simple_card(items, d):
    tot = sum(c["shapLogOdds"] for c in items)
    same = [c for c in items if (c["shapLogOdds"] > 0) == (tot > 0)] or items      # describe an input that moved the risk the way the group did
    same.sort(key=lambda c: -abs(c["shapLogOdds"]))

    def describe(c):
        f = c["feature"]
        vals = []
        if d["scope"] == "region":
            vals, m = _live_values(f, d["quarter"])
            vals = [x for x in vals if x == x]
            v = sum(vals) / len(vals) if vals else None
        else:
            v, m = (c.get("valueUsed") if f.startswith("mi_") else c.get("value")), c.get("referenceMedian")
        _, r_, e_ = _what_happened(f, v, m, d, vals)
        return _public_line(f, v, m, vals, d["scope"], r_), r_, e_

    # the largest input of the group; if it was about as usual, a clearly changed input with at least half its weight explains it better
    s1, r, exp = describe(same[0])
    if r == 0 and abs(tot) >= NEAR_ZERO:
        for c in same[1:]:
            if abs(c["shapLogOdds"]) < 0.5 * abs(same[0]["shapLogOdds"]):
                break
            alt = describe(c)
            if alt[1] != 0:
                s1, r, exp = alt
                break
    a = abs(tot)
    if a < NEAR_ZERO:
        return f"{s1}. This had almost no effect on the risk."
    size = "slightly" if a < 0.05 else "moderately" if a < 0.15 else "greatly"
    verb = "raised" if tot > 0 else "lowered"
    if exp and r and (r * exp > 0) != (tot > 0):
        link = "did not lead to more hunger" if tot < 0 else "came before more hunger"
        return f"{s1}. In past surveys, this {link}, so it {verb} the risk {size}."
    return f"{s1}. This {verb} the risk {size}."


NEWS_RE = __import__("re").compile(r"^(mi_)?([pan]_(e_|net_since|tp_|tg_|intensity)|r_e_net)")


GROUP = [  # (key, dashboard label): what the input measures; news is counted inside its topic's group (thesis convention)
    ("market", "Market / Prices"), ("climate", "Climate Stress"), ("ag_production", "Agricultural Production"), ("employment", "Employment"),
    ("household_economy", "Regional Economy"), ("poverty", "Poverty and Vulnerability"), ("hunger", "Hunger & Food Stress")]


def group_of(feature: str) -> str:
    b = feature[3:] if feature.startswith("mi_") else feature
    if NEWS_RE.match(b):
        topic = b.split("_", 2)[-1]
        return ("market" if "market" in topic else "climate" if "climate" in topic else "employment" if ("employment" in topic or "remittance" in topic)
                else "poverty" if "poverty" in topic else "hunger")
    if b.startswith(("cpi_", "l_")):
        return "market"
    if b.startswith(("ag_", "c_agri", "agri_since")):
        return "ag_production"
    if b.startswith(("c_rain", "c_soil", "c_tc", "rain_", "soil_", "tc_rate", "oni", "vu_")):
        return "climate"
    if b.startswith(("unemp", "income_growth")):
        return "employment"
    if b.startswith("hh_grdp"):
        return "household_economy"
    if b.startswith(("p_poverty", "p_subsistence", "p_density", "income_rel")):
        return "poverty"
    if b == "h2":
        return "hunger"
    return "other"                                                   # timing (gap_q, lead)


SEASON_MONTHS = {"DJF": "December-February", "JFM": "January-March", "FMA": "February-April", "MAM": "March-May", "AMJ": "April-June",
                 "MJJ": "May-July", "JJA": "June-August", "JAS": "July-September", "ASO": "August-October", "SON": "September-November",
                 "OND": "October-December", "NDJ": "November-January"}


def enso_context() -> dict | None:
    """Latest NOAA Oceanic Nino Index from the live download (data/e168/live_raw/noaa/oni.txt). CONTEXT ONLY: ONI is a candidate input
    of FINAL but is not selected by any official live fit, so it has no SHAP contribution; the Climate Stress card states this."""
    try:
        from app.paths import BACKEND_DIR
        lines = (BACKEND_DIR / "data" / "e168" / "live_raw" / "noaa" / "oni.txt").read_text().splitlines()
    except Exception:
        return None
    rows = [ln.split() for ln in lines if len(ln.split()) == 4 and ln.split()[0] in SEASON_MONTHS]
    if not rows:
        return None
    seas, yr, _, anom = rows[-1]
    oni = float(anom)
    if oni >= 0.5:
        strength = "very strong" if oni >= 2.0 else "strong" if oni >= 1.5 else "moderate" if oni >= 1.0 else "weak"
        phase = f"a {strength} El Niño"
    elif oni <= -0.5:
        phase = "a La Niña"
    else:
        phase = None
    m0, m1 = SEASON_MONTHS[seas].split("-")
    y = int(yr)                                    # NOAA labels DJF with the January year and NDJ with the November year
    if seas == "DJF":
        period = f"{m0} {y - 1} to {m1} {y}"
    elif seas == "NDJ":
        period = f"{m0} {y} to {m1} {y + 1}"
    else:
        period = f"{m0} to {m1} {y}"
    return {"oni": oni, "season": f"{seas} {yr}", "period": period, "phase": phase, "inForecast": False, "source": "NOAA Climate Prediction Center, Oceanic Niño Index"}


def _enso_sentence(e: dict | None) -> str:
    if not e or not e["phase"]:
        return ""
    name = e["phase"][0].upper() + e["phase"][1:]
    effect = ("It usually brings less rain to the Philippines from December to May" if "El Niño" in e["phase"]
              else "It usually brings more rain and typhoons to the Philippines")
    mon = {"January": "Jan", "February": "Feb", "March": "Mar", "April": "Apr", "May": "May", "June": "Jun", "July": "Jul", "August": "Aug",
           "September": "Sep", "October": "Oct", "November": "Nov", "December": "Dec"}
    per = e["period"]
    for k, v in mon.items():
        per = per.replace(k, v)
    per = per.replace(" to ", "–")
    kind = "El Niño" if "El Niño" in e["phase"] else "La Niña"
    return (f" {name} is happening now (NOAA, {per}). {effect}. "
            f"The forecast does not include {kind}, so the actual risk may be higher.")


# ---------- Poverty and Vulnerability (owner 2026-11-14: always shown on the left bars and the right cards) ----------
# Its bar is the model's exact contribution (0 when the forecast used no poverty or density input). The card also states the
# province's official figures as of the forecast's cut-off, so readers see the situation even when the model did not use it.
POV_YEARS = (2006, 2009, 2012, 2015, 2018, 2021, 2023, 2025, 2027, 2029)
CENSUS_COL = {2010: "Total Population (01 May 2010)", 2015: "Total Population (01 August 2015)", 2020: "Total Population (01 May 2020)",
              2024: "Total Population (01 July 2024)"}


def _cutoff_of(quarter: str, lead: int) -> pd.Timestamp:
    i = int(quarter[:4]) * 4 + int(quarter[-1]) - 1 - int(lead)                 # issue quarter; issued on the 1st of its 2nd month
    return pd.Timestamp(year=i // 4, month=3 * (i % 4) + 2, day=1)


def _vulnerability_figures(names: list[str], cutoff: pd.Timestamp) -> dict:
    """Latest official poverty incidence among population (round R usable from 1 Jan R+2) and density (census C from 1 Jan C+2)."""
    import re
    from app.paths import BACKEND_DIR as BD
    out = {n: {} for n in names}
    try:
        P = pd.read_csv(BD / "data" / "hcw_official" / "raw" / "psa_poverty_by_province.csv")
        P = P[(P.indicator == "pov_pop") & (P.level == "province_or_district") & P.name.isin(names)]
        P = P[P.year.map(lambda y: pd.Timestamp(year=int(y) + 2, month=1, day=1) <= cutoff)]
        for n, g in P.dropna(subset=["value_pct"]).groupby("name"):
            r = g.sort_values("year").iloc[-1]
            out[n].update(poverty_pct=float(r.value_pct), poverty_year=int(r.year))
    except Exception:
        pass
    try:
        raw = BD / "data" / "e137" / "raw" / "psa"
        pop = pd.read_csv(raw / "population_2010_2024.csv", dtype=str, encoding="latin-1")
        area = pd.read_csv(raw / "land_area_density_2024.csv", dtype=str, encoding="latin-1")
        prov = lambda t: t[t.iloc[:, 0].str.match(r"^\.\.\.\.[^.]", na=False)].copy()   # province rows only (towns have six dots)
        pop, area = prov(pop), prov(area)
        clean = lambda s: re.sub(r"[^a-z ]", "", str(s).lower()).strip()
        pop["k"], area["k"] = pop.iloc[:, 0].map(clean), area.iloc[:, 0].map(clean)
        acol = [c for c in area.columns if "Land Area" in c][0]
        rel = [y for y in CENSUS_COL if pd.Timestamp(year=y + 2, month=1, day=1) <= cutoff]
        for n in names:
            pr, ar = pop[pop.k == n.lower()], area[area.k == n.lower()]
            if rel and len(pr) and len(ar):
                y = max(rel)
                v = float(str(pr.iloc[0][CENSUS_COL[y]]).replace(",", "")) / float(str(ar.iloc[0][acol]).replace(",", ""))
                out[n].update(density=v, census_year=y, population=int(float(str(pr.iloc[0][CENSUS_COL[y]]).replace(",", ""))))
    except Exception:
        pass
    return out


def _vulnerability_text(d: dict, used: bool) -> str:
    names = [p["province"] for p in d.get("provinces", [])] if d["scope"] == "region" else [d["name"]]
    lead = d.get("lead")
    if lead is None:                                     # region view: the lead of this target quarter in the served issue
        S = _load()[1]
        lead = int(S[S.quarter == d["quarter"]]["lead"].iloc[0])
    F = _vulnerability_figures(names, _cutoff_of(d["quarter"], lead))
    pv = [F[n]["poverty_pct"] for n in names if "poverty_pct" in F[n]]
    dn = [F[n]["density"] for n in names if "density" in F[n]]
    py = next((F[n]["poverty_year"] for n in names if "poverty_year" in F[n]), None)
    cy = next((F[n]["census_year"] for n in names if "census_year" in F[n]), None)
    parts = []
    if pv:
        parts.append((f"{min(pv):.1f}%–{max(pv):.1f}% of people were poor" if len(pv) > 1
                      else f"{pv[0]:.1f}% of people were poor") + (f" (PSA {py})" if py else ""))
    if dn:
        parts.append((f"{min(dn):,.0f}–{max(dn):,.0f} people per km²" if len(dn) > 1
                      else f"{dn[0]:,.0f} people per km²") + (f" ({cy} census)" if cy else ""))
    fig = ("; ".join(parts) + ".") if parts else "Official poverty and population figures were not available."
    fig = fig[0].upper() + fig[1:]
    if used:
        return fig
    return f"{fig} This forecast did not use them, so they did not change the risk. They are used to rank towns and cities."


def factor_groups(d: dict) -> dict:
    """Group bars and cards: exact input SHAP summed within each group (additive, so exact); % of the total absolute group SHAP."""
    by = {}
    for c in d["contributors"]:
        by.setdefault(group_of(c["feature"]), []).append(c)
    sums = {g: sum(c["shapLogOdds"] for c in items) for g, items in by.items()}
    tot = sum(abs(v) for v in sums.values()) or 1.0
    enso = enso_context()
    out = []
    for key, label in GROUP:
        if key not in by:
            continue
        s = sums[key]
        g = {"key": key, "label": label, "pct": round(100 * abs(s) / tot), "signedContribution": round(s, 4),
             "direction": "increases_risk" if s >= NEAR_ZERO else "protective" if s <= -NEAR_ZERO else "no_effect",
             "status": "contributes" if abs(s) >= NEAR_ZERO else "no_effect",
             "plainEvidence": _simple_card(by[key], d), "inputs": [c["feature"] for c in by[key]]}
        if key == "poverty":
            g["plainEvidence"] += " " + _vulnerability_text(d, True)
        if key == "climate" and enso and enso["phase"]:
            # context only: the bar and pct above stay the model's exact SHAP; ENSO adds no contribution
            g["plainEvidence"] += _enso_sentence(enso)
            g["enso"] = enso
        out.append(g)
    if not any(g["key"] == "poverty" for g in out):
        # the model used no poverty or vulnerability input in this forecast: shown with its true contribution, 0
        out.append({"key": "poverty", "label": "Poverty and Vulnerability", "pct": 0, "signedContribution": 0.0, "direction": "no_effect",
                    "status": "no_effect", "plainEvidence": _vulnerability_text(d, False), "inputs": [], "usedByModel": False})
    out.sort(key=lambda g: -abs(g["signedContribution"]))
    return {"groups": out, "otherPct": round(100 * abs(sums.get("other", 0.0)) / tot), "otherInputs": [c["feature"] for c in by.get("other", [])]}


def province(pid: str, quarter: str, scope: str = "province") -> dict:
    d = _province(pid, quarter, "region" if pid.lower() == "calabarzon" else scope)
    if d.get("available"):
        d["summary"] = plain_summary(d)
        d.update(factor_groups(d))
    return d


def _province(pid: str, quarter: str, scope: str = "province") -> dict:
    F, S, I, G, chk = _load()
    base = {"available": False, "quarter": quarter, "explainedOutput": OUTPUT, "rateMind": RATE_MIND, "probabilityNote": PROB_NOTE,
            "nearZeroLogOdds": NEAR_ZERO, "model": "final-rate-mind-1.0", "issue": chk.get("live", {}).get("issue"), "checks": chk.get("live")}
    shown = sorted(set(S[S.lead <= _max_lead()].quarter))
    if quarter not in shown:
        return {**base, "reason": f"An exact SHAP explanation exists only for the official FINAL forecasts shown ({shown[0]} to {shown[-1]})."}
    if scope == "region":
        z, s = F[F.quarter == quarter], S[S.quarter == quarter]
        rows = (z.groupby("feature").agg(shap_logit=("shap_logit", lambda v: v.sum() / 5)).reset_index())
        contrib = [{"feature": r.feature, "name": I.at[r.feature, "name"], "group": I.at[r.feature, "group_label"], "shapLogOdds": round(float(r.shap_logit), 4),
                    "direction": _direction(r.shap_logit), "period": I.at[r.feature, "period"], "source": I.at[r.feature, "source"],
                    "kind": I.at[r.feature, "kind"], "component": I.at[r.feature, "component"],
                    "explanation": "Average over the five provinces' official forecasts; each province's own value is in its province view."}
                   for r in rows.itertuples()]
        contrib.sort(key=lambda c: -abs(c["shapLogOdds"]))
        return {**base, "available": True, "scope": "region", "name": "CALABARZON (average of the five provinces)",
                "waterfall": {"anchorLogOdds": round(float(s.anchor_logit.mean()), 4), "expectedLogOdds": round(float(s.expected_value_logit.mean()), 4),
                              "inputsLogOdds": round(float(s.inputs_shap_logit.mean()), 4), "forecastLogOdds": round(float(s.mu.mean()), 4)},
                "provinces": [{"province": r.province, "class": r.official_class, "pHigh": r.official_p_high, "sharePct": round(r.forecast_share_pct, 1)}
                              for r in s.itertuples()],
                "contributors": contrib}
    name = SLUG.get(pid.lower())
    if name is None:
        return {**base, "reason": f"No FINAL forecast for '{pid}'."}
    s = S[(S.province == name) & (S.quarter == quarter)].iloc[0]
    z = F[(F.province == name) & (F.quarter == quarter)]
    contrib = []
    for x in z.itertuples():
        m = I.loc[x.feature]
        contrib.append({"feature": x.feature, "name": m["name"], "group": m["group_label"], "measures": m["measures"],
                        "value": None if x.missing else x.value_raw, "valueText": _fmt(None if x.missing else x.value_raw),
                        "valueUsed": x.value_used, "referenceMedian": x.reference_median, "missing": bool(x.missing),
                        "shapLogOdds": round(float(x.shap_logit), 4), "direction": _direction(x.shap_logit),
                        "seedsUsing": int(x.seeds_using), "explanation": _sentence(m, x), "period": m["period"], "source": m["source"],
                        "coverage": m["coverage"], "kind": m["kind"], "component": m["component"]})
    contrib.sort(key=lambda c: -abs(c["shapLogOdds"]))
    anchors = sorted(set(s.anchor_names.split("|")))
    return {**base, "available": True, "scope": "province", "name": name, "lead": int(s.lead),
            "official": {"class": s.official_class, "pHigh": float(s.official_p_high), "sharePct": round(float(s.forecast_share_pct), 1), "highAtSharePct": 50},
            "waterfall": {"anchorLogOdds": round(float(s.anchor_logit), 4), "anchorSharePct": round(float(s.anchor_share_pct), 1),
                          "anchorText": "Starting point: " + "; ".join(ANCHOR_TEXT.get(a, a) for a in anchors) + ". Not a LightGBM contribution.",
                          "expectedLogOdds": round(float(s.expected_value_logit), 4),
                          "expectedText": (f"Average change the model expects over {int(s.gap_q)} quarters since the anchor survey (LightGBM base value x "
                                           f"elapsed-time scale {s.g_scale:.2f}); the same for any province with this elapsed time."),
                          "inputsLogOdds": round(float(s.inputs_shap_logit), 4), "forecastLogOdds": round(float(s.mu), 4),
                          "forecastSharePct": round(float(s.forecast_share_pct), 1), "additivityError": float(s.additivity_error)},
            "contributors": contrib, "inputsUsed": len(contrib)}


def global_importance() -> dict:
    F, S, I, G, chk = _load()
    if G is None:
        return {"available": False, "reason": "Global importance has not been computed."}
    items = [{"rank": int(r.rank), "feature": r.feature, "name": r.name, "group": I.at[r.feature, "group_label"] if r.feature in I.index else r.group,
              "component": I.at[r.feature, "component"] if r.feature in I.index else "", "meanAbsShapLogOdds": round(float(r.mean_abs_shap_logit), 4),
              "fitsUsing": f"{int(r.fits_using)}/{int(r.fits)}",
              "interpretation": (f"Across the past test forecasts this input moved the model output by {r.mean_abs_shap_logit:.3f} log-odds on average "
                                 f"(either direction). It says how much the model relies on it in general, not why one province got its forecast.")}
             for r in G.itertuples()]
    return {"available": True, "reference": (f"Lead-1 walk-forward test forecasts for the ENNS 2018, 2019 and 2021 rounds ({int(G.reference_rows.iloc[0])} "
                                             f"province forecasts, each from models trained only on earlier rounds), 5 seeds. Mean |SHAP| in log-odds."),
            "explainedOutput": OUTPUT, "items": items, "checks": chk.get("global")}


def context(quarter: str) -> dict:
    """Dashboard indicators that are NOT SHAP contributors of the official forecast, and system inputs FINAL does not use."""
    F, S, I, G, chk = _load()
    used = set(F.feature)
    groups_used = {I.at[c, "parent"] if isinstance(I.at[c, "parent"], str) and I.at[c, "parent"] else c for c in used}
    shown = [  # dashboard surfaces and the model inputs they correspond to
        ("FNRI food-insecurity survey history (status card)", "measured survey levels; enter only through the anchor (starting point), not as inputs", []),
        ("Town and city ranking (poverty and density percentiles)", "weights the province forecast across LGUs after the forecast is made", []),
        ("News articles list", "the articles behind the news inputs; an article is not itself an input", []),
    ]
    out = [{"indicator": a, "role": b} for a, b, _ in shown]
    not_selected = I[I.status.str.startswith("C") & ~I.index.str.startswith("mi_")]
    unused_groups = sorted(set(not_selected.group_label) - {I.at[c, "group_label"] for c in used if c in I.index})
    return {"supportingContext": out,
            "notUsed": [{"feature": c, "name": r["name"], "group": r["group_label"], "reason": "candidate input not selected by any official live model"}
                        for c, r in not_selected.iterrows()],
            "notInModel": [{"name": "OFW remittances", "reason": "excluded from FINAL's candidate inputs (app/hcw/engine.py DROP: no usable provincial series)"},
                           {"name": "Fisheries production / fish kill", "reason": "excluded from FINAL's candidate inputs (app/hcw/engine.py DROP)"},
                           {"name": "DROMIC displacement", "reason": "tested in research (FINAL+D3 ablation); no improvement; not an input of FINAL"},
                           {"name": "Poverty and disaster context panels", "reason": "shown for context; only the PSA poverty inputs listed above enter the model"}],
            "groupsWithNoUsedInput": unused_groups}


def register(app):
    from fastapi import Query
    @app.get("/api/v1/final/shap/province")
    def _p(id: str = Query("calabarzon"), quarter: str = Query(...), scope: str = Query("province")):
        return province(id, quarter, "region" if id.lower() == "calabarzon" else scope)

    @app.get("/api/v1/final/shap/global")
    def _g():
        return global_importance()

    @app.get("/api/v1/final/shap/context")
    def _c(quarter: str | None = Query(None, description="Defaults to the served issue's first forecast quarter")):
        if quarter is None:
            S = pd.read_csv(_issue_dir() / "shap_live_summary.csv")
            quarter = str(S.sort_values("lead")["quarter"].iloc[0])
        return context(quarter)
