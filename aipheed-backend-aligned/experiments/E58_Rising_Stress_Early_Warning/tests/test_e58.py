"""E58 tests (PROTOCOL sections 2-5): event/target alignment, as-of (leakage) checks for the new warning inputs,
sealed-file integrity and reproducibility of the warning rules.

    backend/venv/Scripts/python.exe -B -m pytest -q aipheed-backend-aligned/experiments/E58_Rising_Stress_Early_Warning/tests
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

E58 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E58 / "runner"))
sys.path.insert(0, str(E58.parent / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402
import e58_event_counts as EC  # noqa: E402

F, L, np, pd = G.F, G.L, G.np, G.pd
SEALED = E58 / "sealed" / "predictions.csv"


@pytest.fixture(scope="module")
def d():
    return L.load()


def test_protocol_and_seal_hashes():
    want = (E58 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((E58 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want
    assert hashlib.sha256(SEALED.read_bytes()).hexdigest() == (SEALED.parent / "predictions.csv.sha256").read_text().split()[0]


def test_event_alignment(d):
    """Events refer to exactly two quarters after the predictor quarter; ONSET implies HIGH and a LOW latest label."""
    Ev = pd.read_csv(E58 / "data" / "events.csv", dtype={"province_code": str})
    Y = F.t43_labels(d).set_index(["province_code", "q"])
    for r in Ev.itertuples():
        assert r.target == L.qs(r.t + 2)
        assert int(Y.loc[(r.province_code, r.t + 2), "T43"]) == r.HIGH
        if r.ONSET:
            assert r.HIGH == 1 and r.last_known_T43 == 0
    ev = Ev[Ev["t"] >= L.qi("2023-Q4")]
    assert len(ev) == 50 and int(ev["ONSET"].sum()) == 10 and int(ev["HIGH"].sum()) == 18


def test_latest_known_label_is_as_of(d):
    """The latest known label used for ONSET/persistence was published before the issue date (SWS posting)."""
    r = pd.read_csv(L.SWS_FILE)
    r["q"], r["published"] = r["quarter"].map(L.qi), pd.to_datetime(r["published"])
    for t in range(L.qi("2023-Q4"), L.qi("2026-Q1") + 1):
        for p, (v, q) in F.t43_last(d, t).items():
            assert q is not None and q <= t - 1
            assert (r[r["q"] == q]["published"] < L.origin(t)).all()


def test_rise_label_uses_only_published_cpi(d):
    """RISEP / B-RECENT inputs: the latest complete CPI quarter at O(t) is t-1 (months through month 2 of t are known)."""
    for t in (L.qi("2024-Q1"), L.qi("2025-Q3")):
        c = d.cut(t)
        qs = set(L.quarter_F(c)["q"])
        assert t - 1 in qs and t not in qs


def test_sealed_e56_values_match_e57():
    S = pd.read_csv(SEALED, dtype={"province_code": str})
    S57 = pd.read_csv(E58.parent / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv", dtype={"province_code": str})
    m = S.merge(S57, on=["t", "province_code"], suffixes=("", "_57"))
    assert len(m) == 50 and np.max(np.abs(m["E56_p"] - m["E56_p_57"])) == 0.0


def test_warning_rules_reproducible():
    """Re-deriving the EW flags from the sealed probabilities reproduces the scored rows exactly."""
    runs = sorted((E58 / "runs").glob("2026*"))
    if not runs:
        pytest.skip("not scored yet")
    R = pd.read_csv(runs[0] / "rows.csv", dtype={"province_code": str})
    assert ((R["E56_p_price"] >= 0.5).astype(int) == R["EW_w"]).all()
    assert ((R["E56_p"] >= 0.5).astype(int) == R["C0_E56_w"]).all()
    assert (R["EW_w"] >= R["C0_E56_w"]).all()            # EW never drops an E56 alert (P_price >= P(HIGH))
