# E8 v3: Protected-Data Access Checklist

**Status: DRAFT, 2026-10-12. The controls in §3 are proposals. None is implemented.**

**Purpose.** For every file that contains, may contain, or derives from protected 2026-H2 outcomes, this checklist states:

- what may be done with it (**metadata and hashes only**);
- what is prohibited;
- how the workflow will prevent accidental access later.

**Hash baseline.** The full SHA-256 of every hashed file, with size and mtime, is in `protected_and_carrier_files_sha256_20261012.txt` (this folder; 55 files; recorded 2026-10-12). Prefixes below are the first 16 hex characters.

## 1. Permitted and prohibited operations (all files in §2)

| Permitted (metadata and hash) | Prohibited (content access) |
|---|---|
| Path, size, mtime (`stat`, `ls -l`, `find -printf`) | `Read` tool, `cat`, `head`, `tail`, `less`, `strings`, `xxd`, `od`, `grep` on content |
| SHA-256 of the raw bytes, read in binary chunks and never decoded (`sha256sum`, or `hashlib` with `open(p, "rb")`) | `pd.read_parquet`, `pyarrow.parquet.read_table` / `ParquetFile` / `read_schema` / `read_metadata`, `pd.read_csv`, `json.load` |
| `git hash-object`, `git ls-files -s`, `git rev-parse HEAD:<path>`, `git log --format=%h %ad -- <path>`, `git check-ignore` | `git show`, `git diff` (including `--stat` on text), `git cat-file -p`, `git log -p` |
| Comparing two hashes for equality | `sqlite3` / SQLAlchemy queries; `joblib.load` / `pickle.load` (loading a model exposes its stored metrics, thresholds and training dates) |
| Counting files in a directory | Parquet schema or row-group metadata (it can reveal min/max statistics per column) |
| — | Printing, aggregating or summarizing any row, including counts by quarter |
| — | Opening a session transcript or event list of a session that may have read these files |

## 2. File-level checklist

**Class key:**

- **P3-doc:** documented in earlier session records to contain 2026-H2 rows.
- **Carrier?:** coverage unknown without reading the content, so treated as protected.
- **P4?:** possibly derived from P3 (models, predictions, metrics).
- **Allowlist-candidate:** previously documented to end at 2025-Q4; becomes an E8 input only under approval A5, with its hash verified first.

### 2.1 Production `backend/` (must stay untouched)

All tracked files below have a working copy equal to the git HEAD blob, checked 2026-10-12 by hash. "No info after X" means the bytes were committed on date X, so they cannot carry anything first published after X.

