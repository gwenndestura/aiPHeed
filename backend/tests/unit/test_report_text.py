"""
Unit tests for the PDF report's text generation (app/services/report_text.py
and dashboard.compose_formal_interpretation).

Each function is checked on normal data, empty triggers, a withheld province,
a limited-signal province and a nonzero "other" share where those apply, and
every output is checked to be plain ASCII with no typographic dashes or quotes.
"""

import pytest

from app.services import report_text as txt
from app.services.dashboard import compose_formal_interpretation

HIGH, ALERT = 0.50, 0.60
TYPOGRAPHIC = ("\u2014", "\u2013", "\u2018", "\u2019", "\u201c", "\u201d")


def _t(label, pct, direction="increases_risk", key=None):
    return {"label": label, "pct": pct, "direction": direction, "key": key or label.lower()}


TRIGGERS = [_t("Market / Prices", 62, key="market"), _t("Climate Stress", 24, "protective", "climate"),
            _t("Employment", 10, key="employment"), _t("Fish Kill", 4, key="fish_kill"),
            _t("OFW Remittance", 0, key="ofw_remittance")]


def _clean(text: str) -> None:
    assert text.isascii(), text
    for ch in TYPOGRAPHIC:
        assert ch not in text


def _pts(*pairs, withheld=()):
    return [{"quarter": q, "value": v, "withheld": q in withheld} for q, v in pairs]


# ---------------------------------------------------------------------------
# compose_formal_interpretation (extended)
# ---------------------------------------------------------------------------

def test_formal_interpretation_withheld_reports_nothing_else():
    text = compose_formal_interpretation("Rizal", "2026-Q1", TRIGGERS, 12.0, withheld=True)
    assert text == "The SHAP breakdown for Rizal in 2026 Q1 is withheld from publication."
    _clean(text)


def test_formal_interpretation_empty_states_missing_breakdown():
    text = compose_formal_interpretation("Rizal", "2026-Q1", [])
    assert text.startswith("No SHAP breakdown is available for Rizal in 2026 Q1.")


def test_formal_interpretation_brief_other_share():
    text = compose_formal_interpretation("Cavite", "2026-Q3", TRIGGERS, 7.5, brief=True)
    assert "The 5 groups represent 92.5% of the total SHAP-explained output" in text
    assert "the remaining 7.5% comes from the Food Stress Sentiment Index features" in text
    _clean(text)


# ---------------------------------------------------------------------------
# compose_vintage
# ---------------------------------------------------------------------------

def test_vintage_states_lag_and_missing_inputs():
    text = txt.compose_vintage("2026-Q3", "2026-Q4", 1,
                               {"the news trigger proportions": ["Cavite", "Laguna"]}, 5)
    assert "latest quarter with published input data is 2026 Q3, 1 quarter behind" in text
    assert "the news trigger proportions (Cavite and Laguna)" in text
    assert "substitute zero" in text
    _clean(text)


def test_vintage_all_provinces_and_complete_inputs():
    every = txt.compose_vintage("2026-Q3", "2026-Q4", 2, {"x": ["A", "B"]}, 2)
    assert "x (all 2 provinces)" in every and "2 quarters behind" in every
    complete = txt.compose_vintage("2026-Q4", "2026-Q4", 0, {}, 5)
    assert "which is the current calendar quarter" in complete
    assert "All model inputs are present" in complete


# ---------------------------------------------------------------------------
# compose_summary / compose_province_summary
# ---------------------------------------------------------------------------

def _row(name, start, end, withheld=False, sq="2025-Q1", eq="2026-Q3"):
    return {"name": name, "start": start, "end": end, "withheldLatest": withheld,
            "startQuarter": sq, "endQuarter": eq}


def test_summary_normal():
    rows = [_row("Cavite", 0.70, 0.65), _row("Laguna", 0.55, 0.58), _row("Quezon", 0.80, 0.62)]
    top = {"label": "Market / Prices", "pct": 88, "direction": "increases_risk"}
    out = txt.compose_summary(rows, top, "2025-Q1", "2026-Q3", HIGH, ALERT)
    assert out[0] == ("In 2026 Q3, 2 of 3 published provinces are at or above the alert "
                      "threshold of 0.60: Cavite and Quezon.")
    assert "highest Risk Level score in 2026 Q3 is recorded for Cavite (0.650) and the lowest for Laguna (0.580)" in out[1]
    assert "largest change is observed for Quezon (-0.180, from 0.800 in 2025 Q1 to 0.620 in 2026 Q3)" in out[2]
    assert "dominant SHAP driver group is Market / Prices (88%" in out[3]
    assert 3 <= len(out) <= 5
    for s in out:
        _clean(s)


def test_summary_withheld_province_is_excluded():
    rows = [_row("Cavite", 0.70, 0.65), _row("Batangas", 0.80, None, withheld=True)]
    out = " ".join(txt.compose_summary(rows, None, "2025-Q1", "2026-Q3", HIGH, ALERT))
    assert "Batangas is withheld from publication for 2026 Q3" in out
    assert "0.800" not in out  # the withheld province's numbers never surface
    assert "1 of 1 published provinces is at or above" in out
    assert "No regional SHAP breakdown is available for 2026 Q3." in out


