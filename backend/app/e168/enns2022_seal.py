"""
Seal the FROZEN E168 LightGBM-only procedure for ENNS 2022 (every province, Leads 1-2, origin O3), before any 2022
outcome is seen. Same construction as app.e166.enns2022; the E168 procedure (lgbm_only.run_proc) is unchanged.

    python -m app.e168.enns2022_seal   -> data/e168/out/sealed_enns2022.json (+ sha256 printed)
"""
from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.e147 import features as Fe
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import panel as sun_panel
from app.e164 import auto as A4
from app.e166 import nested_source as N
from app.e166.enns2022 import ORIGIN, T22, targets
from app.e168.lgbm_only import OUT, run_proc

warnings.filterwarnings("ignore")
SEAL = OUT / "sealed_enns2022.json"
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def task(lead, H, L, S_P):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = T22 - lead
    rel = M.released(i, Pv.ROUNDS)
    assert "ENNS2021" not in rel
    P = M.Pipeline(S, i, Pv.ROUNDS, ORIGIN)
    te = N.add_sources(E154.add_income(Pv.add_inputs(S, M.rows_for(S, targets(S), [lead], ORIGIN)), H), L, H, S_P).reset_index(drop=True)
    tr = N.add_sources(E154.add_income(Pv.add_inputs(S, P.tr), H), L, H, S_P).reset_index(drop=True)
    AN = A4.anchors(S, P, tr, te)
    Pr, chosen, tag, _, _, nf = run_proc(tr, te, AN)
    mu, p, half = Pr[chosen]
    o = te[["key", "province", "region", "island", "lead", "gap_q"]].copy()
    o["E168_score"], o["E168_p_high"], o["E168_low90"], o["E168_high90"] = pct(mu).round(2), np.round(p, 4), pct(mu - half).round(2), pct(mu + half).round(2)
    o["E168_class"] = np.where(p >= .5, "HIGH", "LOW")
    o["mu_E168"], o["E168_config"], o["n_features"], o["released"] = mu, tag, nf, "|".join(rel)
    return o


def main():
    if SEAL.exists():
        raise SystemExit("already sealed: " + hashlib.sha256(SEAL.read_bytes()).hexdigest())
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    R = pd.concat([task(h, H, L, S_P) for h in (1, 2)], ignore_index=True)
    doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "target": "ENNS 2022 provincial HFIAS moderate+severe, reference 2022-Q3", "origin": ORIGIN,
           "model": "E168 LightGBM-only, frozen procedure (app.e168.lgbm_only.run_proc, commit b11aa542)", "rule": "HIGH = p_high >= 0.5; scored only on HFIAS moderate_or_severe rows",
           "forecasts": R.round(6).to_dict("records")}
    SEAL.write_text(json.dumps(doc, indent=1, default=str), newline="\n")
    print("sealed", len(R), "rows; sha256", hashlib.sha256(SEAL.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
