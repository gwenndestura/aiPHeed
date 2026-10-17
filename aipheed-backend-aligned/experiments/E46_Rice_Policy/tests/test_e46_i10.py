"""E46 I10 tests (own interpreter: e46_i10 imports e46_i8, which re-points the e41_lib timing functions)."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_e46_i8 import HERE, RUNNER, run  # noqa: E402


def test_addendum_frozen():
    want = (RUNNER / "ADDENDUM_I10_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "ADDENDUM_I10.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_i10_ignores_post_issue_data_and_considers_all_five_groups():
    run("""
    import e46_i10 as I10
    from test_e41 import perturb
    from test_e43 import perturb_extra
    FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}
    ev = M.load_events()
    t = L.qi("2025-Q1")
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d, x in ((L.load(), K.load_extra()), (perturb(L.load(), t), perturb_extra(K.load_extra(), t))):
        X = M.features(d, x, o, ev)
        f = I10.forecast(d, X, P2.bases(d, o), t, n_jobs=1)
        assert f["threshold"] == 0.5 and f["food_groups"][0] == "market" and f["gap_groups"][0] == "market"
        assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in f["pcols"]}
        assert set(f["food_path"][0]["groups"]) == {"market"} and len(f["food_path"]) >= 1
        outs.append((list(np.round(f["p"], 12)), f["food_groups"], f["gap_groups"], f["food_cfg"], f["gap_cfg"]))
    assert outs[0] == outs[1], outs
    """)
