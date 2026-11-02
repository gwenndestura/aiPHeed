# v9 progress (resumable)

**Start:** branch `impl/backend-completion` @ `b221bca`. Protocol lock `8bae6962…dd0d3` verified at start (sha256sum, VERIFIED).

**Standing constraints:** no SWS web searches or fetches; PSA searches name years ≤ 2025 only; Chapter I is the only requirement basis; 2021+ only; no frontend design changes.

**Pre-existing untracked files are left untouched** (v6 seal files, `v6/serving.py`, `v6_seal.py`, `v6_score_sealed.py` and others). **v5, v7 and v8 documents do not exist** in this repository's history (`git log --all` on those paths is empty), so only v2, v3, v4 and v6 were read.

| Stage | Status | Commit |
|---|---|---|
| 1 Spec reconciliation | DONE: Gate 1 passed; label rule awaits owner; 12 ledger trials | this commit |
| 2 Agency methods | DONE: Gate 2 passed with restriction (unverified items excluded) | this commit |
| 3 Data audit | PARTIAL: news audited in v10; non-news sources not yet re-audited under v9 | |
| 4 Method design | NOT STARTED | |
| 5 Pre-registration | **BLOCKED** on the owner's label rule | |
| 6 Run | NOT STARTED | |
| 7 Face validity, ISO, API, tests | NOT STARTED; face validity needs FNRI regional values | |
