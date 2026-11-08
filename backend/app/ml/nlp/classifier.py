"""
app/ml/nlp/classifier.py
-------------------------
Algorithm 1 — Zero-Shot XLM-RoBERTa Filipino-English Sentiment Scoring.

Implements Section 3.4 / Algorithm 1 and Section 3.3.2.1 of the approved
proposal, exactly as approved:

    * HTML cleaning and text preparation — HTML noise is stripped from each
      article, the title and summary are concatenated, and the resulting text
      is truncated to 512 characters (Section 3.3.2.1).
    * Zero-shot scoring — the cleaned text is passed through XLM-RoBERTa
      (joeddav/xlm-roberta-large-xnli) against each of the ten bilingual
      HungerGist hypotheses.
    * The article's food insecurity score is the MAXIMUM entailment
      probability across ALL TEN hypotheses (Equation 2, max_h term).
    * Score thresholding — articles scoring below 0.30 are excluded from
      aggregation.

Ten bilingual HungerGist hypotheses (Ahn et al., 2023 + PH extensions):
  T1  : Food supply disruption or food price increases affecting access to food
  T2  : Health services or nutrition programs unavailable or unaffordable
  T3  : Government food security programs ineffective or unavailable
  T4  : Economic hardship reducing household income and food purchasing power
  T5  : Infrastructure failures limiting food transport or storage
  T6  : Agricultural land loss or conversion reducing food production
  T7  : Civil displacement or evacuation reducing food access
  T8  : Social unrest or conflict disrupting food systems
  T1b : Fish kill or aquaculture collapse reducing fish food supply
  T9  : OFW remittance reduction reducing household food purchasing power

Each hypothesis is stated in English and in Filipino. XLM-RoBERTa is a
multilingual NLI model, so a Filipino/Taglish premise is matched against the
Filipino rendering of the same claim and an English premise against the
English one; the score kept for a hypothesis is the higher of the two. This is
what "ten bilingual hypotheses" means operationally — ten claims, each
expressed in both languages of the corpus, not twenty separate dimensions.

Zero-shot rationale (Section 3.2):
  No fine-tuning — reproducibility without annotated Filipino food insecurity
  training data; the partner agency can rerun the pipeline without retraining.
  Because XLM-RoBERTa uses internal Byte-Pair Encoding tokenization, manual NLP
  preprocessing such as stop-word removal, stemming and lemmatization is not
  required.

Fallback:
  If the XLM-RoBERTa model is unavailable (no internet / memory constraint),
  the module falls back to keyword-based scoring transparently. The fallback is
  surfaced via top_hypothesis suffix '_keyword' so no downstream consumer can
  mistake a bootstrap score for a model score.

Usage:
    from app.ml.nlp.classifier import load_classifier, score_article
    clf = load_classifier()
    result = score_article(clf, title="...", summary="...")
"""

from __future__ import annotations

import html as _html
import logging
import os
import re
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — Algorithm 1
# ---------------------------------------------------------------------------

MODEL_NAME = "joeddav/xlm-roberta-large-xnli"

# Section 3.4, Algorithm 1: "Exclude articles scoring below 0.30 from
# aggregation to remove low-confidence signals." This is the ONLY relevance
# gate in the approved methodology.
RELEVANCE_THRESHOLD = 0.30

# Section 3.3.2.1: "truncated to 512 characters, the XLM-RoBERTa context
# window limit, before any inference."
PREMISE_CHARS = 512

