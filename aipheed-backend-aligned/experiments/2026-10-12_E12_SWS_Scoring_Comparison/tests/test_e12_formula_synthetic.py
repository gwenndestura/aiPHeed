"""E12 synthetic unit tests for the scoring formulas (protocol section 9; request section 5). No project data."""
import numpy as np
import pandas as pd
import pytest

import e12_lib as L

PROV = ["P1", "P2", "P3", "P4", "P5"]
H = 18.0                                  # common regional hunger value
F = [2.0, 5.5, 3.1, 8.4, 1.0]             # five different provincial food-inflation values


def fixture(missing: bool = False) -> pd.DataFrame:
    vals = list(F)
    if missing:
        vals[2] = np.nan
    f = pd.DataFrame({"province_code": PROV, "quarter": "2024-Q1", "F": vals})
    f = L.deviations(f)
    f["H"] = H
    return f


def test_1_deviations_sum_to_zero():
    f = fixture()
    assert abs(f["D"].sum()) < 1e-12
    assert f["mean5"].iloc[0] == pytest.approx(np.mean(F))


def test_2_alpha_does_not_change_rankings():
    f = fixture()
    base = L.within_quarter_ranks(f.assign(s=L.option_a(f["H"], f["D"], 0.0, 2.0)), "s")
    for a in L.ALPHAS:
        r = L.within_quarter_ranks(f.assign(s=L.option_a(f["H"], f["D"], a, 2.0)), "s")
        assert (r == base).all()


def test_3_alpha_does_not_change_spread():
    f = fixture()
    spreads = {a: float(L.within_quarter_spread(f.assign(s=L.option_a(f["H"], f["D"], a, 2.0)), "s").iloc[0]) for a in L.ALPHAS}
    assert max(spreads.values()) - min(spreads.values()) < 1e-12


def test_4_beta_scales_spread_preserves_ranking():
    f = fixture()
    sd = float(L.within_quarter_spread(f, "D").iloc[0])
    r0 = L.within_quarter_ranks(f.assign(s=f["D"]), "s")
    for b in L.BETAS:
        g = f.assign(s=L.option_a(f["H"], f["D"], 1.0, b))
        assert float(L.within_quarter_spread(g, "s").iloc[0]) == pytest.approx(b * sd)
        assert (L.within_quarter_ranks(g, "s") == r0).all()


def test_5_equal_ratios_equivalent_rankings_and_classifications():
    f = fixture()
    tau_s1 = 17.0                                       # any threshold for S1 = 1*H + 2*D
    s1 = L.option_a(f["H"], f["D"], 1.0, 2.0)
    for a, b in L.equivalence_groups()[L.ratio(1.0, 2.0)]:
        s = L.option_a(f["H"], f["D"], a, b)
        assert (L.within_quarter_ranks(f.assign(s=s), "s") == L.within_quarter_ranks(f.assign(s=s1), "s")).all()
        assert ((s > (b / 2.0) * tau_s1) == (s1 > tau_s1)).all()      # consistently transformed threshold
    assert len(L.equivalence_groups()[L.ratio(1.0, 2.0)]) == 5        # (0.25,.5) (.5,1) (.75,1.5) (1,2) (1.25,2.5)


def test_6_missing_not_replaced_with_zero():
    f = fixture(missing=True)
    s = L.option_a(f["H"], f["D"], 1.0, 2.0)
    assert s.isna().all()                               # no zero substitution anywhere in the quarter
    assert not (f["D"] == 0).any()


def test_7_mean_not_computed_when_a_province_is_missing():
    f = fixture(missing=True)
    assert f["mean5"].isna().all() and f["D"].isna().all()


def test_option_b_training_stats_zero_variance_and_equivalences():
    f = fixture()
    st = L.z_stats(pd.Series([10.0, 12.0, 14.0]), pd.Series([-1.0, 0.0, 1.0, 2.0, -2.0]))
    # wH = 0 -> rescaled D (same ranking as D); wH = 1 -> constant within the quarter
    s0 = L.option_b(f["H"], f["D"], 0.0, st)
    assert (L.within_quarter_ranks(f.assign(s=s0), "s") == L.within_quarter_ranks(f, "D")).all()
    s1 = L.option_b(f["H"], f["D"], 1.0, st)
    assert float(L.within_quarter_spread(f.assign(s=s1), "s").iloc[0]) == 0.0
    z = L.z_stats(pd.Series([10.0, 10.0]), pd.Series([1.0, -1.0]))
    assert z["zero_var_h"] and L.option_b(f["H"], f["D"], 0.5, z).notna().all()


def test_option_c_is_option_a_alpha_zero():
    f = fixture()
    assert np.allclose(L.option_a(f["H"], f["D"], 0.0, 1.0), f["D"])
