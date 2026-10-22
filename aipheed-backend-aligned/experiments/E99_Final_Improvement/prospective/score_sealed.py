"""E99-F Q8: score the sealed FIRI v2 prospective forecasts, without retraining, recalibration or threshold change.

Seal: FINAL_Thesis_System/out/firi2_sealed_prospective.csv (commit 151887c, 2026-10-20), SHA-256 of its LF content in
firi2_sealed_prospective.sha256. Rule (FIRI2 protocol section 7, unchanged): the regional mean of the five province
FIRI values >= 0.5 is HIGH; the outcome is the mean of the definition_A SWS rounds of the target quarter > 11.3%.
A target is scored only when its SWS round is in data/inputs/sws_rounds.csv; otherwise it is PENDING.
Run from backend/:  py -3.13 ../aipheed-backend-aligned/experiments/E99_Final_Improvement/prospective/score_sealed.py [out.json]
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEAL = HERE.parents[1] / "FINAL_Thesis_System" / "out" / "firi2_sealed_prospective.csv"
SEAL_SHA = SEAL.with_suffix(".sha256")
SWS = Path("data/inputs/sws_rounds.csv")
LINE, THRESHOLD = 11.3, 0.5


def verify() -> bool:
    raw = SEAL.read_bytes()
    want = SEAL_SHA.read_text().split()[0]
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == want or hashlib.sha256(raw).hexdigest() == want


def wilson_lower(k: int, n: int, z: float = 1.959964) -> float:
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    return c - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)


def quarters_needed(goal: float = 0.75) -> int:
    """Smallest n for which n correct out of n gives a Wilson 95% lower bound above the goal."""
    return next(n for n in range(1, 200) if wilson_lower(n, n) > goal)


def score() -> dict:
    if not verify():
        raise SystemExit("seal does not verify: refusing to score")
    with open(SEAL, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(SWS, newline="", encoding="utf-8") as f:
        sws = [r for r in csv.DictReader(f) if str(r["definition_A"]) == "True"]
    targets = {}
    for r in rows:
        targets.setdefault(r["target"], {"issue_date": r["issue_date"], "values": []})["values"].append(float(r["FIRI"]))
    out = {"seal": str(SEAL.name), "seal_verified": True, "rule": "regional mean FIRI >= 0.5 vs SWS definition_A H > 11.3%",
           "targets": {}}
    for tq, t in sorted(targets.items()):
        reg = sum(t["values"]) / len(t["values"])
        hs = [float(r["H"]) for r in sws if r["quarter"] == tq]
        rec = {"issue_date": t["issue_date"], "regional_mean_firi": round(reg, 6),
               "forecast": "HIGH" if reg >= THRESHOLD else "LOW"}
        if not hs:
            rec["status"] = "PENDING (no definition_A SWS round for this quarter in sws_rounds.csv)"
        else:
            h = sum(hs) / len(hs)
            obs = "HIGH" if h > LINE else "LOW"
            rec.update({"status": "SCORED", "observed_H": h, "observed": obs, "correct": obs == rec["forecast"]})
        out["targets"][tq] = rec
    scored = [v for v in out["targets"].values() if v["status"] == "SCORED"]
    out["scored"] = len(scored)
    out["correct"] = sum(v["correct"] for v in scored)
    out["independent_quarters_needed_for_75pct_claim"] = quarters_needed()
    out["note"] = ("A claim that independent Lead-2 accuracy exceeds 75% needs its Wilson 95% lower bound above 0.75: "
                   f"at least {quarters_needed()} scored quarters even if every one is correct. While the outcome stays "
                   "in one regime, persistence makes the same call, so each quarter also tests little beyond the regime.")
    return out


if __name__ == "__main__":
    res = score()
    txt = json.dumps(res, indent=1, default=float)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(txt, encoding="utf-8")
    print(txt)
