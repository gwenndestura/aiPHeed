# E91 deviations from the frozen protocol

| ID | When | Change | Effect on results |
|---|---|---|---|
| D1 | First `score` call, which failed before any arm was fitted or scored | The SAE poverty file path pointed to the E55 folder; the file lives in `backend/data/reference/`. Corrected the `SAE` constant only. | None: no metric had been computed. |

**Runner SHA-256 after D1:** see `DEVIATIONS.sha256`. `PROTOCOL.md` itself is unchanged.
