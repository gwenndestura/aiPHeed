"""
Unit tests for the plain-language report wording (app/services/plain_text.py).

Every output is checked for the technical words the DA-facing PDFs must not
contain and for typographic dashes or quotes.
"""

import pytest

from app.services import plain_text as pt

HIGH, ALERT = 0.50, 0.60

BANNED = [
    "SHAP", "LightGBM", "logistic regression", "TreeExplainer", "Shapley", "model output",
    "attributed share", "normalized", "served model", "nowcast", "province-quarter",
    "geocoded", "trigger tally", "keyword-matched", "limited signal", "FSSI",
    "Food Stress Sentiment Index", "label_cpi", "Equation", "decision threshold",
    "baseline", "published provinces",
]
TYPOGRAPHIC = ("—", "–", "‘", "’", "“", "”")


def clean(text: str) -> None:
    assert text.isascii(), text
    for ch in TYPOGRAPHIC:
        assert ch not in text
    low = text.lower()
    for word in BANNED:
        assert word.lower() not in low, f"banned word {word!r} in: {text}"


def t(key, pct, direction="increases_risk"):
    return {"key": key, "pct": pct, "direction": direction, "label": key}


QUEZON = [t("market", 98), t("employment", 2), t("climate", 0, "protective"),
          t("fish_kill", 0), t("ofw_remittance", 0)]
CAVITE = [t("market", 97), t("employment", 2), t("climate", 1, "protective"),
          t("fish_kill", 0), t("ofw_remittance", 0)]


def row(name, value, start=None, prev=None, withheld=False, main=("market", 97, "increases_risk")):
    return {"name": name, "value": value, "start": start, "prev": prev, "withheld": withheld,
            "mainKey": main[0] if main else None, "mainPct": main[1] if main else None,
            "mainDirection": main[2] if main else None}


# ---------------------------------------------------------------------------
# Scale, numbers and factor names
# ---------------------------------------------------------------------------

def test_risk_level_scale_and_rounding():
    assert pt.risk_level(0.6263, HIGH, ALERT) == "Alert"
    assert pt.risk_level(0.55, HIGH, ALERT) == "High"
    assert pt.risk_level(0.49, HIGH, ALERT) == "Not elevated"
    # Judged on the printed value, so a table never shows 0.60 as "High".
    assert pt.risk_level(0.5996, HIGH, ALERT) == "Alert"
    clean(pt.level_scale(HIGH, ALERT))


def test_change_wording_adds_up_and_handles_no_change():
    assert pt.describe_change(0.7812, 0.7257) == "decreased by 0.05 (from 0.78 to 0.73)"
    assert pt.describe_change(0.70, 0.74) == "increased by 0.04 (from 0.70 to 0.74)"
    assert pt.describe_change(0.731, 0.729) == "stayed the same (0.73)"
    assert pt.change_cell(0.7963, 0.7374) == "Down 0.06"
    assert pt.change_cell(0.70, 0.74) == "Up 0.04"
    assert pt.change_cell(0.731, 0.729) == "No change"
    assert pt.change_cell(None, 0.7) == "Not available"


def test_plain_factor_names_in_one_place():
    assert pt.PLAIN_FACTORS == {
        "market": "Food prices", "employment": "Jobs and employment",
        "climate": "Weather and climate", "fish_kill": "Fish kills",
        "ofw_remittance": "Remittances from OFWs",
    }
    assert pt.lower_first("Remittances from OFWs") == "remittances from OFWs"


def test_score_explainer_matches_the_training_label():
    text = pt.SCORE_EXPLAINER
    assert "0 to 1" in text and "not a measure of hunger" in text
    assert "two quarters in a row" in text and "past six years" in text
    clean(text)


# ---------------------------------------------------------------------------
# Key points
# ---------------------------------------------------------------------------

def test_key_points_region():
    rows = [row("Quezon", 0.7374, start=0.7963), row("Batangas", 0.6263, start=0.7842),
            row("Rizal", 0.55, start=0.53)]
    out = pt.compose_key_points(rows, "2026-Q3", "2026-Q2", HIGH, ALERT)
    assert 3 <= len(out) <= 5
    assert out[0] == ("In 2026 Q3, two of the three provinces are at the Alert level "
                      "(Quezon and Batangas). Rizal is at the High level.")
    assert "Quezon has the highest risk score (0.74) and Rizal the lowest (0.55)." in out
    assert "Food prices are the main factor behind the risk in every province, and they raise the risk." in out
    assert "Compared with 2026 Q2, the risk score decreased in two provinces and increased in Rizal." in out
    for s in out:
        clean(s)


