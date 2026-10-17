"""D1 regression tests: the original E44 I2 / E46 I6 price signal compares a residual-corrected food projection with an
uncorrected headline projection, which inflates the implied food-headline gap; the I7 correction projects F and G
consistently. Reproduced on a synthetic case and on the committed runs (same data, rows and origins)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runner"))
import e46_gap_defect as G  # noqa: E402

P2, L = G.P2, G.L
CAVITE = "PH040100000"


def test_synthetic_case_original_formula_inflates_the_gap():
    th = L.e40_spec()
    base_F, base_HL, bias = 2.0, 2.5, 2.0               # both projections 2 points low; true F 4.0, true HL 4.5
    true_G = (base_F + bias) - (base_HL + bias)          # -0.5, below Cavite's gap threshold (0.74)
    assert true_G < th["gap"][CAVITE] and base_F + bias < th["food"][CAVITE]
    # original: the residual corrects food only, the headline stays at its base
    p_orig = P2.p_price(np.array([base_F + bias]), np.array([base_HL]), 1.5, [CAVITE])[0]
    # corrected: F and G each projected consistently (G's bias cancels)
    p_corr = P2.p_price_biv(np.array([base_F + bias]), np.array([base_F - base_HL]), 1.5, 1.0, 0.5, [CAVITE])[0]
    assert p_orig > 0.5 > p_corr


def test_defect_reproduced_and_corrected_on_committed_runs():
    P = G.frame()
    implied = float((P["G_implied_I6"] - P["G"]).mean())
    corrected = float((P["I7_G_hat"] - P["G"]).mean())
    uncorrected_bases = float((P["base_sel"] - P["hl_sel"] - P["G"]).mean())
    assert implied > 2.5                                 # +3.07 points
    assert abs(corrected) < 1.0 and abs(uncorrected_bases) < 1.0
    assert float(P["I6_p_price"].mean()) > 0.7 > 0.5 > float(P["I7_p_price"].mean())
