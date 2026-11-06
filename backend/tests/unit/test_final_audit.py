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
