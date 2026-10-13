"""Unit tests of the E23 statistics (synthetic numbers only; never mixed into study data)."""
import itertools, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e23_lib as L


def brute_auc_perm(g, y, a, b):
    ug = np.unique(g); obs = L.auc(y, a) - L.auc(y, b); ge = 0; tot = 0
    for bits in itertools.product([0, 1], repeat=len(ug)):
        aa, bb = a.copy(), b.copy()
        for j, f in enumerate(bits):
            if f:
                m = g == ug[j]; aa[m], bb[m] = b[m], a[m]
        ge += (L.auc(y, aa) - L.auc(y, bb)) >= obs - 1e-12; tot += 1
    return ge / tot


def test_auc_matches_sklearn():
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(1); y = rng.integers(0, 2, 40); s = rng.random(40)
    assert abs(L.auc(y, s) - roc_auc_score(y, s)) < 1e-12
    s[:10] = 0.5
    assert abs(L.auc(y, s) - roc_auc_score(y, s)) < 1e-12


def test_vectorised_auc_perm_equals_bruteforce():
    rng = np.random.default_rng(2)
    g = np.repeat(np.arange(6), 5); y = rng.integers(0, 2, 30); a = rng.random(30); b = (rng.random(30) > .5).astype(float)
    assert abs(L.paired_auc_perm(g, y, a, b)["p_one_sided"] - brute_auc_perm(g, y, a, b)) < 1e-12


def test_signflip_exact_and_extremes():
    r = L.signflip_brier(np.array([-1.0] * 6))
    assert r["exact"] and abs(r["p_one_sided"] - 1 / 64) < 1e-12
    assert L.signflip_brier(np.array([1.0] * 6))["p_one_sided"] == 1.0


def test_holm():
    out = L.holm({"a": 0.01, "b": 0.02, "c": 0.04, "d": None})
    assert abs(out["a"] - 0.03) < 1e-12 and abs(out["b"] - 0.04) < 1e-12 and abs(out["c"] - 0.04) < 1e-12 and out["d"] is None


def test_cls_metrics_counts():
    m = L.cls_metrics([1, 1, 0, 0], [0.9, 0.2, 0.6, 0.1])
    assert (m["TP"], m["FN"], m["FP"], m["TN"]) == (1, 1, 1, 1) and m["accuracy"] == 0.5 and m["ROC_AUC"] == 0.75


def test_grid_is_predeclared_size():
    assert len(L.GRID) == 16 and len({tuple(sorted(c.items())) for c in L.GRID}) == 16
