"""
Mutation-style spot check (v2 step 6): plant one bug at a time in the point-in-time selectors and the lead/target
alignment, run the tests that should guard it, and require them to FAIL. The source file is restored afterwards in a
finally block (verified by hash). A mutant that survives means the tests are vacuous for that bug.

    cd backend && python -I scripts/v2_mutation_check.py   -> docs/aipheed/v2/results/mutation_check.txt
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
OUT = BACKEND.parent / "docs" / "aipheed" / "v2" / "results" / "mutation_check.txt"
PY = sys.executable

MUTANTS = [
    ("as_of: strictly-before -> on-or-before", "app/forecasting/as_of.py",
     "return df[pub < issue_instant(issue)].copy()", "return df[pub <= issue_instant(issue) + pd.Timedelta(days=1)].copy()",
     ["tests/unit/test_v2_core.py", "tests/unit/test_forecasting_core.py"]),
    ("v2 lead/target: D-1+k -> D+k", "app/forecasting/v2/select.py",
     "fc = V.forecast(known, p, D - 1 + k, start)", "fc = V.forecast(known, p, D + k, start)",
     ["tests/unit/test_v2_core.py"]),
    ("v2 inner truth: known at I -> all rounds", "app/forecasting/v2/select.py",
     "return T.known_at(rr, cutoff)[[", "return T.quarter_table(rr)[[",
     ["tests/unit/test_v2_core.py"]),
    ("news asof: < O(t) -> <= O(t)", "app/news/pipeline_v3.py",
     'return [a for a in admitted() if a["quarter"] == q and _ph(a) < O]',
     'return [a for a in admitted() if a["quarter"] == q and _ph(a) <= O]',
     ["tests/unit/test_v2_legacy_leakage.py"]),
    ("FIRI prior: earlier origins -> including the origin", "app/ml/inference/thesis_system.py",
     "return {k: [x for q, x in v if qi(q) < t]", "return {k: [x for q, x in v if qi(q) <= t]",
     ["tests/unit/test_v2_legacy_leakage.py"]),
]


def main() -> None:
    lines = []
    for name, rel, old, new, tests in MUTANTS:
        f = BACKEND / rel
        original = f.read_bytes()
        h0 = hashlib.sha256(original).hexdigest()
        text = original.decode("utf-8")
        if old not in text:
            lines.append(f"ERROR  {name}: anchor text not found in {rel}")
            continue
        try:
            f.write_bytes(text.replace(old, new, 1).encode("utf-8"))
            r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", *tests], cwd=BACKEND,
                               capture_output=True, text=True)
            summary = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
            verdict = "KILLED" if r.returncode != 0 else "SURVIVED"
            lines.append(f"{verdict:8s} {name}: {summary}")
        finally:
            f.write_bytes(original)
            assert hashlib.sha256(f.read_bytes()).hexdigest() == h0, f"{rel} not restored"
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
