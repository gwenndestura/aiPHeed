"""FIRI v1 anchors (FIRI_PROTOCOL.md section 3): P10/P90 of every continuous indicator over the 2021-Q3..2022-Q4 origins
(province rows; national series one value per quarter). Reads predictors only, never a label. Writes
backend/data/thesis/firi_anchors.json (with its SHA-256) once; refuses to overwrite.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/FINAL_Thesis_System/runner/firi_anchors.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

L, E, np, pd = G.L, G.E, G.np, G.pd
BACKEND = EXP.parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
from app.ml.inference import firi as FI  # noqa: E402
from app.news import pipeline_v3 as P3  # noqa: E402

DEST = BACKEND / "data" / "thesis" / "firi_anchors.json"
WINDOW = list(range(L.qi("2021-Q3"), L.qi("2023-Q4") + 1))       # amendment 1
NATIONAL = ("E1", "E2")


def verify_protocol():
    want = (HERE / "FIRI_PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((HERE.parent / "FIRI_PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == want, "FIRI_PROTOCOL.md changed after freezing"
    want1 = (HERE / "FIRI_AMENDMENT_1_SHA256.txt").read_text().split()[0]
    got1 = hashlib.sha256((HERE.parent / "FIRI_PROTOCOL_AMENDMENT_1.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got1 == want1, "FIRI_PROTOCOL_AMENDMENT_1.md changed after freezing"
    return got


def want_amendment():
    return (HERE / "FIRI_AMENDMENT_1_SHA256.txt").read_text().split()[0]


def main():
    sha = verify_protocol()
    if DEST.exists():
        raise SystemExit("anchors already frozen; never recompute")
    d, X, B = E.load()
    vals = {k: [] for k in FI.CONTINUOUS}
    seen_nat = {k: set() for k in NATIONAL}
    for t in WINDOW:
        for p in FI.PROVINCES:
            row = X[(X["t"] == t) & (X["province_code"] == p)]
            if row.empty:
                continue
            feat = row.iloc[0].to_dict()
            raw = FI.raw_indicators(p, feat, None, str(L.origin(t).date()), L.qs(t), None, None, P3.fssi_v3(p, t))
            for k in FI.CONTINUOUS:
                x = raw[k]["x"]
                if x is None:
                    continue
                if k in NATIONAL:
                    if t in seen_nat[k]:
                        continue
                    seen_nat[k].add(t)
                vals[k].append(float(x))
    out = {}
    for k, v in vals.items():
        n = len(v)
        p10, p90 = (float(np.percentile(v, 10)), float(np.percentile(v, 90))) if n else (None, None)
        usable = bool(n >= 5 and p90 is not None and p90 > p10)
        out[k] = {"label": FI.LABELS[k], "n_window_values": n, "p10": p10, "p90": p90, "usable": usable,
                  "reason": None if usable else ("fewer than 5 window values" if n < 5 else "P90 equals P10")}
    body = {"schema": "aipheed.firi.anchors/1", "protocolSha256": sha, "window": ["2021-Q3", "2023-Q4"], "amendment1Sha256": want_amendment(),
            "indicators": out}
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    DEST.write_bytes(json.dumps(body, indent=1, sort_keys=True).encode("utf-8"))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
