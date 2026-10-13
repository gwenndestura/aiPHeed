# Formula Definitions (E12)

**Notation:**

| Symbol | Meaning |
|---|---|
| H[t] | SWS Balance-Luzon involuntary hunger % (mean of the quarter's definition-A rounds). **Regional: one value shared by all five provinces.** |
| F[p, t] | PSA provincial food CPI year-on-year % (quarterly mean of monthly values) |
| D[p, t] | F[p, t] − mean of the five provinces' F[t]; defined only when all five provinces have F |

**Formulas and baselines:**

| Name | Formula | Output label | Threshold / classification |
|---|---|---|---|
| **S1 (baseline)** | H + 2D | Constructed stress indicator | τ0 = 10.84335; HIGH if S1 > τ0 |
| Option A(α, β) | α·H + β·D, with α ∈ {0, .25, .5, .75, 1, 1.25} and β ∈ {.5, 1, 1.5, 2, 2.5, 3} | Weighted composite | Only for α/β = 1/2: threshold (β/2)·τ0. Otherwise **none defined** |
| Option B(wH) | wH·Z(H) + (1 − wH)·Z(D), where Z uses training-only mean and SD in each chronological fold (H statistics over training quarters, one per quarter; D statistics over training province rows) | Standardized composite | **None defined** |
| Option C | D | **Relative provincial food-price pressure.** Not hunger; a value near 0 does not mean low food insecurity. | **None defined.** It sums to 0, so a 0 cut always splits the provinces. |
| H only | H | Regional hunger (Balance Luzon) | Not a provincial classification |
| F only | F | Provincial food inflation (absolute, not relative) | None |
| D only | D | Identical to Option C | None |
| S1 carry-forward | S1 of the latest published label | Persistence baseline | τ0 (S1 scale) |
| Own-score carry-forward | Each score's latest published value | Persistence of that score | Scale-free metrics only |

**Category B inputs at the origin (start of quarter T):**

- H_in: the latest SWS round published before the origin (verified dates);
- D_in, F_in: values at T−2 (provincial release date proxy, unverified);
- S1 carry-forward: the latest published label.

**Common-scale mapping (Category B):** S1_target ≈ a + b·score, fitted by least squares on **training folds only**. Ranking metrics do not depend on the mapping when b > 0.
