# FINAL-ETMIX: independent validation status, FNRI data audit and face validity (Objectives 2 and 5)

## 1. Is FINAL-ETMIX independently validated? **No.**

| Evidence | What it is | Admissible as independent validation? |
|---|---|---|
| Walk-forward Leads 1–8 on ENNS 2018 / 2019 / 2021 (72 province-rounds) | Every fold trained only on rounds released by its origin | **No.** The same 72 outcomes were used across about 45 FINAL-family configurations. ETMIX's structure was fixed knowing its two components' results on them (protocol `a365da1f` records the predicted result before computing it) |
| Prospective seal for ENNS 2022 | FINAL, FINAL-ET and FINAL-ETMIX forecasts for 78 provinces, Leads 1–2, sealed 2026-11-12 23:45 UTC, sha256 `71ebe142…2370` (re-verified 2026-11-13: hash matches; FINAL rows agree with the earlier FINAL seal `4ad9267f` within 5e-7) | **Yes, once scored.** No 2022 provincial HFIAS outcome exists locally, so it cannot be scored now |
| Face validity, CALABARZON (section 4) | Agreement with published FNRI / PSA figures | **No.** Contextual agreement only; no HIGH case exists in CALABARZON |

**Conclusion.** The reported Lead-1 results are honest **retrospective** findings, not independent validation:
- accuracy 0.861; precision 0.778; HIGH recall 0.84; F1 0.808; AUC 0.903.

ETMIX therefore stays **experimental**. E196 remains production.

## 2. Public HFIAS datasets: what the repository holds

| Round | Instrument | Geography | In repository | Weights / design | Used in development? |
|---|---|---|---|---|---|
| NNS 2013 | HFIAS | 78 provinces | `data/e141/clean/nns2013_hfias.csv` (FNRI Facts & Figures, Appendix 33) | Published estimates; SE approximated (design effect from 2015) | Yes: anchors, 2013→2015 training transition |
| 2015 Updating Survey (FNRI Food Security) | HFIAS | 78 provinces + regions | `data/hfias/clean/fnri2015_hfias.csv` | Published estimates with SEs | Yes: anchors; training |
| ENNS 2018 | HFIAS | 38 areas (22 with model inputs) | `data/hfias/clean/enns_hfias.csv` | Published estimates, 90 % CIs | Yes: evaluation fold, later training |
| ENNS 2019 | HFIAS | 38 areas (25 with inputs) | same file | same | Yes |
| ENNS 2021 | HFIAS | 37 areas (25 with inputs) | `data/e147/raw/sealed_2021_labels.csv` (FNRI Heat Map) | No provincial SE published (3.0 points assumed) | Yes |
| NNS 2023 | **FIES** (12-month recall) | Region IV-A 19.1 % (95 % CI 17.0–21.1) | `data/fi_labels/clean/published_fies_psa_sdg212.csv` | Published regional estimate | **Face validity only.** Never a label |
| 2022 ENNS follow-up | HFIAS expected | 20 provinces / HUCs | **Not in repository.** Provincial HFIAS tables are not public in the needed form | — | No: this is the independent test |
| FNRI HFIAS microdata (any round) | HFIAS | Province (design-based) | **Not in repository.** No public-use file found for recent rounds | Needs an FNRI data-sharing agreement | No |

**Rules applied:**
- FIES and HFIAS are never interchanged.
- The 2023 CALABARZON figure is never turned into provincial HFIAS labels.
- No restricted data were obtained or bypassed.

Full detail, with official links: `../aiPHeed_completion_audit_20261113/FINAL_SURVEY_DATA_AVAILABILITY_REPORT.md` (re-checked here).

## 3. Can more public data improve the model or validation now?
No. Every public provincial HFIAS round is already in the training or evaluation rows. The two things that would help both need FNRI:
1. **The 2022 ENNS provincial HFIAS (moderate + severe) results** for its 20 provinces / HUCs. Getting them needs:
   - **your action:** a written request to DOST-FNRI, or an FOI request (portal: foi.gov.ph, NNC/FNRI);
   - the variable "HFIAS moderate + severe, % of households, by province", with SEs.
2. **HFIAS microdata** under an FNRI data-sharing agreement, to replace the approximated 2013 and 2021 standard errors.

## 4. Face validity: DOST-FNRI NNS 2019 and the 2023 CALABARZON reference

| Province | Published HFIAS moderate + severe | Round | Class | ETMIX retrospective forecast (Leads 1–8) | Agreement |
|---|---|---|---|---|---|
| Quezon | 44.0 % | ENNS 2019 | LOW | p 0.11–0.23 (LOW at every lead) | Yes |
| Rizal | 39.1 % | ENNS 2019 | LOW | p 0.02–0.04 | Yes |
| Laguna | 26.2 % | ENNS 2018 | LOW | p 0.02–0.03 | Yes |
| Batangas | 39.9 % | ENNS 2021 | LOW | p 0.00–0.04 | Yes |
| Cavite | 35.5 % | ENNS 2021 | LOW | p 0.00–0.03 | Yes |

Source: `evidence/ETMIX_province_by_lead.csv`.

- **Sealed ENNS 2022 forecasts for CALABARZON (FINAL-ETMIX):** all LOW (p 0.007–0.049). Quezon is the highest, matching its standing as the highest CALABARZON province in 2019.
- **2023 regional FIES (19.1 %, CI 17.0–21.1):** directionally consistent with all-LOW provincial HFIAS forecasts. It is a different instrument with a 12-month recall, so this is context, **not** a test.
- **Live 2027-Q1 FINAL-ETMIX forecasts (experimental):** see `FINAL_ETMIX_BACKEND_FRONTEND_COMPLETION_REPORT.md`.

**What face validity shows and does not show.**
- It shows that the model's CALABARZON outputs agree with published CALABARZON prevalence: all LOW, with Quezon highest.
- It cannot test HIGH detection: no CALABARZON province has been HIGH since 2015.
- It is contextual agreement, **not independent predictive validation**.

## 5. Exact remaining dependencies
1. Provincial HFIAS outcomes for any province covered by the sealed forecasts (ENNS 2022) or by a future round forecast from sealed origins. Once obtained, score the sealed ETMIX rows once under PROTOCOL_SA.
2. About 10 or more HIGH provinces per future round, and 600–1,000 accumulated forecasts, before calibration limits like ECE ≤ 0.05 become testable.
3. DA Region IV-A ISO/IEC 25010 per-characteristic results (Objective 5). These are separate from model validation; see the completion matrix.
