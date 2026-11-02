"""
Mutation spot check for v6: plant one bug at a time, run the guarding tests, require them to fail, restore (hash verified).
Uses the runner of v2_mutation_check.py with v6-specific mutants.

    cd backend && python -I scripts/v6_mutation_check.py   -> docs/aipheed/v6/results/mutation_check.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v2_mutation_check as M  # noqa: E402

CORE = ["tests/unit/test_v6_core.py"]
M.OUT = M.BACKEND.parent / "docs" / "aipheed" / "v6" / "results" / "mutation_check.txt"
M.MUTANTS = [
    ("as_of: strictly-before -> on-or-before + 1 day", "app/forecasting/as_of.py",
     "return df[pub < issue_instant(issue)].copy()", "return df[pub <= issue_instant(issue) + pd.Timedelta(days=1)].copy()", CORE),
    ("v6 history features use every round (hindsight)", "app/forecasting/v6/select.py",
     "k = T.known_at(rr, date.fromisoformat(issue))", "k = T.quarter_table(rr)", CORE),
    ("v6 selection: challenger always replaces", "app/forecasting/v6/select.py",
     "rep = bool(lo > 0)", "rep = True", CORE),
    ("snapshot guard disabled", "app/forecasting/v4/features.py",
     "if used_at is not None and str(used_at) != issue:", "if False:", ["tests/unit/test_v4_core.py"]),
    ("LightGBM minimum rows 30 -> 3", "app/forecasting/v6/lgbm.py", "MIN_ROWS = 30", "MIN_ROWS = 3", CORE),
    ("LightGBM leaves 4 -> 31 (library default)", "app/forecasting/v6/lgbm.py", '"num_leaves": 4', '"num_leaves": 31', CORE),
    ("v6 change not added to the anchor", "app/forecasting/v6/select.py", '"f": r.f + w * c', '"f": r.f', CORE),
]

if __name__ == "__main__":
    M.main()
