"""E35 shared setup: guard (writes confined to E35), E32 code reused read-only, and the preservation manifest.

E32 is imported, never modified: its runner directory is put on sys.path with bytecode writing disabled, and the
E32 data guard is re-pointed at E35 before it is installed, so every builtin open() outside E35 is read-only.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E35 = Path(__file__).resolve().parents[1]
EXPS = E35.parent
ROOT = EXPS.parents[1]
E32 = EXPS / "E32_New_Model"
E31 = EXPS / "E31_Chapter1_Completion"
for p in (E32 / "runner", E31 / "runner", E35 / "runner"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import guard32  # noqa: E402

guard32.EXP = E35                       # writes allowed only inside E35 (and the OS temp directory)
guard32.install()

import e32_common as C  # noqa: E402  (E32 data access; read-only)
import e32_lib as L  # noqa: E402  (E32 features, labels, candidates, references)
import e28_metrics as M  # noqa: E402  (E28/E32 metric definitions, unchanged)

np, pd, P = C.np, C.pd, C.P

# Files whose bytes must not change during E35: the E32 experiment (models, frozen prospective record, runs, code),
# the other frozen prospective records and seals, and the served PCF21 engine in both backends.
PRESERVE_DIRS = [
    E32,
    E31 / "frozen",
    EXPS / "E25_Reliable_Forecasts_2021_2026" / "runs" / "SEAL_E25_20261014T002548Z",
    EXPS / "2026-10-14_Prospective_Validation_Protocol",
    ROOT / "backend" / "app" / "quarterly",
    E31 / "backend_dev" / "app" / "quarterly",
]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def preserved_manifest() -> dict[str, str]:
    out = {}
    for d in PRESERVE_DIRS:
        for f in sorted(d.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                out[f.relative_to(ROOT).as_posix()] = sha(f)
    return out


def dataset_manifest() -> dict[str, str]:
    m = C.inputs_manifest()
    m["rice_cpi"] = sha(L.RICE)
    return m
