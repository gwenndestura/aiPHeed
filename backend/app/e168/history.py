"""
E168 (LightGBM thesis model) for every dashboard quarter, and the sealed 2027-Q1 forecast. Owner decision 2026-11-06:
"use E168 from now on".

Each target quarter T (2023-Q1 .. 2027-Q1) is E168 run as of the issue quarter T-1 (one quarter ahead) with only
information published before that date, by the locked E168 code (app.e168.lgbm.forecast). Past quarters are
back-forecasts: no provincial survey exists for most of them. The 2027-Q1 run is the live forecast and is sealed
(data/e168/out/sealed_2027-Q1.json, written once) before any outcome exists.

Per-input contributions are LightGBM's exact tree attributions (pred_contrib), via app.e166.history.contributions.

    python -m app.e168.history run
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
from joblib import Parallel, delayed

from app.e151 import prov as Pv
from app.e163 import model as C
from app.e164 import auto as U
from app.e166 import history as H
from app.e168 import lgbm as L
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
OUT = BACKEND_DIR / "data" / "e168" / "out"
HIST = OUT / "history"
pct = H.pct


def one(target_label: str, SW) -> dict:
    from app.e148 import panel as Pn
    target = qindex(target_label)
    issue = target - 1
    S, P, tr, te = H.build(issue)
    AN = U.anchors(S, P, tr, te)
    r = L.forecast(tr, te, AN, SW, Pn.q_start(issue), 1)
    phi, use, base, mu_check, slope = H.contributions(tr, te, AN, r["tag"])
    assert np.max(np.abs(mu_check - r["mu"])) < 1e-6, ("contribution model does not reproduce the forecast", target_label)
    lam = r["lam"]
    news = set(Pv.NEWS_ALL)
    contrib = [{"province": te["province"].iloc[k], "feature": c, "group": C.gmap(c) or "timing", "source": "news" if c in news else "official",
                "contribution": float(phi[k, j] * lam)} for k in range(len(te)) for j, c in enumerate(use)]
    n = H.articles(target)
    s, half, ps, cls = r["s"], r["half"], r["ps"], r["cls"]
    rows = [{"province": te["province"].iloc[k], "score": round(float(pct(s[k])), 1), "low90": round(float(pct(s[k] - half[k])), 1),
             "high90": round(float(pct(s[k] + half[k])), 1), "p_high": round(float(ps[k]), 4), "class": "HIGH" if cls[k] else "LOW",
             "articles_last_quarter": n[te["province"].iloc[k]]} for k in range(len(te))]
    lg = H.lgu_rank({x["province"]: x["p_high"] for x in rows}, n, target_label)
    out = {"model": "E168", "target_quarter": target_label, "issue_quarter": qlabel(issue), "issue_date": str(Pn.q_start(issue).date()),
           "lead": 1, "kind": "forecast" if target_label == H.LAST else "back-forecast (as of the issue date; no survey for this quarter)",
           "config": r["tag"], "lam": lam, "lam_source": r["src"], "train_rows": int(len(tr)), "released_rounds": list(P.rel),
           "forecasts": rows, "contributions": contrib, "lgus": lg.round(6).to_dict("records")}
    HIST.mkdir(parents=True, exist_ok=True)
    (HIST / f"{target_label}.json").write_text(json.dumps(out, default=float), newline="\n")
    return {"target": target_label, "config": r["tag"], "lam": round(lam, 3), "p_high": {x["province"]: x["p_high"] for x in rows}}


def run():
    from app.e144 import data as SWSD
    targets = [qlabel(i) for i in range(qindex(H.FIRST), qindex(H.LAST) + 1)]
    SW = L.sws_forecasts(SWSD.sws_quarterly(), qindex(H.LAST) - 1)
    R = Parallel(n_jobs=12)(delayed(one)(t, SW) for t in targets)
    for r in R:
        print(r["target"], r["config"], "lam", r["lam"], r["p_high"])
    (HIST / "index.json").write_text(json.dumps({"quarters": targets, "first": H.FIRST, "last": H.LAST, "model": "E168"}, indent=1), newline="\n")
    seal = OUT / "sealed_2027-Q1.json"
    if not seal.exists():                              # the live forecast, sealed before any outcome exists (written once)
        live = json.loads((HIST / f"{H.LAST}.json").read_text())
        seal.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), "model": "E168", "issue_date": live["issue_date"],
                                    "target_quarter": H.LAST, "config": live["config"], "lam": live["lam"], "forecasts": live["forecasts"]}, indent=1), newline="\n")
    print("seal", hashlib.sha256(seal.read_bytes()).hexdigest()[:8])


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