def test_key_points_single_province():
    out = pt.compose_key_points([row("Quezon", 0.7374, start=0.7963, main=("market", 98, "increases_risk"))],
                                "2026-Q3", "2026-Q2", HIGH, ALERT)
    assert out == [
        "In 2026 Q3, the risk score for Quezon is 0.74, which is at the Alert level.",
        "Food prices are the main factor behind the score, accounting for about 98% of the "
        "factors, and they raise the risk.",
        "Compared with 2026 Q2, the risk score decreased by 0.06 (from 0.80 to 0.74).",
    ]


def test_key_points_withheld_and_missing_factors():
    rows = [row("Cavite", 0.72, start=0.78), row("Batangas", None, withheld=True, main=None)]
    out = " ".join(pt.compose_key_points(rows, "2026-Q3", "2026-Q2", HIGH, ALERT))
    assert "all one" not in out
    assert out.startswith("In 2026 Q3, the risk score for Cavite is 0.72, which is at the Alert level.")
    assert "Compared with 2026 Q2, the risk score decreased by" not in out
    assert "the risk score decreased in Cavite." in out
    assert ("Results for Batangas in 2026 Q3 are withheld by the reviewing team and are not "
            "shown in this report.") in out
    clean(out)
    empty = pt.compose_key_points([row("Rizal", 0.7, main=None)], "2026-Q3", None, HIGH, ALERT)
    assert all("main factor" not in s for s in empty)


# ---------------------------------------------------------------------------
# Trend, factors, profile, news, notes
# ---------------------------------------------------------------------------

def test_trend_paragraph_region_and_single():
    series = [
        {"name": "Cavite", "points": [{"quarter": "2026-Q2", "value": 0.7812},
                                      {"quarter": "2026-Q3", "value": 0.7257}]},
        {"name": "Batangas", "points": [{"quarter": "2026-Q2", "value": 0.7842},
                                        {"quarter": "2026-Q3", "value": 0.6263}]},
    ]
    text = pt.compose_trend_paragraph(series, "2026-Q2", "2026-Q3", "Figure 1")
    assert text.startswith("As shown in Figure 1, between 2026 Q2 and 2026 Q3 the risk score "
                           "decreased in both provinces.")
    assert "The largest change was in Batangas, where the score decreased by 0.15 (from 0.78 to 0.63)." in text
    clean(text)
    single = pt.compose_trend_paragraph(series[:1], "2026-Q2", "2026-Q3", "Figure 1")
    assert single == ("As shown in Figure 1, between 2026 Q2 and 2026 Q3 the risk score for "
                      "Cavite decreased by 0.05 (from 0.78 to 0.73).")
    one_point = [{"name": "Cavite", "points": [{"quarter": "2026-Q3", "value": 0.72}]}]
    assert "cannot be drawn" in pt.compose_trend_paragraph(one_point, "2026-Q3", "2026-Q3", "Figure 1")


def test_factors_province_plain_wording():
    text = pt.compose_factors_province("Cavite", "2026-Q3", CAVITE,
                                       [t("market", 94), t("employment", 6)], "2026-Q2",
                                       figure_label="Figure 2")
    assert text == (
        "As shown in Figure 2, food prices account for about 97% of the factors behind Cavite's "
        "risk score in 2026 Q3 and raise the risk. Jobs and employment account for about 2% and also raise the risk. Weather "
        "and climate account for about 1% and lower the risk. Fish kills and remittances from "
        "OFWs had no noticeable effect this quarter. Compared with 2026 Q2, the share of food "
        "prices rose from 94% to 97%."
    )
    clean(text)
    assert pt.compose_factors_province("Rizal", "2026-Q1", []) == (
        "No breakdown of the factors is available for Rizal in 2026 Q1.")


def test_factors_region_said_once_when_provinces_agree():
    provinces = [{"name": "Cavite", "triggers": CAVITE, "withheld": False},
                 {"name": "Quezon", "triggers": QUEZON, "withheld": False},
                 {"name": "Rizal", "triggers": None, "withheld": True}]
    out = pt.compose_factors_region(provinces, "2026-Q3")
    joined = " ".join(out)
    assert out[0] == ("In every province, food prices are the main factor, accounting for 97% "
                      "to 98% of the factors behind the score, and they raise the risk.")
    assert joined.count("food prices are the main factor") == 1
    assert "Jobs and employment come second everywhere, at about 2%, and raise the risk." in out
    assert "Weather and climate had a small effect (1%) and lowered the risk in Cavite." in out
    assert "Fish kills and remittances from OFWs had no noticeable effect this quarter in any province." in out
    assert "withheld by the reviewing team" in joined
    for s in out:
        clean(s)


