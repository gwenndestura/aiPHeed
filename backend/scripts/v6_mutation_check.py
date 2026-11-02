"""
Mutation spot check for v6: apply one bug at a time IN THE TEST PROCESS ONLY (monkeypatched in a fresh subprocess), run the
guarding tests, and require them to fail. No source file is touched: an earlier version edited files on disk, which is
unsafe in a worktree shared with another session (docs/aipheed/v6/TEST_REPORT.md section 4).

    cd backend && python -I scripts/v6_mutation_check.py   -> docs/aipheed/v6/results/mutation_check.txt
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
OUT = BACKEND.parent / "docs" / "aipheed" / "v6" / "results" / "mutation_check.txt"
CORE = "tests/unit/test_v6_core.py"
LEAK = """
import pandas as pd
from app.forecasting import as_of as A, sws as T
_p = A._published
def leaky(df, issue, published_col='published', strict=True):
    return df[_p(df[published_col]) <= A.issue_instant(issue) + pd.Timedelta(days=1)].copy()
A.as_of = leaky; T.as_of = leaky
"""
HIND = """
from app.forecasting import sws as T
from app.forecasting.v6 import select as S
_h = S.history
def hind(rr, issue):
    k = T.quarter_table(rr); out = []
    for a, g in k.sort_values('qi').groupby('area'):
        y = g.y.to_numpy(); out.append({'area': a, 'last_change': float(y[-1] - y[-2]), 'dev_mean': float(y[-1] - y.mean())})
    return S.pd.DataFrame(out).assign(issue=issue)
S.history = hind
"""
RULE = """
from app.forecasting.v2 import select as S2
S2.paired_ci = lambda *a, **k: (1.0, 1.0)
"""
GUARD = """
from app.forecasting.v4 import features as F
_s = F.snapshot
F.snapshot = lambda t, issue, used_at=None: _s(t, issue, None)
"""
ROWS = "from app.forecasting.v6 import lgbm as L\nL.MIN_ROWS = 3\n"
LEAVES = "from app.forecasting.v6 import lgbm as L\nL.PARAMS['num_leaves'] = 31\n"
MUTANTS = [("as_of: strictly-before -> on-or-before + 1 day", LEAK, CORE),
           ("v6 history features use every round (hindsight)", HIND, CORE),
           ("v6 selection: challenger always replaces", RULE, CORE),
           ("snapshot guard disabled", GUARD, "tests/unit/test_v4_core.py"),
           ("LightGBM minimum rows 30 -> 3", ROWS, CORE),
           ("LightGBM leaves 4 -> 31 (library default)", LEAVES, CORE)]


def main() -> None:
    lines = []
    for name, patch, tests in MUTANTS:
        code = patch + f"\nimport pytest, sys\nsys.exit(pytest.main(['-q', '-x', '-p', 'no:cacheprovider', {tests!r}]))\n"
        r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
        summary = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        lines.append(f"{'KILLED' if r.returncode == 1 else 'SURVIVED' if r.returncode == 0 else 'ERROR':8s} {name}: {summary}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