| File | Class | Last commit | SHA-256 prefix | Note |
|---|---|---|---|---|
| `data/processed/psa_indicators.parquet` | **P3-doc** (rows labelled through 2026-Q4) | eee269b, 2026-09-29 | 305ac1b34a0d1f24 | 2026-Q3/Q4 rows are partial or placeholder of unknown provenance; protected anyway |
| `data/thesis/panel.parquet` | **P3-doc** (rows through 2026-Q3, incl. `label_cpi`) | eee269b, 2026-09-29 | 49af3ee17abe3fac | Source of the disclosed 2026-10-11 aggregate. Read and overwritten by the APScheduler pipeline. |
| `data/thesis/panel_expanded.parquet`, `panel_multiagency.parquet` | Carrier? | eee269b, 2026-09-29 | bcf7f8982fcc7c90, 4d24b234bffa9a86 | — |
| `data/processed/cpi_full.parquet` | Carrier? | 4802f4d, 2026-09-10 | 2a0e69d5f6203d5b | Could hold July–August 2026 CPI; no info after 2026-09-10 |
| `data/processed/cpi_full.pre2026.parquet` | Carrier? (the name is not evidence) | **untracked**, git-ignored (`backend/.gitignore:25`) | 60b6ca4ba51392e8 | No git baseline; mtime 2026-05-02 |
| `data/processed/sws_hunger.parquet` | Carrier? | aa17da3, 2026-09-09 | 64701ed66981697d | No info after 2026-09-09. Whether a round with fieldwork from 2026-07-01 was published before that date is unknown, so the file stays protected. |
| `data/processed/features_fused.parquet`, `fssi_quarterly.parquet`, `bias_weights.parquet`, `trigger_proportions.parquet` | Carrier? / P4? | aa17da3 (09-09) / eee269b (09-29) | f02ea3e2168f9d69, d4dec01335b32588, 674a9c7e8d432eb8, 25528f710ad2ddd6 | Pipeline-derived |
| `data/processed/feature_provenance.json` | P4? | **untracked**, git-ignored | bcc6755bfda2d8c3 | mtime 2026-10-10 21:18. Previously noted to expose 2026-Q1/Q2 outcomes. |
| `data/processed/labels.parquet`, `label_distribution.json` | Carrier? | 0b22d1c, 2026-09-02 / — | c09a4c5051b1b753, a6c2a76964af162e | — |
| `data/processed/final_predictions.parquet`, `final_results.json`, `forecast_results.json`, `thesis_results.json`, `food_availability_tuned.json`; `data/thesis/thesis_results.json`, `baseline_comparison.json` | P4? | 514e126 / eee269b | In the baseline file, except `food_availability_tuned.json` (not hashed) | Metrics may embed 2026 rows |
| `models/thesis_food_insecurity_model.joblib` | **P4?** (trained on the panel) | eee269b, 2026-09-29 | cbab63f867e8f51f | Loading it exposes `trained_through`, metrics and threshold |
| `models/food_availability_model.joblib`, `food_availability_forecast_model.joblib` | P4? | 514e126, 2026-09-23 | 325742b2b87f27f6, 0acf1991dae8db30 | — |
| `aipheed.db` | Carrier? | 514e126, 2026-09-23 | 86fc7b0b907ea8ec | — |
| `mlflow.db`, `mlruns/` | P4? | mtime 2026-09-01 | b1c20d62aa220d5e | Logged runs |
| `data/pipeline_runs/`, `models/candidates/`, `*.pre_pipeline.parquet` | Future scheduled-task outputs | **do not exist** (checked 2026-10-12) | — | Created only if the APScheduler pipeline runs (§2.4) |

### 2.2 Isolated backend `aipheed-backend-aligned/`

| File | Class | SHA-256 prefix | Note |
|---|---|---|---|
| `data/processed/cpi_full.parquet` | **Carrier?** | 2a0e69d5f6203d5b | **Byte-identical to production `cpi_full.parquet`** (hash match). Excluded from E8. |
| `data/processed/sws_hunger.parquet` | **Carrier?** | 1fdcb88b879f1e71 | mtime 2026-09-23. Loaded in memory by the existing development frame (checklist 2, C7). Its SWS values are then replaced by the code registry, which asserts that no protected quarter is present. **Excluded from the E8 frame.** |
| `data/processed/corpus_geocoded.parquet`, `corpus_curated371.parquet`, `topic_proportions.parquet`, `zs_rescore.parquet`, `fssi_quarterly.parquet`, `trigger_proportions.parquet` | **Carrier?** (article text may report protected figures) | in E-run input records | News is excluded from A1–A3 |
| `aipheed.db`, `mlflow.db`, `mlruns/` (225 files, latest 2026-10-08), `models/*.pkl` | P4? | 4dbd89f90d24b817, bff698a6b7098a78, 0cc02324be393aac, 58cfe3626033796b | — |
| `data/processed/psa_indicators.parquet` | Allowlist-candidate | 947be05fcab7d493 | Matches the hash recorded in the served-artifact meta |
| `data/processed/labels.parquet` | Allowlist-candidate | eeb55983d8cf2de0 | Matches the served-artifact meta |
| `data/processed/features_fused.parquet` | Allowlist-candidate | 0080dd5c3cafd82e | Matches the E1–E5 input records |
| `data/supplementary/collection_2026-10-09/*` | Exposed (2026-H1 only, by query) | in its `COLLECTION_MANIFEST.json` | Allowlist-candidate. Documented in v2 as January–June 2026 values only (collected 2026-10-09). |
| `data/revised/*.parquet` (served artifacts) | Target quarters end at 2025-Q4 | 7135eb68…, ed58bdcb… | Not E8 inputs; read-only |

### 2.3 Other locations

