"""
tests/integration/test_e99_chapter3.py
--------------------------------------
E99: the Chapter III pipeline as written (Eq. 3 label, Algorithm 3, Algorithm 4, six comparators) is tied to the
frozen protocol, uses only labels posted before each issue date, finds no reliable lead (k* = 0) and no accepted model;
seals verify and stay PENDING; the evaluation scorer never invents responses; the dashboard (dev branch) no longer
words the price-pressure score or the province estimate as a probability.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

E99 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E99_Chapter3_Evaluation"
RUN = sorted(p for p in (E99 / "runs").iterdir() if (p / "e99_results.json").exists())[-1]
sys.path.insert(0, str(E99 / "runner"))


@pytest.fixture(scope="module")
def r():
    return json.loads((RUN / "e99_results.json").read_text(encoding="utf-8"))


def test_protocol_and_label(r):
    sha = hashlib.sha256((E99 / "PROTOCOL.md").read_bytes()).hexdigest()
    assert (E99 / "PROTOCOL.sha256").read_text().split()[0] == sha == r["protocol_sha256"]
    lab = r["label"]
    assert lab["rows"] == 95 and lab["quarters"] == 19 and lab["is_proxy"]
    assert lab["median"] == pytest.approx(15.4733, abs=1e-3)


def test_training_uses_only_labels_posted_before_issue():
    import chapter3_eval as M
    L, _ = M.labels("all")
    X = M.features()
    for k in (1, 2):
        P = M.pairs(X, L, k)
        for q in sorted(P["q"].unique()):
            tr, te, issue = M.fold_rows(P, q, k)
            assert (tr["posted"] < issue).all() and (tr["q"] <= q - k).all()
    D = pd.read_csv(RUN / "predictions_dev_k2.csv")
    assert (D["train_quarters"] >= 8).all()


def test_algorithm3_and_4_decisions(r):
    assert r["algorithm3"]["k_star"] == 0 and r["S1"]["k_star"] == 0 and r["S2"]["k_star"] == 0
    a3 = r["algorithm3"]["per_k"]["1"]
    assert a3["mean_fold_accuracy"] == pytest.approx(0.30) and a3["arms"]["Persistence"]["mean_fold_accuracy"] == pytest.approx(0.70)
    a4 = r["algorithm4"]["2"]
    assert a4["accepted"] is False and len(a4["trials"]) == 100
    assert a4["final_model_sha256"] == hashlib.sha256((RUN / "lgbm_best_k2.pkl").read_bytes()).hexdigest()
    h = r["hypotheses"]
    assert h["H1"]["rejected"] is False and h["H2"]["rejected"] is False and h["H3"]["rejected_descriptive"] is False
    assert h["H4"].startswith("blocked") and h["H5"].startswith("blocked")


def test_seals_verify_and_are_pending():
    out = subprocess.run([sys.executable, str(E99 / "prospective" / "score_sealed.py")], capture_output=True, text=True,
                         check=True)
    s = json.loads(out.stdout)
    assert s["S-FIRI2"]["verification"]["ok"] and s["S-E99"]["verification"]["ok"]
    assert s["status"].startswith("PENDING")


def test_evaluation_scorer(tmp_path):
    pkg = E99 / "evaluation_package"
    out = subprocess.run([sys.executable, str(pkg / "score_evaluation.py"), str(pkg / "iso_responses_template.csv"),
                          str(pkg / "h4_rankings_template.csv")], capture_output=True, text=True, check=True)
    s = json.loads(out.stdout)
    assert s["iso25010"]["status"] == "NO_RESPONSES" and s["h4"]["status"] == "NO_RESPONSES"
    bad = tmp_path / "bad.csv"                 # export-validation check only (not a response set)
    bad.write_text("respondent_id,agency," + ",".join(f"q{i}" for i in range(1, 16)) + "\nX,DA Regional Field Office IV-A,"
                   + ",".join(["7"] * 15) + "\n", encoding="utf-8")
    out = subprocess.run([sys.executable, str(pkg / "score_evaluation.py"), str(bad), str(pkg / "h4_rankings_template.csv")],
                         capture_output=True, text=True, check=True)
    assert json.loads(out.stdout)["iso25010"]["status"] == "INVALID_EXPORT"


def test_dashboard_wording_not_probability(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-22T10:00:00")
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    txt = json.dumps(c.get("/api/v1/provinces", params={"quarter": "2027-Q1"}).json())
    assert "not a calibrated probability" in txt and "% chance" not in txt and "pressure forecast is" not in txt
    m = c.get("/api/v1/provinces/cavite/municipalities", params={"quarter": "2027-Q1"}).json()["data"][0]
    assert "province probability" not in m.get("rankingMethod", "")
