"""Tests for the FIRI v2 data audit (aipheed-backend-aligned/experiments/FIRI_V2_DATA_AUDIT) and the frozen addenda of
FINAL_THESIS_OBJECTIVES: source reconciliation, the rebuilt BSP series, the typhoon recomputation, the coverage
matrix, issue-date safety of the audited training tables and the rerun verdict."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments"
AUD = EXP / "FIRI_V2_DATA_AUDIT"
CH1 = EXP / "FINAL_THESIS_OBJECTIVES"
OUT = AUD / "out"


def _j(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_protocol_and_addenda_hashes_unchanged():
    for doc, h in (("FINAL_TARGET_AND_EVALUATION_PROTOCOL.md", "PROTOCOL_SHA256.txt"),
                   ("ADDENDUM_1_DATA_CORRECTIONS.md", "ADDENDUM_1_SHA256.txt"),
                   ("ADDENDUM_2_NEWS_COVERAGE.md", "ADDENDUM_2_SHA256.txt")):
        assert _sha(CH1 / doc) == (CH1 / "runner" / h).read_text().strip(), doc


def test_psa_sources_reconcile_with_the_fresh_pull():
    r = _j(OUT / "reconcile.json")
    assert r["cpi"]["index"]["compared"] == r["cpi"]["index"]["equal_within_tol"] == 690
    assert r["cpi"]["yoy_published_vs_recomputed"]["equal_within_tol"] == 690
    for k in ("palay_corn", "fisheries"):
        assert r[k]["compared"] == r[k]["equal_within_tol"] == 220
    assert r["lfs"]["compared"] == r["lfs"]["equal_within_tol"]
    assert {d["q"] for d in r["rice"]["differing"]} == {"2026-Q3"}          # the partial held quarter, nothing else


def test_bsp_quarters_are_differences_of_the_cited_cumulative_figures():
    c = pd.read_csv(AUD / "data" / "bsp_cash_remittances_cumulative.csv").set_index(["year", "period"])[
        "cash_remittances_usd_bn"]
    q = pd.read_csv(AUD / "data" / "bsp_cash_remittances_quarterly.csv").set_index("quarter")["cash_remit_usd_bn"]
    assert q["2025-Q1"] == pytest.approx(c[(2025, "Q1")])
    assert q["2025-Q2"] == pytest.approx(c[(2025, "H1")] - c[(2025, "Q1")], abs=1e-4)
    assert q["2025-Q4"] == pytest.approx(c[(2025, "FY")] - c[(2025, "9M")], abs=1e-4)
    assert {"2026-Q1", "2026-Q2"} <= set(q.index)
    assert pd.read_csv(AUD / "data" / "bsp_cash_remittances_cumulative.csv")["source_url"].str.startswith("http").all()


def test_corrections_reach_the_model_features():
    ch = pd.read_csv(OUT / "feature_change.csv").set_index("feature")
    assert ch.loc["E2", "changed"] > 0 and ch.loc["E2", "newly_available"] > 0
    assert ch.loc["C2", "changed"] > 0
    for f in ("A1_food", "A2", "C1", "C3", "C4", "E1", "N1", "H1", "V1"):
        assert ch.loc[f, "changed"] == 0, f


def test_typhoon_recomputation_matches_most_held_counts():
    t = _j(OUT / "typhoons_compare.json")
    assert t["compared"] == 115 and t["equal"] >= 100
    assert all(abs(d["tc_count"] - d["tc_count_recomputed"]) == 1 for d in t["differing"])


def test_coverage_matrix_has_all_twelve_indicators():
    cov = pd.read_csv(OUT / "coverage_matrix.csv")
    assert set(cov["indicator"]) == {"A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"}
    assert cov["validation"].notna().all() and cov["action"].notna().all()


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_training_tables_use_only_information_published_before_issue(k):
    T = pd.read_csv(OUT / f"training_table_lead{k}.csv")
    T = T[T["sws_newest_published"].notna()]
    assert (T["sws_newest_published"] < T["issue_date"]).all()
    news = T["news_latest_published"].dropna()
    assert (pd.to_datetime(news) < pd.to_datetime(T.loc[news.index, "issue_date"])).all()
    psa = pd.to_datetime(T["psa_newest_month"] + "-01") + pd.offsets.MonthEnd(0) + pd.Timedelta(days=5)
    assert (psa < pd.to_datetime(T["issue_date"])).all()                         # PSA releases ~day 5 of m+1


def test_rerun_verdict_with_audited_inputs():
    r = _j(OUT / "rerun_results.json")
    assert r["primary"]["max_reliable_lead"] == 1
    assert r["primary"]["leads"]["1"]["metrics"]["accuracy"] >= 0.75
    assert not _j(OUT / "news_coverage.json")["news_coverage_adds_value"]


def test_audited_seal_and_first_seal_both_intact():
    for d in (CH1 / "out", OUT / "ch1_audited"):
        p = d / "sealed_prospective.csv"
        assert _sha(p) == (d / "sealed_prospective.csv.sha256").read_text().strip()
