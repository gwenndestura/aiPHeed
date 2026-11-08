"""Locks the reported results to the saved out-of-sample forecasts (no refitting) and checks every seal."""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
A = json.loads((D / "final_audit" / "out" / "audit.json").read_text())


def _acc(path_mu, arm, lead, files):
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    a = pd.concat([pd.read_csv(D / f) for f in files])
    a = a[(a["mode"] == "main") & (a["lead"] == lead)]
    x = G[G["lead"] == lead].merge(a, on=["key", "survey", "lead"])
    return len(x), float(((x["p"] >= .5) == (x["y_high"] == 1)).mean())


@pytest.mark.parametrize("arm,lead,acc,brier", [("E158", 1, 0.736, 0.1344), ("E166", 1, 0.764, 0.1247), ("E166", 2, 0.792, 0.1246), ("E167", 1, 0.667, 0.1562), ("PERS", 1, 0.625, 0.2128)])
def test_reported_metrics_reproduce(arm, lead, acc, brier):
    m = A["leads"][str(lead)][arm]
    assert m["n"] == 72
    assert m["accuracy"] == pytest.approx(acc, abs=1e-3)
    assert m["brier"] == pytest.approx(brier, abs=1e-4)


def test_e166_saved_rows_match_audit():
    n, acc = _acc("mu", "E166", 1, ["e166/out/all_rows.csv"])
    assert n == 72 and acc == pytest.approx(0.764, abs=1e-3)


def test_max_reliable_lead_is_zero_for_every_model():
    m = json.loads((D / "e156" / "out" / "max_lead_all.json").read_text())
    assert m and all(v["maximum_reliable_lead"] == 0 for v in m.values())
    h = json.loads((D / "e166" / "out" / "lead_horizon.json").read_text())
    assert h["maximum_reliable_lead"] == 0 and h["skill_horizon_beats_persistence_C2"] == 6


def test_c4_definition_is_logit_level_slope_and_fails():
    for arm in ("E158", "E166"):
        lo, hi = A["leads"]["1"][arm]["C4_slope_ci95"]
        assert not (lo <= 1 <= hi)
        assert A["e156_reliability_lead1"][arm]["C4"] is False


@pytest.mark.parametrize("path,prefix", [("e158/out/sealed_2027-Q1.json", "f69e7a02"), ("e163/out/sealed_2027-Q1.json", "343d1f06"), ("e164/out/sealed_2027-Q1.json", "cbfb61dc"),
                                         ("e166/out/sealed_enns2022.json", "49e514d2")])
def test_seals_intact(path, prefix):
    assert hashlib.sha256((D / path).read_bytes()).hexdigest().startswith(prefix)


def test_e168_lightgbm_only_results():
    r = json.loads((D / "e168" / "out" / "results.json").read_text())
    l1 = r["leads"]["1"]["class"]["E168"]
    assert l1["accuracy"] == pytest.approx(0.75, abs=1e-3) and l1["brier"] == pytest.approx(0.123, abs=1e-3)
    assert r["leakage_max_abs_change"] < 1e-9
    assert r["decision"] == "IMPROVED BUT NOT ACCEPTED"
    assert not l1["E156"]["C1"] and not l1["E156"]["C4"]
    m = json.loads((D / "e156" / "out" / "max_lead_all.json").read_text())
    assert m["E168_LightGBM_only"]["maximum_reliable_lead"] == 0


def test_e170_locked_protocol_results_and_seals():
    r = json.loads((D / "e170" / "out" / "results.json").read_text())
    l1 = r["leads"]["1"]
    assert l1["rows"] == 72 and l1["correct"] == 47
    assert l1["criteria"]["C4"] and not l1["criteria"]["C1"]
    assert r["leakage_max_abs_change"] < 1e-9
    assert r["decision"] == "NOT ACCEPTED" and r["maximum_reliable_lead"] == 0
    for path, prefix in (("e170/out/sealed_enns2022.json", "af0180af"), ("e170/out/sealed_2027-Q1.json", "df03d885")):
        assert hashlib.sha256((D / path).read_bytes()).hexdigest().startswith(prefix)


def test_e168_enns2022_seal_intact():
    assert hashlib.sha256((D / "e168" / "out" / "sealed_enns2022.json").read_bytes()).hexdigest().startswith("f8228fae")


def test_e171_results_and_seals():
    r = json.loads((D / "e171" / "out" / "results.json").read_text())
    l1 = r["leads"]["1"]
    assert l1["rows"] == 72 and l1["correct"] == 52
    assert not l1["criteria_E156_original"]["C1"] and not l1["criteria_E156_original"]["C4"]
    assert l1["criteria_new_rule"]["C4"] is None          # not evaluable without >= 40 new rows
    assert r["leakage_max_abs_change"] < 1e-9 and r["decision"] == "NOT ACCEPTED"
    for path, prefix in (("e171/out/sealed_enns2022.json", "a929929a"), ("e171/out/sealed_2027-Q1.json", "1559746c")):
        assert hashlib.sha256((D / path).read_bytes()).hexdigest().startswith(prefix)


def test_e168_lead_horizon_and_owner_approval():
    h = json.loads((D / "e168" / "out" / "lead_horizon.json").read_text())
    assert h["horizon_75pct_and_beats_persistence"] == 3 and h["skill_horizon_beats_persistence"] == 6 and h["maximum_reliable_lead_E156"] == 0
    assert [h["leads"][str(k)]["correct"] for k in (1, 2, 3)] == [54, 56, 54]
    from app import registry as R
    p = R.production()
    g = R.load()["models"][p["model_id"]]["gate"]
    assert p["model_id"] == "e168-lgbm-1.0" and g["passed"] and "NOT the E156" in g["basis"] and g["served_leads"] == [1, 2, 3]
