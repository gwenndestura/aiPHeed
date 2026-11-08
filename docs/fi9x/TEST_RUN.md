# FI9-X test run (2026-11-03, branch fi9x/gov-news-fusion)

`python -m pytest tests/unit -q` (from `backend/`): **733 passed**, 0 failed, 218 s. The run includes the 9 new tests in
`test_fi9x.py`:
* lock and code hash;
* news-window future poisoning, with a control that changes the result when articles fall before the cutoff;
* past-only z-scores;
* issue and target alignment;
* independent metric recomputation;
* production unchanged when nothing is adopted;
* label numbers;
* the Crossref-verified literature;
* challenger register integrity and consistency with the served forecast.

Production FI9 (artifact, API, dashboard) was not changed, so the earlier dashboard verification
(docs/fi9r/TEST_RUN.md) still applies.
