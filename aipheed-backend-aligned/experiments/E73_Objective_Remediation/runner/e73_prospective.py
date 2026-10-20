"""E73 prospective validation tool. It never edits a prediction.

    python -B runner/e73_prospective.py register          -> prospective/SEAL_REGISTER.json (verifies every seal's sha256)
    python -B runner/e73_prospective.py score OUTCOMES.csv -> prospective/scores_<date>.json

OUTCOMES.csv schema (prospective/OUTCOME_SCHEMA.md): quarter, kind, province_code, value, published, source_url.
  kind = SWS_H (regional, % families), OCTA_BL (regional, % families), CPI_FOOD_YOY / CPI_ALL_YOY (province, quarter
  mean of 3 published months), FIR71_HIGH (province, 0/1 from E71's rule).
Scoring rules (fixed before any 2026-Q4 / 2027-Q1 outcome exists):
  * a seal is scored only on outcomes published AFTER its sealing time, for its own target quarter;
  * T43 seals (E68 A0, E70 R0/A1/A2/S0): province HIGH = SWS_H > 11.3 AND (food YoY > P60 OR food - all-items > P60),
    E40 thresholds;
  * FIRI v2 seal: the regional class (mean of the five provinces >= 0.5) vs SWS_H > 11.3 and vs OCTA_BL > 11 (E73
    threshold); province rows are not scored (no provincial outcome exists);
  * E69 tier: regional ELEVATED vs SWS_H > 11.3;
  * E71 seals: province class vs FIR71_HIGH.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

E73 = Path(__file__).resolve().parents[1]
EXP = E73.parent
ROOT = EXP.parents[1]
OUT = E73 / "prospective"
SEALS = {
    "E68_T43_A0": ("E68_Resolve_E67_Critical_Failures/sealed/prospective.csv", "prospective.csv.sha256", "T43", "p", {"arm": "A0"}),
    "E69_TIER": ("E69_Food_Insecurity_Risk_Framework/sealed/outlook_forward.csv", "outlook_forward.csv.sha256", "TIER", "tier", {}),
    "FIRI2_C3": ("FINAL_Thesis_System/out/firi2_sealed_prospective.csv", "firi2_sealed_prospective.sha256", "FIRI", "FIRI", {}),
    **{f"E70_T43_{a}": ("E70_Objectives_Completion/sealed/prospective.csv", "prospective.csv.sha256", "T43", f"{a}_p", {"lead": "2"})
       for a in ("R0", "A1", "A2", "S0")},
    **{f"E71_FIR71_{a}": ("E71_Food_Insecurity_Dimensions/sealed/prospective.csv", "prospective.csv.sha256", "FIR71", f"{a}_p", {"lead": "2"})
       for a in ("LGBM", "DIMFUSE", "LR", "PERSIST")},
}
SWS_LINE, OCTA_LINE = 11.3, 11.0


def _sha(path: Path, lf: bool) -> str:
    b = path.read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if lf else b).hexdigest()


def _sealed_at(rel: str) -> str:
    r = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cI", "--", str(EXP / rel)], capture_output=True, text=True,
                       cwd=ROOT)
    return (r.stdout.strip().splitlines() or [""])[-1]


def register() -> dict:
    reg = {}
    for name, (rel, shafile, kind, col, filt) in SEALS.items():
        p = EXP / rel
        want = (p.parent / shafile).read_text().split()[0]
        got_raw, got_lf = _sha(p, False), _sha(p, True)
        reg[name] = {"file": rel, "kind": kind, "column": col, "filter": filt, "sha256": want,
                     "verified": want in (got_raw, got_lf), "line_endings_normalised": want == got_lf != got_raw,
                     "sealed_at": _sealed_at(rel)}
    OUT.mkdir(exist_ok=True)
    (OUT / "SEAL_REGISTER.json").write_text(json.dumps(reg, indent=1))
    return reg


def _rows(rel, filt):
    with (EXP / rel).open(encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if all(str(r.get(k)) == v for k, v in filt.items())]


def score(outcomes_csv: Path, reg: dict | None = None) -> dict:
    reg = reg or register()
    spec = json.loads((EXP / "E40_SWS_CPI_Tiers" / "label_spec.json").read_text())["thresholds"]
    oc = list(csv.DictReader(Path(outcomes_csv).open(encoding="utf-8")))
    res = {}
    for name, s in reg.items():
        if not s["verified"]:
            res[name] = {"status": "SEAL HASH MISMATCH: not scored"}
            continue
        cut = s["sealed_at"][:10]
        ok = [o for o in oc if o["published"][:10] > cut]                  # published after the seal only
        val = {}
        for o in ok:
            val.setdefault((o["quarter"], o["kind"], o.get("province_code") or ""), []).append(float(o["value"]))
        get = lambda q, k, p="": (sum(val[(q, k, p)]) / len(val[(q, k, p)])) if (q, k, p) in val else None  # noqa: E731
        rows = _rows(s["file"], s["filter"])
        scored = []
        if s["kind"] == "T43":
            for r in rows:
                q, p = r["target"], r["province_code"]
                h, f, a = get(q, "SWS_H"), get(q, "CPI_FOOD_YOY", p), get(q, "CPI_ALL_YOY", p)
                if None in (h, f, a):
                    continue
                y = int(h > SWS_LINE and (f > spec["food"][p] or (f - a) > spec["gap"][p]))
                scored.append({"target": q, "unit": p, "p": float(r[s["column"]]), "y": y})
        elif s["kind"] in ("FIRI", "TIER"):
            by_q = {}
            for r in rows:
                by_q.setdefault(r["target"], []).append(r)
            for q, rs in by_q.items():
                if s["kind"] == "FIRI":
                    p_reg = sum(float(r["FIRI"]) for r in rs) / len(rs)
                    pred = float(p_reg >= 0.5)
                else:
                    pred = float(sum(r["tier"] == "ELEVATED" for r in rs) >= 3)
                h, ob = get(q, "SWS_H"), get(q, "OCTA_BL")
                if h is not None:
                    scored.append({"target": q, "unit": "region:SWS", "p": pred, "y": int(h > SWS_LINE)})
                if ob is not None and s["kind"] == "FIRI":
                    scored.append({"target": q, "unit": "region:OCTA", "p": pred, "y": int(ob > OCTA_LINE)})
        elif s["kind"] == "FIR71":
            for r in rows:
                y = get(r["target"], "FIR71_HIGH", r["province_code"])
                if y is not None:
                    scored.append({"target": r["target"], "unit": r["province_code"], "p": float(r[s["column"]]), "y": int(y)})
        n = len(scored)
        correct = sum(int((x["p"] >= 0.5) == bool(x["y"])) for x in scored)
        res[name] = {"scored": n, "correct": correct, "accuracy": (correct / n) if n else None,
                     "brier": (sum((x["p"] - x["y"]) ** 2 for x in scored) / n) if n else None, "rows": scored,
                     "status": "SCORED" if n else "NO ELIGIBLE OUTCOME YET"}
    OUT.mkdir(exist_ok=True)
    (OUT / f"scores_{date.today()}.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    if sys.argv[1] == "register":
        print(json.dumps({k: (v["verified"], v["sealed_at"]) for k, v in register().items()}, indent=1))
    else:
        r = score(Path(sys.argv[2]))
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in r.items()}, indent=1))
