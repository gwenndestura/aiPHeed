# E106 Addendum 1 (frozen before scoring; written after the primary SM was scored)

**Why.** The primary SM failed: its re-trained price part has AUC 0.47 (Lead 1) and 0.44 (Lead 2) on the target. Cause: SM's price features use quarter t − 1 quarterly CPI only, while the production price model uses the latest monthly CPI (months 1–2 of quarter t) and a base-effect projection of food inflation for the target months. That monthly series is not in the repository, so the projection cannot be re-built. The simplest valid repair keeps SM's two-part structure and uses the production model's own sealed price probability, which is already served as FIRI indicator A1.

**This arm was designed after seeing SM's results. It is exploratory.**

## Arm SM-B

P(HIGH) = P_hunger (SM's persistence rule, unchanged) × P_price^E56, where P_price^E56 = `E56_p_price` from `aipheed-backend-aligned/experiments/E63_Lead_Time_Study/sealed/predictions.csv` (hash-checked), for the same lead, origin and province. Same rows, metrics and paired tests as the protocol, compared with E56 (its own combined score), SM and the baselines.

## Rule (fixed now)

SM-B becomes the recommended primary method only if, at Lead 2: it meets the protocol's "reliable" rule, and its Brier is not higher than E56's by more than 0.01 (mean quarter difference). Otherwise E56's combined score stays the recommended forecast and SM-B is reported only.
