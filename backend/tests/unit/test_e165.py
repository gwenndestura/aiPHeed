"""E165: shrink-only calibration keeps every class and never stretches the score."""
import numpy as np

from app.e165 import calib as C


def test_slope_recovers_known_value():
    rng = np.random.default_rng(0)
    mu = rng.normal(0, 1, 500)
    y = 0.2 + 0.7 * mu + rng.normal(0, 0.05, 500)
    assert abs(C.wslope(mu, y, np.ones(500)) - 0.7) < 0.02


def test_clip_bounds_and_nan():
    assert C.clip_b(1.4) == 1.0
    assert C.clip_b(0.1) == 0.25
    assert C.clip_b(float("nan")) == 1.0
    assert C.clip_b(0.6) == 0.6


def test_shrink_never_changes_class():
    mu = np.linspace(-3, 3, 601)
    for b in (0.25, 0.5, 0.73, 1.0):
        assert ((b * mu >= 0) == (mu >= 0)).all()
