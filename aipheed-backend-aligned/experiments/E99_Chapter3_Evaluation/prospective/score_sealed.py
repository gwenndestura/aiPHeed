"""E99: score the sealed prospective forecasts, and only when their outcomes are published. No retraining, no
recalibration, no threshold change. Run from backend/:
    py -3.13 ../aipheed-backend-aligned/experiments/E99_Chapter3_Evaluation/prospective/score_sealed.py [out.json]

Seals:
  S-FIRI2: FINAL_Thesis_System/out/firi2_sealed_prospective.csv (FIRI v2 C3; targets 2026-Q4 issued 2026-07-01 and
           2027-Q1 issued 2026-10-01). Rule (FIRI2_PROTOCOL section 7 / E97): regional mean FIRI >= 0.5 vs SWS
           involuntary hunger > 11.3% (mean of the target quarter's definition_A rounds). Province rows reported too.
  S-E99:   E99 runs/<stamp>/sealed_prospective_2026Q4.csv (Algorithm 4 LightGBM k=2, research seal, not published).
           Rule: p_high >= 0.5 vs the Eq. 3 label of 2026-Q4 with the FROZEN median recorded in the seal (the global
           median is not recomputed with new data).
A seal is verified against its recorded SHA-256 on its LF-normalised bytes (git autocrlf rewrites line endings on
Windows checkouts; the content, not the line endings, is what was sealed).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
E99 = HERE.parent
EXP = E99.parent
LINE = 11.3
SEALS = {
    "S-FIRI2": (EXP / "FINAL_Thesis_System" / "out" / "firi2_sealed_prospective.csv",
                (EXP / "FINAL_Thesis_System" / "out" / "firi2_sealed_prospective.sha256")),
}


def e99_seal() -> tuple[Path, Path]:
    run = sorted(p for p in (E99 / "runs").iterdir() if (p / "sealed_prospective_2026Q4.csv").exists())[-1]
    return run / "sealed_prospective_2026Q4.csv", run / "sealed_prospective_2026Q4.sha256"


def verified(csv: Path, sha_file: Path) -> dict:
    rec = sha_file.read_text().split()[0]
    raw = csv.read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    return {"recorded": rec, "raw": hashlib.sha256(raw).hexdigest(), "lf": hashlib.sha256(lf).hexdigest(),
            "ok": rec in (hashlib.sha256(raw).hexdigest(), hashlib.sha256(lf).hexdigest())}


def sws_outcome(q: str) -> dict:
    s = pd.read_csv("data/inputs/sws_rounds.csv")
    s = s[(s["quarter"] == q) & (s["definition_A"].astype(str) == "True")]
    if s.empty:
        return {"status": "PENDING", "reason": f"no definition_A SWS round for {q} in data/inputs/sws_rounds.csv"}
    return {"status": "AVAILABLE", "H": float(s["H"].mean()), "rounds": len(s), "posted": sorted(s["published"].str[:10])}


def cpi_outcome(q: str) -> pd.Series | None:
    p = pd.read_parquet("data/processed/psa_indicators.parquet")
    p = p[(p["quarter"] == q)].dropna(subset=["food_cpi_yoy"])
    if len(p) < 5:
        return None
    return (p.set_index("province_code")["food_cpi_yoy"] - p["food_cpi_yoy"].mean())


def score() -> dict:
    out = {}
    csv, sha = SEALS["S-FIRI2"]
    v = verified(csv, sha)
    S = pd.read_csv(csv, dtype={"province_code": str})
    res = {"verification": v, "targets": {}}
    for tq, g in S.groupby("target"):
        o = sws_outcome(tq)
        r = {"issue_date": g["issue_date"].iloc[0], "regional_mean_FIRI": float(g["FIRI"].mean()), "outcome": o}
        if o["status"] == "AVAILABLE" and v["ok"]:
            y = int(o["H"] > LINE)
            r["regional_call"] = int(r["regional_mean_FIRI"] >= 0.5)
            r["regional_correct"] = r["regional_call"] == y
            r["province_rows_correct"] = int(((g["FIRI"] >= 0.5).astype(int) == y).sum())
        res["targets"][tq] = r
    out["S-FIRI2"] = res
    csv, sha = e99_seal()
    v = verified(csv, sha)
    S = pd.read_csv(csv, dtype={"province_code": str})
    o = sws_outcome("2026-Q4")
    dev = cpi_outcome("2026-Q4")
    r = {"verification": v, "seal_file": str(csv.relative_to(EXP)), "outcome_sws": o,
         "outcome_cpi": "AVAILABLE" if dev is not None else "PENDING (PSA 2026-Q4 food CPI not in psa_indicators)"}
    if o["status"] == "AVAILABLE" and dev is not None and v["ok"]:
        med = float(S["label_threshold_median"].iloc[0])
        y = ((o["H"] + 2 * dev) > med).astype(int)
        S["y"] = S["province_code"].map(y)
        r["rows_correct"] = int(((S["p_high"] >= 0.5).astype(int) == S["y"]).sum())
        r["rows"] = len(S)
    out["S-E99"] = r
    out["status"] = ("SCORED" if all(t["outcome"]["status"] == "AVAILABLE" for t in out["S-FIRI2"]["targets"].values())
                     else "PENDING: independent validation not yet possible")
    return out


if __name__ == "__main__":
    res = score()
    txt = json.dumps(res, indent=1, default=str)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(txt, encoding="utf-8")
    print(txt)
