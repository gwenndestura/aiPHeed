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


def _forecast(lead, issue_label: str = "2026-Q4"):
    """Forecasts issued at the start of `issue_label` (data published before it) for the quarter `lead` quarters later."""
    from app.e147 import features as Fe
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e164 import auto as A4
    from app.e166 import nested_source as N
    from app.e168 import robust as RB
    from app.e168.lgbm_only import run_proc
    from app.fi5.target import qindex, qlabel
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    issue = qindex(issue_label)
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, issue, Pv.ROUNDS, "F")
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)].assign(T=issue + lead, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, five, [lead], "F")), L, H, S_P).reset_index(drop=True)   # same path as lgbm_only.task
    tr = N.add_sources(Pv.add_inputs(S, P.tr), L, H, S_P).reset_index(drop=True)
    AN = A4.anchors(S, P, tr, te)
    te, filled = RB.fill_unseen_missing(tr, te)      # E183: inputs never missing in training are filled, not read as zero
    Pr, chosen, tag, _, _, nf = run_proc(tr, te, AN)
    mu, p, half = Pr[chosen]
    used = RB.used_by(tag, filled)                   # only inputs of the selected feature set count for the warning
    return [{"province": te["province"].iloc[k], "lead": lead, "target_quarter": qlabel(issue + lead),
             "score_pct": round(float(pct(mu[k])), 1), "range90_pct": [round(float(pct(mu[k] - half[k])), 1), round(float(pct(mu[k] + half[k])), 1)],
             "p_high": round(float(p[k]), 3), "risk_class": "HIGH" if p[k] >= .5 else "LOW", "config": tag,
             "inputs_filled": len(used[k]), "inputs_filled_names": ";".join(used[k]), "data_complete": not used[k]} for k in range(len(te))]


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


def artifact():
    """The approved E168 artifact: the registry's production artifact when it is an E168 issue (or, once the owner
    promotes it, an E184 issue in the same schema), else the 2026-Q4 export."""
    try:
        from app import registry as R
        p = R.production()
        if p["model_id"] in ("e168-lgbm-1.0", "e184-lgbm-syn50-1.0"):
            return BACKEND_DIR / p["artifact_path"]
    except Exception:
        pass
    return LIVE


def _data_used() -> list[dict]:
    try:
        from app.ml.inference import e168_system as E
        return E.data_used()["items"]
    except Exception:                       # the list is descriptive; the forecast is served without it
        return []


def outlook() -> dict:
    path = artifact()
    if not path.exists():
        raise ArtifactMissing("E168 live forecast not exported (python -m app.e168.serve live)")
    d = json.loads(path.read_text())
    served = set(d["served_leads"])
    y, q = d["issue_quarter"].split("-Q")
    cut = d.get("information_cutoff") or f"{y}-{3 * (int(q) - 1) + 1:02d}-01"      # a live issue carries its own as-of date
    return {**{k: d[k] for k in ("model", "name", "issue_quarter", "target", "accuracy_by_lead", "acceptance_basis", "statistical_reliability", "seals")},
            "origin_date": cut, "classification_threshold": 0.5, "information_cutoff": f"data published before {cut}",
            "created_utc": d.get("created_utc"), "data_published_by": d.get("data_published_by") or cut,
            "data_through": (pd.Timestamp(cut) - pd.Timedelta(days=1)).date().isoformat(), "data_used": _data_used(),
            "provinces": [r for r in d["provinces"] if r["lead"] in served]}


if __name__ == "__main__":
    {"live": live}[sys.argv[1]]()
