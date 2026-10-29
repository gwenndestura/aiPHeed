"""
tests/integration/test_release_dates_evidence.py
------------------------------------------------
Safeguards of the PSA provincial CPI release-date record (ERRATUM_ROOT_CAUSE_RELEASE_DATES E3):
- missing or unreviewed dates are never `confirmed`; confirmation needs the owner's two yes marks and a saved copy;
- the release's own date field is used, kept apart from page capture timestamps;
- a CPI month the model used is never shown released after its issue date, and the cut-off rows follow the evidence;
- regional sources stand for a province only when they state its figures; other provinces' releases never do;
- nothing from reference month 2026-10 onward is collected or kept;
- the re-score stays blocked until all 180 rows are confirmed;
- the frozen protocol and addendum keep their hashes; corrections live in the separate erratum.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
EV = LT / "data" / "psa_release_evidence"
V2 = LT / "data" / "psa_cpi_release_dates_TO_FILL_v2.csv"
MAP = LT / "out" / "release_dates_map.json"
PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
pytestmark = pytest.mark.skipif(not MAP.exists(), reason="release-date map missing")


@pytest.fixture(scope="module")
def v2():
    return pd.read_csv(V2, dtype=str).fillna("")


@pytest.fixture(scope="module")
def cat():
    return pd.read_csv(EV / "wayback_catalog.csv", dtype=str).fillna("")


def test_unreviewed_or_missing_dates_are_never_confirmed(v2):
    conf = v2[v2["status"] == "confirmed"]
    assert (conf["confirmed_by_owner"].str.lower() == "yes").all()
    assert (conf["is_release_date_printed_on_document"].str.lower() == "yes").all()
    assert ((conf["saved_evidence_filename"] != "") | (conf["archive_evidence_file"] != "")).all()
    nodate = (v2["release_date_YYYY-MM-DD"] == "") & (v2["archive_release_date"] == "")
    assert (v2.loc[nodate, "status"] == "unresolved").all()
    assert set(v2["status"]) <= {"confirmed", "awaiting_owner_review", "unresolved"} and len(v2) == 180


def test_release_date_field_kept_apart_from_capture_time(cat, v2):
    import sys
    sys.path.insert(0, str(LT / "runner"))
    from release_pages_fetch import parse
    dated = cat[cat["release_date_iso"] != ""]
    assert len(dated) and dated["release_date_label"].str.contains(r"(?i)release").all()
    for r in dated.itertuples():                                         # the date is re-read from the saved page's release field
        p = parse((EV / r.file).read_text(encoding="utf-8", errors="replace"))
        assert p["release_date_iso"] == r.release_date_iso and p["release_date_label"], r.file
    for r in v2[v2["archive_release_date"] != ""].itertuples():
        f = EV / r.archive_evidence_file.replace("psa_release_evidence/", "")
        assert f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() == r.archive_file_sha256


def test_cpi_months_used_were_released_by_issue(v2):
    used = v2[(v2["role"] == "included_by_day10") & (v2["archive_available_by_issue"] != "")]
    assert (used["archive_available_by_issue"] == "yes").all()          # a "no" here would be a timing violation to report
    owner = v2[(v2["role"] == "included_by_day10") & (v2["release_date_YYYY-MM-DD"] != "")]
    assert (owner["release_date_YYYY-MM-DD"] < owner["must_be_released_before"]).all()
    # cut-off row: Rizal July 2023 was released 2023-08-06, after the 2023-08-03 issue, so the day-10 rule rightly left it out
    rz = v2[(v2["reference_month"] == "2023-07") & (v2["province"] == "Rizal")].iloc[0]
    assert rz["role"] == "could_be_added" and rz["archive_release_date"] == "2023-08-06" and rz["archive_available_by_issue"] == "no"


def test_regional_sources_only_when_they_state_the_province(v2, cat):
    for r in v2[v2["archive_evidence_level"] != ""].itertuples():
        c = cat[cat["url"] == r.archive_source_url].iloc[0]
        named = [p for p in PROV if p.lower() in c["title"].lower()]
        assert c["series"] == "all_income" and "lucena" not in c["title"].lower()
        if r.archive_evidence_level == "province_release_page":
            assert named == [r.province], (r.province, c["title"])
        else:
            assert r.archive_evidence_level == "regional_page_states_province" and not named
            assert r.province in c["provinces_with_figures"].split(";")


def test_no_reference_month_from_2026_10(v2, cat):
    assert (v2["reference_month"] < "2026-10").all()
    assert not (cat["reference_month"].replace("", "0000") >= "2026-10").any()
    for f in (EV / "wayback").glob("*.html"):
        title = re.search(r"<title>(.*?)</title>", f.read_text(encoding="utf-8", errors="replace"), re.S | re.I)
        if title and re.search(r"(?i)(october|november|december)\s*,?\s*2026", title.group(1)):
            pytest.fail(f"sealed-period release kept: {f.name}")


def test_rescore_blocked_and_frozen_files_unchanged(v2):
    m = json.loads(MAP.read_text())
    assert m["rescore_can_run"] is False and not (v2["status"] == "confirmed").all()
    r = json.loads((LT / "out" / "release_dates_review.json").read_text())
    assert r["rescore_can_run"] is False
    for doc, sha in (("PROTOCOL_LEAD2_ROOT_CAUSE.md", "ROOT_CAUSE_SHA256.txt"), ("ADDENDUM_ROOT_CAUSE_RELEASE_DATES.md", "ROOT_CAUSE_ADDENDUM_SHA256.txt")):
        assert hashlib.sha256((LT / doc).read_bytes()).hexdigest() == (LT / "runner" / sha).read_text().strip()
    assert (LT / "ERRATUM_ROOT_CAUSE_RELEASE_DATES.md").exists()
