# E151 protocol

Locked before any E151 model is scored against an outcome. **E147 to E150 and their results are unchanged.**

## Status of evidence, stated first

* All HFIAS province labels through 2021 have been read by earlier work. **No E151 result on them is an untouched test.** They are rolling-origin, retrospective evidence.
* SWS 2022 to 2026 was used inside E150 only as part of an aggregate response test. News has not been scored against it under this pipeline. It is the confirmation set for the news question, and it is **not blind** in the strict sense.
* The only blind evidence is prospective: forecasts sealed here for SWS 2026-Q4 onward and for any later FNRI round.

## Questions

**Q1, news.** Does corrected news add forecast information beyond government inputs and the outcome's own history?
**Q2, forecast.** Does a LightGBM forecast with all five groups beat persistence one quarter ahead on province surveys?
**Q3, meaning.** What does an aiPHeed percentage mean, and can it be read as survey-equivalent prevalence?

## Tier 1: area-quarter forecasts (news question)

**Target.** SWS involuntary hunger, logit, next-quarter change from the last reading released before the issue date. Areas: Metro Manila, Balance Luzon, Visayas, Mindanao. SWS is a one-item, 3-month direct measure of hunger. **It is never a provincial label and never pooled with HFIAS or FIES.** Its use here is to test news where a measurement exists every quarter.

**Issue date.** First day of T − h. Lead 1 is the required horizon; leads 2 to 4 are tested separately.

**Validation.** Expanding window: at each issue quarter, fit on rows whose outcome was published before the issue date.

**Development rows:** targets through 2021-Q4. **Confirmation rows:** targets 2022-Q1 to 2026-Q3. All variant choices are made on development rows only.

**Inputs.** Government: area means of province inputs with their geographic scope noted; Metro Manila has no province rows, so it uses national means. News: features of `app/e151/features.py`.

**Configurations, same rows and same folds:**

| Id | Inputs |
|---|---|
| PERS | No change |
| AR | LightGBM on history only |
| LR | Ridge on all inputs (the logistic-type linear baseline; classification uses logistic) |
| GOV | History + government, LightGBM |
| NEWS | History + news, LightGBM |
| GN | History + government + overall news (net stress, hunger, intensity) |
| GNT | History + government + news by trigger group (required model) |

**Development variants of news,** chosen by the lowest development MSE of GNT, ties to the simpler:
window lag 0 or 3 months; geography: national, area, pooled, or area + national; events only, topics only, both; with or without training-only Granger screening.

**Granger screening.** At each origin, on training rows only: for each news feature, an F-test of adding the lagged feature to an autoregression of the outcome, pooled across areas, differencing not needed because the features are already changes against a norm. Keep p < 0.10; if none pass, keep none.

**Primary test of Q1.** On confirmation rows at Lead 1: GNT − GOV squared error, block bootstrap by quarter, 95 % interval, 5,000 draws, plus Diebold-Mariano. **News passes only if the interval is below 0 and at least 95 % of 200 time-shuffled placebos do no better.**

**Secondary, labelled exploratory:** deterioration detection (top-quartile rise in a training window, recall at the threshold giving 50 % precision on development rows), ablations by group, sentiment and topics, leads 2 to 4, removal of the largest outlet.

## Tier 2: province survey forecasts (Q2, Q3)

**Target.** HFIAS any-level logit at province level. Rounds 2018, 2019, 2021 by rolling origin, with 2013 and 2015 as starting history. FIES is never pooled.

**Corrections to E150, fixed in advance:**

1. Structural inputs are relative to the all-province mean of the same issue quarter, removing the poverty double-count.
2. The shared level is carried flat from the last released round, with no trend extrapolation. Movement must come from quarterly inputs.
3. The LightGBM residual is always fitted (no zero-tree option), with all five groups, because the thesis requires them as inputs. Its value is then measured against the anchor alone.
4. Quarterly learning: the SWS GNT model of Tier 1 is applied to province inputs as an input feature, `h2`, with a positive monotone constraint. It uses province news and CPI where they exist, and the scope of each input is stated.
5. News streams at province, area, CALABARZON and national level, in place of E150's 12-month province features.
6. Intervals scale with staleness: squared as-of error is regressed on quarters since the anchor, then conformal.

**Configurations, same rows:**

