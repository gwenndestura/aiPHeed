"""E54 checks: protocol frozen before the scores, poverty inputs and encodings (as-of boundaries, centring, no
pre-2021 value), the audit's claim that no served model's feature list holds a poverty column, reproduction of the
reference models, byte-identical repeats, decisions recomputed from the stored rows, nothing frozen or served.

    backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E54 = Path(__file__).resolve().parents[1]
EXP = E54.parent
ROOT = EXP.parents[1]
sys.path.insert(0, str(E54 / "runner"))
import e54_lib as V  # noqa: E402

C12, C12_REPEAT = (E54 / "runs" / r for r in ("c12_20261017T145258Z", "c12_20261017T145708Z"))
C3, C3_REPEAT = (E54 / "runs" / r for r in ("c3_20261017T145258Z", "c3_20261017T150746Z"))
POVERTY_LIKE = re.compile(r"pov|subsist|sae|poor|kahirapan", re.I)


def _json(p: Path) -> dict:
    return json.loads(p.read_text())


# ---------------------------------------------------------------- protocol and inputs
def test_protocol_frozen_and_used_by_every_run():
    want = (E54 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert V.sha(E54 / "PROTOCOL.md") == want
    for r in (C12, C12_REPEAT, C3, C3_REPEAT):
        assert _json(r / "results.json")["protocol_sha256"] == want


def test_inputs_match_manifest_and_repository_copies():
    got = V.verify_inputs()
    m = _json(E54 / "data" / "MANIFEST.json")
    for f, v in m["files"].items():
        assert got[f] == v["sha256"]
        assert (ROOT / v["source"]).read_bytes() == (E54 / "data" / f).read_bytes()


def test_no_pre_2021_value_and_expected_counts():
    s = pd.read_csv(V.SAE_FILE)
    assert len(s) == 141 and s["poverty_incidence_2021"].notna().sum() == 141
    assert s.groupby("province").size().to_dict() == {"Batangas": 34, "Cavite": 23, "Laguna": 30, "Quezon": 40, "Rizal": 14}
    b = pd.read_csv(V.SUB_FILE)
    assert len(b) == 10 and b["reference_year"].min() == 2021


def test_pov_is_the_unweighted_province_mean():
    s = pd.read_csv(V.SAE_FILE)
    v = V.pov_values()
    assert v[V.BY_NAME["Quezon"]] == pytest.approx(s[s["province"] == "Quezon"]["poverty_incidence_2021"].mean())
    assert round(v[V.BY_NAME["Quezon"]], 2) == 20.30 and round(v[V.BY_NAME["Rizal"]], 2) == 6.89


# ---------------------------------------------------------------- encodings (PROTOCOL sections 1-2)
def test_as_of_boundaries():
    qi = lambda s: int(s[:4]) * 4 + int(s[-1]) - 1  # noqa: E731
    # POV known iff O(t) >= 2025-01-01: O(2024-Q3) = 2024-10-01 unknown, O(2024-Q4) = 2025-01-01 known
    assert all(r["pov"] == 0.0 for r in V.values_at("POV-AS", qi("2024-Q3")).values())
    assert any(r["pov"] != 0.0 for r in V.values_at("POV-AS", qi("2024-Q4")).values())
    # SUB published 2024-08-15: O(2024-Q2) = 2024-07-01 unknown, O(2024-Q3) = 2024-10-01 known (2023 vintage)
    assert all(r["sub"] == 0.0 for r in V.values_at("SUB-AS", qi("2024-Q2")).values())
    sv = V.sub_values()
    k = V.values_at("SUB-AS", qi("2024-Q3"))
    mu = np.mean([sv[(p, 2023)] for p in V.PROVS])
    assert all(k[p]["sub"] == pytest.approx(sv[(p, 2023)] - mu) for p in V.PROVS)
    # look-ahead arms: POV at every origin, SUB 2021 for t in 2021-2022 and 2023 from 2023
    assert any(r["pov"] != 0.0 for r in V.values_at("POV-LA", qi("2021-Q3")).values())
    la = V.values_at("SUB-LA", qi("2022-Q4"))
    mu21 = np.mean([sv[(p, 2021)] for p in V.PROVS])
    assert all(la[p]["sub"] == pytest.approx(sv[(p, 2021)] - mu21) for p in V.PROVS)


@pytest.mark.parametrize("arm", ["POV-AS", "SUB-AS", "POV-LA", "SUB-LA"])
def test_poverty_columns_are_centred_at_every_origin(arm):
    F = V.frame(arm, range(2021 * 4 + 2, 2026 * 4 + 3))
    assert F.notna().all().all()
    assert F.groupby("t")[V.cols(arm)[0]].sum().abs().max() < 1e-12


def test_fe_and_reference_columns():
    assert V.cols("R") == [] and V.values_at("R", 8100) == {p: {} for p in V.PROVS}
    fe = V.values_at("FE", 8100)
    assert all(sum(fe[p].values()) == 1.0 and fe[p][f"prov_{p}"] == 1.0 for p in V.PROVS)


def test_decision_rule():
    m0 = {"balanced_accuracy": 0.75, "recall_HIGH": 0.7, "recall_LOW": 0.8}
    better = {"balanced_accuracy": 0.76, "recall_HIGH": 0.66, "recall_LOW": 0.8}
    assert V.decide(better, m0, {"ci95": [-0.02, -0.001]}, False)["status"] == "IMPROVES"
    assert V.decide(better, m0, {"ci95": [-0.02, 0.001]}, False)["status"] == "NO DEMONSTRATED DIFFERENCE"
    assert V.decide({**better, "recall_HIGH": 0.6}, m0, {"ci95": [-0.02, -0.001]}, False)["status"] != "IMPROVES"
    assert V.decide(m0, m0, {"ci95": [0.001, 0.02]}, False)["status"] == "WORSENS"
    assert V.decide(m0, m0, {"ci95": [0.0, 0.0]}, True)["status"] == "IDENTICAL"


# ---------------------------------------------------------------- the audit's claim, from the model artifacts
def test_no_poverty_column_in_any_served_feature_list():
    e38 = _json(EXP / "E38_Lead2_Diagnosis_Tuning" / "models" / "E38-LGBM-NQ_O2026-10-01_lead2.json")["features"]
    txt = (EXP / "E38_Lead2_Diagnosis_Tuning" / "models" / "E38-LGBM-NQ_O2026-10-01_lead2.txt").read_text()
    names = next(x for x in txt.splitlines() if x.startswith("feature_names=")).split("=", 1)[1].split()
    assert names == e38 == ["H_margin", "H_trend", "D_last", "Dnow", "news_reg", "fssi_v2"]
    i7 = _json(EXP / "E46_Rice_Policy" / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json")["selection_at_origin"]
    assert len(i7["price_features"]) == 30 and len(i7["hunger_features"]) == 12
    for c in e38 + i7["price_features"] + i7["hunger_features"]:
        assert not POVERTY_LIKE.search(c), c
    for rec in ("e46/e46_record.json", "e52/e52_record.json", "e53/e53_record.json"):
        assert "poverty" not in (ROOT / "backend" / "data" / rec).read_text().lower()


def test_poverty_reaches_only_the_ranking_record():
    rec = _json(ROOT / "backend" / "data" / "e36" / "e36_record.json")
    rows = rec["lgu_ranking"]["rows"]
    assert len(rows) == 142 and sum(r["poverty_value_kind"].startswith("PSA municipal") for r in rows) == 141


# ---------------------------------------------------------------- runs
def test_c12_reproduces_references_and_repeats():
    r1, r2 = _json(C12 / "results.json"), _json(C12_REPEAT / "results.json")
    assert all(r1["reproduced"].values())
    for f in ("predictions.csv", "rows_ps.csv", "rows_t43.csv"):
        assert (C12 / f).read_bytes() == (C12_REPEAT / f).read_bytes()
    r1.pop("run_utc"), r2.pop("run_utc")
    assert r1 == r2
    R = pd.read_csv(C12 / "rows_ps.csv")
    assert len(R) == 50 and (R["R_p"] - R["E52PS_p"]).abs().max() < 1e-9


def test_c3_reproduces_e38_and_repeats():
    r1, r2 = _json(C3 / "results.json"), _json(C3_REPEAT / "results.json")
    assert r1["reproduced_committed_E38"] and r1["rows"] == 55 and r1["HIGH"] == 49
    assert (C3 / "predictions.csv").read_bytes() == (C3_REPEAT / "predictions.csv").read_bytes()
    r1.pop("run_utc"), r2.pop("run_utc")
    assert r1 == r2


def _same(a: dict, b: dict) -> bool:
    """Equal within 1e-12 (rows are re-read from CSV; E53 D-2 float tolerance)."""
    return abs(a["diff"] - b["diff"]) < 1e-12 and all(abs(x - y) < 1e-12 for x, y in zip(a["ci95"], b["ci95"]))


def test_decisions_recomputed_from_rows():
    res = _json(C12 / "results.json")
    R = pd.read_csv(C12 / "rows_ps.csv")
    for a in V.ARMS[1:]:
        pb = V.paired_brier(R, a, "R", "target")
        assert _same(pb, res["C1_PS"]["paired_brier_vs_R"][a])
        assert res["C1_PS"]["decision"][a]["status"] == V.decide(
            res["C1_PS"]["metrics"][a], res["C1_PS"]["metrics"]["R"], pb,
            bool((R[f"{a}_p"] - R["R_p"]).abs().max() < 1e-12))["status"]
    S = pd.read_csv(C12 / "rows_t43.csv")
    assert len(S) == 35 and int(S["y"].sum()) == 9
    for a in V.ARMS[1:]:
        assert _same(V.paired_brier(S, a, "R", "target_q"), res["C2_T43"]["S44"]["paired_brier_vs_R"][a])


def test_frozen_only_for_improving_arms_and_nothing_served():
    res = _json(C12 / "results.json")
    want = {f"E54_{c}_{a}_PROSPECTIVE_2027Q1.json" for c, arms in res["improving_arms"].items() for a in arms}
    assert {f.name for f in (E54 / "frozen").glob("*.json")} == want
    lead2 = (ROOT / "backend" / "app" / "ml" / "inference" / "e41_lead2.py").read_text()
    assert "e54" not in lead2.lower() and 'os.getenv("AIPHEED_LEAD2_MODEL", "e38")' in lead2
