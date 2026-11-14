"""
Serving layer of FINAL on the dashboard: points the dashboard modules (app.ml.inference.hcw_system, app.hcw.serve) at the issue
that is served NOW (the latest issue in the forecast history) and applies FINAL's presentation rules. Ported from the reviewed
local preview (research_notes/aiPHeed_final_dashboard_preview_20261113/scripts/run_preview_api.py); every date, quarter and
data period that the preview had fixed for issue 2026-Q4 is computed from the served issue here.

activate() runs at start-up when the registry's production model is FINAL; refresh() re-points after a new issue (cheap; called
by the period endpoint, so a quarter change is picked up without a restart).
"""
from __future__ import annotations

import functools
import json
import re
import threading
from pathlib import Path

import numpy as np
import pandas as pd

from app.final import history as HI
from app.final import period as PD
from app.paths import BACKEND_DIR

ROOT = BACKEND_DIR / "data" / "final"
MIN_PP = 0.5                       # a factor bar is drawn when it moves this forecast share by >= 0.5 points
_LOCK = threading.Lock()
_STATE = {"issue": None, "patched": False}

EVIDENCE_ROLE = {
    "household_economy": ("validated driver", "removing it worsens out-of-sample Brier by 0.029 [0.004, 0.054]; regional GRDP, not provincial"),
    "ag_production": ("validated driver", "removing it worsens out-of-sample Brier by 0.011 [0.001, 0.020]"),
    "market": ("model input, not validated", "out-of-sample contribution not significant (0.011 [-0.004, 0.026])"),
    "ag_vulnerability": ("model input, not validated", "climate and typhoon inputs: no out-of-sample support (-0.002 [-0.012, 0.006])"),
    "employment": ("model input, not validated", "national series only; no measurable contribution (0.000)"),
    "poverty": ("model input, not validated", "PSA provincial poverty statistics; contextual (no significant out-of-sample change)"),
}
_OOS = {"household_economy": True, "ag_production": True, "market": False, "ag_vulnerability": False, "employment": False}


def is_production() -> bool:
    from app import registry as R
    try:
        return R.production()["model_id"] == PD.serving()["model_id"]
    except Exception:
        return False


def served_issue_dir() -> Path | None:
    issue = HI.latest_issue(PD.serving()["model_id"])
    if issue is None:
        return None
    d = ROOT / "issues" / issue
    return d if (d / "dashboard_rows.csv").exists() else None


def _months(a: pd.Timestamp, b: pd.Timestamp) -> str:
    return f"{a:%b}–{b:%b %Y}" if a.year == b.year else f"{a:%b %Y}–{b:%b %Y}"


