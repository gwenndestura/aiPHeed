# E112 Forecast horizon assessment

## 1. Issue-date horizon vs data age

- **Issue date:** O(t) = day 1 of quarter t+1.
- **Newest SWS reading:** the newest round published before O(t). At 19 of 21 issue dates it is quarter t−1 (E111 `out/horizon_table.csv`). The reason is that SWS publishes quarter t only after quarter t has ended.
- **Consequence:** a "Lead k" forecast is in fact **k+1 quarters past the newest observation** (the true horizon).

| Nominal lead | Target | Usual true horizon | Lead-1 evaluation rows (E112 BL) |
|---|---|---|---|
| 1 | next quarter | 2 | 8 of 9 rows at horizon 2; 1 row at horizon 1 (2025-Q3, when the 2025-Q2 round came out on 2025-06-27) |
| 2 | 2 quarters ahead | 3 | 6 of 7 at horizon 3 |
| 3 | 3 quarters ahead | 4 | 5 of 6 at horizon 4 |
| 4 | 4 quarters ahead | 5 | 4 of 5 at horizon 5 |

**The news indicators fill exactly the gap quarter t.** Its headlines are complete before O(t), but its SWS reading is not yet published. This is where news could add information, and it did not measurably do so (`E112_NEWS_EVALUATION.md`).

## 2. Maximum reliable horizon

| Evidence | Result |
|---|---|
| E112 BL candidates (LGBM12, LGBM12N, NEWS-C, NEWS-G) | Lead 1: not reliable. Leads 2–4: insufficient evidence (5–7 quarters < 8) |
| E112 panel NEWS-CP | Not reliable at Leads 1–4 |
| E111 panel (4 areas, 10–13 quarters) | Near misses only: ASYM at Lead 1 (fails the falling-hunger check) and LLR at Lead 2 (fails the ±4 BL bound) |
| Unseen (P6) | No sealed forecast has been scored yet. The first scorable quarter is 2026-Q4, expected about January 2027. |

| | Result |
|---|---|
| **Maximum reliable lead** | **None established.** |
| **Maximum provisional lead** | **None.** |
| **Practical reading** | The latest reading's own error at true horizon 2 (Lead 1) is about 3.0–3.7 points (MAE). At true horizons 3–5 its MAE is 3.2–5.5 points. These rest on 4–7 rows each and do not rise steadily. |

## 3. What would establish a horizon

Prospective scoring of the sealed forecasts (E109–E112 seals; `runner/score_prospective.py`). About 8 new SWS quarters (about 2 years) are needed before P1 can be evaluated on unseen data at Lead 1.
