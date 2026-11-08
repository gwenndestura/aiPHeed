"""
Unit tests for compose_formal_interpretation(), the third-person SHAP
interpretation printed in the exported PDF report.
"""

from app.services import reference as ref
from app.services.dashboard import compose_formal_interpretation, compose_narrative

CUTOFF = ref.TRIGGER_RED_CUTOFF


def _t(label: str, pct: int, direction: str = "increases_risk") -> dict:
    return {"label": label, "pct": pct, "direction": direction}


TRIGGERS = [
    _t("Market / Prices", 41),
    _t("Climate Stress", 27, "protective"),
    _t("Employment", 18),
    _t("OFW Remittance", 14, "protective"),
    _t("Fish Kill", 0),
]


def test_names_dominant_group_share_and_direction():
    text = compose_formal_interpretation("Batangas", "2026-Q3", TRIGGERS)
    assert text.startswith("For Batangas in 2026 Q3,")
    assert "Market / Prices (41%), which increases the predicted Risk Level score" in text


def test_states_direction_of_each_major_driver():
    text = compose_formal_interpretation("Batangas", "2026-Q3", TRIGGERS)
    assert f"Among the 2 groups exceeding the {CUTOFF}% even-share cutoff" in text
    assert "Market / Prices (41%) increases the predicted Risk Level score" in text
    assert "Climate Stress (27%) decreases it" in text


def test_compares_groups_above_and_below_cutoff():
    text = compose_formal_interpretation("Batangas", "2026-Q3", TRIGGERS)
    assert "Employment (18%, increasing)" in text
    assert "OFW Remittance (14%, decreasing)" in text
    assert "Fish Kill receives no measurable share" in text
    assert "account for 68% of the attributed share, compared with 32%" in text


def test_is_data_driven_not_a_fixed_template():
    flipped = [dict(t) for t in TRIGGERS]
    flipped[0]["direction"] = "protective"
    a = compose_formal_interpretation("Batangas", "2026-Q3", TRIGGERS)
    b = compose_formal_interpretation("Batangas", "2026-Q3", flipped)
    assert a != b
    assert "Market / Prices (41%), which decreases the predicted Risk Level score" in b


def test_is_ascii_and_third_person():
    text = compose_formal_interpretation("Batangas", "2026-Q3", TRIGGERS, other_pct=12.5)
    assert text.isascii()
    for informal in (" you ", " we ", " our ", "--"):
        assert informal not in f" {text.lower()} "


def test_typographic_characters_are_folded_to_ascii():
    text = compose_formal_interpretation(
        "Las Pi\u00f1as", "2026-Q3", [_t("Market \u2014 Prices", 100)]
    )
    assert text.isascii()
    assert "Las Pinas" in text
    assert "Market - Prices" in text


def test_empty_trigger_list():
    text = compose_formal_interpretation("Quezon", "2025-Q1", [])
    assert text.isascii()
    assert "No SHAP breakdown is available for Quezon in 2025 Q1" in text


def test_nonzero_other_share_is_explained():
    text = compose_formal_interpretation("Rizal", "2026-Q2", TRIGGERS, other_pct=23.4)
    assert "together represent 76.6% of the total SHAP-explained output" in text
    assert "The remaining 23.4% is attributable to model inputs outside" in text
    assert "Food Stress Sentiment Index (FSSI)" in text


def test_negligible_other_share_is_omitted():
    text = compose_formal_interpretation("Rizal", "2026-Q2", TRIGGERS, other_pct=0.4)
    assert "remaining" not in text


def test_single_group_above_cutoff():
    triggers = [_t("Climate Stress", 60, "protective"), _t("Employment", 20), _t("Fish Kill", 20)]
    text = compose_formal_interpretation("Laguna", "2026-Q1", triggers)
    assert "Climate Stress is the only driver group whose share exceeds" in text
    assert "which decreases the predicted Risk Level score" in text


def test_compose_narrative_is_unchanged_for_the_caption():
    text = compose_narrative("Batangas", "2026-Q3", TRIGGERS)
    assert text.startswith("For Batangas in 2026-Q3, the model's prediction breaks down as:")