def test_province_summary_withheld_and_missing():
    held = txt.compose_province_summary("Rizal", "2026-Q1", 0.9, True, 1, 5, None, 3, HIGH, ALERT)
    assert held == ["The 2026 Q1 forecast for Rizal is withheld from publication by a reviewer; "
                    "no score or driver breakdown is reported."]
    no_shap = txt.compose_province_summary("Rizal", "2026-Q1", 0.55, False, 2, 5, None, 1, HIGH, ALERT)
    assert "high-risk line (0.50) but below the alert threshold (0.60)" in no_shap[0]
    assert "No SHAP breakdown is available for Rizal in 2026 Q1." in no_shap
    assert "1 relevant news article was geocoded" in no_shap[-1]


# ---------------------------------------------------------------------------
# compose_trend_interpretation
# ---------------------------------------------------------------------------

def test_trend_single_series():
    series = [{"name": "Batangas", "points": _pts(("2025-Q1", 0.7813), ("2025-Q2", 0.8249), ("2025-Q3", 0.6263))}]
    text = txt.compose_trend_interpretation(series, "2025-Q1", "2025-Q3", HIGH, ALERT)
    assert "decreased from 0.781 in 2025 Q1 to 0.626 in 2025 Q3, a net change of -0.155" in text
    assert "highest value of 0.825 in 2025 Q2" in text
    assert "alert threshold of 0.60 in 3 of 3 published quarters" in text
    _clean(text)


def test_trend_withheld_quarter_is_omitted_and_span_stated():
    series = [
        {"name": "Cavite", "points": _pts(("2025-Q1", 0.70), ("2025-Q2", 0.75))},
        {"name": "Rizal", "points": _pts(("2025-Q1", None), ("2025-Q2", 0.61), withheld=("2025-Q1",))},
    ]
    text = txt.compose_trend_interpretation(series, "2025-Q1", "2025-Q2", HIGH, ALERT)
    assert "Cavite (+0.050)" in text
    assert "Rizal (+0.000, 2025 Q2 to 2025 Q2)" in text
    assert "Quarters withheld from publication are omitted from the series: Rizal (2025 Q1)." in text
    _clean(text)


def test_trend_empty():
    text = txt.compose_trend_interpretation([], "2025-Q1", "2025-Q2", HIGH, ALERT)
    assert text.startswith("No published Risk Level scores are available")


# ---------------------------------------------------------------------------
# compose_driver_change
# ---------------------------------------------------------------------------

def test_driver_change_normal_and_direction_flip():
    first = [_t("Market / Prices", 40), _t("Climate Stress", 45, "protective"), _t("Employment", 15, "protective")]
    last = [_t("Market / Prices", 70), _t("Climate Stress", 20, "protective"), _t("Employment", 10)]
    text = txt.compose_driver_change("Laguna", "2025-Q1", "2026-Q3", first, last)
    assert "Market / Prices gained the most share for Laguna (+30 percentage points, from 40% to 70%)" in text
    assert "Climate Stress lost the most (-25 percentage points, from 45% to 20%)" in text
    assert "Employment changed from decreases to increases the predicted Risk Level score" in text
    _clean(text)


def test_driver_change_empty_and_withheld():
    empty = txt.compose_driver_change("Laguna", "2025-Q1", "2026-Q3", [], TRIGGERS)
    assert empty == ("No SHAP breakdown is available for Laguna in 2025 Q1, so the change in "
                     "drivers cannot be assessed.")
    held = txt.compose_driver_change("Laguna", "2025-Q1", "2026-Q3", TRIGGERS, TRIGGERS,
                                     withheld_last=True)
    assert "2026 Q3 forecast is withheld from publication" in held
    assert "%" not in held


# ---------------------------------------------------------------------------
# compose_news_evidence
# ---------------------------------------------------------------------------

def test_news_normal_with_matches():
    arts = [{"title": "Rice prices climb"}, {"title": "Market supply tight"}]
    text = txt.compose_news_evidence("Cavite", "2025-Q3", 12, 5, TRIGGERS[0], arts, False)
    assert text.startswith("12 relevant articles were geocoded to Cavite for 2025 Q3")
    assert "records 5 keyword-matched articles" in text
    assert "2 articles matching the top driver group, Market / Prices, are listed below." in text
    assert "limited signal" not in text
    _clean(text)


def test_news_limited_signal_uses_actual_count():
    text = txt.compose_news_evidence("Quezon", "2026-Q3", 1, 0, TRIGGERS[0], [], True)
    assert "Quezon is flagged as limited signal for 2026 Q3" in text
    assert "1 relevant article was geocoded to it" in text
    assert "None of these articles matches the top driver group, Market / Prices." in text


