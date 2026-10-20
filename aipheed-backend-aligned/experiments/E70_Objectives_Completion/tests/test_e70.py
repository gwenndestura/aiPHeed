"""E70 checks that need no model library: seals, protocol freeze, reproduction of the sealed E63 reference, the
pre-registered decision, the target audit, leakage result and the annotation sample's blindness.

    python -m pytest -q aipheed-backend-aligned/experiments/E70_Objectives_Completion/tests
"""
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd

E70 = Path(__file__).resolve().parents[1]
EXP = E70.parent
SCORE = json.loads((E70 / "out" / "score.json").read_text(encoding="utf-8"))


def _sha(p: Path, lf=False) -> str:
    b = p.read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if lf else b).hexdigest()


def test_protocol_frozen():
    assert _sha(E70 / "PROTOCOL.md", lf=True) == (E70 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]


def test_seals_match():
    for n in ("predictions.csv", "prospective.csv", "ablations.csv"):
        want = (E70 / "sealed" / f"{n}.sha256").read_text().split()[0]
        assert _sha(E70 / "sealed" / n) == want == SCORE["seals"][n]


def test_reference_reproduces_sealed_e63():
    P = pd.read_csv(E70 / "sealed" / "predictions.csv", dtype={"province_code": str})
    S = pd.read_csv(EXP / "E63_Lead_Time_Study" / "sealed" / "predictions.csv", dtype={"province_code": str})
    m = P.merge(S, on=["lead", "origin_quarter", "province_code"])
    assert len(m) == len(P) == 155
    assert (m["R0_p"] - m["E56_p"]).abs().max() < 1e-9
    assert (m["R0_cfg"].astype(int) == m["E56_config"].astype(int)).all()
    assert P.groupby("lead").size().to_dict() == {1: 60, 2: 50, 3: 45}


def test_lead_timing():
    P = pd.read_csv(E70 / "sealed" / "predictions.csv")
    qi = lambda q: int(q[:4]) * 4 + int(q[-1]) - 1  # noqa: E731
    assert ((P["target"].map(qi) - P["origin_quarter"].map(qi)) == P["lead"]).all()
    nxt = P["origin_quarter"].map(qi) + 1
    assert (P["issue_date"] == [f"{n // 4}-{(n % 4) * 3 + 1:02d}-01" for n in nxt]).all()
    assert not P.duplicated(["lead", "target", "province_code"]).any()


def test_prospective_targets_have_no_outcome_yet():
    Q = pd.read_csv(E70 / "sealed" / "prospective.csv")
    assert set(Q["target"]) == {"2026-Q4", "2027-Q1"} and len(Q) == 15
    sealed_at = json.loads((E70 / "sealed" / "meta_main.json").read_text())["sealed_at_utc"][:10]
    sws = pd.read_csv(EXP.parents[1] / "backend" / "data" / "inputs" / "sws_rounds.csv")
    later = sws[sws["quarter"].isin(["2026-Q4", "2027-Q1"])]
    assert (later["published"].astype(str).str[:10] > sealed_at).all()   # any outcome round came after the seal


def test_target_is_price_dominated_and_disclosed():
    for lead, d in SCORE["target_audit"]["by_lead"].items():
        assert d["T43_equals_PS"] == d["rows"] and d["hunger_binding_rows"] == 0
        assert all(v["T43_equals_PS"] == d["rows"] for v in d["threshold_sensitivity"].values())


def test_decision_rule_applied_as_registered():
    L2 = SCORE["leads"]["2"]
    for a in ("A1", "A2"):
        c = SCORE["decision"]["rule1"][a]["criteria"]
        p = L2["paired"][f"{a} vs R0"]
        assert c["brier_ci_upper_below_0"] == (p["ci95"][1] < 0)
        assert c["holm_sign_p_below_0.05"] == (p["holm_p"] < 0.05)
        assert SCORE["decision"]["rule1"][a]["passes"] == all(c.values())
    g = SCORE["decision"]["goal_80"]
    m = L2["metrics"][g["selected_arm"]]
    assert g["met"] == (m["accuracy"] >= 0.80 and m["recall_HIGH"] >= 0.5 and m["balanced_accuracy"] >= 0.70)
    assert g["met"] is False                        # the honest outcome of E70; change only with new evidence


def test_leakage_corruption_passes():
    lk = json.loads((E70 / "out" / "leak.json").read_text())
    assert lk["all_pass"] and len(lk["rows"]) == 3


def test_annotation_sample_is_blind():
    rows = list(csv.DictReader((E70 / "annotation" / "HUMAN_ANNOTATION_SAMPLE.csv").open(encoding="utf-8")))
    assert len(rows) == 300
    assert not {"model_relevant", "model_trigger", "stratum", "model_province"} & set(rows[0])
    assert all(r["human_relevant"] == "" for r in rows)           # Claude does not fill human labels
