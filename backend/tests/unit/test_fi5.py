"""FI5 unit tests: target rule, as-of (no future information), models, metrics, NLP bias correction, rankings,
plain-language explanations, FIRI v2 independence, and the read-only API."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.fi5 import evaluate as E
from app.fi5 import explain as X
from app.fi5 import nlp as N
from app.fi5 import rankings as R
from app.fi5.features import ALL, FEATURE_SETS, NEWS, OUTCOME, FeatureBuilder
from app.fi5.models import Model
from app.fi5.paths import OUT
from app.fi5.target import BASELINE_Q, MIN_BASELINE_OBS, labels, q_end, qindex, qlabel, quarterly

FI5_DIR = Path(__file__).resolve().parents[2] / "app" / "fi5"


# ---------------------------------------------------------------- target
def test_label_rule_matches_definition():
    lab = labels()
    q = quarterly()
    for _, r in lab.dropna(subset=["y"]).sample(15, random_state=0).iterrows():
        prev = q[(q["qi"] >= r["qi"] - BASELINE_Q) & (q["qi"] < r["qi"])]["hunger"]
        assert len(prev) >= MIN_BASELINE_OBS
        assert r["y"] == int(r["hunger"] > prev.mean())


def test_unobserved_quarters_have_no_label():
    lab = labels()
    observed = set(lab["quarter"])
    assert "2020-Q1" not in observed or not np.isnan(lab.set_index("quarter").loc["2020-Q1", "hunger"])
    assert lab["y"].dropna().isin([0, 1]).all()
    assert lab["y"].isna().sum() > 0          # the first quarters have too short a history: unlabeled, not LOW


def test_quarter_helpers_roundtrip():
    for s in ["1999-Q1", "2010-Q4", "2026-Q3"]:
        assert qlabel(qindex(s)) == s
    assert q_end(qindex("2026-Q3")) == pd.Timestamp("2026-09-30")


# ---------------------------------------------------------------- as-of: no future information
def _truncated_builder(d: pd.Timestamp) -> FeatureBuilder:
    fb, cut = FeatureBuilder(), FeatureBuilder()
    for name in ["cpi", "palay", "lfs", "nasa", "oni", "gdelt", "remit", "poverty", "fssi"]:
        df = getattr(fb, name)
        setattr(cut, name, df[df["available_from"] <= d] if len(df) else df)
    cut.sws = fb.sws[fb.sws["published"] <= d]
    cut.tc = fb.tc[fb.tc["t"] <= d]
    return fb, cut


@pytest.mark.parametrize("issue,lead", [("2008-Q2", 1), ("2015-Q4", 2), ("2020-Q1", 3), ("2024-Q3", 1), ("2026-Q3", 4)])
def test_rows_do_not_depend_on_later_data(issue, lead):
    t = qindex(issue)
    fb, cut = _truncated_builder(q_end(t))
    a, b = fb.row(t, t + lead), cut.row(t, t + lead)
    for k in ALL:
        va, vb = a.get(k, np.nan), b.get(k, np.nan)
        assert (pd.isna(va) and pd.isna(vb)) or va == pytest.approx(vb), k


def test_training_labels_are_published_before_issue():
    X1 = E.design(2)
    L = X1[X1["y"].notna()]
    r = L[L["tqi"] >= qindex("2015-Q1")].iloc[0]
    tr = L[L["target_published"] <= r["issue_ts"]]
    assert (tr["target_published"] <= r["issue_ts"]).all()
    assert tr["tqi"].max() < r["tqi"]


# ---------------------------------------------------------------- feature architecture
def test_five_domains_and_no_news_group():
    from app.fi5.sources import REG
    doms = {REG[f].domain for f in ALL if f not in OUTCOME}
    assert doms == {"market", "climate", "employment", "remittance", "poverty"}
    for d in doms:     # every domain carries government and news evidence together
        kinds = {REG[f].kind for f in ALL if f not in OUTCOME and REG[f].domain == d}
        assert kinds == {"government", "news"}, d
    assert "news" not in doms


def test_domain_ablation_sets():
    for d in ["market", "climate", "employment", "remittance", "poverty"]:
        fs = E.feature_list(f"drop_{d}")
        assert set(OUTCOME) <= set(fs)
        assert all(X.block_of(f) != d for f in fs)
    assert not set(FEATURE_SETS["psa_only"]) & set(NEWS)
    assert set(FEATURE_SETS["nlp_only"]) == set(NEWS)


# ---------------------------------------------------------------- models and metrics
def test_persistence_uses_latest_anomaly():
    df = pd.DataFrame({"hunger_last_anom": [2.0, -1.0, 0.0]})
    assert Model("persistence").predict_proba(df).tolist() == [1.0, 0.0, 0.0]


def test_lgbm_learns_planted_signal_and_handles_missing():
    rng = np.random.default_rng(0)
    n = 80
    df = pd.DataFrame({c: rng.normal(size=n) for c in FEATURE_SETS["full"]})
    df.loc[: n // 2, NEWS] = np.nan                       # news absent in the first half, as in the real data
    y = (df["cpi_food_yoy"] > 0).astype(int).to_numpy()
    m = Model("lgbm", FEATURE_SETS["full"]).fit(df.iloc[:60], y[:60])
    acc = ((m.predict_proba(df.iloc[60:]) >= .5) == y[60:]).mean()
    assert acc >= 0.8


def test_metrics_known_case():
    m = E.metrics(np.array([1, 1, 0, 0]), np.array([.9, .4, .2, .6]), np.array([.5] * 4))
    assert m["accuracy"] == .5 and m["precision"] == .5 and m["recall"] == .5
    assert m["auc"] == pytest.approx(0.75)
    assert m["brier"] == pytest.approx((0.01 + 0.36 + 0.04 + 0.36) / 4)
    assert m["brier_skill"] == pytest.approx(1 - m["brier"] / 0.25)


def test_auc_unavailable_with_one_class():
    assert E.metrics(np.array([1, 1]), np.array([.7, .8]))["auc"] is None


def test_max_reliable_lead_is_contiguous():
    s = {1: {"reliability": {"reliable": True}}, 2: {"reliability": {"reliable": False}}, 3: {"reliability": {"reliable": True}}}
    assert E.max_reliable_lead(s) == 1
    assert E.max_reliable_lead({1: {"reliability": {"reliable": False}}}) is None


# ---------------------------------------------------------------- NLP
def test_gate_and_title_normalisation():
    assert N.GATE.search("Presyo ng bigas tumaas")
    assert N.GATE.search("Libu-libong manggagawa nawalan ng trabaho")
    assert not N.GATE.search("Quezon, In Thy Name lead FAMAS awards nominations")
    assert N.norm_title("Rice prices rise - Inquirer.net") == "rice prices rise"


def _toy_cell(n_rel=4, n_irr=0, dup=1):
    rows = []
    for i in range(n_rel):
        for _ in range(dup):
            rows.append({"event_id": i, "ph_date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                         "source_domain": f"s{i % 2}", "relevant": True, "stress": 0.8, "topic_domain": "market",
                         "evidence_type": "risk_factor", **{f"p_{d}": (0.9 if d == "market" else 0.0) for d in N.DOMAINS},
                         **{f"is_{d}": d == "market" for d in N.DOMAINS}})
    for j in range(n_irr):
        rows.append({"event_id": 100 + j, "ph_date": pd.Timestamp("2024-02-01"), "source_domain": "s9", "relevant": False,
                     "stress": 0.0, "topic_domain": "none", "evidence_type": "irrelevant",
                     **{f"p_{d}": 0.0 for d in N.DOMAINS}, **{f"is_{d}": False for d in N.DOMAINS}})
    return pd.DataFrame(rows)


def test_fssi_counts_events_not_repeats():
    a, b = N._cell_fssi(_toy_cell(dup=1)), N._cell_fssi(_toy_cell(dup=5))
    assert a["fssi_raw_market"] == pytest.approx(b["fssi_raw_market"])
    assert b["n_events"] == 4 and b["n_articles"] == 20


def test_fssi_is_a_share_not_a_volume():
    small, big = N._cell_fssi(_toy_cell(n_rel=4)), N._cell_fssi(_toy_cell(n_rel=40))
    assert small["fssi_raw_market"] == pytest.approx(big["fssi_raw_market"])     # more coverage, same score
    diluted = N._cell_fssi(_toy_cell(n_rel=4, n_irr=4))
    assert diluted["fssi_raw_market"] < small["fssi_raw_market"]


# ---------------------------------------------------------------- rankings
def test_all_142_lgus_ranked():
    t = R.rank_lgus(0.6)
    assert len(t) == 142 and t["lgu_psgc"].nunique() == 142
    assert t["poverty_incidence_2021"].notna().all() and t["density_2024"].gt(0).all()
    assert t.groupby("province_name").size().to_dict() == {"Batangas": 34, "Cavite": 23, "Laguna": 30, "Quezon": 41, "Rizal": 14}
    assert t.loc[t["lgu_psgc"] == "045624000", "poverty_source"].iloc[0].startswith("PSA OpenSTAT")
    assert np.allclose(t["priority_score"], 100 * 0.6 * (0.5 * t["pct_poverty"] + 0.5 * t["pct_density"]))
    assert t["rank"].tolist() == list(range(1, 143))


def test_province_priority_and_sensitivity():
    t = R.rank_lgus(0.5)
    p = R.province_priority(t)
    assert len(p) == 5 and p["n_lgus"].sum() == 142
    s = R.sensitivity(t)
    assert set(s["weights"]) >= {"poverty only", "density only"}


# ---------------------------------------------------------------- explanations
def _n_sentences(s: str) -> int:
    return len([x for x in re.split(r"(?<=[.!?])\s+", s.strip()) if x])


@pytest.mark.parametrize("blocks", [{"market": .5, "employment": .2, "climate": -.3}, {"outcome": -.4},
                                    {"market": .01}, {"remittance": .3, "poverty": .25, "outcome": .9}])
def test_sentences_short_plain_and_directional(blocks):
    s = X.sentence(blocks, "2026-Q4")
    assert _n_sentences(s) <= 2
    assert not re.search(r"SHAP|log-odds|feature|LightGBM|z-score", s)
    if blocks.get("climate", 0) < -0.1:
        assert "weather conditions lowered" in s


# ---------------------------------------------------------------- independence
def test_no_firi_dependency():
    for f in FI5_DIR.glob("*.py"):
        src = f.read_text(encoding="utf-8").lower()
        assert not re.search(r"^\s*(from|import)\s+\S*firi", src, re.M), f.name
        assert not re.search(r"firi2?\.(py|json|csv)|firi_history|firi2_reference", src), f.name


# ---------------------------------------------------------------- API (needs pipeline outputs)
@pytest.mark.skipif(not (OUT / "forecast.json").exists(), reason="run python -m app.fi5.pipeline all first")
def test_api_routes_serve_pipeline_files():
    from app.main import app
    c = TestClient(app)
    for path in ["/api/v1/fi5/status", "/api/v1/fi5/forecast", "/api/v1/fi5/evaluation", "/api/v1/fi5/baselines",
                 "/api/v1/fi5/provinces", "/api/v1/fi5/lgus", "/api/v1/fi5/nlp/fssi", "/api/v1/fi5/nlp/topics",
                 "/api/v1/fi5/features"]:
        r = c.get(path)
        assert r.status_code == 200, path
        assert "status" in r.json()
    assert c.get("/api/v1/fi5/lgus").json()["n"] == 142
    assert c.get("/api/v1/fi5/lgus?province=Nowhere").status_code == 404
    f = c.get("/api/v1/fi5/forecast").json()
    assert len(f["forecasts"]) == 4
    for x in f["forecasts"]:
        assert 0 <= x["p_high"] <= 1 and _n_sentences(x["explanation"]) <= 2