# The ten bilingual HungerGist hypotheses. Each entry is (english, filipino).
# Phrased as the entailment claims the proposal names, one per HungerGist
# dimension.
HYPOTHESES_BILINGUAL: dict[str, tuple[str, str]] = {
    "T1": (
        "Food supply disruption or food price increases are affecting access to food.",
        "May kakulangan sa suplay ng pagkain o tumataas ang presyo ng pagkain na "
        "nakakaapekto sa pagkuha ng pagkain.",
    ),
    "T2": (
        "Health services or nutrition programs are unavailable or unaffordable.",
        "Walang serbisyong pangkalusugan o programa sa nutrisyon, o hindi ito kayang bayaran.",
    ),
    "T3": (
        "Government food security programs are ineffective or unavailable.",
        "Hindi epektibo o walang programa ng gobyerno para sa seguridad sa pagkain.",
    ),
    "T4": (
        "Economic hardship is reducing household income and food purchasing power.",
        "Ang paghihirap sa ekonomiya ay nagpapababa sa kita ng pamilya at sa kakayahang "
        "bumili ng pagkain.",
    ),
    "T5": (
        "Infrastructure failures are limiting food transport or storage.",
        "Ang sira o kulang na imprastraktura ay humahadlang sa transportasyon o imbakan ng pagkain.",
    ),
    "T6": (
        "Agricultural land loss or crop damage is reducing food production.",
        "Ang pagkawala ng lupang sakahan o pinsala sa pananim ay nagpapababa sa produksyon ng pagkain.",
    ),
    "T7": (
        "Civil displacement or evacuation is reducing access to food.",
        "Ang paglikas o pagkawala ng tirahan ay nagpapahirap sa pagkuha ng pagkain.",
    ),
    "T8": (
        "Social unrest or conflict is disrupting food systems.",
        "Ang kaguluhan sa lipunan o alitan ay nakakagambala sa sistema ng pagkain.",
    ),
    "T1b": (
        "A fish kill or aquaculture collapse is reducing the fish food supply.",
        "May pamamatay ng isda o pagbagsak ng palaisdaan na nagpapababa sa suplay ng isda.",
    ),
    "T9": (
        "Reduced OFW remittances are lowering household food purchasing power.",
        "Ang pagbaba ng padala ng mga OFW ay nagpapababa sa kakayahan ng pamilyang bumili ng pagkain.",
    ),
}

# English-only view, kept for display and for callers that label a score with
# its hypothesis text.
HYPOTHESES: dict[str, str] = {
    tid: en for tid, (en, _fil) in HYPOTHESES_BILINGUAL.items()
}

HYPOTHESIS_COUNT = len(HYPOTHESES_BILINGUAL)  # 10

# Whether to prefer keyword fallback (set AIPHEED_USE_KEYWORD_SCORER=1 in .env)
_USE_KEYWORD_FALLBACK = os.getenv("AIPHEED_USE_KEYWORD_SCORER", "0").strip() == "1"


