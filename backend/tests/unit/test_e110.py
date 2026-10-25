"""Tests for E110 (SWS hunger forecasts across Balance Luzon and the 4-area panel; PROTOCOL.md section 7)."""
import json
import sys
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E110_Hunger_Generalization"
sys.path.insert(0, str(EXP / "runner"))
import e110_lib as F  # noqa: E402

E, H9, np, pd = F.E, F.H9, F.np, F.pd
OUT = EXP / "out"


def test_area_data_reproduce_the_e109_balance_luzon_series():
    a = pd.read_csv(F.AREA_FILE)
    r = H9.rounds()
    p = r[r["in_primary_series"]].reset_index(drop=True)
    assert len(a) == len(p) == 23
    assert (a["balance_luzon"].to_numpy() == p["H"].to_numpy()).all()
    assert (a["published"].to_numpy() == p["published"].str[:10].to_numpy()).all()
    for q in F.outcome_quarters("BL"):
        assert F.outcome(q, "BL") == pytest.approx(H9.outcome(q))


def test_all_four_areas_have_twenty_quarters_and_no_commissioned_round():
    assert all(len(F.outcome_quarters(ar)) == 20 for ar in F.AREAS)
    assert not pd.read_csv(F.AREA_FILE)["commissioned"].astype(str).eq("True").any()


def test_observation_variance_comes_from_the_published_margin():
    r = F.rounds()
    sep26 = r[(r["area"] == "BL") & (r["q"] == E.qi("2026-Q3"))]["R"].iloc[0]
    jun26 = r[(r["area"] == "BL") & (r["q"] == E.qi("2026-Q2"))]["R"].iloc[0]
    assert sep26 == pytest.approx((4 / 1.959964) ** 2) and jun26 == pytest.approx((6 / 1.959964) ** 2)
    s = dict((q, v) for q, _, v in F.known("2025-12-01", "BL"))
    assert s[E.qi("2025-Q2")] == pytest.approx(((4 / 1.959964) ** 2 + (6 / 1.959964) ** 2) / 2 / 2)


def test_vintages_use_publication_dates():
    k = {q: h for q, h, _ in F.known("2025-08-01", "BL")}
    assert k[E.qi("2025-Q2")] == 17.0                                   # June round published 2025-08-15
    assert E.qi("2026-Q3") not in {q for q, _, _ in F.known("2026-10-01", "MIN")}


def _perturb(monkeypatch, published: str, quarter: str, value: float):
    r0 = F.rounds()
    fake = r0[r0["q"] == E.qi("2024-Q4")].copy()
    fake["q"], fake["H"], fake["published"] = E.qi(quarter), value, published
    both = pd.concat([r0, fake], ignore_index=True)
    monkeypatch.setattr(F, "rounds", lambda: both)
    for f in (F.known, F.forecast, F.residual_pairs, F._pooled_q):
        f.cache_clear()


def _clear():
    for f in (F.known, F.forecast, F.residual_pairs, F._pooled_q):
        f.cache_clear()


def test_rounds_published_after_the_issue_change_no_forecast(monkeypatch):
    t = E.qi("2025-Q3")
    base = {(m, k, a): F.forecast(m, t, k, a)["forecast"] for k in (1, 2) for a in ("BL", "MIN")
            for m in F.PANEL_METHODS}
    base_bl = {(m, k): (F.forecast(m, t, k, "BL") or {}).get("forecast") for k in (1, 2) for m in ("LGBM-R", "RIDGE-R")}
    assert base_bl[("LGBM-R", 1)] is not None                               # eligible at Lead 1 (8 pairs)
    _perturb(monkeypatch, "2027-01-01", "2025-Q3", 80.0)
    try:
        for (m, k, a), v in base.items():
            assert F.forecast(m, t, k, a)["forecast"] == pytest.approx(v, abs=1e-12)
        for (m, k), v in base_bl.items():
            new = (F.forecast(m, t, k, "BL") or {}).get("forecast")
            assert (new is None) == (v is None) and (v is None or new == pytest.approx(v, abs=1e-12))
    finally:
        _clear()


