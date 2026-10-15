"""Local validation (section F) and two-layer reporting (section G). SYNTHETIC data only."""
import numpy as np
import pandas as pd
import pytest

import _paths  # noqa: F401
from app.quarterly import local_validation as LV
from app.quarterly import pcf_engine as PE

PROVS = PE.PROVINCES


# ---------------------------------------------------------------------------------------------- local validation
def lgu_table(seed, signal):
    rng = np.random.default_rng(seed)
    n = 142
    prov = np.repeat(PROVS, [30, 30, 40, 14, 28])
    dens, pov = rng.normal(size=n), rng.normal(size=n)
    risk = 0.5 * dens + 0.5 * pov
    out = signal * pov + rng.normal(size=n)              # the synthetic outcome follows poverty only
    return pd.DataFrame({"lgu_code": [f"04{i:07d}" for i in range(n)], "province_code": prov, "density": dens,
                         "poverty_value_used": pov, "risk_index": risk, "fies": out}).set_index("lgu_code")


def test_agreement_detects_a_real_ordering_and_attributes_it():
    t = lgu_table(1, signal=2.0)
    res = LV.attribution(t, "fies")
    assert res["poverty_only"]["spearman"] > res["aiPHeed_risk_index"]["spearman"] > res["density_only"]["spearman"]
    lo, hi = res["aiPHeed_risk_index"]["spearman_ci95"]
    assert lo > 0
    assert res["density_only"]["spearman_ci95"][0] < 0 < res["density_only"]["spearman_ci95"][1]
    assert set(res["aiPHeed_risk_index"]["within_province_spearman"]) == set(PROVS)
    assert res["poverty_only"]["top_third_agreement"] > 1 / 3


def test_agreement_ci_has_nominal_coverage_without_signal_and_refuses_tiny_samples(monkeypatch):
    """Coverage, not one draw: a single null data set excludes 0 about 5% of the time by design (E26 BUG_FIXES T1)."""
    monkeypatch.setattr(LV, "N_BOOT", 400)
    excl = 0
    for seed in range(100):
        t = lgu_table(100 + seed, signal=0.0)
        lo, hi = LV.agreement(t["risk_index"], t["fies"])["spearman_ci95"]
        excl += not (lo < 0 < hi)
    assert excl <= 12                                    # binomial(100, 0.05): mean 5, P(> 12) < 0.002
    t = lgu_table(2, signal=0.0)
    with pytest.raises(ValueError, match="fewer than 5"):
        LV.agreement(t["risk_index"].iloc[:4], t["fies"].iloc[:4])


# ---------------------------------------------------------------------------------------------- two layers
def synthetic_inputs(seed=0):
    rng = np.random.default_rng(seed)
    qq = [PE.qs(i) for i in range(PE.qk("2021-Q1"), PE.qk("2026-Q2") + 1)]
    rounds = pd.DataFrame([{"quarter": q, "fieldwork_quarter": q, "round": q, "H": 14 + rng.normal(),
                            "published": str((pd.Timestamp(q[:4] + "-01-01") + pd.DateOffset(months=3 * int(q[-1]))).date()),
                            "published_eff": str((pd.Timestamp(q[:4] + "-01-01") + pd.DateOffset(months=3 * int(q[-1]))).date()),
                            "date_type": "verified", "definition_A": True, "source": "production"} for q in qq])
    Dm, Nm, s1 = {}, {}, []
    for q in qq:
        d = rng.normal(size=5)
        d -= d.mean()
        for p, v in zip(PROVS, d):
            Dm[(p, PE.qk(q))] = float(v)
            Nm[(p, PE.qk(q))] = float(v + rng.normal(0, .2))
            s1.append({"province_code": p, "quarter": q, "S1": float(rounds.set_index("quarter").loc[q, "H"] + 2 * v)})
    return rounds, pd.DataFrame(s1), Dm, Nm


def test_forecast_reports_regional_and_provincial_layers_separately():
    rounds, S1, Dm, Nm = synthetic_inputs()
    t = PE.qk("2026-Q1")
    out = PE.forecast(pd.Timestamp("2026-04-01"), t, [1, 2], rounds, S1, Dm, Nm, {})
    for k in ("1", "2"):
        lead = out["leads"][k]
        lay = lead["layers"]
        assert set(lay) == {"regional_risk", "provincial_differential", "composite"}
        reg = lay["regional_risk"]
        assert 0 <= reg["p_H_above_threshold"] <= 1 and "one observation per quarter" in reg["unit_of_evaluation"]
        assert "not a verified food-insecurity outcome" in lay["provincial_differential"]["kind"]
        for p, v in lead["provinces"].items():
            assert "not a verified food-insecurity outcome" in v["price_pressure"]["kind"]
            comp = v["risk"]["components"]
            assert np.isclose(comp["regional_hunger_H"]["contribution"] + comp["provincial_price_pressure_2D"]["contribution"],
                              v["risk"]["S1_forecast"])
            assert np.isclose(lay["provincial_differential"]["contribution_2D"][p],
                              comp["provincial_price_pressure_2D"]["contribution"])
            assert v["risk"]["indicative_only"]          # no validated evidence attached
        # the regional layer is one value for all five provinces
        assert len({round(v["risk"]["components"]["regional_hunger_H"]["value"], 12) for v in lead["provinces"].values()}) == 1
    assert "assumed" in out["leads"]["1"]["H"]["sampling_n"]


# ---------------------------------------------------------------------------------------------- per-round SWS n
def test_per_round_sample_size_is_optional_and_exact():
    rng = np.random.default_rng(5)
    times = np.arange(20, dtype=float)
    ys = 15 + np.cumsum(rng.normal(0, 2, 20))
    a = PE.h_forecast(times, ys, 21.0)
    b = PE.h_forecast(times, ys, 21.0, np.full(20, 600.0))
    assert all(np.isclose(a[k], b[k]) for k in ("mu_H", "V_H", "sigma_eta"))     # unchanged when n is constant
    c = PE.h_forecast(times, ys, 21.0, np.r_[np.full(12, 300.0), np.full(8, 600.0)])
    assert c["sampling_n"].startswith("per-round") and not np.isclose(a["mu_H"], c["mu_H"])
    rounds, S1, Dm, Nm = synthetic_inputs()
    rounds["n_respondents"] = np.where(rounds["quarter"] < "2025-Q1", 300, 600)
    out = PE.forecast(pd.Timestamp("2026-04-01"), PE.qk("2026-Q1"), [1], rounds, S1, Dm, Nm, {})
    assert out["leads"]["1"]["H"]["sampling_n"].startswith("per-round")
