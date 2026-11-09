"""E178 Part A (docs/e178/PROTOCOL.md): the scenario rules on small frames, and the generated scenario files: S0 equals
production, every row is labelled, probabilities and classes are valid, S3 turns a province HIGH, inputs stay within
historical bounds unless flagged as extrapolated, and the recorded hashes match."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.e151 import prov as Pv
from app.e178 import common as K
from app.e178 import scenarios as S

OUT = K.SYN / "scenarios_outputs.csv"
needs_run = pytest.mark.skipif(not OUT.exists(), reason="python -m app.e178.scenarios run not run")


# ------------------------------------------------------------------------------------------------- rules (no model)
def test_stress_directions_follow_the_model_signs():
    for cols in list(S.GROUPS.values()) + list(S.SHOCKS.values()):
        for c, d in cols.items():
            s = Pv.SIGN.get(c, 0)
            if s:
                assert d == s, c
            else:
                assert c in S.UNSIGNED, c


def _frames(seed=0):
    from app.e168 import lgbm_only as E
    cols = sorted({c for g in S.GROUPS.values() for c in g} | set(E.TRIG[:20]))
    r = np.random.default_rng(seed)
    tr = pd.DataFrame(r.normal(0, 1, (60, len(cols))), columns=cols)
    te = pd.DataFrame(r.normal(0, .5, (5, len(cols))), columns=cols)
    te.iloc[0, 0] = np.nan
    te["gap_q"] = 22
    return tr, te, cols


def test_variants_follow_the_protocol():
    tr, te, cols = _frames()
    V, B = S.build_variants(tr, te)
    by = {v["variant"]: v for v in V}
    assert V[0]["scenario_id"] == "S0" and V[0]["te"][cols].equals(te[cols].astype(float))
    # S1: one SD toward stress, clipped to the historical bounds
    t = by["food_prices:+1SD"]["te"]
    want = np.clip(te["cpi_food_yoy"] + B.at["cpi_food_yoy", "sd"], B.at["cpi_food_yoy", "min"], B.at["cpi_food_yoy", "max"])
    assert np.allclose(t["cpi_food_yoy"], want)
    assert np.allclose(by["remittances:+2SD"]["te"]["remit_yoy"],
                       np.clip(te["remit_yoy"] - 2 * B.at["remit_yoy", "sd"], B.at["remit_yoy", "min"], B.at["remit_yoy", "max"]))
    # S2: the stated share of each row's available trigger cells is missing
    _, trig = S.scenario_columns(te)
    m = by["mask 50% #01"]["te"]
    for r in range(5):
        avail = te.loc[r, trig].notna().sum()
        assert m.loc[r, trig].isna().sum() - te.loc[r, trig].isna().sum() == round(0.5 * avail)
    assert by["all triggers missing"]["te"][trig].isna().all().all()
    # S3: t = 1 reaches the historical extreme in the stress direction; t > 1 is flagged
    t1 = by["combined:t=1"]["te"]
    assert np.allclose(t1["cpi_rice_yoy"], B.at["cpi_rice_yoy", "max"]) and np.allclose(t1["remit_yoy"], B.at["remit_yoy", "min"])
    assert by["combined:t=1.5"]["extrapolated"] and not by["combined:t=1"]["extrapolated"]
    # missing values stay missing in every shifted variant
    first = cols[0]
    assert all(pd.isna(v["te"].at[0, first]) for v in V)


def test_variants_are_reproducible():
    tr, te, _ = _frames()
    a, _ = S.build_variants(tr, te)
    b, _ = S.build_variants(tr, te)
    assert all(x["te"].equals(y["te"]) and x["variant"] == y["variant"] for x, y in zip(a, b))


# ------------------------------------------------------------------------------------------------ generated files
@pytest.fixture(scope="module")
def out():
    return pd.read_csv(OUT)


@needs_run
def test_s0_equals_the_production_issue(out):
    prod = K.production_issue()
    live = {(r["province"], r["lead"]): r for r in prod["live"]["provinces"]}
    s0 = out[out.scenario_id == "S0"]
    assert len(s0) == len(live) == 15
    for _, r in s0.iterrows():
        a = live[(r["province"], int(r["lead"]))]
        assert (a["target_quarter"], a["score_pct"], a["range90_pct"], a["p_high"], a["risk_class"], a["config"]) == \
               (r["quarter"], r["score_pct"], [r["range90_low"], r["range90_high"]], r["probability"], r["class"], r["config"])
    dash = pd.read_csv(prod["dashboard_rows"]).set_index(["province", "lead"])
    shap = [c for c in out.columns if c.startswith("shap_")] + ["baseline_pct", "change_logit", "bias_logit"]
    for _, r in s0.iterrows():
        d = dash.loc[(r.province, r.lead)]
        assert all(abs(float(d[c]) - float(r[c])) <= 1e-9 for c in shap)


@needs_run
def test_every_row_is_labelled(out):
    assert out[out.scenario_id == "S0"].is_synthetic.eq(False).all()
    assert out[out.scenario_id != "S0"].is_synthetic.eq(True).all()
    assert out.scenario_id.notna().all() and set(out.scenario_id) <= {"S0", "S1", "S2", "S3", "S3-B"}
    seeded = out[out.group.isin(["noise", "mask"])]
    assert seeded.generator_seed.notna().all()
    for name in ("scenarios_inputs.csv", "s5_municipal.csv", "s4_dashboard_rows.csv"):
        f = pd.read_csv(K.SYN / name)
        assert {"is_synthetic", "scenario_id"} <= set(f.columns), name
    s5 = pd.read_csv(K.SYN / "s5_municipal.csv")
    assert s5.is_synthetic.all() and s5.note.str.contains("not a municipal forecast").all()
    assert json.loads((K.SYN / "s4_response.json").read_text(encoding="utf-8"))["label"] == K.LABEL
    assert K.SYN.name == "synthetic"


@needs_run
def test_probabilities_and_classes_are_valid(out):
    assert out.p_high_exact.between(0, 1).all() and out.probability.between(0, 1).all()
    assert (out["class"] == np.where(out.p_high_exact >= .5, "HIGH", "LOW")).all()
    assert out.score_pct.between(0, 100).all() and (out.range90_low <= out.score_pct).all() and (out.score_pct <= out.range90_high).all()


@needs_run
def test_a_shock_turns_a_province_high(out):
    s3 = out[out.scenario_id.isin(["S3", "S3-B"]) & (out.lead == 1)]
    assert (s3.p_high_exact >= .5).any()
    s4 = json.loads((K.SYN / "s4_response.json").read_text(encoding="utf-8"))
    assert s4["high_rows"] and s4["alerts"]
    assert all(a["alert_reason"] == "E168_HIGH" and a["evidence"]["p_high"] >= .5 for a in s4["alerts"])


@needs_run
def test_inputs_stay_within_bounds_unless_flagged():
    inp = pd.read_csv(K.SYN / "scenarios_inputs.csv")
    log = [json.loads(x) for x in (K.SYN / "run_log.jsonl").read_text(encoding="utf-8").splitlines()]
    bounds = {e["lead"]: {b["column"]: (b["min"], b["max"]) for b in e["bounds"]} for e in log if e["event"] == "bounds"}
    cols = [c for g in S.GROUPS.values() for c in g]
    inside = inp[~inp.extrapolated & inp.scenario_id.isin(["S1", "S2", "S3"])]
    for lead, g in inside.groupby("lead"):
        for c in cols:
            if c in g and c in bounds[lead]:
                lo, hi = bounds[lead][c]
                v = g[c].dropna()
                assert ((v >= lo - 1e-6) & (v <= hi + 1e-6)).all(), (lead, c)
    ext = inp[inp.extrapolated]
    assert set(ext.scenario_id) <= {"S3", "S3-B"}


@needs_run
def test_recorded_hashes_match():
    h = json.loads((K.SYN / "hashes.json").read_text())
    want = {"scenarios_outputs.csv", "scenarios_inputs.csv", "s5_municipal.csv", "s4_response.json", "s4_dashboard_rows.csv",
            "scenarios_summary.json", "run_log.jsonl"}
    assert {r.rsplit("/", 1)[1] for r in h["outputs"]} == want
    for rel, sha in h["outputs"].items():
        assert K.sha256(K.BACKEND_DIR.parent / rel) == sha, rel
    assert h["production_artifact_sha256"] == K.production_issue()["artifact_sha256"]
