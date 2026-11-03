"""HFIAS target pipeline: parsed values against the published FNRI tables, instrument separation, the workbook check,
release-date cutoffs of every feature, the train/test split and the protocol lock."""
from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from app.hfias import CLEAN, OUT, RAW
from app.hfias import panel as P
from app.hfias import study as S

F15 = pd.read_csv(CLEAN / "fnri2015_hfias.csv").set_index("name")
ENNS = pd.read_csv(CLEAN / "enns_hfias.csv")


def test_fnri2015_matches_published_calabarzon():
    assert (F15.loc["CALABARZON", ["food_secure_pct", "mild_pct", "moderate_pct", "severe_pct"]].tolist()
            == [44.4, 12.6, 24.0, 19.0])
    assert F15.loc["Quezon", "mod_sev_pct"] == pytest.approx(48.8) and F15.loc["Philippines", "insecure_pct"] == pytest.approx(66.1)
    s = F15[["food_secure_pct", "mild_pct", "moderate_pct", "severe_pct"]].sum(axis=1).dropna()
    assert s.between(99.4, 100.6).all() and (F15["level"] == "province").sum() == 78


def test_enns_parsed_from_fnri_reports():
    assert ENNS.groupby("year").size().to_dict() == {2018: 38, 2019: 38}
    lag = ENNS[(ENNS["area"] == "Laguna") & (ENNS["year"] == 2018)].iloc[0]
    assert (lag["food_secure_pct"], lag["moderate_pct"], lag["severe_pct"]) == (60.7, 18.3, 7.9)
    q = ENNS[(ENNS["area"] == "Quezon") & (ENNS["year"] == 2019)].iloc[0]
    assert (q["food_secure_pct"], q["mild_pct"], q["moderate_pct"], q["severe_pct"]) == (38.1, 17.8, 30.3, 13.7)
    cats = ENNS.dropna(subset=["food_secure_pct"])
    assert cats["sum_check"].between(99.4, 100.6).all()
    assert set(ENNS["instrument"]) == {"HFIAS"}


def test_fies_kept_separate_from_hfias():
    q = ENNS[(ENNS["area"] == "Quezon") & (ENNS["year"] == 2019)].iloc[0]
    assert q["fies_mod_sev_pct"] == pytest.approx(32.2) and q["mod_sev_pct"] == pytest.approx(44.0)
    o = P.outcomes()
    assert "fies_mod_sev_pct" not in o.columns


def test_workbook_enns_column_is_hfias_moderate_only():
    """The owner workbook's ENNS 'moderate-to-severe' values equal FNRI's HFIAS *moderate* category (RDP mislabel)."""
    w = pd.read_csv(RAW.parent.parent / "fi_labels" / "raw" / "owner_supplied" / "sheet_ENNS_Provincial.csv").set_index("Province")
    for prov, yr in (("Laguna", 2018), ("Quezon", 2019), ("Rizal", 2019)):
        e = ENNS[(ENNS["area"] == prov) & (ENNS["year"] == yr)].iloc[0]
        assert w.loc[prov, "Moderate-to-severe food insecurity (%)"] == e["moderate_pct"]
        assert w.loc[prov, "Severe food insecurity (%)"] == e["severe_pct"]


def test_panel_rows_and_matching():
    o = P.outcomes()
    assert o["year"].value_counts().to_dict() == {2019: 30, 2018: 22}
    assert set(o.attrs["unmatched_enns"]) == {"davao occidental", "dinagat islands"}        # created after 2015
    assert not o["key"].str.contains("city").any()


@pytest.mark.parametrize("lead", [1, 2, 3, 4])
def test_features_respect_release_dates(lead):
    o = P.outcomes().head(6)
    X = P.features(o, lead)
    for _, r in X.iterrows():
        issue = pd.Timestamp(r["issue_date"])
        assert issue == pd.Timestamp(year=int(r["year"]), month=1, day=1) - pd.DateOffset(months=3 * (lead - 1))
        assert pd.Timestamp(f"{int(r['cpi_year_used']) + 1}-02-15") <= issue        # annual CPI published by then
    assert X["lead"].eq(lead).all()


def test_quarterly_production_uses_published_quarters_only():
    """2017-Q3 (ends 30 Sep) is public 45 days later, on 14 Nov 2017: the trailing window moves on that day, not before."""
    f = ("palay_corn_quarterly.csv", "Ecosystem/Croptype", ["Palay", "Corn"])
    before, on, later = (P._quarterly(*f, pd.Timestamp(d)).dropna() for d in ("2017-11-13", "2017-11-14", "2018-02-13"))
    assert not before.equals(on)
    assert on.equals(later)                                     # 2017-Q4 is public only from 14 Feb 2018


def test_study_split_is_chronological_and_disjoint():
    o = P.outcomes()
    tr, te = o[o["year"] == 2018], o[o["year"] == 2019]
    assert set(tr["key"]).isdisjoint(te["key"])


def test_protocol_lock_matches_code():
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    assert lock["protocol_sha256"] == S.protocol_sha()
    from app.paths import BACKEND_DIR
    code = hashlib.sha256((BACKEND_DIR / "app/hfias/study.py").read_bytes() + (BACKEND_DIR / "app/hfias/panel.py").read_bytes()).hexdigest()
    assert lock["code_sha256"] == code
