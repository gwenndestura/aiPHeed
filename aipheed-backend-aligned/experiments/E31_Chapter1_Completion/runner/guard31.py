"""E31 data-access guard (writes confined to E31; E25-E29 are read-only). Call install() before any analysis or test code.

E31 change: the researcher authorized data released up to 2026-10-14 (H2-2026 is no longer protected). The production
data trees stay unreadable because they contain pre-2021 rows (study-window rule: never load such a file).

Reads
  * PROTECTED (raise): the production data trees (backend/data, aipheed-backend-aligned/data except data/reference),
    every database (*.db, *.sqlite), mlruns/, models/, the news corpus, `Claude outputs/`, and E26's contamination
    logs (they quote protected H2-2026 values). These are hash/metadata-only under the E8 v3 blind boundary.
  * Everything else is read normally: E27's own files, E25/E26 run outputs and seals (read-only), the frozen
    E25-exported pipeline inputs, and the validated acquisition tables.
Writes
  * Only inside E28 and the OS temp directory. E25, E26, E27, backend/, frontend/ and everything else raise.
"""
from __future__ import annotations

import builtins
import io
import os
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Users\admin\aipheed").resolve()
AL = ROOT / "aipheed-backend-aligned"
EXP = Path(__file__).resolve().parents[1]
E25 = AL / "experiments" / "E25_Reliable_Forecasts_2021_2026"
E26 = AL / "experiments" / "E26_Root_Cause_and_Data_Needs"
E27 = AL / "experiments" / "E27_Resolve_Forecasting_Failures"
E28 = AL / "experiments" / "E28_Objectives_1_4"
TEMP = Path(tempfile.gettempdir()).resolve()

PROTECTED_DIRS = [ROOT / "backend" / "data", AL / "data", AL / "mlruns", AL / "models", ROOT / "backend" / "models",
                  ROOT / "Claude outputs"]
ALLOWED_UNDER_PROTECTED = [AL / "data" / "reference"]
# E34 promoted E31's in-window runtime data into backend/data as NEW sub-folders (byte copies of backend_dev/data, see
# E34 runner/e34_promote_backend.py). Only those copies and the 142-LGU roster are readable; backend/data/processed,
# thesis, raw, archive, e20-e22 and reference/cph2020_* stay protected.
E34_PROMOTED = ["e25", "e27", "e28", "e29", "e31", "inputs", "inputs_vintage1_e29", "news_e28", "news_e31", "ledger",
                "quarterly_runs", "quarterly_store", "outcomes", "inbox"]
ALLOWED_UNDER_PROTECTED += [ROOT / "backend" / "data" / d for d in E34_PROMOTED]
ALLOWED_UNDER_PROTECTED += [ROOT / "backend" / "data" / f for f in ("cycle_log.jsonl", "evidence_status_derived.json",
                                                                     "reference/calabarzon_lgus.csv",
                                                                     "reference/SOURCE.txt")]
PROTECTED_FILES = [E26 / "docs" / "CONTAMINATION_LOG.md", E26 / "docs" / "CONTAMINATION_LOG_ADDENDUM.md"]
PROTECTED_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
_INSTALLED = False


class AccessDenied(PermissionError):
    pass


def _under(p: Path, d: Path) -> bool:
    try:
        p.relative_to(d.resolve())
        return True
    except ValueError:
        return False


def check(path, mode: str = "r") -> None:
    if isinstance(path, int):
        return
    p = Path(os.fspath(path)).resolve()
    writing = any(c in mode for c in "wax+")
    if writing:
        if not (_under(p, EXP) or _under(p, TEMP)):
            raise AccessDenied(f"E31 guard: write outside E31 refused: {p}")
        return
    if p.suffix.lower() in PROTECTED_SUFFIXES or p in [f.resolve() for f in PROTECTED_FILES]:
        raise AccessDenied(f"E31 guard: protected file: {p}")
    if any(_under(p, d) for d in PROTECTED_DIRS) and not any(_under(p, a) for a in ALLOWED_UNDER_PROTECTED):
        raise AccessDenied(f"E31 guard: protected location: {p}")
    # E31's own (and copied E28) re-collected, in-window news store lives under EXP and is allowed; any other corpus file is not.
    if "corpus" in p.name.lower() and p.suffix.lower() in (".parquet", ".csv", ".jsonl") and not _under(p, EXP):
        raise AccessDenied(f"E31 guard: news corpus file: {p}")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _open, _io_open = builtins.open, io.open

    def g_open(file, mode="r", *a, **k):
        check(file, mode)
        return _open(file, mode, *a, **k)

    def g_io_open(file, mode="r", *a, **k):
        check(file, mode)
        return _io_open(file, mode, *a, **k)

    builtins.open = g_open
    io.open = g_io_open
    _INSTALLED = True
