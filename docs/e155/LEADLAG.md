# Does news show a shock before official data?

Rule fixed before looking: a series "shows" a shock on the first date in the event window where it exceeds its previous-24-month mean by 2 standard deviations. News is dated by publication (30-day rolling share). Official data are dated by an **assumed** release: CPI on the 5th of the next month, quarterly farm output 45 days after the quarter, the April 2020 LFS round in early June 2020. Past release dates are not held, so these are approximations. Code: `backend/app/e155/leadlag.py`; result: `backend/data/e155/out/leadlag.json`. CPI read only to 2025-06.

| Shock | First news signal | First official signal | Which came first |
|---|---|---|---|
| 2018 rice price surge | Archive 2018-05-01 (already high at the window start); SunStar 2018-09-05; GDELT 2018-09-21 | CPI rice, 2018-05-05 release | **Official, or a tie.** SunStar and GDELT about 4 months later |
| 2023 rice price surge | SunStar 2023-09-04; archive 2023-09-27; GDELT none | CPI rice, 2023-09-05 release | **Tie** (SunStar one day earlier) |
| 2020 COVID job losses | GDELT 2020-03-16; archive 2020-03-25; SunStar 2020-03-31 | LFS April round, about 2020-06-05 | **News, by about 2 to 2.5 months** |
| 2021 Typhoon Odette | SunStar 2021-12-21; archive and GDELT 2021-12-31 | Quarterly farm output, about 2022-02-14 or later | **News, by about 6 to 8 weeks** |
| 2024 Typhoon Kristine | None of the three | Quarterly farm output, about 2025-02-14 or later | **News missed it** |

## What this shows

* **For prices, news did not lead.** Monthly CPI showed the rice surges as early as news did, or earlier.
* **For jobs and typhoon damage, news led by weeks to months,** because the official series are quarterly.
* **News can miss a shock,** as with Kristine, where coverage in these sources was too thin.

## Limits

Five events. Release dates are assumed. Faster official channels exist that are not counted here, such as DA damage bulletins within days of a typhoon and NDRRMC reports. None of this measures forecast accuracy.

## What can be claimed

> "News indicators preceded official quarterly labor and farm-output data by weeks to months for the 2020 COVID job losses and Typhoon Odette, but did not precede monthly CPI for the 2018 and 2023 rice price surges, and missed Typhoon Kristine. News is earliest where official data are infrequent."
