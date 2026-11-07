"""
E173: freeze the SIMPLE LightGBM rule (from E172) and issue sealed prospective forecasts of SIMPLE and E168, per docs/e173/PROTOCOL.md.
No independent labels exist yet (verified 2026-11-07), so nothing is scored here.

    python -m app.e173.freeze config     write data/e173/out/simple_config.json and print its hash
    python -m app.e173.freeze seal       sealed Lead-1 (2027-Q1) and Lead-2 (2027-Q2) forecasts for every panel province (written once)
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e144 import data as SWSD
from app.e147 import features as Fe
from app.e148 import panel as Pn
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e164 import auto as U
from app.e166 import temperature as T
from app.e168 import lgbm as L
from app.e171 import candidates as C171
from app.e172 import lgbm_only as E
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e173" / "out"
ISSUE = qindex("2026-Q4")
CODE = ["app/e173/freeze.py", "app/e172/lgbm_only.py", "app/e171/candidates.py", "app/e168/lgbm.py", "app/e166/temperature.py",
        "app/e165/calib.py", "app/e164/auto.py", "app/e151/prov.py", "app/e150/model.py"]


def simple_menu(anchor: str) -> list:
    return [c for c in E.stage2(anchor) if E.SUBSETS["SIMPLE"](c)]


def config() -> dict:
    """The frozen SIMPLE rule and the hashes of every file it runs; the config hash is SHA-256 of this JSON (sorted keys)."""
    cfg = {"name": "SIMPLE (E172 diagnostic, frozen in E173)",
           "stage1_menu": ["|".join(c) for c in E.STAGE1],
           "stage2_menu_with_anchor_A": ["|".join(c) for c in simple_menu("A")],
           "settings": {k: {kk: (vv if not isinstance(vv, float) else round(vv, 6)) for kk, vv in v.items()} for k, v in E.R.items() if k != "R0"},
           "inputs": {f: U.FS[f] for f in ("GOV", "FULL", "GOV_S")}, "tree_grid": E.LGB.GRID, "seed": list(E.SEEDS1),
           "lead_exact_min_rows": 30, "selection": "app.e171.candidates.score_all (forward over whole survey rounds if 2+ rounds, else region folds)",
           "calibration": "identity or cross-fitted linear, chosen on the same folds", "shrink": "E168 temperature shrink (app.e166.temperature)",
           "high_rule": "P(HIGH) >= 0.5", "monotone_plus_one": C171.S_COLS,
           "code_sha256": {p: hashlib.sha256((BACKEND_DIR / p).read_bytes()).hexdigest() for p in CODE}}
    cfg["config_sha256"] = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    return cfg


def build(issue: int, lead: int, sw: pd.DataFrame):
    """app.e166.history.build for every panel province at `lead`, with the E171 SWS inputs (published before the issue only)."""
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    H = E154.income()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, issue, Pv.ROUNDS, "F")
    tr = C171.add_sws(E154.add_income(Pv.add_inputs(S, P.tr), H), sw).reset_index(drop=True)
    b = S.base.drop_duplicates("key")
    rows = M.rows_for(S, b.assign(T=issue + lead, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [lead], "F")
    te = C171.add_sws(E154.add_income(Pv.add_inputs(S, rows), H), sw).reset_index(drop=True)
    return S, P, tr, te


def job(lead: int, mode: str):
    E._install()
    C171.LEAD_NOW["v"] = lead
    cut = Pn.q_start(ISSUE)
    sw = SWSD.sws_quarterly()
    if mode == "corrupt":
        sw = T.corrupt_sws(sw, cut)
    SW = L.sws_forecasts(sw, ISSUE)
    S, P, tr, te = build(ISSUE, lead, sw)
    AN = U.anchors(S, P, tr, te)
    r8 = L.forecast(tr, te, AN, SW, cut, lead)
    scheme, msk, res1 = E.score(tr, AN, E.STAGE1)
    anchor = min(E.STAGE1, key=lambda c: res1[c]["sse"])[0]
    menu = simple_menu(anchor)
    _, _, res2 = E.score(tr, AN, menu)
    rs = C171.finalize(tr, te, AN, SW, cut, lead, scheme, msk, {**res1, **res2}, menu)
    o = te[["key", "province", "region"]].copy()
    o["lead"], o["target_quarter"], o["mode"] = lead, qlabel(ISSUE + lead), mode
    o["E168_score"], o["E168_p_high"], o["E168_tag"], o["E168_lam"] = r8["s"], r8["ps"], r8["tag"], r8["lam"]
    o["SIMPLE_score"], o["SIMPLE_p_high"], o["SIMPLE_tag"], o["SIMPLE_lam"] = rs["mu"], rs["p"], rs["tag"], rs["lam"]
    o["scheme"], o["train_rows"] = scheme, len(tr)
    return o


def seal():
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "sealed_prospective.json"
    if f.exists():
        sys.exit("already sealed (written once)")
    cfg = config()
    (OUT / "simple_config.json").write_text(json.dumps(cfg, indent=1), newline="\n")
    R = Parallel(n_jobs=4)(delayed(job)(l, m) for l in (1, 2) for m in ("main", "corrupt"))
    A = pd.concat(R, ignore_index=True)
    main, cor = A[A["mode"] == "main"].reset_index(drop=True), A[A["mode"] == "corrupt"].reset_index(drop=True)
    leak = float(max(np.abs(main[c].values - cor[c].values).max() for c in ("E168_p_high", "SIMPLE_p_high", "E168_score", "SIMPLE_score")))
    served = {r["province"]: r["p_high"] for r in json.loads((D / "e168" / "out" / "sealed_2027-Q1.json").read_text())["forecasts"]}
    l1 = main[(main["lead"] == 1) & main["province"].isin(served)]
    repro = float(max(abs(round(p, 4) - served[k]) for k, p in zip(l1["province"], l1["E168_p_high"])))
    out = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "issue_date": str(Pn.q_start(ISSUE).date()), "config_sha256": cfg["config_sha256"],
           "leakage_max_abs_change": leak, "E168_reproduces_served_2027Q1_max_abs_diff": repro,
           "forecasts": main.drop(columns=["mode"]).round(6).to_dict("records")}
    f.write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print("config", cfg["config_sha256"][:12], "seal", hashlib.sha256(f.read_bytes()).hexdigest()[:8], "leak", leak, "E168 repro", repro)
    s = main.assign(E168_HIGH=main["E168_p_high"] >= .5, SIMPLE_HIGH=main["SIMPLE_p_high"] >= .5)
    print(s.groupby("lead")[["E168_HIGH", "SIMPLE_HIGH"]].sum(), "provinces per lead", s.groupby("lead").size().to_dict())
    print("class disagreements:", int((s["E168_HIGH"] != s["SIMPLE_HIGH"]).sum()))
    print(s.groupby("lead")[["E168_tag", "SIMPLE_tag", "scheme"]].first())


if __name__ == "__main__":
    {"config": lambda: print(json.dumps({k: v for k, v in config().items() if k in ("name", "config_sha256")}, indent=1)), "seal": seal}[sys.argv[1]]()