def test_negative_control_round_published_before_issue_changes_forecasts(monkeypatch):
    t = E.qi("2025-Q3")
    llr = F.forecast("LLR", t, 1, "BL")["forecast"]
    _perturb(monkeypatch, "2025-09-15", "2025-Q3", 80.0)
    try:
        assert F.forecast("RW", t, 1, "BL")["forecast"] == 80.0
        assert F.forecast("LLR", t, 1, "BL")["forecast"] != llr
    finally:
        _clear()


def test_pooled_q_uses_only_known_data():
    issue = E.issue(E.qi("2024-Q2"))
    vals = []
    for ar in F.AREAS:
        s = F.known(issue, ar)
        assert all(q < E.qi("2024-Q2") + 1 for q, _, _ in s)
        vals += [((h1 - h0) ** 2 - r0 - r1) / (q1 - q0) for (q0, h0, r0), (q1, h1, r1) in zip(s, s[1:])]
    assert F._pooled_q(issue) == pytest.approx(max(np.mean(vals), F.Q_FLOOR))


@pytest.mark.parametrize("k", F.BL_LEADS)
def test_residual_pairs_targets_are_known_at_issue_and_precede_it(k):
    for t in range(E.qi("2024-Q1"), E.LAST_ORIGIN + 1, 3):
        tr = F.residual_pairs(t, k, ("BL",))
        if not len(tr):
            continue
        assert (tr["t"] < t).all() and (tr["q"] == tr["t"] + k).all() and t + k not in set(tr["q"])
        kn = {q for q, _, _ in F.known(E.issue(t), "BL")}
        assert set(tr["q"]) <= kn


def test_lgbm_r_uses_all_12_families():
    f = F.forecast("LGBM-R", E.qi("2025-Q4"), 1, "BL")
    assert list(f["gain"]) == E.COLUMNS and sorted({E.FAMILY_OF[c] for c in f["gain"]}) == E.EXPECTED_FAMILIES


needs_run = pytest.mark.skipif(not (OUT / "results.json").exists(), reason="run runner/run_e110.py score first")


@needs_run
@pytest.mark.parametrize("k", [1, 2, 4])
def test_stored_panel_predictions_reproduce(k):
    st = pd.read_csv(OUT / f"panel_lead{k}.csv")
    r = st.iloc[len(st) // 2]
    for m in F.PANEL_METHODS:
        assert F.forecast(m, int(r["t"]), k, r["area"])["forecast"] == pytest.approx(r[m], abs=1e-6)


@needs_run
def test_scored_under_frozen_protocol_with_clean_runner():
    r = json.loads((OUT / "results.json").read_text())
    assert r["run"]["protocol_sha256"] == (EXP / "runner/PROTOCOL_SHA256.txt").read_text().strip() == F.sha256(EXP / "PROTOCOL.md")
    assert not r["run"]["runner_dirty"]


@pytest.mark.skipif(not (OUT / "sealed_prospective.csv").exists(), reason="run prospective first")
def test_all_seals_unchanged():
    assert F.sha256(OUT / "sealed_prospective.csv") == (OUT / "sealed_prospective.csv.sha256").read_text().strip()
    want = {"E107_Twelve_Indicator_LightGBM": "246700a8d3c4fe76daf43adbfd5ea3c9d622dd124fb4d7137bde9f84a90c75fb",
            "E108_Best_Defensible_Forecasting": "fbc8bf911b1342e7f839cd4c27d35b037bbcd92953281067cffe7747650c325f",
            "E109_Hunger_Forecasting": "61bcc3535d802b58c540a42b958533f8e171bbc8e3ae67e183a1c319df141840"}
    for e, h in want.items():
        assert F.sha256(EXP.parent / e / "out/sealed_prospective.csv") == h


SERVE = E.BACKEND / "data" / "e110"


@pytest.mark.skipif(not (SERVE / "forecast.json").exists(), reason="run export first")
def test_api_serves_exported_files():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for route, name in (("evaluation", "evaluation_summary.json"), ("forecast", "forecast.json")):
        r = c.get(f"/api/v1/e110/{route}")
        assert r.status_code == 200 and r.json() == json.loads((SERVE / name).read_text(encoding="utf-8"))
