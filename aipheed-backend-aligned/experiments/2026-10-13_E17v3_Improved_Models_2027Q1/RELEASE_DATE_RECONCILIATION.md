# Release-Date Reconciliation Status (E17 v3)

**Reused records (not repeated):**

- E9 `02_DATA_ELIGIBILITY_AND_FEATURE_AVAILABILITY.md`
- E12 `details.json` (per-round SWS dates)
- E13 `TARGET_AND_TIMING_AUDIT.md`
- E17 `DATA_TIMING_AUDIT.md`

| Series | Status | Evidence | Unresolved |
|---|---|---|---|
| **SWS rounds (H)** | **Reconciled per round** for 2021–2025: 18 `verified`, 3 `verified-single` publication dates (E12) | `details.json` | (1) `scripts/supplementary/timing_audit.py` records the 2025-Q4 release as **2026-05-12**, but E12's verified record has **2026-01-14**. E17 v3 uses E12's. (2) The **quarter assignment** of the three supplementary 2025 rounds (two placed in 2025-Q2, one in 2025-Q3) disagrees with `docs/DATA_AVAILABILITY.md`, which records no rounds in those quarters. **Disputed; not treated as settled.** |
| **Provincial food CPI (F, D)** | **Not reconciled.** Dates are proxies (national release + 14 days); a provincial date is verified only for 2024-Q4. | E9, E13 | Every provincial publication date before the forecast origin is assumed, not verified |
| **National LFS unemployment** | Schedule-based (E9), unverified | E9 | Unverified |
| **Regional CPI** (not used here) | Verified (E9) | E9 | — |

**What the timing assertions prove.** The code obeys the configured dates. It does **not** prove that the dates match real publication schedules.

**Consequence for the 2027-Q1 forecast:**

- **H:** input availability is verified (the 2025-Q4 round was published 2026-01-14), apart from the disputed assignment of the supplementary rounds.
- **F and D:** input availability rests on a proxy. **They cannot be described as operationally valid.**
