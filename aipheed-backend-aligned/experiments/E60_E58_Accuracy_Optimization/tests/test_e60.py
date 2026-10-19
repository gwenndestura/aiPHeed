"""E60 tests: frozen-file integrity (protocol, classifier v2, annotations, sealed candidates), news-feature timing (no article
published on or after the issue date can change a feature), target alignment, and reproducibility of a sealed candidate.

    backend/venv/Scripts/python.exe -B -m pytest -q aipheed-backend-aligned/experiments/E60_E58_Accuracy_Optimization/tests
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

E60 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E60.parents[2] / "backend"))
sys.path.insert(0, str(E60 / "runner"))
import n5_features as N  # noqa: E402

L, np, pd = N.L, N.np, N.pd


def _lf_sha(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_frozen_files():
    assert _lf_sha(E60 / "MODEL_SELECTION_AND_VALIDATION_PROTOCOL.md") == (E60 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert _lf_sha(E60 / "runner" / "n4_classifier.py") == (E60 / "runner" / "CLASSIFIER_V2_SHA256.txt").read_text().split()[0]
    s = E60 / "sealed" / "candidates.csv"
    assert hashlib.sha256(s.read_bytes()).hexdigest() == (s.parent / "candidates.csv.sha256").read_text().split()[0]


@pytest.fixture(scope="module")
def corpus():
    return N.corpus()


def test_news_features_use_only_articles_published_before_issue(corpus):
    full = N.features(corpus)
    for t in (L.qi("2023-Q4"), L.qi("2025-Q2"), L.qi("2026-Q1")):
        O = L.origin(t).tz_localize("Asia/Manila")
        trunc = corpus[pd.to_datetime(corpus["published_ph"], utc=True) < O]
        part = N.features(trunc)
        a = full[full["t"] == t].set_index("province_code")[N.NEWS_COLS]
        b = part[part["t"] == t].set_index("province_code")[N.NEWS_COLS]
        assert np.allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True), L.qs(t)


def test_feature_window_is_quarter_t_only(corpus):
    """Perturbing every article published in quarter t+1 (after the issue date) leaves origin-t features unchanged."""
    t = L.qi("2024-Q4")
    full = N.features(corpus)
    c2 = corpus.copy()
    c2.loc[c2["q"] == t + 1, "trigger"] = "market"
    c2.loc[c2["q"] == t + 1, "relevant"] = 1
    pert = N.features(c2)
    a = full[full["t"] == t][N.NEWS_COLS].to_numpy(float)
    b = pert[pert["t"] == t][N.NEWS_COLS].to_numpy(float)
    assert np.allclose(a, b, equal_nan=True)


def test_history_features_as_of():
    d = L.load()
    h = N.history(d)
    Y = N.F.t43_labels(d)
    ps = {(p, int(q)): int(v) for p, q, v in zip(Y["province_code"], Y["q"], Y["PS"])}
    r = h[h["t"] == L.qi("2025-Q1")].set_index("province_code")
    for p in L.PROVS:
        assert r.loc[p, "hist_ps_last"] == ps[(p, L.qi("2024-Q4"))]        # quarter t-1 only


def test_candidate_A_reproduces_sealed():
    sys.path.insert(0, str(E60.parent / "E56_LightGBM_Optimization" / "runner"))
    import c1_candidates as C
    d, X0, B = C.E.load()
    X = X0.merge(pd.read_csv(E60 / "data" / "news_features.csv", dtype={"province_code": str}), on=["t", "province_code"], how="left")
    t = L.qi("2024-Q3")
    fx = C.tuned(d, X, B, t, C.G.search_space(), C.colfn("A"))
    S = pd.read_csv(E60 / "sealed" / "candidates.csv", dtype={"province_code": str})
    s = S[S["t"] == t].set_index("province_code")["A_p"]
    assert np.max(np.abs(np.array([s[p] for p in L.PROVS]) - fx["p"])) < 1e-9
