"""aiPHeed FI7: release-aware operational forecasting system (Objectives 1-4).

FI7 keeps the FI6 target (SWS Balance Luzon hunger significantly above its five-year normal), the FI6 change model
and the FI6-N news archive, and adds:

  * release-aware operational issue dates: the forecast is issued inside the current quarter (end of its second
    month), when DA would actually use it, with every input as published by that date;
  * forward-looking and sharper government indicators tested one at a time (world rice and fertilizer prices,
    typhoon intensity, underemployment, fisheries output);
  * timely news windows (the 90 days before the issue date) instead of the last complete quarter;
  * simple statistical competitors (damped persistence, ridge change model) and training-only decision thresholds;
  * an experiment registry: every change is a controlled experiment against the frozen FI6-N reference.

Lead convention (what the dashboard shows): the issue date lies in the dashboard's current quarter c.
"h = 1" is the NEXT quarter (c+1), the DA operational outlook; h = 2, 3 are further ahead; h = 0 is the current
quarter (a nowcast, SWS for c is not yet published). Under the FI5/FI6 quarter-end protocol the next quarter was
called "Lead 2" (issued at the end of c-1).
"""

VERSION = "fi7-1.0"
