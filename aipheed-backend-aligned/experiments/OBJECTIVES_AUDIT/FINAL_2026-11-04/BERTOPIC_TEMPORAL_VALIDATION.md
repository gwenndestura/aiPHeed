# BERTopic temporal validation

**Source:** `OBJ1_NLP_RESULTS.md` §5 and `out/obj1_topics.json`, pre-registered in `OBJ1_PREREGISTRATION.md`
(c263c36e…). Run 2026-11-03; no input has changed since.

## Leakage removed

- **Problem:** the served model was fitted once on all quarters, so later headlines shaped earlier topics.
- **Fix:** at each of 19 origins (2022-Q1..2026-Q3), it is refitted on headlines published before O(t) only. Output:
  `out/obj1_topic_proportions_timesafe.*`.
- **Alignment:** consecutive fits are compared by ARI.

| | All-quarter (leaky) | Time-safe (mean) | Rule | Result |
|---|---|---|---|---|
| Topics | 146 | 17 → 151 | — | — |
| Outliers | 37% | 30–41% | — | — |
| NPMI coherence | −0.37 | −0.47 | > 0 | ❌ |
| Place-name topics | 55% | 53% | < 50% | ❌ |
| Stability (ARI) | — | 0.44 | ≥ 0.30 | ✅ |

**Decision (pre-registered):** the topics are descriptive only, not forecast features. Short headlines give negative
NPMI, and topics cluster by place name.

**Status:**
- **Completed** for temporal validity.
- **Not achieved** for topic quality.