def test_factors_region_names_a_province_that_differs():
    rizal = [t("employment", 55), t("market", 45)]
    out = pt.compose_factors_region(
        [{"name": "Cavite", "triggers": CAVITE, "withheld": False},
         {"name": "Laguna", "triggers": CAVITE, "withheld": False},
         {"name": "Rizal", "triggers": rizal, "withheld": False}], "2026-Q3")
    assert out[0].startswith("In Cavite and Laguna, food prices are the main factor")
    assert "In Rizal, the main factor is jobs and employment (55%), which raises the risk." in out


def test_profile_and_news():
    lead = pt.compose_profile_lead(
        [{"name": "Cavite", "population": 4344829, "poverty": 4.2},
         {"name": "Quezon", "population": 2229383, "poverty": 16.6}], "Table 3")
    assert lead == ("Table 3 gives basic facts about each province. Cavite has the largest "
                    "population (4,344,829), and Quezon has the highest poverty incidence (17%).")
    news = pt.compose_news([{"name": "Cavite", "count": 6, "incomplete": True, "withheld": False,
                             "mainKey": "market", "matched": 0, "newsShare": 3}], "2026-Q3", None)
    assert news == [
        "Six news reports about food conditions in Cavite were found for 2026 Q3.",
        "News-based information for this quarter is not yet complete.",
        "Information from news reports accounts for about 3% of the factors behind the score, "
        "so the score depends mainly on price and employment data.",
        "None of these reports was specifically about food prices.",
    ]
    # The share is stated as found; incompleteness is not given as its cause.
    assert not any("so news had little influence" in x for x in news)
    many = pt.compose_news([
        {"name": "Cavite", "count": 6, "incomplete": True, "withheld": False, "mainKey": "market", "matched": 2},
        {"name": "Batangas", "count": 0, "incomplete": False, "withheld": True, "mainKey": None, "matched": 0},
    ], "2026-Q3", "Table 4")
    assert "Table 4 lists up to three reports per province" in " ".join(many)
    for s in news + many:
        clean(s)


@pytest.mark.parametrize("lag,expected", [
    (1, "which is one quarter behind the current quarter (2026 Q4)."),
    (0, "which is the current quarter."),
])
def test_notes(lag, expected):
    out = pt.compose_notes("2026-Q3", "2026-Q4", lag, any_withheld=True)
    assert expected in out[1]
    assert out[-1].startswith("This report presents findings only.")
    assert any("withheld by the reviewing team" in s for s in out)
    for s in out:
        clean(s)


def test_counts_at_the_start_of_a_sentence_are_spelled_out():
    assert pt.count_lead(1, "news report") == "One news report"
    assert pt.count_lead(4, "news report") == "Four news reports"
    assert pt.count_lead(0, "news report") == "No news reports"
    assert pt.count_lead(12, "news report") == "12 news reports"


def test_news_only_factors_are_not_called_ineffective_when_news_is_incomplete():
    text = pt.compose_factors_province("Laguna", "2026-Q3", QUEZON, news_incomplete=True)
    assert "had no noticeable effect" not in text
    assert ("Weather and climate, fish kills, and remittances from OFWs are measured only from "
            "news reports, which are not yet complete for this quarter, so their effect cannot "
            "yet be judged.") in text
    complete = pt.compose_factors_province("Laguna", "2026-Q3", QUEZON)
    assert "had no noticeable effect this quarter" in complete
    clean(text)


def test_region_news_only_factors_when_news_is_incomplete():
    provinces = [{"name": "Cavite", "triggers": CAVITE, "withheld": False},
                 {"name": "Quezon", "triggers": QUEZON, "withheld": False}]
    out = " ".join(pt.compose_factors_region(provinces, "2026-Q3", news_incomplete=True))
    assert "no noticeable effect this quarter in any province" not in out
    assert "measured only from news reports, which are not yet complete" in out
    clean(out)


def test_news_share_range_across_provinces():
    rows = [{"name": n, "count": c, "incomplete": False, "withheld": False, "mainKey": "market",
             "matched": 0, "newsShare": sh} for n, c, sh in (("Cavite", 6, 3), ("Laguna", 8, 4))]
    out = pt.compose_news(rows, "2026-Q2", None)
    assert ("Information from news reports accounts for between 3% and 4% of the factors behind "
            "each province's score, so the score depends mainly on price and employment data.") in out