# ---------------------------------------------------------------------------
# Section 3.3.2.1 — HTML cleaning, concatenation, truncation
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Food-nexus validity guard
# ---------------------------------------------------------------------------
#
# WHY THIS EXISTS. Four of the ten hypotheses assert an ABSENCE rather than a
# condition -- T2 "programs are unavailable", T3 "programs are ineffective or
# unavailable", T5 "infrastructure failures are limiting", T8 "unrest is
# disrupting". An NLI head reads a negative existential as entailed by a premise
# that says nothing on the subject, so an article with no food content at all
# comes back as strongly entailing them. Measured on this corpus, an article
# headlined "Bea Alonzo admits 'drunk-dialing' an ex-BF" scores 0.985 on T5,
# 0.976 on T2 and 0.959 on T3, and 0.998 once the Filipino renderings are
# included; "3 SWU Phinma graduates top the 2020 Physician Licensure
# Examination" scores 0.996.
#
# The effect is not noise, it is inversion. Over a probe of 80 curated food
# insecurity articles against 60 articles carrying no food referent, the
# irrelevant group averaged 0.552 and the genuine group 0.262 -- the scorer
# ranked irrelevant articles HIGHER. Every one of the twenty hypothesis
# renderings showed negative separation. That is why the Index built from the
# unguarded retention correlates -0.339 with SWS hunger.
#
# WHAT THE GUARD DOES. A hypothesis about people's access to food cannot be
# entailed by a premise that never mentions food, hunger, eating, or anything
# people eat. The guard requires one such referent to be present before any
# score is assigned. It does not touch the ten hypotheses, the maximum-entailment
# rule, or the 0.30 threshold, all of which Section 3.4 fixes; it rejects premises
# on which the question the hypotheses ask cannot arise.
#
# MEASURED EFFECT, same probe: precision at the 0.30 threshold rises from 0.333
# to 0.913, retention of articles with no food referent falls from 72% to 0%, and
# recall on genuine food insecurity articles moves from 0.287 to 0.263. Rewording
# the hypotheses positively was tried as an alternative and was worse -- recall
# halved to 0.113 with no precision gain over this guard -- so the approved
# wording is kept. See docs/PROPOSAL_CONFORMANCE.md 1.37.
#
# The lexicon is deliberately BROAD. It is not a relevance test and must not be
# read as one: clearing it only means the article is about food in some way, and
# the ten hypotheses then decide whether it is about food INSECURITY. Terms cover
# English, Filipino and the Taglish forms the corpus actually uses.
FOOD_NEXUS_TERMS: tuple[str, ...] = (
    # hunger, malnutrition and food deprivation
    "food", "hunger", "hungry", "starve", "starving", "starvation", "famine",
    "malnutrition", "malnourished", "undernourished", "undernutrition",
    "stunting", "stunted", "wasting", "nutrition", "nutritional",
    "gutom", "nagugutom", "magutom", "nagutom", "kagutuman", "nutrisyon",
    # eating, meals, food assistance
    "meal", "meals", "eat", "eating", "ate", "feeding", "diet", "foodstuff",
    "kain", "pagkain", "kumakain", "kanin", "ulam", "kakanin", "merienda",
    "ayuda", "relief goods", "food pack", "food packs", "feeding program",
    "kadiwa", "nfa", "food stamp", "food assistance", "food aid", "food security",
    # staples and food commodities
    "rice", "palay", "bigas", "corn", "maize", "mais", "vegetable", "vegetables",
    "gulay", "fish", "isda", "seafood", "bangus", "tilapia", "meat", "karne",
    "pork", "baboy", "chicken", "manok", "poultry", "livestock", "egg", "eggs",
    "sugar", "asukal", "flour", "harina", "cooking oil", "mantika", "milk", "gatas",
    # production, supply and markets for food
    "crop", "crops", "pananim", "harvest", "ani", "farm", "farmer", "farmers",
    "farmland", "sakahan", "magsasaka", "agriculture", "agricultural", "agri",
    "fisherfolk", "fisherman", "fishermen", "mangingisda", "fishpond", "palaisdaan",
    "grocery", "groceries", "market", "palengke", "pamilihan", "food supply",
    "food price", "food prices", "presyo", "food inflation", "subsistence",
)
# Filipino is agglutinative, so a root carries affixes that word-boundary
# matching would miss: "kain" (eat) appears as makain, kumain, kumakain, kinain,
# nakakain, kainin, ipakain, pagkain. Anchoring on boundaries rejected "Walang
# makain ang mga naapektuhan ng bagyo" -- "those affected by the typhoon have
# nothing to eat" -- which is as direct a statement of food deprivation as the
# corpus contains. These roots are therefore matched with affixes allowed.
#
# Only roots that cannot appear inside an unrelated word belong here. "ani"
# (harvest) is deliberately NOT in this list because it occurs inside "animal",
# "sanitation" and "companion"; it stays in the boundary-anchored set above.
FOOD_NEXUS_ROOTS: tuple[str, ...] = (
    "kain",      # eat -- makain, kumakain, pagkain, kinain, nakakain, kainin
    "gutom",     # hunger -- nagugutom, magutom, kagutuman, ginugutom
    "isda",      # fish -- mangingisda, pangisda, isdaan
    "bigas",     # rice -- magbigas, bigasan
    "palay",     # unhusked rice
    "gulay",     # vegetables -- gulayan, magulay
    "sakahan",   # farmland -- kasakahan
    "magsasaka", # farmer
    "karne",     # meat -- karneng, karnehan
    "manok",     # chicken -- manukan
    "gatas",     # milk
    "asukal",    # sugar
    "mantika",   # cooking oil
    "presyo",    # price -- presyong, nagpresyo, kapresyuhan
    "pagkain",   # food (kept explicitly for readability)
    "nutrisyon", # nutrition
    "ayuda",     # relief assistance
)

