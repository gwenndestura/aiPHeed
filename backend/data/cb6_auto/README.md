# Automatic quarterly update (frozen C-B6)

The system updates itself every quarter: it collects its data, scores one saved model, and stages the result for review.
It never trains, tunes or selects a model.

## What happens, and when

The scheduler runs `app.cb6_auto.job.run_daily` at 05:00 Asia/Manila every day, and once about two minutes after every start.

| When | What |
|---|---|
| Every day | Collects news (Google News RSS). Scores it only if `AIPHEED_CB6_NEWS_SCORING=1`. |
| Issue date (Jan 1, Apr 1, Jul 1, Oct 1) | Collects every source, builds the inputs under the as-of rules, scores the frozen model, adds the forecast to the served rows, stages it. |
| A source is stale | Retries daily for 7 days, then issues the forecast with that input missing and recorded. |
| 14 days after the issue date with no forecast | Records `MISSED`. It is never back-filled. |

A new forecast stays hidden from public endpoints until an administrator approves it (Rule 1).

## Files

| Path | Contents |
|---|---|
| `frozen/model.txt`, `frozen/manifest.json` | The one saved booster, fitted at origin 2026-Q3. Its SHA-256 is checked on every load. |
| `seed/` | First-start copy of every source, plus the reference table for the parity tests. |
| `$AIPHEED_CB6_STATE_DIR/sources/` | The live source files. |
| `$AIPHEED_CB6_STATE_DIR/forecast_ledger.jsonl` | Append-only, hash-chained record of each issue: inputs, stale sources, source hashes. |
| `$AIPHEED_CB6_STATE_DIR/run_log.jsonl` | Every run, including `WAITING`, `MISSED` and anything that needs a person. |
| `$AIPHEED_FI_DATA_DIR/rows.csv` | The served rows. Rows are added and existing ones are never changed. |

## Checking on it

- As an admin: `GET /api/v1/admin/auto-update`
- On the server: `python -m scripts.cb6_quarterly status`

## Sources

| Input | Source | Collected by |
|---|---|---|
| CPI (food, headline, rice) | PSA OpenSTAT `0012M4ACP22` | automatic |
| Palay, corn, fisheries | PSA OpenSTAT `0012E4EVCP0`, `0132E4GVFP1` | automatic |
| Rice stocks | PSA OpenSTAT `0032E4ECNV0` | automatic |
| ONI | NOAA CPC | automatic |
| World prices | World Bank Pink Sheet (the link is read from its page) | automatic |
| Typhoons | NOAA IBTrACS, last-3-years file | automatic |
| SWS hunger | SWS posts API | automatic; a release that fails the parser's checks is reported in `needs_human` and never guessed |
| News input `z_N1R` | Google News RSS, then XLM-RoBERTa | collection is automatic; scoring needs more memory than a Render starter instance |

## When a person is needed

- **SWS release refused by the parser:** add the round to `sources/sws_area_rounds_full.csv` by hand.
- **News scoring:** set `AIPHEED_CB6_NEWS_SCORING=1` on a larger instance, or run `python -m scripts.cb6_quarterly score-news` before the issue date. Otherwise `z_N1R` stays missing and the forecast records it as stale.
- **Approving each forecast:** Rule 1 requires it.

## Never run in production

`scripts/freeze_cb6.py` and `scripts/build_cb6_seed.py` were one-time development steps. They import code that is not in the Docker image, and the freeze script refuses to replace an existing model.
