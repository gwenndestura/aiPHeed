"""Tests of app.quarterly (the configuration-driven quarterly update) and the PHT quarter fix.

All data here are SYNTHETIC fixtures written to pytest's tmp_path. They test mechanics only and are never
mixed into study data, model evaluation or reported results.
Run: python -B -m pytest -q --noconftest -c tests/pytest.ini --rootdir tests tests/test_quarterly_pipeline.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

AL = Path(__file__).resolve().parents[1] / "backend_dev"   # E24 isolated copy
sys.path.insert(0, str(AL))

from app.ml.corpus._dates import quarter_of_publication  # noqa: E402
from app.ml.corpus.bias_weighter import _parse_quarter  # noqa: E402
from app.quarterly.config import ForecastPeriod, load_period, save_period  # noqa: E402
from app.quarterly.eligibility import (AFTER, BEFORE, DUP, ELIGIBLE, UNDATED, classify_news,  # noqa: E402
                                       indicator_rows_available)
from app.quarterly.periods import Quarter, to_ph  # noqa: E402
from app.quarterly.registry import Registry, SnapshotStore  # noqa: E402
from app.quarterly.update import PROVINCES, load_latest, run_update  # noqa: E402
from app.quarterly.completeness import province_quarter_matrix, summarize  # noqa: E402

CAV, LAG = PROVINCES[0], PROVINCES[1]


# ------------------------------------------------------------------ PHT quarter fix (regression)
@pytest.mark.parametrize("value,expected", [
    ("2025-12-31T19:00:00Z", "2026-Q1"),            # 03:00 PHT on 1 Jan -> next quarter (was 2025-Q4)
    ("2025-12-31T15:59:59+00:00", "2025-Q4"),       # 23:59:59 PHT on 31 Dec
    ("Wed, 31 Dec 2025 17:00:00 GMT", "2026-Q1"),   # RFC 822
    ("2026-01-01", "2026-Q1"),
    ("2025-12-31 23:30", "2025-Q4"),                # naive = PHT
    ("not a date", None), (None, None)])
def test_quarter_of_publication_uses_philippine_time(value, expected):
    assert quarter_of_publication(value) == expected
    if value is not None:
        assert _parse_quarter(value) == expected      # bias weights use the same rule


# ------------------------------------------------------------------ periods / config
def period(ref="2026-Q4", cutoff=None, reqs=None):
    r = Quarter.parse(ref)
    return ForecastPeriod(r, to_ph(cutoff) if cutoff else r.end().floor("s"), "m-test", "f-test", reqs or [])


def test_target_and_news_window_are_derived():
    p = period()
    assert str(p.target_quarter) == "2027-Q1"
    assert p.news_window_start == pd.Timestamp("2026-10-01 00:00", tz="Asia/Manila")
    assert p.news_window_end == pd.Timestamp("2026-12-31 23:59:59", tz="Asia/Manila")
    assert p.quarter_complete
    assert p.target_quarter.display() == "Q1 2027 (January–March 2027)"
    assert p.reference_quarter.display() == "Q4 2026 (October–December 2026)"


def test_early_cutoff_marks_quarter_incomplete():
    p = period(cutoff="2026-11-15T12:00:00+08:00")
    assert not p.quarter_complete and p.news_window_end == to_ph("2026-11-15T12:00:00+08:00")


def test_cutoff_inside_target_quarter_is_rejected():
    with pytest.raises(ValueError):
        period(cutoff="2027-01-01T00:00:00+08:00").validate()
    with pytest.raises(ValueError):
        period(cutoff="2026-09-30T23:00:00+08:00").validate()


def test_config_roundtrip_and_inconsistent_target_rejected(tmp_path):
    p = period()
    f = tmp_path / "fp.json"
    save_period(p, f)
    q = load_period(f)
    assert str(q.target_quarter) == "2027-Q1" and q.cutoff == p.cutoff
    d = json.loads(f.read_text())
    d["target_quarter"] = "2027-Q2"
    f.write_text(json.dumps(d))
    with pytest.raises(ValueError):
        load_period(f)


def test_advance_to_next_quarter():
    p = period(reqs=[{"id": "news", "kind": "news", "quarter": "2026-Q4"},
                     {"id": "gov", "kind": "indicator", "quarter": "2026-Q3"}])
    n = p.advanced()
    assert str(n.reference_quarter) == "2027-Q1" and str(n.target_quarter) == "2027-Q2"
    assert n.news_window_start == pd.Timestamp("2027-01-01", tz="Asia/Manila")
    assert [r["quarter"] for r in n.requirements] == ["2027-Q1", "2026-Q4"]


# ------------------------------------------------------------------ news eligibility
def news_frame():
    return pd.DataFrame([
        {"link": "https://a.ph/1", "published": "2026-10-01T00:00:00+08:00", "province_code": CAV},   # first second
        {"link": "https://a.ph/2", "published": "2026-12-31T15:59:59Z", "province_code": CAV},        # 23:59:59 PHT
        {"link": "https://a.ph/3", "published": "2026-12-31T16:00:00Z", "province_code": CAV},        # 2027-01-01 PHT
        {"link": "https://a.ph/4", "published": "2027-02-10", "province_code": LAG},                  # target quarter
        {"link": "https://a.ph/5", "published": "2026-09-30T23:59:00+08:00", "province_code": LAG},   # previous q
        {"link": "https://a.ph/6", "published": None, "retrieved_at": "2026-11-01", "province_code": LAG},
        {"link": "http://www.a.ph/1/", "published": "2026-10-02", "province_code": CAV},              # duplicate URL
    ])


def test_news_classification_by_publication_time_only():
    c = classify_news(news_frame(), period())
    assert c["eligibility"].tolist() == [ELIGIBLE, ELIGIBLE, AFTER, AFTER, BEFORE, UNDATED, DUP]


def test_retrieval_date_never_assigns_a_quarter():
    df = news_frame().iloc[[5]].assign(retrieved_at="2026-11-01T10:00:00+08:00")
    assert classify_news(df, period())["eligibility"].iloc[0] == UNDATED


def test_cutoff_excludes_later_reference_quarter_news():
    c = classify_news(news_frame(), period(cutoff="2026-11-15T00:00:00+08:00"))
    assert c.loc[1, "eligibility"] == AFTER          # 31 Dec article is after a 15 Nov cutoff


def test_indicator_availability_unknown_is_unavailable():
    df = pd.DataFrame({"v": [1, 2, 3], "available_at": ["2026-12-01T00:00:00+08:00", "2027-01-05", None]})
    out = indicator_rows_available(df, period().cutoff)
    assert out["v"].tolist() == [1]


# ------------------------------------------------------------------ registry / store / update
def make_files(tmp_path, with_news=True, authorized=True):
    reg = Registry(tmp_path / "registry.json")
    news = tmp_path / "news.csv"
    news_frame().to_csv(news, index=False)
    gov = tmp_path / "gov.csv"
    pd.DataFrame({"province_code": PROVINCES, "quarter": "2026-Q3", "v": 1.0}).to_csv(gov, index=False)
    mdl = tmp_path / "model.bin"
    mdl.write_bytes(b"synthetic-model")
    if with_news:
        reg.register("news_2026Q4", "news", news, observation_start="2026-Q4", observation_end="2026-Q4",
                     available_at="2026-12-31T23:59:59+08:00", authorized=authorized, authorized_by="test")
    reg.register("gov", "indicator", gov, observation_start="2021-Q1", observation_end="2026-Q3",
                 available_at="2026-11-20T00:00:00+08:00", authorized=True, authorized_by="test")
    reg.register("model", "model", mdl, authorized=True, authorized_by="test")
    reg.save()
    reqs = [{"id": "news", "kind": "news", "quarter": "2026-Q4", "source_ids": ["news_2026Q4"]},
            {"id": "gov", "kind": "indicator", "quarter": "2026-Q3", "source_ids": ["gov"]},
            {"id": "model", "kind": "model", "source_ids": ["model"]}]
    return reg, reqs


def loader(entry):
    return pd.read_csv(entry.path, dtype={"province_code": str})


def test_registry_hashes_and_vintages(tmp_path):
    reg, _ = make_files(tmp_path)
    e = reg.latest("gov")
    assert len(e.sha256) == 64 and e.verify()
    assert reg.register("gov", "indicator", e.path) is e                      # same bytes: idempotent
    Path(e.path).write_text("province_code,quarter,v\nPH040100000,2026-Q3,2.0\n")
    assert not e.verify()                                                     # silent overwrite detected
    with pytest.raises(ValueError):
        reg.register("gov", "indicator", e.path)                              # revision needs a note
    e2 = reg.register("gov", "indicator", e.path, revision_note="PSA revision", authorized=True,
                      observation_end="2026-Q3", available_at="2026-12-01")
    assert e2.vintage == 2 and reg.latest("gov") is e2 and len([x for x in reg.entries if x.source_id == "gov"]) == 2


def test_snapshot_ingest_is_idempotent(tmp_path):
    reg, _ = make_files(tmp_path)
    st = SnapshotStore(tmp_path / "store")
    a = st.ingest(reg.latest("gov"))
    b = st.ingest(reg.latest("gov"))
    assert a["new"] and not b["new"] and len(st.records()) == 1


def test_full_update_ready_and_consistent(tmp_path):
    reg, reqs = make_files(tmp_path)
    p = period(reqs=reqs)
    rec = run_update(p, reg, tmp_path / "out", store=SnapshotStore(tmp_path / "store"), news_loader=loader,
                     forecaster=lambda per, r: {"target_quarter": str(per.target_quarter), "provinces": []},
                     now=pd.Timestamp("2027-01-15", tz="Asia/Manila"))
    assert rec["status"] == "READY" and rec["forecast"]["target_quarter"] == "2027-Q1"
    n = rec["supporting_news"]
    assert n["eligible"] == 2 and n["excluded_after_cutoff"] == 2 and n["quarantined_undated"] == 1
    assert all(a["published_ph"] <= "2026-12-31T23:59:59+08:00" for a in n["articles"])
    assert rec["labels"]["target"] == "Forecast target: Q1 2027 (January–March 2027)"
    assert rec["labels"]["news"] == "Supporting news: Q4 2026 (October–December 2026)"
    assert load_latest(tmp_path / "out")["content_sha256"] == rec["content_sha256"]
    again = run_update(p, reg, tmp_path / "out", news_loader=loader,
                       forecaster=lambda per, r: {"target_quarter": str(per.target_quarter), "provinces": []},
                       now=pd.Timestamp("2027-01-16", tz="Asia/Manila"))
    assert again.get("unchanged") is True                                     # idempotent rerun
    assert not (tmp_path / "out" / "2027-Q1" / "history").exists()


def test_missing_news_gives_insufficient_not_a_forecast(tmp_path):
    reg, reqs = make_files(tmp_path, with_news=False)
    rec = run_update(period(reqs=reqs), reg, tmp_path / "out", news_loader=loader,
                     forecaster=lambda *a: {"should": "not run"}, now=pd.Timestamp("2027-01-15", tz="Asia/Manila"))
    assert rec["status"] == "INSUFFICIENT_DATA" and rec["forecast"] is None
    assert any(m.startswith("news: MISSING") for m in rec["missing"])
    assert rec["supporting_news"]["eligible"] == 0


def test_unauthorized_source_blocks(tmp_path):
    reg, reqs = make_files(tmp_path, authorized=False)
    rec = run_update(period(reqs=reqs), reg, tmp_path / "out", news_loader=loader,
                     now=pd.Timestamp("2027-01-15", tz="Asia/Manila"))
    assert rec["status"] == "BLOCKED" and rec["forecast"] is None
    assert rec["supporting_news"]["eligible"] == 0                            # unauthorized news never read


def test_cutoff_not_reached_is_insufficient(tmp_path):
    reg, reqs = make_files(tmp_path)
    rec = run_update(period(reqs=reqs), reg, tmp_path / "out", news_loader=loader,
                     forecaster=lambda *a: {"x": 1}, now=pd.Timestamp("2026-10-13", tz="Asia/Manila"))
    assert rec["status"] == "INSUFFICIENT_DATA" and any("not yet reached" in m for m in rec["missing"])


def test_stale_and_late_indicators(tmp_path):
    reg, reqs = make_files(tmp_path)
    late = tmp_path / "late.csv"
    late.write_text("x\n1\n")
    reg.register("late", "indicator", late, observation_end="2026-Q3", available_at="2027-02-01", authorized=True)
    stale = tmp_path / "stale.csv"
    stale.write_text("x\n2\n")
    reg.register("stale", "indicator", stale, observation_end="2026-Q1", available_at="2026-06-01", authorized=True)
    reqs = reqs + [{"id": "late", "kind": "indicator", "quarter": "2026-Q3", "source_ids": ["late"]},
                   {"id": "stale", "kind": "indicator", "quarter": "2026-Q3", "source_ids": ["stale"]}]
    rec = run_update(period(reqs=reqs), reg, tmp_path / "out", news_loader=loader,
                     now=pd.Timestamp("2027-01-15", tz="Asia/Manila"))
    st = {c["id"]: c["status"] for c in rec["requirements"]}
    assert st["late"] == "NOT_AVAILABLE_BY_CUTOFF" and st["stale"] == "STALE" and rec["status"] == "INSUFFICIENT_DATA"


def test_transition_2027q1_to_2027q2(tmp_path):
    """The same code advances one quarter: target, news window and exclusions all move together."""
    reg, reqs = make_files(tmp_path)
    p1 = period(reqs=reqs)
    p2 = p1.advanced()
    q1news = tmp_path / "news_q1.csv"
    pd.DataFrame([{"link": "https://b.ph/1", "published": "2027-02-01T10:00:00+08:00", "province_code": CAV},
                  {"link": "https://b.ph/2", "published": "2026-12-20T10:00:00+08:00", "province_code": CAV},
                  {"link": "https://b.ph/3", "published": "2027-04-01T00:00:00+08:00", "province_code": CAV}]
                 ).to_csv(q1news, index=False)
    reg.register("news_2027Q1", "news", q1news, observation_start="2027-Q1", observation_end="2027-Q1",
                 available_at="2027-03-31T23:59:59+08:00", authorized=True)
    reg.register("gov", "indicator", reg.latest("gov").path, revision_note="unchanged bytes ok")
    gov2 = tmp_path / "gov2.csv"
    gov2.write_text("province_code,quarter,v\nPH040100000,2026-Q4,1\n")
    reg.register("gov", "indicator", gov2, revision_note="2026-Q4 added", observation_end="2026-Q4",
                 available_at="2027-02-20T00:00:00+08:00", authorized=True)
    p2.requirements = [{"id": "news", "kind": "news", "quarter": "2027-Q1", "source_ids": ["news_2027Q1"]},
                       {"id": "gov", "kind": "indicator", "quarter": "2026-Q4", "source_ids": ["gov"]},
                       {"id": "model", "kind": "model", "source_ids": ["model"]}]
    rec = run_update(p2, reg, tmp_path / "out", news_loader=loader, forecaster=lambda per, r: {"t": str(per.target_quarter)},
                     now=pd.Timestamp("2027-04-15", tz="Asia/Manila"))
    assert rec["period"]["target_quarter"] == "2027-Q2" and rec["forecast"] == {"t": "2027-Q2"}
    assert rec["labels"]["news"] == "Supporting news: Q1 2027 (January–March 2027)"
    n = rec["supporting_news"]
    assert n["eligible"] == 1 and n["excluded_before_window"] == 1 and n["excluded_after_cutoff"] == 1
    # the 2027-Q1 record is untouched and still reproducible
    rec1 = run_update(p1, reg, tmp_path / "out", news_loader=loader, now=pd.Timestamp("2027-01-15", tz="Asia/Manila"))
    assert rec1["period"]["target_quarter"] == "2027-Q1"
    assert json.loads((tmp_path / "out" / "latest.json").read_text())["target_quarter"] == "2027-Q1"


def test_completeness_reports_missing_not_zero():
    df = pd.DataFrame({"province_code": [CAV, CAV, LAG], "quarter": ["2026-Q1", "2026-Q1", "2026-Q2"],
                       "v": [1.0, 2.0, None]})
    m = province_quarter_matrix(df, "v", [CAV, LAG], ["2026-Q1", "2026-Q2"])
    s = dict(zip(zip(m["quarter"], m["province_code"]), m["status"]))
    assert s[("2026-Q1", CAV)] == "CONFLICT" and s[("2026-Q1", LAG)] == "MISSING" and s[("2026-Q2", LAG)] == "NULL"
    assert summarize(m)["expected"] == 4


def test_api_router_serves_the_same_record(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.v1.quarterly as q
    reg, reqs = make_files(tmp_path, with_news=False)
    rec = run_update(period(reqs=reqs), reg, tmp_path / "out", now=pd.Timestamp("2026-10-13", tz="Asia/Manila"))
    monkeypatch.setattr(q, "RECORDS_DIR", tmp_path / "out")
    a = FastAPI()
    a.include_router(q.router, prefix="/api/v1")
    r = TestClient(a).get("/api/v1/quarterly/forecast-period")
    assert r.status_code == 200 and r.json()["content_sha256"] == rec["content_sha256"]
    assert r.json()["labels"]["target"].startswith("Forecast target: Q1 2027")
