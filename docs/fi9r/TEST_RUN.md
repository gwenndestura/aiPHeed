# FI9-R test run and dashboard check (2026-11-03)

## Automated tests

`python -m pytest tests/unit -q` (from `backend/`): **718 passed** in 242 s, 0 failed. This includes:
* `test_fi9r.py` (9): production pin, isolation of the reassessment code, register immutability, conformal
  interval equality, local-level filter, reproduction, label stability, API scope and baseline;
* `test_fi9.py` (15);
* `test_fi_labels.py` (17);
* FI5–FI8.

Audits: `python -m app.fi9r.audit run` passes 13/13 checks; `python -m app.fi9.audit run` still passes.

## Served forecast vs dashboard

The API (port 8000) and web dev server (port 8080) were run, and the `/dashboard` card read in the browser:

| Field | API `/api/v1/fi9/outlook` | Dashboard card |
|---|---|---|
| Target quarter | 2027-Q1 | 2027-Q1 |
| Class | HIGH | HIGH |
| Probability | 0.44 | 44% |
| Projected hunger | 20 | 20% |
| Likely range | [9, 30] | 9–30% |

The card also showed:
* the baseline comparison ("no better than simply carrying the latest reading forward");
* the 5 limitations;
* the FNRI 2015 provincial measurements, labelled as historical survey values and not a forecast.

The approved colours are unchanged. The existing P0H4 panels are unchanged.
