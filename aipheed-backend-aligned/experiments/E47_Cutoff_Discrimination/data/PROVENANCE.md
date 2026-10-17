# E47 data provenance

## Brent crude oil spot price (FRED DCOILBRENTEU)

| Field | Value |
|---|---|
| Series | Brent - Europe crude oil spot price, USD per barrel, daily |
| Primary source | U.S. Energy Information Administration (EIA), via FRED (Federal Reserve Bank of St. Louis) |
| URL | https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU&cosd=2021-01-01&coed=2026-09-30 |
| Retrieved | 2026-10-17T03:12:16Z (UTC) |
| Coverage | 2021-01-04 .. 2026-09-30 (study window; no pre-2021 value requested) |
| Rows | 1498 trading days; 46 rows without a value (market holidays), dropped |
| File | data/brent_daily_fred_raw.csv, unmodified |
| SHA-256 | ee3adafb23d9beb6cea213a983cff1999f7f8ff2e002ab322276bce9b77389a0 |
| Geography | world market price (identical for all provinces) - an exogenous price driver, labelled national/global |
| Publication | EIA publishes daily spot prices weekly with a lag of a few days; E47 uses only the 30 days ending 10 days before each issue date |
| Transformations | 30-day mean; % change vs the same window 1 year earlier (brent_yoy) and 3 months earlier (brent_mom3) |
