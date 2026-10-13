"""
Regression tests for the food-nexus validity guard in Algorithm 1.

Four of the ten approved hypotheses assert an absence rather than a condition
("programs are unavailable", "infrastructure failures are limiting"). An NLI
head reads a negative existential as entailed by a premise that says nothing on
the subject, so before this guard an article about a licensure examination or a
celebrity's love life scored above 0.99 and was retained as evidence of food
insecurity. Measured over the corpus, 398 of the 558 retained articles contained
no reference to food, hunger or eating at all.

These tests pin the two halves of the guard: English and unaffixed terms matched
on word boundaries, and Filipino roots matched with affixes allowed. They run
without loading the model.

See app/ml/nlp/classifier.py and docs/PROPOSAL_CONFORMANCE.md 1.37.
"""

from __future__ import annotations

import pytest

from app.ml.nlp.classifier import has_food_nexus


# Headlines drawn from the corpus that scored above 0.99 and were retained.
OBSERVED_FALSE_POSITIVES = [
    "Bea Alonzo admits 'drunk-dialing' an ex-BF, but clarifies: 'Hindi 'yung huling ex'",
    "3 SWU Phinma graduates top the 2020 Physician Licensure Examination",
    "Just two teachers facing 'child grooming' cases under DepEd",
    "Marcos: Philippines lacks capacity to drive off China",
    "Two Mandaue brgys tasked to maintain 2 eco-friendly projects",
    "Floorball takes center stage as Philippines hosts men",
    "LRT-2, MRT-3 to offer free rides on Rizal Day",
]

# Genuine food insecurity content in English, Filipino and Taglish. Every one of
# these must survive the guard; the hypotheses then decide relevance.
GENUINE_FOOD_INSECURITY = [
    "Rice prices surge in Quezon as supply tightens",
    "Feeding program launched for malnourished children in Rizal",
    "DSWD distributes food packs to evacuees in Laguna",
    "BFAR: Algal blooms caused fish kill in Cavite",
    "Taal eruption damages crops worth P577M",
    # Filipino and Taglish. These carry affixed roots that boundary matching
    # alone would reject, which is why FOOD_NEXUS_ROOTS exists.
    "Maraming pamilya ang nagugutom sa Batangas",
    "Walang makain ang mga naapektuhan ng bagyo",
    "Hindi na kayang bumili ng pagkain ng mga magsasaka",
    "Tumaas ang presyo ng bigas sa palengke",
    "Mga mangingisda, walang huli dahil sa red tide",
    "Kumakain na lang ng isang beses sa isang araw ang ilang pamilya",
]

# Words that CONTAIN a nexus term as a substring but are unrelated. These pin
# the word-boundary half of the guard: "ani" (harvest) must not fire inside
# "animal", nor "ate" inside "state".
SUBSTRING_TRAPS = [
    "The state opened a companion animal shelter",
    "Sanitation workers complete the drainage project",
    "The candidate delegated the estate matter",
]


@pytest.mark.parametrize("headline", OBSERVED_FALSE_POSITIVES)
def test_observed_false_positives_are_rejected(headline):
    """Articles with no food referent cannot reach the hypotheses."""
    assert has_food_nexus(headline) is False, (
        f"{headline!r} carries no food, hunger or eating referent and must not "
        "be eligible for a food insecurity score"
    )


@pytest.mark.parametrize("headline", GENUINE_FOOD_INSECURITY)
def test_genuine_food_insecurity_survives(headline):
    """English, Filipino and Taglish food content all pass the guard."""
    assert has_food_nexus(headline) is True, (
        f"{headline!r} is about food and must remain eligible for scoring"
    )


@pytest.mark.parametrize("headline", SUBSTRING_TRAPS)
def test_substring_traps_are_rejected(headline):
    """A nexus term appearing inside an unrelated word must not fire."""
    assert has_food_nexus(headline) is False


def test_guard_short_circuits_before_the_model():
    """
    A premise with no food referent returns a zero score without inference.

    The mode is reported so a reader can tell a guarded rejection from a low
    entailment score, and `is_relevant` is False regardless of any threshold.
    """
    from app.ml.nlp.classifier import _KeywordClassifier, score_article

    # A non-keyword classifier stand-in: if the guard fails to short-circuit,
    # calling .classify() raises and the test fails loudly rather than silently
    # falling back.
    class _Exploding:
        mode = "xlm-roberta"

        def classify(self, text):  # pragma: no cover - must never be reached
            raise AssertionError("the guard did not short-circuit")

    out = score_article(_Exploding(), "Rizal Day free rides on LRT-2", "")
    assert out["food_insecurity_score"] == 0.0
    assert out["is_relevant"] is False
    assert out["scoring_mode"] == "no_food_nexus"
    assert out["all_scores"] == {}
    # The keyword fallback has its own path and is unaffected by this test.
    assert not isinstance(_Exploding(), _KeywordClassifier)
