"""FI9-X tests: news-window leakage, past-only scaling, timing, recomputation, production protection, labels, registers."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.fi9 import MODEL
from app.fi9 import prospective as PR
from app.fi9 import quarters as Q
from app.fi9x import OUT
from app.fi9x import newsfeat as NF
from app.paths import BACKEND_DIR


def test_lock_matches_code_and_protocol():
    from app.fi9x.study import _code_sha, _digest
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    assert lock["sha256"] == _digest() and lock["code_sha256"] == _code_sha()


def test_news_features_ignore_anything_published_after_the_cutoff(monkeypatch):
    a, e = NF._load()
    d = pd.Timestamp("2020-06-30")
    base = NF.features([d]).iloc[0]
    fa = a.tail(500).copy().assign(published=d + pd.Timedelta(hours=30))
    fe = e.tail(200).copy().assign(published=d + pd.Timedelta(hours=30), event_id=lambda x: x["event_id"].astype(str) + "_future")
    monkeypatch.setattr(NF, "_load", lambda: (pd.concat([a, fa]), pd.concat([e, fe])))
    poisoned = NF.features([d]).iloc[0]
    for k in base.index:
        assert (pd.isna(base[k]) and pd.isna(poisoned[k])) or base[k] == poisoned[k], k
    early = e.head(50).copy().assign(published=d - pd.Timedelta(days=3), event_id=lambda x: x["event_id"].astype(str) + "_early")
    monkeypatch.setattr(NF, "_load", lambda: (a, pd.concat([e, early])))
    assert not NF.features([d]).iloc[0].equals(base)                     # control: the test can fail


def test_expanding_z_uses_only_earlier_values():
    df = pd.DataFrame({"x": np.arange(20, dtype=float)})
    z1 = NF.expanding_z(df, ["x"])["z_x"]
    df.loc[19, "x"] = 1e6
    z2 = NF.expanding_z(df, ["x"])["z_x"]
    assert z1.iloc[:19].equals(z2.iloc[:19]) and z1.iloc[:8].isna().all()


def test_predictions_timing_and_alignment():
    W = pd.read_csv(OUT / "predictions.csv")
    from app.fi9x.study import ORIGINS
    for o, (timing, lead) in ORIGINS.items():
        g = W[W["origin"] == o]
        iq = pd.to_datetime(g["issue_date"]).map(Q.qi_of)
        assert (g["target_quarter"].map(Q.index) == iq + lead).all(), o
        assert (pd.to_datetime(g["target_published"]) > pd.to_datetime(g["issue_date"])).all(), o
        full = g.groupby("config")["target_quarter"].nunique()
        assert full.max() == 62
    assert not W.duplicated(["origin", "config", "target_quarter"]).any()


def test_metrics_recomputed_independently():
    from app.fi9.audit import _recompute
    W = pd.read_csv(OUT / "predictions.csv")
    E = json.loads((OUT / "evaluation.json").read_text())
    worst = 0.0
    for (o, c), g in W.groupby(["origin", "config"]):
        for k, v in _recompute(g).items():
            rep = E[o]["full"]["models"][c].get(k)
            if v is not None and rep is not None:
                worst = max(worst, abs(v - rep))
    assert worst < 1e-9


def test_no_adoption_means_production_unchanged():
    A = json.loads((OUT / "adoption.json").read_text())
    pin = json.loads((BACKEND_DIR / "data" / "fi9" / "PRODUCTION_PIN.json").read_text())
    art = json.loads((MODEL / "lead1_model.json").read_text())
    assert A["adopted"] == [] and (art["model"], art["kind"], art["sha256"]) == (pin["model"], pin["kind"], pin["artifact_sha256_at_pin"])
    for k, v in A["candidates"].items():
        assert v["adopt"] == all(v["checks"].values()), k


def test_label_integration_numbers():
    L = json.loads((OUT / "label_integration.json").read_text())
    assert L["target_validation"]["calabarzon_fies_2023"] == 19.1
    t = pd.DataFrame(L["provincial"]["table"])
    from scipy.stats import spearmanr
    assert abs(spearmanr(t["hfias2015_mod_sev"], t["poverty2015"]).statistic - L["provincial"]["spearman_vs_hfias2015_mod_sev"]["poverty2015"]) < 1e-12
    assert all(r["verification_status_aipheed"] == "unverified_secondary" for r in L["provincial"]["enns_unverified"])


def test_literature_verified():
    lit = json.loads((OUT / "literature_crossref.json").read_text(encoding="utf-8"))
    assert len(lit) >= 26 and all(v["found"] for v in lit.values())


def test_challenger_register_intact_and_consistent_with_production():
    reg = OUT / "challenger_register.jsonl"
    recs = PR.read(reg)
    assert PR.verify(reg) and len(recs) >= 3
    live = [r for r in recs if r["origin"] == "OP1" and r["target_quarter"] == "2027-Q1"][0]
    served = json.loads((BACKEND_DIR / "data" / "fi9" / "out" / "forecast.json").read_text())
    assert abs(live["models"]["C0 damped persistence (production)"]["p_high"] - served["forecast"]["p_high"]) < 0.006   # served p is rounded


def test_priority_alternatives_reproduce_production_and_validation():
    from scipy.stats import spearmanr
    lg = pd.read_csv(OUT / "priority_alternatives_lgu.csv", dtype={"lgu_psgc": str}).set_index("lgu_psgc")
    prod = pd.read_csv(BACKEND_DIR / "data" / "fi9" / "out" / "lgu_priority.csv", dtype={"lgu_psgc": str}).set_index("lgu_psgc")
    cur = "current (0.5 poverty / 0.5 density)"
    assert len(lg) == 142 and ((lg[f"V | {cur}"] - prod.loc[lg.index, "vulnerability"]).abs() < 1e-4).all()
    pv = pd.read_csv(OUT / "priority_alternatives_province.csv").set_index("province")
    J = json.loads((OUT / "priority_validation.json").read_text())
    for name, v in J["provincial"]["scenarios"].items():
        assert abs(spearmanr(pv[f"score | {name}"], pv["hfias2015_mod_sev"]).statistic - v["mod_sev"]["spearman"]) < 1e-9
    assert all(0 <= x <= 1 for x in lg[f"p_top_third | {cur}"])


def test_api_priority_alternatives_is_separate_from_served_ranking():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    a = c.get("/api/v1/fi9/priority/alternatives").json()
    assert "Comparison only" in a["note"] and len(a["lgus"]) == 142 and len(a["provinces"]) == 5
    assert c.get("/api/v1/fi9/priority/alternatives", params={"province": "Atlantis"}).status_code == 404
    served = c.get("/api/v1/fi9/priority").json()
    assert served["n"] == 142 and "Comparison only" not in served["note"]


def test_served_province_priority_uses_approved_weights_and_lgus_unchanged():
    p = pd.read_csv(BACKEND_DIR / "data" / "fi9" / "out" / "province_priority.csv")
    lg = pd.read_csv(BACKEND_DIR / "data" / "fi9" / "out" / "lgu_priority.csv", dtype={"lgu_psgc": str})
    alt = pd.read_csv(OUT / "priority_alternatives_province.csv").set_index("province")
    assert (p["weights"].str.startswith("province: 0.65 poverty")).all()
    assert list(p["province_name"]) == list(alt["score | moderate (0.65 / 0.35)"].sort_values(ascending=False).index)
    assert (lg["weights"].str.startswith("LGU: 0.5 poverty")).all()
    lalt = pd.read_csv(OUT / "priority_alternatives_lgu.csv", dtype={"lgu_psgc": str}).set_index("lgu_psgc")
    assert ((lg.set_index("lgu_psgc")["vulnerability"] - lalt.loc[lg["lgu_psgc"], "V | current (0.5 poverty / 0.5 density)"].to_numpy()).abs() < 1e-4).all()
    pin = json.loads((BACKEND_DIR / "data" / "fi9" / "PRODUCTION_PIN.json").read_text())
    assert pin["priority_weights"] == {"province": {"poverty": 0.65, "density": 0.35}, "lgu": {"poverty": 0.5, "density": 0.5}}
