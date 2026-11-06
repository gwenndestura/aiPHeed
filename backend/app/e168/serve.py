"""
E168 LightGBM-only: live 2027-Q1 to 2027-Q3 forecasts for the five CALABARZON provinces (frozen procedure,
app.e168.lgbm_only.run_proc, unchanged since b11aa542) and the serving function behind
GET /api/v1/final/food-insecurity/outlook once the owner approves it in the registry.

    python -m app.e168.serve live    -> data/e168/out/live_2027.json (artifact the registry hashes)
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
OUT = BACKEND_DIR / "data" / "e168" / "out"
LIVE = OUT / "live_2027.json"
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


class ArtifactMissing(RuntimeError):
    pass


def _forecast(lead):
    from app.e147 import features as Fe
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e164 import auto as A4
    from app.e166 import nested_source as N
    from app.e168.lgbm_only import run_proc
    from app.fi5.target import qindex
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    issue = qindex("2026-Q4")
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, issue, Pv.ROUNDS, "F")
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)].assign(T=issue + lead, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"])
    te = N.add_sources(E154.add_income(Pv.add_inputs(S, M.rows_for(S, five, [lead], "F")), H), L, H, S_P).reset_index(drop=True)
    tr = N.add_sources(E154.add_income(Pv.add_inputs(S, P.tr), H), L, H, S_P).reset_index(drop=True)
    AN = A4.anchors(S, P, tr, te)
    Pr, chosen, tag, _, _, nf = run_proc(tr, te, AN)
    mu, p, half = Pr[chosen]
    return [{"province": te["province"].iloc[k], "lead": lead, "target_quarter": ["2027-Q1", "2027-Q2", "2027-Q3"][lead - 1],
             "score_pct": round(float(pct(mu[k])), 1), "range90_pct": [round(float(pct(mu[k] - half[k])), 1), round(float(pct(mu[k] + half[k])), 1)],
             "p_high": round(float(p[k]), 3), "risk_class": "HIGH" if p[k] >= .5 else "LOW", "config": tag} for k in range(len(te))]


def live():
    H = json.loads((OUT / "lead_horizon.json").read_text())
    rows = _forecast(1) + _forecast(2) + _forecast(3)
    acc = {int(k): {"accuracy": v["accuracy"], "high_recall": v["high_recall"], "persistence_accuracy": v["persistence_accuracy"], "beats_persistence": v["beats_persistence_C2"]} for k, v in H["leads"].items()}
    doc = {"model": "e168-lgbm-1.0", "name": "E168 LightGBM-only (survey baseline + constrained LightGBM change + calibration layer)",
           "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issue_quarter": "2026-Q4", "target": "HFIAS moderate+severe household food insecurity, HIGH at 50 %",
           "provinces": rows, "accuracy_by_lead": acc,
           "acceptance_basis": "owner-defined (2026-11-07): accuracy >= 75 % and significantly better than reusing the latest survey (Brier CI < 0) at each served lead",
           "served_leads": [l for l in (1, 2, 3) if acc[l]["accuracy"] >= 0.75 and acc[l]["beats_persistence"]],
           "statistical_reliability": "E156 C1-C6 not passed at Lead 1 (maximum reliable lead 0 under that stricter test; 72 validation rows from 3 survey rounds)",
           "seals": {"ENNS2022": "f8228fae"}}
    LIVE.write_text(json.dumps(doc, indent=1), newline="\n")
    print(json.dumps(doc, indent=1))


def outlook() -> dict:
    if not LIVE.exists():
        raise ArtifactMissing("E168 live forecast not exported (python -m app.e168.serve live)")
    d = json.loads(LIVE.read_text())
    served = set(d["served_leads"])
    return {**{k: d[k] for k in ("model", "name", "issue_quarter", "target", "accuracy_by_lead", "acceptance_basis", "statistical_reliability", "seals")},
            "provinces": [r for r in d["provinces"] if r["lead"] in served]}


if __name__ == "__main__":
    {"live": live}[sys.argv[1]]()
