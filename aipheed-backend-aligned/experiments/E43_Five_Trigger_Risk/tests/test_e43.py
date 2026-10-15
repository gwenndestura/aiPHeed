"""E43 validity tests (gate G0): study window, label definition and availability, five-trigger as-of features,
leakage of every arm, freeze."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runner"))
sys.path.insert(0, str(HERE.parents[1] / "E41_Lead2_Audit" / "tests"))
import e43_lib as K  # noqa: E402
from test_e41 import perturb  # noqa: E402

L = K.L
D, XR = L.load(), K.load_extra()


def perturb_extra(x: dict, t: int) -> dict:
    y = {k: v.copy() for k, v in x.items()}
    c = y["climate"]
    c.loc[c["q"] > t, ["tc_count", "tc_max_signal", "tc_severe_flag"]] += 5
    c.loc[c["q"] > t - 1, "enso_phase"] = "EL_NINO"
    y["ofw"].loc[y["ofw"]["q"] > t - 1, ["ofw_cash_remit_usd_bn", "fx_usd_php_avg"]] *= 3
    y["rice"].loc[y["rice"]["q"] > t - 1, "price_php_per_kg"] *= 3
    y["fssi"].loc[y["fssi"]["q"] > t, ["FSSI_v2", "n_admitted"]] = 99
    return y


def test_protocol_frozen():
    want = (HERE.parent / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((K.E43 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_pre2021_files_are_refused_before_loading():
    with pytest.raises(L.WindowViolation):
        K.assert_meta_in_window(K.PROC / "province_rainfall.parquet")
    assert all(v["q"].min() >= L.FIRST_Q for v in XR.values())


def test_t43_equals_e40_signals_without_sustain():
    lab = K.label_frame(D, "T43").set_index(["province_code", "q"])["y"]
    e40 = L.e40_labels(D).set_index(["province_code", "q"])
    assert (lab.loc[e40.index] == e40["both"]).all()
    # E40's sustain-2 label is T43 in q and q-1
    for (p, q), v in e40["y"].items():
        assert v == int(lab.get((p, q), 0) == 1 and lab.get((p, q - 1), 0) == 1)


def test_label_availability_follows_sws_posting():
    t = L.qi("2026-Q3")                                  # O = 2026-10-01; the Sept round was posted 2026-10-14
    a = set(K.available_labels(D, t)["q"])
    assert L.qi("2026-Q3") not in a and L.qi("2026-Q2") in a
    assert L.qi("2025-Q2") not in a and L.qi("2025-Q3") not in a          # no approved round: no label


@pytest.mark.parametrize("t", [L.qi("2023-Q2"), L.qi("2024-Q4"), L.qi("2026-Q1")])
def test_five_trigger_features_ignore_post_origin_data(t):
    o = list(range(L.qi("2021-Q3"), t + 1))
    a = K.features(D, XR, o)
    b = K.features(perturb(D, t), perturb_extra(XR, t), o)
    pd.testing.assert_frame_equal(a[a["t"] == t].reset_index(drop=True), b[b["t"] == t].reset_index(drop=True))


@pytest.mark.parametrize("t", [L.qi("2024-Q4"), L.qi("2026-Q1")])
def test_models_and_simulations_ignore_post_origin_data(t):
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d, x in ((D, XR), (perturb(D, t), perturb_extra(XR, t))):
        X = K.features(d, x, o)
        tr = K.training_pairs(X, d, t)
        assert tr["q"].max() <= t - 1
        te = X[X["t"] == t]
        r = [K.simulate(d.cut(t), t, n=2000), K.h_shift_5t(X, d, t)[0]]
        if K.eligible(tr):
            r += [list(cls(K.COMB).fit(tr).predict(te)) for cls in (K.LRModel, K.GBModel)]
        outs.append(r)
    assert outs[0] == outs[1]


def test_five_triggers_have_government_and_news_columns():
    for g in ("market", "climate", "fish_kill", "employment", "ofw_remittance"):
        assert K.GROUPS[g] and K.NEWS[g] in K.NLP
    assert "HL_now" not in K.COMB                                          # exact collinearity removed (E42)


def test_prospective_freeze_intact():
    fz = K.E43 / "frozen" / "E43_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        pytest.skip("not frozen yet")
    want = (fz.parent / "E43_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    assert hashlib.sha256(fz.read_bytes()).hexdigest() == want
    r = json.loads(fz.read_text())
    assert r["origin"] == "2026-10-01" and r["target_quarter"] == "2027-Q1" and r["cpi_months_used_through"] == "2026-08"