| Location | Class | Permitted |
|---|---|---|
| `Claude outputs/` (18 .docx, 2 .html, 1 folder; dated 2026-09-10 to 10-10) | Carrier? | Metadata only. The .docx files were not hashed this time (outside the baseline's file types). |
| `aipheed-lean/outputs/*`, `aiPHeed_Simplified_Methodology/outputs/*` (dated 2026-09-09) | Carrier? / P4? | Hashed in the baseline file |
| `~/.claude/projects/C--Users-admin-aipheed/*.jsonl` (133 session transcripts, including scheduled-task sessions) | **Carrier?** | **Never opened**: no `Read`, no `list_events`, no `search_session_transcripts` |
| `~/.claude/projects/C--Users-admin-aipheed/memory/*.md` | Unknown | The auto-loaded index has no values. Individual files are not opened for E8. |
| Web sources: SWS site, PSA / RSSO IV-A releases, news | **P1/P2 at source** | No access during the blind period except under approval A3's safeguards |

### 2.4 Scheduled-task output paths

| Mechanism | Writes | Can it acquire protected data? |
|---|---|---|
| Production APScheduler pipeline (`backend/app/tasks/quarterly_pipeline.py`) | `psa_indicators.parquet` and `psa_rice_prices.parquet` (upserted from OpenStat, 2020 to the run date); `corpus_geocoded.parquet`; `data/thesis/panel.parquet`; `models/candidates/`; `models/thesis_food_insecurity_model.joblib` on promotion; `data/pipeline_runs/*.json` | **Yes**: an OpenStat fetch would add July–September 2026 CPI. **Currently blocked:** `SCHEDULER_ENABLED=false` in `backend/.env` (line present, checked 2026-10-12), and it runs only inside a started backend. |
| Claude Desktop tasks `aipheed`, `aipheed-auditing` | Session transcripts, plus any file the session decides to write | **Yes** (checklist 4) |

## 3. How accidental access is prevented later (proposed; approval A2 and A7)

| # | Control | What it stops | Known limit |
|---|---|---|---|
| X1 | **Allowlist loader** for the E8 frame. A manifest lists every permitted input path with its expected SHA-256. The loader checks the hash before reading and refuses any path not listed. | Reading a carrier by mistake through a helper that loads more than it uses (checklist 2, C7) | Only as good as the manifest; the manifest itself is part of approval A5 |
| X2 | **Deny-list guard** in the E8 process: `sys.addaudithook` raises on `open`, `os.listdir`/`os.scandir`, `sqlite3.connect` and `subprocess.Popen` events whose path matches the deny-list (§2). It also wraps `pd.read_parquet`, `pyarrow.parquet.read_table` / `ParquetFile` / `read_schema` and `joblib.load` to check paths. | Direct reads from Python | **PyArrow's native I/O does not raise Python `open` audit events**, which is why the explicit wrappers are needed. Code outside the E8 process is not covered. |
| X3 | **Hash-only utility** (`open(p, "rb")`, chunked, never decoded) as the only permitted call on deny-listed paths; used for pre- and post-run hash comparison | Content exposure during integrity checks | — |
| X4 | **Post-run comparison.** Every deny-listed hash must be unchanged after each step, and every allowlisted input must match the manifest. Any change halts the protocol. | Silent modification by a pipeline or another session | Detects change; does not detect reads |
| X5 | **Session rules** for any Claude session working on E8: only the operations in §1; no transcript reads of other sessions; no WebSearch or WebFetch of SWS, PSA or RSSO pages | Interactive accidents | Behavioural; enforced by X6 only if approved |
| X6 | **Project permission deny rules** (approval A7, option b). Example: `deny: Read(//c/Users/admin/aipheed/backend/data/**)`, `Read(**/cpi_full*.parquet)`, `Read(**/sws_hunger*.parquet)`, `WebSearch`, `WebFetch` for the blind period. | Reads by any session in this project, including the scheduled ones | Permission rules match tool patterns, so `Bash` and `python -c` can still read files. Defence in depth, not a guarantee. **This changes persistent configuration and needs explicit approval.** |
| X7 | **Production scheduler stays disabled** (`SCHEDULER_ENABLED=false`) until the 2026-Q4 outcome is evaluated | Automatic acquisition of July–December 2026 CPI into production | Changing `.env` or running the pipeline manually needs your approval |

**What cannot be guaranteed.** Reads leave no trace on disk, so a hash or mtime check can show that a file did **not change**, never that it was **not read**. Evidence that a protected file was not read in this session comes only from this session's own command history.
