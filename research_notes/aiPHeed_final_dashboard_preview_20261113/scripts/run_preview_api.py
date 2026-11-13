r"""LOCAL PREVIEW API for FINAL (RATE + MIND). Runs the H_cw branch backend (C:\Users\admin\aipheed_hcw\backend) unchanged on disk,
and, inside this process only, points its dashboard module (app.ml.inference.hcw_system) and its outlook (app.hcw.serve) at
FINAL's preview files (../out: live.json, dashboard_rows.csv, lead_horizon.json, thesis_metrics.json) and relabels the model's name in
user-facing text. No branch file, registry, artifact or seal is modified. Database: a scratch SQLite file in ../out.
Run from C:\Users\admin\aipheed_hcw\backend:  python run_preview_api.py [port]"""
import os, sys
from pathlib import Path

PREV = Path(__file__).resolve().parents[1] / os.environ.get("PREVIEW_OUT", "out")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8975
os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(PREV / 'preview.db').as_posix()}")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8095")
sys.path.insert(0, os.getcwd())

from app.ml.inference import hcw_system as HS        # noqa: E402
from app.hcw import serve as SV                       # noqa: E402

HS.DATA, HS.ROWS = PREV, PREV / "dashboard_rows.csv"
SV.OUT, SV.LIVE, SV.ROWS = PREV, PREV / "live.json", PREV / "dashboard_rows.csv"

# Display basis (LONG_GAP_CORRECTION_PROTOCOL.md): the dashboard's "risk level" number is the forecast food insecurity risk,
# i.e. the forecast share of households moderately or severely food insecure (HFIAS) as a decimal 0-1, HIGH at 0.50. The
# chance of HIGH is kept in column p_high and shown as a secondary line. Only a served copy is written; the built rows stay as built.
if os.environ.get("PREVIEW_RISK_LEVEL", "share") == "share":
    import pandas as _pd
    _r = _pd.read_csv(PREV / "dashboard_rows.csv")
    _r["p_high"] = _r["probability"]
    _r["probability"] = (_r["score_pct"] / 100.0).round(3)
    HS.ROWS = PREV / "dashboard_rows_served.csv"
    _r.to_csv(HS.ROWS, index=False, lineterminator="\n")
    _province_row = HS.province_row

    def _row_share(code, name, quarter, base):
        out = _province_row(code, name, quarter, base)
        if out is None:
            return None
        r = HS.row(code, quarter)
        lvl, ph = float(r["probability"]), float(r["p_high"])
        out["score_type"] = "final_forecast_food_insecurity_risk"
        out["confidence_statement"] = (f"{name}, {quarter}: food insecurity risk {lvl:.2f} (forecast share of households moderately or "
                                       f"severely food insecure; HIGH at 0.50), class {r['class']}; chance of HIGH {ph:.3f}. "
                                       f"{out['horizon_label']}")
        return out

    HS.province_row = _row_share

# Town and city ranking: the min-max-within-province scaling gives the least vulnerable LGU of every province a weight of
# exactly 0 (shown as 0.00). The preview uses the owner-recorded Option A basis instead (app/e145/lgu.py): vulnerability =
# 0.6 x poverty percentile + 0.4 x density percentile across the 142 LGUs, which keeps the same weights and order logic.
if os.environ.get("PREVIEW_LGU_BASIS", "percentile") == "percentile":
    import pandas as _pd
    from app.services import dashboard as _D
    from app.e145 import lgu as _L
    _V = _pd.read_csv(_L.BASE, dtype={"lgu_psgc": str})
    _V["code"] = _V["lgu_psgc"].str.zfill(9)
    _VUL = dict(zip(_V["code"], _L.W_POVERTY * _V["pct_poverty"] + _L.W_DENSITY * _V["pct_density"]))
    _muni = _D.municipality_summary
    _METHOD = ("vulnerability = 0.6 x poverty percentile + 0.4 x density percentile across the 142 LGUs (owner Option A, app/e145/lgu.py); "
               "priority = province food insecurity risk x vulnerability, 4 dp; ranked on the unrounded value. A relative "
               "prioritisation within the province forecast, not a municipal forecast.")

    def _muni_pct(quarter, province_id=None):
        rows = [dict(m) for m in _muni(quarter, province_id=None)]
        for m in rows:
            v, p = _VUL.get(m["lguCode"]), m.get("provinceEstimate")
            if v is not None and p is not None:
                m["vulnerabilityIndex"], m["riskIndex"], m["rankingMethod"] = round(float(v), 6), round(float(p) * float(v), 4), _METHOD
                m["_u"] = float(p) * float(v)
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