| Id | Inputs |
|---|---|
| ANCHOR | Anchor only: PSA/vulnerability level + shrunk own surveys + flat shared level |
| GOV | ANCHOR + LightGBM on government inputs |
| NEWS | ANCHOR + LightGBM on news only |
| GN | ANCHOR + LightGBM on government + overall news |
| **GNT, required model** | ANCHOR + LightGBM on five groups, news by group, `h2` |
| PERS | Last measured value |
| PSA | PSA/vulnerability only, logistic and no own survey |
| LR | Logistic on the GNT inputs |

**Class.** HIGH when the score is ≥ 50, LOW otherwise, as approved by the panel. The class is identical whether read from the score or from P(HIGH) ≥ 0.5.

**Release gates, Lead 1, pool:** R1 accuracy ≥ 0.75; R2 AUC ≥ 0.70; R3 both class recalls ≥ 0.50; R4 Brier below persistence with interval below 0; R5 above always-HIGH accuracy; R6 interval coverage 0.80 to 0.98; R7 slope interval includes 1; R8 at least one province pair of five separated; R9 news passes Q1. All must pass before any production or dashboard work.

## Q3: scale of the score

Calibrators, nested in time so each round uses only earlier rounds' as-of forecasts: none; intercept-slope on the logit; isotonic; region partial pooling. The calibrator with the lowest mean error on the last available round is applied to the next; none is used when fewer than 20 earlier as-of rows exist.

**The percentage may be called estimated HFIAS any-level prevalence only if,** on nested out-of-sample rows, the slope interval includes 1, the mean error interval includes 0, and 90 % coverage is 0.80 to 0.98. **Otherwise it is called a survey-anchored risk score.** Neither reading changes the HIGH/LOW line.

**Survey weights.** Microdata are not held, so survey-weight-aware estimation is **not possible**; published standard errors are used as precision weights, and this is disclosed.

## Fix-only rule

Deviations are logged here with reasons and never change a threshold or a gate after seeing a result.

## Deviations and corrections

**D5, 2026-11-05, after the E151 results: one locked improvement attempt, at the owner's request for accuracy above 75 %.** E151's results below stand and are not replaced.

1. **One run only.** `app/e151/attempt.py` refuses a second run. The code and this protocol are hashed before it runs.
2. **Choices are made inside each target round's training rows,** by cross-validation across regions, on rounds released before the issue date. Rule: lowest soft Brier; ties to the earlier candidate. The target round's outcomes play no part.
3. **Candidates, all stated in advance:** input set (required, government, market + climate + poverty, the last with overall news); weight on the LightGBM adjustment (1 or 0.5); correction of mean training error (no or yes).
4. **The gates, the 50 line and the rows do not change.** A pass needs accuracy of at least 0.75 on the pool and all other gates.
5. **Evidence is retrospective whatever the result.** The author knew the E151 results when writing the candidates: the simplified input set was suggested by the near-zero weight of employment and remittances, and the error correction by the positive mean error. That is disclosed and cannot be removed.
6. Removing employment and remittances would conflict with the requirement that all five groups be inputs. If such a candidate is picked, that conflict is reported and the owner decides.

**D4, 2026-11-05, before any E151 model was scored: the target becomes HFIAS moderate plus severe, by the owner's decision.** The owner asked for a score that reflects food insecurity as it is, so that areas not very food insecure read low, and for the classes to stay HIGH and LOW. Changes:

1. The province score now tracks HFIAS moderate plus severe (`app/e141/panel.py outcomes("mod_sev")`). This replaces "HFIAS any-level logit" in Tier 2 and in the Q3 wording, so prevalence wording, if earned, reads "estimated HFIAS moderate-or-severe prevalence".
2. **HIGH is still score >= 50 and LOW below 50.** The line is the panel's and is unchanged. Whether the panel meant 50 on this measure is for the owner's adviser to confirm.
3. **The score is not scaled, shifted or capped.** It is lower only because the target is lower. No factor is applied to reach a wanted level.
4. **R5 now reads: accuracy above the majority-class rule,** because LOW is now the majority. The direction of the test is unchanged in spirit and it is applied to the pool and to the 2021 round, where the majority rule reaches 84 %.
5. Any-level is run as a labelled sensitivity (`E151_TARGET=insecure`) and cannot be chosen afterwards in place of the main target.
6. Disclosed: earlier label audits showed the distribution of this measure before the choice, and every round through 2021 has been read before. The choice does not use any model result.

