"""E29: reachability and outcome eligibility (Objective 2), target-version separation (D10), source policy (D8),
leaky-label safeguards (D9)."""
import ast
import json

import pandas as pd
import pytest

from _paths import EXP

BD = EXP / "backend_dev"


# ------------------------------------------------------------------ reachability / outcome eligibility
def test_c6_gap_counts_rows_as_written_and_dates_dependence_aware():
    from app.quarterly.reachability import c6_gap, lead_counts

    rows = []
    for t in range(9):                                   # 9 dates x 5 provinces; LOW on 4 dates, one province each
        for p in range(5):
            rows.append({"lead": 1, "t": f"d{t}", "province_code": p, "y": 0 if (t < 4 and p == 0) else 1})
    for p in range(5):                                   # a 10th date where ALL five provinces are LOW (one regional event)
        rows.append({"lead": 2, "t": "x", "province_code": p, "y": 0})
    lc = lead_counts(pd.DataFrame(rows)).set_index("lead")
    g1 = c6_gap(lc.loc[1].to_dict() | {"lead": 1})
    assert g1["as_written"]["additional_LOW_rows"] == 1 and g1["dependence_aware"]["additional_LOW_dates"] == 1
    g2 = c6_gap(lc.loc[2].to_dict() | {"lead": 2})
    # five LOW rows on ONE date satisfy C6 as written but are one regional event: 4 more LOW dates needed
    assert g2["as_written"]["additional_LOW_rows"] == 0 and g2["dependence_aware"]["additional_LOW_dates"] == 4


def test_e28_reproduced_reachability_lead1_is_one_low_short():
    d = json.loads((EXP / "runs" / "e29_reachability.json").read_text(encoding="utf-8"))
    l1 = d["T1_A"]["by_lead"][0]
    assert l1["counts"] == {"lead": 1, "dates": 9, "rows": 45, "HIGH_rows": 41, "LOW_rows": 4, "LOW_dates": 4,
                            "LOW_rows_per_LOW_date": 1.0}
    assert l1["as_written"]["additional_LOW_rows"] == 1 and l1["as_written"]["additional_dates"] == 0
    assert [r["as_written"]["additional_LOW_rows"] for r in d["T1_A"]["by_lead"]] == [1, 3, 3, 3, 4, 4]


def test_skill_needs_far_more_dates_than_c6_counts():
    from app.quarterly.reachability import dates_for_skill, min_dates_any_significance

    assert min_dates_any_significance(0.05) == 5
    assert dates_for_skill(0.9) == 8 and dates_for_skill(0.7) > 30 and dates_for_skill(0.5) is None


def test_new_outcome_eligibility_rules():
    from app.quarterly.reachability import check_new_outcome

    T = pd.Timestamp
    ok = check_new_outcome("2026-Q4", "T1_A", T("2027-01-20"), T("2026-10-02"), ("2021-Q1", "2026-Q4"), {"2026-Q2"},
                           quarter_end=T("2026-12-31"))
    assert ok.eligible
    cases = {
        "DUPLICATE_QUARTER": check_new_outcome("2026-Q2", "T1_A", T("2026-08-01"), T("2026-04-02"), ("2021-Q1", "2026-Q4"), {"2026-Q2"}),
        "OUTSIDE_AUTHORIZED_WINDOW": check_new_outcome("2027-Q1", "T1_A", T("2027-04-20"), T("2027-01-02"), ("2021-Q1", "2026-Q4"), set()),
        "FORECAST_SEALED_AFTER_OUTCOME_PUBLICATION": check_new_outcome("2026-Q4", "T1_A", T("2027-01-20"), T("2027-01-21"), ("2021-Q1", "2026-Q4"), set()),
        "TARGET_NOT_APPROVED": check_new_outcome("2026-Q4", "T2", T("2027-01-20"), T("2026-10-02"), ("2021-Q1", "2026-Q4"), set()),
        "PUBLICATION_DATE_UNKNOWN": check_new_outcome("2026-Q4", "T1_A", None, T("2026-10-02"), ("2021-Q1", "2026-Q4"), set()),
        "FORECAST_SEALED_AFTER_TARGET_QUARTER_ENDED": check_new_outcome("2026-Q4", "T1_A", T("2027-03-01"), T("2027-01-05"), ("2021-Q1", "2026-Q4"), set(), quarter_end=T("2026-12-31")),
    }
    for reason, res in cases.items():
        assert not res.eligible and res.reason.startswith(reason), (reason, res)


