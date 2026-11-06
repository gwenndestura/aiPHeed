"""E166 pure rules: drift formula with hand-computed numbers and units, cap, one-round case, and top-5 ranking with ties."""
import numpy as np
import pandas as pd

from app.e166 import drift as Dm
from app.fi5.target import qindex


class _Hp:
    """Stand-in for Hier2 with N, slope and last_q computed exactly as app.e150.model.Hier.fit does."""

    def __init__(self, levels):                      # {quarter label: national level, logit}
        self.N = {q: v for q, v in levels.items()}
        qs = np.array([qindex(q) for q in levels], float)
        ns = np.array(list(levels.values()), float)
        self.slope = float(np.polyfit(qs, ns, 1)[0]) if len(qs) > 1 else 0.0
        self.last_q = int(qs.max())


class _Cache:
    def __init__(self, hp):
        self.hp = hp

    def get(self, i):
        return self.hp, None, None


def _D(levels, target):
    d = pd.DataFrame({"i": [qindex("2018-Q2")], "T": [qindex(target)]})
    return Dm.drift_rows(_Cache(_Hp(levels)), d).iloc[0]


def test_quarter_index_units():
    assert qindex("2015-Q3") - qindex("2013-Q3") == 8          # 8 quarters between rounds
    assert qindex("2018-Q3") - qindex("2015-Q3") == 12         # 12 quarters from last round to target


def test_drift_hand_computed_two_rounds():
    # slope = (-0.46 - -0.30) / 8 = -0.02 per quarter; gap 12; D = 0.5 * -0.02 * 12 = -0.12
    r = _D({"2013-Q3": -0.30, "2015-Q3": -0.46}, "2018-Q3")
    assert abs(r["r"] - (-0.02)) < 1e-12
    assert r["gap"] == 12
    assert abs(r["D"] - (-0.12)) < 1e-12


def test_drift_clipped_at_minus_half():
    # slope = (-1.10 - -0.30) / 8 = -0.10; 0.5 * -0.10 * 12 = -0.60 -> -0.5
    assert _D({"2013-Q3": -0.30, "2015-Q3": -1.10}, "2018-Q3")["D"] == -0.5


def test_drift_clipped_at_plus_half():
    # slope = (0.50 - -0.30) / 8 = 0.10; 0.5 * 0.10 * 12 = 0.60 -> +0.5
    assert _D({"2013-Q3": -0.30, "2015-Q3": 0.50}, "2018-Q3")["D"] == 0.5


def test_one_released_round_gives_zero_drift():
    r = _D({"2013-Q3": -0.30}, "2016-Q4")
    assert r["D"] == 0.0 and r["r"] == 0.0 and r["n_rounds"] == 1


def test_drift_value_formula():
    assert abs(Dm.drift_value(-0.02, 100, 110) - 0.5 * -0.02 * 10) < 1e-12
    assert Dm.drift_value(0.0, 100, 130) == 0.0


def test_top5_lowest_scores_ties_to_earlier_menu_position():
    assert Dm.rank_top([5.0, 1.0, 3.0, 1.0, 2.0, 3.0, 0.5]) == [6, 1, 3, 4, 2]


def test_fewer_than_five_configs_uses_all():
    assert Dm.rank_top([2.0, 1.0, 3.0]) == [1, 0, 2]
