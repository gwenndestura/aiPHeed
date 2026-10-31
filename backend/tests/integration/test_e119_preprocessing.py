"""
tests/integration/test_e119_preprocessing.py
--------------------------------------------
E119: frozen protocol unchanged; no pre-2021 observation; every value used was observed before the target quarter and
available before the issue; every dataset value traces to a cleaned 2021+ observation (no fill or imputation); no national
or regional value copied into the provincial dataset; all 12 FIRI v2 indicators mapped with the served labels and domains;
raw inputs keep their logged hashes; no label in the provincial dataset.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "aipheed-backend-aligned" / "experiments" / "E119_Preprocessing"
pytestmark = pytest.mark.skipif(not (E / "out" / "manifest.json").exists(), reason="E119 outputs missing")
PROVS = {"Cavite", "Laguna", "Batangas", "Rizal", "Quezon"}


def _q(s: str) -> int:
    return int(s[:4]) * 4 + int(s[-1]) - 1


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_protocol_frozen():
    assert _sha(E / "E119_PREPROCESSING_PROTOCOL.md") == (E / "runner" / "PROTOCOL_SHA256.txt").read_text().strip()


def test_raw_inputs_unchanged():
    import sys
    sys.path.insert(0, str(E / "runner"))
    import preprocess as P
    logged = json.loads((E / "out" / "manifest.json").read_text())["inputs_sha256"]
    assert logged.keys() == P.INPUTS.keys()
    missing = [k for k, p in P.INPUTS.items() if not Path(p).exists()]
    if missing:
        pytest.skip(f"untracked inputs absent: {missing}")
    for k, p in P.INPUTS.items():
        assert _sha(Path(p)) == logged[k], k


def test_leakage_checks_recorded_true():
    lk = json.loads((E / "out" / "manifest.json").read_text())["leakage"]
    for k in ("features_observed_before_target", "features_available_before_issue", "no_target_quarter_hunger_in_features",
              "sws_history_published_before_issue", "no_pre2021_observation_in_any_series"):
        assert lk[k] is True, k


def test_point_in_time_rows():
    pit = pd.read_csv(E / "E119_POINT_IN_TIME_VALIDATION.csv")
    assert (pit["avail_date"].astype(str) < pit["issue_date"].astype(str)).all()
    reg = pit[pit["dataset"] == "regional"].dropna(subset=["obs_q"])
    assert (reg["obs_q"] < reg["target_quarter"].map(_q)).all()
    assert (pit["obs_q"].dropna() >= 2021 * 4).all()                         # nothing before 2021-Q1
    assert set(pit["status"]) <= {"verified", "rule_unverified"}


def test_no_pre2021_in_clean_outputs():
    for f in (E / "out" / "indicators").glob("*/observations_clean.csv"):
        d = pd.read_csv(f)
        if "period" in d and f.parent.name != "V1":
            assert (d["period"] >= 2021 * 4).all(), f
    R = pd.read_csv(E / "E119_REGIONAL_MODELING_DATASET.csv")
    for c in [c for c in R.columns if c.endswith("__period")]:
        per = R[c].dropna().astype(str)
        per = per[per.str.fullmatch(r"\d{4}-Q[1-4]")]                       # C1 is an advisory state, not a period
        assert (per.map(_q) >= 2021 * 4).all(), c
    # computed YoY needs a 2021+ base, so it starts in 2022 (PSA-published CPI YoY is the declared exception)
    yoy = pd.read_csv(E / "out" / "indicators" / "C3" / "observations_clean.csv")
    assert yoy.loc[yoy["feature"].str.endswith("_yoy_pct"), "period"].min() >= 2022 * 4


def test_values_trace_to_clean_observations():
    """Every provincial dataset value equals a cleaned observation of that unit and period: no fill, no imputation."""
    obs = pd.concat([pd.read_csv(f) for f in (E / "out" / "indicators").glob("*/observations_clean.csv") if f.parent.name not in ("H1", "V1")])
    obs = obs.assign(pl=obs["period"].map(lambda p: f"{int(p) // 4}-Q{int(p) % 4 + 1}")).set_index(["feature", "unit", "pl"])["value"]
    Pv = pd.read_csv(E / "E119_PROVINCIAL_VULNERABILITY_DATASET.csv")
    checked = 0
    for c in [c[:-8] for c in Pv.columns if c.endswith("__period")]:
        for _, r in Pv[Pv[c].notna()].iterrows():
            assert obs.loc[(c, r["province"], r[f"{c}__period"])] == pytest.approx(r[c], rel=1e-8, abs=1e-8), (c, r["province"])
            checked += 1
    assert checked > 1000


def test_provincial_dataset_has_no_label_and_no_copied_coarse_values():
    Pv = pd.read_csv(E / "E119_PROVINCIAL_VULNERABILITY_DATASET.csv")
    assert set(Pv["province"]) == PROVS and len(Pv) == 5 * Pv["origin"].nunique()
    assert not [c for c in Pv.columns if c.startswith(("y_", "H1_", "E1_", "E2_", "region_", "oni", "typhoons_PAR", "news_gdelt", "unemployment"))]
    G = pd.read_csv(E / "E119_GEOGRAPHIC_ALIGNMENT_REPORT.csv")
    coarse = G[G["source_resolution"].isin(["national", "region", "global/national", "region proxy"])]
    assert not coarse["used_in_provincial"].any()
    assert not G["copied_across_provinces"].any()
    # within an origin, a feature never takes one identical value in all five provinces unless it is a genuine count of 0
    for c in [c[:-8] for c in Pv.columns if c.endswith("__period")]:
        same = Pv.groupby("origin")[c].agg(lambda s: s.notna().sum() == 5 and s.nunique() == 1 and s.iloc[0] != 0)
        assert same.mean() < .5, c


def test_twelve_indicators_mapped():
    from app.ml.inference import firi as FI
    ipr = pd.read_csv(E / "E119_INDICATOR_PREPROCESSING_REPORT.csv").set_index("indicator")
    assert set(FI.LABELS) <= set(ipr.index)
    for code, label in FI.LABELS.items():
        assert ipr.loc[code, "label"] == label
        assert ipr.loc[code, "clean_observations_2021plus"] > 0, code
        assert (E / "out" / "indicators" / code / "observations_clean.csv").exists(), code
    mp = pd.read_csv(E / "E119_12_INDICATOR_DATA_MAPPING.csv")
    assert set(FI.LABELS) <= set(mp["indicator"])
    assert mp["relationship"].str.startswith(("direct", "supporting", "unassigned")).all()
    fao = pd.read_csv(E / "E119_FAO_DIMENSION_MAPPING.csv")
    assert set(fao["indicator"]) == set(FI.LABELS)


def test_regional_dataset_shape_and_target():
    R = pd.read_csv(E / "E119_REGIONAL_MODELING_DATASET.csv")
    assert set(R["lead"]) == {1, 2}
    y = R[R["y_bl_hunger"].notna()]
    assert len(y) == 39
    assert (R.loc[R["H1_bl_latest_quarter"].notna(), "H1_bl_latest_quarter"].map(_q) <= R.loc[R["H1_bl_latest_quarter"].notna(), "t"]).all()
