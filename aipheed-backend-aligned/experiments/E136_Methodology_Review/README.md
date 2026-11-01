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
