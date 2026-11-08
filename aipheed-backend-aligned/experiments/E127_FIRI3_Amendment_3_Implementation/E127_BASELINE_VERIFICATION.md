# E127 baseline verification (before any change, 2026-10-31)

| Item | Value |
|---|---|
| Starting commit | `fd2794a029a4c7bcbd3a9fd3ae6ec2a646092970` (E126); no uncommitted changes under `backend/` or `experiments/E12*` |
| FIRI3 version | `FIRI3-candidate-1.2` |
| `firi3.py` | `c55224e3dd3e7e53ef9f948431f4adc9bc43e6d4d01261332b552c04582892cd` |
| E121 protocol | `8a431a9ddb1efc0515e1b539924562b65119649edf44dfac8e4c878c2bf4b717` |
| Amendment 1 | `4fd05309c3dee0800693e9a12b92ed112aebef35f9a219a8a620c88860050549` |
| Amendment 2 | `8b5f729cc34790e00dbadbc5ce02bfd050ca31dc665fd049bff9e38675f7711b` |
| E126 Amendment 3 proposal | `a359c6cfbf1e0c35612458c699823c9e3af79c8f4f49075737e03cf3c5d88c8b` |
| E124 frozen configuration (v1.2, canonical JSON) | `8973ca661cfcd68d41d7d1c9eb033adcdf3454723a7253294a8343f70d2178f0` |
| `firi.py` (FIRI v2) | `0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3` |
| Store | `forecasts/` empty; registry: 1 `attempt_blocked` event (2026-10-31, `FIRI3-1.2-2026-Q4`) |
| E126 outputs | SHA-256 of every `E126_*` file in `out/summary.json` → `e126_outputs_sha256`; not modified |

## Scope of the approval

The approval concerns only the three quarters that E126 found absent and verified as zero: **2023-Q1, 2024-Q1, 2025-Q1**.

- **The general rule adds exactly these three in 2021–2026.** `E127_PAR_ZERO_STORM_DATA.csv` → `explicit_zero_added`.
- **No other PAR count changes.** The one difference from E114's file is 2026-Q3 (E114: 8; builder: 7). That is E125's de-duplication of WP172026 SAUDEL, and E119 never used that E114 value.
- **Every other input is identical** between v1.2 and v1.3 (`other_inputs_identical = true`).
