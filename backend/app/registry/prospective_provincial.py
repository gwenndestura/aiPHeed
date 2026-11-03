"""
Provincial prospective validation: an append-only, hash-chained register of sealed provincial risk predictions, and
their scoring against the NEXT measured provincial food-insecurity round, which none of the models has seen.

    python -m app.registry.prospective_provincial verify
    python -m app.registry.prospective_provincial score <round.csv>

<round.csv> columns (one row per province, as published by FNRI/PSA): province, survey, year, p (moderate-or-severe %),
se_p, ref (national value of the same round), instrument (HFIAS or FIES). Instruments are never pooled: a seal is scored
only against the instrument it names (HFIAS by default; FIES rounds are scored separately and labelled).

Scoring uses E137's target rules (relative logit, survey SE, soft label q, ELEVATED/LOWER/NOT_DISTINGUISHABLE status),
so the result is directly comparable with the development evidence. Baselines: national base rate (0.5 prior of being
above national is not assumed; the training base rate of the sealing model's rows is used), the province's previous
measured position, and the region's previous measured level.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import roc_auc_score

from app.paths import BACKEND_DIR

REGISTER = BACKEND_DIR / "data" / "registry" / "prospective_provincial.jsonl"
SEALS = {"e138-where-lrp-1.0": "data/e138/out/sealed_prediction.json",
         "e139-lgbm-1.0": "data/e139/out/sealed_prediction.json"}


def _hash(rec: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in rec.items() if k != "record_sha256"}, sort_keys=True).encode()).hexdigest()


def read(path: Path = REGISTER) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def verify(path: Path = REGISTER) -> bool:
    prev = "0" * 64
    for rec in read(path):
        if rec["prev_sha256"] != prev or _hash(rec) != rec["record_sha256"]:
            return False
        prev = rec["record_sha256"]
    return True


def register(model_id: str, seal_path: Path, seal_sha256: str, issue_date: str, path: Path = REGISTER) -> dict:
    """Append a sealed prediction once (same model and sha are not re-appended)."""
    recs = read(path)
    if not verify(path):
        raise RuntimeError("provincial prospective register hash chain is broken; refusing to append")
    if any(r["model_id"] == model_id and r["seal_sha256"] == seal_sha256 for r in recs):
        return next(r for r in recs if r["model_id"] == model_id and r["seal_sha256"] == seal_sha256)
    rec = {"model_id": model_id, "seal_path": str(Path(seal_path).resolve().relative_to(BACKEND_DIR)).replace("\\", "/"),
           "seal_sha256": seal_sha256, "issue_date": issue_date, "registered_utc": datetime.now(timezone.utc).isoformat(),
           "prev_sha256": recs[-1]["record_sha256"] if recs else "0" * 64}
    rec["record_sha256"] = _hash(rec)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def register_existing() -> list[dict]:
    """Register the E138/E139 seals written before this register existed (their sha256 are in their own reports)."""
    out = []
    for mid, rel in SEALS.items():
        p = BACKEND_DIR / rel
        if p.exists():
            body = p.read_text()
            out.append(register(mid, p, hashlib.sha256(body.encode()).hexdigest(), json.loads(body).get("issue_date", "2026-11-04")))
    return out


def outcome_rows(df: pd.DataFrame) -> pd.DataFrame:
    from app.e137.outcomes import _rel, status
    from app.hfias.panel import norm as key
    d = df.copy()
    d["k"] = d["province"].map(key).str.replace(" ", "")
    d["y"], d["se_y"] = _rel(d["p"], d["se_p"], d["ref"].astype(float))
    d["status"] = status(d["y"], d["se_y"], 1.959964 * d["se_p"], d["p"].notna() & d["se_p"].notna())
    d["q"] = norm.cdf(d["y"] / d["se_y"])
    return d


def score(round_csv: str, path: Path = REGISTER) -> dict:
    if not verify(path):
        raise RuntimeError("register hash chain broken")
    new = outcome_rows(pd.read_csv(round_csv))
    res = {"round": round_csv, "scored_utc": datetime.now(timezone.utc).isoformat(), "models": {}}
    for rec in read(path):
        body = (BACKEND_DIR / rec["seal_path"]).read_text()
        if hashlib.sha256(body.encode()).hexdigest() != rec["seal_sha256"]:
            res["models"][rec["model_id"]] = {"error": "seal file changed after registration; not scored"}
            continue
        pr = pd.DataFrame(json.loads(body)["predictions"]).rename(columns={"p_elevated": "p"})
        m = new.merge(pr[["k", "p"]], on="k", suffixes=("_obs", ""))
        eb = float(np.mean((m["p"] - m["q"]) ** 2 + m["q"] * (1 - m["q"])))
        dec = m[m["status"].isin(["ELEVATED", "LOWER"])]
        r = {"n": int(len(m)), "n_decisive": int(len(dec)), "expected_brier": eb}
        if dec["status"].nunique() == 2:
            yt = (dec["status"] == "ELEVATED").astype(int)
            r["auc"] = float(roc_auc_score(yt, dec["p"]))
            r["accuracy"] = float(((dec["p"] >= 0.5).astype(int) == yt).mean())
        res["models"][rec["model_id"]] = r
    return res


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "verify":
        ok = verify()
        print("ok" if ok else "BROKEN")
        sys.exit(0 if ok else 1)
    if cmd == "register-existing":
        print(register_existing())
    if cmd == "score":
        print(json.dumps(score(sys.argv[2]), indent=1))
