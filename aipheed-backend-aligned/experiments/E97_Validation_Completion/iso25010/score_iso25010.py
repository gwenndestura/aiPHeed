"""E97 Q8: ISO/IEC 25010 scoring from ACTUAL evaluator responses only.

Input: a CSV with one row per respondent: respondent_id, agency, q1..q15 (integers 1-5; blank = not answered).
    py -3.13 score_iso25010.py responses.csv [out.json]
With no responses (or only the empty template) it reports status NO_RESPONSES and computes nothing.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = json.loads((HERE / "item_map.json").read_text(encoding="utf-8"))


def band(m: float) -> str:
    for lo, hi, lab in MAP["interpretation_bands"]:
        if lo <= round(m, 2) <= hi:
            return lab
    return "out of range"


def score(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if any((r.get(f"q{i}") or "").strip() for i in range(1, 16))]
    req = MAP["required_respondents"]
    if not rows:
        return {"status": "NO_RESPONSES", "respondents": 0, "required": req,
                "remaining": f"collect {req} DA Region IV-A evaluator responses (items 1-15)"}
    bad = [(r.get("respondent_id"), i) for r in rows for i in range(1, 16)
           if (r.get(f"q{i}") or "").strip() and r[f"q{i}"].strip() not in {"1", "2", "3", "4", "5"}]
    if bad:
        raise ValueError(f"invalid Likert values: {bad[:5]}")
    out = {"status": "COMPLETE" if len(rows) >= req else "PARTIAL", "respondents": len(rows), "required": req,
           "agencies": sorted({(r.get("agency") or "").strip() or "unstated" for r in rows}), "characteristics": {}}
    for name, spec in MAP["characteristics"].items():
        vals = [int(r[f"q{i}"]) for r in rows for i in spec["items"] if (r.get(f"q{i}") or "").strip()]
        complete = sum(all((r.get(f"q{i}") or "").strip() for i in spec["items"]) for r in rows)
        m = statistics.fmean(vals)
        out["characteristics"][name] = {
            "items": spec["items"], "answers": len(vals), "respondents_complete": complete,
            "weighted_mean": round(m, 3), "sd": round(statistics.stdev(vals), 3) if len(vals) > 1 else None,
            "interpretation": band(m), "favorable": m >= 3.41,
            "item_means": {i: round(statistics.fmean(int(r[f"q{i}"]) for r in rows if (r.get(f"q{i}") or "").strip()), 3)
                           for i in spec["items"] if any((r.get(f"q{i}") or "").strip() for r in rows)}}
    if out["status"] == "PARTIAL":
        out["remaining"] = f"{req - len(rows)} more responses needed for the Chapter I sample"
    return out


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "response_template.csv"
    res = score(src)
    txt = json.dumps(res, indent=1)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(txt, encoding="utf-8")
    print(txt)
