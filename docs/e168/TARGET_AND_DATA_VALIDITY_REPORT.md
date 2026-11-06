# Target and data validity report

**Unchanged from the final audit. See:**
- `docs/final/TARGET_VALIDITY_AUDIT.md`: FNRI HFIAS moderate + severe by province; 5 rounds (2013, 2015, 2018, 2019, 2021); HIGH ≥ 50; the 2021 SE assumed at 3.0 points; FIES, SWS and poverty never pooled; the post-2015 decline is plausible but its design comparability is not proven;
- `docs/final/DATA_AVAILABILITY_AND_PROVENANCE.md`: source, level, frequency, as-of rule and missingness per group; employment and remittances **national only**; consumption ends in 2023, so it is unavailable at the 2026-Q4 issue.

**E168-specific notes:**
- **In-fold correlation pruning** reduced the feature set to 20 columns (2018/2019 origins) and 62 (2021).
- **No national value was copied into provinces.**
- **Leakage test:** unreleased-round corruption changed E168 forecasts by **0.0**.
