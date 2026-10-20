# aiPHeed: objective ISO/IEC 25010 measurements (E63)

Measured 2026-10-18 on branch `final-aipheed-integration` (uncommitted working tree).

**What changed:** no app code, model, record, calibration or frontend file. Added:
- tests under `backend/tests/quality/`;
- the load script `backend/experiments/e63/runner/loadtest.py`;
- this report, and the raw results in `backend/experiments/e63/E63_load.json`.

**Databases:** all tests used a throwaway SQLite database (the `api` fixture of
`tests/integration/test_api_admin.py`). The load test used its own temporary database; `aipheed.db` was not used.

> **These objective measurements complement, not replace, the DA Region IV-A evaluator survey (H5).** ISO/IEC 25010
> quality in use and the evaluators' judgements of functional suitability and usability can only come from the
> pre-declared survey (at least 30 valid responses, `E25.../instruments/DECISION_RULES.md`). H5 remains untested
> until that survey is run. Nothing here is a usability or user-satisfaction result.

## Test environment

| Item | Value |
|---|---|
| Machine | Laptop, 11th Gen Intel Core i5-1135G7 @ 2.40 GHz, 4 cores / 8 threads; 7.8 GB RAM (0.9 GB free at the start); NVMe SSD (Micron 2210) |
| OS / runtime | Windows 11 Home 10.0.26200; Python 3.13.7; uvicorn 0.45.0; httpx 0.28.1 |
| Server | `uvicorn app.main:app`, **one worker**, 127.0.0.1:8011; `AIPHEED_RECORD=e49`, `AIPHEED_MAX_LEAD=1`; throwaway SQLite; scheduler off |
| Rate limiter | **Off** for the load test. A single load-generator address would otherwise be throttled on the guarded routes. The limiter's behaviour is covered by its own tests (Security section). |
| Load generator | asyncio + httpx on the **same laptop** (client and server compete for the CPU). N concurrent users, each looping over the 7 endpoints; 5 s warm-up (not measured), then 60 s measured per level. |
| Endpoints | `/provinces`, `/forecast` (region and province), `/ranking`, `/explainability` (province), `/provinces/quezon/municipalities`, `/report/data` (trend, region), all for 2026-Q4 |

## 1. Performance efficiency

ISO/IEC 25010 sub-characteristics: **time behaviour** (latency), **capacity** (throughput at increasing load) and
resource utilisation (not measured; see limits).

Latencies are of successful responses, in milliseconds; throughput is successful responses per second.

### 10 concurrent users

| Endpoint | Requests | Throughput (req/s) | p50 | p95 | p99 | Error rate |
|---|---|---|---|---|---|---|
| provinces | 427 | 7.1 | 184 | 413 | 521 | 0 |
| forecast (region) | 428 | 7.1 | 289 | 608 | 709 | 0 |
| forecast (province) | 427 | 7.1 | 267 | 510 | 632 | 0 |
| ranking | 427 | 7.1 | 178 | 394 | 476 | 0 |
| explainability | 424 | 7.1 | 59 | 162 | 248 | 0 |
| municipalities | 426 | 7.1 | 209 | 393 | 476 | 0 |
| report/data | 426 | 7.1 | 118 | 269 | 341 | 0 |
| **All** | **2,985** | **49.8** | **172** | **462** | **609** | **0** |

### 50 concurrent users

| Endpoint | Requests | Throughput (req/s) | p50 | p95 | p99 | Error rate |
|---|---|---|---|---|---|---|
| provinces | 421 | 7.0 | 1,238 | 3,625 | 5,473 | 0 |
| forecast (region) | 424 | 7.1 | 876 | 3,627 | 4,377 | 0 |
| forecast (province) | 431 | 7.2 | 1,085 | 3,820 | 5,687 | 0 |
| ranking | 433 | 7.2 | 569 | 3,436 | 5,059 | 0 |
| explainability | 429 | 7.2 | 97 | 224 | 314 | 0 |
| municipalities | 427 | 7.1 | 1,157 | 3,641 | 6,939 | 0 |
| report/data | 422 | 7.0 | 164 | 321 | 501 | 0 |
| **All** | **2,987** | **49.8** | **488** | **3,272** | **5,038** | **0** |

### 100 concurrent users

