"""E35 reproducibility and integrity tests: protocol frozen, artifacts preserved, the default configuration equals
E32-PCFN, every configuration ignores unreleased data, the nested selection uses only outcomes public at each origin,
the selection and verdict follow the protocol, the spread scale cannot change a decision, runs are byte-identical,
and the prospective record is intact."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E35 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E35 / "runner"))
import e35_common as E  # noqa: E402
import e35_grid as G  # noqa: E402
import e35_preserve as PR  # noqa: E402
import e35_tune as TU  # noqa: E402
import e35_verify as V  # noqa: E402

C, L = E.C, E.L
PRIMARY, REPEAT = E35 / "runs" / "20261015T005446Z", E35 / "runs" / "20261015T005506Z"


@pytest.fixture(scope="module")
def d():
    return L.Data()


@pytest.fixture(scope="module")
def res():
    return json.loads((PRIMARY / "results.json").read_text(encoding="utf-8"))


def test_protocol_is_the_frozen_one(res):
    want = (E35 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert E.sha(E35 / "PROTOCOL.md") == want == res["protocol_sha256"]


def test_preserved_artifacts_unchanged():
    assert PR.main("check") == 0


def test_dataset_is_the_one_tuned_on(res):
    assert E.dataset_manifest() == res["dataset_sha256"]


def test_pre_tuning_verification_passed():
    v = json.loads((E35 / "verification" / "VERIFICATION.json").read_text(encoding="utf-8"))
    assert v["all_pass"] and len(v["checks"]) == 7


def test_default_configuration_is_e32_pcfn(d):
    assert G.DEFAULT_CFG.id == "lam0.5|D4|c1.00" and len(G.GRID) == 36
    assert V.v7_default_reproduces_e32(d)["pass"]


def test_unreleased_data_cannot_change_any_configuration(d):
    rng = np.random.default_rng(7)
    for k, T in ((1, "2026-Q3"), (2, "2025-Q4"), (1, "2026-Q4")):
        t = C.qk(T) - k
        base = G.all_probs(d, t, k)
        got = G.all_probs(V.scrambled(d, t, rng), t, k)
        assert all(base[c][p] == got[c][p] for c in base for p in C.PROVS)


def test_spread_scale_never_changes_a_decision():
    g = pd.read_csv(PRIMARY / "grid_predictions.csv", dtype={"province_code": str})
    g[["lam", "dset", "c"]] = g["config"].str.split("|", expand=True)
    dec = g.assign(h=g["p"] >= 0.5).groupby(["lead", "target_quarter", "province_code", "lam", "dset"])["h"].nunique()
    assert (dec == 1).all()


def test_nested_inner_dates_were_public_at_each_origin(d):
    sl = pd.read_csv(PRIMARY / "selection_log.csv", keep_default_na=False)
    for r in sl.itertuples():
        t = C.qk(r.outer_target) - r.lead
        posted = set(d.posted_quarters(L.origin(t)))
        inner = r.inner_dates.split() if r.inner_dates else []
        assert len(inner) == r.n_inner
        assert all(C.qk(x) <= t - 1 and C.qk(x) in posted for x in inner)
        assert r.outer_target not in inner
        if r.n_inner < TU.MIN_INNER:
            assert r.selected == G.DEFAULT_CFG.id


def test_selection_rule_recomputed_from_inner_scores():
    sl = pd.read_csv(PRIMARY / "selection_log.csv")
    inn = pd.read_csv(PRIMARY / "inner_scores.csv")
    for r in sl[sl["n_inner"] >= TU.MIN_INNER].itertuples():
        g = inn[(inn["lead"] == r.lead) & (inn["outer_target"] == r.outer_target)]
        assert len(g) == 36
        sc = dict(zip(g["config"], g["inner_mean_brier"]))
        best = min(sc.values())
        tied = [c for c, v in sc.items() if v <= best + TU.TIE + 1e-9]
        assert r.selected == min(tied, key=lambda c: (TU.CFG[c].tie_key(), c))


def test_tuned_predictions_are_the_selected_configurations():
    pr = pd.read_csv(PRIMARY / "predictions.csv", dtype={"province_code": str})
    g = pd.read_csv(PRIMARY / "grid_predictions.csv", dtype={"province_code": str})
    sl = pd.read_csv(PRIMARY / "selection_log.csv")
    for r in sl.itertuples():
        a = pr[(pr.arm == "E35-TUNED") & (pr.lead == r.lead) & (pr.target_quarter == r.outer_target)].sort_values("province_code")
        b = g[(g.config == r.selected) & (g.lead == r.lead) & (g.target_quarter == r.outer_target)].sort_values("province_code")
        assert np.array_equal(a["p"].to_numpy(), b["p"].to_numpy()) and np.array_equal(a["y"].to_numpy(), b["y"].to_numpy())


def test_identical_rows_for_every_arm():
    pr = pd.read_csv(PRIMARY / "predictions.csv", dtype={"province_code": str})
    for k, n in ((1, 50), (2, 40)):
        s = pr[(pr.lead == k) & (pr.arm != "P45")]
        keys = {a: set(zip(g.target_quarter, g.province_code)) for a, g in s.groupby("arm")}
        assert all(len(v) == n for v in keys.values()) and len({frozenset(v) for v in keys.values()}) == 1
        assert s.groupby(["target_quarter", "province_code"])["y"].nunique().max() == 1


def test_acceptance_and_verdict_follow_the_protocol(res):
    m = res["acceptance"]["mean_per_date_brier_lead1"]
    a = res["acceptance"]
    assert a["A1_brier_below_PCF21"] == (m["E35-TUNED"] < m["PCF21"])
    assert a["A2_brier_not_worse_than_persistence"] == (m["E35-TUNED"] <= m["B1"])
    assert a["T_brier_below_E32_PCFN"] == (m["E35-TUNED"] < m["E32-PCFN"])
    assert a["A3_accuracy_at_least_0.75"] == (a["accuracy_lead1"] >= 0.75)
    assert a["verdict"] == "NO IMPROVEMENT" and not a["A1_brier_below_PCF21"]
    assert abs(m["E32-PCFN"] - 0.10065021972820214) < 1e-9          # the E32 result, unchanged


def test_runs_are_byte_identical():
    files = sorted(p.name for p in PRIMARY.iterdir())
    assert files == sorted(p.name for p in REPEAT.iterdir()) and len(files) == 7
    for f in files:
        assert (PRIMARY / f).read_bytes() == (REPEAT / f).read_bytes(), f


def test_prospective_record_intact_and_reproducible(d, res):
    f = E35 / "frozen" / "E35_PROSPECTIVE.json"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == (E35 / "frozen" / "E35_PROSPECTIVE.sha256").read_text().split()[0]
    rec = json.loads(f.read_text(encoding="utf-8"))
    assert rec["e32_frozen_record"]["sha256"] == E.sha(E.E32 / "frozen" / "E32_PROSPECTIVE.json")
    for k in ("1", "2"):
        b = rec["leads"][k]
        assert "2026-Q3" not in b["inner_dates"]                    # posted 2026-10-14, after the origin
        cfg = TU.CFG[b["selected_config"]["id"]]
        got = G.probs(G.components(d, TU.OPERATIONAL_T, int(k)), cfg)
        assert all(abs(got[p] - b["p_high"][p]) < 1e-12 for p in C.PROVS)
        assert b["selected_config"]["id"] == res["prospective_selection"][k]["selected"]
