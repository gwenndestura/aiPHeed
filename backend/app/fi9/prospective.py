"""Append-only, hash-chained register of prospective Lead-1 forecasts, and their scoring once outcomes are published.

    python -m app.fi9.prospective verify      # checks the hash chain (exit 1 if broken)
    python -m app.fi9.prospective score       # scores the FIRST registered forecast per target quarter, when published

Each record is one JSON line holding its own sha256 and the previous record's. Records are never edited or deleted.
A later issue for an already-registered target quarter is appended as a revision (`revision` > 0) and is not scored:
only the first forecast, made before any later information, counts as prospective evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

from app.fi9 import OUT

REGISTER = OUT / "prospective_register.jsonl"
SCORES = OUT / "prospective_scores.json"


def _hash(rec: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in rec.items() if k != "record_sha256"}, sort_keys=True).encode()).hexdigest()


def read(path=REGISTER) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def verify(path=REGISTER) -> bool:
    prev = "0" * 64
    for rec in read(path):
        if rec["prev_sha256"] != prev or _hash(rec) != rec["record_sha256"]:
            return False
        prev = rec["record_sha256"]
    return True


def append(rec: dict, path=REGISTER) -> dict:
    recs = read(path)
    if not verify(path):
        raise RuntimeError("prospective register hash chain is broken; refusing to append")
    rec = dict(rec)
    rec["revision"] = sum(1 for r in recs if r["target_quarter"] == rec["target_quarter"])
    rec["scored"] = rec["revision"] == 0
    rec["prev_sha256"] = recs[-1]["record_sha256"] if recs else "0" * 64
    rec["record_sha256"] = _hash(rec)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def score(path=REGISTER) -> dict:
    """Score first-registered forecasts whose target quarter's SWS result has been published."""
    from app.fi6.target import labels
    lab = labels().set_index("quarter")
    rows = []
    for r in read(path):
        if not r["scored"] or r["target_quarter"] not in lab.index or pd.isna(lab.loc[r["target_quarter"], "y"]):
            continue
        y = int(lab.loc[r["target_quarter"], "y"])
        h = float(lab.loc[r["target_quarter"], "hunger"])
        row = {"target_quarter": r["target_quarter"], "issue_date": r["issue_date"], "observed": "HIGH" if y else "LOW", "hunger": h,
               "model_class": r["forecast"]["class"], "model_p": r["forecast"]["p_high"], "brier": (r["forecast"]["p_high"] - y) ** 2,
               "in_interval": r["forecast"]["interval95_pct"][0] <= h <= r["forecast"]["interval95_pct"][1]}
        for b, v in r["baselines"].items():
            if v.get("p_high") is not None:
                row[f"brier_{b}"] = (v["p_high"] - y) ** 2
        rows.append(row)
    out = {"n_scored": len(rows), "rows": rows}
    if rows:
        d = pd.DataFrame(rows)
        out["model_accuracy"] = float((d["model_class"] == d["observed"]).mean())
        out["model_brier"] = float(d["brier"].mean())
        out["interval_coverage"] = float(d["in_interval"].mean())
        out["baseline_brier"] = {c[6:]: float(d[c].mean()) for c in d if c.startswith("brier_")}
    SCORES.write_text(json.dumps(out, indent=1, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1:] or ["verify"]
    if cmd == ["verify"]:
        ok = verify()
        print("register intact" if ok else "REGISTER BROKEN", len(read()), "records")
        sys.exit(0 if ok else 1)
    print(json.dumps(score(), indent=1, default=str))
