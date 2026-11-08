# E136 · Independent methodology review

**Recommendation** (frozen E136 rule): **SEAS-LLM**, the measurement-aware seasonal local level.
- It won an exact four-way tie on mean rank by being the simplest model.
- SIMPLE is the sealed challenger, and X-RED is sealed as a separate hypothesis.

**Outcome:**
- No model reaches 75 % or passes N1–N7; there is no reliable lead.
- LightGBM and ridge overfit and lose to persistence.

The main document is `E136_FINAL_RESEARCH_PACKAGE.md` (sections A–H, with a flowchart).

**Context.** Protocol `f12ea6b`. Offline; production and earlier seals are unchanged.

**Reproduce.** Run E135 `runner/e135_run.py` first, then:

```
python -I runner/e136_run.py
python -I runner/e136_seal.py   # write-once (sealed/E136_PROSPECTIVE_SEAL.csv, sha 9bccb2ec)
```

## Amendment approved (2026-11-01)

The owner approved E134 Addendum 2 (`../E134_Information_Bottleneck/E134_ADDENDUM_2_AMENDED_PRIMARY.md`):
- **SEAS-LLM** is the prospective primary;
- **SIMPLE** and **HFM-X** are challengers.

**Quarterly re-issue.** On each quarter start, after refreshing the driver data:

```
python -I runner/e136_reissue.py <YYYY-MM-01>
```

It writes `sealed/E136_REISSUE_<quarter>.csv` once. A dry run on today's data reproduces the sealed forecasts exactly.

**Scoring.** Primary criterion only, plus N1–N7 once 10 or more quarters are scored:

```
python -I runner/score_e136.py
```
