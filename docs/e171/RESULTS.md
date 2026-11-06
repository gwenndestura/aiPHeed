# E171 results: retrospective (INFORMED design, run once as locked) — NOT ACCEPTED

**Run details:**
- Protocol: `docs/e171/PROTOCOL.md` (blob 5d70b029, commit f26a7279).
- Code: `backend/app/e171/model.py`.
- Rows: `data/e171/out/all_rows.csv`.
- Gates: `data/e171/out/results.json`.

**This retrospective is not acceptance evidence.** E171 was designed after seeing E168 and E170. **No prospective rows exist yet.**

## Decision: **NOT ACCEPTED. E158 stays in production.**
| Requirement | Result |
|---|---|
| Original E156 rule, Lead 1 | ❌ C1 (52/72; lower bound 0.592 vs majority 0.653), ❌ C4 (0.36–0.93); C2 ✅, C3 ✅, C5 ✅, C6 ✅ |
| New rule (C4 on new rows, n ≥ 40; pending adviser) | C4 **not yet evaluable** (0 new rows); C1 ❌ |
| Leakage ≤ 1e-9 | ✅ 0.0 |
| Real inputs no worse than shuffled (upper bound ≤ 0.005) | ❌ +0.0118 [−0.0008, +0.0267] |

**Maximum reliable lead: 0** under both rules.

## Lead 1 and Lead 2 (n = 72)
| Model | L1 accuracy | L1 Brier | L2 accuracy | HIGH recall (L1) | Beats persistence (Brier) |
|---|---|---|---|---|---|
| E158 (production) | 73.6 % | 0.134 | 73.6 % | 0.84 | yes |
| E168 | 75.0 % | 0.123 | 77.8 % | 0.88 | yes |
| E170 | 65.3 % | 0.178 | 63.9 % | — | no |
| **E171** | **72.2 %** | **0.148** | **76.4 %** | **0.92** | **yes, [−0.122, −0.016]** |

E171 at Lead 1: AUC 0.86, HIGH precision 0.56.

## By round (Lead 1)
| Round | Training transitions available at origin | Level used | Observed | Bias | Accuracy |
|---|---|---|---|---|---|
| ENNS 2018 | 1 (2013→2015) | 53.9 % | 47.4 % | +7.3 | 59 % |
| ENNS 2019 | 1 (2013→2015) | 55.3 % | 49.2 % | +5.3 | 72 % |
| **ENNS 2021** | 3 (2013→15, 15→18, 15→19) | **40.5 %** | **41.6 %** | **−0.8** | **84 %** |

## Reading
1. **The level-change model works once it has more than one survey-to-survey change to learn from.**
   - In 2021 it moved the level from 48 % (2019 round) to 40.5 %, against 41.6 % observed. It scored 84 % with almost no bias.
   - For 2018 and 2019 it had a single training change and could not anticipate the fall, the identification limit described in E169.
2. **Every future forecast has at least 3 training changes,** the 2021 situation. This is the strongest available evidence that E171 is the right design for new rounds. **It remains evidence, not proof:** 2021 is one round of 25 provinces, and it was read before E171 was designed.
3. **C4 fails on the pooled historical rows,** as expected under both E168-type and E171-type models, because of 2018/2019. C4 can only be judged under the pending rule once 40 or more new rows exist.
4. **The shuffle control fails.** The provincial-trigger inputs still show no advantage over shuffled inputs. Market timing is the only group close to helping (−0.0044 [−0.0096, +0.0005]). Remittance inputs hurt slightly (+0.004 [+0.0014, +0.0065]).

## What has to happen for E171 (or E168) to pass every criterion
1. **New provincial HFIAS outcomes** scored against the sealed forecasts (`SEALS.md`): ENNS 2022 or later. C1 needs roughly 22–30 new provinces at about 80–85 %.
2. **Adviser confirmation of the C4 rule** before any new outcome is scored.
3. **The shuffle control must pass on the pooled set.** This is not guaranteed even with new rows, because the trigger inputs have so far added no provincial information.
