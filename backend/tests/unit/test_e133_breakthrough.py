"""
tests/unit/test_e133_breakthrough.py
------------------------------------
E133 (forecasting breakthrough directive): frozen protocol and write-once seals, exact reproduction of E132, the
hierarchical factor model's Kalman filter (exact against a direct Gaussian likelihood), drivers available before the
issue date only, 2021+ inputs, the frozen selection rule and its reported outcome (75 % not reached, no rule set
passed, no reliable lead), the trigger-group criterion, and the primary-only scorer.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E133_Forecasting_Breakthrough"
pytestmark = pytest.mark.skipif(not (E / "out" / "e133_metrics.csv").exists(), reason="E133 outputs not built")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load(name: str):
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location(name, E / "runner" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_protocol_seals_and_package():
    assert (E / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0] == _sha(E / "E133_FROZEN_PROTOCOL.md")
    for line in (E / "sealed" / "E133_SEAL_SHA256.txt").read_text().splitlines():
        h, name = line.split()
        assert _sha(E / "sealed" / name) == h
    r = subprocess.run([sys.executable, "-I", "-B", str(E / "runner" / "e133_seal.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "refusing to overwrite" in (r.stdout + r.stderr)
    text = (E / "E133_FINAL_RESEARCH_PACKAGE.md").read_text(encoding="utf-8")
    for i in range(1, 15):
        assert f"\n## {i}. " in text


def test_e132_reproduced_exactly():
    rep = json.loads((E / "out" / "e133_reproduction_check.json").read_text())
    assert rep["rows_matched"] == rep["rows_old"] == rep["rows_new"]
    assert all(v < 1e-9 for k, v in rep.items() if k.startswith("max_abs_diff"))
    assert rep["lead2_shared_rows"] == 28 and abs(rep["lead2_within_SEAS-LLM"] - 17 / 28) < 1e-12


def test_kalman_filter_matches_direct_gaussian_likelihood():
    M = _load("e133_models")
    rng = np.random.default_rng(1)
    T = 5
    Y = rng.normal(15, 3, (T, 4))
    Y[2, 1] = np.nan
    R = np.full((T, 4), 4.0)
    idx = np.arange(100, 100 + T)
    fit = M.Fit(q_c=2.0, q_d=1.5, rho=0.6, b=0.0, tau2=0.5)
    x, P, ll, _ = M.kfilter(Y, R, idx, fit, brk=10**6)
    # direct: stack the states, build the joint covariance of all observations after the first period
    n = M.N
    x0, P0 = M._init(Y[0], fit)
    F = M._transition(fit)
    Q = np.zeros((n, n)); Q[0, 0] = fit.q_c; Q[6:, 6:] = np.eye(4) * fit.q_d
    # condition on period 0 by filtering it, then compare the predictive likelihood of periods 1..T-1
    xf, Pf, _, _ = M.kfilter(Y[:1], R[:1], idx[:1], fit, brk=10**6)
    means, covs, obs = [], [], []
    states_mean = [xf]
    A = [np.eye(n)]
    for t in range(1, T):
        A.append(F @ A[-1])
    cov_state = {}
    for t in range(1, T):
        for s in range(1, T):
            m = min(t, s)
            c = A[t] @ Pf @ A[s].T
            for j in range(1, m + 1):
                c = c + A[t - j] @ Q @ A[s - j].T
            cov_state[(t, s)] = c
    rows = [(t, a) for t in range(1, T) for a in range(4) if np.isfinite(Y[t, a])]
    mu = np.array([M.H[a] @ (A[t] @ xf) for t, a in rows])
    S = np.array([[M.H[a] @ cov_state[(t, s)] @ M.H[b] + (R[t, a] + fit.tau2 if (t, a) == (s, b) else 0.0)
                   for s, b in rows] for t, a in rows])
    y = np.array([Y[t, a] for t, a in rows])
    sign, logdet = np.linalg.slogdet(S)
    direct = -0.5 * (len(y) * np.log(2 * np.pi) + logdet + (y - mu) @ np.linalg.solve(S, y - mu))
    assert abs(ll - direct) < 1e-8


def test_drivers_point_in_time_and_window():
    R = _load("e133_run")
    for tag in ("rice", "b30"):
        d = R.Drivers(tag)
        for g, t in d.tab.items():
            assert (t["qi"] >= R.L.qi("2021-Q1")).all()
            assert all(a > R.L.qend(R.L.qs(int(q))) for q, a in zip(t["qi"], t["available"]))
        issue = date(2024, 1, 1)
        vals, last, _ = d.at(issue)
        for g, t in d.tab.items():
            ok = set(t.loc[t["available"] <= issue, "qi"].astype(int))
            assert set(vals[g]) <= ok
    raw = pd.read_csv(E / "data" / "raw" / "psa_cpi_bottom30_region_2021_2026.csv", nrows=1, encoding="utf-8-sig")
    assert all(int(c[:4]) >= 2021 for c in raw.columns if c[:4].isdigit())


def test_selection_rule_and_reported_outcome():
    s = json.loads((E / "out" / "e133_summary.json").read_text())
    Mt = pd.read_csv(E / "out" / "e133_metrics.csv")
    sel = Mt[(Mt.set == "S-U") & (Mt.policy == "P-DASH") & (Mt.lead == 2)
             & Mt.model.isin(["HFM", "HFM-NS", "HFM-NS-DES", "HFM-TREND", "HFM-X", "HFM-X-B30", "ENS133", "SEAS-LLM"])]
    best = sel.sort_values(["within_tolerance", "mae"], ascending=[False, True]).iloc[0]
    assert s["selection"]["candidate"] == best["model"] == "HFM-X"
    assert best["n"] == 40 and best["n_quarters"] == 10 and best["within_tolerance"] == 0.5
    assert not s["any_model_any_lead_75"] and (Mt["within_tolerance"] < 0.75).all()
    assert s["any_rule_set_passed"] == [] and s["maximum_reliable_lead"] is None
    assert not any(v["validated"] for v in s["candidate_rules"].values())
    assert "HFM-X-PH1" not in s["selection"]["table"][0]["model"]


def test_trigger_criterion_applied_as_frozen():
    a = pd.read_csv(E / "out" / "e133_trigger_contribution.csv")
    exp = (a["delta_mae_when_removed"] > 0) & (a["delta_within_when_removed"] < 0) & (a["p_full_better_sq_error"] < 0.10)
    assert (a["demonstrated"] == exp).all()
    assert not a.loc[a.lead == 2, "demonstrated"].any()


def test_primary_only_scorer(tmp_path):
    sc = _load("score_e133")
    seal = pd.read_csv(E / "sealed" / "E133_PROSPECTIVE_SEAL.csv")
    rounds = tmp_path / "r.csv"
    pd.DataFrame([{"quarter": "2026-Q4", "fieldwork": "2026-12-01/2026-12-05", "published": "2027-01-20",
                   "respondent_base": "adults", "commissioned": False, "national": 22.0, "metro_manila": 25.0,
                   "balance_luzon": 22.0, "visayas": 20.0, "mindanao": 23.0, "bl_n": 600, "area_moe_bl": 4,
                   "area_moe_other": 6, "source_type": "test", "source": "test"}]).to_csv(rounds, index=False)
    S, summ = sc.score(seal, rounds)
    assert len(S) == 4 and "primary only" in summ["criterion"]
    r = S[S.area == "balance_luzon"].iloc[0]
    f = seal[(seal.area == "balance_luzon") & (seal.target == "2026-Q4")]["HFM-X"].iloc[0]
    assert r["within_primary_HFM-X"] == (abs(f - 22.0) <= r["tolerance_primary"])