# "Latest data used" list: the branch appends four rows with vague periods; two repeat rows already listed
# (Rice & corn output = Rice & corn harvest; Dry spells & typhoons = Rainfall + Typhoons). The preview drops those two and gives the
# other two their actual periods for this issue (2026-Q4): local prices = 3 months ending 3 months before 1 Oct 2026
# (app/e152/panel.py LAG_M = 3, window n = 3); regional GRDP = E154.available_year(2026-Q4) = 2025 (value present in the rows).
_data_used = HS.data_used


def _data_used_preview():
    d = _data_used()
    items = [dict(it) for it in d.get("items", []) if it.get("group") not in ("ag_vulnerability", "ag_production")]
    for it in items:
        if it.get("group") == "food_market":
            it["when"], it["period"] = "May–Jul 2026", "May–Jul 2026 (3 months ending 3 months before the issue)"
        elif it.get("group") == "household_economy":
            it["when"], it["period"] = "2025", "2025 (latest year published by the issue date)"
    return {**d, "items": items}


HS.data_used = _data_used_preview

# Contributor bars: only what is meaningful for THIS forecast (owner instruction 2026-11-13). A group is shown only when its exact
# LightGBM contribution moves this province-quarter's forecast share by at least MIN_PP percentage points:
#   effect = 100 x [sigmoid(z) - sigmoid(z - c)],  z = logit(survey baseline) + change_logit,  c = the group's contribution.
# Everything else moved into "Other model inputs", so the bars plus Other still cover 100 % of the forecast change:
#   - groups below MIN_PP (their |c| is added, nothing is dropped from the total);
#   - the elapsed-time trend (change_logit minus all stored contributions), which the built rows leave out of every column
#     although it is the largest single part of the change. It belongs under "forecast timing and survey history".
# The forecast itself is unchanged; this only decides which bars are drawn. PREVIEW_MIN_PP=0 restores every bar.
import numpy as _np

