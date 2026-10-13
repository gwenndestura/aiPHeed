"""E24v2 tests: PCF engine maths, publication-time (leakage) guards, pipeline READY / INSUFFICIENT_DATA / REPLAY paths,
pipeline = research seal on the real authorized inputs, prospective scoring refusals, acquisition year guard,
T1 back-cast refusals and a synthetic dry run, LGU ranking reproduction.

Synthetic fixtures live only in pytest's tmp_path and are never used in any reported result."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

EXP = Path(__file__).resolve().parents[1]
BD = EXP / "backend_dev"
sys.path.insert(0, str(BD))
sys.path.insert(0, str(EXP / "runner"))
sys.path.insert(0, str(EXP / "acquisition"))

from app.quarterly import pcf_engine as E  # noqa: E402
from app.quarterly.config import ForecastPeriod, load_period  # noqa: E402
from app.quarterly.forecaster_v2 import lgu_table, make_pcf_forecaster  # noqa: E402
from app.quarterly.periods import Quarter  # noqa: E402
from app.quarterly.registry import Registry  # noqa: E402
from app.quarterly.update import load_latest, run_update  # noqa: E402

PROV = E.PROVINCES


# ------------------------------------------------------------------ engine maths
def test_filter_with_zero_level_variance_is_precision_weighted_mean():
    ys = np.array([10.0, 14.0])
    ll, L, P, last = E._filter(np.array([0.0, 0.0]), ys, 0.0, 600)
    w = 1 / np.array([E.samp_var(10, 600), E.samp_var(14, 600)])
    # sequential update with the first observation as the diffuse start equals the inverse-variance mean
    assert L == pytest.approx((w * ys).sum() / w.sum())
    assert P == pytest.approx(1 / w.sum())


def test_h_forecast_variance_grows_with_gap_and_rejects_past_targets():
    t, y = np.arange(8, dtype=float), np.array([10, 11, 9, 12, 14, 13, 15, 16], float)
    a, b = E.h_forecast(t, y, 8.0), E.h_forecast(t, y, 11.0)
    assert a["mu_H"] == b["mu_H"] and b["V_H"] >= a["V_H"] and b["gap_quarters"] == 4
    with pytest.raises(ValueError):
        E.h_forecast(t, y, 7.0)


def test_p_high_is_one_half_at_the_threshold_and_monotone():
    from scipy.stats import norm
    tau, mu = 14.0, 14.0
    sd = np.sqrt(9 + 4)
    assert 1 - norm.cdf((tau - mu) / sd) == pytest.approx(0.5)
    assert E.signal_level(0.5) == "UNCERTAIN" and E.signal_level(0.9) == "STRONG" and E.signal_level(0.3) == "MODERATE"


def synthetic_panels(seed=0, last="2021-Q4"):
    rng = np.random.default_rng(seed)
    qs = [E.qs(i) for i in range(E.qk("2005-Q1"), E.qk(last) + 1)]
    D, N = [], []
    prev = {p: 0.0 for p in PROV}
    for q in qs:
        raw = {p: 0.6 * prev[p] + rng.normal(0, 1) for p in PROV}
        m = np.mean(list(raw.values()))
        for p in PROV:
            d = raw[p] - m
            D.append({"province_code": p, "quarter": q, "D": d})
            N.append({"province_code": p, "quarter": q, "Dnow": d + rng.normal(0, 0.3)})
            prev[p] = d
    return pd.DataFrame(D), pd.DataFrame(N)


def test_d_fit_recovers_a_known_coefficient():
    D, N = synthetic_panels()
    Dm, Nm = E.panels_from_tables(D, N)
    beta, sig, n = E.d_fit(Dm, Nm, E.qk("2021-Q4"), 1, False)
    assert 0.2 < beta[0] < 0.6 and n > 300 and sig > 0       # true lead-1 (2-step) coefficient is 0.36


def synthetic_rounds():
    rows = []
    for i, q in enumerate([E.qs(j) for j in range(E.qk("2019-Q1"), E.qk("2021-Q4") + 1)]):
        y, n = q.split("-Q")
        pub = pd.Timestamp(int(y), 3 * int(n), 28) + pd.Timedelta(days=40)
        rows.append({"quarter": q, "round": f"r{i}", "H": 10 + i * 0.5, "published": pub.date().isoformat(),
                     "date_type": "verified", "definition_A": True, "source": "production"})
    return pd.DataFrame(rows)


def synthetic_s1(rounds, D):
    H = rounds.set_index("quarter")["H"]
    S = D[D["quarter"].isin(H.index)].copy()
    S["S1"] = S["quarter"].map(H) + 2 * S["D"]
    return S[["province_code", "quarter", "S1"]]


# ------------------------------------------------------------------ leakage guards
def test_engine_ignores_everything_not_published_at_the_origin():
    D, N = synthetic_panels(last="2022-Q4")
    R = synthetic_rounds()
    S = synthetic_s1(R, D)
    t = E.qk("2021-Q2")
    origin = Quarter.parse("2021-Q3").start()
    Dm, Nm = E.panels_from_tables(D, N)
    base = E.forecast(origin, t, [1, 2], R, S, Dm, Nm, {})
    # perturb: D of quarters >= t, Dnow of quarters > t, rounds published after the origin, labels of quarters >= t
    D2, N2, R2, S2 = D.copy(), N.copy(), R.copy(), S.copy()
    D2.loc[D2["quarter"].map(E.qk) >= t, "D"] += 50
    N2.loc[N2["quarter"].map(E.qk) > t, "Dnow"] += 50
    late = pd.to_datetime(R2["published"]) >= origin.tz_localize(None)
    assert late.any()
    R2.loc[late, "H"] += 50
    S2.loc[S2["quarter"].map(E.qk) >= t, "S1"] += 50
    Dm2, Nm2 = E.panels_from_tables(D2, N2)
    pert = E.forecast(origin, t, [1, 2], R2, S2, Dm2, Nm2, {})
    assert json.dumps(base, sort_keys=True, default=str) == json.dumps(pert, sort_keys=True, default=str)


def test_unverified_or_late_rounds_are_unusable():
    R = synthetic_rounds()
    R.loc[3, "date_type"] = "estimated"
    origin = pd.Timestamp("2021-01-01")
    use = E.rounds_at_origin(R, origin)
    assert "r3" not in set(use["round"]) and (pd.to_datetime(use["published"]) < origin).all()


def test_threshold_uses_only_labels_whose_rounds_were_published():
    R = synthetic_rounds()
    D, _ = synthetic_panels()
    S = synthetic_s1(R, D)
    t = E.qk("2020-Q4")
    tau, n = E.threshold_at(S, R, t, Quarter.parse("2021-Q1").start())
    ok = [q for q, p in zip(R["quarter"], pd.to_datetime(R["published"])) if E.qk(q) <= t - 1 and p < pd.Timestamp("2021-01-01")]
    assert n == 5 * len(ok) and tau == pytest.approx(S[S["quarter"].isin(ok)]["S1"].median())


# ------------------------------------------------------------------ pipeline paths (synthetic registry)
def registry_with(tmp, last_d="2021-Q4", lgu=True):
    D, N = synthetic_panels(last=last_d)
    R = synthetic_rounds()
    S = synthetic_s1(R, D)
    files = {"sws_rounds_verified": R, "s1_labels": S, "d_quarterly_panel": D, "dnow_panel": N}
    if lgu:
        files["lgu_vulnerability"] = pd.read_csv(BD / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    reg = Registry(tmp / "sources.json")
    for i, (sid, df) in enumerate(files.items()):
        p = tmp / f"fx_{i}.csv"              # neutral names: the data guard denies protected-looking file names
        df.to_csv(p, index=False)
        kind = "label" if sid in ("sws_rounds_verified", "s1_labels") else ("static" if sid == "lgu_vulnerability" else "indicator")
        end = {"sws_rounds_verified": "2021-Q4", "s1_labels": "2021-Q4"}.get(sid, last_d)
        reg.register(sid, kind, p, observation_start="2005-Q1", observation_end=None if kind == "static" else end,
                     available_at="2021-12-20T00:00:00+08:00", authorized=True, authorized_by="test")
    card = tmp / "card.json"
    card.write_text(json.dumps({"model": "PCF test"}))
    reg.register("pcf_model_card", "model", card, authorized=True, authorized_by="test")
    return reg


def period_for(ref, req_q):
    r = Quarter.parse(ref)
    reqs = [{"id": "news", "kind": "news", "quarter": ref, "source_ids": ["news_x"], "blocking": False},
            {"id": "sws", "kind": "label", "quarter": req_q, "source_ids": ["sws_rounds_verified"]},
            {"id": "d", "kind": "indicator", "quarter": req_q, "source_ids": ["d_quarterly_panel"]},
            {"id": "model", "kind": "model", "source_ids": ["pcf_model_card"]},
            {"id": "lgu", "kind": "static", "source_ids": ["lgu_vulnerability"]}]
    return ForecastPeriod(r, r.end().floor("s"), requirements=reqs)


def test_pipeline_ready_with_nonblocking_news_missing(tmp_path):
    reg = registry_with(tmp_path)
    rec = run_update(period_for("2021-Q4", "2021-Q3"), reg, tmp_path / "runs", forecaster=make_pcf_forecaster({}),
                     now=pd.Timestamp("2022-02-01T00:00:00+08:00"))
    assert rec["status"] == "READY" and rec["mode"] == "LIVE" and rec["missing"] == []
    assert any("display context only" in m for m in rec["context_missing"])
    k1 = rec["forecast"]["leads"]["1"]
    assert k1["target_quarter"] == "2022-Q1" and len(k1["provinces"]) == 5
    assert len(rec["forecast"]["lgu_ranking"]) == 142 and load_latest(tmp_path / "runs")["content_sha256"] == rec["content_sha256"]


def test_pipeline_stale_input_gives_insufficient_data_and_no_forecast(tmp_path):
    reg = registry_with(tmp_path)
    rec = run_update(period_for("2022-Q4", "2022-Q3"), reg, tmp_path / "runs", forecaster=make_pcf_forecaster({}),
                     now=pd.Timestamp("2023-02-01T00:00:00+08:00"))
    assert rec["status"] == "INSUFFICIENT_DATA" and rec["forecast"] is None
    assert any("STALE" in m for m in rec["missing"])


def test_live_run_rejects_files_that_became_available_after_the_cutoff_but_replay_is_labelled(tmp_path):
    reg = registry_with(tmp_path)
    p = period_for("2021-Q3", "2021-Q2")         # cutoff 2021-09-30; files available 2021-12-20
    live = run_update(p, reg, tmp_path / "runs", forecaster=make_pcf_forecaster({}),
                      now=pd.Timestamp("2022-02-01T00:00:00+08:00"))
    assert live["status"] == "INSUFFICIENT_DATA" and any("NOT_AVAILABLE_BY_CUTOFF" in m for m in live["missing"])
    rep = run_update(p, reg, tmp_path / "runs", forecaster=make_pcf_forecaster({}), replay=True,
                     now=pd.Timestamp("2022-02-01T00:00:00+08:00"))
    assert rep["status"] == "READY" and rep["mode"] == "REPLAY" and "not a live forecast" in rep["labels"]["mode"]
    assert (tmp_path / "runs" / "replays" / "2021-Q4" / "forecast_record.json").exists()
    assert load_latest(tmp_path / "runs")["mode"] == "LIVE"       # a replay never becomes the live record


def test_unauthorized_input_blocks(tmp_path):
    reg = registry_with(tmp_path)
    reg.latest("d_quarterly_panel").authorized = False
    rec = run_update(period_for("2021-Q4", "2021-Q3"), reg, tmp_path / "runs", forecaster=make_pcf_forecaster({}),
                     now=pd.Timestamp("2022-02-01T00:00:00+08:00"))
    assert rec["status"] == "BLOCKED" and rec["forecast"] is None


# ------------------------------------------------------------------ real authorized inputs (isolated copy)
def test_pipeline_replay_equals_the_research_seal():
    rec = json.loads((BD / "data" / "quarterly_runs" / "replays" / "2026-Q3" / "forecast_record.json").read_text())
    seal_dir = EXP / "runs" / "SEAL_20261013T164218Z"
    s = json.loads((seal_dir / "SEAL_PROSPECTIVE.json").read_text())
    assert hashlib.sha256((seal_dir / "prospective_forecasts.csv").read_bytes()).hexdigest() == s["sha256"]
    F = pd.read_csv(seal_dir / "prospective_forecasts.csv", dtype={"province_code": str})
    k1 = rec["forecast"]["leads"]["1"]["provinces"]
    for p in PROV:
        a = F[(F.lead == 1) & (F.province_code == p) & (F.model == "FINAL_V2_PCF")]["score"].iloc[0]
        b = F[(F.lead == 1) & (F.province_code == p) & (F.model == "FINAL_V2_M4_pcf_D_now")]["score"].iloc[0]
        assert k1[p]["risk"]["p_high"] == pytest.approx(a, abs=1e-12)
        assert k1[p]["price_pressure"]["p_above_regional_mean"] == pytest.approx(b, abs=1e-12)
    assert rec["forecast"]["threshold"] == pytest.approx(s["threshold_T1"], abs=1e-12)


def test_live_2027Q1_cycle_is_insufficient_without_authorized_inputs():
    rec = load_latest(BD / "data" / "quarterly_runs")
    assert rec["period"]["target_quarter"] == "2027-Q1" and rec["status"] == "INSUFFICIENT_DATA"
    assert rec["forecast"] is None and rec["mode"] == "LIVE"
    assert rec["supporting_news"]["eligible"] == 0


def test_lgu_table_reproduces_e24_risk_index():
    lg = pd.read_csv(BD / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    e24 = pd.read_csv(EXP.parent / "2026-10-14_E24_Resolve_Forecasting" / "LGU_RANKING_VALIDATION.csv", dtype={"lgu_code": str})
    pp = {E.qs(0) and k: v for k, v in e24.groupby("province")["province_probability"].first().items()}
    prob = {[c for c, n in E.PROVINCE_NAMES.items() if n == name][0]: v for name, v in pp.items()}
    r = lgu_table(lg, prob).merge(e24[["lgu_code", "risk_index"]], on="lgu_code", suffixes=("", "_e24"))
    assert len(r) == 142 and (r["risk_index"] - r["risk_index_e24"]).abs().max() < 1e-9


# ------------------------------------------------------------------ prospective scoring refusals
def test_score_prospective_refuses_tampering_and_missing_authorization(tmp_path):
    import score_prospective as SC
    runs = tmp_path / "runs"
    shutil.copytree(EXP / "runs" / "SEAL_20261013T164218Z", runs / "SEAL_20261013T164218Z")
    out = tmp_path / "outcomes.csv"          # SYNTHETIC outcomes for the mechanics test only
    pd.DataFrame([{"target_quarter": "2026-Q3", "province_code": p, "S1": 20.0, "D": 0.1} for p in PROV]).to_csv(out, index=False)
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({"authorized_by": "test", "authorized_on": "2026-01-01",
                                "authorized_files": [{"path": "outcomes.csv", "sha256": "0" * 64}]}))
    with pytest.raises(SystemExit, match="does not match"):
        SC.main(["--outcomes", str(out), "--authorization", str(auth), "--runs", str(runs)])
    auth.write_text(json.dumps({"authorized_by": "test", "authorized_on": "2026-01-01", "authorized_files": [
        {"path": "outcomes.csv", "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}]}))
    assert SC.main(["--outcomes", str(out), "--authorization", str(auth), "--runs", str(runs)]) == 0
    res = json.loads((runs / "PROSPECTIVE_SCORES.json").read_text())["results"]
    assert res["T1_k1"]["_evidence"]["verdict"] == "INSUFFICIENT_PROSPECTIVE_EVIDENCE"   # one origin < 8
    f = runs / "SEAL_20261013T164218Z" / "prospective_forecasts.csv"
    f.write_text(f.read_text().replace("FINAL_V2_PCF", "FINAL_V2_PCX", 1))
    with pytest.raises(SystemExit, match="modified after sealing"):
        SC.main(["--outcomes", str(out), "--authorization", str(auth), "--runs", str(runs)])


# ------------------------------------------------------------------ acquisition guard (no network)
def test_acquisition_refuses_2026_or_later():
    import fetch_openstat as FO
    md = {"variables": [{"code": "Year", "values": ["0", "1", "2"], "valueTexts": ["2024", "2025", "2026"]}]}
    assert FO.years_sel(md, 2024, 2025) == ["0", "1"]
    with pytest.raises(AssertionError):
        FO.years_sel(md, 2025, 2026)
    js = {"columns": [{"code": "Year"}], "data": [{"key": ["2"], "values": ["1.0"]}]}
    with pytest.raises(AssertionError):
        FO.check_years(js, md, "t")


def test_comparability_gate_passed_on_the_acquired_series():
    g = json.loads((EXP / "data" / "comparability_gate.json").read_text())
    assert g["backcast_valid"] and g["gate_i_vs_E12_2021_2025"]["max_abs_dD"] <= 0.20
    m = json.loads((EXP / "acquisition" / "ACQUISITION_MANIFEST.json").read_text())
    assert m["max_year_requested"] == 2025
    for name, v in m["tidy_files"].items():
        assert hashlib.sha256((EXP / "acquisition" / name).read_bytes()).hexdigest() == v["sha256"]


# ------------------------------------------------------------------ T1 back-cast runner (A2)
def sws_fixture(tmp, late=False):
    rng = np.random.default_rng(1)
    rows = [{"quarter": E.qs(i), "H": round(12 + 4 * np.sin(i / 5) + rng.normal(0, 1), 1), "published": "",
             "source": "SYNTHETIC TEST FIXTURE"} for i in range(E.qk("1998-Q1"), E.qk("2020-Q4") + 1)]
    if late:
        rows.append({"quarter": "2021-Q1", "H": 10.0, "published": "", "source": "x"})
    p = tmp / "sws.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    a = tmp / "auth.json"
    a.write_text(json.dumps({"authorized_by": "test", "authorized_on": "2026-01-01",
                             "authorized_files": [{"path": "sws.csv", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}]}))
    return p, a


def test_t1_backcast_refuses_unauthorized_and_post_2020_rows(tmp_path):
    import run_bx_t1 as BT
    p, a = sws_fixture(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"authorized_by": "t", "authorized_on": "d", "authorized_files": []}))
    with pytest.raises(SystemExit, match="not authorized"):
        BT.main(["--sws", str(p), "--authorization", str(bad), "--out", str(tmp_path / "o")])
    p2, a2 = sws_fixture(tmp_path, late=True)
    with pytest.raises(SystemExit, match="after 2020-Q4"):
        BT.main(["--sws", str(p2), "--authorization", str(a2), "--out", str(tmp_path / "o")])


def test_t1_backcast_dry_run_on_synthetic_fixture(tmp_path):
    import run_bx_t1 as BT
    p, a = sws_fixture(tmp_path)
    out = BT.main(["--sws", str(p), "--authorization", str(a), "--out", str(tmp_path / "o"), "--leads", "1"])
    res = json.loads((out / "results_T1_BX.json").read_text())
    assert set(res["confirmatory"]) == {"HT1", "HT2", "HT3"} and res["by_lead"]["1"]["n_test_quarters"] >= 8
    P = pd.read_csv(out / "predictions_T1_BX.csv")
    assert P["target_quarter"].map(E.qk).max() <= E.qk("2020-Q4")
