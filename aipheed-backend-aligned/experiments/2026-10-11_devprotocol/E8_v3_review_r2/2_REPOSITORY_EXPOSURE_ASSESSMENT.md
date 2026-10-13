# Repository Exposure Assessment (review revision r2)

**Status: 2026-10-12. Local git metadata only.** No fetch, pull, push, `git show`, `git diff` or file-content access. Nothing was copied or changed.

## 1. Confirmed facts (local metadata)

| Fact | Evidence |
|---|---|
| A single remote, `origin` = `https://github.com/gwenndestura/aiPHeed.git`. No credentials in the URL, no submodules, no `.gitattributes`, no LFS files listed. | `git config --get-regexp '^remote\.'` |
| **eee269b** ("Replace backend/ with the thesis-connected implementation", 2026-09-29) was authored and committed by **Christina Esico**, not in this clone | `git log`; HEAD reflog has no commit entry for it |
| This clone **received** eee269b by **fetch** on 2026-10-06 20:16:24 ("storing head"), then created the local `backend+frontend` branch from it | Reflog of `refs/remotes/origin/backend+frontend` and `backend+frontend` |
| As of that fetch, **origin's `backend+frontend` branch pointed to eee269b**. Local and remote-tracking refs are level (0 ahead, 0 behind). | `git rev-list --left-right --count` |
| eee269b is contained only in `backend+frontend` and `origin/backend+frontend` | `git branch -a --contains` |
| **Earlier carrier versions were pushed from this clone:** aa17da3 (2026-09-09, `sws_hunger`, `features_fused`, `final_predictions`; "extend training to 2021-2026Q2") and 4802f4d (2026-09-10, adds `cpi_full.parquet` and `psa_indicators.parquet`) | Reflog "update by push" on `origin/week12` |
| aa17da3 and 4802f4d are in `origin/week12` and `origin/backend+frontend`. 514e126 (Christina Esico, 2026-09-23: `final_predictions`, `aipheed.db`) is in `origin/backend+frontend`. | `git branch -r --contains` |
| The aligned `psa_indicators.parquet` is byte-identical to the 4802f4d blob (`03a4ec47…`). The aligned `cpi_full.parquet` is identical to blob `201e3e8d…`. Both are therefore in remote history. The aligned `sws_hunger`, `labels` and `features_fused` blobs are **not** in git history. | `git hash-object` + `git log --all --find-object` |
| Five Claude worktrees (`.claude/worktrees/*`) are at dc613c0 (2026-04-23), with no data files modified since 2026-07-01 | `git worktree list`; mtime scan |

### Affected paths (blob ID, size) at eee269b

| Path | Blob | Bytes | Introduced | Class |
|---|---|---|---|---|
| `backend/data/processed/psa_indicators.parquet` | 38167f68… | 8433 | M in eee269b (A in 4802f4d) | **P3-doc** (rows labelled to 2026-Q4) |
| `backend/data/thesis/panel.parquet` | 8e9d7a14… | 16455 | A in eee269b | **P3-doc** (to 2026-Q3) |
| `backend/data/thesis/panel_expanded.parquet` | 50d46d32… | 28364 | A in eee269b | Carrier |
| `backend/data/thesis/panel_multiagency.parquet` | e9b3864b… | 16638 | A in eee269b | Carrier |
| `backend/models/thesis_food_insecurity_model.joblib` | 5a9a2fb1… | 277996 | A in eee269b | P4? |
| `backend/data/processed/cpi_full.parquet` | 201e3e8d… | 13539 | A in 4802f4d (pushed from here) | Carrier |
| `backend/data/processed/sws_hunger.parquet` | 02ab6262… | 12582 | M in aa17da3 (pushed from here) | Carrier |
| `final_predictions.parquet`, `aipheed.db` | — | — | M in 514e126 | P4? / carrier |

## 2. Assumptions and unknowns

| Item | Status |
|---|---|
| Whether origin **still** has eee269b (it could have been force-pushed or deleted since 2026-10-06) | **Unknown.** Would need a fetch (not done). |
| Repository visibility (public or private), collaborators, forks, branch protection | **Unknown.** Read-only check for your approval: `gh repo view gwenndestura/aiPHeed --json visibility,isFork,forkCount` and the collaborator list in the GitHub settings UI. |
| Whether the 2026-Q3/Q4 rows in these files are real releases, partial, or placeholders | Unknown (earlier records say "partial or placeholder of unknown provenance"). Q4 rows committed 2026-09-29 **cannot** contain October–December 2026 data, which did not exist yet. |
| Other clones (the collaborators' machines, CI, the Vercel deployment) | Unknown. Vercel is recorded as an old frontend prototype (memory index). |

## 3. Remediation options (not executed; your decision)

The concern is **research blinding**, not secrecy: PSA and SWS figures become public anyway.

| Option | Effect | Cost and risk | Recommendation |
|---|---|---|---|
| R-a. **Process control:** never open these paths in any ref (`git show origin/...`, the GitHub web UI, the raw URLs), and add them to the deny-list | Protects the blinding from your side | No repository change | **Do now (needs only your agreement)** |
| R-b. **Access restriction:** if the repo is public, make it private; review collaborators; ask the collaborators not to open these files until the outcome is collected | Limits who can see the files | Visibility change is a repository setting; needs the owner (gwenndestura) | Recommended if public |
| R-c. **Stop propagation:** commit nothing further that adds 2026-H2 rows; keep the production pipeline disabled | No new exposure | None | Recommended |
| R-d. **History rewrite** (`git filter-repo` to drop the paths, force-push, collaborators re-clone, GitHub support to purge cached views) | Removes the files from GitHub history | **Destructive.** It breaks commit IDs cited in the integrity records (eee269b, 514e126, aa17da3, 4802f4d), does not remove existing clones or forks, needs every collaborator's coordination, and touches the teammates' work. | **Not recommended** for a blinding concern. Consider only if the files contain something genuinely confidential. |
