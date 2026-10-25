"""Tests for E109 (forecasting SWS Balance Luzon experienced hunger; PROTOCOL.md section 10)."""
import json
import sys
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E109_Hunger_Forecasting"
sys.path.insert(0, str(EXP / "runner"))
import e109_lib as H  # noqa: E402

E, np, pd = H.E, H.np, H.pd
OUT = EXP / "out"


# ------------------------------------------------------------------------------------------------ outcome
def test_outcome_rounds_match_the_project_sws_file_and_the_commission_rule():
    r = H.rounds()
    sws = pd.read_csv(E.BACKEND / "data/inputs/sws_rounds.csv")
    assert len(r) == len(sws) == 24 and (r["H"].to_numpy() == sws["H"].to_numpy()).all()
    assert (r["in_primary_series"] == ~r["commissioned"]).all()
    assert r.loc[r["commissioned"], "round"].str.contains("Stratbase").all() and r["commissioned"].sum() == 1


def test_primary_quarter_values_are_round_means_and_cover_20_quarters():
    qs_ = H.outcome_quarters()
    assert len(qs_) == 20 and E.qi("2025-Q1") not in qs_ and E.qi("2022-Q1") not in qs_
    assert H.outcome(E.qi("2025-Q2")) == pytest.approx((17.0 + 15.3) / 2)
    assert H.outcome(E.qi("2026-Q3")) == 23.6
    assert H.outcome(E.qi("2025-Q1"), "ALL") == 24.0 and H.outcome(E.qi("2025-Q1")) is None


def test_known_at_issue_uses_publication_dates():
    k = dict(H.known("2026-10-01"))
    assert E.qi("2026-Q2") in k and E.qi("2026-Q3") not in k            # 2026-Q3 posted 2026-10-14
    # ADDENDUM_1 real-time vintage: on 2025-08-01 only the April round (17.0) of 2025-Q2 was public
    assert dict(H.known("2025-08-01"))[E.qi("2025-Q2")] == 17.0
    assert dict(H.known("2025-08-16"))[E.qi("2025-Q2")] == pytest.approx((17.0 + 15.3) / 2)
    assert E.qi("2025-Q2") not in dict(H.known("2025-06-27"))            # published 2025-06-27, not before it


@pytest.mark.parametrize("k", H.LEADS)
def test_training_pairs_never_use_an_outcome_unknown_at_the_issue(k):
    for t in range(E.qi("2023-Q1"), E.LAST_ORIGIN + 1):
        tr = H.pairs(t, k)
        if not len(tr):
            continue
        kn = dict(H.known(E.issue(t)))
        assert (tr["t"] < t).all() and (tr["q"] == tr["t"] + k).all()
        assert all(q in kn for q in tr["q"]) and t + k not in set(tr["q"])
        assert all(y == kn[q] for q, y in zip(tr["q"], tr["y"]))       # targets are the vintage known at O(t)
        for tp, hl in zip(tr["t"], tr["h_last"]):
            assert hl == H.h_last(int(tp))[1]


def test_future_sws_rounds_do_not_change_any_forecast(monkeypatch):
    """A fake round published after the issue (for every quarter) changes none of the methods' forecasts or sigmas."""
    t, base = E.qi("2025-Q3"), {}
    for k in (1, 2):
        for m in H.METHODS:
            base[(m, k)] = (H.forecast(m, t, k)["forecast"], H.sigma(m, t, k))
    r0 = H.rounds()
    fake = r0.copy()
    fake["H"] = fake["H"] + 30.0
    fake["published"] = "2027-12-31"
    fake["round"] = fake["round"] + " (fake)"
    both = pd.concat([r0, fake], ignore_index=True)
    monkeypatch.setattr(H, "rounds", lambda: both)
    H.known.cache_clear()
    H.forecast.cache_clear()
    try:
        for (m, k), (f, s) in base.items():
            assert H.forecast(m, t, k)["forecast"] == pytest.approx(f, abs=1e-12)
            assert H.sigma(m, t, k) == pytest.approx(s, abs=1e-12)
    finally:
        H.known.cache_clear()
        H.forecast.cache_clear()


def test_local_level_parameters_use_only_known_quarters():
    t = E.qi("2024-Q2")
    a, P, Q = H.local_level(H.known(E.issue(t)))
    a2, _, _ = H.local_level(H.known(E.issue(t)) + ((E.qi("2030-Q1"), 99.0),))
    assert a != a2                                           # the filter does respond to data
    assert H.forecast("LL", t, 1)["forecast"] == pytest.approx(a)


