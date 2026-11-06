"""
Objective deliverables for the E166 thesis model. No model is tuned here; E166's locked outputs are only read.

    python -m app.e166.objectives baseline   SO4: government-only logistic baseline (RQ3) + comparison with all baselines
    python -m app.e166.objectives lgu        SO3: 142 LGU rankings from E166, paper Algorithm 5 formula
    python -m app.e166.objectives face       SO5: face validity against FNRI published figures

Baseline definition, fixed before it was computed (2026-11-06):
    LR_GOV   = SoftLogit (as E151's other logistic baselines) on GOV_COLS: the five trigger groups' official inputs + gap_q + lead.
               No news, no last survey. Mirrors the NLP-only logistic baseline (LR_NEWS), which also has no survey anchor.
    LR_GOV_A = the same plus y_anchor (last survey). Sensitivity only; both are always reported.
Same rows, same rolling-origin as-of rule as app.e151.prov.task, Leads 1-8.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e166" / "out" / "objectives"
KEY = ["key", "survey", "lead"]
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")


# ---------- SO4 baseline ----------
def _task(survey, lead):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    if not M.released(i, Pv.ROUNDS):
        return None
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey]))
    if te.empty:
        return None
    tr = Pv.add_inputs(S, P.tr)
    fill = lambda fr: fr.fillna({c: 0.0 for c in Pv.NEWS_ALL})

    def lr(cols):
        use = [c for c in cols if tr[c].notna().any()]
        return M.M137.SoftLogit(use).fit(fill(tr).assign(q=tr["q_true"])).predict_proba(fill(te))

    o = te[KEY].copy()
    o["LR_GOV"], o["LR_GOV_A"] = lr(Pv.GOV_COLS), lr(Pv.GOV_COLS + ["y_anchor"])
    o["LR_check"] = lr(Pv.GNT_COLS + ["y_anchor"])          # must reproduce E151's LR exactly
    return o


def cls(g, a):
    y, p = g["y_high"].values == 1, g[a].values >= .5
    tp, fp, fn, tn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
    prec, hr, lr = tp / max(1, tp + fp), tp / max(1, tp + fn), tn / max(1, tn + fp)
    return {"correct": tp + tn, "rows": len(g), "accuracy": round((tp + tn) / len(g), 3), "precision": round(prec, 3), "high_recall": round(hr, 3),
            "low_recall": round(lr, 3), "f1": round(2 * prec * hr / max(1e-9, prec + hr), 3), "auc": round(float(roc_auc_score(y, g[a])), 3),
            "brier": round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4)}


RQ3 = {"PERS": "Naive persistence", "LR": "Logistic, combined", "LR_GOV": "Logistic, government only (NEW)", "LR_NEWS": "Logistic, NLP only",
       "GOV": "LightGBM, government only", "NEWS": "LightGBM, NLP only"}
EXTRA = {"PSA": "PSA-only (SO4)", "LR_GOV_A": "Logistic, government + last survey (sensitivity)", "E158": "E158 (previous thesis model)", "AUTO": "AUTO (E164)"}


def baseline():
    OUT.mkdir(parents=True, exist_ok=True)
    R = [x for x in Parallel(n_jobs=12)(delayed(_task)(s, h) for s in SURVEYS for h in range(1, 9)) if x is not None]
    N = pd.concat(R, ignore_index=True)
    F = pd.read_csv(D / "e166" / "out" / "oof.csv")
    G = pd.read_csv(D / "e151" / "out" / "prov_oof.csv")[KEY + ["NEWS"]].rename(columns={"NEWS": "NEWS_LGBM"})
    F = F.merge(N, on=KEY, how="inner").merge(G, on=KEY, how="left")
    F["NEWS"] = F["NEWS_LGBM"]
    check = float(np.max(np.abs(F["LR_check"] - F["LR"])))
    F[KEY + ["LR_GOV", "LR_GOV_A"]].to_csv(OUT / "baseline_lr_gov.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(1661)
    res = {"reproduction_LR_max_abs": check, "rows": int(len(F)), "leads": {}}
    for L, g in F.groupby("lead"):
        g = g.reset_index(drop=True)
        arms = ["TS"] + [a for a in list(RQ3) + list(EXTRA) if a in g and g[a].notna().all()]
        m = {a: cls(g, a) for a in arms}
        d = {a: (lambda z: {"diff": round(z["diff"], 4), "ci95": [round(v, 4) for v in z["ci95"]]})(E7.diff_ci(g, "TS", a, "q_true", rng, n=2000)) for a in arms if a != "TS"}
        beats = {a: {k: m["TS"][k] > m[a][k] for k in ("accuracy", "precision", "f1", "auc")} | {"brier": m["TS"]["brier"] < m[a]["brier"]} for a in RQ3 if a in m}
        res["leads"][int(L)] = {"metrics": m, "E166_minus_brier": d, "E166_beats_rq3": beats}
    (OUT / "baseline_results.json").write_text(json.dumps(res, indent=1), newline="\n")
    print("reproduction of E151 combined logistic (max abs diff):", check)
    for L in (1, 2):
        r = res["leads"][L]
        print(f"\nLead {L}")
        print(pd.DataFrame(r["metrics"]).T[["correct", "accuracy", "precision", "high_recall", "low_recall", "f1", "auc", "brier"]].to_string())
        print("E166 - baseline Brier:", json.dumps(r["E166_minus_brier"]))
        print("E166 beats (RQ3):", json.dumps(r["E166_beats_rq3"]))


# ---------- SO3: LGU rankings, paper Algorithm 5 ----------
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
MIN_ARTICLES = 5                                             # paper: LIMITED_SIGNAL below five articles
W_POV, W_DEN = 0.6, 0.4
LABEL = "Relative within-province vulnerability ranking derived from the province forecast; not an independent municipal forecast or an official food-insecurity classification"


def province_forecast():
    """E166's 2027-Q1 Lead-1 forecast for the five provinces, from the unchanged E166 code (app.e166.temperature.forecast).
    E166 failed its own Brier adoption rule, so this is labelled pending the adviser's decision. Written once, with a hash."""
    import hashlib
    from datetime import datetime, timezone

    from app.e144 import data as SWSD
    from app.e148 import panel as Pn
    from app.e160.trace import build
    from app.e164 import auto as U
    from app.e166 import temperature as T
    from app.fi5.target import qindex

    p = OUT / "forecast_2027-Q1.json"
    if p.exists():
        return json.loads(p.read_text())
    S, P, tr, m, te = build()
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    i = qindex("2026-Q4")
    SW = T.sws_forecasts(SWSD.sws_quarterly(), i)
    AN = U.anchors(S, P, tr, te)
    mu, sd, half, pa, s, ps, half_s, cls, tag, lam, src, la, va, lb, vb, nb, kb, n_rounds = T.forecast(tr, te, AN, SW, Pn.q_start(i), 1)
    pct = lambda v: float(100 / (1 + np.exp(-v)))
    rows = [{"province": te["province"].iloc[k], "score": round(pct(s[k]), 1), "low90": round(pct(s[k] - half_s[k]), 1), "high90": round(pct(s[k] + half_s[k]), 1),
             "p_high": round(float(ps[k]), 4), "class": "HIGH" if cls[k] else "LOW"} for k in range(len(te))]
    out = {"model": "E166 (AUTO + temperature shrink)", "status": "adoption pending adviser decision: passes C1-C6 at Leads 1-2, failed its own Brier rule",
           "issue": "2026-10-01", "target_quarter": "2027-Q1", "lead": 1, "config": tag, "lam": lam, "lam_source": src, "forecasts": rows,
           "written_utc": datetime.now(timezone.utc).isoformat()}
    p.write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print("forecast written, sha256", hashlib.sha256(p.read_bytes()).hexdigest())
    return out


