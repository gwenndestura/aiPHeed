"""Tests for E111 (audited SWS hunger forecasting; PROTOCOL.md section 7)."""
import json
import sys
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E111_Hunger_Forecast_Audit"
sys.path.insert(0, str(EXP / "runner"))
import e111_lib as G  # noqa: E402

E, F, H9, np, pd = G.E, G.F, G.H9, G.np, G.pd
OUT = EXP / "out"


def test_horizon_table_uses_only_rounds_published_before_issue():
    h = pd.read_csv(OUT / "horizon_table.csv")
    for r in h.dropna(subset=["newest_sws_published"]).itertuples():
        assert r.newest_sws_published < r.issue_date
        assert r.lead1_true_horizon_quarters == E.qi(r.lead1_target) - E.qi(r.newest_sws_quarter)
    assert (h["observation_age_quarters"].dropna() >= 1).all()


def _clear():
    for f in (F.known, F.forecast, F.residual_pairs, F._pooled_q, G.forecast, G._phi):
        f.cache_clear()


def test_future_rounds_change_no_e111_forecast(monkeypatch):
    t = E.qi("2025-Q3")
    base = {(m, k, a): G.forecast(m, t, k, a)["forecast"] for m in G.PANEL for k in (1, 2) for a in ("BL", "VIS")}
    r0 = F.rounds()
    fake = r0.copy()
    fake["H"], fake["published"] = fake["H"] + 40, "2027-06-01"
    monkeypatch.setattr(F, "rounds", lambda: pd.concat([r0, fake], ignore_index=True))
    _clear()
    try:
        for key, v in base.items():
            assert G.forecast(key[0], t, key[1], key[2])["forecast"] == pytest.approx(v, abs=1e-12)
    finally:
        _clear()


def test_negative_control_published_round_changes_dt_and_asym(monkeypatch):
    t = E.qi("2025-Q3")
    dt = G.forecast("DT", t, 1, "BL")["forecast"]
    r0 = F.rounds()
    extra = r0[(r0["area"] == "BL") & (r0["q"] == E.qi("2025-Q2"))].iloc[[0]].copy()
    extra["q"], extra["H"], extra["published"] = t, 60.0, "2025-09-20"
    monkeypatch.setattr(F, "rounds", lambda: pd.concat([r0, extra], ignore_index=True))
    _clear()
    try:
        assert G.forecast("ASYM", t, 1, "BL")["forecast"] >= 60.0
        assert G.forecast("DT", t, 1, "BL")["forecast"] != dt
    finally:
        _clear()


def test_phi_is_bounded_and_uses_known_targets():
    for t in (E.qi("2024-Q1"), E.qi("2025-Q4")):
        assert 0.0 <= G._phi(t, 1) <= 1.0


def test_brk_restarts_only_after_the_2025_change():
    assert G.forecast("BRK", E.qi("2026-Q1"), 1, "BL")["restarted"] is True
    assert G.forecast("BRK", E.qi("2024-Q2"), 1, "BL")["restarted"] is False


@pytest.mark.parametrize("t", [E.qi("2024-Q3"), E.qi("2025-Q4"), E.qi("2026-Q2")])
def test_asym_never_below_latest_reading(t):
    for a in F.AREAS:
        f = G.forecast("ASYM", t, 1, a)
        assert f["forecast"] >= f["h_last"] - 1e-12


def test_family_screen_uses_only_that_familys_columns():
    cols = {f: [c for c in E.COLUMNS if E.FAMILY_OF[c] == f] for f in E.FAMILIES}
    assert sum(len(v) for v in cols.values()) == 13 and len(cols) == 12 and cols["A1"] == ["A1_food", "A1_gap"]


needs_run = pytest.mark.skipif(not (OUT / "results.json").exists(), reason="run runner/run_e111.py score first")


@needs_run
@pytest.mark.parametrize("k", [1, 2])
def test_stored_predictions_reproduce(k):
    st = pd.read_csv(OUT / f"panel_lead{k}.csv")
    r = st.iloc[len(st) // 2]
    for m in G.PANEL:
        assert G.forecast(m, int(r["t"]), k, r["area"])["forecast"] == pytest.approx(r[m], abs=1e-6)


@needs_run
def test_scored_under_frozen_protocol_with_clean_runner():
    r = json.loads((OUT / "results.json").read_text())
    assert r["run"]["protocol_sha256"] == (EXP / "runner/PROTOCOL_SHA256.txt").read_text().strip() == G.sha256(EXP / "PROTOCOL.md")
    assert not r["run"]["runner_dirty"]


@pytest.mark.skipif(not (OUT / "sealed_prospective.csv").exists(), reason="run prospective first")
def test_seals_unchanged():
    assert G.sha256(OUT / "sealed_prospective.csv") == (OUT / "sealed_prospective.csv.sha256").read_text().strip()
    want = {"E107_Twelve_Indicator_LightGBM": "246700a8d3c4fe76daf43adbfd5ea3c9d622dd124fb4d7137bde9f84a90c75fb",
            "E108_Best_Defensible_Forecasting": "fbc8bf911b1342e7f839cd4c27d35b037bbcd92953281067cffe7747650c325f",
            "E109_Hunger_Forecasting": "61bcc3535d802b58c540a42b958533f8e171bbc8e3ae67e183a1c319df141840",
            "E110_Hunger_Generalization": "81f0b237ad0c98c3e65cc9371338817cbfa0e81ccd002b0539639ea2be751ee5"}
    for e, h in want.items():
        assert G.sha256(EXP.parent / e / "out/sealed_prospective.csv") == h


SERVE = E.BACKEND / "data" / "e111"


@pytest.mark.skipif(not (SERVE / "forecast.json").exists(), reason="run export first")
def test_api_serves_exported_files():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for route, name in (("evaluation", "evaluation_summary.json"), ("forecast", "forecast.json")):
        r = c.get(f"/api/v1/e111/{route}")
        assert r.status_code == 200 and r.json() == json.loads((SERVE / name).read_text(encoding="utf-8"))
