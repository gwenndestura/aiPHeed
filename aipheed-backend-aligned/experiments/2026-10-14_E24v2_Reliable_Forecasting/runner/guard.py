"""E24v2 data-access guard (copied from E24, which copied E23). Adds read access to E24's own sealed outputs. Import and call install() BEFORE any pandas/pyarrow analysis code.

Allowlist = union of the E17 and E18 allowlists, IMPORTED PROGRAMMATICALLY from those experiments' guard
modules (no hash is typed here). E18's entries carry the user's 2026-10-13 authorization of the
January-June 2026 sources (E18/DATA_AUTHORIZATION_RECORD.md). Every read re-verifies the SHA-256 of the file.

Policy (unchanged from E17/E18):
  * Data reads only for allowlisted, hash-verified files; parquet only via read_allowed_parquet() with the
    file's read-time row filter; every other parquet entry point raises.
  * Any other open() of a project data file, ~/.claude, a database or a model file raises.
  * Writes only inside this experiment folder (and the OS temp dir outside the project, for pytest).
  * sqlite3 / subprocess are blocked.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Users\admin\aipheed").resolve()
AL = ROOT / "aipheed-backend-aligned"
EXP = Path(__file__).resolve().parents[1]
E17_GUARD = AL / "experiments" / "2026-10-13_E17_Objectives_Evaluation" / "runner" / "guard.py"
E18_GUARD = AL / "experiments" / "2026-10-13_E18_Objectives_Improvement" / "runner" / "guard.py"
E23_DIR = AL / "experiments" / "2026-10-13_E23_Chapter1_Complete"   # own prior outputs (no protected data); read-only
E24_DIR = AL / "experiments" / "2026-10-14_E24_Resolve_Forecasting"  # own prior outputs (no protected data); read-only
HOME_CLAUDE = Path.home().joinpath(".claude").resolve()
TEMP = Path(tempfile.gettempdir()).resolve()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # module-level code only defines constants/functions
    return mod


_g17 = _load("_e17_guard_pins", E17_GUARD)
_g18 = _load("_e18_guard_pins", E18_GUARD)
E12_RUN = _g18.E12_RUN
PROC, COLL, PROD_SWS = _g18.PROC, _g18.COLL, _g18.PROD_SWS

ALLOW: dict[Path, tuple[str, object]] = {}
PIN_SOURCE: dict[str, str] = {}
for src, mod in (("E17", _g17), ("E18", _g18)):
    for p, v in mod.ALLOW.items():
        p = Path(p).resolve()
        if p in ALLOW and ALLOW[p][0] != v[0]:
            raise RuntimeError(f"E24v2 guard: E17 and E18 pin different hashes for {p}")
        ALLOW[p] = v
        PIN_SOURCE[str(p)] = PIN_SOURCE.get(str(p), "") + ("+" if str(p) in PIN_SOURCE else "") + src
AUTHORIZED_2026 = {COLL / "provincial_food_cpi_yoy_2026H1_raw.csv", COLL / "cpi_2026_release_dates.csv", PROD_SWS}

DENY_NAME_PARTS = tuple(_g18.DENY_NAME_PARTS)
DATA_SUFFIXES = set(_g18.DATA_SUFFIXES)
ACCESS_LOG: list[dict] = []
REFERENCE_READS: list[str] = []
_INSTALLED = False
_BYPASS = False


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
    p = _resolve(path)
    if p is None:
        return "neutral"
    if _under(p, EXP):
        return "allow"
    if _under(p, HOME_CLAUDE):
        return "deny"
    if write:
        if _under(p, TEMP) and not _under(p, ROOT):
            return "allow"
        return "deny" if _under(p, ROOT) else "neutral"
    if p in ALLOW:
        return "allow"
    if _under(p, (AL / "data" / "reference").resolve()) and p.suffix.lower() == ".csv":
        REFERENCE_READS.append(str(p))                  # static PSGC / census reference lists (no 2026 data)
        return "allow"
    if _under(p, E23_DIR.resolve()) and "node_modules" not in p.parts and "dashboard_dev" not in p.parts:
        return "allow"                                  # E23 sealed predictions / results (hash-checked by callers)
    if _under(p, E24_DIR.resolve()) and "node_modules" not in p.parts and "dashboard_dev" not in p.parts:
        return "allow"                                  # E24 sealed predictions / results (hash-checked by callers)
    if p in (E17_GUARD.resolve(), E18_GUARD.resolve()):
        return "allow"
    name = p.name.lower()
    in_venv = _under(p, ROOT / "backend" / "venv")
    if not in_venv and p.suffix.lower() in DATA_SUFFIXES and any(s in name for s in DENY_NAME_PARTS):
        return "deny"
    if _under(p, TEMP) and not _under(p, ROOT):
        return "neutral"
    if _under(p, ROOT):
        if in_venv:
            return "neutral"
        # source code of the isolated backend's pure-Python modules (no data) may be imported
        if p.suffix.lower() == ".py" and _under(p, AL / "app"):
            return "neutral"
        return "deny"
    return "neutral"


def _audit(event: str, args) -> None:
    if _BYPASS:
        return
    if event == "open":
        path, mode = args[0], args[1] if len(args) > 1 else "r"
        flags = args[2] if len(args) > 2 else 0
        write = bool(mode) and any(c in str(mode) for c in "wax+") or bool(
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
        if decide(path, write) == "deny":
            raise AccessDenied(f"E24v2 guard: {'write' if write else 'read'} denied: {path}")
    elif event in ("sqlite3.connect", "subprocess.Popen", "os.system", "os.posix_spawn", "os.spawn"):
        raise AccessDenied(f"E24v2 guard: {event} is blocked")


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


def verify_allowlist() -> list[dict]:
    out = []
    for p, (want, flt) in sorted(ALLOW.items(), key=lambda kv: str(kv[0])):
        got = sha256_file(p)
        out.append({"path": str(p), "pinned_by": PIN_SOURCE[str(p)], "sha256_expected": want, "sha256_actual": got,
                    "match": got == want, "authorized_2026_source": p in {a.resolve() for a in AUTHORIZED_2026},
                    "read_time_filter": list(flt) if flt else None})
        if got != want:
            raise AccessDenied(f"E24v2 guard: hash mismatch for {p}")
    return out


def _check(p: Path):
    p = p.resolve()
    if p not in ALLOW:
        raise AccessDenied(f"E24v2 guard: {p} is not allowlisted")
    want, flt = ALLOW[p]
    if sha256_file(p) != want:
        raise AccessDenied(f"E24v2 guard: hash mismatch for {p}")
    return want, flt


def read_allowed_text(p: Path) -> str:
    _check(p)
    with open(p, "r", encoding="utf-8") as f:
        txt = f.read()
    ACCESS_LOG.append({"op": "read_text", "path": str(p.resolve()), "bytes": len(txt.encode("utf-8"))})
    return txt


_ORIG_DATASET = None


def _blocked(name):
    def f(*a, **k):
        raise AccessDenied(f"E24v2 guard: {name} is blocked; use guard.read_allowed_parquet()")
    return f


def read_allowed_parquet(p: Path, columns: list[str]):
    import pyarrow.dataset as ds
    _, flt = _check(p)
    if flt and flt[0] not in columns:
        columns = list(columns) + [flt[0]]
    dset = _ORIG_DATASET(str(p), format="parquet")
    expr = ((ds.field(flt[0]) >= flt[1]) & (ds.field(flt[0]) <= flt[2])) if flt else None
    df = dset.to_table(columns=list(columns), filter=expr).to_pandas()
    if flt and ((df[flt[0]] < flt[1]) | (df[flt[0]] > flt[2])).any():
        raise AccessDenied(f"E24v2 guard: filter failed for {p}")
    ACCESS_LOG.append({"op": "read_parquet", "path": str(p.resolve()), "columns": sorted(columns),
                       "row_filter": f"{flt[1]} <= {flt[0]} <= {flt[2]}" if flt else None, "rows_returned": int(len(df))})
    return df


def install() -> None:
    global _INSTALLED, _ORIG_DATASET
    if _INSTALLED:
        return
    import pandas as pd
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq
    _ORIG_DATASET = ds.dataset
    pd.read_parquet = _blocked("pandas.read_parquet")
    for n in ("read_table", "ParquetFile", "ParquetDataset", "read_schema", "read_metadata"):
        setattr(pq, n, _blocked(f"pyarrow.parquet.{n}"))
    ds.dataset = _blocked("pyarrow.dataset.dataset")
    sys.addaudithook(_audit)
    _INSTALLED = True
