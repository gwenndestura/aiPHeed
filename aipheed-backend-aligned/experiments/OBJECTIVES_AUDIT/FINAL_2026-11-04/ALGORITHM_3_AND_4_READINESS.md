# Algorithm 3 and Algorithm 4 readiness

## Algorithm 3 (75% rule: mean walk-forward accuracy ≥ 0.75, k = 1..8, stop at the first failure)

| Model | L1 | L2 | L3 | L4 | MRLT |
|---|---|---|---|---|---|
| C-b | 0.790 | 0.790 | 0.726 | — | 2 |
| **C-E2** | 0.774 | 0.758 | 0.758 | **0.645** | **3** |
| C-E2-NONEWS | 0.774 | 0.758 | 0.758 | 0.645 | 3 |

- **Reproduced** byte-identically (`CE2_REPRODUCTION_REPORT.md`).
- **The served C-E2 `evaluation.json`** now includes Lead 4, so the API states the stopping lead (0.645).

## Algorithm 4 (2027 prospective holdout)

| Step | Status |
|---|---|
| Seal procedure (`SENIOR_REVIEW/runner/seal_next.py`) | ✅ Dry run for issue 2026-10-01 (output to the scratchpad): every stored forecast replays (max diff 3e-16); `replay_matches: true` |
| Ledger untouched | ✅ `SENIOR_REVIEW/prospective/SEAL_LEDGER.md` SHA-256 b22faf62… before and after |
| C-E2 replay (`runner/seal_ce2_dryrun.py`) | ✅ Refit at 2026-Q3 equals the stored fit (diff 0.0); 2027-Q1 L2 p = 0.896098 HIGH; would-be record SHA 00c541cf… (scratchpad only) |
| C-E2 in the prospective registry | ❌ Not included. `seal_next.py` seals C-b, the 7 baselines, CLIM and K1–K3 |
| Real seal for the 2027-01-01 issue | ⏳ **Needs your explicit approval** |

**What the real seal for C-E2 requires:**
1. Approval to add C-E2 to `prospective_lib.CANDIDATES` and `seal_next.py`. This changes the registry spec.
2. Running `seal_next.py --issue 2027-01-01` between 1 and 15 Jan 2027, after the inputs are refreshed to what is
   published at O(t).
3. Committing the seal file and the ledger line (needs commit approval).

**The 2027 labels do not exist yet,** and nothing reads them. Scoring runs only after SWS publishes the 2027 rounds.
