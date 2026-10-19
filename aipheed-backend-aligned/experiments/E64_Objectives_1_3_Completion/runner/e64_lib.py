"""E64 shared helpers: protocol check, paths, the backend news module (training/serving parity), sealed-file IO."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E64 = Path(__file__).resolve().parents[1]
EXP = E64.parent
ROOT = EXP.parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
sys.path.insert(0, str(BACKEND))
import e56_lib as G  # noqa: E402

E, F, I7, L, np, pd = G.E, G.F, G.I7, G.L, G.np, G.pd
ORIGINS_EVAL = list(range(L.qi("2023-Q4"), L.qi("2026-Q1") + 1))
ORIGINS_OP = [L.qi("2026-Q2"), L.qi("2026-Q3")]
DEV = [f"{y}-Q{q}" for y, q in [(2024, 2), (2024, 3), (2024, 4), (2025, 1), (2025, 2), (2025, 3)]]
E60_FEAT = EXP / "E60_E58_Accuracy_Optimization" / "data" / "news_features.csv"
HIST_COLS = ["hist_ps_last", "hist_ps_share4"]


def verify_protocol():
    want = (E64 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E64 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("E64 PROTOCOL.md changed after freezing")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_sealed(df: pd.DataFrame, path: Path):
    if path.exists():
        raise SystemExit(f"{path.name} already sealed; written once")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(df.to_csv(index=False, float_format="%.12g", lineterminator="\n").encode())
    (path.parent / (path.name + ".sha256")).write_text(sha(path) + f"  {path.name}\n")


def n3_table() -> pd.DataFrame:
    from app.news import pipeline_v3 as P
    rows = []
    for t in range(L.qi("2021-Q1"), L.qi("2026-Q3") + 1):
        for r in P.n3_features(t):
            rows.append({k: v for k, v in r.items() if k not in ("article_keys", "national_keys")})
    return pd.DataFrame(rows)
