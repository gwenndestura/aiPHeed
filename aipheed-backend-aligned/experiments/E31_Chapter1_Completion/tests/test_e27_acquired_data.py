"""E27: the acquired public data are hash-consistent, in-window, and pass the outcome adapter (which refuses, never
filters). Real files only; nothing is fetched here."""
import hashlib
import json

import pandas as pd
import pytest

import _paths  # noqa: F401
from _paths import EXP

# E28: the acquired public data stay in E27 (read-only, hash-listed there); E28 does not copy them.
ACQ_ROOT = EXP.parent / "E27_Resolve_Forecasting_Failures"
from app.quarterly import outcomes as OC

VAL = ACQ_ROOT / "acquisition" / "validated"


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_raw_files_match_the_acquisition_manifest():
    rows = [json.loads(l) for l in (ACQ_ROOT / "acquisition" / "ACQUISITION_MANIFEST.jsonl").read_text().splitlines() if l]
    assert len(rows) >= 6
    for r in rows:
        assert _sha(ACQ_ROOT / r["file"].replace("\\", "/")) == r["sha256"], r["file"]
        assert not str(r.get("publication_date", "")).startswith(r["retrieved_utc"][:10])   # never the retrieval day


@pytest.mark.parametrize("name", ["psa_subsistence_families_2021_2023", "psa_subsistence_population_2021_2023",
                                  "psa_bottom30_cpi_yoy_2021_2026H1"])
def test_validated_tables_match_their_metadata(name):
    meta = json.loads((VAL / f"{name}.meta.json").read_text())
    assert _sha(VAL / f"{name}.csv") == meta["sha256"]
    assert meta["limitations"]


def test_bottom30_series_is_complete_and_inside_the_window():
    b = pd.read_csv(VAL / "psa_bottom30_cpi_yoy_2021_2026H1.csv")
    assert b["month"].min() == "2021-01" and b["month"].max() == "2026-06"
    assert len(b) == 6 * 2 * 66 and b["yoy_pct"].notna().all()


def test_real_subsistence_file_passes_the_outcome_adapter_and_a_2018_row_is_refused():
    f = _paths.BD / "data" / "inputs" / "psa_subsistence_population_2021_2023.csv"
    raw = f.read_bytes()
    df, rep = OC.validate("psa_subsistence_incidence", raw, authorized_sha256=_sha(f), authorized_until="2026-06-30")
    assert rep["rows"] == 10 and rep["reference_min"] == "2021-01-01"
    bad = raw + b"PH040100000,2018,3.0,30.0,2019-12-06\n"
    with pytest.raises(OC.OutcomeRefused):
        OC.validate("psa_subsistence_incidence", bad, authorized_sha256=hashlib.sha256(bad).hexdigest(),
                    authorized_until="2026-06-30")


def test_sws_sample_size_table_names_real_rounds_and_never_guesses():
    n = pd.read_csv(VAL / "sws_round_sample_sizes_partial.csv")
    # E31: the E27 table describes the rounds of input vintage 1 (to 2026-Q2); the September 2026 round added in
    # vintage 2 has its sample size verified on its SWS release (data_acquired/sws/sws_rounds_2026_verified.csv)
    r = pd.read_csv(_paths.BD / "data" / "inputs_vintage1_e29" / "sws_rounds.csv")
    assert set(n["round"]) == set(r["round"])
    v2 = pd.read_csv(_paths.BD / "data" / "inputs" / "sws_rounds.csv")
    new = set(v2["round"]) - set(r["round"])
    ver = pd.read_csv(EXP / "data_acquired" / "sws" / "sws_rounds_2026_verified.csv")
    assert new == {"September 2026 SWS Survey"} and new <= set(ver["round"])
    assert ver["n_balance_luzon"].isin([300, 600]).all() and ver["source_url"].str.startswith("https://sws.org.ph").all()
    unknown = n[n["status"] == "UNKNOWN"]
    assert unknown["n_balance_luzon"].isna().all() and unknown["n_total"].isna().all()
    known = n[n["status"].isin(["VERIFIED_SECONDARY", "DERIVED_FROM_MARGIN"])]
    assert known["n_balance_luzon"].isin([300, 360, 600]).all() and known["source_url"].notna().all()


def test_unopened_enns_files_are_hash_listed_only():
    rows = [json.loads(l) for l in (ACQ_ROOT / "acquisition" / "ACQUISITION_MANIFEST.jsonl").read_text().splitlines() if l]
    enns = [r for r in rows if r["source_id"].startswith("enns2021_provincial_")]
    assert {r["source_id"] for r in enns} == {"enns2021_provincial_batangas", "enns2021_provincial_cavite"}
    assert all("NOT OPENED" in r["note"] for r in enns)
