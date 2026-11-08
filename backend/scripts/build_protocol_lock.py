"""
Build docs/aipheed/PROTOCOL_LOCK.md: verbatim quotes of the frozen evaluation protocol (tolerance, eligible
observations, reliability criteria N1-N7, CPI cutoff rule, evaluation windows), each with its repository path, the
commit it was frozen at, and its line range. Every excerpt is read at that commit (git show) and must equal the
working-tree lines, so a later edit to a source is caught. Writes the lock file, its SHA-256, and a JSON manifest
that backend/tests/unit/test_protocol_lock.py re-checks.

    python -I backend/scripts/build_protocol_lock.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "aipheed"
EXP = "aipheed-backend-aligned/experiments"
# (id, title, path, frozen commit, first line, last line) -- 1-based, inclusive
SOURCES = [
    ("T1", "Target, sampling SE and the frozen primary tolerance", f"{EXP}/E131_Objectives_Resolution/E131_FROZEN_PROTOCOL.md", "88b270c", 20, 28),
    ("T2", "Primary criterion only (no secondary tolerance)", f"{EXP}/E131_Objectives_Resolution/E131_ADDENDUM_1_DA_OPERATIONAL_TOLERANCE.md", "c32e5bc", 29, 29),
    ("T3", "Tolerance in code", f"{EXP}/E130_Provincial_Risk_Score_Forecasting/runner/e130_lib.py", "f2c8d0f", 173, 180),
    ("T4", "Tolerance multiplier in code", f"{EXP}/E130_Provincial_Risk_Score_Forecasting/runner/e130_lib.py", "f2c8d0f", 30, 30),
    ("E1", "Leads, issue policies and eligible evaluation quarters", f"{EXP}/E131_Objectives_Resolution/E131_FROZEN_PROTOCOL.md", "88b270c", 30, 38),
    ("E2", "Primary evaluation set S-U (eligible rows: n_obs >= 8)", f"{EXP}/E133_Forecasting_Breakthrough/E133_FROZEN_PROTOCOL.md", "9683aad", 63, 64),
    ("R1", "Reliability rules N1-N7, reliable lead and maximum reliable lead", f"{EXP}/E130_Provincial_Risk_Score_Forecasting/E130_FROZEN_EXPERIMENT_PROTOCOL.md", "b58c48e", 164, 184),
    ("R2", "Reliability rules in code", f"{EXP}/E130_Provincial_Risk_Score_Forecasting/runner/e130_lib.py", "f2c8d0f", 257, 266),
    ("C1", "CPI cutoff rule (protocol)", f"{EXP}/E131_Objectives_Resolution/E131_FROZEN_PROTOCOL.md", "88b270c", 67, 67),
    ("C2", "CPI cutoff rule (code: availability and YoY base)", f"{EXP}/E131_Objectives_Resolution/runner/e131_x1.py", "c32e5bc", 158, 158),
    ("C3", "CPI YoY base rule (code)", f"{EXP}/E131_Objectives_Resolution/runner/e131_x1.py", "c32e5bc", 168, 168),
    ("C4", "CPI availability date (code)", f"{EXP}/E131_Objectives_Resolution/runner/e131_x1.py", "c32e5bc", 185, 185),
    ("W1", "Study window", f"{EXP}/E131_Objectives_Resolution/E131_FROZEN_PROTOCOL.md", "88b270c", 142, 142),
    ("W2", "Prospective adoption window", f"{EXP}/E134_Information_Bottleneck/E134_ADDENDUM_2_AMENDED_PRIMARY.md", "2d9a2d9", 21, 21),
    ("W3", "Dashboard target and issue rule (served code)", "backend/app/quarterly/target.py", "772b852", 46, 63),
]


def lines_at(commit: str, path: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"], capture_output=True, check=True)
    return out.stdout.decode("utf-8").splitlines()


def excerpt(src) -> str:
    sid, _, path, commit, a, b = src
    frozen = lines_at(commit, path)[a - 1:b]
    now = (REPO / path).read_text(encoding="utf-8").splitlines()[a - 1:b]
    if frozen != now:
        raise SystemExit(f"{sid}: {path} lines {a}-{b} differ from commit {commit}: the protocol source changed")
    return "\n".join(frozen)


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    manifest, parts = [], ["# AIPHEED protocol lock (read-only)\n",
                           "Verbatim quotes of the frozen evaluation protocol. Each block is read from the named file at "
                           "the named commit and equals the current working tree. Built by "
                           "`python -I backend/scripts/build_protocol_lock.py`; checked by "
                           "`backend/tests/unit/test_protocol_lock.py`. **Never edit by hand.** A change to any value "
                           "requires the owner's explicit approval and a new protocol.\n"]
    for src in SOURCES:
        sid, title, path, commit, a, b = src
        text = excerpt(src)
        manifest.append({"id": sid, "title": title, "path": path, "commit": commit, "lines": [a, b],
                         "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
        lang = "python" if path.endswith(".py") else "text"
        parts.append(f"## {sid} · {title}\n\n`{path}` lines {a}–{b} @ `{commit}`\n\n```{lang}\n{text}\n```\n")
    lock = DOCS / "PROTOCOL_LOCK.md"
    lock.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    (DOCS / "PROTOCOL_LOCK.sha256").write_text(f"{digest}  PROTOCOL_LOCK.md\n", encoding="utf-8", newline="\n")
    (DOCS / "protocol_lock_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
    print(digest)


if __name__ == "__main__":
    main()