| Endpoint | Requests | Throughput (req/s) | p50 | p95 | p99 | Error rate |
|---|---|---|---|---|---|---|
| provinces | 429 | 7.2 | 2,544 | 7,627 | 12,199 | 0 |
| forecast (region) | 438 | 7.3 | 815 | 8,246 | 11,771 | 0 |
| forecast (province) | 437 | 7.3 | 2,178 | 7,637 | 10,420 | 0 |
| ranking | 433 | 7.2 | 1,420 | 7,713 | 10,578 | 0 |
| explainability | 431 | 7.2 | 116 | 244 | 326 | 0 |
| municipalities | 431 | 7.2 | 2,645 | 9,089 | 13,284 | 0 |
| report/data | 429 | 7.2 | 164 | 310 | 365 | 0 |
| **All** | **3,028** | **50.5** | **504** | **7,441** | **11,053** | **0** |

### Reading

**Capacity**
- Throughput saturates at about **50 requests/s** (one worker, on this laptop) and does not grow from 10 to 100
  users.
- Extra users therefore queue. The overall p95 rises from 0.46 s (10 users) to 3.3 s (50) and 7.4 s (100); p99
  reaches 11 s at 100 users.
- No request failed at any level.

**Time behaviour**
- At 10 users every endpoint answers within 0.71 s at p99.
- The routes that read the review state from the database are the ones that slow down under load: `/provinces`,
  `/forecast`, `/ranking` and `/municipalities` (each reads the withheld list per request).
- `/explainability` and `/report/data` stay fast: p99 0.33 s and 0.37 s even at 100 users.

**Limits of this measurement**
- Client and server share one 4-core laptop with little free memory. This is a worst-case local measurement, not
  the capacity of a deployed server.
- A single worker. More uvicorn workers or a host with more cores would raise capacity.
- CPU and memory use were not recorded, so **resource utilisation is NOT MEASURED**.

## 2. Reliability

ISO/IEC 25010 sub-characteristics: **availability / fault tolerance** (errors under load) and **recoverability**
(restart).

**Error rate under load:** 0 of 9,000 requests failed across the three load levels.

**Restart mid-run**
- 50 users for 60 s. The server process was killed at t = 20.0 s and a new one was started at once.

| Measure | Value |
|---|---|
| Recovery time (kill -> first successful response) | **5.3 s** (cold start of a new process alone: 4.9 s) |
| Failed requests | 120 of 2,731 (4.4%): 48 in flight at the kill, 72 attempted while the server was down. Errors were ConnectError and ReadError only. |
| Errors after recovery | **0** |
| Throughput over the 60 s including the outage | 43.5 req/s |

**Reading**
- **Recoverability:** recovery is bounded by process start-up (loading the record and the model libraries). Once
  the new process answered, no request failed. Nothing is persisted per request except the review state in the
  database, so no data loss is possible from the restart.
- **Availability limit:** a single process means a restart is an outage of about 5 s. A deployment with two
  workers or instances behind a proxy would hide it; this was not measured.

## 3. Security

ISO/IEC 25010 sub-characteristics: **confidentiality**, **integrity**, **authenticity**, **accountability** and
non-repudiation.

### Existing tests, summarised (unchanged)

| File / class | Tests | What they establish | Sub-characteristic |
|---|---|---|---|
| `test_api_admin.py::TestAuth` | 12 | Admin route needs a token; wrong password and unknown account give the same answer; forged token refused; logout revokes; deactivated account stops at once; non-admin role 403; default SECRET_KEY refuses to sign; failed sign-ins and sign-outs audited without the password; outside e-mail domains cannot sign in | authenticity, accountability, confidentiality |
| `test_api_admin.py::TestRateLimiting` | 9 | Login attempts capped (counting successes too), per-account failure lockout across addresses, report generation and feedback capped, limits per client | integrity / availability under abuse |
| `test_api_admin.py::TestInputLimits` | 5 | Free text, names, e-mails, notes and passwords capped | integrity |
| `test_api_admin.py::TestRejectionIsEnforced` | 11 | Public rejection list names no reviewer; withheld forecasts 404 everywhere; publication changes need an admin | confidentiality, integrity |
| `test_api_accounts.py` (7 classes) | 57 | Sign-up, e-mail verification (single-use, expiring, hashed links), approval, password reset (one hour, single use, old sessions ended), demo account read-only with masked personal details | authenticity, confidentiality, accountability |
| `test_api_sessions.py` (6 classes) | 27 | HttpOnly SameSite refresh cookie, hashed storage, rotation and reuse detection, idle and maximum lifetime, CSRF header and origin checks, logout and password change end sessions | authenticity, integrity |

