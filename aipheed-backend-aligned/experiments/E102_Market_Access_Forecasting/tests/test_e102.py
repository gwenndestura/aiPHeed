"""E102 tests (PROTOCOL.md section 8). Run from backend/:

    venv/Scripts/python.exe -m pytest -q -p no:cacheprovider ../aipheed-backend-aligned/experiments/E102_Market_Access_Forecasting/tests
"""
import copy
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e102_lib as L  # noqa: E402

CPI = L.load_cpi()
T = L.qi("2024-Q3")


def test_indicators_ignore_quarters_at_or_after_origin():
    base = {p: L.indicators_at(CPI, p, T) for p in L.PROVS}
    bad = copy.deepcopy(CPI)
    for d in bad.values():
        for k in list(d):
            if k[1] >= T:
                d[k] = d[k] * 3 + 50
    for p in L.PROVS:
        assert L.indicators_at(bad, p, T) == base[p]


def test_level_and_burden_are_zero_at_the_base():
    t = L.qi("2021-Q2")                                      # t - 1 = 2021-Q1, the base quarter
    for p in L.PROVS:
        v = L.indicators_at(CPI, p, t)
        assert abs(v["LVL"]) < 1e-12 and abs(v["REL"]) < 1e-12


def test_percentiles_use_strictly_earlier_origins():
    vals = {(t, p): float(t) for t in range(L.qi("2021-Q2"), L.qi("2024-Q1")) for p in L.PROVS}
    sc = L.percentiles(vals)
    # every value is above all earlier values -> score 1.0, never influenced by later origins
    assert all(abs(s - 1.0) < 1e-12 for s in sc.values())
    first = min(t for t, _ in sc)
    assert sum(1 for (t, _) in vals if t < first) * 1 >= 8


def test_training_pairs_contain_only_posted_outcomes():
    t = L.qi("2024-Q2")
    feats = {tp: {"x": 1.0} for tp in range(L.qi("2021-Q4"), L.qi("2026-Q3") + 1)}
    tr = L.training_pairs(feats, 2, t, ["x"])
    known = L.full_quarters_posted(L.TS.issue_of(t))
    assert len(tr) > 0
    assert all(L.qs(int(tp) + 2) in known for tp in tr["t"]) and (tr["t"] < t).all()


def test_served_firi_is_reproduced():
    H = L.R.load_history()
    arm, _ = L.R.build_arm(H, L.R.DOMS)
    diffs = [abs(arm[(r.target, r.province_code)] - float(r.FIRI)) for r in H.itertuples()
             if r.FIRI == r.FIRI and arm.get((r.target, r.province_code)) is not None]
    assert diffs and max(diffs) < 1e-6