# ------------------------------------------------------------------ targets (D10)
def test_target_registry_keeps_food_insecurity_hunger_and_price_pressure_apart():
    from app.quarterly.targets import TARGETS, describe, wording_violations

    assert TARGETS["T2"]["status"] == "EXPLORATORY_INDICATOR" and TARGETS["T2"]["measures_food_insecurity_directly"] is False
    assert TARGETS["T1_A"]["status"] == "APPROVED" and "regional" in TARGETS["H"]["geography"]
    assert wording_violations("T2", "Relative food-price pressure; never a food-insecurity forecast.") == []
    assert wording_violations("T2", "Constructed price pressure, not food insecurity.") == []
    assert "food insecurity" in wording_violations("T2", "High food insecurity in Quezon")
    assert "provincial hunger" in wording_violations("H", "Batangas provincial hunger rose")
    with pytest.raises(KeyError):
        describe("T3")


# ------------------------------------------------------------------ source policy (D8)
def test_source_policy_versions():
    from app.news.policy import additions_only_fn, credible_fn, load

    assert load()["active"] == "v1"
    v1, v2 = credible_fn("v1"), credible_fn("v2")
    for d in ("tribune.net.ph", "verafiles.org", "pco.gov.ph", "laguna.gov.ph"):
        assert not v1(d) and v2(d), d
    for d in ("newsinfo.inquirer.net", "pna.gov.ph", "da.gov.ph"):
        assert v1(d) and v2(d)
    for d in ("facebook.com", "ocregister.com", "spot.ph"):
        assert not v2(d)
    add = additions_only_fn("v2")
    assert add("tribune.net.ph") and not add("newsinfo.inquirer.net")
    assert credible_fn().version == "v1"


def test_collected_articles_record_the_admitting_policy_version(tmp_path):
    from datetime import datetime, timezone

    from app.news import sources as S
    from app.news.collector import Collector
    from app.news.policy import credible_fn
    from app.news.store import NewsStore

    class Src:
        name, cap = "fake", 100

        def search(self, q, a, b):
            items = [{"source_item_id": "1", "title": "Batangas rice price", "link": "l1", "source_domain": "tribune.net.ph",
                      "published_raw": "2021-02-02T03:00:00+00:00"},
                     {"source_item_id": "2", "title": "Batangas fish kill", "link": "l2", "source_domain": "pna.gov.ph",
                      "published_raw": "2021-02-03T03:00:00+00:00"}]
            got = [i for i in items if a.isoformat() <= i["published_raw"][:10] < b.isoformat()]
            return S.FetchResult("fake", S.OK if got else S.EMPTY, items=got, n_raw=len(got))

    for ver, expect in (("v1", {"Batangas fish kill"}), ("v2", {"Batangas fish kill", "Batangas rice price"})):
        st = NewsStore(tmp_path / ver)
        Collector(st, [Src()], authorized_until="2026-Q2", now=datetime(2026, 7, 5, tzinfo=timezone.utc),
                  credible=credible_fn(ver), geocode=lambda t: "PH040500000").run("backfill", ["2021-Q1"], provinces=["Batangas"])
        assert {a["title"] for a in st.articles.values()} == expect
        assert {a["source_policy"] for a in st.articles.values()} == {ver}


# ------------------------------------------------------------------ leaky label path (D9)
def test_legacy_label_generation_is_refused_by_default(monkeypatch):
    from app.ml.features import label_generator, label_guard

    monkeypatch.delenv(label_guard.ENV, raising=False)
    with pytest.raises(label_guard.LeakyLabelError):
        label_generator.generate_labels()
    with pytest.raises(label_guard.LeakyLabelError):
        label_guard.assert_not_leaky(pd.DataFrame({"label_stress": [1], "global_threshold": [14.6]}), "test")
    ok = pd.DataFrame({"label": [1]})
    assert label_guard.assert_not_leaky(ok, "test") is ok
    monkeypatch.setenv(label_guard.ENV, "1")
    label_guard.assert_not_leaky(pd.DataFrame({"global_threshold": [14.6]}), "legacy reproduction")


def test_legacy_loaders_call_the_guard_and_valid_paths_never_import_the_leaky_code():
    for f in ("app/ml/training/trainer.py", "app/ml/training/evaluator.py", "app/ml/features/feature_selector.py"):
        assert "assert_not_leaky" in (BD / f).read_text(encoding="utf-8"), f
    valid = [EXP / "runner" / "e28_evaluate.py"] + list((BD / "app" / "quarterly").glob("*.py")) + \
        list((BD / "app" / "news").glob("*.py"))
    for f in valid:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                names.add(n.module or "")
                names |= {a.name for a in n.names}
            elif isinstance(n, ast.Import):
                names |= {a.name for a in n.names}
        assert not any("label_generator" in x or x == "generate_labels" for x in names), f
    g = json.loads((BD / "config" / "governing_model.json").read_text(encoding="utf-8"))
    assert g["e29_leakage_flag"]["status"] == "LEGACY_LEAKY_TARGET"