def issue_facts(issue_dir: Path) -> dict:
    """Dates and data periods of one issue, for the explanatory text (no constant from any other issue)."""
    from app.e154 import model as E154
    man = json.loads((issue_dir / "manifest.json").read_text(encoding="utf-8"))
    issue = man["issue_quarter"]
    i = PD.quarter_index(PD.base_quarter(issue))                          # leads and quarterly data periods count from this quarter
    qs = pd.Timestamp(year=i // 4, month=3 * (i % 4) + 1, day=1)
    end = qs - pd.DateOffset(months=3)                                     # local prices: 3 months ending 3 months before the quarter start
    rounds = [y for y in (2006, 2009, 2012, 2015, 2018, 2021, 2023, 2025, 2027, 2029) if pd.Timestamp(year=y + 2, month=1, day=1) <= pd.Timestamp(man["information_cutoff"])]
    leads = sorted(pd.read_csv(issue_dir / "dashboard_rows.csv")["lead"].unique().tolist())
    return {"issue": issue, "cutoff": man["information_cutoff"], "generated_utc": man["generated_utc"],
            "local_prices": _months(end - pd.DateOffset(months=2), end), "grdp_year": int(E154.available_year(i)),
            "poverty_round": rounds[-1] if rounds else None, "leads": leads,
            "targets": {L: PD.label(i + L) for L in leads}, "model_sha": man.get("model_sha256", "")}


def model_accuracy_by_lead() -> dict:
    """The model's walk-forward accuracy per lead (data/final/meta/lead_horizon.json), in the outlook's shape."""
    H = json.loads((ROOT / "meta" / "lead_horizon.json").read_text(encoding="utf-8"))["leads"]
    return {k: {"accuracy": v["accuracy"], "mean_fold_accuracy": v.get("mean_fold_accuracy"), "high_recall": v.get("high_recall"),
                "low_recall": v.get("low_recall"), "persistence_accuracy": v.get("persistence_accuracy"),
                "beats_persistence": v.get("beats_persistence_C2")} for k, v in H.items()}


def _served_rows(issue_dir: Path) -> Path:
    """Map value = forecast SHARE (0-1, HIGH at 0.50); the probability of HIGH is kept in p_high (served copy only)."""
    out = issue_dir / "dashboard_rows_served.csv"
    if not out.exists() or out.stat().st_mtime < (issue_dir / "dashboard_rows.csv").stat().st_mtime:
        r = pd.read_csv(issue_dir / "dashboard_rows.csv")
        r = r[r["lead"] <= PD.max_lead()].reset_index(drop=True)
        r["p_high"] = r["probability"]
        r["probability"] = (r["score_pct"] / 100.0).round(3)
        r.to_csv(out, index=False, lineterminator="\n")
    return out


def activate(issue_dir: Path | None = None) -> dict:
    """Point the dashboard at the served issue and install FINAL's presentation rules (once)."""
    from app.hcw import serve as SV
    from app.ml.inference import hcw_system as HS
    with _LOCK:
        issue_dir = issue_dir or served_issue_dir()
        if issue_dir is None:
            return {"active": False, "reason": "no FINAL issue in the forecast history"}
        F = issue_facts(issue_dir)
        cfg = PD.serving()
        HS.MODEL_ID = cfg["model_id"]
        HS.DATA, HS.ROWS, HS.ISSUE = ROOT / "meta", _served_rows(issue_dir), F["cutoff"]   # meta: the model's walk-forward evaluation
        SV.OUT, SV.LIVE, SV.ROWS = issue_dir, issue_dir / "live.json", HS.ROWS
        if not _STATE["patched"]:
            _install(HS, SV)
            _STATE["patched"] = True
        _texts(HS, F, cfg)
        for f in (getattr(HS, "_rows", None), getattr(HS, "_rows_path", None), getattr(HS, "_production", None)):
            if hasattr(f, "cache_clear"):
                f.cache_clear()
        _STATE["issue"] = F["issue"]
        return {"active": True, "issue": F["issue"], "issue_dir": str(issue_dir)}


def refresh() -> dict:
    """Re-point when the history has a newer issue than the one served (called on period requests)."""
    if not _STATE["patched"]:
        return activate() if is_production() else {"active": False}
    latest = HI.latest_issue(PD.serving()["model_id"])
    if latest and latest != _STATE["issue"]:
        return activate()
    return {"active": True, "issue": _STATE["issue"]}


def current_issue() -> str | None:
    return _STATE["issue"]


def _texts(HS, F: dict, cfg: dict) -> None:
    """Every issue-specific sentence, rebuilt from the served issue."""
    leads = F["leads"]
    tgt = ", ".join(f"Lead {L} = {F['targets'][L]}" for L in leads)
    HS.INDICATOR = {**HS.INDICATOR,
                    "id": "final_food_insecurity_risk",
                    "name": f"Food-insecurity risk ({cfg.get('model_name', 'FINAL')}): forecast share of households moderately or severely food insecure",
                    "unit": "forecast share 0-1 of households moderately or severely food insecure (FNRI HFIAS); HIGH at 0.50",
                    "definition": ("Forecast share (0-1) of households with moderate or severe food insecurity (FNRI HFIAS) in the province; HIGH when "
                                   "it is 0.50 or more, which is the same rule as a probability of HIGH of 0.50 or more. The probability of HIGH is "
                                   "stated separately. A forecast, not a measured survey value."),
                    "horizon": f"issued with data published before {F['cutoff']}; {tgt}. {cfg.get('lead_basis', '')}",
                    "caveat": ("A forecast risk class, not a measured food-insecurity rate. " + cfg.get("caveat", ""))}
    HS.RISK_LEVEL_BASIS = str(getattr(HS, "RISK_LEVEL_BASIS", "")).replace("Setup H + class weights", "FINAL (RATE + MIND)")
    HS.REPORT_COVER = str(getattr(HS, "REPORT_COVER", "")).replace("Setup H + class weights", "FINAL (RATE + MIND)")
    HS._FACTS = F


def _install(HS, SV) -> None:
    """FINAL's presentation rules (from the reviewed preview), written once; they read the served issue through HS._FACTS."""
    import math
    from app.services import dashboard as _D
    from app.e145 import lgu as _L
    from app.services import report as _RPT

    # ---- outlook: an issue's live.json carries the forecasts; the acceptance basis and per-lead accuracy describe the MODEL
    # and come from data/final (serving.json, meta) when an issue file does not carry them (issues are never rewritten)
    def _outlook_final():
        d = json.loads(SV.LIVE.read_text(encoding="utf-8"))
        cfg = PD.serving()
        d.setdefault("acceptance_basis", cfg.get("lead_basis", ""))
        d.setdefault("statistical_reliability", cfg.get("caveat", ""))
        d.setdefault("accuracy_by_lead", model_accuracy_by_lead())
        served = set(d["served_leads"])
        cut = d["information_cutoff"]
        return {**{k: d[k] for k in ("model", "name", "issue_quarter", "target", "acceptance_basis", "statistical_reliability")},
                "accuracy_by_lead": {str(k): v for k, v in d["accuracy_by_lead"].items()}, "seals": {},
                "origin_date": cut, "classification_threshold": 0.5,
                "information_cutoff": (f"data for periods before {cut}, as published by {PD.published_by(d['issue_quarter'])}"
                                       if PD.issue_note(d["issue_quarter"]) else f"data published before {cut}"),
                "created_utc": d.get("created_utc"), "data_published_by": PD.published_by(d["issue_quarter"]),
                "issue_note": PD.issue_note(d["issue_quarter"]),
                "data_through": (pd.Timestamp(cut) - pd.Timedelta(days=1)).date().isoformat(), "data_used": HS.data_used()["items"],
                "provinces": [r for r in d["provinces"] if r["lead"] in served]}
    SV.outlook = _outlook_final

    # ---- confidence statement: the share is the map value; the chance of HIGH is stated from p_high
    _province_row = HS.province_row

    def _row_share(code, name, quarter, base):
        out = _province_row(code, name, quarter, base)
        if out is None:
            return None
        r = HS.row(code, quarter)
        lvl, ph = float(r["probability"]), float(r["p_high"])
        out["score_type"] = "final_forecast_food_insecurity_risk"
        out["confidence_statement"] = (f"{name}, {quarter}: food insecurity risk {lvl:.2f} (forecast share of households moderately or "
                                       f"severely food insecure; HIGH at 0.50), class {r['class']}; chance of HIGH {ph:.3f}. {out['horizon_label']}")
        return out
    HS.province_row = _row_share

    # ---- towns and cities: owner Option A percentile basis (app/e145/lgu.py), ranked within the province on the unrounded value
    V = pd.read_csv(_L.BASE, dtype={"lgu_psgc": str})
    V["code"] = V["lgu_psgc"].str.zfill(9)
    VUL = dict(zip(V["code"], _L.W_POVERTY * V["pct_poverty"] + _L.W_DENSITY * V["pct_density"]))
    # the poverty value the ranking actually used, with its source (audit 2026-11-14: Lucena showed a 16.8% "province substitute"
    # while the ranking used PSA's own 2021 City of Lucena figure, 10%); the panel must show the value behind the rank
    POV = {c: (float(v), str(s)) for c, v, s in zip(V["code"], V["poverty_incidence_2021"], V["poverty_source"])}
    _muni = _D.municipality_summary
    METHOD = ("vulnerability = 0.6 x poverty percentile + 0.4 x density percentile across the 142 LGUs (owner Option A, app/e145/lgu.py); "
              "priority = province food insecurity risk x vulnerability, 4 dp; ranked on the unrounded value. A relative "
              "prioritisation within the province forecast, not a municipal forecast.")

    def _muni_pct(quarter, province_id=None):
        rows = [dict(m) for m in _muni(quarter, province_id=None)]
        for m in rows:
            v, p = VUL.get(m["lguCode"]), m.get("provinceEstimate")
            if v is not None and p is not None:
                m["vulnerabilityIndex"], m["riskIndex"], m["rankingMethod"] = round(float(v), 6), round(float(p) * float(v), 4), METHOD
                m["_u"] = float(p) * float(v)
            used = POV.get(m["lguCode"])
            if used is not None and (m.get("povertyValueUsed") is None or abs(float(m["povertyValueUsed"]) - used[0]) > 1e-6):
                m["povertyRate"], m["povertyValueUsed"] = used[0], used[0]
                m["povertyEstimateKind"] = f"PSA city or municipal estimate: {used[1]}"
                m["povertyLimitation"] = ("PSA publishes this figure rounded to the whole percent." if "whole percent" in used[1]
                                          else None)
        scored = sorted([m for m in rows if "_u" in m], key=lambda m: (-m["_u"], m["lguCode"]))
        for i, m in enumerate(scored, 1):
            m["rankRegion"] = i
        for prov in {m["provinceId"] for m in scored}:
            for i, m in enumerate([x for x in scored if x["provinceId"] == prov], 1):
                m["rankInProvince"] = i
        for m in rows:
            m.pop("_u", None)
            m["tied"] = False
        return [m for m in rows if province_id is None or m["provinceId"] == province_id]
    _D.municipality_summary = _muni_pct

    # ---- "Latest data used": drop duplicate rows, give local prices and GRDP the served issue's periods
    _data_used = HS.data_used

    def _data_used_final():
        d = _data_used()
        F = HS._FACTS
        items = [dict(it) for it in d.get("items", []) if it.get("group") not in ("ag_vulnerability", "ag_production")]
        for it in items:
            if it.get("group") == "food_market":
                it["when"], it["period"] = F["local_prices"], f"{F['local_prices']} (3 months ending 3 months before the issue quarter)"
            elif it.get("group") == "household_economy":
                it["when"], it["period"] = str(F["grdp_year"]), f"{F['grdp_year']} (latest year published by the issue date)"
            elif it.get("name") == "Rice and corn harvest":
                it["when"], it["period"] = _harvest_window(F["cutoff"])
        # news: the window the issue's news inputs actually read (an issue that reused earlier news inputs records it)
        win = json.loads(SV.LIVE.read_text(encoding="utf-8")).get("news_window") if SV.LIVE.exists() else None
        if win:
            a, b = (pd.Timestamp(x) for x in win.split(" to "))
            for it in items:
                if it.get("label") == "News" or str(it.get("name", "")).startswith("News"):
                    it["when"] = _months(a, b)
                    it["period"] = f"{a:%d %B %Y} to {b:%d %B %Y}".replace(" 0", " ").lstrip("0")
        return {**d, "items": items}

    def _harvest_window(cutoff):
        """The four quarters FINAL's harvest inputs used: a quarter counts 45 days after it ends (app.hcw.inputs ->
        app.e137.features._published_quarters, no download rule). Audit 2026-11-14: the panel said Oct 2025-Sep 2026 (the
        E168 download rule) while the inputs used Q3 2025-Q2 2026."""
        cut = pd.Timestamp(cutoff)
        y, q = cut.year, (cut.month - 1) // 3 + 1
        while True:
            q, y = (q - 1, y) if q > 1 else (4, y - 1)
            end = pd.Timestamp(year=y, month=3 * q, day=1) + pd.offsets.MonthEnd(0)
            if end + pd.Timedelta(days=45) <= cut:
                break
        last = pd.Period(f"{y}Q{q}", "Q")
        first, prev = last - 3, last - 7
        mon = lambda p, e: (p.end_time if e else p.start_time).strftime("%b %Y")
        return (f"{mon(first, 0)}–{mon(last, 1)}",
                f"Q{first.quarter} {first.year} to Q{last.quarter} {last.year}, compared with Q{prev.quarter} {prev.year} to "
                f"Q{(last - 4).quarter} {(last - 4).year} (a quarter counts 45 days after it ends)")
    HS.data_used = _data_used_final

    # ---- evaluation: the served leads (period.max_lead) and the five-metric rule
    _evaluation0 = HS.evaluation

    @functools.lru_cache(maxsize=1)
    def _evaluation_final():
        ev = _evaluation0()
        L = PD.max_lead()
        rule = PD.serving().get("lead_basis", "")
        ev = {**ev, "max_reliable_lead": L, "acceptance_rule": rule, "protocol_name": "owner five-metric acceptance (2026-11-13), pooled walk-forward, FINAL"}
        ev["leads"] = {k: {**v, "reliable": int(k) <= L} for k, v in ev["leads"].items()}
        hz = dict(ev["horizon"]); hz["max_reliable_lead"] = L
        hz["leads"] = {k: {**v, "reliable": int(k) <= L} for k, v in hz["leads"].items()}
        hz["individually_passing_leads"] = list(range(1, L + 1))
        hz["why_not_longer"] = "From Lead 3 pooled precision (73.1%) and F1 (74.5%) fall below 75%."
        ev["horizon"] = hz
        return ev
    HS.evaluation = _evaluation_final
    _horizon0 = HS.horizon

    def _horizon_final():
        # /final/risk/rows: the horizon note is FINAL's own (it carried Setup H's "Lead 7 ... up to Lead 18"; audit 2026-11-14)
        return {**_horizon0(), "why_not_longer": HS.evaluation()["horizon"]["why_not_longer"]}
    HS.horizon = _horizon_final

    # ---- factor groups as shown (merged, non-overlapping) + poverty bar
    HS.GROUPS = {"market": "Food prices", "ag_production": "Rice and corn harvests", "ag_vulnerability": "Dry spells and typhoons",
                 "employment": "Employment (national)", "household_economy": "Regional economy (GRDP)", "poverty": "Poverty level"}
    HS.BAR_COLS = {"market": ("shap_market", "shap_food_market"), "ag_production": ("shap_ag_production",),
                   "ag_vulnerability": ("shap_climate", "shap_ag_vulnerability"), "employment": ("shap_employment",),
                   "household_economy": ("shap_household_economy",), "poverty": ("shap_poverty",)}
    HS.OTHER_COLS = tuple(c for c in getattr(HS, "OTHER_COLS", ()) if c != "shap_poverty")
    HS.SHOWN_GROUPS, HS.GROUP_KEYS = dict(HS.GROUPS), tuple(HS.GROUPS)

    _plain0 = HS.plain_evidence

    def _plain_final(code, quarter, group):
        if group == "poverty":
            rs = HS._rs(code, quarter)
            if not rs:
                return None
            yr = HS._FACTS.get("poverty_round")
            src = f"latest official PSA poverty statistics ({yr}, released in {yr + 1})" if yr else "latest official PSA poverty statistics"
            if code is None:
                pps = [HS._pp(q, group) for q in rs]
                avg = sum(pps) / len(pps)
                eff = "On average it barely changed the provinces' forecasts." if abs(avg) < 0.05 else \
                    f"On average it {'raised' if avg > 0 else 'lowered'} each province's forecast by about {abs(avg):.1f} points."
                return f"The model uses each province's {src}. {eff} In tests on past surveys it was context, not a proven driver."
            pp = HS._pp(rs[0], group)
            eff = f"It barely changed {rs[0]['province']}'s forecast." if abs(pp) < 0.05 else \
                f"This {'raised' if pp > 0 else 'lowered'} {rs[0]['province']}'s forecast by about {abs(pp):.1f} points."
            return f"The model uses {rs[0]['province']}'s {src}. {eff} In tests on past surveys it was context, not a proven driver."
        t = _plain0(code, quarter, group)
        if t is None or group not in _OOS:
            return t
        return t + (" In tests on past surveys, forecasts got measurably worse without this group." if _OOS[group] else
                    " In tests on past surveys, forecasts were not measurably worse without this group, so read it as context.")
    HS.plain_evidence = _plain_final

    # ---- contributor bars: groups that move THIS forecast share by >= MIN_PP points; the rest is "Other"
    def _pp_effect(r, c):
        z = math.log(float(r["baseline_pct"]) / (100 - float(r["baseline_pct"]))) + float(r["change_logit"])
        return 100 * (1 / (1 + math.exp(-z)) - 1 / (1 + math.exp(-(z - c))))

    def _shap_parts(r):
        cols = [k for k in r if k.startswith("shap_") and not k.startswith("shap_news_")]
        stored = sum(HS._f(r.get(c)) or 0.0 for c in cols)
        return cols, stored, float(r["change_logit"]) - stored

    _drivers_all = HS.drivers

    def _drivers_meaningful(code, quarter, base):
        out = _drivers_all(code, quarter, base)
        r = HS.row(code, quarter)
        if r is None or "drivers" not in out:
            return out
        cols, _, expv = _shap_parts(r)
        bar_cols = {c for g in HS.GROUPS for c in HS.BAR_COLS[g]}
        rest = sum(abs(HS._f(r.get(c)) or 0.0) for c in cols if c not in bar_cols)
        kept, small = [], []
        for d in out["drivers"]:
            role, why = EVIDENCE_ROLE.get(d["driver_group"], ("model input, not validated", "no group-level out-of-sample test"))
            pp = float(_pp_effect(r, d["group_shap"]))
            (kept if abs(pp) >= MIN_PP else small).append({**d, "effect_pp": round(pp, 2), "evidence_role": role, "evidence": why})
        other_abs = rest + sum(abs(d["group_shap"]) for d in small)
        tot = sum(abs(d["group_shap"]) for d in kept) + other_abs
        return {**out, "drivers": kept, "other_abs": other_abs, "other_pct": round(100 * other_abs / tot, 1) if tot else 0.0,
                "expected_value_logit": round(expv, 6), "hidden_groups": [d["driver_group"] for d in small], "demoted_groups": [],
                "attribution_basis": r.get("attribution_basis")}
    HS.drivers = _drivers_meaningful

    _bar_table0 = _RPT._bar_table

    def _bar_table_or_note(rows, width):
        if rows:
            return _bar_table0(rows, width)
        return _RPT._p(f"No single factor group moved this forecast by {MIN_PP:g} percentage point or more. The forecast is set by the "
                       "province's latest survey level and the time elapsed since it (\"Other model inputs\").", "cell")
    _RPT._bar_table = _bar_table_or_note

    # ---- the chance of HIGH is quoted from p_high (the served "probability" column holds the share)
    _sentence = HS.sentence

    def _chance(p):
        return "less than 1 in 100" if p < 0.005 else f"about {round(p * 100)} in 100"

    def _sentence_fixed(code, name, quarter, mean_p=None):
        s = _sentence(code, name, quarter, mean_p)
        r = HS.row(code, quarter) if code else None
        if s and r is not None and "p_high" in r:
            s = s.replace(f"chance of that is {_chance(float(r['probability']))}", f"chance of that is {_chance(float(r['p_high']))}")
        return s
    HS.sentence = _sentence_fixed

    # ---- serving model and data completeness follow the served issue
    def _serving_model():
        ev = HS.evaluation()
        F = HS._FACTS
        return {"mode": "final", "model": HS.MODEL_ID, "issued": F["cutoff"], "issueQuarter": F["issue"],
                "targetQuarter": F["targets"][min(F["targets"])], "lead": 1, "servedLeads": F["leads"],
                "maxReliableLead": ev["max_reliable_lead"]}
    HS.serving_model = _serving_model

    _status0 = HS.data_status

    def _data_status(code, quarter):
        st, msg = _status0(code, quarter)
        return st, re.sub(r"regional GRDP \(\d{4}\)", f"regional GRDP ({HS._FACTS['grdp_year']})", msg)
    HS.data_status = _data_status

    # ---- /explainability (Visualization "Why is this at risk?", its PDF, the panels' fallbacks): the same exact FINAL SHAP
    # groups as the dashboard cards (/final/shap), never another model's grouping next to a FINAL forecast
    from app.final import shap_api as _SA
    from app.services import reference as _ref
    _expl0, _expl_reg0 = _D.explainability, _D.explainability_region

    def _final_groups(pid, quarter, base):
        d = _SA.province(pid, quarter)
        if not d.get("available"):
            return base
        trig = [{"key": g["key"], "label": g["label"], "share": round(g["pct"] / 100, 4), "pct": int(g["pct"]),
                 "signedContribution": float(g["signedContribution"]), "direction": g["direction"],
                 "color": _D.trigger_color(int(g["pct"]), g["direction"]), "status": g["status"],
                 "statusNote": ("This moved the forecast in the direction shown (model influence, not a cause)."
                                if g["status"] == "contributes" else "This had almost no effect on this forecast."),
                 "evidenceNote": None, "plainEvidence": g["plainEvidence"], "newsSignalProportion": None}
                for g in d["groups"]]
        return {**base, "quarter": quarter, "triggers": trig, "otherPct": d["otherPct"], "otherAbs": None,
                "model": "final-rate-mind-1.0", "summaryLines": d.get("summary")}

    def _explainability_final(code, quarter):
        try:
            base = _expl0(code, quarter)
        except Exception:
            base = {"articleCount": _D.article_count(code, quarter), "triggerMatchedArticles": 0}
        return _final_groups(_ref.province_slug(code), quarter, base)

    def _explainability_region_final(quarter):
        try:
            base = _expl_reg0(quarter)
        except Exception:
            base = {"articleCount": 0, "triggerMatchedArticles": 0}
        return _final_groups("calabarzon", quarter, base)
    _D.explainability, _D.explainability_region = _explainability_final, _explainability_region_final

    OLD, NEW = "Setup H + class weights", "FINAL (RATE + MIND)"
    for k, v in list(vars(HS).items()):
        if not k.startswith("_") and isinstance(v, str) and OLD in v:
            setattr(HS, k, v.replace(OLD, NEW))
    # the province value behind a town is FINAL's forecast SHARE of food-insecure households, not a probability (audit 2026-11-14)
    HS.LGU_BASIS = ("Relative position within the province: the province's FINAL (RATE + MIND) forecast share of food-insecure "
                    "households re-weighted by PSA poverty incidence (60%) and population density (40%), as Objective 3 specifies. Not a "
                    "measured or official municipal food-insecurity rate or forecast; the ranking has not been checked against municipal outcomes.")
    HS.LGU_LEVEL_BASIS = ("Colour = the province's FINAL (RATE + MIND) risk class (High when 50% or more of its households are forecast to be "
                          "food insecure). The number and rank are this city's or municipality's priority within the province: the province "
                          "forecast share re-weighted by PSA poverty incidence (60%) and population density (40%). Not a measured or official "
                          "municipal food-insecurity rate; the ranking has not been checked against municipal outcomes.")
