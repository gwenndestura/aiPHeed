"""E47 A1 tests: addendum frozen; price-signal labels only from CPI published before the origin; PS models and their
thresholds ignore anything published after the origin; the decision is the product structure's AND rule."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E47 = HERE.parent
sys.path.insert(0, str(E47 / "runner"))
sys.path.insert(0, str(E47.parent / "E41_Lead2_Audit" / "tests"))
sys.path.insert(0, str(E47.parent / "E43_Five_Trigger_Risk" / "tests"))
import e47_a1 as A  # noqa: E402
from test_e41 import perturb  # noqa: E402
from test_e43 import perturb_extra  # noqa: E402

E, L, K, P2, pd = A.E, A.L, A.K, A.P2, A.pd
T = L.qi("2025-Q1")


def test_addendum_frozen():
    want = (E47 / "runner" / "ADDENDUM_A1_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((E47 / "ADDENDUM_A1.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_price_signal_labels_are_published_before_the_origin():
    d = L.load()
    lab = A.ps_labels(d, T)
    assert lab["q"].max() == T - 1                          # month 3 of t-1 is published before O(t)
    assert set(A.ps_labels(perturb(L.load(), T), T).itertuples(index=False)) == set(lab.itertuples(index=False))


def test_ps_models_ignore_post_origin_data():
    o = list(range(L.qi("2021-Q3"), T + 1))
    s = E.load_brent()
    late = s.copy()
    late[late.index >= L.origin(T) - pd.Timedelta(days=E.LAG_DAYS)] *= 2.0
    for kind in ("PS-P", "PS-5T"):
        outs = []
        for d, x, b in ((L.load(), K.load_extra(), s), (perturb(L.load(), T), perturb_extra(K.load_extra(), T), late)):
            D = E.margin_frame(E.features(d, x, o, brent=b), P2.bases(d, o))
            f = A.forecast_ps(kind, D, d, T)
            outs.append((list(np.round(f["p_ps"], 12)), f["tau"]))
        assert outs[0] == outs[1]