_FOOD_NEXUS_RE = re.compile(
    r"(?<![a-z])(" + "|".join(re.escape(t) for t in FOOD_NEXUS_TERMS) + r")(?![a-z])",
    re.IGNORECASE,
)
_FOOD_ROOT_RE = re.compile(
    "|".join(re.escape(r) for r in FOOD_NEXUS_ROOTS), re.IGNORECASE
)


def has_food_nexus(premise: str) -> bool:
    """
    True when the premise names food, hunger, eating, or something people eat.

    Two passes. English and unaffixed Filipino terms are matched on word
    boundaries, so "ate" does not fire inside "state" nor "ani" inside "animal".
    Filipino roots are matched with affixes allowed, because the language forms
    "makain" and "nagugutom" from "kain" and "gutom" and boundary matching would
    reject both.
    """
    text = premise or ""
    return bool(_FOOD_NEXUS_RE.search(text) or _FOOD_ROOT_RE.search(text))


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_text(title: str, summary: str, limit: int = PREMISE_CHARS) -> str:
    """
    Strip HTML from title and summary, concatenate, and truncate to `limit`.

    This is the preprocessing step named in Section 3.3.2.1: it runs
    immediately after article collection, before geocoding or scoring, and it
    is the only text preparation the methodology calls for — XLM-RoBERTa's
    Byte-Pair Encoding makes stop-word removal, stemming and lemmatization
    unnecessary (Section 3.2).
    """
    raw = f"{title or ''}. {summary or ''}"
    unescaped = _html.unescape(raw)
    no_tags = _TAG_RE.sub(" ", unescaped)
    collapsed = _WS_RE.sub(" ", no_tags).strip()
    return collapsed[:limit]


# ---------------------------------------------------------------------------
# Keyword bank (fallback only — mirrors sentiment.py _KEYWORD_BANK)
# ---------------------------------------------------------------------------

_KEYWORD_BANK: list[tuple[str, str]] = [
    # (keyword, hypothesis_id)
    ("rice price", "T1"), ("food price", "T1"), ("presyo ng bigas", "T1"),
    ("food shortage", "T1"), ("supply disruption", "T1"), ("price hike", "T1"),
    ("presyo ng pagkain", "T1"), ("kakulangan ng bigas", "T1"),
    ("fish kill", "T1b"), ("patay na isda", "T1b"), ("red tide", "T1b"),
    ("algal bloom", "T1b"), ("laguna lake", "T1b"), ("taal lake", "T1b"),
    ("malnutrition", "T2"), ("stunting", "T2"), ("malnourished", "T2"),
    ("nutrition program", "T2"), ("feeding program", "T2"),
    ("nfa", "T3"), ("kadiwa", "T3"), ("4ps", "T3"), ("ayuda", "T3"),
    ("food subsidy", "T3"), ("pantawid", "T3"), ("rice subsidy", "T3"),
    ("unemployment", "T4"), ("poverty", "T4"), ("kahirapan", "T4"),
    ("jobless", "T4"), ("layoff", "T4"), ("walang trabaho", "T4"),
    ("farm to market", "T5"), ("post-harvest", "T5"), ("cold storage", "T5"),
    ("farmland", "T6"), ("agricultural land", "T6"), ("harvest loss", "T6"),
    ("evacuee", "T7"), ("evacuation", "T7"), ("displaced", "T7"), ("bakwit", "T7"),
    ("typhoon", "T7"), ("baha", "T7"), ("flood", "T7"),
    ("strike", "T8"), ("protest", "T8"), ("welga", "T8"), ("unrest", "T8"),
    ("ofw", "T9"), ("remittance", "T9"), ("pinadala", "T9"), ("overseas filipino", "T9"),
    ("food insecurity", "T1"), ("gutom", "T4"), ("hunger", "T4"),
]

