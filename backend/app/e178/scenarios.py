"""
E178 Part A: what the frozen E168 procedure does with synthetic scenario inputs (docs/e178/PROTOCOL.md, Part A).

The live issue that is in production (the registry artifact, cut-off 2026-11-01) is re-run through
app.e168.serve._forecast unchanged. Its call to app.e168.lgbm_only.run_proc is wrapped only to append scenario copies of
the five live rows to the test frame and to read LightGBM's pred_contrib on them. The training rows, the selected
configuration, the fitted model and the calibration are E168's. A test row's output depends only on the training rows and
that row, so the S0 slice is what production computes; it is checked against the production artifact and its dashboard
rows before anything is written.

    python -m app.e178.scenarios run      -> data/e178/synthetic/ (inputs, outputs, S4, S5, summary, run log, hashes)
    python -m app.e178.scenarios charts   -> docs/e178/img/*.png

Every row except S0 is synthetic and labelled (is_synthetic, scenario_id, generator_seed).
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from contextlib import nullcontext

import numpy as np
import pandas as pd

from app.e178 import common as K

warnings.filterwarnings("ignore")
MODULE = "app.e178.scenarios"
ISSUE = "2026-Q4"
LEADS = (1, 2, 3)
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))
logit = lambda s: np.log(np.asarray(s, float) / (100 - np.asarray(s, float)))

# Trigger groups shown to the panel, official-statistics columns only, with the stress direction of each column:
# Pv.SIGN where the model constrains it, otherwise the documented El Nino / drought / price direction (UNSIGNED).
GROUPS = {
    "weather_farm": {"c_tc_4q": 1, "tc_rate_since": 1, "c_agri_yoy": -1, "agri_since": -1, "oni": 1,
                     "c_rain_anom_6m": -1, "c_soil_anom_3m": -1, "rain_since": -1, "soil_since": -1},
    "food_prices": {"cpi_food_yoy": 1, "cpi_rice_yoy": 1, "cpi_food_3m": 1, "cpi_food_accel": 1, "cpi_since": 1,
                    "cpi_food_rel_nat": 1},
    "jobs": {"unemp_rate": 1, "unemp_yoy": 1, "unemp_chg_since": 1, "unemp_region": 1},
    "remittances": {"remit_yoy": -1, "remit_since": -1, "remit_q_yoy": -1},
    "fish_catch": {"c_fish_yoy": -1},
}
UNSIGNED = {"oni", "c_rain_anom_6m", "c_soil_anom_3m", "rain_since", "soil_since", "cpi_food_rel_nat"}
GROUP_LABEL = {"weather_farm": "Weather and farm", "food_prices": "Food prices", "jobs": "Jobs",
               "remittances": "Remittances", "fish_catch": "Fish catch"}
SHOCKS = {
    "typhoon": {"c_tc_4q": 1, "tc_rate_since": 1, "c_agri_yoy": -1, "agri_since": -1},
    "el_nino_drought": {"oni": 1, "c_rain_anom_6m": -1, "c_soil_anom_3m": -1, "rain_since": -1, "soil_since": -1,
                        "c_agri_yoy": -1, "agri_since": -1},
    "rice_price_spike": GROUPS["food_prices"],
    "job_loss": GROUPS["jobs"],
    "remittance_drop": GROUPS["remittances"],
    "low_fish_catch": GROUPS["fish_catch"],
}
SHOCKS["combined"] = {c: d for s in list(SHOCKS.values()) for c, d in s.items()}
SHOCK_LABEL = {"typhoon": "Typhoon", "el_nino_drought": "El Niño drought", "rice_price_spike": "Rice and food price spike",
               "job_loss": "Job loss", "remittance_drop": "Remittance drop", "low_fish_catch": "Low fish catch",
               "combined": "All shocks combined"}
K_SD = (-2, -1, 1, 2)
N_NOISE, SEED_NOISE = 100, 17810
MASKS = ((0.25, 17811), (0.50, 17812), (0.75, 17813))
N_MASK = 20
T_LADDER = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)
DELTAS = tuple(round(0.1 * k, 1) for k in range(1, 21))
SCENARIO_TITLES = {"S0": "Baseline (real latest inputs)", "S1": "Perturbation / sensitivity", "S2": "Limited data",
                   "S3": "High-risk shock", "S3-B": "High-risk shock with a hypothetical worse survey baseline",
                   "S4": "High-risk response", "S5": "Municipal high-risk sample"}
MODEL_NOTE = "e168-lgbm-1.0 frozen procedure, scenario inputs (not a forecast)"


# --------------------------------------------------------------------------------------------------------- variants
def _variant(sid: str, name: str, te: pd.DataFrame, **kw) -> dict:
    return {"scenario_id": sid, "variant": name, "te": te, "delta": 0.0, "seed": None, "extrapolated": False,
            "clipped": 0, "masked": 0, "param": None, "group": None, **kw}


def _move(te0: pd.DataFrame, dirs: dict, f, B: pd.DataFrame, clip: bool) -> tuple[pd.DataFrame, int]:
    """Apply f(j, column, direction, x0) to each listed column; missing values stay missing."""
    te, nclip = te0.copy(), 0
    for j, (c, d) in enumerate(dirs.items()):
        if c not in te0.columns:
            continue
        x0 = te0[c].to_numpy(float)
        x = np.asarray(f(j, c, d, x0), float)
        if clip:
            xc = np.clip(x, B.at[c, "min"], B.at[c, "max"])
            nclip += int(np.sum((xc != x) & ~np.isnan(x0)))
            x = xc
        te[c] = np.where(np.isnan(x0), np.nan, x)
    return te, nclip


def scenario_columns(te0: pd.DataFrame) -> tuple[list[str], list[str]]:
    from app.e168 import lgbm_only as E
    groups = [c for g in GROUPS.values() for c in g if c in te0.columns]
    trig = [c for c in E.TRIG if c in te0.columns]
    return groups, trig


def build_variants(tr: pd.DataFrame, te0: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    """All S0-S3-B variants of the five live rows (docs/e178/PROTOCOL.md, Part A)."""
    groups, trig = scenario_columns(te0)
    te0 = te0.reset_index(drop=True).copy()
    num = sorted(set(groups) | set(trig))
    te0[num] = te0[num].astype(float)               # NaN-able; LightGBM reads float either way
    B = K.bounds([tr, te0], num)
    out = [_variant("S0", "real inputs", te0.copy())]
    for g, dirs in GROUPS.items():                  # S1: one group moved by k SD toward stress (k < 0: relief)
        for k in K_SD:
            te, n = _move(te0, dirs, lambda j, c, d, x, k=k: x + k * d * B.at[c, "sd"], B, clip=True)
            out.append(_variant("S1", f"{g}:{k:+d}SD", te, clipped=n, param=k, group=g))
    alld = {c: d for g in GROUPS.values() for c, d in g.items()}
    rng = np.random.default_rng(SEED_NOISE)
    for n_ in range(N_NOISE):                       # S1: joint noise on all five groups
        z = rng.standard_normal((len(alld), len(te0)))
        te, n = _move(te0, alld, lambda j, c, d, x, z=z: x + z[j] * B.at[c, "sd"], B, clip=True)
        out.append(_variant("S1", f"noise #{n_ + 1:03d}", te, clipped=n, seed=SEED_NOISE, param=n_ + 1, group="noise"))
    for f, seed in MASKS:                           # S2: random share of each row's trigger cells missing
        rng = np.random.default_rng(seed)
        for m in range(N_MASK):
            te, nm = te0.copy(), 0
            for r in range(len(te0)):
                avail = [c for c in trig if pd.notna(te0.at[r, c])]
                k = int(round(f * len(avail)))
                for c in rng.choice(np.array(avail, dtype=object), size=k, replace=False):
                    te.at[r, c] = np.nan
                nm += k
            out.append(_variant("S2", f"mask {int(f * 100)}% #{m + 1:02d}", te, masked=nm, seed=seed, param=f, group="mask"))
    te = te0.copy()
    te[trig] = np.nan
    out.append(_variant("S2", "all triggers missing", te, masked=int(te0[trig].notna().sum().sum()), param=1.0, group="all_missing"))
    for s, dirs in SHOCKS.items():                  # S3: move toward the historical extreme; t > 1 extrapolates
        for t in T_LADDER:
            def f(j, c, d, x, t=t):
                ext = B.at[c, "max"] if d > 0 else B.at[c, "min"]
                return x + t * (ext - x)
            te, _ = _move(te0, dirs, f, B, clip=False)
            out.append(_variant("S3", f"{s}:t={t:g}", te, extrapolated=t > 1, param=t, group=s))
    comb = next(v["te"] for v in out if v["variant"] == "combined:t=1")
    for dl in DELTAS:                               # S3-B: kept only if no S3 variant turns a province HIGH
        out.append(_variant("S3-B", f"combined:t=1+anchor+{dl:g}", comb.copy(), delta=dl, param=dl, group="combined"))
    return out, B


# ------------------------------------------------------------------------------------------------------- one lead
def _lead_job(lead: int, no2021: bool = False) -> dict:
    """serve._forecast(lead) with the scenario variants added to its test frame (or, with no2021, without ENNS2021)."""
    from app.e151 import prov as Pv
    from app.e168 import lgbm_only as E
    from app.e168 import serve as SV
    store: dict = {}
    orig_run, orig_pred = E.run_proc, E.LGBRes.predict

    def spy(tr, te, AN, ablate=False):
        te = te.reset_index(drop=True)
        if no2021:
            V, B = [_variant("S2", "latest survey round missing", te.copy(), group="latest_missing")], None
        else:
            V, B = build_variants(tr, te)
        te_all = pd.concat([v["te"] for v in V], ignore_index=True)
        n = len(te)
        dl = np.repeat([v["delta"] for v in V], n)
        AN_all = {a: (atr, np.tile(np.asarray(ate, float), len(V)) + dl) for a, (atr, ate) in AN.items()}
        cap: dict = {}

        def pred(self, X):
            if X is te_all:                          # the final model's call on the test frame (inner folds use tr)
                cap["contrib"], cap["cols"] = self.m_.predict(X[self.use_], pred_contrib=True), list(self.use_)
            return orig_pred(self, X)

        with K.patched(E.LGBRes, "predict", pred):
            P, chosen, tag, abl, inner, nf = orig_run(tr, te_all, AN_all, ablate)
        store.update(V=V, B=B, te_all=te_all, P=P, chosen=chosen, tag=tag, cap=cap, n=n, n_tr=len(tr), n_features=nf)
        return {k: (np.asarray(mu)[:n], np.asarray(p)[:n], np.asarray(h)[:n]) for k, (mu, p, h) in P.items()}, chosen, tag, abl, inner, nf

    orig_target = Pv.target_rows
    ctx = K.patched(Pv, "target_rows", lambda with_2021=False: orig_target(with_2021=False)) if no2021 else nullcontext()
    with K.sun_standin(), K.patched(E, "run_proc", spy), ctx:
        rows = SV._forecast(lead, ISSUE)
    out, inp = _assemble(store, lead)
    return {"lead": lead, "no2021": no2021, "forecast_rows": rows, "outputs": out, "inputs": inp, "config": store["tag"],
            "calibration": store["chosen"], "n_train_rows": store["n_tr"], "n_features": store["n_features"],
            "bounds": None if store["B"] is None else store["B"].round(6).reset_index(names="column").to_dict("records")}


def _assemble(st: dict, lead: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Output rows in the dashboard_rows schema (app.e168.dashboard_export._lead), plus the scenario columns."""
    from app.e163 import model as C
    from app.e168 import dashboard_export as X
    from app.e168 import lgbm_only as E
    from app.fi5.target import qindex, qlabel
    V, te_all, n = st["V"], st["te_all"], st["n"]
    mu, p, half = st["P"][st["chosen"]]
    contrib, cols = st["cap"]["contrib"], st["cap"]["cols"]
    news = set(E.NEWS)
    grp = [X.OWN_BAR.get(c) or (X.GROUPS.get(C.gmap(c)) if C.gmap(c) else None) for c in cols]
    issue_date, quarter = X._cutoff(ISSUE), qlabel(qindex(ISSUE) + lead)
    groups, trig = scenario_columns(te_all)
    rows, inputs = [], []
    for j in range(len(te_all)):
        v, k = V[j // n], j % n
        r = te_all.iloc[j]
        score = round(float(pct(mu[j])), 1)
        ph = float(p[j])
        g = {b: 0.0 for b in X.BARS}
        gn = {b: 0.0 for b in X.BARS}
        other = 0.0
        for i, c in enumerate(cols):
            if grp[i] is None:
                other += contrib[j][i]
            else:
                g[grp[i]] += contrib[j][i]
                if c in news:
                    gn[grp[i]] += contrib[j][i]
        change = float(contrib[j].sum())
        trig5 = sorted(((b, g[b]) for b in X.BARS if b != "poverty"), key=lambda t: -abs(t[1]))[:3]
        syn = v["scenario_id"] != "S0"
        o = {"province_code": X.CODES[r["province"]], "province": r["province"], "quarter": quarter, "lead": lead,
             "issue_date": issue_date, "probability": round(ph, 3), "class": "HIGH" if ph >= .5 else "LOW",
             "score_pct": score, "range90_low": round(float(pct(mu[j] - half[j])), 1),
             "range90_high": round(float(pct(mu[j] + half[j])), 1), "config": st["tag"],
             "baseline_pct": round(float(pct(logit(score) - change)), 2), "change_logit": round(change, 6),
             "bias_logit": round(float(contrib[j][-1]), 6), "shap_other": round(float(other), 6),
             "model": "e168-lgbm-1.0"}
        for b in X.BARS:
            o[f"shap_{b}"], o[f"shap_news_{b}"] = round(g[b], 6), round(gn[b], 6)
        for c in X.VALUES:
            o[f"val_{c}"] = None if c not in te_all or pd.isna(r[c]) else float(r[c])
        o.update({"scenario_id": v["scenario_id"], "variant": v["variant"], "group": v["group"], "param": v["param"],
                  "p_high_exact": ph, "range90_width_pts": round(float(pct(mu[j] + half[j]) - pct(mu[j] - half[j])), 2),
                  "gap_q": int(r["gap_q"]), "anchor_shift_logit": v["delta"], "extrapolated": bool(v["extrapolated"]),
                  "clipped_cells": int(v["clipped"]), "masked_cells": int(v["masked"]), "calibration": st["chosen"],
                  "top_driver_1": trig5[0][0], "top_driver_1_logit": round(trig5[0][1], 6),
                  "top_driver_2": trig5[1][0], "top_driver_2_logit": round(trig5[1][1], 6),
                  "top_driver_3": trig5[2][0], "top_driver_3_logit": round(trig5[2][1], 6),
                  "is_synthetic": syn, "generator_seed": v["seed"], "model_note": MODEL_NOTE})
        rows.append(o)
        inputs.append({"province": r["province"], "lead": lead, "quarter": quarter, "scenario_id": v["scenario_id"],
                       "variant": v["variant"], "gap_q": int(r["gap_q"]), "anchor_shift_logit": v["delta"],
                       "extrapolated": bool(v["extrapolated"]), "is_synthetic": syn, "generator_seed": v["seed"],
                       **{c: (None if pd.isna(r[c]) else float(r[c])) for c in sorted(set(groups) | set(trig))}})
    return pd.DataFrame(rows), pd.DataFrame(inputs)


# ---------------------------------------------------------------------------------------------------- S0 checks
def check_s0(results: list[dict], prod: dict) -> list[str]:
    """S0 must equal the production artifact (all 15 rows) and its dashboard rows (scores, classes and SHAP columns)."""
    from app.e168 import dashboard_export as X
    bad = []
    live = {(r["province"], int(r["lead"])): r for r in prod["live"]["provinces"]}
    dash = pd.read_csv(prod["dashboard_rows"]).set_index(["province", "lead"])
    seen = set()
    for res in (x for x in results if not x["no2021"]):
        for r in res["forecast_rows"]:
            key = (r["province"], int(r["lead"]))
            seen.add(key)
            a = live.get(key)
            for f in ("target_quarter", "score_pct", "range90_pct", "p_high", "risk_class", "config"):
                if a is None or a[f] != r[f]:
                    bad.append(f"{key} {f}: production {None if a is None else a[f]} vs S0 {r[f]}")
        s0 = res["outputs"][res["outputs"]["scenario_id"] == "S0"]
        for _, o in s0.iterrows():
            d = dash.loc[(o["province"], int(o["lead"]))]
            cols = ["probability", "score_pct", "range90_low", "range90_high", "baseline_pct", "change_logit", "bias_logit",
                    "shap_other"] + [f"shap_{b}" for b in X.BARS] + [f"shap_news_{b}" for b in X.BARS]
            for c in cols:
                if abs(float(d[c]) - float(o[c])) > 1e-9:
                    bad.append(f"{(o['province'], o['lead'])} dashboard {c}: production {d[c]} vs S0 {o[c]}")
            if d["class"] != o["class"] or d["config"] != o["config"]:
                bad.append(f"{(o['province'], o['lead'])} dashboard class/config differ")
    if seen != set(live):
        bad.append(f"S0 covers {sorted(seen)}, production {sorted(live)}")
    return bad


# ------------------------------------------------------------------------------------------------------- S4 and S5
def _texts(obj) -> list[str]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "text" and isinstance(v, str):
                out.append(v)
            else:
                out.extend(_texts(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(_texts(v))
    return out


def s4_s5(rows: pd.DataFrame, variant: str, log) -> tuple[dict, pd.DataFrame]:
    """The system's response to a HIGH result, computed by the production functions on the synthetic rows. The rows are
    swapped in only inside this offline process, for the duration; nothing is written to the database or to E168 files."""
    os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")            # the production configuration (.env.example)
    from app.ml.inference import e168_system as E
    from app.quarterly import alerts_e168 as AL
    from app.services import dashboard as svc
    from app.services import reference as ref
    from app.services import report_data as RD
    path = K.SYN / "s4_dashboard_rows.csv"
    rows.to_csv(path, index=False, lineterminator="\n")
    syn = E._rows.__wrapped__(str(path), 0)
    token = f"+e178-synthetic:{variant}"
    names = {ref.province_code(s): ref.PROVINCES[s]["name"] for s in ref.PROVINCES}

    def clear():
        for m in (svc, E):
            for f in vars(m).values():
                if hasattr(f, "cache_clear"):
                    f.cache_clear()

    clear()
    try:
        with K.patched(E, "rows", lambda: syn), K.patched(E, "state_token", lambda: token):
            assert E.active(), "E168 is not the production map model; S4 needs it"
            quarters = sorted(rows["quarter"].unique())
            high = sorted({(r.province_code, r.quarter) for r in rows.itertuples() if r.p_high_exact >= .5},
                          key=lambda t: (t[1], t[0]))
            alerts = AL.candidates()
            ranking = {q: [{"rank": i + 1, "province": x["province_name"], "p_high": x["risk_probability"], "band": x["band"]}
                           for i, x in enumerate(E.province_rows([], q, names))] for q in quarters}
            explain, report, muni = [], {}, []
            for code, q in high:
                d = E.drivers(code, q, {})
                explain.append({"province_code": code, "province": names[code], "quarter": q,
                                "lead": int(rows[(rows.province_code == code) & (rows.quarter == q)]["lead"].iloc[0]),
                                "drivers": d["drivers"], "other_pct": d["other_pct"],
                                "plain_evidence": {g: E.plain_evidence(code, q, g) for g in E.GROUPS},
                                "evidence_note": E.evidence_note(code, q),
                                "statement": E.province_row(code, names[code], q, None)["confidence_statement"]})
                slug = ref.province_slug(code)
                try:
                    report[f"{names[code]} {q}"] = _texts(RD.build_report("shap", "province", slug, q, q, set()))[:12]
                except Exception as e:                                # noqa: BLE001 - recorded, not hidden
                    report[f"{names[code]} {q}"] = [f"report not built: {type(e).__name__}: {e}"]
                ms = svc.municipality_summary(q, slug)
                for m in ms[:10]:
                    muni.append({"province": names[code], "quarter": q, "lead": explain[-1]["lead"],
                                 "rank_in_province": m["rankInProvince"], "municipality": m["name"], "lgu_code": m["lguCode"],
                                 "risk_index": m["riskIndex"], "risk_level": m["riskLevel"],
                                 "province_p_high": m["provinceEstimate"], "poverty_rate": m["povertyRate"],
                                 "population": m["population"], "disaggregation_label": m["disaggregationLabel"],
                                 "note": "reweighted provincial estimate, not a municipal forecast",
                                 "is_synthetic": True, "scenario_id": "S5", "generator_seed": None})
    finally:
        clear()
    resp = {"label": K.LABEL, "scenario_id": "S4", "source_variant": variant, "is_synthetic": True,
            "high_rows": [{"province": names[c], "quarter": q} for c, q in high],
            "alerts": alerts, "alert_rule": f"{AL.REASON}: P(HIGH) >= {AL.P_HIGH} at a lead the acceptance rule covers",
            "review_flow": ["The candidate is STAGED (app.quarterly.alerts_e168.stage), never published automatically.",
                            "A DA Region IV-A administrator opens Admin > Review and either confirms it "
                            "(POST /api/v1/admin/alerts/{id}/confirm) or dismisses it (POST /api/v1/admin/alerts/{id}/dismiss).",
                            "Only a confirmed alert reaches the public dashboard (GET /api/v1/alerts); a dismissed one stays "
                            "in the records for audit. The demo account can view the queue but cannot confirm or dismiss.",
                            "In this demonstration nothing was written to the database: the candidates above are what "
                            "staging would insert."],
            "ranking": ranking, "explanations": explain, "report_text": report}
    log("S4_S5", variant=variant, high=resp["high_rows"], n_alerts=len(alerts), n_municipal=len(muni))
    return resp, pd.DataFrame(muni)


# ---------------------------------------------------------------------------------------------------------- summary
def summary(out: pd.DataFrame, s4: dict, s5: pd.DataFrame, meta: dict) -> dict:
    o = out.copy()
    s0 = o[o.scenario_id == "S0"].set_index(["lead", "province"])
    doc = {"label": K.LABEL, "meta": meta, "titles": SCENARIO_TITLES, "scenarios": {}}
    doc["scenarios"]["S0"] = o[o.scenario_id == "S0"][["province", "lead", "quarter", "score_pct", "range90_low", "range90_high",
                                                       "probability", "class", "top_driver_1", "top_driver_2", "top_driver_3"]].to_dict("records")
    s1 = o[(o.scenario_id == "S1") & (o.group != "noise")]
    doc["scenarios"]["S1"] = {
        "shifts": s1[["province", "lead", "group", "param", "probability", "score_pct", "class", "clipped_cells"]].to_dict("records"),
        "noise": [{"province": p, "lead": int(l), "p_mean": round(float(g.p_high_exact.mean()), 4),
                   "p_p05": round(float(g.p_high_exact.quantile(.05)), 4), "p_p95": round(float(g.p_high_exact.quantile(.95)), 4),
                   "score_p05": round(float(g.score_pct.quantile(.05)), 1), "score_p95": round(float(g.score_pct.quantile(.95)), 1),
                   "p_s0": float(s0.at[(l, p), "probability"]), "n_high": int((g.p_high_exact >= .5).sum())}
                  for (p, l), g in o[(o.scenario_id == "S1") & (o.group == "noise")].groupby(["province", "lead"])]}
    s2 = o[o.scenario_id == "S2"]
    doc["scenarios"]["S2"] = {
        "masks": [{"province": p, "lead": int(l), "masked_share": float(f), "p_mean": round(float(g.p_high_exact.mean()), 4),
                   "p_min": round(float(g.p_high_exact.min()), 4), "p_max": round(float(g.p_high_exact.max()), 4),
                   "range90_width_mean": round(float(g.range90_width_pts.mean()), 2),
                   "range90_width_s0": float(s0.at[(l, p), "range90_width_pts"]), "p_s0": float(s0.at[(l, p), "probability"])}
                  for (p, l, f), g in s2[s2.group == "mask"].groupby(["province", "lead", "param"])],
        "all_missing": s2[s2.group == "all_missing"][["province", "lead", "probability", "score_pct", "range90_width_pts", "class"]].to_dict("records"),
        "latest_missing": [{"province": r.province, "lead": int(r.lead), "probability": r.probability, "score_pct": r.score_pct,
                            "range90_low": r.range90_low, "range90_high": r.range90_high, "range90_width_pts": r.range90_width_pts,
                            "gap_q": r.gap_q, "gap_q_s0": int(s0.at[(r.lead, r.province), "gap_q"]),
                            "range90_width_s0": float(s0.at[(r.lead, r.province), "range90_width_pts"]),
                            "p_s0": float(s0.at[(r.lead, r.province), "probability"]), "class": r["class"]}
                           for _, r in s2[s2.group == "latest_missing"].iterrows()],
        "what_the_system_warns": meta["s2_warnings"]}
    s3 = o[o.scenario_id.isin(["S3", "S3-B"])]
    doc["scenarios"]["S3"] = {
        "ladder": [{"scenario_id": sid, "shock": s, "lead": int(l), "param": float(t), "max_p": round(float(g.p_high_exact.max()), 4),
                    "highest_province": g.loc[g.p_high_exact.idxmax(), "province"],
                    "high_provinces": sorted(g[g.p_high_exact >= .5].province), "extrapolated": bool(g.extrapolated.any())}
                   for (sid, s, l, t), g in s3.groupby(["scenario_id", "group", "lead", "param"])],
        "first_high": meta["s3_first_high"], "s3b_used": meta["s3b_used"]}
    doc["scenarios"]["S4"] = s4
    doc["scenarios"]["S5"] = s5.to_dict("records")
    return doc


# --------------------------------------------------------------------------------------------------------------- run
def run() -> None:
    prod = K.production_issue()
    if not K.at_production_cutoff(prod):
        sys.exit(K.rerun_at_cutoff(MODULE, sys.argv[1:], prod))
    from joblib import Parallel, delayed
    K.SYN.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(K.SYN / "run_log.jsonl")
    prov = K.check_provenance(prod)
    log("start", protocol_sha256=K.sha256(K.DOCS / "PROTOCOL.md"), production={k: prod[k] for k in
        ("model_id", "folder", "issue", "cutoff", "published", "artifact_sha256")}, provenance=prov,
        seeds={"noise": SEED_NOISE, "masks": [s for _, s in MASKS]}, python=sys.version.split()[0])
    t0 = time.time()
    res = Parallel(n_jobs=min(6, max(1, (os.cpu_count() or 2) - 1)))(delayed(_lead_job)(l, b) for b in (False, True) for l in LEADS)
    log("procedure_done", seconds=round(time.time() - t0, 1),
        runs=[{k: r[k] for k in ("lead", "no2021", "config", "calibration", "n_train_rows", "n_features")} for r in res])
    for r in res:
        if not r["no2021"]:
            log("bounds", lead=r["lead"], bounds=r["bounds"])
    bad = check_s0(res, prod)
    log("S0_check", equal=not bad, mismatches=bad[:50])
    if bad:
        raise SystemExit("S0 does not reproduce the production issue; stopping (protocol). " + "; ".join(bad[:5]))
    out = pd.concat([r["outputs"] for r in res], ignore_index=True)
    inp = pd.concat([r["inputs"] for r in res], ignore_index=True)
    s3l1 = out[(out.scenario_id == "S3") & (out.lead == 1)]
    order = list(SHOCKS)
    hit = s3l1[s3l1.p_high_exact >= .5].assign(o=lambda d: d.group.map(order.index)).sort_values(["param", "o"])
    s3b_used = hit.empty
    if s3b_used:
        b = out[(out.scenario_id == "S3-B") & (out.lead == 1) & (out.p_high_exact >= .5)].sort_values("param")
        if b.empty:
            raise SystemExit("no S3 or S3-B variant reached P(HIGH) >= 0.5; reported as found")
        first = {"scenario_id": "S3-B", "variant": b.variant.iloc[0], "param": float(b.param.iloc[0]), "province": b.province.iloc[0]}
    else:
        out, inp = out[out.scenario_id != "S3-B"], inp[inp.scenario_id != "S3-B"]
        first = {"scenario_id": "S3", "variant": hit.variant.iloc[0], "param": float(hit.param.iloc[0]), "province": hit.province.iloc[0]}
    log("S3_first_high", s3b_used=s3b_used, first=first)
    s4rows = out[out.variant == first["variant"]].copy()
    s4rows["scenario_id"], s4rows["source_scenario"] = "S4", first["scenario_id"]
    s4, s5 = s4_s5(s4rows, first["variant"], log)
    warn = {"forecast_row_flag": "The forecast rows (live.json, dashboard rows) have no field for missing inputs; a masked input "
                                 "is passed to LightGBM as missing and nothing in the output says so.",
            "range90": "The 90 % range is computed from survey age (gap_q) only (app.e164.auto.scale), so it does not widen "
                       "when inputs are missing.",
            "stale_panel_check": "app.e168.regenerate._check_fresh refuses to stage an issue when the provincial panel ends more "
                                 "than two quarters before the issue quarter; that is the only staleness stop.",
            "data_freshness_panel": "The dashboard's 'Latest data used' list (app.ml.inference.e168_system.data_used) shows the "
                                    "newest period of each real source; it describes the real inputs, not scenario inputs."}
    meta = {"production": {k: prod[k] for k in ("model_id", "folder", "issue", "cutoff", "published", "artifact_sha256")},
            "provenance": prov, "s3_first_high": first, "s3b_used": s3b_used, "s2_warnings": warn,
            "configs": {f"lead{r['lead']}{'_no2021' if r['no2021'] else ''}": r["config"] for r in res},
            "groups": {g: {"label": GROUP_LABEL[g], "columns": d} for g, d in GROUPS.items()},
            "shocks": {s: {"label": SHOCK_LABEL[s], "columns": d} for s, d in SHOCKS.items()}, "unsigned_columns": sorted(UNSIGNED)}
    files = {"scenarios_outputs.csv": out, "scenarios_inputs.csv": inp, "s5_municipal.csv": s5}
    for name, df in files.items():
        df.to_csv(K.SYN / name, index=False, lineterminator="\n", float_format="%.10g")
    K.dump_json(s4, K.SYN / "s4_response.json")
    K.dump_json(summary(out, s4, s5, meta), K.SYN / "scenarios_summary.json")
    paths = [K.SYN / n for n in list(files) + ["s4_response.json", "s4_dashboard_rows.csv", "scenarios_summary.json", "run_log.jsonl"]]
    log("done", seconds=round(time.time() - t0, 1), rows={n: len(df) for n, df in files.items()})
    K.write_hashes(paths, K.SYN / "hashes.json", {"production_artifact_sha256": prod["artifact_sha256"]})
    print(json.dumps({"S0_equals_production": True, "first_high": first, "s3b_used": s3b_used,
                      "rows": {n: len(df) for n, df in files.items()}, "alerts": len(s4["alerts"])}, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        run()
    elif cmd == "charts":
        from app.e178 import scenario_charts
        scenario_charts.main()
    else:
        raise SystemExit("usage: python -m app.e178.scenarios run | charts")