# ------------------------------------------------------------------------------------------------ thresholds, families
def test_thresholds_are_the_protocol_values():
    assert H.THRESHOLDS == {"B1": 11.3, "B2": 15.0, "B3": 20.0} and H.RISE == 4.0 and H.MOE_BL == 4.0
    assert H.p_above(11.3, 11.3, 2.0) == pytest.approx(0.5)


def test_lightgbm_uses_the_13_columns_of_all_12_families():
    t = E.qi("2025-Q4")
    f = H.forecast("LGBM", t, 1)
    assert list(f["gain"]) == E.COLUMNS and sorted({E.FAMILY_OF[c] for c in f["gain"]}) == E.EXPECTED_FAMILIES
    tr = H.pairs(t, 1)
    m = H._lgbm_fit(tr, f["trees"])
    assert m.booster_.feature_name() == E.COLUMNS


def test_regional_rows_are_one_per_origin():
    X = H.regional_features(1)
    assert X.index.is_unique and len(X) == E.LAST_ORIGIN - E.FIRST_ORIGIN + 1


# ------------------------------------------------------------------------------------------------ results, seals, API
needs_run = pytest.mark.skipif(not (OUT / "results.json").exists(), reason="run runner/run_e109.py score first")


@needs_run
@pytest.mark.parametrize("k", H.LEADS)
def test_stored_predictions_reproduce(k):
    st = pd.read_csv(OUT / f"predictions_lead{k}.csv")
    r = st.iloc[len(st) // 2]
    for m in H.METHODS:
        assert H.forecast(m, int(r["t"]), k)["forecast"] == pytest.approx(r[m], abs=1e-6)


@needs_run
def test_scored_under_frozen_protocol_with_clean_runner():
    r = json.loads((OUT / "results.json").read_text())
    assert r["run"]["protocol_sha256"] == (EXP / "runner/PROTOCOL_SHA256.txt").read_text().strip() == H.sha256(EXP / "PROTOCOL.md")
    assert not r["run"]["runner_dirty"]


@pytest.mark.skipif(not (OUT / "sealed_prospective.csv").exists(), reason="run runner/run_e109.py prospective first")
def test_all_three_seals_unchanged():
    assert H.sha256(OUT / "sealed_prospective.csv") == (OUT / "sealed_prospective.csv.sha256").read_text().strip()
    p = json.loads((OUT / "prospective_record.json").read_text())
    assert p["e107_seal"] == "246700a8d3c4fe76daf43adbfd5ea3c9d622dd124fb4d7137bde9f84a90c75fb"
    assert p["e108_seal"] == "fbc8bf911b1342e7f839cd4c27d35b037bbcd92953281067cffe7747650c325f"
    assert H.sha256(EXP.parent / "E107_Twelve_Indicator_LightGBM/out/sealed_prospective.csv") == p["e107_seal"]
    assert H.sha256(EXP.parent / "E108_Best_Defensible_Forecasting/out/sealed_prospective.csv") == p["e108_seal"]


SERVE = E.BACKEND / "data" / "e109"


@pytest.mark.skipif(not (SERVE / "lgu_status.json").exists(), reason="run runner/run_e109.py export first")
def test_api_and_every_lgu_has_a_truthful_status():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for route, name in (("evaluation", "evaluation_summary.json"), ("forecast", "forecast.json"),
                        ("lgu-status", "lgu_status.json")):
        r = c.get(f"/api/v1/e109/{route}")
        assert r.status_code == 200 and r.json() == json.loads((SERVE / name).read_text(encoding="utf-8"))
    lg = json.loads((SERVE / "lgu_status.json").read_text(encoding="utf-8"))
    assert lg["n_lgus"] == 142 and {x["status"] for x in lg["lgus"]} == {"INSUFFICIENT LOCAL EVIDENCE"}


def test_negative_control_a_round_published_before_the_issue_does_change_the_forecast(monkeypatch):
    t = E.qi("2025-Q3")
    rw = H.forecast("RW", t, 1)["forecast"]
    r0 = H.rounds()
    extra = r0.iloc[[-1]].copy()
    extra["q"], extra["quarter"], extra["H"], extra["published"] = t, E.qs(t), 60.0, "2025-09-30"
    monkeypatch.setattr(H, "rounds", lambda: pd.concat([r0, extra], ignore_index=True))
    H.known.cache_clear()
    H.forecast.cache_clear()
    try:
        assert H.forecast("RW", t, 1)["forecast"] == 60.0 != rw
    finally:
        H.known.cache_clear()
        H.forecast.cache_clear()