### Added (`backend/tests/quality/test_security.py`, 52 tests, all pass)

- **Every admin route (16 method-path pairs, found from the app's routing table, not listed by hand):**
  - no token: 401 `missing_token`;
  - expired token (correctly signed, `exp` two hours ago): 401 `token_expired`;
  - non-admin role: 403 `forbidden`.

  That is 48 tests (16 routes x 3 cases), plus 1 test that the routing table yields at least 16 admin routes.
- **Public routes expose no personal data** (1 test).
  - Setup: a respondent first submits the survey with a full name, e-mail, agency and designation, and an admin
    signs in and rejects a forecast.
  - Then 20 public GET routes are fetched (map, ranking, forecast, timeseries, LGUs, explainability, news,
    rejections, alerts, search, report payloads, record summary, topics, config).
  - None contains the respondent's name, e-mail, agency or designation, or the admin's name or e-mail.
  - `/rejections` carries only province, quarter, reason, notes and timestamp.
- **Public routes need no token and ignore a bad one** (1 test).
- **Rejection notes are public** (1 test, a documented observation): the reviewer's free-text note is published on
  `/rejections` (`RejectionRow.notes`). It names no reviewer, but text an admin types there is public.

### Finding (not changed: report only)

- **Free-text notes:** rejection notes are public free text. If the DA wants zero risk of personal data reaching
  the public site, either the notes field should be dropped from the public schema, or reviewers told that notes
  are published.
- **Security overall:** no other confidentiality issue was found.

## 4. Functional suitability

ISO/IEC 25010 sub-characteristic: **functional correctness** (consistency of the served numbers).

`backend/tests/quality/test_functional_consistency.py` (2 tests, both pass) checks every one of the 14 served
quarters (2023-Q1..2026-Q4, without 2025-Q2/Q3). For each province, the score is **identical** across:
- `/provinces` and `/ranking`;
- `/forecast` (province);
- `/explainability` (riskScore);
- the PDF payload `/report/data`: the figure series for every quarter, and Table 1 at two decimals for the latest
  quarter.

Two further checks:
- The region score from `/forecast` equals the mean of the five provinces, and equals the regional `/explainability`
  riskScore.
- The driver report's bars equal the explainability shares and directions.

**Result:** 70 province-quarters, no mismatch.

Functional completeness and appropriateness (whether the functions meet the DA's needs) are not measurable this
way; they are part of the survey (H5).

## Summary by ISO/IEC 25010 sub-characteristic

| Characteristic | Sub-characteristic | Objective result | Status |
|---|---|---|---|
| Performance efficiency | Time behaviour | p95 0.46 s at 10 users; 3.3 s at 50; 7.4 s at 100 (one worker, shared laptop) | measured |
| Performance efficiency | Capacity | about 50 req/s saturation; 0 errors up to 100 users | measured |
| Performance efficiency | Resource utilisation | not recorded | NOT MEASURED |
| Reliability | Availability / fault tolerance | 0 errors in 9,000 requests under load | measured |
| Reliability | Recoverability | 5.3 s from kill to first success; 0 errors after; 120 requests lost during the restart | measured |
| Security | Authenticity | every admin route refuses missing, expired and wrong-role tokens; existing token, session and CSRF tests | tested (pass) |
| Security | Confidentiality | no personal data on 20 public routes; caveat: public rejection notes | tested (pass) + 1 finding |
| Security | Accountability | admin actions and sign-ins audited (existing tests) | tested (pass) |
| Security | Integrity | input caps, rate limits (existing tests) | tested (pass) |
| Functional suitability | Functional correctness | the same score on every endpoint and in the PDF payload, all 14 quarters | tested (pass) |
| Functional suitability | Completeness / appropriateness | needs the evaluators | survey (H5) |
| Usability, quality in use | all | needs the evaluators | survey (H5) |

## How to reproduce

```
cd backend
ENABLE_API_DOCS=false venv/Scripts/python.exe -m pytest tests/quality -q
venv/Scripts/python.exe -B experiments/e63/runner/loadtest.py      # about 5 minutes; port 8011
```
