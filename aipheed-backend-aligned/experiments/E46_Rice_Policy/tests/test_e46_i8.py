"""E46 I8 tests. e46_i8 re-points the e41_lib timing functions for the whole process, so every I8 check runs in its
own interpreter and never leaks the O'(t) convention into the other E41-E46 tests collected in this session."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parent / "runner"
PRELUDE = f"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, r"{RUNNER}")
sys.path.insert(0, r"{HERE.parents[1] / 'E41_Lead2_Audit' / 'tests'}")
sys.path.insert(0, r"{HERE.parents[1] / 'E43_Five_Trigger_Risk' / 'tests'}")
import e46_i8 as I8
M, L, K, P2, np, pd = I8.M, I8.L, I8.K, I8.P2, I8.np, I8.pd
"""


def run(body: str):
    r = subprocess.run([sys.executable, "-B", "-c", PRELUDE + textwrap.dedent(body)], capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, r.stderr[-3000:]


def test_addendum_frozen():
    want = (RUNNER / "ADDENDUM_I8_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "ADDENDUM_I8.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_issue_time_and_cuts():
    run("""
    t = L.qi("2024-Q4")
    assert L.origin(t) == pd.Timestamp("2025-01-15") and L.ym_s(L.m0_of(t)) == "2024-12"
    d = L.load(); c = d.cut(t)
    assert c.idx["ym"].max() == L.m0_of(t) and (c.sws["published"] < pd.Timestamp("2025-01-15")).all()
    assert (c.sws["published"] == pd.Timestamp("2025-01-14")).any()          # 2024-Q4 round posted on the 14th
    assert c.prod["q"].max() <= t - 1
    ev = M.load_events()
    assert M.policy_features(ev, L.qi("2024-Q1"))["tariff_yoy_regime"] == 0.0   # EO 62 announced 2024-06-20
    """)


def test_i8_ignores_post_issue_data_and_keeps_five_triggers():
    run("""
    from test_e41 import perturb
    from test_e43 import perturb_extra
    FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}
    ev = M.load_events()
    t = L.qi("2025-Q1")
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d, x in ((L.load(), K.load_extra()), (perturb(L.load(), t), perturb_extra(K.load_extra(), t))):
        X = M.features(d, x, o, ev)
        f = I8.forecast(d, X, P2.bases(d, o), t, n_jobs=1)
        assert f["threshold"] == 0.5 and set(M.POLICY) <= set(f["pcols"])
        assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in f["pcols"]}
        outs.append((list(np.round(f["p"], 12)), f["food_cfg"], f["gap_cfg"]))
    assert outs[0] == outs[1], outs
    """)
