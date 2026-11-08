# DRAFT: Protocol amendment (NOT ACTIVE)

> **Status: DRAFT TEMPLATE. NOT IN EFFECT.**
> - It changes nothing until every blank is filled, the owner and the adviser sign §6, and it is committed with its SHA-256 recorded in a test.
> - The frozen protocol (`docs/aipheed/PROTOCOL_LOCK.md`, SHA-256 `8bae6962…dd0d3`) stays read-only and is never edited by this amendment.

## 1. Amendment identity

| Field | Value |
|---|---|
| Amendment number | `____` |
| Title | `____` |
| Author | `____` |
| Date drafted | `____` |
| Evidence base | `docs/aipheed/v3/PROTOCOL_VALIDITY.md` (commit `____`) |

## 2. Chosen metric (fill one; definitions must be complete before signature)

| Item | Value |
|---|---|
| Option (from PROTOCOL_VALIDITY Task 2) | `____` (for example b2: published 95 % SWS margin) |
| Exact formula | `____` (for example tol(a, q) = 1.96 × √(Σ (MoE_i / 1.96)²) / k for the k non-commissioned rounds of quarter q, MoE_i the published area margin) |
| Source of every constant | `____` (must be a measurement property or a pre-existing document, never a result) |
| Leads it applies to | `____` |
| Threshold for success | `____` (if different from the frozen 75 %, an independent justification is required in §3) |
| Reliability rules | Frozen N1–N7 apply unchanged, except: `____` (none, or list) |

## 3. Justification

- **Measurement basis:** `____`
- **Why this was not chosen by its result:** `____`
- **Known limitation**, copied from PROTOCOL_VALIDITY Task 2 "cannot support": `____`
- **Development evidence:** it is shown for information only, labelled DEVELOPMENT, and is not a reason for adoption. Oracle `____`, persistence `____`.

## 4. Scope and effective date

- **Applies to sealed / future quarters only.** The first target quarter scored under this amendment is `____`. It must be a quarter with no published SWS round on the signature date.
- **Effective date** (signature date): `____`.
- **No re-scoring:** no quarter published before the effective date is re-scored to support a claim under this amendment.

## 5. Mandatory reporting rule

1. **Every** report, chapter, dashboard note or API response that cites a result under this amendment states, beside it and with equal prominence, the result under the **original frozen protocol** (tolerance 1.645 × binomial SE; N1–N7).
2. Development results (2021-Q2 … 2026-Q3) are always labelled DEVELOPMENT.
3. A result is reported as confirmed only after N1 (≥ 10 unseen target quarters, 40 rows) is met on future quarters.
4. Any later change is a new, numbered amendment; this one is never edited after signature.

## 6. Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| Researcher (owner) | `____` | `____` | `____` |
| Thesis adviser | `____` | `____` | `____` |
| Panel acknowledgement (if required) | `____` | `____` | `____` |

## 7. Activation checklist (all must be true)

- [ ] All blanks filled; no "for example" text remains.
- [ ] Signed by the owner and the adviser.
- [ ] Committed as `docs/aipheed/v3/PROTOCOL_AMENDMENT_<n>.md` (a new file; this draft is kept).
- [ ] SHA-256 recorded in a test, and `PROTOCOL_LOCK.md` re-verified unchanged.
- [ ] The scorer reports both the frozen and the amended metric (`backend/scripts/v2_score_sealed.py` extension, implemented after signature).
