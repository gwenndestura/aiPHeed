# E174 ledger: data dictionary

Built by `python -m app.e174.ledger` (reads files only). One row per published observation (survey round x area x source).

| Column | Meaning |
|---|---|
| `source_record_id` | Unique id: `HEAT-<year>-<area>` (FNRI Heat Map), `E87-<survey>-<area>-<indicator>` (FNRI dissemination decks), `SDG212-<year>-<area>` (PSA OpenSTAT) |
| `survey_round` | NNS/Updating 2011, NNS2013, FNRI2015, ENNS2018, ENNS2019, ENNS2021, or the survey named in the source |
| `year` | Survey (fieldwork) year as published |
| `area`, `key` | Area as published; `key` = the panel's normalised name (`app.hfias.panel.norm`) |
| `level` | province, city/HUC, region, national |
| `instrument` | HFIAS, FIES, or Radimer-Cornell (2011, inferred from its published categories; marked "verify") |
| `outcome_definition`, `categories_present` | What the source publishes for that observation |
| `raw_source` | File path (and page/URL for decks) |
| `sampling_weight` | Not in any source used here (published estimates, no microdata) |
| `fieldwork`, `published` | Fieldwork year; publication year (approximate where the source gives no date) |
| `prior_use` | Use in E151-E173: test rows, training/anchor rows, external reference, or not used |
| `status` | previously used / excluded / eligible independent |
| `reason` | Why excluded, or why eligible |
| `se_published` | Whether a standard error is published (needed for q_true, Brier and C2) |
| `cross_source_abs_diff` | |Heat Map value - ENNS publication value| (points), where both exist |
| `is_calabarzon` | Batangas, Cavite, Laguna, Quezon or Rizal (or the region) |

No household-level data is held or exported.
