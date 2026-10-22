"""E99-F Q7: ISO/IEC 25010 scoring from ACTUAL DA Region IV-A responses only (v2: explicit eligibility rules).

Input CSV columns (see iso_responses_template.csv):
    respondent_id, submitted_at, agency, office_unit, consent, q1..q15   (q values 1-5; blank = not answered)
Eligibility (all required, decided before any response exists):
    E1 agency is DA Region IV-A (DA RFO IV-A / Department of Agriculture Regional Field Office IV-A);
    E2 consent == "yes";  E3 respondent_id is unique (later duplicates are excluded);
    E4 every answered item is an integer 1-5, and at least one item of each characteristic is answered.
Excluded rows are listed with their reason and never imputed. Items map to characteristics through
../../E97_Validation_Completion/iso25010/item_map.json (unchanged since E97); favourable = weighted mean >= 3.41.
    py -3.13 score_iso25010_v2.py responses.csv [out.json]
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = json.loads((HERE.parents[1] / "E97_Validation_Completion" / "iso25010" / "item_map.json").read_text(encoding="utf-8"))
REQUIRED = ["respondent_id", "submitted_at", "agency", "office_unit", "consent"] + [f"q{i}" for i in range(1, 16)]
DA = re.compile(r"^\s*(DA\s*(RFO)?\s*(Region)?\s*IV-?A|Department of Agriculture.*(IV-?A|CALABARZON))\s*$", re.I)


def band(m: float) -> str:
    return next((lab for lo, hi, lab in MAP["interpretation_bands"] if lo <= round(m, 2) <= hi), "out of range")


def eligible(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    ok, excluded, seen = [], [], set()
    for r in rows:
        rid = (r.get("respondent_id") or "").strip()
        vals = [(r.get(f"q{i}") or "").strip() for i in range(1, 16)]
        why = None
        if not DA.match(r.get("agency") or ""):
            why = "E1 agency is not DA Region IV-A"
        elif (r.get("consent") or "").strip().lower() != "yes":
            why = "E2 no recorded consent"
        elif not rid or rid in seen:
            why = "E3 missing or duplicate respondent_id"
        elif any(v and v not in {"1", "2", "3", "4", "5"} for v in vals):
            why = "E4 an answer outside 1-5"
        elif any(not any(vals[i - 1] for i in spec["items"]) for spec in MAP["characteristics"].values()):
            why = "E4 a characteristic has no answered item"
        seen.add(rid)
        (excluded if why else ok).append({**r, "_reason": why} if why else r)
    return ok, excluded


def score(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (rd.fieldnames or [])]
        if missing:
            raise SystemExit(f"export format: missing columns {missing}")
        rows = [r for r in rd if any((r.get(c) or "").strip() for c in REQUIRED)]
    req = MAP["required_respondents"]
    if not rows:
        return {"status": "NO_RESPONSES", "eligible": 0, "required": req,
                "remaining": f"collect {req} eligible DA Region IV-A responses (items 1-15)"}
    ok, excluded = eligible(rows)
    out = {"status": "COMPLETE" if len(ok) >= req else ("PARTIAL" if ok else "NO_ELIGIBLE_RESPONSES"),
           "submitted": len(rows), "eligible": len(ok), "required": req,
           "excluded": [{"respondent_id": r.get("respondent_id"), "reason": r["_reason"]} for r in excluded],
           "characteristics": {}}
    for name, spec in MAP["characteristics"].items():
        vals = [int(r[f"q{i}"]) for r in ok for i in spec["items"] if (r.get(f"q{i}") or "").strip()]
        if not vals:
            continue
        m = statistics.fmean(vals)
        out["characteristics"][name] = {"items": spec["items"], "answers": len(vals), "weighted_mean": round(m, 3),
                                        "sd": round(statistics.stdev(vals), 3) if len(vals) > 1 else None,
                                        "interpretation": band(m), "favorable": m >= 3.41}
    if out["status"] != "COMPLETE":
        out["remaining"] = f"{req - len(ok)} more eligible responses needed for the Chapter I sample"
    out["h5_decision"] = ("not decidable before COMPLETE" if out["status"] != "COMPLETE" else
                          "H5 rejected (favourable on all three)" if all(c["favorable"] for c in out["characteristics"].values())
                          else "H5 not rejected")
    return out


if __name__ == "__main__":
    res = score(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "iso_responses_template.csv")
    txt = json.dumps(res, indent=1)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(txt, encoding="utf-8")
    print(txt)
