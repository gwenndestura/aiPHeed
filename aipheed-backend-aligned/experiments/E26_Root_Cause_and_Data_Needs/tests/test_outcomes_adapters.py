"""New-outcome adapters (section F): every refusal path. SYNTHETIC files only; no real outcome is read."""
import hashlib

import pandas as pd
import pytest

import _paths  # noqa: F401
from app.quarterly import outcomes as OC


def csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, lineterminator="\n").encode()


def ok(kind, df, until="2026-06-30", **kw):
    b = csv(df)
    return OC.validate(kind, b, authorized_sha256=hashlib.sha256(b).hexdigest(), authorized_until=until, **kw)


def cbms():
    return pd.DataFrame({"lgu_code": ["041005000", "042103000", "043404000", "045624000", "045802000"],
                         "lgu_name": ["A", "B", "C", "D", "E"], "reference_year": [2024] * 5,
                         "households_assessed": [1000] * 5, "fies_moderate_severe_pct": [10.0, 20.0, 5.5, 40.0, 0.0],
                         "source_document": ["CBMS 2024 LGU report"] * 5, "publication_date": ["2025-06-30"] * 5})


def fnri():
    return pd.DataFrame({"province_code": list(OC.CALABARZON_PROVINCES), "survey": ["NNS 2023"] * 5,
                         "scale": ["FIES"] * 5, "reference_start": ["2023-01-01"] * 5,
                         "reference_end": ["2023-12-31"] * 5, "prevalence_pct": [30.0, 25.0, 45.0, 20.0, 35.0],
                         "n_households": [384] * 5, "publication_date": ["2024-08-01"] * 5})


def test_valid_files_pass():
    df, rep = ok("cbms_fies_lgu", cbms(), known_lgu_codes=set(cbms()["lgu_code"]))
    assert rep["lgus"] == 5 and rep["role"] == "outcome"
    _, rep = ok("fnri_provincial_fies", fnri())
    assert rep["reference_min"] == "2023-01-01"


def test_hash_must_match_and_be_complete():
    b = csv(fnri())
    with pytest.raises(OC.OutcomeRefused, match="64"):
        OC.validate("fnri_provincial_fies", b, authorized_sha256=hashlib.sha256(b).hexdigest()[:16],
                    authorized_until="2026-06-30")
    with pytest.raises(OC.OutcomeRefused, match="do not match"):
        OC.validate("fnri_provincial_fies", b, authorized_sha256=hashlib.sha256(b + b"x").hexdigest(),
                    authorized_until="2026-06-30")


def test_pre2021_rows_refuse_the_whole_file():
    df = pd.concat([fnri(), fnri().assign(survey="ENNS 2019", reference_start="2019-01-01", reference_end="2019-12-31")])
    with pytest.raises(OC.OutcomeRefused, match="before 2021"):
        ok("fnri_provincial_fies", df)


def test_rows_after_the_authorized_limit_refuse_the_whole_file():
    df = pd.concat([fnri(), fnri().assign(survey="later", reference_start="2026-07-01", reference_end="2026-09-30",
                                          publication_date="2026-12-01")])
    with pytest.raises(OC.OutcomeRefused, match="authorized limit"):
        ok("fnri_provincial_fies", df)


def test_geography_checks():
    with pytest.raises(OC.OutcomeRefused, match="non-CALABARZON"):
        ok("fnri_provincial_fies", fnri().assign(province_code=["PH137400000"] + list(OC.CALABARZON_PROVINCES)[1:]))
    with pytest.raises(OC.OutcomeRefused, match="outside CALABARZON"):
        ok("cbms_fies_lgu", cbms().assign(lgu_code=["137401000"] + list(cbms()["lgu_code"][1:])))
    with pytest.raises(OC.OutcomeRefused, match="142-LGU"):
        ok("cbms_fies_lgu", cbms(), known_lgu_codes={"041005000"})
    sws = pd.DataFrame({"quarter": ["2024-Q1"], "area": ["LUZON_ALL"], "hunger_pct": [15.0], "n_respondents": [300],
                        "fieldwork_end": ["2024-03-25"], "publication_date": ["2024-04-20"]})
    with pytest.raises(OC.OutcomeRefused, match="unknown SWS areas"):
        ok("sws_area_series", sws)


def test_publication_date_required_and_not_before_reference_end():
    with pytest.raises(OC.OutcomeRefused, match="publication date"):
        ok("fnri_provincial_fies", fnri().assign(publication_date=[""] + ["2024-08-01"] * 4))
    with pytest.raises(OC.OutcomeRefused, match="precedes"):
        ok("fnri_provincial_fies", fnri().assign(publication_date="2023-06-30"))


def test_values_never_filled_and_years_and_duplicates_checked():
    with pytest.raises(OC.OutcomeRefused, match="out-of-range"):
        ok("fnri_provincial_fies", fnri().assign(prevalence_pct=[30.0, None, 45.0, 20.0, 35.0]))
    with pytest.raises(OC.OutcomeRefused, match="out-of-range"):
        ok("fnri_provincial_fies", fnri().assign(prevalence_pct=[130.0, 25.0, 45.0, 20.0, 35.0]))
    with pytest.raises(OC.OutcomeRefused, match="reference years"):
        ok("cbms_fies_lgu", cbms().assign(reference_year=2023, publication_date="2024-06-30"))
    with pytest.raises(OC.OutcomeRefused, match="duplicate"):
        ok("fnri_provincial_fies", pd.concat([fnri(), fnri()]))
    with pytest.raises(OC.OutcomeRefused, match="missing columns"):
        ok("fnri_provincial_fies", fnri().drop(columns=["n_households"]))


def test_signal_adapter_is_labelled_as_signal_not_outcome():
    dr = pd.DataFrame({"province_code": ["PH040300000"], "event_name": ["Typhoon X"], "event_start": ["2024-10-22"],
                       "report_date": ["2024-11-05"], "affected_families": [120000]})
    _, rep = ok("dromic_affected", dr)
    assert rep["role"] == "signal"
