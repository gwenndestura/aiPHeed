# Read-only experiments: hash-list verification

Generated 2026-10-13T23:27:27+00:00 by `runner/verify_readonly.py` (hashes computed, not typed).

A file counts as **identical** if its bytes equal the listed hash. **Line-ending only** means the bytes equal the listed hash once git's CRLF/LF normalization (core.autocrlf=true) is undone, including shell-captured logs with mixed endings; the text is unchanged. **Content differs** means no such form matches.

| Experiment | Listed files | Commit 5113ae5: identical / line-ending only / content differs / missing | Working tree: identical / line-ending only / content differs / missing | Extra files in working tree (not in list) |
|---|---|---|---|---|
| E17 | 65 | 61 / 2 / 0 / 2 | folder absent | 0 |
| E18 | 198 | 65 / 131 / 0 / 2 | 0 / 0 / 0 / 198 | 84 |
| E23 | 249 | 75 / 174 / 0 / 0 | 0 / 0 / 0 / 249 | 22 |
| E24 | 347 | 113 / 226 / 0 / 8 | 3 / 0 / 0 / 344 | 23 |
| E24v2 | 419 | 166 / 237 / 0 / 16 | 7 / 0 / 0 / 412 | 26 |

## Content differences and missing files

- E17 commit: listed file not in commit 5113ae5: `runs/supporting_20261013T034830Z/supporting_per_quarter_province.csv`
- E17 commit: listed file not in commit 5113ae5: `runs/supporting_20261013T034941Z/supporting_per_quarter_province.csv`
- E18 commit: listed file not in commit 5113ae5: `dashboard_dev/meeting-materials/aiPHeed_DOST_Presentation.pptx`
- E18 commit: listed file not in commit 5113ae5: `dashboard_dev/meeting-materials/aiPHeed_PostTesting_Questionnaire_Draft.docx`
- E18 working tree has 84 file(s) not in the hash list, e.g. `dashboard_dev/.vite-cache/deps/@radix-ui_react-dialog.js`, `dashboard_dev/.vite-cache/deps/@radix-ui_react-dialog.js.map`, `dashboard_dev/.vite-cache/deps/@radix-ui_react-toast.js`, `dashboard_dev/.vite-cache/deps/@radix-ui_react-toast.js.map`, `dashboard_dev/.vite-cache/deps/@radix-ui_react-tooltip.js`, `dashboard_dev/.vite-cache/deps/@radix-ui_react-tooltip.js.map`
- E23 working tree has 22 file(s) not in the hash list, e.g. `dashboard_dev/.vite-cache/vitest/da39a3ee5e6b4b0d3255bfef95601890afd80709/results.json`, `dashboard_dev/dist-e23/aiPHeed_forecast_report_2027-Q1.pdf`, `dashboard_dev/dist-e23/assets/hero-bg-BoqQDG8U.jpg`, `dashboard_dev/dist-e23/assets/index-DRN6hzy3.js`, `dashboard_dev/dist-e23/assets/index-DZ_a4pXe.css`, `dashboard_dev/dist-e23/assets/index.es-C09iLeU7.js`
- E24 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/68355a016610_add_municipal_forecast_records.py`
- E24 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/809280281fd2_add_admin_users_review_pipeline_audit_.py`
- E24 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/a1b2c3d4e5f6_add_dismissed_to_alert_records.py`
- E24 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/b2c3d4e5f6a7_add_shap_display_fields_and_driver_records.py`
- E24 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/c3d4e5f6a7b8_add_sudden_rise_fields_to_alert_records.py`
- E24 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/manifest.jsonl`
- E24 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/snapshots/03c92a8db785534e305c1fcd6dfb5bc9b5e1c26fd860f9cd655387edb9ef16b7/lgu_poverty.parquet`
- E24 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/snapshots/705cece6a8855f9fc8e9d2d4447d47dc067f5de0e4b717e75325593be19ec778/lgu_census.parquet`
- E24 working tree has 23 file(s) not in the hash list, e.g. `dashboard_dev/.vite-cache/vitest/da39a3ee5e6b4b0d3255bfef95601890afd80709/results.json`, `dashboard_dev/dist-e24/aiPHeed_forecast_report_2027-Q1.pdf`, `dashboard_dev/dist-e24/assets/hero-bg-BoqQDG8U.jpg`, `dashboard_dev/dist-e24/assets/index-B7r9icud.js`, `dashboard_dev/dist-e24/assets/index-DZ_a4pXe.css`, `dashboard_dev/dist-e24/assets/index.es-tlvgB7tV.js`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/63cd1ffe42fe_initial.py`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/68355a016610_add_municipal_forecast_records.py`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/809280281fd2_add_admin_users_review_pipeline_audit_.py`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/a1b2c3d4e5f6_add_dismissed_to_alert_records.py`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/b2c3d4e5f6a7_add_shap_display_fields_and_driver_records.py`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/app/db/migrations/versions/c3d4e5f6a7b8_add_sudden_rise_fields_to_alert_records.py`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_runs/replays/2026-Q3/forecast_record.json`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_runs/replays/2026-Q3/history/20261013T164817.360099+0000.json`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/manifest.jsonl`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/snapshots/08cbd6873fbae67d65e3f5aa69be842fdae6d5bc3a91974c9acb787dda80f61d/s1_labels.csv`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/snapshots/258fab535f5b7d438a86e145a927757f81ad4346c65638ddeac6ab6490228637/sws_rounds_verified.csv`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/snapshots/4f2b7c6c260aafce5d707fde2eaabc19b832245ec2a16b42b2c12b02688525b8/model_card_pcf_v2.json`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/snapshots/b731ff53045f0f48bb5b6a93140c0f4f749d5179115e57293914a6d077cb8d18/dnow_panel.csv`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/snapshots/d6ac42e10a940a54c4b80fd245cf78e510607d1539f19b374b5593f46cbea3f2/d_quarterly_panel.csv`
- E24v2 commit: listed file not in commit 5113ae5: `backend_dev/data/quarterly_store/snapshots/f0ca2c53f716d95e81cbb5ea67908c1753d2640f15aafe775019695616d6233e/lgu_vulnerability.csv`
- E24v2 commit: listed file not in commit 5113ae5: `dashboard_dev/public/aiPHeed_forecast_report_2026-Q3_replay.pdf`
- E24v2 working tree has 26 file(s) not in the hash list, e.g. `dashboard_dev/.vite-cache/vitest/da39a3ee5e6b4b0d3255bfef95601890afd80709/results.json`, `dashboard_dev/dist-e24v2/aiPHeed_forecast_report_2026-Q3_replay.pdf`, `dashboard_dev/dist-e24v2/aiPHeed_forecast_report_2027-Q1.pdf`, `dashboard_dev/dist-e24v2/aiPHeed_forecast_report_2027-Q1_v2.pdf`, `dashboard_dev/dist-e24v2/assets/hero-bg-BoqQDG8U.jpg`, `dashboard_dev/dist-e24v2/assets/index-BGx4PpSP.js`
