"""
E178 shared helpers (docs/e178/PROTOCOL.md): synthetic labels, the production issue and its inputs, the two gitignored raw
inputs, feature bounds, SHA-256 hashing and the JSONL run log.

Everything here only READS the E168 files and the registry; it never writes to them.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
ROOT = D / "e178"
SYN = ROOT / "synthetic"                     # every synthetic file lives under a folder named synthetic/
OUT = ROOT / "out"
DOCS = BACKEND_DIR.parent / "docs" / "e178"
LABEL = "SYNTHETIC – FOR DEMONSTRATION"
INPUTS = ["e152/out/local_panel.parquet", "e151/out/news_panel.parquet", "hfias/clean/enns_hfias.csv"]   # = app.e168.regenerate.INPUTS
INCOME_RAW = D / "e154" / "raw" / "regional_income_long.csv"
INCOME_LOCK = D / "e154" / "out" / "lock.json"
LABEL_COLS = ["is_synthetic", "scenario_id", "generator_seed"]


class ProvenanceError(RuntimeError):
    pass


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path) -> str:
    return str(Path(path).resolve().relative_to(BACKEND_DIR.parent)).replace("\\", "/")


# ------------------------------------------------------------------------------------------------- production issue
def production_issue() -> dict:
    """The registry's production E168 artifact, its manifest and its information cut-off (read-only)."""
    reg = json.loads((D / "registry" / "registry.json").read_text())
    p = reg["production"]
    art = BACKEND_DIR / p["artifact_path"]
    man = json.loads((art.parent / "manifest.json").read_text())
    live = json.loads(art.read_text())
    y, q = live["issue_quarter"].split("-Q")
    cut = live.get("information_cutoff") or f"{y}-{3 * (int(q) - 1) + 1:02d}-01"
    return {"model_id": p["model_id"], "artifact": art, "folder": art.parent.name, "issue": live["issue_quarter"],
            "cutoff": cut, "published": live.get("data_published_by") or cut, "inputs_sha256": man["inputs_sha256"],
            "artifact_sha256": sha256(art), "live": live, "dashboard_rows": art.parent / "dashboard_rows.csv"}


def check_provenance(prod: dict | None = None) -> dict:
    """Stop unless the inputs are the ones the production issue was made from and the consumption source matches its lock."""
    prod = prod or production_issue()
    got = {p: sha256(D / p) for p in INPUTS}
    bad = {p: (got[p], prod["inputs_sha256"].get(p)) for p in INPUTS if got[p] != prod["inputs_sha256"].get(p)}
    if bad:
        raise ProvenanceError(f"inputs differ from the production issue's manifest: {bad}")
    if not INCOME_RAW.exists():
        raise ProvenanceError(f"{rel(INCOME_RAW)} is missing (gitignored PSA regional consumption). Copy it in; its "
                              f"SHA-256 must equal the value in {rel(INCOME_LOCK)}.")
    want = json.loads(INCOME_LOCK.read_text())["hashes"]["regional_income_long.csv"]
    have = sha256(INCOME_RAW)
    if have != want:
        raise ProvenanceError(f"{rel(INCOME_RAW)} SHA-256 {have} differs from the lock {want}")
    from app.e155 import test as T155
    return {"inputs_sha256": got, "regional_income_long.csv": have,
            "sunstar": "raw file" if T155.SUN.exists() else "empty stand-in (columns used by no E168 feature set)"}


def sun_panel() -> pd.DataFrame:
    """app.e155.test.panel(), or, when the gitignored raw SunStar file is absent, an empty panel with the same columns.
    No sun_* column is in any E168 feature set or trigger list, so E168's output cannot depend on it (verified by the
    bit-for-bit reproduction checks in tests and run logs)."""
    from app.e155 import test as T155
    if T155.SUN.exists():
        return T155.panel()
    return pd.DataFrame({"key": pd.Series(dtype=object), "qi": pd.Series(dtype="int64"),
                         **{c: pd.Series(dtype=float) for c in T155.SUNCOLS}})


@contextlib.contextmanager
def patched(obj, name: str, value):
    """Temporarily replace obj.name in this process only (never on disk)."""
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


@contextlib.contextmanager
def sun_standin():
    """serve._forecast imports app.e155.test.panel at call time; route it to sun_panel() for the duration."""
    from app.e155 import test as T155
    if T155.SUN.exists():
        yield
        return
    with patched(T155, "panel", sun_panel):
        yield


def pipeline_inputs():
    """(H, L, S_P): the regional consumption table, the local panel and the SunStar panel, as lgbm_only.evaluate loads them."""
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    return E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()


# ------------------------------------------------------------------------------------------------------ subprocess
def at_production_cutoff(prod: dict) -> bool:
    return os.getenv("AIPHEED_LIVE_ASOF") == prod["cutoff"] and os.getenv("AIPHEED_LIVE_PUBLISHED") == prod["published"]


def rerun_at_cutoff(module: str, args: list[str], prod: dict) -> int:
    """Re-run `python -m module args` with the production issue's cut-off set before any pipeline import (the panels read
    AIPHEED_LIVE_ASOF when they are imported), as app.e168.live_refresh does."""
    env = {**os.environ, "AIPHEED_LIVE_ASOF": prod["cutoff"], "AIPHEED_LIVE_PUBLISHED": prod["published"],
           "PYTHONPATH": str(BACKEND_DIR), "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, "-m", module, *args], cwd=str(BACKEND_DIR), env=env).returncode


# ----------------------------------------------------------------------------------------------- labels and bounds
def label(df: pd.DataFrame, scenario_id: str, generator_seed: int | None, synthetic: bool = True) -> pd.DataFrame:
    df = df.copy()
    df["is_synthetic"] = bool(synthetic)
    df["scenario_id"] = scenario_id
    df["generator_seed"] = pd.array([generator_seed] * len(df), dtype="Int64")
    return df


def bounds(frames: list[pd.DataFrame], cols: list[str]) -> pd.DataFrame:
    """Per-column min, max and SD over real rows (the protocol's 'real as-of feature rows')."""
    x = pd.concat([f[[c for c in cols if c in f]] for f in frames], ignore_index=True)
    return pd.DataFrame({"min": x.min(), "max": x.max(), "sd": x.std(ddof=1), "n": x.notna().sum()})


# ------------------------------------------------------------------------------------------------- logs and hashes
class RunLog:
    def __init__(self, path: Path, fresh: bool = True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if fresh:
            self.path.write_text("", newline="\n")

    def __call__(self, event: str, **kw) -> None:
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"utc": utc(), "event": event, **kw}, default=_json_default, ensure_ascii=False) + "\n")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    if isinstance(o, Path):
        return rel(o)
    return str(o)


def dump_json(obj, path: Path) -> None:
    Path(path).write_text(json.dumps(obj, indent=1, default=_json_default, ensure_ascii=False), encoding="utf-8", newline="\n")


def write_hashes(outputs: list[Path], path: Path, extra: dict | None = None) -> dict:
    code = sorted((BACKEND_DIR / "app" / "e178").glob("*.py"))
    doc = {"utc": utc(), "outputs": {rel(p): sha256(p) for p in outputs if Path(p).exists()},
           "code": {rel(p): sha256(p) for p in code}, "protocol": {rel(DOCS / "PROTOCOL.md"): sha256(DOCS / "PROTOCOL.md")},
           **(extra or {})}
    dump_json(doc, path)
    return doc