def lgu():
    OUT.mkdir(parents=True, exist_ok=True)
    from app.fi5.target import qindex
    fc = province_forecast()
    prob = {r["province"]: r["p_high"] for r in fc["forecasts"]}
    assert set(CAL) <= set(prob), prob
    c = pd.read_parquet(D / "processed" / "lgu_census.parquet")
    l = pd.read_csv(D / "e143" / "out" / "issue" / "lgus_next_quarter.csv", dtype={"lgu_psgc": str})
    c["k"], l["k"] = c["lgu_code"].astype(str).str.zfill(9), l["lgu_psgc"].astype(str).str.zfill(9)
    d = c.merge(l[["k", "poverty_incidence_2021"]], on="k", how="inner")
    assert len(d) == 142, len(d)
    # Pass 1-2: density = population / land area; province mean density where land area is 0 (none in the data, kept for the rule)
    d["density"] = np.where(d["land_area_km2"] > 0, d["population_2020"] / d["land_area_km2"].where(d["land_area_km2"] > 0), np.nan)
    d["density"] = d["density"].fillna(d.groupby("province_name")["density"].transform("mean"))
    # within-province min-max normalisation (0 when a province has no spread)
    mm = lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else x * 0.0
    d["poverty_norm"] = d.groupby("province_name")["poverty_incidence_2021"].transform(mm)
    d["density_norm"] = d.groupby("province_name")["density"].transform(mm)
    d["vulnerability"] = W_POV * d["poverty_norm"] + W_DEN * d["density_norm"]
    d["province_risk_prob"] = d["province_name"].map(prob)
    d["risk_index"] = (d["province_risk_prob"] * d["vulnerability"]).clip(0, 1)
    # data sufficiency: articles naming the province in the last complete quarter before the issue date
    N = pd.read_parquet(D / "e151" / "out" / "news_panel.parquet")
    qi = qindex("2026-Q3")
    n = {p: int(N[(N["stream"] == f"prov:{p.lower()}") & (N["qi"] == qi) & (N["lag_m"] == Pv.NEWS_LAG)]["n"].sum()) for p in CAL}
    d["articles_last_quarter"] = d["province_name"].map(n)
    d["data_sufficiency_flag"] = np.where(d["articles_last_quarter"] >= MIN_ARTICLES, "OK", "LIMITED_SIGNAL")
    d["disaggregation_label"] = LABEL
    d = d.sort_values(["risk_index", "poverty_incidence_2021"], ascending=[False, False]).reset_index(drop=True)
    d["rank_in_region"] = np.arange(1, len(d) + 1)
    d["rank_in_province"] = d.groupby("province_name")["risk_index"].rank(ascending=False, method="first").astype(int)
    d["target_quarter"] = fc["target_quarter"]
    cols = ["rank_in_region", "rank_in_province", "province_name", "lgu_code", "lgu_name", "lgu_type", "population_2020", "land_area_km2", "density", "poverty_incidence_2021",
            "poverty_norm", "density_norm", "vulnerability", "province_risk_prob", "risk_index", "articles_last_quarter", "data_sufficiency_flag", "disaggregation_label", "target_quarter"]
    d[cols].to_csv(OUT / "lgu_rankings_2027-Q1.csv", index=False, lineterminator="\n")
    print(json.dumps(fc["forecasts"], indent=0))
    print("articles last quarter:", n)
    print(d[cols[:6] + ["poverty_incidence_2021", "vulnerability", "risk_index", "data_sufficiency_flag"]].head(15).round(4).to_string(index=False))
    print("top-20 by province:", d.head(20)["province_name"].value_counts().to_dict(), "| distinct risk values:", d["risk_index"].nunique())


