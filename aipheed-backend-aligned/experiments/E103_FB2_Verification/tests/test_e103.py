"""E103 statistics tests. Run from backend/:

    venv/Scripts/python.exe -m pytest -q -p no:cacheprovider ../aipheed-backend-aligned/experiments/E103_FB2_Verification/tests
"""
import itertools
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e103_run as E  # noqa: E402

np = E.np


def test_permutation_p_matches_brute_force():
    d = np.array([-0.05, 0.01, -0.02, -0.03, 0.04, -0.01])
    obs = abs(d.mean())
    hits = sum(abs(np.mean(np.array(s) * d)) >= obs - 1e-15 for s in itertools.product([-1, 1], repeat=len(d)))
    assert abs(E.permutation_p(d) - hits / 2 ** len(d)) < 1e-12


def test_sign_test_ignores_floating_point_ties():
    y = np.array([1.0, 0.0, 1.0, 1.0])
    a = np.array([0.6, 0.3, 0.7, 0.8])
    b = a + np.array([0.0, 1e-16, 0.1, 0.1])
    p = E.paired(y, a, b)
    assert p["ties"] == 2 and p["wins"] == 0 and p["losses"] == 2


def test_persistence_variant_reads_only_the_past():
    cpi = E.L.load_cpi()
    t = E.qi("2025-Q1")
    base = E.pers_variant(cpi, "PH040200000", t, 4.0, 4)
    for k in list(cpi["yoy"]):
        if k[1] >= t:
            cpi["yoy"][k] = 99.0
    assert E.pers_variant(cpi, "PH040200000", t, 4.0, 4) == base
