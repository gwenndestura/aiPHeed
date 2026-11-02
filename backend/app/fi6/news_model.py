"""FI6-N: does properly collected news add forecasting information? Controlled walk-forward comparisons.

Same FI6 target, origins (targets 2010-Q1..2026-Q3), leads, LightGBM change model and reliability rules. Only the
feature sets differ:

    gov_only        latest reading + government indicators (FI6 'gov_only')
    news_only       latest reading anchor + archive news features only (change model)
    gov_plus_news   latest reading + government + archive news
    minus_<domain>  gov_plus_news without that domain's archive news feature(s)
    NLP-only        Objective 4 baseline: LightGBM classifier on archive news features only (no SWS information)

Archive news features (news_events.FEATURES), each z-scored against the same feature's earlier quarters only
(>= 8 earlier non-missing quarters), using news published inside the issue quarter (complete at the issue date):
    na_market, na_climate, na_employment, na_remittance, na_poverty  risk-event shares (coverage-normalised)
    na_climate_damage, na_displaced                                  log P damage, log families affected
Expected direction +1 for all (monotone constraints). A news gain is claimed only if the moving-block bootstrap
95 % interval of Brier(gov_plus_news) - Brier(gov_only) lies below 0.

    python -m app.fi6.news_model lock | evaluate
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.fi5.evaluate import block_bootstrap_diff, mcnemar_p
from app.fi5.paths import BACKEND_DIR
from app.fi5.target import qindex
from app.fi6 import models as M
from app.fi6.evaluate import EVAL_FIRST_TARGET, LEADS, metrics, reliability
from app.fi6.features import GOV, OUTCOME, design
from app.fi6.news_events import FEATURES
from app.fi6.paths import FI6

OUT = FI6 / "out_news"
OUT.mkdir(parents=True, exist_ok=True)
LOCK = OUT / "METHOD_LOCK_NEWS.json"
NEWS_MAP = {"na_market": "risk_share_market", "na_climate": "risk_share_climate", "na_employment": "risk_share_employment",
            "na_remittance": "risk_share_remittance", "na_poverty": "risk_share_poverty",
            "na_climate_damage": "climate_damage_log", "na_displaced": "displaced_families_log"}
NEWS_DOMAIN = {"na_market": "market", "na_climate": "climate", "na_climate_damage": "climate", "na_employment": "employment",
               "na_remittance": "remittance", "na_poverty": "poverty", "na_displaced": "poverty"}
NEWSA = list(NEWS_MAP)
M.EXTRA_MONOTONE.update({f: 1 for f in NEWSA})
MIN_HISTORY = 8
SETS = {"gov_only": OUTCOME + GOV, "news_only": OUTCOME[:1] + NEWSA, "gov_plus_news": OUTCOME + GOV + NEWSA,
        **{f"minus_{d}_news": OUTCOME + GOV + [f for f in NEWSA if NEWS_DOMAIN[f] != d]
           for d in ["market", "climate", "employment", "remittance", "poverty"]}}
SPECS = {"Government only": ("reg", "gov_only"), "News only": ("reg", "news_only"),
         "Government + news": ("reg", "gov_plus_news"),
         **{f"Government + news without {d} news": ("reg", f"minus_{d}_news") for d in ["market", "climate", "employment", "remittance", "poverty"]},
         "NLP-only baseline (classifier, archive news)": ("clf_lgbm", "nlp_archive"),
         "Naive persistence": ("persist", None), "Climatology (base rate)": ("clim", None)}
SETS["nlp_archive"] = NEWSA


def asof_news() -> pd.DataFrame:
    """Quarter -> z-scored archive news features using only earlier quarters."""
    f = pd.read_csv(FEATURES).sort_values("quarter").reset_index(drop=True)
    out = pd.DataFrame({"issue_quarter": f["quarter"]})
    for k, c in NEWS_MAP.items():
        x = f[c].astype(float)
        z = []
        for i in range(len(x)):
            hist = x.iloc[:i].dropna()
            if pd.isna(x.iloc[i]) or len(hist) < MIN_HISTORY:
                z.append(np.nan)
                continue
            sd = hist.std(ddof=1)
            z.append(float((x.iloc[i] - hist.mean()) / sd) if sd > 0 else 0.0)
        out[k] = z
    return out


def design_n(lead: int) -> pd.DataFrame:
    X = design(lead)
    return X.merge(asof_news(), on="issue_quarter", how="left")


def _task(args):
    lead, X, chunk = args
    L = X[X["y"].notna()].reset_index(drop=True)
    ev = L[L["tqi"] >= qindex(EVAL_FIRST_TARGET)].iloc[chunk[0]::chunk[1]]
    rows = []
    for i, r in ev.iterrows():
        tr = L[L["target_published"] <= r["issue_ts"]]
        te = L.loc[[i]]
        rec = {"lead": lead, "target_quarter": r["target_quarter"], "y": int(r["y"]), "p_flip": r["p_flip"],
               "news_available": bool(pd.notna(te[NEWSA]).any(axis=1).iloc[0]),
               "train_rows_with_news": int(tr[NEWSA].notna().any(axis=1).sum())}
        for name, (kind, fs) in SPECS.items():
            m = M.fit(M.make(kind, SETS.get(fs) if fs else None), kind, tr)
            rec[name] = float(m.predict_proba(te)[0])
        rows.append(rec)
    return rows


def lock() -> dict:
    files = ["app/fi6/news_archive.py", "app/fi6/news_events.py", "app/fi6/news_model.py", "app/fi6/models.py", "app/fi6/features.py"]
    body = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sets": SETS,
            "specs": {k: list(v) if v else None for k, v in SPECS.items()}, "news_features": NEWS_MAP,
            "min_history": MIN_HISTORY, "decision_rule": "news helps only if the 95% block-bootstrap CI of "
            "Brier(Government + news) - Brier(Government only) is below 0",
            "features_sha256": hashlib.sha256((FEATURES).read_bytes()).hexdigest(),
            "code_sha256": {f: hashlib.sha256((BACKEND_DIR / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for f in files}}
    body["lock_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    LOCK.write_text(json.dumps(body, indent=1))
    return body


def evaluate() -> dict:
    workers = max(1, (os.cpu_count() or 4) - 2)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        designs = dict(zip(LEADS, ex.map(design_n, LEADS)))
        k = max(1, workers // len(LEADS))
        parts = list(ex.map(_task, [(L, designs[L], (c, k)) for L in LEADS for c in range(k)]))
    pr = pd.DataFrame([r for p in parts for r in p]).sort_values(["lead", "target_quarter"]).reset_index(drop=True)
    pr.to_csv(OUT / "news_walkforward_predictions.csv", index=False, lineterminator="\n")
    res = {}
    for lead, g in pr.groupby("lead"):
        y = g["y"].to_numpy(int)
        clim = g["Climatology (base rate)"].to_numpy(float)
        per = {}
        for subset, sel in [("all_origins", np.ones(len(g), bool)), ("origins_with_news", g["news_available"].to_numpy())]:
            ys, cs = y[sel], clim[sel]
            mm = {name: metrics(ys, g[name].to_numpy(float)[sel], cs) for name in SPECS}
            base = g["Government only"].to_numpy(float)[sel]
            comp = {}
            for name in SPECS:
                if name == "Government only":
                    continue
                q = g[name].to_numpy(float)[sel]
                bd = block_bootstrap_diff((q - ys) ** 2, (base - ys) ** 2)
                comp[name] = {"brier_diff_vs_gov_only": bd[0], "ci95": [bd[1], bd[2]],
                              "auc_diff": (mm[name]["auc"] or np.nan) - (mm["Government only"]["auc"] or np.nan),
                              "mcnemar_p": mcnemar_p(((q >= .5) == ys).astype(int), ((base >= .5) == ys).astype(int))}
            per[subset] = {"n": int(sel.sum()), "n_high": int(ys.sum()), "models": mm, "vs_gov_only": comp,
                           "reliability_gov_plus_news": reliability({**mm["Government + news"], "eras": {}})}
        gn = per["all_origins"]["vs_gov_only"]["Government + news"]
        per["news_helps"] = bool(gn["ci95"][1] < 0)
        res[int(lead)] = per
    lk = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    out = {"by_lead": res, "lock_sha256": lk.get("lock_sha256"),
           "features_unchanged_since_lock": lk.get("features_sha256") == hashlib.sha256(FEATURES.read_bytes()).hexdigest()}
    (OUT / "news_evaluation.json").write_text(json.dumps(out, indent=1, default=str))
    return out



def issue(issue_quarter: str = "2026-Q3") -> dict:
    """Live forecasts from the government + archive-news change model (adopted for lead 1 by the locked rule)."""
    import shap

    from app.fi5.features import FeatureBuilder
    from app.fi5.target import q_end, qlabel
    from app.fi6.features import DOMAIN, live_row
    from app.fi6.pipeline import sentence

    iq = qindex(issue_quarter)
    d = q_end(iq)
    fb = FeatureBuilder()
    news = asof_news().set_index("issue_quarter")
    ev = json.loads((OUT / "news_evaluation.json").read_text())
    dom = {**DOMAIN, **NEWS_DOMAIN}
    out = []
    for lead in LEADS:
        X = design_n(lead)
        L = X[X["y"].notna()]
        tr = L[L["target_published"] <= d]
        m = M.DeltaModel(SETS["gov_plus_news"]).fit(tr, tr["delta_target"].to_numpy(float))
        live = live_row(iq, lead, fb)
        for c in NEWSA:
            live[c] = news.loc[issue_quarter, c] if issue_quarter in news.index else np.nan
        p = float(m.predict_proba(live)[0])
        sv = np.asarray(shap.TreeExplainer(m.est).shap_values(live[m.cols]))[0]
        blocks: dict[str, float] = {}
        for c, s in zip(m.cols, sv):
            blocks[dom[c]] = blocks.get(dom[c], 0.0) + float(s)
        news_part = {c: round(float(s), 3) for c, s in zip(m.cols, sv) if c in NEWSA}
        out.append({"lead": lead, "issue_quarter": issue_quarter, "target_quarter": qlabel(iq + lead), "p_high": round(p, 4),
                    "class": "HIGH" if p >= .5 else "LOW",
                    "forecast_hunger_pct": round(float(live["hunger_last"].iloc[0] + m.predict_delta(live)[0]), 2),
                    "threshold_pct": round(float(live["threshold_known"].iloc[0]), 2),
                    "news_helps_at_this_lead": bool(ev["by_lead"][str(lead)]["news_helps"]),
                    "explanation": sentence(blocks, qlabel(iq + lead)),
                    "news_contributions_pp": news_part, "news_features_live": {c: (None if pd.isna(live[c].iloc[0]) else round(float(live[c].iloc[0]), 3)) for c in NEWSA},
                    "n_train": int(len(tr)), "config": m.choice})
        m.est.booster_.save_model(str(FI6 / "models" / f"fi6n_lead{lead}.txt"))
    body = {"issued_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "forecasts": out,
            "model": "LightGBM change model, government + archive news (FI6-N)"}
    (OUT / "forecast_news.json").write_text(json.dumps(body, indent=1, default=str))
    return body


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["lock", "evaluate", "issue"])
    a = ap.parse_args()
    fn = {"lock": lock, "evaluate": evaluate, "issue": issue}[a.cmd]
    print(json.dumps(fn(), indent=1, default=str)[:4000])
