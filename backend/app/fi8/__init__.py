"""aiPHeed FI8: persistence-correction study (does any government/news information improve on persistence?).

FI7 (frozen at commit 6a8b114, hashes in data/fi8/FI7_FROZEN_REFERENCE.json) found that no model beats naive or
damped persistence for the next quarter. FI8 adds one model family, chosen from a diagnostic and not from the
final comparison:

    damped persistence + sparse linear correction of its error, with the inputs selected INSIDE each training
    window (lasso with expanding time folds), decision threshold from training folds only.

Same FI6 target, FI7 operational issue dates, origins, rules and baselines.
"""

VERSION = "fi8-1.0"
