# E95 deviations

| ID | When | Change | Effect |
|---|---|---|---|
| D1 | The first run crashed before any metric existed | Skip origins that have no evaluation rows at a given K (the E93 guard had not been carried over) | None |
| D2 | The final console print at K = 4, after `metrics.json` was written | Use `.get` for arms not issued at K = 4 (S-COV, E92) | None. Printing only. |
