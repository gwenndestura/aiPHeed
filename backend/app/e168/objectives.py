"""
Objective deliverables for the LightGBM thesis model E168. Nothing is tuned; E168's locked outputs are only read, and the
live model is refitted exactly as app.e168.lgbm does (deterministic) to attribute it.

    python -m app.e168.objectives shap    RQ1 / H1: LightGBM SHAP (pred_contrib) of the live model on its training rows
    python -m app.e168.objectives face    SO5: face validity against DOST-FNRI published figures

H1 definitions are those fixed for E166 (app.e166.objectives): FSSI family, food CPI deviation = cpi_food_rel_nat, top 10.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

from app.e151 import prov as Pv
from app.e163 import model as C
from app.e164 import auto as U
from app.e166 import history as H
from app.e166.objectives import CPI_DEV, FSSI_FAMILY, TOP_K
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e168" / "out" / "objectives"
FIVE = {"market": "market", "climate": "climate", "employment": "employment", "remittance": "ofw_remittance"}


def shap():
    OUT.mkdir(parents=True, exist_ok=True)
    live = json.loads((D / "e168" / "out" / "history" / "2027-Q1.json").read_text())
    a, l, f, cal = live["config"].split("|")
    S, P, tr, te = H.build(qindex("2026-Q4"))
    AN = U.anchors(S, P, tr, te)
    y = tr["y_true"].values
    m = U.LEARNERS[l](U.FS[f]).fit(tr.assign(e=y - AN[a][0]))
    cc = m.m_.booster_.predict(tr[m.use_], pred_contrib=True)[:, :-1] * float(live["lam"])
    imp = pd.Series(np.abs(cc).mean(axis=0), index=m.use_).sort_values(ascending=False)
    rank = {c: i + 1 for i, c in enumerate(imp.index)}
    news = set(Pv.NEWS_ALL)
    grp = lambda c: "fish_kill" if c == "c_fish_yoy" else FIVE.get(C.gmap(c) or "", "other")
    G = imp.groupby([grp(c) for c in imp.index]).sum()
    five = G.drop("other", errors="ignore")
    src = imp.groupby(["news (NLP)" if c in news else "official" for c in imp.index]).sum()
    fam = {"FSSI": min([rank[c] for c in FSSI_FAMILY if c in rank] or [None]), "food_CPI_deviation": min([rank[c] for c in CPI_DEV if c in rank] or [None])}
    h1 = {k: (v is not None and v <= TOP_K) for k, v in fam.items()}
    res = {"model": "E168 " + live["config"], "lam": live["lam"], "n_inputs": len(m.use_), "train_rows": int(len(tr)),
           "five_driver_share": (five / five.sum()).round(4).to_dict(), "other_share_of_total": round(float(G.get("other", 0) / G.sum()), 4),
           "source_share": (src / src.sum()).round(4).to_dict(),
           "top15": [{"rank": rank[c], "feature": c, "group": grp(c), "source": "news" if c in news else "official", "mean_abs_shap": round(float(v), 5)}
                     for c, v in imp.head(15).items()],
           "H1": {"definitions": {"FSSI": FSSI_FAMILY, "food_CPI_deviation": CPI_DEV, "top_k": TOP_K}, "best_rank": fam, "among_strongest": h1,
                  "null_rejected": bool(all(h1.values())), "cpi_since_rank": rank.get("cpi_since")},
           "note": "LightGBM exact tree attributions of the model's adjustment to the survey anchor, on the live training rows, times lambda."}
    (OUT / "shap_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps({k: res[k] for k in ("model", "five_driver_share", "other_share_of_total", "source_share", "H1")}, indent=1, default=float))
    print(pd.DataFrame(res["top15"]).to_string(index=False))


def face():
    from scipy.stats import spearmanr

    from app.e151.validate import _norm_region
    OUT.mkdir(parents=True, exist_ok=True)
    pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))
    F = pd.read_csv(D / "e168" / "out" / "oof.csv")
    x = F[F["lead"] == 1].copy()
    x["forecast_pct"], x["fnri_pct"] = pct(x["mu_L"]), pct(x["y_true"])
    cal = x[x["province"].isin(H.CAL)][["province", "survey", "forecast_pct", "fnri_pct", "L"]].copy()
    cal["error_points"] = cal["forecast_pct"] - cal["fnri_pct"]
    cal["agree"] = (cal["forecast_pct"] >= 50) == (cal["fnri_pct"] >= 50)
    f = pd.read_csv(D / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    f = f[(f["level"] == "region") & (f["year"] == 2023) & (f["category"] == "moderate_or_severe_food_insecurity")].copy()
    f["reg"] = f["geography"].map(_norm_region)
    g = x[x["survey"] == "ENNS2021"].assign(reg=lambda d: d["region"].map(lambda s: _norm_region(s) or s)).groupby("reg").agg(forecast_pct=("forecast_pct", "mean"))
    z = f.set_index("reg")[["percent"]].join(g, how="inner").sort_values("forecast_pct")
    res = {"calabarzon_provinces_lead1": cal.round(1).to_dict("records"), "calabarzon_mean_abs_error_points": round(float(cal["error_points"].abs().mean()), 1),
           "calabarzon_class_agreement": f"{int(cal['agree'].sum())} of {len(cal)}",
           "regions_vs_nns2023_fies": {"n_regions": int(len(z)), "spearman": round(float(spearmanr(z["forecast_pct"], z["percent"]).statistic), 3),
                                       "calabarzon_rank_low_to_high_forecast": int(list(z.index).index("CALABARZON") + 1) if "CALABARZON" in z.index else None},
           "note": "Face-validity anchor only. Provincial rows: same instrument (HFIAS), retrospective Lead-1 forecasts. Regional 2023: FIES, a different instrument and year."}
    (OUT / "face_validity.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(cal.round(1).to_string(index=False))
    print({k: v for k, v in res.items() if k not in ("calabarzon_provinces_lead1", "note")})


if __name__ == "__main__":
    {"shap": shap, "face": face}[sys.argv[1]]()
