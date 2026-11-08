"""FI12 tests: lock integrity, outcome values, reference-year matching without future information, recomputation."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.fi12 import OUT, PROVINCES
from app.fi12 import outcomes as O
from app.fi12 import study as S

T = pd.read_csv(OUT / "outcomes.csv")
A = pd.read_csv(OUT / "model_scores_by_reference_year.csv")
R = pd.read_csv(OUT / "ranking_agreement.csv")


def test_lock_matches_code_and_protocol():
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    assert lock["sha256"] == S._digest() and lock["code_sha256"] == S._code()
    assert json.loads((OUT / "evaluation.json").read_text())["protocol_sha256"] == lock["sha256"]


def test_outcomes_unchanged_from_workbook_and_tracks_separate():
    wb = pd.read_csv(O.WB)
    assert len(T) == len(wb) == 50
    m = T.merge(wb, on="record_id")
    same = m["outcome"] != "FNRI15_INSEC"
    assert np.allclose(m.loc[same, "value"], m.loc[same, "label_value"])
    assert np.allclose(m.loc[~same, "value"], 100 - m.loc[~same, "label_value"])
    assert set(T["track"]) == {"A", "B"} and not T["description"].str.contains("SWS").any()
    assert set(T["province"]) == set(PROVINCES)


def test_matching_uses_reference_years_and_past_issues_only():
    R0 = S.M._quarterly()
    assert (R0["issue_qi"] < R0["target_qi"]).all()
    assert set(A["year"]) <= set(S.M.YEARS)
    p0 = A[A["model"].str.startswith(("P0H4", "CR", "UNI", "CH1", "E108"))]
    assert set(p0["year"]) == {2023}


def test_served_p0h4_scores_match_served_rows():
    r = pd.read_csv(S.BACKEND_DIR / "data" / "ch1_engine" / "rows.csv")
    r = r[(r["lead"] == 1) & r["quarter"].str.startswith("2023")].groupby("province")["probability"].mean()
    a = A[(A["model"] == "P0H4") & (A["lead"] == 1) & (A["year"] == 2023)].set_index("province")["score"]
    assert np.allclose(a.loc[r.index], r, atol=1e-9)


def test_baselines_use_only_available_waves():
    B = pd.read_csv(OUT / "baseline_scores.csv")
    assert ((B["from_wave"] + 2) <= B["year"]).all()


def test_reported_ranking_recomputes():
    g = T[(T["outcome"] == "PSA_SUB_FAM") & (T["reference_year"] == 2023)].sort_values("province")
    s = A[(A["model"] == "P0H4") & (A["lead"] == 1) & (A["year"] == 2023)].set_index("province").loc[g["province"], "score"]
    row = R[(R["outcome"] == "PSA_SUB_FAM") & (R["key"] == "P0H4|L1") & (R["year"] == "2023")].iloc[0]
    assert abs(S.spearman(s.to_numpy(), g["value"].to_numpy()) - row["spearman"]) < 1e-9
    assert abs(S.exact_p(s.to_numpy(), g["value"].to_numpy()) - row["p_one_sided"]) < 1e-9


def test_exact_permutation_p_bounds():
    x = np.arange(5.0)
    assert abs(S.spearman(x, x) - 1) < 1e-9 and abs(S.exact_p(x, x) - 1 / 120) < 1e-12
    m, p = S.pooled_p([(x, x), (x, x)])
    assert abs(m - 1) < 1e-9 and abs(p - 1 / 120 ** 2) < 1e-12


def test_no_model_has_rank_skill_and_no_classification_labels():
    models = R[~R["key"].str.startswith("BASE")]
    assert not ((models["p_one_sided"] < 0.05) & (models["spearman"] > 0)).any()
    meas = json.loads((OUT / "evaluation.json").read_text())["measurement"]
    for oid in ("FNRI15_SEV", "PSA_SUB_FAM", "PSA_SUB_POP"):
        hi = sum(len(v.get("significantly_above_region", [])) for k, v in meas.items() if k.startswith(oid + "|"))
        assert hi < 3, oid
