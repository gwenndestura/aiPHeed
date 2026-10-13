# E24v2: making aiPHeed's forecasting reliable, useful and accurate

**Start with `FINAL_REPORT.md`.** The forecasting goal is **not met**:

- the approved composite forecast is not yet shown to beat persistence on unseen quarters;
- the provincial price-pressure component **is** shown to beat persistence, on 94 unseen quarters;
- two blind prospective seals and a pre-registered back-cast are in place to settle the rest.

| File | Contents |
|---|---|
| `FINAL_REPORT.md` | Answers to every required question, Chapter I objective, SOP question and H1–H5 (exact wording) |
| `ROOT_CAUSE_ANALYSIS.md` | Why persistence is hard to beat; what was fixed; what needs data |
| `DATA_ACQUISITION_REGISTER.md` | Acquired public PSA data, and what is still needed, prioritized |
| `FROZEN_EVALUATION_PROTOCOL.md`, `PROTOCOL_AMENDMENTS.md` | Frozen before the runs (hashes in `runner/*_SHA256.txt`) |
| `BASELINE_COMPARISON.csv` | Every model, lead and evidence class, on identical rows |
| `PREDICTIONS_BY_QUARTER.csv` | Every lead-1 development row with every arm and the PCF components |
| `FEATURE_ABLATION_RESULTS.csv` | Information-set ablations (back-cast and development) |
| `LGU_RANKING_VALIDATION.csv` | 142 LGUs, with ranking basis and limitation |
| `QUARTERLY_PIPELINE_AUDIT.md` | Pipeline rules, live and replay cycles, seals |
| `BUG_FIXES.md` | Defects fixed, process errors disclosed, isolation status |
| `TEST_RESULTS.md` | Python, frontend, reproducibility and integrity checks |
| `REPRODUCE.md` | Commands in order |
| `ADVISER_AND_AUTHORIZATION_CHECKLIST.md` | What you, your adviser and the evaluators need to do |
| `acquisition/` | Public PSA OpenSTAT downloads: raw responses, queries, manifest |
| `data/`, `data_v2/` | Derived series and comparability gate; LGU input table |
| `runner/` | Guard, runners, seals, scorer, builders |
| `runs/` | Back-cast, development runs, seals, analyses |
| `backend_dev/` | Isolated pipeline: PCF engine, forecaster, replay mode, configs, inputs, records |
| `dashboard_dev/` | Isolated dashboard: `/forecast-period` page, JSON, PDFs, tests |
| `instruments/` | DA Region IV-A questionnaire and scorer (unchanged from E24) |
| `thesis_source/` | Chapter I extraction (identical to E23) |
