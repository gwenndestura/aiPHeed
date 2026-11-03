"""Prospective challenger register: government vs government + news forecasts registered before their outcome is
published, at the FI9 issue timing (OP1) and at quarter end (QE1). Production FI9 is not touched.

    python -m app.fi9x.challenger issue --origin QE1 --as-of 2026-09-30     # target = next quarter after as-of's quarter
    python -m app.fi9x.challenger verify
    python -m app.fi9x.challenger score

Only data published on or before --as-of are used (Designer as-of cutoff; news published on or before the date).
A registration is refused if the target quarter's SWS result is already published.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.fi6.target import labels, quarterly
from app.fi7.design import Designer
from app.fi9 import prospective as PR
from app.fi9r.evaluate import _tau
from app.fi9x import OUT, VERSION
from app.fi9x import newsfeat as NF
from app.fi9x import study as S

REGISTER = OUT / "challenger_register.jsonl"
MODELS = ["Naive persistence", "C0 damped persistence (production)", "Seasonal damped persistence", "LightGBM (government)",
          "LightGBM (government + news R0)", "LightGBM (government + news R1)"]


def _frame(origin: str, as_of: pd.Timestamp):
    timing, lead = S.ORIGINS[origin]
    D = Designer(timing, as_of=as_of)
    iq = D.issue_qis[-1]
    X = D.frame(lead)
    X = X[X["issue_ts"] < D.dates[iq]]
    live = pd.DataFrame([D.row(iq, iq + lead)])
    live["issue_ts"] = pd.to_datetime(live["issue_date"])
    X = pd.concat([X, live], ignore_index=True).sort_values("issue_ts").reset_index(drop=True)
    nf = NF.features(X["issue_ts"]).rename(columns={"issue_date": "issue_ts"})
    X = X.merge(nf, on="issue_ts", how="left")
    X = pd.concat([X, NF.expanding_z(X, S.RAW)], axis=1)
    for w in ["QTD", "W90", "LCQ"]:
        X[f"nidx_{w}"] = X[[f"z_dom_{d}_{w}" for d in S.DOMS]].mean(axis=1, skipna=False)
    return X, D.q[D.q["published"] <= D.dates[iq]], D.dates[iq]


def issue(origin: str, as_of: str) -> dict:
    X, q, d = _frame(origin, pd.Timestamp(as_of))
    live = X.iloc[[-1]]
    target = live["target_quarter"].iloc[0]
    if target in set(quarterly().loc[quarterly()["published"] <= pd.Timestamp(datetime.now().date()), "quarter"]):
        raise RuntimeError(f"{target} is already published: not a prospective forecast")
    L = X[X["y"].notna() & (X["target_published"] <= d)].reset_index(drop=True)
    out = {}
    for name in MODELS:
        kind, feats = S.CONFIGS[name]
        r = S._fit_base(kind, feats, L, live, q)
        if r.get("cls") is None:             # training-only threshold from earlier rows' walk-forward predictions
            wf = []
            for i in range(len(L)):
                tr = L[L["target_published"] <= L.loc[i, "issue_ts"]]
                if len(tr) >= S.MIN_TRAIN:
                    wf.append((i, S._fit_base(kind, feats, tr, L.loc[[i]], q[q["published"] <= L.loc[i, "issue_ts"]])["p"]))
            inn = [i for i, _ in wf][max(25, int(len(wf) * 0.6)):]
            pw = dict(wf)
            tau = _tau(np.array([pw[i] for i in inn]), L.loc[inn, "y"].to_numpy(int)) if len(inn) >= 10 else 0.5
            r["cls"], r["tau"] = int(r["p"] >= tau), tau
        out[name] = {"p_high": round(float(r["p"]), 4), "class": "HIGH" if r["cls"] else "LOW",
                     **({"level_pp": round(float(r["level"]), 2)} if r.get("level") is not None and r.get("level") == r.get("level") else {})}
    rec = {"origin": origin, "issue_date": str(pd.Timestamp(d).date()), "target_quarter": target, "as_of": as_of,
           "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version": VERSION,
           "latest_reading_quarter": live["last_reading_quarter"].iloc[0], "news_index_z": None if pd.isna(live["nidx_QTD"].iloc[0]) else round(float(live["nidx_QTD"].iloc[0]), 3),
           "forecast": out["C0 damped persistence (production)"] | {"interval95_pct": [None, None]}, "baselines": {}, "models": out}
    return PR.append(rec, REGISTER)


def score() -> dict:
    lab = labels().set_index("quarter")
    rows = []
    for r in PR.read(REGISTER):
        t = r["target_quarter"]
        if not r["scored"] or t not in lab.index or pd.isna(lab.loc[t, "y"]):
            continue
        y = int(lab.loc[t, "y"])
        rows.append({"origin": r["origin"], "target": t, "y": y, **{f"brier|{m}": (v["p_high"] - y) ** 2 for m, v in r["models"].items()},
                     **{f"correct|{m}": int((v["class"] == "HIGH") == bool(y)) for m, v in r["models"].items()}})
    res = {"n_scored": len(rows), "rows": rows}
    if rows:
        d = pd.DataFrame(rows)
        res["mean"] = d.drop(columns=["origin", "target", "y"]).mean().to_dict()
    (OUT / "challenger_scores.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["issue", "verify", "score"])
    ap.add_argument("--origin", default="QE1", choices=["OP1", "QE1"])
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()
    if a.cmd == "issue":
        rec = issue(a.origin, a.as_of)
        print(rec["origin"], rec["issue_date"], "->", rec["target_quarter"], json.dumps(rec["models"]))
    elif a.cmd == "verify":
        print("intact" if PR.verify(REGISTER) else "BROKEN", len(PR.read(REGISTER)))
    else:
        print(json.dumps(score(), indent=1))
