"""Objectives completion (E57 objectives audit, follow-up): E59 lead-time scan results, the descriptive BERTopic files,
endpoint and PDF section, the Rule 7 rolling-threshold alert, and the 75% verdict composed from the stored numbers."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.news import topics as T
from app.quarterly import alerts_e31 as A
from app.quarterly.verdicts import compose_75pct_verdict, verdict_from_record
from app.services import dashboard as svc

client = TestClient(app)
E59 = Path("experiments/e59")
REC49 = json.loads(Path("data/e49/e49_record.json").read_text(encoding="utf-8"))
REC53 = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------- 1. E59 lead-time scan
def test_e59_scan_reports_every_lead_and_algorithm3():
    md = (E59 / "E59_results.md").read_text(encoding="utf-8")
    assert md.index("## Pre-registration") < md.index("## Results")            # protocol written first
    r = json.loads((E59 / "E59_results.json").read_text(encoding="utf-8"))
    assert r["k1_reproduces_E49"] is True and r["md5_start"] == r["md5_end"]
    assert [x["k"] for x in r["leads"]] == list(range(1, 9))                       # no lead skipped silently
    for x in r["leads"]:
        if not x["evaluable"]:
            assert x["reason"] and x["n_dates"] < 4 or "class" in x["reason"]
    assert r["algorithm3"]["maximum_reliable_lead_time"] == 1
    assert r["algorithm3_ci"]["maximum_reliable_lead_time"] == 1
    trail = r["algorithm3"]["trail"]
    assert trail[0]["pass"] and not trail[-1]["pass"] and trail[-1]["k"] == 2      # halts at the first failing k
    k1 = r["leads"][0]["model"]
    assert round(k1["accuracy"], 3) == 0.846 and k1["accuracy_ci95"][0] >= 0.75


# ------------------------------------------------------------------------------------------- 2. BERTopic
class _Store:
    def __init__(self, root: Path, n: int):
        self.root = root
        self.articles = {f"a{i}": {"article_key": f"a{i}", "title": f"title {i}", "geo_province_code": "PH040300000",
                                   "quarter": "2026-Q2" if i % 2 else "2026-Q3"} for i in range(n)}
        self._scores = [{"article_key": f"a{i}", "model_key": "K", "status": "OK", "score": 0.9} for i in range(n)]

    def read(self, name):
        return iter(self._scores if name == "scores" else [])


class _Model:
    def __init__(self, topics):
        self.topics_ = topics

    def get_topic_info(self):
        import pandas as pd
        s = pd.Series(self.topics_).value_counts()
        return pd.DataFrame({"Topic": s.index, "Count": s.values})

    def get_topic(self, t):
        return [(f"word{t}a", 0.5), (f"word{t}b", 0.4)]


def _fake_pipeline(monkeypatch, by_seed):
    import app.ml.nlp.topic_model as TM

    class P:
        def fit(self, texts, min_topic_size=10, seed=42):
            return _Model(by_seed(seed, len(texts)))
    monkeypatch.setattr(TM, "TopicModelPipeline", P)


def test_topics_insufficient_articles_writes_only_the_manifest(tmp_path):
    out = T.build_topic_files(_Store(tmp_path, 12), ["2026-Q2", "2026-Q3"], "K", out_dir=tmp_path / "topics")
    assert out["status"] == "INSUFFICIENT_ARTICLES" and out["n_articles"] == 12
    assert sorted(p.name for p in (tmp_path / "topics").iterdir()) == ["manifest.json"]


def test_topics_unstable_is_not_published(tmp_path, monkeypatch):
    rng = np.random.default_rng(0)
    _fake_pipeline(monkeypatch, lambda seed, n: [0, 1] * (n // 2) if seed == 42 else list(rng.integers(0, 2, n)))
    out = T.build_topic_files(_Store(tmp_path, 40), ["2026-Q2", "2026-Q3"], "K", out_dir=tmp_path / "topics")
    assert out["status"] == "UNSTABLE" and out["stability_ari_mean"] < 0.5
    assert not (tmp_path / "topics" / "topic_proportions.csv").exists()


def test_topics_stable_run_writes_proportions_keywords_and_manifest(tmp_path, monkeypatch):
    _fake_pipeline(monkeypatch, lambda seed, n: [0, 1] * (n // 2))                 # identical at every seed
    out = T.build_topic_files(_Store(tmp_path, 40), ["2026-Q2", "2026-Q3"], "K", out_dir=tmp_path / "topics",
                              now="2026-10-17T00:00:00Z")
    assert out["status"] == "OK" and out["stability_ari_mean"] == 1.0 and out["n_articles"] == 40
    m = json.loads((tmp_path / "topics" / "manifest.json").read_text(encoding="utf-8"))
    for k in ("embedding_model", "seed", "n_articles", "created_utc", "use", "proportions_sha256"):
        assert m[k] is not None, k
    assert "Not a forecast feature" in m["use"]
    assert json.loads((tmp_path / "topics" / "topics.json").read_text())["topics"]["0"][0]["word"] == "word0a"
    # the service reads the same files: region = provinces weighted by their article counts
    monkeypatch.setattr(svc.E31, "NEWS_STORE", tmp_path)
    q3 = svc.news_topics(None, "2026-Q3")
    assert q3["status"] == "OK" and q3["nArticles"] == 20 and abs(sum(t["share"] for t in q3["topics"]) - 1) < 1e-9
    assert q3["topics"][0]["keywords"][0].startswith("word")


def test_topics_endpoint_reports_the_stored_status_with_numbers():
    m = json.loads(Path("data/news_e31/topics/manifest.json").read_text(encoding="utf-8"))
    for scope, ident in (("region", "calabarzon"), ("province", "quezon"), ("municipality", "quezon-infanta")):
        b = client.get(f"/api/v1/insights/topics?scope={scope}&id={ident}&quarter=2026-Q3").json()
        assert b["status"] == m["status"] and b["use"] and "forecast" in b["use"]
        if m["status"] != "OK":                                                     # never forced output
            assert b["topics"] == [] and str(m["n_articles"]) in b["note"]
    assert m["status"] in ("OK", "UNSTABLE", "INSUFFICIENT_ARTICLES")


def test_pdf_reports_have_the_topics_section(monkeypatch):
    from app.services import report as rpt

    flow = rpt._topics_block(svc.news_topics(None, "2026-Q3"), 160)
    text = " ".join(getattr(f, "text", "") for f in flow)
    assert "forecast" in text.lower()
    seen = []
    real = rpt._topics_block
    monkeypatch.setattr(rpt, "_topics_block", lambda topics, width: seen.append(topics) or real(topics, width))
    q = svc.latest_quarter()
    assert rpt.build_region_report(q)[:4] == b"%PDF"
    assert rpt.build_province_report("quezon", q)[:4] == b"%PDF"
    assert len(seen) == 2 and all("status" in t for t in seen)                     # both reports render the section


# ------------------------------------------------------------------------------------------- 4. Rule 7
def test_rolling_threshold_is_the_trailing_75th_percentile_of_the_provinces_own_estimates():
    by_q = {}
    for q in REC49["quarters"]:
        by_q.setdefault(q["quarter"], q)
    code = "PH040300000"
    prior = [by_q[x]["provinces"][code]["p_high"] for x in sorted(by_q) if x < "2026-Q4"]
    r = A.rolling_threshold(REC49, "2026-Q4", code)
    assert r["n_prior"] == len(prior) == 13 and r["prior_quarters"][-1] == "2026-Q3"     # no look-ahead
    assert r["threshold"] == pytest.approx(np.percentile(prior, 75), abs=1e-4)
    assert A.rolling_threshold(REC49, "2023-Q4", code) is None                    # fewer than 4 earlier estimates


def test_rule7_candidates_carry_the_definition_and_stay_staged(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    c = A.candidates(REC49)
    roll = [x for x in c if x["alert_reason"] == "ROLLING_THRESHOLD"]
    assert roll and all(x["evidence"]["p_high"] > x["evidence"]["threshold"] for x in roll)
    assert all("75th percentile" in x["reason_text"] and "Rule 7" in x["reason_text"] for x in roll)
    assert all(x["reason_text"] for x in c)                                        # every reason is explained
    assert "PH040500000" not in {x["province_code"] for x in roll}                 # Batangas 0.335 is below its own
    # a province at or below its own threshold does not fire
    rec = json.loads(json.dumps(REC49))
    q4 = next(q for q in rec["quarters"] if q["quarter"] == "2026-Q4")
    for v in q4["provinces"].values():
        v["p_high"] = 0.10
    assert not [x for x in A.candidates(rec) if x["alert_reason"] == "ROLLING_THRESHOLD"]


def test_alerts_api_returns_the_reason_text():
    from app.api.v1 import alerts as api

    row = api._row(SimpleNamespace(id=1, quarter="2026-Q4", province_code="PH040300000", threshold_exceeded=True,
                                   confirmed=False, created_at=None, dismissed=False, alert_reason="ROLLING_THRESHOLD",
                                   prev_risk_probability=None, risk_delta=None))
    assert row["confirmed"] is False and "rolling historical threshold" in row["reason_text"].lower()


# ------------------------------------------------------------------------------------------- 5. 75% verdict
def test_verdict_follows_the_stored_interval():
    v49 = verdict_from_record(REC49["validation"])
    v53 = verdict_from_record(REC53["validation"])
    assert v49["demonstrated"] is True and "stays above 75%, so the target is demonstrated" in v49["verdict"]
    assert "0.769 to 0.923" in v49["verdict"]
    assert v53["demonstrated"] is False and "reaches below 75%, so the target is not demonstrated" in v53["verdict"]
    assert "0.646 to 0.908" in v53["verdict"]
    low = compose_75pct_verdict(correct=40, n=65, accuracy=0.615, ci95=[0.5, 0.7], n_dates=13, first_quarter="2023-Q1",
                                last_quarter="2026-Q3", balanced_accuracy=0.6, always_high_accuracy=0.8,
                                persistence_accuracy=0.85, holm_p={"B1_PERSISTENCE": 0.01})
    assert "below 75%" in low["verdict"] and "Significant paired differences" in low["verdict"]


def test_served_e49_verdict_says_demonstrated(serve_e49):
    note = client.get("/api/v1/config").json()["modelPerformance"]["targets"]["note"]
    assert "the target is demonstrated on development dates" in note and "not demonstrated" not in note


def test_served_e53_verdict_says_not_demonstrated():                     # the default record
    note = client.get("/api/v1/config").json()["modelPerformance"]["targets"]["note"]
    assert "not demonstrated" in note and "0.646 to 0.908" in note


def test_record_builders_compose_the_verdict():
    for path in ("scripts/build_record_e36.py", "experiments/e53/runner/build_record_e53.py"):
        src = Path(path).read_text(encoding="utf-8")
        assert "compose_75pct_verdict" in src or "verdict_from_record" in src, path
        assert "reaches below 75%" not in src, path
