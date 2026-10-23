"""Tests for the simple methodology (E106, branch aipheed/simple-methodology).

They check what the methodology promises: only published information at each origin, distinct Lead-1 / Lead-2
targets, consistent probabilities and classes, every LGU covered, reproducible metrics, the API serving the pipeline's
own record, and untouched sealed artifacts. Run `scripts/run_simple_method.py` first (it writes the files read here).
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.ml import simple_method as S

OUT = S.BACKEND / "data/simple_method"
EXP = S.REPO / "aipheed-backend-aligned/experiments"
pytestmark = pytest.mark.skipif(not (OUT / "evaluation.json").exists(), reason="run scripts/run_simple_method.py first")


def _rec():
    return json.loads((OUT / "record.json").read_text(encoding="utf-8"))


def _eval():
    return json.loads((OUT / "evaluation.json").read_text(encoding="utf-8"))


def test_sws_input_uses_only_rounds_published_before_the_issue():
    for t in S.origins():
        issue = S.issue_of(t)
        for q in S.posted(issue):
            pubs = [pub for qq, _, pub in S.sws_rounds() if S.qi(qq) == q]
            assert pubs and all(p < issue for p in pubs)
    # the 2026-Q3 round (posted 2026-10-14) is not available to the 2026-10-01 issue
    assert S.qi("2026-Q3") not in S.posted(S.issue_of(S.qi("2026-Q3")))


def test_features_use_only_the_previous_cpi_quarter():
    t = S.qi("2025-Q2")
    for p in S.PROVINCES:
        assert S.features(t, p)["F_last"] == S.food_yoy()[(p, t - 1)]
    assert not S.label_known(t, t, needs_sws=False) and S.label_known(t - 1, t, needs_sws=False)


@pytest.mark.parametrize("lead", [1, 2])
def test_training_rows_have_labels_complete_before_the_issue(lead):
    t = S.qi("2025-Q3")
    tr = S.training_rows(t, lead, "target", S.ALL_FEATURES)
    assert len(tr) > 0
    for tp in tr["t"]:
        assert tp + lead <= t - 1 and (tp + lead) in S.posted(S.issue_of(t))


def test_lead1_and_lead2_are_different_horizons():
    t = S.qi("2025-Q1")
    f1, f2 = S.forecast(t, 1), S.forecast(t, 2)
    assert (S.qi(f1["target"]), S.qi(f2["target"])) == (t + 1, t + 2)
    assert f1["training_rows"] != f2["training_rows"] or f1["p_hunger"] != f2["p_hunger"]


def test_record_probabilities_and_classes_are_consistent():
    for lead, f in _rec()["forecasts"].items():
        for v in f["provinces"].values():
            assert abs(v["p_high"] - f["p_hunger"] * v["p_price"]) < 1e-12
            assert v["class"] == ("HIGH" if v["p_high"] >= 0.5 else "LOW")
            if v["SM_B"] is not None:
                assert abs(v["SM_B"] - f["p_hunger"] * v["E56_p_price"]) < 1e-12


def test_every_lgu_has_an_output_or_a_status():
    for f in _rec()["forecasts"].values():
        rows = f["lgu"]["rows"]
        assert len(rows) == 142 and len({r["lgu_code"] for r in rows}) == 142
        assert all(r["risk_index"] is not None or r["limitation"] for r in rows)


def test_evaluation_metrics_reproduce_from_the_saved_rows():
    ev = _eval()
    for lead in ("1", "2", "3"):
        df = pd.read_csv(OUT / f"evaluation_rows_lead{lead}.csv")
        arms = list(ev["leads"][lead]["arms"])
        common = df.dropna(subset=arms)
        assert len(common) == ev["leads"][lead]["rows_common"]
        for a in arms:
            m = ev["leads"][lead]["arms"][a]
            assert abs(np.mean((common[a] - common["y"]) ** 2) - m["brier"]) < 1e-5
            assert abs(np.mean((common[a] >= 0.5).astype(int) == common["y"]) - m["accuracy"]) < 1e-12


def test_forecasts_are_not_constant():
    for lead in ("1", "2"):
        df = pd.read_csv(OUT / f"evaluation_rows_lead{lead}.csv")
        for a in ("SM", "SM_B", "E56"):
            assert df[a].nunique() > 5 and (df[a] >= 0.5).nunique() == 2


def test_api_serves_the_pipeline_record_unchanged():
    from app.main import app
    with TestClient(app) as c:
        assert c.get("/api/v1/simple/forecast").json() == _rec()
        assert c.get("/api/v1/simple/evaluation").json() == _eval()


def test_sealed_artifacts_are_unchanged():
    for f in (EXP / "E102_Market_Access_Forecasting/out/sealed_prospective.csv",
              EXP / "E103_FB2_Verification/out/sealed_addendum.csv",
              EXP / "E63_Lead_Time_Study/sealed/predictions.csv",
              OUT / "sealed_prospective.csv"):
        want = (f.parent / (f.name + ".sha256")).read_text().split()[0]
        assert hashlib.sha256(f.read_bytes()).hexdigest() == want
