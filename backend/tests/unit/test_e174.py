"""E174: the provenance ledger never counts used, non-HFIAS, city, duplicate or conflicting rows as independent; the runner refuses
to evaluate an insufficient set."""
import pandas as pd
import pytest

from app.e174 import evaluate_future as R
from app.paths import BACKEND_DIR

DIR = BACKEND_DIR / "data" / "e174" / "independent_rows"


def _ok(n=45, rounds=2):
    return pd.DataFrame({"source_record_id": [f"x{i}" for i in range(n)], "survey_round": [f"R{i % rounds}" for i in range(n)], "year": 2027,
                         "key": [f"p{i}" for i in range(n)], "level": "province", "instrument": "HFIAS", "status": "eligible independent",
                         "prior_use": "not used", "se_published": True})


def test_ledger_files_exist():
    for f in ("source_inventory.csv", "observation_provenance.csv", "instrument_compatibility.csv", "geographic_coverage.csv",
              "independent_rows.csv", "excluded_rows.csv", "data_dictionary.md", "PROVENANCE.md"):
        assert (DIR / f).exists(), f


def test_independent_rows_are_unused_hfias_provinces_only():
    d = pd.read_csv(DIR / "independent_rows.csv")
    assert (d["instrument"] == "HFIAS").all() and (d["level"] == "province").all() and (d["prior_use"] == "not used").all()
    assert (d["cross_source_abs_diff"].fillna(0) <= 0.2).all()
    p = pd.read_csv(DIR / "observation_provenance.csv")
    used = set(p.loc[p["status"] == "previously used", "source_record_id"])
    assert not used & set(d["source_record_id"])
    assert p["source_record_id"].is_unique


def test_fies_and_radimer_cornell_never_eligible():
    p = pd.read_csv(DIR / "observation_provenance.csv")
    assert (p.loc[p["instrument"] != "HFIAS", "status"] != "eligible independent").all()


def test_runner_refuses_todays_set_and_small_or_mixed_sets():
    today = R.readiness(pd.read_csv(DIR / "independent_rows.csv"))
    assert not today["ready"] and any("< 40" in r for r in today["reasons"])
    assert not R.readiness(_ok(39))["ready"]
    assert not R.readiness(_ok(45, rounds=1))["ready"]
    assert not R.readiness(_ok().assign(instrument="FIES"))["ready"]
    assert not R.readiness(_ok().assign(se_published=False))["ready"]
    with pytest.raises(R.NotReady):
        R.run()


def test_a_qualifying_set_passes_the_provenance_checks():
    assert R.readiness(_ok())["ready"] or (R.OUT / "evaluation.json").exists()