# Groups by what the inputs measure, with no overlap, following the contributor evidence (owner briefs 2026-11-13: "make it clear the
# grouping"; "official model selection" Section 6). The branch had seven bars, several measuring the same thing:
#   Food prices              = market (PSA food and rice CPI) + food_market (local rice, palay, farmgate and fish prices)
#   Rice and corn harvests   = ag_production: palay/corn output by crop + the combined farm-output inputs (c_agri_yoy, agri_since,
#                              moved from Climate at build time by build_corrected.py, PREVIEW_HARVEST_SPLIT). Agriculture and fish is
#                              the group with out-of-sample support (06_CONTRIBUTOR_GROUP_VALIDATION.md).
#   Dry spells and typhoons  = climate (rain/soil anomalies, typhoons, ENSO) + ag_vulnerability (dry months, rainfall, typhoon exposure)
#   Employment               = unchanged (national series)
#   Regional economy         = household_economy (regional GRDP; the same for every CALABARZON province)
# Contributions are exact and additive, so a merged bar is the sum of its columns; nothing is re-estimated. Keys and names are the
# ones the approved frontend already has (market "Food prices", ag_production "Rice and corn harvests", ag_vulnerability "Dry spells
# and typhoons"). PREVIEW_MERGE_GROUPS=0 restores the seven branch bars. Poverty and density stay in "Other" (thesis: LGU weights).
if os.environ.get("PREVIEW_MERGE_GROUPS", "1") == "1":
    HS.GROUPS = {"market": "Food prices", "ag_production": "Rice and corn harvests", "ag_vulnerability": "Dry spells and typhoons",
                 "employment": "Employment (national)", "household_economy": "Regional economy (GRDP)"}
    HS.BAR_COLS = {"market": ("shap_market", "shap_food_market"), "ag_production": ("shap_ag_production",),
                   "ag_vulnerability": ("shap_climate", "shap_ag_vulnerability"),
                   "employment": ("shap_employment",), "household_economy": ("shap_household_economy",)}
    HS.SHOWN_GROUPS = dict(HS.GROUPS)
    HS.GROUP_KEYS = tuple(HS.GROUPS)
    # evidence of a shown group = its parts' sentences (each part keeps its own columns for that, never drawn as a bar)
    _MERGED = {"market": ("market", "food_market"), "ag_production": ("climate", "ag_production"), "ag_vulnerability": ("climate", "ag_vulnerability")}
    _PART_COLS = {"market": ("shap_market",), "food_market": ("shap_food_market",), "climate": ("shap_climate",),
                  "ag_vulnerability_part": ("shap_ag_vulnerability",), "ag_production_part": ("shap_ag_production",)}
    import re as _re
    _EFFECT = _re.compile(r"\s*(This (raised|lowered) .+? points\.|It barely changed .+?forecast\.|On average it (raised|lowered) .+? points\.|"
                          r"On average it barely changed .+?forecasts\.)")
    _DROP = ("Typhoons, dry weather and poor harvests", "Typhoons, soil moisture and farm harvests also count", "Dry spells and typhoons can cut",
             "Smaller harvests mean", "Bigger harvests mean", "Higher local rice prices make", "Taken together, local rice and palay prices",
             "Taken together, food prices here")
    _plain_part = HS.plain_evidence
    _sent = lambda t: [s.strip() for s in _re.split(r"(?<=[a-z%)\]])\. (?=[A-Z0-9])", t.strip().rstrip(".")) if s.strip()]

    def _part_text(code, quarter, part):
        """A part group's own evidence sentence; the part's columns are put in BAR_COLS only for this call."""
        saved = dict(HS.BAR_COLS)
        HS.BAR_COLS.update({"market": ("shap_market",), "climate": ("shap_climate",), "food_market": ("shap_food_market",),
                            "ag_vulnerability": ("shap_ag_vulnerability",), "ag_production": ("shap_ag_production",)})
        try:
            t = _plain_part(code, quarter, part)
        finally:
            HS.BAR_COLS.clear(); HS.BAR_COLS.update(saved)
        return None if (t is None or t.startswith("No figures had been published yet")) else _EFFECT.sub("", t).strip()

    def _body(group, texts, region):
        if group == "ag_production":          # combined harvest sentence from the climate text + the by-crop sentence
            clim, prod = (t or "" for t in texts)
            keep = [s for s in _sent(clim) if "harvests in" in s or "Rice and corn output" in s]
            keep += [s for s in _sent(prod) if not s.startswith(_DROP)]
            tail = "" if region else " Harvests affect local food supply and farm income."
            return (". ".join(keep) + "." + tail) if keep else None
        if group == "ag_vulnerability":       # weather sentences from the climate text + the dry-months clause
            clim, vul = (t or "" for t in texts)
            keep = [s.replace(" Typhoons, soil moisture and farm harvests also count", "") for s in _sent(clim)
                    if "harvests in" not in s and not s.startswith(_DROP)]
            m = _re.search(r"(\d+) of the last 6 months had less than half the usual rain", vul)
            if m:
                keep.append(m.group(0)[0].upper() + m.group(0)[1:])
            elif region and vul:
                keep += [s for s in _sent(vul) if not s.startswith(_DROP)]
            tail = "" if region else " Dry spells and typhoons can cut harvests and incomes."
            return (". ".join(keep) + "." + tail) if keep else None
        keep = [s for t in texts if t for s in _sent(t) if not s.startswith(_DROP)]
        return ". ".join(keep) + "." if keep else None

    def _plain_merged(code, quarter, group):
        if group not in _MERGED:
            return _plain_part(code, quarter, group)
        texts = [_part_text(code, quarter, p) for p in _MERGED[group]]
        body = _body(group, texts, code is None)
        if not body:
            return "No figures had been published yet when this forecast was made. That does not mean the risk is low."
        rs = HS._rs(code, quarter)
        if code is None:
            pps = [HS._pp(q, group) for q in rs]
            avg = sum(pps) / len(pps) if pps else 0.0
            eff = ("Taken together, on average it barely changed the provinces' forecasts." if abs(avg) < 0.05 else
                   f"Taken together, on average it {'raised' if avg > 0 else 'lowered'} each province's forecast by about {abs(avg):.1f} points.")
        else:
            pp = HS._pp(rs[0], group)
            eff = (f"Taken together, it barely changed {rs[0]['province']}'s forecast." if abs(pp) < 0.05 else
                   f"Taken together, this {'raised' if pp > 0 else 'lowered'} {rs[0]['province']}'s forecast by about {abs(pp):.1f} points.")
        return body + " " + eff

    # Predictive versus contextual (official-model brief 2026-11-13, Section 6D): one sentence from the retraining ablation
    # (aiPHeed_final_reliability_20261113/06_CONTRIBUTOR_GROUP_VALIDATION.md; aiPHeed_final_official_20261113 report 13), written into the
    # existing explanation text, so DA staff can tell model-supported factors from context. No new UI element.
    _OOS = {"household_economy": True, "ag_production": True, "market": False, "ag_vulnerability": False, "employment": False}
    _plain_merged0 = _plain_merged

    def _plain_with_support(code, quarter, group):
        t = _plain_merged0(code, quarter, group)
        if t is None or group not in _OOS:
            return t
        return t + (" In tests on past surveys, forecasts got measurably worse without this group." if _OOS[group] else
                    " In tests on past surveys, forecasts were not measurably worse without this group, so read it as context.")

    HS.plain_evidence = _plain_with_support

MIN_PP = float(os.environ.get("PREVIEW_MIN_PP", "1.0"))

# PDF report: with the MIN_PP rule a forecast can have no factor bar at all (e.g. Cavite 2027-Q1), and reportlab refuses an empty
# table. Write one plain sentence in its place (text only, same report layout).
from app.services import report as _RPT
_bar_table0 = _RPT._bar_table