def test_news_empty_triggers_and_withheld():
    empty = txt.compose_news_evidence("Rizal", "2026-Q1", 3, 0, None, [], False)
    assert "No SHAP breakdown is available for Rizal in 2026 Q1" in empty
    held = txt.compose_news_evidence("Rizal", "2026-Q1", 3, 2, TRIGGERS[0], [], True, withheld=True)
    assert held == ("News evidence for Rizal in 2026 Q1 is not reported because the forecast "
                    "is withheld from publication.")


# ---------------------------------------------------------------------------
# compose_reliability
# ---------------------------------------------------------------------------

PERF = {"n": 95, "accuracy": 0.8842, "precision": 0.9615, "recall": 0.9036, "f1": 0.9317,
        "rocAuc": 0.9127, "baselines": {"majorityClass": 0.8737, "seasonalPersistence": None},
        "skill": {"vsMajority": 0.0105, "vsSeasonal": None}}


def test_reliability_quotes_backend_figures_and_missing_baseline():
    out = txt.compose_reliability(PERF)
    joined = " ".join(out)
    assert "accuracy is 0.8842, against a majority-class baseline of 0.8737 (a margin of +0.0105)" in joined
    assert "seasonal-persistence baseline is not reported" in joined
    assert "precision 0.9615, recall 0.9036, and F1 0.9317" in joined
    for s in out:
        _clean(s)


def test_reliability_with_seasonal_baseline_and_empty():
    perf = dict(PERF, baselines={"majorityClass": 0.72, "seasonalPersistence": 0.79},
                skill={"vsMajority": 0.1, "vsSeasonal": 0.03})
    assert "A seasonal-persistence baseline scores 0.7900 (a margin of +0.0300)." in txt.compose_reliability(perf)
    assert txt.compose_reliability({}) == ["Model performance figures are not available from the results file."]


# ---------------------------------------------------------------------------
# compose_limitations / compose_method
# ---------------------------------------------------------------------------

def test_limitations_keep_the_findings_only_position():
    items = txt.compose_limitations("2026-Q3", 1, None, 0.6, 0.4, "Findings only. No actions.", True)
    titles = [i["title"] for i in items]
    assert "Municipal values are disaggregated, not modelled" in titles
    assert items[-1] == {"title": "Findings only", "text": "Findings only. No actions."}
    assert "poverty incidence (60%) and population density (40%)" in " ".join(i["text"] for i in items)
    for i in items:
        _clean(i["title"] + i["text"])
        assert "recommend" not in i["title"].lower()


def test_method_is_filled_from_model_metadata():
    meta = {"components": [("a LightGBM classifier", 0.4), ("a logistic regression", 0.6)],
            "featureCount": 12, "label": "label_cpi", "trainedThrough": "2026-Q3",
            "trainRows": 135, "decisionThreshold": 0.712}
    out = txt.compose_method(meta, ["Source A \u2014 test"], {"high": 0.5, "alert": 0.6, "evenShare": 20},
                             "rule.")
    assert "a LightGBM classifier (40%) and a logistic regression (60%)" in out["model"]
    assert "135 province-quarter rows through 2026 Q3" in out["model"]
    assert "decision threshold of 0.712" in out["definition"]
    assert out["sources"] == ["Source A - test"]
    for v in [out["model"], out["explanation"], out["definition"], *out["sources"]]:
        _clean(v)


@pytest.mark.parametrize("name", ["Las Pi\u00f1as", "Quezon \u201cNorth\u201d"])
def test_names_with_typographic_characters_are_folded(name):
    for text in (
        compose_formal_interpretation(name, "2026-Q3", TRIGGERS, 3.0),
        txt.compose_news_evidence(name, "2026-Q3", 2, 1, TRIGGERS[0], [], True),
        " ".join(txt.compose_province_summary(name, "2026-Q3", 0.7, False, 1, 5, TRIGGERS[0], 2, HIGH, ALERT)),
    ):
        _clean(text)


# ---------------------------------------------------------------------------
# compose_limited_signal_note / brief interpretation
# ---------------------------------------------------------------------------

def test_limited_signal_note_uses_each_actual_count():
    many = txt.compose_limited_signal_note("2026-Q3", [("Cavite", 6), ("Quezon", 1)])
    assert many.startswith("Cavite and Quezon are flagged as limited signal for 2026 Q3")
    assert "6 and 1 relevant articles respectively" in many
    one = txt.compose_limited_signal_note("2026-Q3", [("Rizal", 1)])
    assert "1 relevant article was geocoded to it" in one
    assert txt.compose_limited_signal_note("2026-Q3", []) is None
    _clean(many)
    _clean(one)


def test_brief_interpretation_drops_repeated_total_only_for_a_single_major_group():
    single = [_t("Market / Prices", 90), _t("Employment", 10)]
    assert "Taken together" not in compose_formal_interpretation("A", "2026-Q3", single, brief=True)
    assert "Taken together" in compose_formal_interpretation("A", "2026-Q3", single)
    assert "Taken together" in compose_formal_interpretation("A", "2026-Q3", TRIGGERS, brief=True)
