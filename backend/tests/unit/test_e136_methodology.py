"""
tests/unit/test_e136_methodology.py
-----------------------------------
E136 (methodology review): frozen protocol, write-once seal, references reproduce E135, the fixed damped trend
uses only published values, the recommendation rule applied as frozen, and the reported outcome.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E136_Methodology_Review"
pytestmark = pytest.mark.skipif(not (E / "out" / "e136_metrics.csv").exists(), reason="E136 outputs not built")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_protocol_and_seal():
    assert (E / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0] == _sha(E / "E136_FROZEN_PROTOCOL.md")
    h, name = (E / "sealed" / "E136_SEAL_SHA256.txt").read_text().split()
    assert _sha(E / "sealed" / name) == h
    r = subprocess.run([sys.executable, "-I", "-B", str(E / "runner" / "e136_seal.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "refusing to overwrite" in (r.stdout + r.stderr)


def test_references_and_trend():
    P = pd.read_csv(E / "out" / "e136_predictions.csv")
    old = pd.read_csv(REPO / "aipheed-backend-aligned" / "experiments" / "E135_Feature_Influence" / "out" / "e135_predictions.csv")
    for c in ("f_HFM-X", "f_SEAS-LLM", "f_X-RED", "f_PERSIST"):
        assert np.nanmax(np.abs(P[c] - old[c])) < 1e-9
    assert np.nanmax(np.abs(P["f_TREND-D"] - P["f_PERSIST"])) > 0
    m = P["n_obs"] == 1
    assert np.allclose(P.loc[m, "f_TREND-D"], P.loc[m, "f_PERSIST"])


def test_recommendation_rule_as_frozen():
    T = pd.read_csv(E / "out" / "e136_recommendation_table.csv").set_index("model")
    s = json.loads((E / "out" / "e136_summary.json").read_text())
    p = T.loc["PERSIST"]
    el = T[(T.su_mae < p.su_mae) & (T.se_mae < p.se_mae) & (T.index != "PERSIST")].copy()
    assert set(el.index) == set(s["eligible_order"])
    el["r"] = (el.su_within.rank(ascending=False) + el.se_within.rank(ascending=False)) / 2
    best = el.sort_values(["r", "params", "su_mae"]).index[0]
    assert best == s["recommended"] == "SEAS-LLM"
    assert s["maximum_reliable_lead_any"] == [] and not s["any_within_75"]
    assert "RIDGE-ALL" not in el.index and "LGBM-ALL" not in el.index


def _load(name: str):
    import importlib.util
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location(name, E / "runner" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_addendum2_scorer_covers_primary_and_challengers(tmp_path):
    assert (E.parent / "E134_Information_Bottleneck" / "E134_ADDENDUM_2_AMENDED_PRIMARY.md").exists()
    sc = _load("score_e136")
    F = sc.forecasts()
    assert set(F["model"]) == {"SEAS-LLM", "SIMPLE", "HFM-X"} and (F["issue"] == "2026-11-01").all()
    rounds = tmp_path / "r.csv"
    pd.DataFrame([{"quarter": "2026-Q4", "fieldwork": "2026-12-01/2026-12-05", "published": "2027-01-20",
                   "respondent_base": "adults", "commissioned": False, "national": 22.0, "metro_manila": 25.0,
                   "balance_luzon": 22.0, "visayas": 20.0, "mindanao": 23.0, "bl_n": 600, "area_moe_bl": 4,
                   "area_moe_other": 6, "source_type": "test", "source": "test"}]).to_csv(rounds, index=False)
    S, summ = sc.score(F, rounds)
    assert len(S) == 12 and "primary only" in summ["criterion"]
    assert ((S["f"] - S["y"]).abs() <= S["tolerance_primary"]).equals(S["within_primary"])


def test_reissue_reproduces_seals_without_new_data():
    from datetime import date
    Q = _load("e136_reissue")
    d = Q.reissue(date(2027, 1, 1))
    s = pd.read_csv(E / "sealed" / "E136_PROSPECTIVE_SEAL.csv")
    e = pd.read_csv(E.parent / "E132_Final_Methodology" / "sealed" / "E132_PROSPECTIVE_SEAL.csv")
    m = d.merge(s[["area", "target", "SIMPLE"]], on=["area", "target"], suffixes=("", "_s")) \
         .merge(e[["area", "target", "SEAS-LLM"]], on=["area", "target"], suffixes=("", "_e"))
    assert len(m) == 12
    assert np.allclose(m["SIMPLE"], m["SIMPLE_s"]) and np.allclose(m["SEAS-LLM"], m["SEAS-LLM_e"])
    assert not (E / "sealed" / "E136_REISSUE_2027-Q1.csv").exists()
