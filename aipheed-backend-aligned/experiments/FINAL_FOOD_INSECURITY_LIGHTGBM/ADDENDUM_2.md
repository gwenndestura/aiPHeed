# Addendum 2: replication test of the agri-supply news signal

**When frozen:** after protocol §8.4 found one Holm-significant leading association, and before the test below was run. The SHA-256 is in `runner/ADDENDUM_2_SHA256.txt`.

## The finding to be replicated

- **Signal:** `NC_gap_agri_supply`, the change in the share of agriculture and supply headlines since the last survey, in the project corpus.
- **Association:** it correlates with the realised hunger anomaly z at Lead 1. Spearman ρ = 0.74 on 17 origins (4-area mean); Holm p = .018 over 7 columns × 4 leads.
- **Already-known non-replication:** the same category from GDELT GKG CALABARZON themes does not replicate (ρ = 0.16, p = .53).
- **Status:** E112 had reported an agri-supply lead (Holm p = .074) on the same 2021+ quarters, so this is not a fresh discovery. It needs replication in data it was not found in.

## The single replication test (one-sided, α = 0.05)

**Signal used:** the GDELT DOC national `agri_supply` volume series (E114), gap-aligned as in §7.

The column `ND_gap_agri_supply` is already built for every row of the long-history panel.

**Test:** Spearman ρ between `ND_gap_agri_supply` at O(t) and the 4-area mean realised z at Lead 1, computed per origin, in two separate periods:

| Set | Targets | Status |
|---|---|---|
| (a) | 2018-Q1 … 2020-Q4 | Never used for any news association; the only untouched news period |
| (b) | 2021-Q1 onward | Independent source, same period |

**Verdict rule**
- **Replicated:** ρ > 0 with one-sided p < 0.05 in set (a).
- **Consistent:** ρ > 0 in set (b).
- **Otherwise:** the corpus association is reported as unreplicated.

**Nothing else is tested.**
