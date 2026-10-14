"""E32 finding fixed in the ledger code: persistence must use only labels published before the origin."""
import pandas as pd

import _paths  # noqa: F401
from app.quarterly.cycle import reference_probabilities

EXP = _paths.EXP


def test_persistence_ignores_a_label_posted_after_the_origin():
    inp = EXP / "backend_dev" / "data" / "inputs"
    S1 = pd.read_csv(inp / "s1_labels.csv", dtype={"province_code": str})
    rounds = pd.read_csv(inp / "sws_rounds.csv")
    # origin 2026-07-01, reference 2026-Q2: the June 2026 round was posted 2026-08-24, the March round 2026-05-12
    old = reference_probabilities(S1, 15.0, "2026-Q3", 1)                                   # pre-E32 behaviour
    new = reference_probabilities(S1, 15.0, "2026-Q3", 1, rounds=rounds, origin="2026-07-01")
    assert old["last_label_quarter"] == "2026-Q2"          # used a label nobody could have seen on 1 July
    assert new["last_label_quarter"] == "2026-Q1"
