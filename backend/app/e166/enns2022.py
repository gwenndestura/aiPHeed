"""
Untouched test round: ENNS 2022 (PSA-cleared; 20 provinces/HUCs, fieldwork Jul-Dec 2022, reference 2022-Q3 by the
project convention). Frozen E158 and E166 forecasts are generated for EVERY province at Leads 1 and 2 and sealed
BEFORE any 2022 outcome is obtained. Origin "O3" (released rounds at a 2022 issue: 2013, 2015, 2018, 2019).

    python -m app.e166.enns2022 seal          -> data/e166/out/sealed_enns2022.json (+ sha256 printed)
    python -m app.e166.enns2022 score FILE    FILE: province,instrument,measure,pct  (HFIAS moderate_or_severe only)
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
from scipy.stats import norm

from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import panel as sun_panel
from app.e158 import model as E8
from app.e164 import auto as A4
from app.e166 import nested_source as N
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
OUT = BACKEND_DIR / "data" / "e166" / "out"
SEAL = OUT / "sealed_enns2022.json"
T22 = qindex("2022-Q3")
ORIGIN = "O3"
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def targets(S):
    b = S.base.drop_duplicates("key")[["key", "province", "region", "island", "sws_area"]].copy()
    return b.assign(survey="ENNS2022", T=T22)


def task(lead, H, L, S_P):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = T22 - lead
    assert all(s != "ENNS2021" for s in M.released(i, Pv.ROUNDS))
    P = M.Pipeline(S, i, Pv.ROUNDS, ORIGIN)
    tg = targets(S)
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], ORIGIN)), H).reset_index(drop=True)
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    # E158 (frozen)
    base, _ = P.hier.predict(te, te["T"].values)
    m = Pv.Res2(E8.COLS).fit(tr)
    mu8 = base + m.predict(te)
    sd8, half8, _ = m.scale(te["gap_q"].values)
    # E166 (frozen procedure)
    tr6, te6 = N.add_sources(tr, L, H, S_P), N.add_sources(te, L, H, S_P)
    AN = A4.anchors(S, P, tr6, te6)
    mu6, p6, half6, sd6, tag, src, miss = N.run_proc(tr6, te6, AN)
    o = te[["key", "province", "region", "island", "lead", "gap_q"]].copy()
    o["E158_score"], o["E158_p_high"], o["E158_low90"], o["E158_high90"] = pct(mu8).round(2), norm.cdf(mu8 / sd8).round(4), pct(mu8 - half8).round(2), pct(mu8 + half8).round(2)
    o["E166_score"], o["E166_p_high"], o["E166_low90"], o["E166_high90"] = pct(mu6).round(2), np.round(p6, 4), pct(mu6 - half6).round(2), pct(mu6 + half6).round(2)
    o["mu_E158"], o["mu_E166"], o["sd_E158"], o["E166_config"], o["E166_source"], o["E166_source_missing"] = mu8, mu6, sd8, tag, src, miss
    return o


def seal():
    if SEAL.exists():
        raise SystemExit("already sealed: " + hashlib.sha256(SEAL.read_bytes()).hexdigest())
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    R = pd.concat(Parallel(n_jobs=2)(delayed(task)(h, H, L, S_P) for h in (1, 2)), ignore_index=True)
    doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "target": "ENNS 2022 provincial HFIAS moderate+severe, reference 2022-Q3", "origin": ORIGIN,
           "models": {"E158": "frozen (seal f69e7a02 model)", "E166": "frozen nested-source procedure"}, "rule": "HIGH = score >= 50; scored only on HFIAS moderate_or_severe rows",
           "forecasts": R.round(6).to_dict("records")}
    SEAL.write_text(json.dumps(doc, indent=1, default=float), newline="\n")
    print("sealed", len(R), "rows; sha256", hashlib.sha256(SEAL.read_bytes()).hexdigest())


if __name__ == "__main__":
    {"seal": seal}[sys.argv[1]]()