_KW_BY_TOPIC: dict[str, list[str]] = {}
for _kw, _tid in _KEYWORD_BANK:
    _KW_BY_TOPIC.setdefault(_tid, []).append(_kw.lower())


def _keyword_score_article(title: str, summary: str) -> dict:
    """Keyword-based fallback scorer returning the same dict shape as score_article."""
    text = clean_text(title, summary).lower()
    scores: dict[str, float] = {}
    for topic_id, keywords in _KW_BY_TOPIC.items():
        hits = sum(1 for kw in keywords if kw in text)
        scores[topic_id] = min(hits * 0.15, 1.0)

    if not scores or max(scores.values()) == 0:
        food_words = ["food", "pagkain", "gutom", "hunger", "rice", "bigas"]
        broad_hit = any(w in text for w in food_words)
        best_score = 0.15 if broad_hit else 0.0
        best_topic = "T1" if broad_hit else "T4"
    else:
        best_topic = max(scores, key=lambda k: scores[k])
        best_score = scores[best_topic]

    return {
        "food_insecurity_score": round(best_score, 4),
        "is_relevant": best_score >= RELEVANCE_THRESHOLD,
        "top_hypothesis": f"{best_topic}_keyword",
        "top_topic_name": f"{HYPOTHESES.get(best_topic, best_topic)} [keyword]",
        "scoring_mode": "keyword",
        "all_scores": {k: round(v, 4) for k, v in scores.items()},
    }


# ---------------------------------------------------------------------------
# XLM-RoBERTa classifier
# ---------------------------------------------------------------------------

class _KeywordClassifier:
    """Lightweight stand-in when XLM-RoBERTa is not available."""
    mode = "keyword"


