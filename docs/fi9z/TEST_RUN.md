# FI9-Z test run and dashboard check (2026-11-03, branch fi9z/final-objectives)

## Automated tests

`python -m pytest tests/unit -q` (from `backend/`): **741 passed**, 0 failed, 227 s. This includes 5 new FI9-Z tests:
* class metrics against a hand-computed confusion matrix;
* the protocol and code lock;
* class metrics recomputed from the saved predictions;
* decision consistency, with production unchanged;
* the outlook API reporting the production model's HIGH-recall failure, P(LOW) and the news status.

## Browser check (API on port 8000, web dev server on 8080, `/dashboard`)

The outlook card showed, matching `/api/v1/fi9/outlook`:
* target 2027-Q1, class HIGH, 44 % HIGH and 56 % LOW;
* the track record: "caught 6 of 11 HIGH quarters (55%), 6 false alarms in 51 LOW quarters (LOW correctly identified 88%); balanced accuracy 0.71", with the statement that it misses too many HIGH quarters to meet the requirement;
* the five trigger groups (Market and prices; Climate stress; Employment and remittances; Poverty and social vulnerability; News and NLP), with news marked as not used to set the outlook.

Existing colours only. The P0H4 layer is unchanged.

**Open issue (owner decision):** the existing welcome tour (P0H4 layer) says aiPHeed forecasts whether "each CALABARZON province" is at high or low risk. No provincial or CALABARZON outcome supports that claim (CALABARZON_FORECASTING_FEASIBILITY_REPORT.md).
