"""
Provincial prospective validation: an append-only, hash-chained register of sealed provincial risk predictions, and
their scoring against the NEXT measured provincial food-insecurity round, which none of the models has seen.

    python -m app.registry.prospective_provincial verify
    python -m app.registry.prospective_provincial score <round.csv>

<round.csv> columns (template: data/registry/provincial_round_TEMPLATE.csv), one row per province as published by
FNRI/PSA: province, survey, year, p (moderate-or-severe %), se_p (standard error of p, percentage points), ref (the
national value of the same round, %), instrument (HFIAS or FIES). Instruments are never pooled: the seals were trained on
HFIAS, so only HFIAS rows are scored as confirmation; FIES rows are scored separately and labelled as agreement.

Scoring uses E137's target rules (relative logit, survey SE, soft label q, ELEVATED/LOWER/NOT_DISTINGUISHABLE status),
so the result is directly comparable with the development evidence. Baselines on the same rows:
    NAT      base rate of the HFIAS training rows (share of soft labels above national)
    PERS     the province's latest measured relative position (E137 persistence, change variance from training rows)
    REGPREV  the mean latest measured relative position of the province's region
Each model's expected Brier is reported with the paired difference to every baseline.
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


def baselines(new: pd.DataFrame) -> pd.DataFrame:
    """NAT, PERS and REGPREV probabilities for the new round's rows, from the measured HFIAS history only."""
    from app.e137 import model as M137
    from app.e137.outcomes import load
    hist = load()
    hist = hist[hist["has_value"]].sort_values("year")
    latest = hist.groupby("key").last()
    latest.index = latest.index.str.replace(" ", "")
    reg_mean = latest.groupby("region")["y"].mean()
    pers = M137.Persistence().fit(hist)
    out = new[["k"]].copy()
    out["NAT"] = float(hist["q"].mean())
    prev = new["k"].map(latest["y"])
    prev_se = new["k"].map(latest["se_y"])
    out["PERS"] = pers.predict_proba(pd.DataFrame({"prev_y": prev, "prev_se_y": prev_se}))
    rp = new["k"].map(latest["region"]).map(reg_mean)
    out["REGPREV"] = norm.cdf(rp / np.sqrt(M137.tau2(hist)))
    out["region"] = new["k"].map(latest["region"])
    return out


CONFIRM = {"min_n": 20, "auc": 0.75}            # stated in docs/system/DATA_REQUEST_FNRI_PROVINCIAL_HFIAS.md


def diff_ci(m: pd.DataFrame, a: str, b: str, n_boot: int = 1000, seed: int = 20261105) -> dict:
    """EB(a) - EB(b) on rows where both exist, with a cluster (region) bootstrap 95 % interval."""
    d = m.dropna(subset=[a, b, "q"])
    eb = lambda x, c: float(np.mean((x[c] - x["q"]) ** 2 + x["q"] * (1 - x["q"])))
    est = eb(d, a) - eb(d, b)
    regs = d["region"].dropna().unique()
    if len(regs) < 3:
        return {"diff": est, "ci95": None, "n": int(len(d))}
    rng = np.random.default_rng(seed)
    grp = {r: d[d["region"] == r] for r in regs}
    v = []
    for _ in range(n_boot):
        x = pd.concat([grp[r] for r in rng.choice(regs, len(regs))])
        v.append(eb(x, a) - eb(x, b))
    return {"diff": est, "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], "n": int(len(d))}


def _metrics(m: pd.DataFrame, col: str) -> dict:
    d = m.dropna(subset=[col, "q"])
    r = {"n": int(len(d)), "expected_brier": float(np.mean((d[col] - d["q"]) ** 2 + d["q"] * (1 - d["q"])))}
    dec = d[d["status"].isin(["ELEVATED", "LOWER"])]
    r["n_decisive"] = int(len(dec))
    if dec["status"].nunique() == 2:
        yt = (dec["status"] == "ELEVATED").astype(int)
        yh = (dec[col] >= 0.5).astype(int)
        r.update({"auc": float(roc_auc_score(yt, dec[col])), "accuracy": float((yh == yt).mean()),
                  "recall_elevated": float(((yh == 1) & (yt == 1)).sum() / max(1, yt.sum())),
                  "confusion": {"tp": int(((yh == 1) & (yt == 1)).sum()), "fp": int(((yh == 1) & (yt == 0)).sum()),
                                "tn": int(((yh == 0) & (yt == 0)).sum()), "fn": int(((yh == 0) & (yt == 1)).sum())}})
    return r


def score(round_csv: str, path: Path = REGISTER) -> dict:
    if not verify(path):
        raise RuntimeError("register hash chain broken")
    raw = pd.read_csv(round_csv)
    missing = {"province", "p", "se_p", "ref", "instrument"} - set(raw.columns)
    if missing:
        raise ValueError(f"round file lacks columns {sorted(missing)}")
    res = {"round": str(round_csv), "scored_utc": datetime.now(timezone.utc).isoformat(), "by_instrument": {}}
    for inst, rows in raw.groupby(raw["instrument"].str.upper()):
        new = outcome_rows(rows)
        new = new.merge(baselines(new), on="k")
        role = "confirmation (same instrument as training)" if inst == "HFIAS" else "agreement only (different instrument)"
        block = {"role": role, "models": {b: _metrics(new, b) for b in ("NAT", "PERS", "REGPREV")}}
        for rec in read(path):
            body = (BACKEND_DIR / rec["seal_path"]).read_text()
            if hashlib.sha256(body.encode()).hexdigest() != rec["seal_sha256"]:
                block["models"][rec["model_id"]] = {"error": "seal file changed after registration; not scored"}
                continue
            pr = pd.DataFrame(json.loads(body)["predictions"]).rename(columns={"p_elevated": rec["model_id"]})
            m = new.merge(pr[["k", rec["model_id"]]], on="k", how="left")
            r = _metrics(m, rec["model_id"])
            r["minus_baseline_expected_brier"] = {b: r["expected_brier"] - _metrics(m.dropna(subset=[rec["model_id"]]), b)["expected_brier"]
                                                  for b in ("NAT", "PERS", "REGPREV")}
            r["vs_baseline_ci"] = {b: diff_ci(m, rec["model_id"], b) for b in ("PERS", "REGPREV")}
            ok = [r["vs_baseline_ci"][b]["ci95"] is not None and r["vs_baseline_ci"][b]["ci95"][1] < 0 for b in ("PERS", "REGPREV")]
            r["confirmed"] = bool(inst == "HFIAS" and r["n"] >= CONFIRM["min_n"] and all(ok) and r.get("auc", 0) >= CONFIRM["auc"])
            r["unmatched_provinces"] = sorted(m.loc[m[rec["model_id"]].isna(), "k"])
            block["models"][rec["model_id"]] = r
        res["by_instrument"][inst] = block
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
