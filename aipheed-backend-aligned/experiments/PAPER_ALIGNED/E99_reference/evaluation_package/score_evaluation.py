"""E99 evaluation package scorer (Objective 5 / H5 and Objective 3 / H4), from ACTUAL responses only.

    py -3.13 score_evaluation.py iso_responses.csv h4_rankings.csv [out.json]      (run from backend/)

iso_responses.csv: respondent_id, agency, q1..q15 (1-5, blank = unanswered); the E97 item map
                   (E97_Validation_Completion/iso25010/item_map.json) defines the characteristics.
h4_rankings.csv:   respondent_id, agency, province (Batangas|Cavite|Laguna|Quezon|Rizal), top1..top5 (PSGC lgu_code of
                   the five LGUs the evaluator judges most food-insecurity vulnerable in that province, most first).

Eligibility (Chapter I): agency must be exactly "DA Regional Field Office IV-A" (the form's fixed option); other rows are
excluded and counted. Export checks: required columns, unique respondent_id, Likert values in 1-5, LGU codes valid
for the stated province, no repeated LGU in one ranking.

H4 rule (fixed before any response): for each province with >= 3 eligible rankings, the evaluators' Borda top 5
(5 points for top1 .. 1 for top5) is compared with the served vulnerability top 5 (0.6 poverty_norm + 0.4
density_norm within province). H4 is rejected iff at least 4 of the 5 provinces are scorable and in at least 4 of the
scorable provinces the overlap is >= 3 of 5. Each province also reports the hypergeometric chance probability of an
overlap at least that large.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import hypergeom

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
MAP = json.loads((EXP / "E97_Validation_Completion" / "iso25010" / "item_map.json").read_text(encoding="utf-8"))
AGENCY = "DA Regional Field Office IV-A"
REQUIRED = 50
PROVINCES = ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")


def _rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)]


def check_iso(rows: list[dict]) -> list[str]:
    errs = []
    need = {"respondent_id", "agency", *[f"q{i}" for i in range(1, 16)]}
    if rows and not need <= set(rows[0]):
        errs.append(f"missing columns: {sorted(need - set(rows[0]))}")
    ids = [r.get("respondent_id") for r in rows]
    if len(ids) != len(set(ids)):
        errs.append("duplicate respondent_id")
    for r in rows:
        for i in range(1, 16):
            v = (r.get(f"q{i}") or "").strip()
            if v and v not in {"1", "2", "3", "4", "5"}:
                errs.append(f"{r.get('respondent_id')}: q{i}={v!r} is not 1-5")
    return errs


def score_iso(path: Path) -> dict:
    rows = [r for r in _rows(path) if any((r.get(f"q{i}") or "").strip() for i in range(1, 16))]
    errs = check_iso(rows)
    if errs:
        return {"status": "INVALID_EXPORT", "errors": errs[:20]}
    elig = [r for r in rows if (r.get("agency") or "").strip() == AGENCY]
    out = {"submitted": len(rows), "eligible": len(elig), "excluded_not_DA": len(rows) - len(elig), "required": REQUIRED}
    if not elig:
        return {**out, "status": "NO_RESPONSES", "remaining": f"collect {REQUIRED} eligible DA Region IV-A responses"}
    out["status"] = "COMPLETE" if len(elig) >= REQUIRED else "PARTIAL"
    out["characteristics"] = {}
    for name, spec in MAP["characteristics"].items():
        vals = [int(r[f"q{i}"]) for r in elig for i in spec["items"] if (r.get(f"q{i}") or "").strip()]
        m = statistics.fmean(vals)
        band = next(lab for lo, hi, lab in MAP["interpretation_bands"] if lo <= round(m, 2) <= hi)
        out["characteristics"][name] = {"answers": len(vals), "weighted_mean": round(m, 3),
                                        "sd": round(statistics.stdev(vals), 3) if len(vals) > 1 else None,
                                        "interpretation": band, "favorable": m >= 3.41}
    out["H5_rejected"] = (out["status"] == "COMPLETE" and all(c["favorable"] for c in out["characteristics"].values()))
    return out


def served_top5() -> dict[str, list[str]]:
    v = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    v["density"] = v["population_2024"] / v["land_area_km2"]
    out = {}
    for p, g in v.groupby("province"):
        mm = lambda s: (s - s.min()) / ((s.max() - s.min()) or 1)  # noqa: E731
        idx = 0.6 * mm(g["poverty_value_used"]) + 0.4 * mm(g["density"])
        out[p] = list(g.assign(i=idx).sort_values(["i", "lgu_code"], ascending=[False, True])["lgu_code"].head(5))
    return out


def score_h4(path: Path) -> dict:
    v = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    valid = {p: set(g["lgu_code"]) for p, g in v.groupby("province")}
    size = {p: len(s) for p, s in valid.items()}
    rows = [r for r in _rows(path) if (r.get("top1") or "").strip()]
    errs = []
    for r in rows:
        p = (r.get("province") or "").strip()
        codes = [(r.get(f"top{i}") or "").strip() for i in range(1, 6)]
        codes = [c for c in codes if c]
        if p not in valid:
            errs.append(f"{r.get('respondent_id')}: unknown province {p!r}")
        elif any(c not in valid[p] for c in codes) or len(codes) != len(set(codes)):
            errs.append(f"{r.get('respondent_id')}: invalid or repeated LGU code for {p}")
    if errs:
        return {"status": "INVALID_EXPORT", "errors": errs[:20]}
    elig = [r for r in rows if (r.get("agency") or "").strip() == AGENCY]
    if not elig:
        return {"status": "NO_RESPONSES", "submitted": len(rows), "eligible": 0,
                "remaining": "collect >= 3 eligible DA rankings for each of at least 4 provinces"}
    top = served_top5()
    per = {}
    for p in PROVINCES:
        rs = [r for r in elig if r["province"].strip() == p]
        if len(rs) < 3:
            per[p] = {"rankings": len(rs), "scorable": False}
            continue
        borda: dict[str, int] = {}
        for r in rs:
            for i in range(1, 6):
                c = (r.get(f"top{i}") or "").strip()
                if c:
                    borda[c] = borda.get(c, 0) + (6 - i)
        ev = [c for c, _ in sorted(borda.items(), key=lambda x: (-x[1], x[0]))][:5]
        ov = len(set(ev) & set(top[p]))
        per[p] = {"rankings": len(rs), "scorable": True, "evaluator_top5": ev, "served_top5": top[p], "overlap": ov,
                  "chance_p_overlap_at_least": float(hypergeom.sf(ov - 1, size[p], 5, 5))}
    sc = [x for x in per.values() if x["scorable"]]
    return {"status": "SCORED" if len(sc) >= 4 else "PARTIAL", "eligible": len(elig), "provinces": per,
            "H4_rejected": len(sc) >= 4 and sum(x["overlap"] >= 3 for x in sc) >= 4}


if __name__ == "__main__":
    iso = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "iso_responses_template.csv"
    h4 = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "h4_rankings_template.csv"
    res = {"iso25010": score_iso(iso), "h4": score_h4(h4)}
    txt = json.dumps(res, indent=1)
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(txt, encoding="utf-8")
    print(txt)