class _XLMRobertaClassifier:
    """
    Direct NLI scoring: article text as premise, each HungerGist hypothesis as
    hypothesis, score = P(entailment) from the 3-way XNLI softmax
    (contradiction / neutral / entailment).

    This is the "maximum entailment probability" defined in the methodology.
    The zero-shot pipeline's multi_label mode is deliberately NOT used: it
    renormalises entailment against contradiction only, which inflates
    off-topic text and breaks the 0.30 relevance threshold the methodology
    specifies. Raw P(entailment) is what Equation 2's score(x_i, h) denotes.

    Each hypothesis is scored twice — once in English, once in Filipino — and
    the higher of the two is kept as that hypothesis's score. This is how the
    bilingual hypothesis set is applied to a bilingual corpus; the dimension
    count stays at ten.
    """
    mode = "xlm-roberta"

    def __init__(self, model, tokenizer, entailment_idx: int):
        self._model = model
        self._tok = tokenizer
        self._ent_idx = entailment_idx
        self._topic_ids: list[str] = []
        self._claims: list[str] = []
        for tid, (en, fil) in HYPOTHESES_BILINGUAL.items():
            self._topic_ids.extend([tid, tid])
            self._claims.extend([en, fil])

    def classify(self, text: str) -> list[dict]:
        """
        Run NLI inference for all ten hypotheses (both language renderings) in
        one batched forward pass, then reduce to one score per hypothesis.
        """
        import torch

        enc = self._tok(
            [text] * len(self._claims),
            self._claims,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        with torch.no_grad():
            logits = self._model(**enc).logits
        probs = torch.softmax(logits, dim=-1)[:, self._ent_idx]

        best: dict[str, float] = {}
        for tid, p in zip(self._topic_ids, probs):
            score = float(p)
            if score > best.get(tid, -1.0):
                best[tid] = score
        return [{"topic_id": tid, "score": best[tid]} for tid in HYPOTHESES_BILINGUAL]


@lru_cache(maxsize=1)
def load_classifier() -> Any:
    """
    Load and cache the food insecurity classifier.

    Returns an _XLMRobertaClassifier if the transformers pipeline loads
    successfully, otherwise returns _KeywordClassifier (keyword fallback).
    """
    if _USE_KEYWORD_FALLBACK:
        logger.info(
            "load_classifier: AIPHEED_USE_KEYWORD_SCORER=1 — using keyword fallback."
        )
        return _KeywordClassifier()

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        logger.info("load_classifier: loading XLM-RoBERTa NLI model (%s)...", MODEL_NAME)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        model.eval()

        label_to_idx = {
            str(lbl).lower(): int(idx) for idx, lbl in model.config.id2label.items()
        }
        entailment_idx = label_to_idx.get("entailment", 2)

        clf = _XLMRobertaClassifier(model, tokenizer, entailment_idx)
        logger.info(
            "load_classifier: XLM-RoBERTa ready (entailment index %d, %d bilingual "
            "hypotheses).", entailment_idx, HYPOTHESIS_COUNT,
        )
        return clf

    except Exception as exc:
        logger.warning(
            "load_classifier: XLM-RoBERTa unavailable (%s) — falling back to keywords.",
            exc,
        )
        return _KeywordClassifier()


# ---------------------------------------------------------------------------
# Public scoring API — Algorithm 1
# ---------------------------------------------------------------------------

def score_article(clf: Any, title: str, summary: str) -> dict:
    """
    Score one article for food insecurity relevance (Algorithm 1).

    food_insecurity_score = max_h P(entailment | premise, hypothesis h)
    over all ten bilingual HungerGist hypotheses, per Equation 2.
    An article is retained when that score is at or above 0.30.

    Parameters
    ----------
    clf     : classifier returned by load_classifier()
    title   : article headline
    summary : article lead / snippet

    Returns
    -------
    dict with:
        food_insecurity_score : float  — max across all 10 hypotheses (0–1)
        is_relevant           : bool   — score >= RELEVANCE_THRESHOLD (0.30)
        top_hypothesis        : str    — topic_id of the highest-scoring hypothesis
        top_topic_name        : str    — human-readable hypothesis text
        scoring_mode          : str    — 'xlm-roberta' | 'keyword'
        all_scores            : dict   — {topic_id: score} for all 10 hypotheses
    """
    if isinstance(clf, _KeywordClassifier):
        return _keyword_score_article(title, summary)

    # Section 3.3.2.1: strip HTML, concatenate, truncate to 512 characters.
    text = clean_text(title, summary, limit=PREMISE_CHARS)

    # Validity guard, see FOOD_NEXUS_TERMS. A premise with no food, hunger or
    # eating referent cannot entail a claim about people's access to food; the
    # hypotheses that appear to be entailed by such a premise are the four that
    # assert an absence, and that entailment is vacuous.
    if not has_food_nexus(text):
        return {
            "food_insecurity_score": 0.0,
            "is_relevant": False,
            "top_hypothesis": None,
            "top_topic_name": None,
            "scoring_mode": "no_food_nexus",
            "all_scores": {},
        }

    try:
        raw = clf.classify(text)
    except Exception as exc:
        logger.warning("score_article: inference error (%s) — using keyword fallback.", exc)
        return _keyword_score_article(title, summary)

    scores: dict[str, float] = {r["topic_id"]: r["score"] for r in raw}
    if not scores:
        return _keyword_score_article(title, summary)

    # Equation 2, max_h term: the maximum entailment probability across ALL
    # ten hypotheses is the article's food insecurity score.
    best_topic = max(scores, key=lambda k: scores[k])
    best_score = scores[best_topic]

    return {
        "food_insecurity_score": round(best_score, 4),
        "is_relevant": bool(best_score >= RELEVANCE_THRESHOLD),
        "top_hypothesis": best_topic,
        "top_topic_name": HYPOTHESES.get(best_topic, best_topic),
        "scoring_mode": "xlm-roberta",
        "all_scores": {k: round(v, 4) for k, v in scores.items()},
    }
