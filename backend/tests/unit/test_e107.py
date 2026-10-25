"""Tests for E107 (one LightGBM on the 12 aiPHeed indicators; PROTOCOL.md section 12).

They check that all 12 indicator families reach LightGBM, that no value published on or after an issue date changes the
features of that origin, that training rows never contain the evaluated outcome or an outcome unknown at the issue date,
that targets and horizons are aligned, the study window, and that stored predictions and the seal reproduce.
"""
import json
import sys
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E107_Twelve_Indicator_LightGBM"
sys.path.insert(0, str(EXP / "runner"))
import e107_lib as E  # noqa: E402
import e107_model as M  # noqa: E402

L, np, pd = E.L, E.np, E.pd
OUT = EXP / "out"
SAMPLE = [E.qi(q) for q in ("2022-Q3", "2023-Q4", "2024-Q2", "2025-Q1", "2026-Q2", "2026-Q3")]


# ------------------------------------------------------------------------------------------------ 1 completeness
def test_all_twelve_families_are_model_columns():
    assert sorted(E.FAMILIES) == E.EXPECTED_FAMILIES and len(E.FAMILIES) == 12
    assert {E.FAMILY_OF[c] for c in E.COLUMNS} == set(E.EXPECTED_FAMILIES)
    X = E.feature_table(2)
    assert all(c in X.columns for c in E.COLUMNS)
    for c in E.COLUMNS:                                   # every column has observed values somewhere in the window
        assert X[c].notna().any(), c


def test_fitted_booster_uses_every_column_as_an_input():
    X = E.feature_table(1)
    t = E.qi("2025-Q4")
    tr = M.train_rows(X, t, 1, "T43")
    assert E.eligible(tr, "T43")
    m = M.Model(M.GRID[3], "T43", E.COLUMNS).fit(tr)
    assert m.m.booster_.feature_name() == E.COLUMNS


