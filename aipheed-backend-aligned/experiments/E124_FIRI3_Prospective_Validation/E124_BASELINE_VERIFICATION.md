# E124 baseline verification

**Checked on** 2026-10-31, against the files and the commit history.

**Starting commit:** `e78d7d4793d360f22623afd2f962693016315984` (E123), branch `aiPHeed/corrected-data-pipeline`, with no uncommitted changes under `backend/` or `experiments/E12*`.

| Item | SHA-256 | Status |
|---|---|---|
| E121 protocol `E121_FIRI3_PROTOCOL.md` | 8a431a9ddb1efc0515e1b539924562b65119649edf44dfac8e4c878c2bf4b717 | equals `firi3.PROTOCOL_SHA256` |
| Amendment 1 `E122_FIRI3_PROTOCOL_AMENDMENT_1.md` | 4fd05309c3dee0800693e9a12b92ed112aebef35f9a219a8a620c88860050549 | equals `firi3.AMENDMENT_1_SHA256`; **active** (40 rows rejected) |
| Amendment 2 `E123_FIRI3_PROTOCOL_AMENDMENT_2.md` | 8b5f729cc34790e00dbadbc5ce02bfd050ca31dc665fd049bff9e38675f7711b | equals `firi3.AMENDMENT_2_SHA256`; **active** (10 scores use the latest complete year) |
| `backend/app/ml/inference/firi3.py` (v `FIRI3-candidate-1.2`) | b04658a4deb6df4a2f617947a29c69aa18c50cd7fa89a5d5b4ddd7c98fcbabdf | unchanged in E124 |
| `backend/app/ml/inference/firi.py` (FIRI v2) | 0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3 | unchanged since 2b1f65a |
| `backend/data/thesis/firi2_history.csv` | b84558def7a00d4f077c0206d9c9cb6e9df3ef1fa02125fe0141f263ebb753ad | unchanged |
| `backend/data/thesis/firi2_reference.json` | 25af6411488563d0b5782aa9ac05792be79d4880399d18558a63203a44860189 | unchanged |

## Confirmations

1. **Amendment 1 is active.** `validate_inputs` rejects the 40 provincial 2021 CPI YoY rows (food 20, headline 20).
2. **Amendment 2 is active.** Annual EHS uses the latest complete year: 2025 is skipped, 2024 is used. CCS, SVS and the common cores are computed.
3. **The overall FIRI3 formula is unchanged** apart from the two amendments. A fresh run reproduces the E123 overall scores exactly (138 of 138, |Δ| < 1e-12). The comparison file shows that Amendment 1 changed 73 rows and Amendment 2 changed 10, with nothing else different.
4. **CCS and SVS remain supplementary** (`firi3.subscore`). The overall FIRI3 is computed independently of them.
5. **The common cores remain comparison tools** (`firi3.common_core`), reported beside FIRI3.
6. **FIRI v2 and production are unchanged.** Hashes above; `git status` of `backend/app`, `frontend/src` and `backend/data` is clean.
7. **E123 tests reproduce.** Full suite at `e78d7d4`: **1140 passed, 0 failed, 18 skipped**.
