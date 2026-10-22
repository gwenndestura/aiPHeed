# E91 deviations from the frozen protocol

| ID | When | Change | Effect on results |
|---|---|---|---|
| D1 | First `score` call, which failed before any arm was fitted or scored | The SAE poverty file path pointed to the E55 folder; the file lives in `backend/data/reference/`. Corrected the `SAE` constant only. | None: no metric had been computed. |

**Runner SHA-256 after D1:** see `DEVIATIONS.sha256`. `PROTOCOL.md` itself is unchanged.
| D2 | Second `score` call, which crashed inside the evaluation before any metric was printed or saved | `run_e83.evaluate` selects arms by column prefix and does not recognise `U-`. The U- columns are renamed with the accepted `HYB-` prefix for the call, and the results are mapped back. The scoring code itself is unchanged. | None: no metric had been seen. |
| D3 | Third `score` call, which crashed at K = 4 before any metric was printed or saved | (a) Arms that issue no row at a horizon (the structural core at K = 4) are recorded as unissued, with every row wrong, without calling the bootstrap. (b) Clarifies an ambiguity in §4: the frozen text does not say how unissued rows enter the selection Brier. Selection averages the horizons that **every** selectable candidate issues (K = 1..3), so a candidate is not chosen merely because it alone issues K = 4. K = 4 is still scored for every arm under the PASS rule. Fixed before any result was seen. | None on the metrics. (b) fixes the selection horizons before results. |