# ------------------------------------------------------------------------------------------------ 2 future perturbation
def _perturbed(t: int):
    d, x = E.data()
    m0, O = L.m0_of(t), L.origin(t)
    idx = d.idx.copy()
    idx.loc[idx["ym"] > m0, "index"] *= 3.0
    yoy = d.yoy.copy()
    yoy.loc[yoy["ym"] > m0, "yoy"] += 50.0
    sws = d.sws.copy()
    sws.loc[sws["published"] >= O, "H"] += 30.0
    prod = d.prod.copy()
    prod.loc[prod["q"] > t - 1, "value"] *= 5.0
    lfs = d.lfs.copy()
    lfs.loc[lfs["ym"] > (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2, "value"] += 10.0
    news = d.news.copy()
    news.loc[news["q"] > t, "news_n"] *= 7.0
    x2 = {k: v.copy() for k, v in x.items()}
    c = x2["climate"]
    c.loc[c["q"] > t, "tc_count"] += 9
    c.loc[c["q"] >= t, "enso_phase"] = "LA_NINA"
    for k in ("ofw", "rice"):
        num = x2[k].select_dtypes("number").columns.drop(["year", "q"], errors="ignore")
        x2[k].loc[x2[k]["q"] > t - 1, num] *= 3.0
    return L.Data(idx, yoy, sws, prod, lfs, news, meta=d.meta), x2


@pytest.mark.parametrize("t", SAMPLE)
@pytest.mark.parametrize("k", E.LEADS)
def test_values_published_after_the_issue_do_not_change_features(t, k):
    dm, xm = _perturbed(t)
    a = E.feature_table(k, [t]).set_index("province_code")[E.COLUMNS]
    b = E.feature_table(k, [t], dm, xm).set_index("province_code")[E.COLUMNS]
    pd.testing.assert_frame_equal(a, b)


@pytest.mark.parametrize("t", SAMPLE)
def test_backend_asof_inputs_respect_the_issue_date(t):
    issue = E.issue(t)
    for k in E.LEADS:                                     # H1: only rounds posted before the issue
        rh = E.TS.regional_hunger(t, k)
        if rh["status"] == "OK":
            q = rh["latestReadingQuarter"]
            pubs = pd.read_csv(E.L.SWS_FILE).query("quarter == @q and definition_A == True")["published"]
            assert len(pubs) and (pubs.str[:10] < issue).all()
    for a in E.P3.asof(t):                                # N1: headlines of quarter t published before the issue
        assert a["quarter"] == E.qs(t) and E.P3._ph(a) < E.P3.origin(t)
    st = E.CW.hazard(issue)[1]                            # C1: PAGASA item issued before the issue
    if st.startswith("PAGASA "):
        assert st[7:17] < issue


# ------------------------------------------------------------------------------------------------ 3 split integrity
@pytest.mark.parametrize("target", ["T43", "R"])
@pytest.mark.parametrize("k", E.LEADS)
def test_training_rows_are_known_at_the_issue_and_exclude_the_evaluated_outcome(target, k):
    X = E.feature_table(k)
    Xr = M.regional(X) if target == "R" else X
    for q in sorted(E.outcomes(target)["q"].unique()):
        t = q - k
        if t < E.FIRST_ORIGIN:
            continue
        tr = M.train_rows(Xr, t, k, target)
        if not len(tr):
            continue
        known = E.known_labels(t, target)
        assert (tr["q"] <= t - 1).all() and (tr["t"] + k == tr["q"]).all() and (tr["t"] < t).all()
        assert set(tr["q"]) <= set(known["q"])
        assert q not in set(tr["q"])
        for qq in tr["q"].unique():                       # every SWS round of a training quarter was posted before O(t)
            pubs = E.data()[0].sws.query("q == @qq")["published"]
            assert (pubs < L.origin(t)).all()


def test_latest_sws_quarter_is_not_known_at_its_own_next_issue():
    t = E.qi("2026-Q3")                                    # 2026-Q3 round posted 2026-10-14, after the 2026-10-01 issue
    assert E.qi("2026-Q3") not in set(E.known_labels(t, "R")["q"])
    assert E.qi("2026-Q2") in set(E.known_labels(t, "R")["q"])


# ------------------------------------------------------------------------------------------------ 4 target alignment
def test_targets_are_t_plus_k_and_labels_match_the_rule():
    for k in E.LEADS:
        X = E.feature_table(k)
        assert (X["target_q"] == X["t"] + k).all()
    d = E.data()[0]
    th = L.e40_spec()
    F = L.quarter_F(d).set_index(["province_code", "q"])["F"]
    HL = L.quarter_F(d, "all_items").set_index(["province_code", "q"])["F"]
    H = L.h_quarters(d).set_index("q")["H"]
    lab = E.t43_frame(d)
    for r in lab.itertuples():
        f, hl, h = F[(r.province_code, r.q)], HL[(r.province_code, r.q)], H[r.q]
        y = int(h > 11.3 and (f > th["food"][r.province_code] or f - hl > th["gap"][r.province_code]))
        assert y == r.y
    assert len(lab) == 95 and int(lab["y"].sum()) == 18
    R = E.r_frame(d)
    assert len(R) == 19 and ((R["H"] > 11.3).astype(int) == R["y"]).all()


# ------------------------------------------------------------------------------------------------ 5 horizon arithmetic
def test_horizon_arithmetic():
    assert E.issue(E.qi("2026-Q3")) == "2026-10-01" and E.issue(E.qi("2025-Q4")) == "2026-01-01"
    for t in SAMPLE:
        for k in E.LEADS:
            months = L.target_months(t, k)
            assert {L.q_of_ym(m) for m in months} == {t + k} and len(months) == 3
            assert all(b <= L.m0_of(t) for b in E.projection_bases(t, k))
    t = E.qi("2026-Q3")
    assert len(E.projection_bases(t, 4)) == 2 and all(len(E.projection_bases(t, k)) == 3 for k in (1, 2, 3))


# ------------------------------------------------------------------------------------------------ 6 window
def test_nothing_before_2021():
    d, x = E.data()
    assert d.idx["ym"].min() >= 2021 * 12 and d.yoy["ym"].min() >= 2021 * 12 and d.lfs["ym"].min() >= 2021 * 12
    assert d.sws["q"].min() >= E.qi("2021-Q1") and d.prod["q"].min() >= E.qi("2021-Q1")
    assert all(v["q"].min() >= E.qi("2021-Q1") for v in x.values())
    assert E.feature_table(1)["t"].min() == E.qi("2021-Q1")


# ------------------------------------------------------------------------------------------------ 7, 8 reproducibility
needs_run = pytest.mark.skipif(not (OUT / "results.json").exists(), reason="run runner/run_e107.py dev and final first")


@needs_run
@pytest.mark.parametrize("target,k", [("T43", 1), ("T43", 3), ("R", 2)])
def test_stored_predictions_reproduce(target, k):
    st = pd.read_csv(OUT / f"predictions_{target}_lead{k}.csv", dtype={"province_code": str})
    q = int(st["q"].iloc[len(st) // 2])
    df, _ = M.run(k, target, quarters=[q], arms=False)
    j = st[st["q"] == q].merge(df[["province_code", "p"]], on="province_code", suffixes=("", "_new"))
    assert len(j) and np.allclose(j["p"], j["p_new"], atol=1e-9)


@needs_run
def test_results_were_scored_under_the_frozen_protocol():
    r = json.loads((OUT / "results.json").read_text())
    frozen = (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text().strip()
    assert r["protocol_sha256"] == frozen == E.sha256(EXP / "PROTOCOL.md")
    assert r["dev_run"]["utc"] < r["final_run"]["utc"]
    assert not r["final_run"]["git"]["runner_dirty"]


@pytest.mark.skipif(not (OUT / "sealed_prospective.csv").exists(), reason="run runner/run_e107.py prospective first")
def test_seal_hash_matches():
    assert E.sha256(OUT / "sealed_prospective.csv") == (OUT / "sealed_prospective.csv.sha256").read_text().strip()


# ------------------------------------------------------------------------------------------------ read-only API
SERVE = E.BACKEND / "data" / "e107"


@pytest.mark.skipif(not (SERVE / "evaluation_summary.json").exists(), reason="run runner/run_e107.py export first")
def test_api_serves_the_exported_files_unchanged():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for route, name in (("evaluation", "evaluation_summary.json"), ("forecast", "forecast.json"),
                        ("indicators", "indicators.json")):
        r = c.get(f"/api/v1/e107/{route}")
        assert r.status_code == 200
        assert r.json() == json.loads((SERVE / name).read_text(encoding="utf-8"))
    ind = c.get("/api/v1/e107/indicators").json()
    assert ind["n_families"] == 12 and sorted(f["code"] for f in ind["families"]) == E.EXPECTED_FAMILIES
    fc = c.get("/api/v1/e107/forecast").json()
    assert fc["sealed_sha256"] == (OUT / "sealed_prospective.csv.sha256").read_text().strip()


@pytest.mark.skipif(not (SERVE / "evaluation_summary.json").exists(), reason="run runner/run_e107.py export first")
def test_exported_decisions_match_results():
    ev = json.loads((SERVE / "evaluation_summary.json").read_text(encoding="utf-8"))
    r = json.loads((OUT / "results.json").read_text())
    for tg, T in r["targets"].items():
        assert ev["results"][tg]["max_reliable_lead"] == T["max_reliable_lead"]
        for k in map(str, E.LEADS):
            if T["blocks"][k]["combined"].get("primary"):
                assert ev["results"][tg]["leads"][k]["reliable"] == T["decision"][k]["reliable"]
