"""E32 shared data access: the E31 corrected inputs (read-only) and the release-time rules.

Sources (all 2021-Q1..2026-Q3, nothing before 2021, nothing published after 2026-10-14):
  * SWS Balance Luzon rounds, vintage 2: verified SWS posting dates for every 2026 round (E31 data_acquired/sws).
  * S1 labels and D / Dnow panels, vintage 2 (PSA OpenStat 0012M4ACP23 food YoY; same construction as E25).
  * News: the E31 store (Google News RSS titles), relevance rule R1.1, FSSI-v2 intensity scores (XLM-R, v2 key).
E31 files are read, never written. E32 writes only inside E32.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

E32 = Path(__file__).resolve().parents[1]
EXPS = E32.parent
E31 = EXPS / "E31_Chapter1_Completion"
BD31 = E31 / "backend_dev"
for p in (E32 / "runner", BD31):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import guard32  # noqa: E402

guard32.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.quarterly import pcf_engine as P  # noqa: E402

INP = BD31 / "data" / "inputs"
STORE = BD31 / "data" / "news_e31"
PROVS = P.PROVINCES
NAMES = P.PROVINCE_NAMES
qk, qs = P.qk, P.qs
FIRST, LAST = "2021-Q1", "2026-Q3"
INPUT_FILES = ("sws_rounds.csv", "s1_labels.csv", "d_quarterly_panel.csv", "dnow_panel.csv")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inputs_manifest() -> dict:
    m = {f: sha(INP / f) for f in INPUT_FILES}
    for f in ("articles.jsonl", "scores.jsonl", "fssi_v2_panel.csv"):
        m["news_e31/" + f] = sha(STORE / f)
    return m


def load() -> dict:
    rounds = pd.read_csv(INP / "sws_rounds.csv")
    S1 = pd.read_csv(INP / "s1_labels.csv", dtype={"province_code": str})
    dq = pd.read_csv(INP / "d_quarterly_panel.csv", dtype={"province_code": str})
    dn = pd.read_csv(INP / "dnow_panel.csv", dtype={"province_code": str})
    for name, df in (("rounds", rounds), ("S1", S1), ("D", dq), ("Dnow", dn)):
        q = df["quarter"].map(qk)
        assert q.min() >= qk(FIRST) and q.max() <= qk(LAST), name
    Dm, Nm = P.panels_from_tables(dq, dn)
    return {"rounds": rounds, "S1": S1, "dq": dq, "dn": dn, "Dm": Dm, "Nm": Nm, "news": news_panel()}


def news_panel() -> pd.DataFrame:
    """Province-quarter and region-quarter news aggregates from the validated (R1.1) articles, by publication quarter.
    Columns: n_attr (province-attributed), n_rel (R1.1 relevant, deduplicated), n_direct, fssi_v2 (bias-weighted mean
    v2 intensity; NaN when no admitted article). Rows for province 'REGION' aggregate the five provinces."""
    p = pd.read_csv(STORE / "fssi_v2_panel.csv", dtype={"province_code": str})
    p = p[p["quarter"].map(qk) <= qk(LAST)]
    out = p.rename(columns={"n_province_attributed": "n_attr", "n_admitted": "n_rel", "FSSI_v2": "fssi_v2"})[
        ["province_code", "quarter", "n_attr", "n_rel", "n_direct", "fssi_v2"]].copy()
    reg = out.groupby("quarter").agg(n_attr=("n_attr", "sum"), n_rel=("n_rel", "sum"), n_direct=("n_direct", "sum"),
                                     fssi_v2=("fssi_v2", "mean")).reset_index()
    reg["province_code"] = "REGION"
    return pd.concat([out, reg[out.columns]], ignore_index=True)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(obj, indent=1, default=float, allow_nan=False).encode("utf-8"))


def clean(o):
    if isinstance(o, float):
        return None if (np.isnan(o) or np.isinf(o)) else o
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.generic):
        return clean(o.item())
    return o
