"""Read-only check that the running API serves exactly the exported forecasts.

1. Map (FIRI v2): every province of every available quarter in /api/v1/quarters, /api/v1/provinces riskScore and
   riskLevel against backend/data/thesis/firi2_history.csv (FIRI rounded to 6 decimals, class lower-cased).
2. P0H4 archive: every row of /api/v1/final/risk/rows against backend/data/ch1_engine/rows.csv, field by field.

    python scripts/check_api_vs_export.py [--base http://127.0.0.1:8000]

Exits 1 on any mismatch. Writes nothing.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def get(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def check_map(base: str) -> tuple[int, int, list[str]]:
    hist = {}
    with open(DATA / "thesis" / "firi2_history.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hist[(r["target"], r["province_code"])] = r
    quarters = [q["id"] for q in get(base, "/api/v1/quarters")["quarters"] if q.get("state") != "unavailable"]
    ok, n, bad = 0, 0, []
    for q in quarters:
        for p in get(base, f"/api/v1/provinces?quarter={q}")["data"]:
            n += 1
            h = hist.get((q, p["provinceCode"]))
            want = None if h is None or h["FIRI"] == "" else round(float(h["FIRI"]), 6)
            cls = None if h is None or h["class"] == "" else h["class"].lower()
            if want is not None and p["riskScore"] == want and p["riskLevel"] == cls:
                ok += 1
            else:
                bad.append(f"map {q} {p['provinceCode']}: API {p['riskScore']}/{p['riskLevel']} export {want}/{cls}")
    return ok, n, bad


def check_rows(base: str) -> tuple[int, int, list[str]]:
    with open(DATA / "ch1_engine" / "rows.csv", newline="", encoding="utf-8") as f:
        exp = {(r["province_code"], r["quarter"]): r for r in csv.DictReader(f)}
    api = get(base, "/api/v1/final/risk/rows")["rows"]
    ok, bad = 0, []
    for r in api:
        e = exp.get((r["province_code"], r["quarter"]))
        diff = [k for k in (e or {}) if str(r.get(k, "")) != e[k]]
        if e is not None and not diff:
            ok += 1
        else:
            bad.append(f"rows {r['quarter']} {r['province_code']}: {'missing in export' if e is None else diff[:5]}")
    if len(api) != len(exp):
        bad.append(f"rows: API {len(api)} vs export {len(exp)}")
    return ok, len(exp), bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    a = ap.parse_args()
    m_ok, m_n, m_bad = check_map(a.base)
    r_ok, r_n, r_bad = check_rows(a.base)
    print(f"FIRI v2 map vs firi2_history.csv: {m_ok}/{m_n}")
    print(f"P0H4 /final/risk/rows vs rows.csv: {r_ok}/{r_n}")
    for b in m_bad + r_bad:
        print("  MISMATCH", b)
    return 0 if not (m_bad or r_bad) and m_ok == m_n and r_ok == r_n else 1


if __name__ == "__main__":
    sys.exit(main())
