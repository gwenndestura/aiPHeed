# E91 deviations from the frozen protocol

| ID | When | Change | Effect on results |
|---|---|---|---|
| D1 | First `score` call, which failed before any arm was fitted or scored | The SAE poverty file path pointed to the E55 folder; the file lives in `backend/data/reference/`. Corrected the `SAE` constant only. | None: no metric had been computed. |

**Runner SHA-256 after D1:** see `DEVIATIONS.sha256`. `PROTOCOL.md` itself is unchanged.
| D2 | Second `score` call, which crashed inside the evaluation before any metric was printed or saved | `run_e83.evaluate` selects arms by column prefix and does not recognise `U-`. The U- columns are renamed with the accepted `HYB-` prefix for the call, and the results are mapped back. The scoring code itself is unchanged. | None: no metric had been seen. |
