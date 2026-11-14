"""FINAL (RATE + MIND), app.hcw.final_engine: experimental, not served.
1. The backend module must reproduce the research predictions that were scored against the seven rules (to 1e-9).
2. It must not be wired into serving or the registry.
3. Missing-value flags must be built from inputs only.
Needs the research fold tables (AIPHEED_FINAL_RESEARCH_DIR, default: research_notes of the aipheed_final worktree); skipped when absent."""
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RN = Path(os.getenv("AIPHEED_FINAL_RESEARCH_DIR", r"C:\Users\admin\aipheed_final\research_notes"))
CACHE = RN / "aiPHeed_objective_completion_20261111" / "cache"
PARTS = RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd"
BACKEND = Path(__file__).resolve().parents[2]
CASES = [("ENNS2018", 1, 168), ("ENNS2021", 1, 1), ("ENNS2019", 2, 3)]


def _load(survey, lead):
    """Same construction as the research runner (as-of local price panel, added input groups)."""
    from app.hcw import engine as H
    o = pickle.load(open(CACHE / f"{survey}_{lead}.pkl", "rb"))
    tr, te, AN = o["tr"], o["te"], o["AN"]
    L = pd.read_parquet(CACHE / "local_panel_asof.parquet")
    lc = [c for c in L.columns if c not in ("key", "qi") and c in tr.columns]
    tr = tr.drop(columns=lc).merge(L[["key", "qi"] + lc].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.drop(columns=lc).merge(L[["key", "qi"] + lc].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    cp = pd.read_parquet(CACHE / "cand_panel.parquet")
    new = [c for c in H.ADD if c in cp and c not in tr]
    tr = tr.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    return tr, te, AN


@pytest.mark.skipif(not (CACHE.exists() and PARTS.exists()), reason="research fold tables not available")
@pytest.mark.parametrize("survey,lead,seed", CASES)
def test_final_engine_reproduces_scored_research_predictions(survey, lead, seed):
    from app.hcw import final_engine as FE
    tr, te, AN = _load(survey, lead)
    out = FE.fit_predict(tr, te, AN, seed)
    saved = pd.read_csv(PARTS / f"FINAL__{survey}__{lead}__{seed}.csv")
    got = te.reset_index(drop=True)[["key"]].assign(p=out["p"], mu=out["mu"]).merge(saved[["key", "p", "mu"]], on="key", suffixes=("", "_saved"))
    assert len(got) == len(te) == len(saved)
    assert np.abs(got["p"] - got["p_saved"]).max() < 1e-9
    assert np.abs(got["mu"] - got["mu_saved"]).max() < 1e-9
    assert out["version"].endswith("experimental") and ((out["p"] >= 0) & (out["p"] <= 1)).all()


@pytest.mark.legacy_served
def test_final_engine_is_not_wired_into_serving_or_registry():
    for rel in ("app/hcw/serve.py", "app/hcw/make_system.py", "app/ml/inference/map_engine.py", "app/api/v1/registry.py", "app/main.py"):
        p = BACKEND / rel
        if p.exists():
            assert "final_engine" not in p.read_text(encoding="utf-8", errors="ignore"), rel
    reg = BACKEND / "data" / "registry" / "registry.json"
    if reg.exists():
        assert "final-rate-mind" not in reg.read_text(encoding="utf-8", errors="ignore")


def test_missing_flags_use_inputs_only_and_leave_values_untouched():
    from app.hcw import final_engine as FE
    tr = pd.DataFrame({"a": [1.0, np.nan, 3.0, 4.0], "b": [1.0, 2.0, 3.0, 4.0], "c": [np.nan] * 4, "y_true": [0.1, -0.2, 0.3, np.nan]})
    te = pd.DataFrame({"a": [np.nan, 2.0], "b": [np.nan, 1.0], "c": [np.nan, np.nan]})
    tr2, te2, FS, gappy = FE.add_missing_flags(tr, te, {"S": ["a", "b", "c"]})
    assert gappy == ["a"]                                    # b has no training gap; c is empty in training
    assert FS["S"] == ["a", "b", "c", "mi_a"]
    assert tr2["mi_a"].tolist() == [0.0, 1.0, 0.0, 0.0] and te2["mi_a"].tolist() == [1.0, 0.0]
    assert tr2["a"].isna().sum() == 1 and "mi_b" not in te2 and "mi_y_true" not in tr2
