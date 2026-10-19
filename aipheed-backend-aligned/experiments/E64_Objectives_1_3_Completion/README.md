# E64: completing Objectives 1–3 (2026-10-19)

## Read first

| File | What it covers |
|---|---|
| `FINAL_REPORT.md` | Direct answers, Objectives 1–3, metrics, feature audit, Lead-2 evidence, tests, files, blockers |
| `OBJECTIVE_COMPLIANCE_MATRIX.md` | Status of each objective: Met, Partially Met or Not Met |
| `DEFECT_REGISTER.md` | Each defect: cause, fix, test and evidence |
| `DATA_TO_DASHBOARD_FLOW.md` | The served e64 path, and one forecast traced through it |

## Protocols

| File | sha256 |
|---|---|
| `PROTOCOL.md` | `2a37c236…` |
| `PROTOCOL_ADDENDUM_1.md` | `f0b59396…` |

Both hashes are in `runner/`.

## Reproduce

Run from `backend/` with `venv/Scripts/python.exe -B <script>`.

| Script | Output |
|---|---|
| `scripts/score_news_v3.py` | XLM-RoBERTa intensities → `data/news_v3/scores.jsonl` |
| `scripts/fit_topics_v3.py` | BERTopic → `data/news_v3/topic_*` |
| `runner/c1_candidates.py` | sealed candidates. Writes once; refuses to overwrite. |
| `runner/c2_score.py` | selection, metrics and claims → `out/c2_score.json`, `tables/c2_*` |
| `runner/r1_fssi_audit.py` | FSSI audit, FSSI-v3 panel and keys |
| `runner/r2_news_diagnostics.py` | why news adds little |
| `runner/r3_lgu_audit.py` | 142-LGU audit and sensitivity |
| `runner/r4_targets.py` | descriptive target comparison |
| `scripts/build_record_e64.py` | the served record and the 2027-Q1 prospective seal |
| `runner/serve_e64_stack.py` | local preview: API on 8064, frontend on 8094 |

## Status

**Uncommitted.** Nothing was pushed or deployed. **E38 is still the production default.**
