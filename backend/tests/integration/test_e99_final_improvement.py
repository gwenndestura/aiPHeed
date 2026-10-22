"""
tests/integration/test_e99_final_improvement.py
-----------------------------------------------
E99 (final improvement): tied to the frozen protocol; SWS and OCTA disagree on the class in most common quarters (the
regional outcome is survey-specific); smoothed persistence does not beat FIRI v2 (nothing promoted); no provincial
food-insecurity module in the PSA PUF; the Lucena substitute is not Lucena's own estimate and does not enter FIRI;
thesis-mode texts never present the price score, FIRI or an LGU index as a probability; the evaluation scorers apply
their eligibility rules and never invent results; the sealed forecasts verify and stay PENDING; the served model
artifacts are the production ones; the release gate is recorded as FAILED.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

E99 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E99_Final_Improvement"


def _load(rel: str):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, E99 / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _latest(suffix: str, name: str) -> dict:
    d = sorted(p for p in (E99 / "runs").iterdir() if p.is_dir() and p.name.endswith(suffix))[-1]
    return json.loads((d / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fe():
    return _latest("_forecast", "forecast_evidence.json")


@pytest.fixture(scope="module")
def prov():
    return _latest("_provincial", "provincial_lucena.json")


def test_protocol(fe, prov):
    sha = hashlib.sha256((E99 / "PROTOCOL.md").read_bytes()).hexdigest()
    assert (E99 / "PROTOCOL.sha256").read_text().split()[0] == sha == fe["protocol_sha256"] == prov["protocol_sha256"]


def test_outcome_is_survey_specific(fe):
    q = fe["Q1"]["octa_gt_11.0"]
    assert q["common_quarters"] == 7 and q["class_agreement"] == 3 and q["survey_specific"]
    assert q["cohen_kappa"] == pytest.approx(0.0)
    assert q["disagreeing_quarters"] == ["2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3"]


def test_smoothed_persistence_does_not_replace_firi(fe):
    m2 = fe["leads"]["2"]["metrics"]
    assert m2["FIRI"]["accuracy"] == pytest.approx(14 / 15)
    assert m2["MA2"]["accuracy"] == pytest.approx(12 / 15) and m2["MA2"]["accuracy"] < m2["FIRI"]["accuracy"]
    tr = fe["leads"]["2"]["regime_split"]["transition"]
    assert tr["FIRI"] == [4, 5] and tr["H1"] == [1, 5]


def test_no_provincial_food_insecurity_module_and_lucena(prov):
    for y in ("2021", "2023"):
        assert prov["puf"][y]["food_insecurity_experience_columns"] == []
    L = prov["lucena"]
    assert L["lucena_in_2021_table"] is False and L["served_substitute"] == 16.8
    assert L["lucena_own_sae"]["2018"] == pytest.approx(6.5)
    assert L["rank_in_quezon"] == {"served": 1, "with_own_2018_sae": 14}
    assert L["firi_v1_uses_substitute"] is False


def test_score_text_rewrites_stored_percentages():
    from app.ml.inference import thesis_system as T
    s = "No price-score early warning: food-price pressure 4%, price-score HIGH-risk probability 11%."
    assert T.score_text(s) == "No price-score early warning: food-price pressure 0.04, price-score HIGH-risk score 0.11."


PATTERNS = _load("runner/label_audit.py").PATTERNS


@pytest.fixture()
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-22T10:00:00")
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)
    elif isinstance(o, str):
        yield o


@pytest.mark.parametrize("url", [
    "/api/v1/provinces?quarter=2027-Q1", "/api/v1/provinces?quarter=2024-Q2",
    "/api/v1/provinces/quezon/municipalities?quarter=2027-Q1",
    "/api/v1/explainability?scope=province&id=batangas&quarter=2027-Q1",
    "/api/v1/forecast?scope=province&id=laguna&quarter=2027-Q1",
])
def test_thesis_texts_have_no_probability_wording(thesis, url):
    r = thesis.get(url)
    assert r.status_code == 200
    bad = [(n, s[:120]) for s in _strings(r.json()) for n, rx in PATTERNS.items() if rx.search(s)]
    assert bad == []


def test_price_score_is_a_0_1_score_in_the_province_row(thesis):
    j = thesis.get("/api/v1/provinces", params={"quarter": "2027-Q1"}).json()
    for p in j["data"]:
        assert re.search(r"food-price-pressure score is \d\.\d\d \(0-1; not a calibrated probability\)", p["confidenceStatement"])


def test_iso_v2_eligibility(tmp_path):
    S = _load("evaluation/score_iso25010_v2.py")
    hdr = S.REQUIRED
    rows = [dict(zip(hdr, ["r1", "2027-01-10", "DA RFO IV-A", "PMED", "yes"] + ["4"] * 15)),
            dict(zip(hdr, ["r1", "2027-01-10", "DA RFO IV-A", "PMED", "yes"] + ["4"] * 15)),      # duplicate id
            dict(zip(hdr, ["r2", "2027-01-10", "DSWD IV-A", "x", "yes"] + ["5"] * 15)),           # not DA
            dict(zip(hdr, ["r3", "2027-01-10", "Department of Agriculture Region IV-A", "x", "no"] + ["5"] * 15)),
            dict(zip(hdr, ["r4", "2027-01-10", "DA Region IV-A", "x", "yes"] + ["6"] + ["3"] * 14))]  # out of range
    f = tmp_path / "r.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        w.writeheader()
        w.writerows(rows)
    out = S.score(f)
    assert out["eligible"] == 1 and out["status"] == "PARTIAL" and out["h5_decision"].startswith("not decidable")
    assert sorted(x["reason"][:2] for x in out["excluded"]) == ["E1", "E2", "E3", "E4"]
    assert S.score(E99 / "evaluation" / "iso_responses_template.csv")["status"] == "NO_RESPONSES"


def test_h4_sets_and_scorer(tmp_path):
    H = _load("evaluation/h4_ranking.py")
    sets = list(csv.DictReader(open(H.SETS, encoding="utf-8")))
    assert len(sets) == 30 and {r["province"] for r in sets} == {"Batangas", "Cavite", "Laguna", "Quezon", "Rizal"}
    assert H.score(E99 / "evaluation" / "h4_responses_template.csv")["status"] == "NO_RESPONSES"
    q = [r for r in sets if r["province"] == "Rizal"]
    f = tmp_path / "h.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["respondent_id", "agency", "consent", "province", "lgu_code", "evaluator_rank"])
        for i in range(3):
            for r in q:
                w.writerow([f"e{i}", "DA RFO IV-A", "yes", "Rizal", r["lgu_code"], r["aipheed_rank_in_province"]])
    out = H.score(f)
    assert out["eligible_evaluators"] == 3 and out["status"] == "INSUFFICIENT"


def test_sealed_forecasts_verify_and_are_pending():
    S = _load("prospective/score_sealed.py")
    assert S.verify()
    out = S.score()
    assert out["scored"] == 0 and all(v["status"].startswith("PENDING") for v in out["targets"].values())
    assert out["targets"]["2026-Q4"]["forecast"] == "HIGH" and out["independent_quarters_needed_for_75pct_claim"] == 12


def test_model_artifacts_are_the_production_ones():
    M = _load("runner/manifest.py")
    r = M.main()
    assert r["artifacts_identical_to_production"] and r["artifacts_identical_to_e98"]
    assert set(r["code_changed_vs_e98"]) == {"app/ml/inference/thesis_system.py", "app/services/dashboard.py",
                                             "app/quarterly/lgu_audit.py"}


def test_release_gate_recorded_failed():
    g = json.loads((E99 / "release_gate.json").read_text(encoding="utf-8"))
    assert g["deploy"] is False
    assert {"G1", "G2", "G4", "G9"} <= {c["id"] for c in g["criteria"] if c["status"] != "PASS"}
