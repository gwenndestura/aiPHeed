"""
tests/integration/test_lead2_final.py
-------------------------------------
LEAD2_FINAL: the food-price composition/breadth candidate K1 is scored under a protocol frozen before scoring, its
features read only months published by the cut-off, B0 reproduces P0H4-U, the frozen adoption rule is applied as
written (K1 not adopted, Lead 2 still fails R6), and the served model is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "final.json"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="LEAD2_FINAL results missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


@pytest.fixture(scope="module")
def fv4():
    sys.path.insert(0, str(LT / "runner"))
    import features_v4
    return features_v4


def test_protocol_frozen_and_used(res):
    want = (LT / "runner" / "FINAL_SHA256.txt").read_text().strip()
    assert hashlib.sha256((LT / "PROTOCOL_LEAD2_FINAL.md").read_bytes()).hexdigest() == want == res["protocol_sha256"]


def test_features_read_only_months_published_by_the_cut_off(fv4):
    I, W, _, _ = fv4.load()
    S = pd.read_csv(LT / "data" / "stack_v4.csv", dtype={"province_code": str}, usecols=["t", "province_code", "psa_newest_month"])
    pm = pd.to_datetime(S["psa_newest_month"], format="%Y-%m")
    pairs = set(zip(S["province_code"], pm.dt.year * 12 + pm.dt.month - 1))
    for p, m0 in pairs:
        cut = {k: s[s.index <= m0] for k, s in I.items()}
        a, b = fv4.features(p, int(m0), I, W), fv4.features(p, int(m0), cut, W)
        assert all((x == y) or (pd.isna(x) and pd.isna(y)) for x, y in zip(a, b)), (p, m0)


def test_subgroup_food_index_is_the_model_food_cpi():
    a = pd.read_csv(ROOT / "aipheed-backend-aligned" / "experiments" / "E84_Objective_Continuation" / "data_acquired"
                    / "psa_cpi_subgroups_2021_2026.csv")
    b = pd.read_csv(ROOT / "aipheed-backend-aligned" / "experiments" / "E41_Lead2_Audit" / "data_acquired" / "cpi_index_ACP22.csv")
    a = a[a["Commodity Description"] == "01.1 - FOOD"].assign(ym=lambda d: d["ym"])
    b = b[b["Commodity Description"] == "01.1 - FOOD"].drop_duplicates(["Geolocation", "Year", "Period"])
    b = b.assign(ym=b["Year"].astype(str) + " " + b["Period"], Geolocation=b["Geolocation"].str.strip(". "))
    m = a.merge(b, on=["Geolocation", "ym"])
    assert len(m) >= 5 * 60 and (m["index"] - m["value"]).abs().max() == 0


def test_b0_reproduces_p0h4u_and_rows_are_unchanged(res):
    assert res["b0_reproduction_max_abs"] < 1e-5
    rows = pd.read_csv(LT / "out" / "final_rows.csv")
    assert rows.groupby("lead").size().to_dict() == {1: 70, 2: 65, 3: 60, 4: 55}
    m = res["cands"]["B0"]["leads"]["2"]["metrics"]
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (10, 6, 7, 42)


def test_frozen_rule_applied_as_written(res):
    a = res["adoption"]
    assert a["adopted"] is all(a["rule"].values()) is False
    assert a["FINAL"] == "B0" and a["lead2_reliable"] is False and a["lead2_failed"] == ["R6"]
    k1 = res["cands"]["K1"]["leads"]
    assert "R6" in k1["1"]["failed"] and "R6" in k1["2"]["failed"]
    assert res["cands"]["B0"]["max_reliable_lead"] == 1


def test_subgroup_protocol_frozen_and_k2_not_adopted():
    want = (LT / "runner" / "SUBGROUP_SHA256.txt").read_text().strip()
    assert hashlib.sha256((LT / "PROTOCOL_LEAD2_SUBGROUP.md").read_bytes()).hexdigest() == want
    r = json.loads((LT / "out" / "subgroup_k2.json").read_text())
    assert r["protocol_sha256"] == want and r["cols"][-1] == "K_diff"
    assert r["adoption"]["adopted"] is all(r["adoption"]["rule"].values()) is False
    assert r["adoption"]["FINAL"] == "B0" and r["adoption"]["lead2_failed"] == ["R6"]


def test_no_order_preserving_cut_meets_r6_for_k1():
    d = json.loads((LT / "out" / "subgroup_diag.json").read_text())
    assert d["lead2_low_rows_scored_above_best_missed_K1"] > 0
    assert not any(h["recall"] >= .6 and h["precision"] >= .6 for h in d["headroom_K1"])
    rows = pd.read_csv(LT / "out" / "final_rows.csv")
    g = rows[rows["lead"] == 2]
    for cut in sorted(set(g["K1_p"].round(6))):
        tp = int(((g["K1_p"] >= cut) & (g["y"] == 1)).sum())
        fp = int(((g["K1_p"] >= cut) & (g["y"] == 0)).sum())
        assert not (tp / g["y"].sum() >= .6 and tp / max(1, tp + fp) >= .6), cut


def test_case_audit_covers_every_lead2_error_with_one_cause():
    a = pd.read_csv(LT / "out" / "case_audit.csv")
    rows = pd.read_csv(LT / "out" / "final_rows.csv")
    g = rows[rows["lead"] == 2]
    assert len(a) == int(((g["B0_p"] >= .5).astype(int) != g["y"]).sum()) == 13
    assert set(a["cause"]) <= set("HLRVP") and a["cause"].notna().all()
    assert a["type"].str.startswith("FN").sum() == 7
    # every cut-off falls after the SWS reading it used was published (no later reading enters the audit)
    assert (pd.to_datetime(a["cutoff_issue_date"]) > pd.to_datetime(a["sws_used"].str.extract(r"published (\S+)\)")[0])).all()


def test_rain_screen_frozen_dev_only_and_stops():
    want = (LT / "runner" / "CAUSES_SHA256.txt").read_text().strip()
    assert hashlib.sha256((LT / "PROTOCOL_LEAD2_CAUSES_SCREEN.md").read_bytes()).hexdigest() == want
    r = json.loads((LT / "out" / "rain_screen.json").read_text())
    assert r["protocol_sha256"] == want and r["targets"][1] <= "2024-Q4"
    assert r["proceed_to_candidate"] is False and not any(s["passes"] for s in r["signals"].values())


def test_baseline_p0h4u_unchanged():
    c = pd.read_csv(LT / "out" / "candidates.csv")
    f = pd.read_csv(LT / "out" / "final_rows.csv")
    m = c.merge(f[["t", "lead", "province_code", "B0_p"]], on=["t", "lead", "province_code"])
    assert len(m) == 250 and (m["C0_p"] - m["B0_p"]).abs().max() < 1e-5


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL
