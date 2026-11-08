# E174 results: pure zero-shot XLM-RoBERTa Tier 1

- **Protocol:** `docs/e174/PROTOCOL.md` (blob 0552e845, commit ce5f0a09), locked before these runs.
- **Code:** `backend/app/e174/zero_shot.py` (Step A) and `backend/app/e174/model.py` (Step B).
- **Outputs:** `backend/data/e174/out/` (zero-shot news panel, FSSI, topic report) and `backend/data/e174/model/`.

## Step A: zero-shot news signals and FSSI (adopted as the Objective 1 FSSI, as locked)

Re-mapping the 257 BERTopic topics with zero-shot probabilities only moved **163 of them** to a different trigger group. The extra readers had been shaping the mapping a great deal.

| Check | E151 FSSI (three readers) | **Zero-shot FSSI** |
|---|---|---|
| Within-province ρ, FSSI vs food CPI | 0.033 | 0.015 |
| Within-province ρ, market stress vs food CPI | 0.044 | −0.011 |
| Event z, 2018-Q4 rice surge (FSSI / market stress) | −1.00 / +3.26 | −1.42 / +2.03 |
| Event z, 2023-Q4 rice crisis (FSSI / market stress) | −1.30 / +0.49 | −1.73 / −0.13 |
| Event z, 2022-Q1 after Odette (FSSI) | +1.30 | +1.25 |

**Result:**
- The zero-shot FSSI is what Objective 1 specifies, so it is now the Objective 1 FSSI.
- It is no better on the face checks. The diagnosis in `NLP_FSSI_VALIDATION_E168.md` still applies: dilution across groups, coverage collapse in 2023-Q4, and outlet centring.
- Nothing was re-weighted.

## Step B: E168 with zero-shot news inputs

The same 72 forecasts per lead were scored.

| Lead | E174 accuracy | E168 accuracy | Persistence | E174 Brier | E168 Brier | E174 − E168 (95 % CI) | Beats persistence |
|---|---|---|---|---|---|---|---|
| 1 | 73.6 % | 75.0 % | 62.5 % | 0.1230 | 0.1230 | −0.0000 [−0.0016, +0.0016] | yes |
| 2 | 77.8 % | 77.8 % | 62.5 % | 0.1230 | 0.1221 | +0.0008 [−0.0033, +0.0053] | yes |
| 3 | 75.0 % | 75.0 % | 62.5 % | 0.1323 | 0.1352 | −0.0029 [−0.0119, +0.0064] | yes |

**Decision, by the locked rule:**

| Check | Result |
|---|---|
| Non-inferior to E168 at Lead 1 (upper CI below +0.010) | **yes** (+0.0016) |
| Project rule at Leads 1–3 | **no**: Lead 1 is 73.6 %, one forecast short |

**E168 stays served.**

**What this means:**
- The pure zero-shot news inputs produce the **same forecast quality** as E168's three-reader inputs (identical Lead-1 Brier). So deviation D3 does not drive E168's results.
- E168's served news columns still come from the three-reader version. This is disclosed as a remaining deviation.
