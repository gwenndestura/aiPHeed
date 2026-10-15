"""E28 section 5.5: the DA province brief on representative scenarios. Each must give an understandable, defensible,
proportionate result (no category without validation, missing news is not low risk, missing inputs give no estimate)."""
import _paths  # noqa: F401
from app.quarterly.da_brief import province_brief, signal

BASE = dict(province="Batangas", target_quarter="2026-Q4", lead=1, origin="2026-10-01", info_cutoff="2026-09-30",
            tau=15.0, sd_S1=3.0, lo80_S1=13.0, hi80_S1=21.0, evidence_status="EXPERIMENTAL",
            last_round="June 2026 SWS Survey", last_round_published="2026-09-10", last_cpi_month="2026-06",
            news_quarter="2026-Q2", news_status="COMPLETE", news_articles_in_fssi=12, gov_missing=[],
            horizon_determination="not determinable on the available outcomes")


def test_rising_provincial_pressure_prompts_review_not_allocation():
    b = province_brief({**BASE, "p": 0.86, "mu_H": 17.0, "mu_D": 1.2, "previous_D": 0.1})
    assert b["category"] is None and "No HIGH/LOW category" in b["category_withheld_reason"]
    assert b["signal"] == "STRONG" and b["price_trend"] == "rising"
    assert b["attention"] == "REVIEW_RECOMMENDED"
    assert "Do not allocate resources on this estimate alone" in b["suggested_use"]
    assert b["drivers"][0]["factor"].startswith("Provincial food-price")  # |2.4| > |2.0|: largest first
    assert abs(sum(d["contribution"] for d in b["drivers"]) - (17.0 - 15.0 + 2 * 1.2)) < 1e-9
    assert "not proof of cause" in b["driver_method"]
    assert "does not replace official" in b["disclaimer"]


def test_little_change_and_regional_driver_gives_monitoring():
    b = province_brief({**BASE, "p": 0.7, "mu_H": 16.0, "mu_D": -0.2, "previous_D": -0.1})
    assert b["price_trend"] == "little change" and b["attention"] == "MONITOR"
    assert any(d["direction"] == "lowers" for d in b["drivers"])


def test_uncertain_estimate_is_called_uncertain():
    b = province_brief({**BASE, "p": 0.5, "mu_H": 15.0, "mu_D": 0.0})
    assert b["signal"] == "UNCERTAIN" and b["attention"] == "UNCERTAIN"
    assert any("cannot distinguish" in x for x in b["limitations"])
    assert signal(0.2) == "STRONG" and signal(0.3) == "MODERATE" and signal(None) is None


def test_quarter_with_insufficient_news_is_flagged_not_read_as_low_risk():
    b = province_brief({**BASE, "p": 0.25, "mu_H": 13.0, "mu_D": -0.3, "news_status": "COMPLETE_NO_USABLE_EVIDENCE",
                        "news_articles_in_fssi": 0})
    assert "missing evidence, not low risk" in b["data_coverage"]["news"]
    assert b["evidence_sufficiency"].startswith("LIMITED") and "news evidence insufficient" in b["evidence_sufficiency"]
    assert "not evidence that households are food secure" in b["suggested_use"]


def test_missing_government_indicators_give_no_estimate():
    b = province_brief({**BASE, "p": None, "mu_H": None, "mu_D": None,
                        "gov_missing": ["September 2026 SWS round", "July-November 2026 provincial CPI"]})
    assert b["estimate"] is None and b["category"] is None and b["drivers"] == []
    assert b["attention"] == "NO_ESTIMATE" and "missing" in b["evidence_sufficiency"]
    assert "September 2026 SWS round" in b["missing_inputs"]


def test_only_a_validated_lead_gets_a_category():
    b = province_brief({**BASE, "p": 0.9, "mu_H": 18.0, "mu_D": 0.5, "evidence_status": "VALIDATED"})
    assert b["category"] == "HIGH" and b["attention"] == "VALIDATED_FORECAST"
