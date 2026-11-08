"""Tests for the FINAL food-insecurity LightGBM experiment (FINAL_PROTOCOL.md + ADDENDUM_1.md)."""
import json
import sys
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "FINAL_FOOD_INSECURITY_LIGHTGBM"
sys.path.insert(0, str(EXP / "runner"))
import fi_lib as M  # noqa: E402
import news_features as NF  # noqa: E402

np, pd = M.np, M.pd
OUT = EXP / "out"
scored = pytest.mark.skipif(not (OUT / "results_primary.json").exists(), reason="run run_final.py all first")


def test_protocol_and_addendum_hashes_unchanged():
    assert M.sha256(EXP / "FINAL_PROTOCOL.md") == (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text().strip()
    assert M.sha256(EXP / "ADDENDUM_1.md") == (EXP / "runner" / "ADDENDUM_1_SHA256.txt").read_text().strip()


def test_twelve_families_all_in_the_model():
    assert sorted(M.FAMILY_COLS) == sorted(M.E.EXPECTED_FAMILIES)          # the 12 FIRI indicators
    model = set(M.PRIMARY_COLS)
    for fam, cols in M.FAMILY_COLS.items():
        assert set(cols) <= model, fam
    fm = pd.read_csv(EXP / "data" / "feature_map.csv")
    assert set(fm["feature"]) == model and fm["family"].nunique() == 13      # 12 families + design (area, lead)


def test_primary_rounds_respect_study_window():
    r = M.rounds("primary")
    assert r["q"].min() >= M.qi("2021-Q1") and (r["published"] >= "2021-01-01").all()
    assert len(pd.read_csv(EXP / "data" / "sws_area_rounds_2021.csv")) == 23


def test_label_definition():
    q = M.qi("2024-Q3")
    prev = [M.outcome("BL", x) for x in range(q - 4, q) if M.outcome("BL", x) is not None]
    assert M.ref_final("BL", q) == pytest.approx(np.mean(prev))
    assert M.label_final("BL", q) == int(M.outcome("BL", q) > np.mean(prev))
    assert M.label_final("BL", M.qi("2021-Q2")) is None                     # fewer than two earlier 2021+ quarters


def test_ref_hat_uses_persistence_fill_after_newest_known():
    kn = ((10, 5.0, "x", "x", 4.0), (11, 7.0, "x", "x", 4.0))
    assert M.ref_hat(kn, 13) == pytest.approx(np.mean([5.0, 7.0, 7.0]))   # q-4=9 missing, 10, 11 known, 12 filled
    assert M.ref_hat(kn, 16) == pytest.approx(7.0)                          # all four filled


def test_vintage_excludes_rounds_published_on_or_after_issue():
    iss = M.issue(M.qi("2024-Q3"))                                          # 2024-10-01; 2024-Q3 published 10-17
    assert M.known(iss, "BL")[-1][0] == M.qi("2024-Q2")


def test_training_targets_known_before_issue():
    P = M.panel("primary", "primary")
    t = M.qi("2025-Q2")
    tr = M.training(P, t, "primary")
    for r in tr.itertuples():
        assert r.t < t and r.q in {x[0] for x in M.known(M.issue(t), r.area_name)}


def test_news_window_ends_before_issue_and_dedup_flags():
    fw, iss = "2024-06-29", "2024-10-01"
    v = NF.gap_features(fw, iss, "C")
    assert v[8] is not None and v[8] < pd.Timestamp(iss)
    d = NF.corpus()
    assert d["anticipatory"].le(d["food_event"]).all()
    assert d["event_dup"].sum() > 0


def test_anticipatory_lexicon():
    assert NF.ANTICIPATORY.search("PH braces for severe El Nino seen to last until May")
    assert not NF.ANTICIPATORY.search("Typhoon damage to crops reaches P1 billion")


@scored
def test_leakage_audit_passed_with_negative_control():
    a = json.loads((OUT / "leakage_audit.json").read_text())
    assert a["passed"] and a["negative_control"]["changed"] and len(a["origins"]) == 10


@scored
def test_reported_primary_verdict_reproduces_from_predictions():
    R = pd.read_csv(OUT / "predictions_primary.csv")
    res = json.loads((OUT / "results_primary.json").read_text())
    for k in M.LEADS:
        D = R[R["lead"] == k]
        acc = float(((D["FIL_p"] > 0.5).astype(int) == D["label"]).mean())
        assert acc == pytest.approx(res["FIL"][str(k)]["metrics"]["accuracy"])
    assert res["max_reliable_lead"] == 0


@scored
def test_prediction_rows_carry_issue_time_bookkeeping():
    R = pd.read_csv(OUT / "predictions_primary.csv")
    for c in ("issue_date", "sws_newest_q", "sws_newest_published", "psa_newest_month", "news_latest_published",
              "target_quarter", "lead_days", "true_horizon", "h_age_days"):
        assert R[c].notna().all(), c
    assert (R["sws_newest_published"] < R["issue_date"]).all()
    assert (pd.to_datetime(R["news_latest_published"]) < pd.to_datetime(R["issue_date"])).all()
    assert (R["true_horizon"] >= R["lead"]).all()
    # usually one quarter more than the lead; equal only at 2025-07-01 (April 2025 round published 27 June)
    short = R[R["true_horizon"] == R["lead"]]
    assert set(short["issue_date"]) == {"2025-07-01"}


@scored
def test_seal_hash():
    p = OUT / "sealed_prospective.csv"
    assert M.sha256(p) == (OUT / "sealed_prospective.csv.sha256").read_text().strip()
    s = pd.read_csv(p)
    assert set(s["target_quarter"]) == {"2026-Q4", "2027-Q1", "2027-Q2", "2027-Q3"}
