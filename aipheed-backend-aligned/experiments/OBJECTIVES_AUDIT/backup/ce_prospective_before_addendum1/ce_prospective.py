"""Shared pieces of the C-E prospective protocol (CE_PROSPECTIVE_PLAN.md): paths, hash checks, the CE ledger, the
authorization rule and the model registry. Imports prospective_lib (SENIOR_REVIEW, read only) for everything the C-b
protocol already defines, so both protocols use the same table, freshness, labels and ledger format.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]                   # OBJECTIVES_AUDIT
EXP = HERE.parent
ROOT = EXP.parents[1]
RUN = HERE / "runner"
PROS_CE = HERE / "prospective_ce"
LEDGER_CE = PROS_CE / "SEAL_LEDGER_CE.md"
REGISTRY_CE = PROS_CE / "REGISTRY_CE.json"
PLAN = HERE / "CE_PROSPECTIVE_PLAN.md"
SENIOR = EXP / "SENIOR_REVIEW"
sys.path.insert(0, str(SENIOR / "runner"))
sys.path.insert(0, str(RUN))
import prospective_lib as P  # noqa: E402

SEAL_LEADS = (1, 2, 3)
CE_MODELS = {"C-E2": "CE2_PREREGISTRATION.md", "C-E6": "CE6_PREREGISTRATION.md"}
CODE = ["ce_model.py", "ce2_model.py", "ce6_model.py", "ce_prospective.py", "seal_ce.py", "score_ce_prospective.py",
        "ce_registry.py"]
LEDGER_HEAD = ["# C-E prospective seal ledger (CE_PROSPECTIVE_PLAN.md)", "",
               "One row per sealed file; sealed files are never edited. C-b and the baselines are sealed separately in "
               "`SENIOR_REVIEW/prospective/SEAL_LEDGER.md`.", "",
               "| File | SHA-256 | Issue date | Targets | Sealed at | Code commit |", "|---|---|---|---|---|---|"]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hash_line(path: Path, key: str = "PLAN-SHA256") -> str:
    """Verify a pre-registration: SHA-256 of every byte before the last line equals the recorded value."""
    b = Path(path).read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(key.encode() + b": ") and last.split()[1].decode() == h, f"{Path(path).name} changed"
    return h


def check_plan() -> str:
    return hash_line(PLAN)


def code_hashes() -> dict:
    from importlib import import_module
    H = P.H
    out = {f"OBJECTIVES_AUDIT/runner/{f}": sha(RUN / f) for f in CODE if (RUN / f).exists()}
    for mod in ("hr_lib", "iv2_lib", "phase_c", "run_news_v2", "prospective_lib"):
        try:
            m = sys.modules.get(mod) or import_module(mod)
            out[str(Path(m.__file__).resolve().relative_to(EXP)).replace("\\", "/")] = sha(Path(m.__file__))
        except Exception:  # noqa: BLE001
            pass
    _ = H
    return dict(sorted(out.items()))


def ce_code_dirty() -> bool:
    paths = ["aipheed-backend-aligned/experiments/OBJECTIVES_AUDIT/runner",
             *[f"aipheed-backend-aligned/experiments/OBJECTIVES_AUDIT/{f}" for f in [*CE_MODELS.values(), PLAN.name]]]
    r = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=ROOT, capture_output=True, text=True)
    return bool(r.stdout.strip())


def authorized(issue: str) -> bool:
    """A real seal needs prospective_ce/AUTHORIZATION_<issue>.txt containing 'AUTHORIZED: seal_ce <issue>'."""
    f = PROS_CE / f"AUTHORIZATION_{issue}.txt"
    return f.exists() and f"AUTHORIZED: seal_ce {issue}" in f.read_text(encoding="utf-8")


def init_ledger(path: Path) -> None:
    assert not path.exists(), "the CE ledger already exists"
    lines = LEDGER_HEAD[:4] + [f"Protocol: `CE_PROSPECTIVE_PLAN.md`, SHA-256 `{check_plan()}`.", "",
                               "## Sealed files", ""] + LEDGER_HEAD[4:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_ledger(path: Path) -> list[dict]:
    return P.read_ledger(path)                           # same row format, same parser


def append_ledger(path: Path, row: dict) -> None:
    if not path.exists():
        init_ledger(path)
    P.append_ledger(path, row)


def dumps(x) -> str:
    return json.dumps(x, indent=1, default=str)
