"""E39 scoring ledger (append-only JSONL, runs/ledger.jsonl). Replaces the unrecorded "Correct?" export logic.

    init   <eval run dir>                 record every issued forecast (sha256), its baselines, the observed value and the
                                          per-date scores of the one-time evaluation; plus the frozen 2026-Q4/2027-Q1
                                          forecasts (no outcome yet)
    score  <quarter> <label csv>          mechanical: for forecasts of <quarter> without an outcome, read the observed
                                          values from a label CSV built with the FROZEN rule (same columns as
                                          label_v2.csv), append outcome and per-date score entries. Nothing is refitted.
    show                                  print the ledger summary

Per-date scores: Brier (A) or mean absolute error (B, C) for the model and every baseline; the date is the unit.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

E39 = Path(__file__).resolve().parents[1]
LEDGER = E39 / "runs" / "ledger.jsonl"
THRESHOLD = 4.0


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append(entries: list[dict]):
    LEDGER.parent.mkdir(exist_ok=True)
    with LEDGER.open("ab") as f:
        for e in entries:
            body = json.dumps(e, sort_keys=True)
            e = {**e, "sha256": hashlib.sha256(body.encode()).hexdigest()}
            f.write((json.dumps(e, sort_keys=True) + "\n").encode())


def read() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(x) for x in LEDGER.read_bytes().decode().splitlines() if x.strip()]


def _loss(kind, pred, y):
    return (pred - y) ** 2 if kind == "A" else abs(pred - y)


def init(run_dir: str):
    if LEDGER.exists():
        raise SystemExit("ledger exists; it is append-only")
    run = Path(run_dir)
    P = pd.read_csv(run / "predictions.csv", dtype={"province_code": str})
    P = P[P["pred"].notna()]
    entries = []
    for (kind, k, q), g in P.groupby(["target", "lead", "target_quarter"]):
        status = g["status"].iloc[0]
        rows = {}
        for p, h in g.groupby("province_code"):
            rows[p] = {"pred": float(h[h.arm == "model"]["pred"].iloc[0]),
                       "baselines": {a: float(v) for a, v in zip(h[h.arm != "model"]["arm"], h[h.arm != "model"]["pred"])},
                       "observed": None if pd.isna(h["y"].iloc[0]) else float(h["y"].iloc[0])}
        entries.append({"type": "forecast", "target": kind, "lead": int(k), "target_quarter": q,
                        "source": f"evaluation {run.name}", "provinces": {p: {k2: v for k2, v in r.items() if k2 != "observed"}
                                                                           for p, r in rows.items()}, "recorded_at": _now()})
        if status == "Scored":
            entries.append({"type": "outcome", "target": kind, "lead": int(k), "target_quarter": q,
                            "observed": {p: r["observed"] for p, r in rows.items()}, "recorded_at": _now()})
            arms = ["model"] + sorted(next(iter(rows.values()))["baselines"])
            sc = {}
            for a in arms:
                vals = [_loss(kind, (r["pred"] if a == "model" else r["baselines"][a]), r["observed"]) for r in rows.values()]
                sc[a] = sum(vals) / len(vals)
            entries.append({"type": "score", "target": kind, "lead": int(k), "target_quarter": q,
                            "metric": "brier" if kind == "A" else "mae", "per_date": sc, "recorded_at": _now()})
    fr = json.loads((E39 / "frozen" / "E39_FORECASTS_2026Q4_2027Q1.json").read_text())
    for key, rec in fr["forecasts"].items():
        kind, k = key.split("_lead")
        if any(e["type"] == "forecast" and e["target"] == kind and e["lead"] == int(k) and
               e["target_quarter"] == rec["target_quarter"] for e in entries):
            continue
        entries.append({"type": "forecast", "target": kind, "lead": int(k), "target_quarter": rec["target_quarter"],
                        "source": "frozen/E39_FORECASTS_2026Q4_2027Q1.json",
                        "provinces": {p: {"pred": v["pred"], "baselines": v["baselines"]} for p, v in rec["provinces"].items()},
                        "recorded_at": _now()})
    _append(entries)
    print(f"ledger initialised: {len(entries)} entries")


def score(quarter: str, label_csv: str):
    L = pd.read_csv(label_csv, dtype={"province_code": str})
    L = L[L["quarter"] == quarter]
    led = read()
    done = {(e["target"], e["lead"], e["target_quarter"]) for e in led if e["type"] == "outcome"}
    new = []
    for e in led:
        if e["type"] != "forecast" or e["target_quarter"] != quarter or (e["target"], e["lead"], quarter) in done:
            continue
        kind = e["target"]
        if kind == "C":
            if L["H"].isna().all():
                continue                                            # no approved round yet: not scored
            obs = {p: float(L["H"].iloc[0]) for p in e["provinces"]}
        else:
            f = dict(zip(L["province_code"], L["F"]))
            if not all(p in f for p in e["provinces"]):
                continue
            obs = {p: (float(f[p] > THRESHOLD) if kind == "A" else float(f[p])) for p in e["provinces"]}
        if any(v["pred"] is None for v in e["provinces"].values()):
            continue
        arms = ["model"] + sorted(next(iter(e["provinces"].values()))["baselines"])
        sc = {a: sum(_loss(kind, (v["pred"] if a == "model" else v["baselines"][a]), obs[p])
                     for p, v in e["provinces"].items()) / len(obs) for a in arms}
        new += [{"type": "outcome", "target": kind, "lead": e["lead"], "target_quarter": quarter, "observed": obs,
                 "recorded_at": _now()},
                {"type": "score", "target": kind, "lead": e["lead"], "target_quarter": quarter,
                 "metric": "brier" if kind == "A" else "mae", "per_date": sc, "recorded_at": _now()}]
    _append(new)
    print(f"{len(new) // 2} forecasts scored for {quarter}")


def show():
    led = read()
    print({t: sum(1 for e in led if e["type"] == t) for t in ("forecast", "outcome", "score")})


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"init": lambda: init(sys.argv[2]), "score": lambda: score(sys.argv[2], sys.argv[3]), "show": show}[cmd]()