**D3, 2026-11-05, before any outcome was read: event labels failed the label check.** On 80 random stories labelled before seeing the model's output, the top event agreed with the reader on 20 %, and the filter removed 0 of the 18 stories the reader judged off-topic. Causes found: raw logits are not comparable between hypotheses (displacement took 34 % of top events and climate 0.9 %), the negatively worded "none" hypothesis does not work (mean 0.003), and problem and plan readings saturate (means 0.72 and 0.83). Changes, using no outcome:

1. Each hypothesis is standardised against articles published before the first forecast date (2015-01-01), before any comparison between hypotheses.
2. Off-topic, foreign and weather-bulletin reporting are asked about directly in positive form (`app/e151/relevance.py`).
3. These changes are tuned on that sample, so it is now a development sample. **A fresh random sample is labelled before its output is read, and that second figure is the one reported as the label check.** If the fresh figure stays poor, it is reported and the news result is read in that light.
4. Standardising and the positive hypotheses alone reached only 35 % on the development sample, and the off-topic hypothesis did not separate off-topic stories. So each event became the mean of three readers on their own scales (XLM-RoBERTa, embedding similarity, seed phrases, `app/e151/labeler.py`), with a rule-based off-topic filter. The seed phrases were written after reading the development sample, so its 66 % is optimistic.

**Fresh check, rule fixed first (seed 1510, n = 80):** top event agreement 69 % (55 of 80, Wilson 95 % 58 to 78 %), 84 % on stories the reader judged relevant (48 of 57), current-problem agreement 80 %. **The filter removed only 7 of 23 stories the reader judged off-topic,** and it wrongly removed 1 of 57 relevant ones, so off-topic noise remains. The filter is not tuned further, since that would need a third sample. The reader is the system's author, not an independent annotator.

**D2, 2026-11-05, before any outcome was read: test period and upgrades, from recommendations the owner was shown and did not choose between; the owner said "continue", and may overrule these before the lock.**

* **Main test period 2021 to 2026, training on earlier data.** Tier 1 development rows now end at 2020-Q4 and confirmation rows run 2021-Q1 to 2026-Q3. This replaces the 2021-Q4 and 2022-Q1 boundaries above. In Tier 2 the 2021 round is reported as the main test and 2018 and 2019 as extra evidence. **Release gates must pass on both the pool and the 2021 round,** which is stricter than the gate above. 2021 was read by earlier experiments, so it remains retrospective.
* **Upgrade 1, province-target scoring** (`app/e151/target.py`). Sentences naming a province are read against hypotheses naming that province. Added to the province model as `p_tg_hard`, `p_tg_resp`, `p_tg_net`.
* **Upgrade 2, label check.** A random sample of eligible stories is labelled by Claude before seeing the model's output, then compared. It is one reader's check by the system's author, not independent human annotation, and is reported as such. Results do not tune the pipeline unless logged here.
* **Upgrade 3, comparison arms in Tier 2.** FH: Fay-Herriot style, a poverty-covariate prior updated with each province's rounds and their standard errors. SS: the same with a local level; drift variance chosen by predictive likelihood on released rounds only. MIDAS: ridge on the change since the last survey, using aggregates since that survey (U-MIDAS style, no Almon weights). None can replace the required LightGBM without a new decision.
* **Added reporting, no new gate:** model against the old survey by survey age (under 2, 2 to 3, 3+ years), share of forecasts HIGH by arm, and moderate-or-severe figures where the data supports them.
* **The 50 % line stays on any-level, provisionally,** until the owner's adviser confirms the measure. The 75 % target is taken from the current mission, and Chapter I sets no threshold per the owner's earlier instruction; the adviser should confirm it.

**D1, 2026-11-05, before any outcome was read: sign of the stored event scores.** `app/e151/score.py` read logit index 0 as entailment. The model's config gives contradiction 0, neutral 1, entailment 2, and known sentence pairs confirm it ("A man is asleep" against "A man is sleeping on the sofa" gives [-2.84, -2.16, 4.68]). The stored value was therefore contradiction minus entailment, the exact negative of what was intended. The fix is to negate the stored values once when the scoring run ends and correct the code; no article needs rescoring, because the neutral logit is not used. The earlier scorers in `app/e145/news.py` and `app/fi6/news_events.py` read index 2 as entailment and are not affected.