def _bar_table_or_note(rows, width):
    if rows:
        return _bar_table0(rows, width)
    return _RPT._p(f"No single factor group moved this forecast by {MIN_PP:g} percentage point or more. The forecast is set by the "
                   "province's latest survey level and the time elapsed since it (\"Other model inputs\").", "cell")


_RPT._bar_table = _bar_table_or_note
_drivers_all = HS.drivers


def _pp_effect(r, c):
    z = _np.log(float(r["baseline_pct"]) / (100 - float(r["baseline_pct"]))) + float(r["change_logit"])
    return 100 * (1 / (1 + _np.exp(-z)) - 1 / (1 + _np.exp(-(z - c))))


def _drivers_meaningful(code, quarter, base):
    out = _drivers_all(code, quarter, base)
    r = HS.row(code, quarter)
    if r is None or "drivers" not in out or MIN_PP <= 0:
        return out
    # shap_news_<g> is the news part INSIDE shap_<g> (build_corrected.py), so it is not counted again
    shap_cols = [k for k in r if k.startswith("shap_") and not k.startswith("shap_news_")]
    bar_cols = {c for g in HS.GROUPS for c in HS.BAR_COLS[g]}
    stored = sum(HS._f(r.get(c)) or 0.0 for c in shap_cols)
    trend = float(r["change_logit"]) - stored
    unmapped = sum(abs(HS._f(r.get(c)) or 0.0) for c in shap_cols if c not in bar_cols and c not in HS.OTHER_COLS)
    kept, folded = [], 0.0
    for d in out["drivers"]:
        if abs(_pp_effect(r, d["group_shap"])) >= MIN_PP:
            kept.append({**d, "effect_pp": round(float(_pp_effect(r, d["group_shap"])), 2)})
        else:
            folded += abs(d["group_shap"])
    other_abs = out.get("other_abs", 0.0) + folded + unmapped + abs(trend)
    tot = sum(abs(d["group_shap"]) for d in kept) + other_abs
    return {**out, "drivers": kept, "other_abs": other_abs, "other_pct": round(100 * other_abs / tot, 1) if tot else 0.0,
            "trend_logit": round(trend, 6),
            "hidden_groups": [d["driver_group"] for d in out["drivers"] if abs(_pp_effect(r, d["group_shap"])) < MIN_PP]}


HS.drivers = _drivers_meaningful
_evidence_note = HS.evidence_note


def _evidence_note_meaningful(code, quarter, other_pct=None, group=None):
    note = _evidence_note(code, quarter, other_pct, group)
    if MIN_PP > 0:
        note += (f" Only factors that move this forecast by at least {MIN_PP:g} percentage point are shown; smaller pushes, and the change "
                 f"expected from the time elapsed since the last survey, are part of \"Other model inputs\".")
    return note


HS.evidence_note = _evidence_note_meaningful

# The served rows carry the forecast SHARE in "probability" (display basis above), so the branch sentence quoted the share as the
# "chance of HIGH" (Batangas: "about 22 in 100" when the chance is 0.001). State the chance from p_high, the actual probability.
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

OLD, NEW = "Setup H + class weights", "FINAL (RATE + MIND)"


def sub(x):
    if isinstance(x, str):
        return x.replace(OLD, NEW)
    if isinstance(x, dict):
        return {k: sub(v) for k, v in x.items()}
    if isinstance(x, tuple):
        return tuple(sub(v) for v in x)
    return x


for k, v in list(vars(HS).items()):
    if not k.startswith("_") and isinstance(v, (str, dict, tuple)) and OLD in str(v):
        setattr(HS, k, sub(v))
HS.INDICATOR = {**HS.INDICATOR,
                "id": "final_food_insecurity_risk",
                "name": "Food-insecurity risk (FINAL RATE + MIND LightGBM, LOCAL PREVIEW): probability that the province is HIGH",
                "horizon": ("issued with data published before 2026-11-01; Lead 1 = 2027-Q1 to Lead 5 = 2028-Q1. Leads 1-5 meet the project "
                            "acceptance rule (accuracy >= 75% and better than the latest survey), retrospectively; the stricter robust rule holds to Lead 4."),
                "caveat": ("LOCAL PREVIEW of a research model; not the public forecast (E196) and not validated for deployment. A forecast risk "
                           "class, not a measured food-insecurity rate. Walk-forward on 72 provincial forecasts from 3 survey rounds: accuracy 86.1% "
                           "one quarter ahead (precision 0.80, recall 0.80, F1 0.80, AUC 0.90) against 62.5% for the latest survey alone. Those rows "
                           "were reused during development, and in the 2021 round only 1 of 4 HIGH provinces was found.")}

from app.main import app                              # noqa: E402
import uvicorn                                        # noqa: E402

if __name__ == "__main__":
    print(f"FINAL preview API on http://127.0.0.1:{PORT} reading {PREV}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
