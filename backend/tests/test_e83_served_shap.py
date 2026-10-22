"""E83: the explanation served for each province is the deployed model's own exact TreeSHAP decomposition.

Independently of the serving code, reload the deployed artifacts (booster, inference features, structural offset), recompute
the forecast and its contributions, and compare with the served record: same model version (artifact hashes), same
target quarter, same province, same probability, same grouped contributions, and log-odds additivity.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

lgb = pytest.importorskip("lightgbm")
from scipy.stats import multivariate_normal  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "data" / "e56" / "model"
RECORD = ROOT / "data" / "e58" / "e58_record.json"


@pytest.fixture(scope="module")
def served():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    b = lgb.Booster(model_file=str(MODEL / "booster.txt"))
    names = b.feature_name()
    F = pd.read_csv(MODEL / f"features_{rec['targetQuarter'].replace('-', '')}.csv",
                    dtype={"province_code": str}).set_index("province_code")
    off = json.loads((MODEL / "offset.json").read_text())
    groups = {f["name"]: f["group"] for f in json.loads((MODEL / "feature_schema.json").read_text())["features"]}
    return rec, b, names, F, off, groups


def test_artifacts_are_the_recorded_model_version(served):
    rec = served[0]
    for name, sha in rec["finalModelArtifacts"].items():
        data = (MODEL / name).read_bytes()
        got = {hashlib.sha256(data).hexdigest(), hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()}
        assert sha in got, name


def test_treeshap_is_additive(served):
    _, b, names, F, _, _ = served
    X = F[names].astype(float)
    assert np.abs(b.predict(X, pred_contrib=True).sum(axis=1) - b.predict(X, raw_score=True)).max() < 1e-9


def test_probability_and_contributions_match_record(served):
    rec, b, names, F, off, groups = served
    X = F[names].astype(float)
    raw = b.predict(X, raw_score=True)
    C = b.predict(X, pred_contrib=True)[:, :-1]
    rho = off["error_correlation"]
    assert set(rec["provinces"]) == set(F.index)
    for i, p in enumerate(X.index):
        v = rec["provinces"][p]
        assert v["forecast"]["targetQuarter"] == rec["targetQuarter"] and v["provinceCode"] == p
        z = [(off["threshold_food"][p] - F.loc[p, "base_0.0"]) / off["food_rmse"],
             (off["threshold_gap"][p] - F.loc[p, "gbase_0.0"]) / off["gap_rmse"]]
        ps = 1 - multivariate_normal(mean=[0, 0], cov=[[1, rho], [rho, 1]]).cdf(z)
        init = float(np.clip(math.log(ps / (1 - ps)), -off["logit_clip"], off["logit_clip"]))
        logit = init + raw[i] - off["tree_mean_constant"]
        p_price = 1 / (1 + math.exp(-logit))
        comp = v["forecast"]["components"]
        assert abs(p_price - comp["probabilityPricePressure"]) < 5e-4
        assert abs(p_price * comp["probabilityHungerElevated"] - v["forecast"]["probability"]) < 5e-4
        eff = {g: d["logOddsEffect"] for g, d in v["fiveTriggerContributions"].items()}
        # non-market groups = the booster's own TreeSHAP sums for that group's features
        for g in ("climate", "fish_kill", "employment", "ofw_remittance"):
            mine = sum(C[i, j] for j, n in enumerate(names) if groups.get(n) == g)
            assert abs(mine - eff[g]) < 5e-4, (p, g)
        # log-odds additivity of the served bars: baseline + groups + other = logit(price probability)
        total = v["baselineLogOdds"] + sum(eff.values()) + v["otherContribution"]["logOddsEffect"] + \
            v["povertyContribution"]["logOddsEffect"]
        assert abs(total - logit) < 5e-3, p