# ---------- SO5: face validity against FNRI published figures (descriptive anchor, no pass rule) ----------
def face():
    from scipy.stats import spearmanr

    from app.e151.validate import _norm_region
    OUT.mkdir(parents=True, exist_ok=True)
    pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))
    F = pd.read_csv(D / "e166" / "out" / "oof.csv")
    x = F[F["lead"] == 1].copy()
    x["forecast_pct"], x["fnri_pct"] = pct(x["mu_TS"]), pct(x["y_true"])
    # 1. CALABARZON provinces, same instrument (HFIAS moderate-or-severe), the round each was measured
    cal = x[x["province"].isin(CAL)][["province", "survey", "forecast_pct", "fnri_pct", "TS"]].copy()
    cal["error_points"] = cal["forecast_pct"] - cal["fnri_pct"]
    cal["class_forecast"] = np.where(cal["forecast_pct"] >= 50, "HIGH", "LOW")
    cal["class_fnri"] = np.where(cal["fnri_pct"] >= 50, "HIGH", "LOW")
    cal["agree"] = cal["class_forecast"] == cal["class_fnri"]
    # 2. Regions: E166 latest-round (ENNS2021) forecasts averaged by region vs NNS 2023 regional FIES (different instrument and year)
    f = pd.read_csv(D / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    f = f[(f["level"] == "region") & (f["year"] == 2023) & (f["category"] == "moderate_or_severe_food_insecurity")].copy()
    f["reg"] = f["geography"].map(_norm_region)
    out_reg = {}
    for name, g in (("ENNS2021 round", x[x["survey"] == "ENNS2021"]), ("all rounds", x)):
        g = g.assign(reg=g["region"].map(lambda s: _norm_region(s) or s)).groupby("reg").agg(forecast_pct=("forecast_pct", "mean"), n=("key", "size"))
        z = f.set_index("reg")[["percent"]].join(g, how="inner")
        rng = np.random.default_rng(166)
        bs = [spearmanr(z["forecast_pct"].values[i], z["percent"].values[i]).statistic for i in (rng.integers(0, len(z), len(z)) for _ in range(2000))]
        bs = [b for b in bs if np.isfinite(b)]
        z = z.sort_values("forecast_pct")
        out_reg[name] = {"n_regions": int(len(z)), "spearman": round(float(spearmanr(z["forecast_pct"], z["percent"]).statistic), 3),
                         "spearman_ci95": [round(float(np.percentile(bs, q)), 3) for q in (2.5, 97.5)],
                         "calabarzon_rank_low_to_high_forecast": int(list(z.index).index("CALABARZON") + 1) if "CALABARZON" in z.index else None,
                         "calabarzon_rank_low_to_high_fies2023": int(z["percent"].rank().get("CALABARZON", np.nan)) if "CALABARZON" in z.index else None,
                         "table": z.round(1).reset_index().to_dict("records")}
    res = {"calabarzon_provinces_lead1": cal.round(1).to_dict("records"), "calabarzon_mean_abs_error_points": round(float(cal["error_points"].abs().mean()), 1),
           "calabarzon_class_agreement": f"{int(cal['agree'].sum())} of {len(cal)}", "regional_vs_nns2023_fies": out_reg,
           "note": "Face-validity anchor only. Provincial rows: same instrument (HFIAS), retrospective Lead-1 forecasts. Regional 2023: FIES, a different instrument and year; agreement is contextual."}
    (OUT / "face_validity.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(cal.round(1).to_string(index=False))
    print("mean abs error (points):", res["calabarzon_mean_abs_error_points"], "| class agreement:", res["calabarzon_class_agreement"])
    for k, v in out_reg.items():
        print(k, {a: b for a, b in v.items() if a != "table"})


# ---------- RQ1 / H1: SHAP drivers of the E166 live model ----------
# Fixed before computing (2026-11-06):
#   FSSI family      = news net-stress columns at every geography: *_e_net and *_net_since (docs/e151/OBJECTIVE1_FSSI.md)
#   Food CPI dev.    = cpi_food_rel_nat (provincial food inflation relative to national); cpi_since reported alongside
#   "Among the strongest" = at least one column of the family ranks in the top 10 of all inputs by mean |SHAP| on training rows.
#   H1 (null) is rejected only if BOTH FSSI and food CPI deviation are among the strongest.
FSSI_FAMILY = ["p_e_net", "a_e_net", "n_e_net", "r_e_net", "p_net_since", "a_net_since", "n_net_since"]
CPI_DEV = ["cpi_food_rel_nat"]
TOP_K = 10


def shap_drivers():
    import shap

    from app.e160.trace import build
    from app.e163 import model as C
    from app.e164 import auto as U
    OUT.mkdir(parents=True, exist_ok=True)
    fc = json.loads((OUT / "forecast_2027-Q1.json").read_text())
    a, l, f, cal = fc["config"].split("|")
    assert l == "RF" and cal == "id", fc["config"]
    lam = float(fc["lam"])
    S, P, tr, m, te = build()
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    atr, ate = AN[a]
    y = tr["y_true"].values
    rf = U.LEARNERS["RF"](U.FS[f]).fit(tr.assign(e=y - atr))
    mu = ate + rf.predict(te)
    pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))
    sc = dict(zip(te["province"], pct(lam * mu)))
    repro = max(abs(sc[r["province"]] - r["score"]) for r in fc["forecasts"])
    assert repro < 0.06, ("live model not reproduced", repro)
    Xtr, Xte = tr[rf.use_].fillna(rf.med_).values, te[rf.use_].fillna(rf.med_).values
    ex = shap.TreeExplainer(rf.m_)
    sv_tr, sv_te = ex.shap_values(Xtr), ex.shap_values(Xte)
    base = float(np.atleast_1d(ex.expected_value)[0])
    add = float(np.max(np.abs(base + sv_te.sum(axis=1) - rf.m_.predict(Xte))))
    imp = pd.Series(np.abs(sv_tr).mean(axis=0) * lam, index=rf.use_).sort_values(ascending=False)
    rank = {c: int(i + 1) for i, c in enumerate(imp.index)}
    news = set(c for c in rf.use_ if c in Pv.NEWS_ALL)
    grp = lambda c: C.gmap(c) or "timing"
    G = imp.groupby([grp(c) for c in imp.index]).sum().sort_values(ascending=False)
    src = imp.groupby(["news (NLP)" if c in news else "official" for c in imp.index]).sum()
    fam_rank = {"FSSI": min([rank[c] for c in FSSI_FAMILY if c in rank] or [None]), "food_CPI_deviation": min([rank[c] for c in CPI_DEV if c in rank] or [None])}
    h1 = {k: (v is not None and v <= TOP_K) for k, v in fam_rank.items()}
    rows = []
    for k in range(len(te)):
        s = pd.Series(sv_te[k] * lam, index=rf.use_)
        top = s.reindex(s.abs().sort_values(ascending=False).index).head(5)
        rows.append({"province": te["province"].iloc[k], "score": round(float(pct(lam * mu[k])), 1), "survey_anchor_part": round(float(lam * ate[k]), 3),
                     "model_baseline_part": round(lam * base, 3), "adjustment_part": round(float(s.sum()), 3),
                     "top_drivers": [{"feature": c, "group": grp(c), "source": "news" if c in news else "official", "logit_contribution": round(float(v), 4)} for c, v in top.items()]})
    res = {"model": fc["config"], "lam": lam, "reproduction_max_points": round(float(repro), 4), "shap_additivity_max": add, "n_inputs": len(rf.use_), "train_rows": int(len(tr)),
           "group_share": (G / G.sum()).round(4).to_dict(), "source_share": (src / src.sum()).round(4).to_dict(),
           "top15": [{"rank": rank[c], "feature": c, "group": grp(c), "source": "news" if c in news else "official", "mean_abs_shap": round(float(v), 5)} for c, v in imp.head(15).items()],
           "H1": {"definitions": {"FSSI": FSSI_FAMILY, "food_CPI_deviation": CPI_DEV, "top_k": TOP_K}, "best_rank": fam_rank, "among_strongest": h1,
                  "null_rejected": bool(all(h1.values())), "cpi_since_rank": rank.get("cpi_since")},
           "anchor_note": "SHAP explains the RandomForest adjustment only; the survey anchor (last measured level, shrunk) is reported as its own part of each score.",
           "province_2027Q1": rows}
    (OUT / "shap_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    # full per-province, per-input contributions (logit scale x lam), for the dashboard's driver panel
    long = [{"province": te["province"].iloc[k], "feature": c, "group": grp(c), "source": "news" if c in news else "official",
             "contribution": float(sv_te[k][j] * lam)} for k in range(len(te)) for j, c in enumerate(rf.use_)]
    pd.DataFrame(long).to_csv(OUT / "shap_province_features_2027-Q1.csv", index=False, lineterminator="\n")
    print("reproduction (points):", round(repro, 4), "| SHAP additivity:", add)
    print("group share:", res["group_share"]); print("source share:", res["source_share"])
    print(pd.DataFrame(res["top15"]).to_string(index=False))
    print("H1:", json.dumps(res["H1"]))
    for r in rows:
        print(r["province"], r["score"], "anchor", r["survey_anchor_part"], "adj", r["adjustment_part"], [(d["feature"], d["logit_contribution"]) for d in r["top_drivers"][:3]])


if __name__ == "__main__":
    {"baseline": baseline, "lgu": lgu, "face": face, "shap": shap_drivers}[sys.argv[1]]()
