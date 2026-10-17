"""E47 tests: protocol frozen; publication cutoffs; energy window as of the issue date; no dependence on anything
published after the origin (I7-E, SL-5T, LGBM-C, thresholds included); gap margins; metric arithmetic."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E47 = HERE.parent
sys.path.insert(0, str(E47 / "runner"))
sys.path.insert(0, str(E47.parent / "E41_Lead2_Audit" / "tests"))
sys.path.insert(0, str(E47.parent / "E43_Five_Trigger_Risk" / "tests"))
import e47_lib as E  # noqa: E402
from test_e41 import perturb  # noqa: E402
from test_e43 import perturb_extra  # noqa: E402

L, K, M, P2, pd = E.L, E.K, E.M, E.P2, E.pd
T = L.qi("2025-Q1")


def test_protocol_frozen():
    want = (E47 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((E47 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_brent_file_matches_provenance_and_window():
    sha = hashlib.sha256(E.BRENT_FILE.read_bytes()).hexdigest()
    assert sha in (E47 / "data" / "PROVENANCE.md").read_text()
    s = E.load_brent()
    assert s.index.min() >= pd.Timestamp("2021-01-01") and s.index.max() <= pd.Timestamp("2026-09-30")


def test_energy_uses_only_the_window_ending_10_days_before_issue():
    s = E.load_brent()
    cut = L.origin(T) - pd.Timedelta(days=E.LAG_DAYS)
    late = s.copy()
    late[late.index >= cut] *= 3.0
    a, b = E.energy_features(T, s), E.energy_features(T, late)
    assert a == b and a["brent_window_end"] < str(L.origin(T).date())


def test_cutoff_audit_finds_every_input_published_before_issue():
    r = subprocess.run([sys.executable, "-B", str(E47 / "runner" / "e47_cutoff_audit.py"), "i7"], capture_output=True,
                       text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    a = json.loads((E47 / "runs" / "cutoff_audit_i7.json").read_text())
    assert a["all_origins_available"] and a["min_margin_days"]["cpi_provincial"] >= 14
    last = a["origins"][-1]
    assert last["target"] == "2027-Q1" and last["sources"]["cpi_provincial"]["latest_observation"] == "2026-08"


def test_gap_margins_are_consistent():
    d, x = L.load(), K.load_extra()
    o = list(range(L.qi("2021-Q3"), T + 1))
    D = E.margin_frame(E.features(d, x, o), P2.bases(d, o))
    th = L.e40_spec()
    r = D[(D["t"] == T)].iloc[0]
    assert r["mG1"] == pytest.approx((r["base_1.0"] - r["hl_1.0"]) - th["gap"][r["province_code"]])
    assert r["mF0"] == pytest.approx(r["base_0.0"] - th["food"][r["province_code"]])


@pytest.mark.parametrize("kind", ["SL-5T", "LGBM-C"])
def test_structural_models_and_thresholds_ignore_post_origin_data(kind):
    o = list(range(L.qi("2021-Q3"), T + 1))
    s = E.load_brent()
    late = s.copy()
    late[late.index >= L.origin(T) - pd.Timedelta(days=E.LAG_DAYS)] *= 2.0
    outs = []
    for d, x, b in ((L.load(), K.load_extra(), s), (perturb(L.load(), T), perturb_extra(K.load_extra(), T), late)):
        D = E.margin_frame(E.features(d, x, o, brent=b), P2.bases(d, o))
        g = E.forecast_sl(kind, D, d, T)
        outs.append((list(np.round(g["p"], 12)), g["threshold"]))
    assert outs[0] == outs[1]


def test_i7e_ignores_post_origin_data_and_has_energy_and_five_triggers():
    o = list(range(L.qi("2021-Q3"), T + 1))
    outs = []
    for d, x in ((L.load(), K.load_extra()), (perturb(L.load(), T), perturb_extra(K.load_extra(), T))):
        X = E.features(d, x, o)
        f = E.forecast_i7e(d, X, P2.bases(d, o), T, n_jobs=1)
        assert set(E.ENERGY) <= set(f["pcols"])
        assert {"market", "climate", "fish_kill", "employment", "ofw_remittance"} <= {
            g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in f["pcols"]}
        outs.append(list(np.round(f["p"], 12)))
    assert outs[0] == outs[1]


def test_confusion_and_rates_arithmetic():
    sys.path.insert(0, str(E47 / "runner"))
    import e47_evaluate as V
    S = pd.DataFrame({"y": [1, 1, 0, 0, 0], "A_yhat": [1, 0, 1, 0, 0]})
    r = V.prf(S, "A")
    assert r["confusion"] == {"TP": 1, "TN": 2, "FP": 1, "FN": 1}
    assert r["precision_HIGH"] == pytest.approx(0.5) and r["f1_HIGH"] == pytest.approx(0.5)
