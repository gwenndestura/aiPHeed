"""aiPHeed FI6: food insecurity forecasting with an uncertainty-aware target (Objectives 1-4).

Why FI6 exists. FI5 (app.fi5) labelled a quarter HIGH when SWS hunger was above its five-year average. 74 % of its
evaluated labels sat inside the survey's sampling margin, so the label was mostly noise and no model could learn it.
FI6 changes three things, each fixed before any FI6 result was produced:

  1. Target: HIGH = hunger significantly above normal, i.e. above the five-year average by more than the round's
     published SWS margin of error (95 %). Label-flip probability under sampling error falls from 0.142 to 0.067.
  2. Model: LightGBM forecasts the continuous change in hunger from the latest published reading (using every
     quarter's information instead of ~10 rare positives); P(HIGH) comes from the forecast and its out-of-sample
     error spread. Monotone constraints encode the expected direction of each driver, so the model cannot learn a
     backwards relationship from a coincidence.
  3. Features: 18 a-priori features, one news composite per domain (no separate news group).

FI5's data layer (sources), NLP tier (XLM-R, BERTopic, FSSI), LGU ranking and plain-sentence code are reused.
"""

VERSION = "fi6-1.0"
