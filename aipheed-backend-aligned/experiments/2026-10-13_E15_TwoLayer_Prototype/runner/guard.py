"""
E15 data-access guard (copy of the E13 guard; allowlist replaced). Import and call install() BEFORE importing pandas-based analysis code.

Policy:
  * Reads of data are allowed ONLY for four hash-pinned files (ALLOW), all eligible-only (2021-2025).
    No parquet file is read; every parquet entry point raises.
  * Files are read through read_allowed_text(), which verifies the SHA-256 first.
  * Any other open() of a project path, the production backend,
    ~/.claude (transcripts, memory, task definitions), a database or a model file raises.
  * Writes are allowed only inside this experiment folder (and the OS temp dir outside the project,
    for pytest's tmp_path). sqlite3 and subprocess are blocked.
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
E12_RUN = AL / "experiments" / "2026-10-12_E12_SWS_Scoring_Comparison" / "runs" / "20261012T151208Z"
HOME_CLAUDE = Path.home().joinpath(".claude").resolve()
TEMP = Path(tempfile.gettempdir()).resolve()

# absolute path -> (sha256, None). All four hold only 2021-2025 quarters (checked again at load time).
E13_RUN = AL / "experiments" / "2026-10-13_E13_DA_Predictive_Accuracy" / "runs" / "20261013T022702Z"
ALLOW: dict[Path, tuple[str, tuple[int, int] | None]] = {
    (E12_RUN / "realized_components_2021_2025.csv").resolve():
        ("6719baf75ad60dd47f94cfb269058354783414d7437b19a93101582432e67ce1", None),
    (E12_RUN / "details.json").resolve():
        ("ee022c35135d86fa9ec987d52212bd9c229037b835628ef03f2e4ec281a6865c", None),
    (E13_RUN / "metrics.json").resolve():
        ("4234d0604fe4aeb66c38c4215d7aac746ef19a0c6004571b12a6a91b78820ed4", None),
    (E13_RUN / "scored_rows.csv").resolve():
        ("94e16df47537437eb961b530e52a35ea206f133b4a8d9ccb848397e6e2364bc7", None),
}
DENY_NAME_PARTS = ("sws_hunger", "cpi_full", "corpus_", "fssi_quarterly", "trigger_proportions",
                   "topic_proportions", "zs_rescore", "panel", "final_predictions", "feature_provenance",
                   "mlflow", "mlruns", "lgbm_best", "optuna_study", "psa_indicators", "labels",
                   "features_fused", "2026h1", "2026_release")
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


def decide(path, write: bool) -> str:
    """Return 'allow', 'deny' or 'neutral' for an open of `path`."""
    p = _resolve(path)
    if p is None:
        return "neutral"
    if _under(p, EXP):
        return "allow"
    if _under(p, HOME_CLAUDE):
        return "deny"                                   # transcripts, memory, task definitions
    if write:
        if _under(p, TEMP) and not _under(p, ROOT):
            return "allow"                              # pytest tmp_path
        return "deny" if _under(p, ROOT) else "neutral"
    if p in ALLOW:
        return "allow"
    name = p.name.lower()
    in_venv = _under(p, ROOT / "backend" / "venv")
    if not in_venv and p.suffix.lower() in DATA_SUFFIXES and any(s in name for s in DENY_NAME_PARTS):
        return "deny"                                   # protected/carrier/mixed names anywhere, incl. temp
    if _under(p, TEMP) and not _under(p, ROOT):
        return "neutral"
    if _under(p, ROOT):
        if in_venv:
            return "neutral"                            # the interpreter and its libraries
        return "deny"                                   # every other project file, incl. production
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
            raise AccessDenied(f"E15 guard: {'write' if write else 'read'} denied: {path}")
        p = _resolve(path)
        if d == "allow" and p is not None and p in ALLOW and not write:
            ACCESS_LOG.append({"op": "open", "path": str(p)})
    elif event in ("sqlite3.connect", "subprocess.Popen", "os.system", "os.posix_spawn", "os.spawn"):
        raise AccessDenied(f"E15 guard: {event} is blocked")


def sha256_file(p: Path) -> str:
    global _BYPASS
    _BYPASS = True
    try:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()
    finally:
        _BYPASS = False


def verify_allowlist() -> dict:
    out = {}
    for p, (want, _) in ALLOW.items():
        got = sha256_file(p)
        if got != want:
            raise AccessDenied(f"E15 guard: hash mismatch for {p}")
        out[str(p)] = got
    return out


def _check(p: Path) -> tuple[str, tuple[int, int] | None]:
    p = p.resolve()
    if p not in ALLOW:
        raise AccessDenied(f"E15 guard: {p} is not allowlisted")
    want, yr = ALLOW[p]
    if sha256_file(p) != want:
        raise AccessDenied(f"E15 guard: hash mismatch for {p}")
    return want, yr


def read_allowed_text(p: Path) -> str:
    _check(p)
    with open(p, "r", encoding="utf-8") as f:
        txt = f.read()
    ACCESS_LOG.append({"op": "read_text", "path": str(p.resolve()), "bytes": len(txt.encode("utf-8"))})
    return txt


def _blocked(name):
    def f(*a, **k):
        raise AccessDenied(f"E15 guard: {name} is blocked; use guard.read_allowed_parquet()")
    return f


_ORIG_DATASET = None


def read_allowed_parquet(p: Path, columns: list[str]):
    """Hash-verified, column-projected parquet read with a read-time year filter."""
    import pyarrow.dataset as ds
    _, yr = _check(p)
    if yr and "year" not in columns:
        columns = list(columns) + ["year"]
    dset = _ORIG_DATASET(str(p), format="parquet")
    flt = ((ds.field("year") >= yr[0]) & (ds.field("year") <= yr[1])) if yr else None
    df = dset.to_table(columns=list(columns), filter=flt).to_pandas()
    if yr and ((df["year"] < yr[0]) | (df["year"] > yr[1])).any():
        raise AccessDenied(f"E15 guard: year filter failed for {p}")
    ACCESS_LOG.append({"op": "read_parquet", "path": str(p.resolve()), "columns": sorted(columns),
                       "row_filter": f"{yr[0]} <= year <= {yr[1]}" if yr else None, "rows_returned": int(len(df))})
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
