"""
E11 data-access guard (copy of the E9 guard; adds read-only access to the E9 experiment folder). Import and call install() BEFORE importing any project module.

Policy:
  * Reads of project data are allowed ONLY for the hash-pinned ALLOW list.
  * Parquet is readable ONLY through read_allowed_parquet(), which verifies the SHA-256 and applies a
    read-time row filter (quarter <= the file's maximum), so rows after the eligible window are never
    returned to Python. Every other parquet entry point (pandas, pyarrow) raises.
  * Any other open() of a project data path, production backend file, session transcript, memory file,
    database or model file raises PermissionError (Python audit hook). Writes are allowed only inside
    this experiment folder (and the OS temp dir, for pytest's tmp_path).
  * sqlite3 and subprocess are blocked.
Every allowed data access is appended to ACCESS_LOG for the run manifest.
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Users\admin\aipheed").resolve()
AL = ROOT / "aipheed-backend-aligned"
EXP = Path(__file__).resolve().parents[1]
READ_ONLY_DIRS = [AL / "experiments" / "2026-10-12_E9_S1_safe_training"]
HOME_CLAUDE = Path.home().joinpath(".claude").resolve()
TEMP = Path(tempfile.gettempdir()).resolve()

# relative to AL -> (sha256, max quarter for the read-time row filter or None)
ALLOW: dict[str, tuple[str, str | None]] = {
    "data/processed/labels.parquet":
        ("eeb55983d8cf2de0c01e3654120c827a217bcbdb5221f4ebfe2108943ae32d1e", "2025-Q4"),
    "data/processed/psa_indicators.parquet":
        ("947be05fcab7d493edf585e59893e830d66eb52483bc43e951be94cbd3a9ff4c", "2025-Q4"),
    "data/processed/features_fused.parquet":
        ("0080dd5c3cafd82e68a6baa198c6d37894890e4fd9eeb44a72e34e3a2fda1292", "2025-Q4"),
    "data/supplementary/collection_2026-10-09/sws_balance_luzon_2025_raw.csv":
        ("1d7bd40ac52e6cf33a4b9c1a0a8598498bc0829a49f621c5e2bfb9d6e5789580", None),
    "evidence/2026-10-09_readiness/cpi_final_month_release_dates.csv":
        ("38ea731073b0897d28789a1d92a2651c60be7b19fe736b0d133237ad098a3de6", None),
    "evidence/2026-10-11_working_decisions/feature_eligibility_by_protocol.csv":
        ("1c8b9667ae0b1f8ba88f61dd3a15810bd8df82581235f757fbf09a8fa4c5657c", None),
    "config/governing_model.json":
        ("c9697b6b920cdf32986b422ea9c48533db72b7b1632dae221f4200dd2557dcc1", None),
}
DENY_NAME_PARTS = ("sws_hunger", "cpi_full", "corpus_", "fssi_quarterly", "trigger_proportions",
                   "topic_proportions", "zs_rescore", "panel", "final_predictions", "feature_provenance",
                   "mlflow", "mlruns", "lgbm_best", "optuna_study")
DATA_SUFFIXES = {".parquet", ".csv", ".json", ".db", ".sqlite", ".joblib", ".pkl", ".pickle", ".xlsx", ".jsonl"}

ACCESS_LOG: list[dict] = []
_INSTALLED = False
_BYPASS = False          # set only while hashing an allowlisted file


class AccessDenied(PermissionError):
    pass


def _resolve(path) -> Path | None:
    if isinstance(path, int):
        return None
    try:
        return Path(os.fsdecode(path)).resolve()
    except Exception:
        return None


def _under(p: Path, base: Path) -> bool:
    try:
        p.relative_to(base)
        return True
    except ValueError:
        return False


def _rel_al(p: Path) -> str | None:
    return p.relative_to(AL).as_posix() if _under(p, AL) else None


def decide(path, write: bool) -> str:
    """Return 'allow', 'deny' or 'neutral' for an open of `path`."""
    p = _resolve(path)
    if p is None:
        return "neutral"
    if _under(p, EXP):
        return "allow"
    if not write and any(_under(p, d) for d in READ_ONLY_DIRS):
        return "allow"
    if _under(p, HOME_CLAUDE):
        return "deny"                                   # transcripts, memory, task definitions
    if write:
        if _under(p, TEMP) and not _under(p, ROOT):
            return "allow"                              # pytest tmp_path
        return "deny" if _under(p, ROOT) else "neutral"
    name = p.name.lower()
    in_venv = _under(p, ROOT / "backend" / "venv")
    if not in_venv and p.suffix.lower() in DATA_SUFFIXES and any(s in name for s in DENY_NAME_PARTS):
        return "deny"                                   # protected/carrier names anywhere, incl. temp
    if _under(p, TEMP) and not _under(p, ROOT):
        return "neutral"
    if _under(p, ROOT):
        if _under(p, ROOT / "backend") and not _under(p, ROOT / "backend" / "venv"):
            return "deny"                               # production backend (its venv is the interpreter)
        rel = _rel_al(p)
        if rel is None:
            return "neutral" if _under(p, ROOT / "backend" / "venv") else "deny"
        if rel in ALLOW:
            return "allow"
        if p.suffix.lower() in {".py", ".pyc"}:
            return "allow"                              # project code imports
        return "deny"                                   # any other aligned-backend file
    return "neutral"


def _audit(event: str, args) -> None:
    if _BYPASS:
        return
    if event == "open":
        path, mode = args[0], args[1] if len(args) > 1 else "r"
        flags = args[2] if len(args) > 2 else 0
        write = bool(mode) and any(c in str(mode) for c in "wax+") or bool(
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
        d = decide(path, write)
        if d == "deny":
            raise AccessDenied(f"E11 guard: {'write' if write else 'read'} denied: {path}")
        p = _resolve(path)
        if d == "allow" and p is not None and _rel_al(p) in ALLOW and not write:
            ACCESS_LOG.append({"op": "open", "path": _rel_al(p)})
    elif event in ("sqlite3.connect", "subprocess.Popen", "os.system", "os.posix_spawn", "os.spawn"):
        raise AccessDenied(f"E11 guard: {event} is blocked")


def sha256(rel: str) -> str:
    global _BYPASS
    _BYPASS = True
    try:
        h = hashlib.sha256()
        with open(AL / rel, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()
    finally:
        _BYPASS = False


def verify_allowlist() -> dict:
    out = {}
    for rel, (want, _) in ALLOW.items():
        got = sha256(rel)
        if got != want:
            raise AccessDenied(f"E11 guard: hash mismatch for {rel}")
        out[rel] = got
    return out


def _blocked(name):
    def f(*a, **k):
        raise AccessDenied(f"E11 guard: {name} is blocked; use guard.read_allowed_parquet()")
    return f


_ORIG_DATASET = None


def read_filtered(path, columns: list[str], maxq: str | None):
    """Column-projected scan with the row filter quarter <= maxq applied during the scan
    (rows after it are never returned to Python)."""
    import pyarrow.dataset as ds
    dset = _ORIG_DATASET(str(path), format="parquet")
    flt = (ds.field("quarter") <= maxq) if maxq else None
    df = dset.to_table(columns=list(columns), filter=flt).to_pandas()
    if maxq and (df["quarter"] > maxq).any():          # defensive: the filter must have applied
        raise AccessDenied(f"E11 guard: row filter failed for {path}")
    return df


def read_allowed_parquet(rel: str, columns: list[str]):
    """Hash-verified, column-projected, row-filtered parquet read. Returns a pandas DataFrame."""
    if rel not in ALLOW or not rel.endswith(".parquet"):
        raise AccessDenied(f"E11 guard: {rel} is not an allowlisted parquet file")
    want, maxq = ALLOW[rel]
    if sha256(rel) != want:
        raise AccessDenied(f"E11 guard: hash mismatch for {rel}")
    if maxq and "quarter" not in columns:
        columns = list(columns) + ["quarter"]
    df = read_filtered(AL / rel, columns, maxq)
    ACCESS_LOG.append({"op": "read_parquet", "path": rel, "columns": sorted(columns), "row_filter": f"quarter <= {maxq}",
                       "rows_returned": int(len(df))})
    return df


def install() -> None:
    global _INSTALLED, _ORIG_DATASET
    if _INSTALLED:
        return
    import pandas as pd
    import pyarrow.parquet as pq
    import pyarrow.dataset as ds
    _ORIG_DATASET = ds.dataset
    pd.read_parquet = _blocked("pandas.read_parquet")
    pq.read_table = _blocked("pyarrow.parquet.read_table")
    pq.ParquetFile = _blocked("pyarrow.parquet.ParquetFile")
    pq.ParquetDataset = _blocked("pyarrow.parquet.ParquetDataset")
    pq.read_schema = _blocked("pyarrow.parquet.read_schema")
    pq.read_metadata = _blocked("pyarrow.parquet.read_metadata")
    ds.dataset = _blocked("pyarrow.dataset.dataset")
    sys.addaudithook(_audit)
    _INSTALLED = True
