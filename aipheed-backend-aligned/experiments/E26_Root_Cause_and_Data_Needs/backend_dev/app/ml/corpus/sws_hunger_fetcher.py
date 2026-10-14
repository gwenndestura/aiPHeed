"""
app/ml/corpus/sws_hunger_fetcher.py
------------------------------------
Social Weather Stations (SWS) Hunger Survey — quarterly self-reported
involuntary hunger fetcher.

PURPOSE
-------
The SWS Hunger Survey is the **canonical Philippine quarterly food
insecurity indicator** — administered every quarter since 1998. It asks:
"In the last 3 months, did your family experience involuntary hunger
(nagutom) because there was nothing to eat?"

Reported as % of families experiencing:
    • Total hunger (overall)
    • Moderate hunger (sometimes / a few times)
    • Severe hunger (often / always)

WHY ESSENTIAL FOR aiPHeed
--------------------------
1. **Quarterly cadence** — bridges the 2-year gap between NNS 2021 and NNS
   2023 (the DOST-FNRI cycles). Provides 24 quarterly observations
   2020Q1–2025Q4 vs only 2 NNS data points.
2. **Region-level granularity** — Balance of Luzon (where CALABARZON sits)
   reported separately from NCR / Visayas / Mindanao.
3. **Methodologically independent** of FIES — provides cross-validation
   anchor for the model's quarterly forecasts.
4. **Used by FAO, World Bank, ADB Philippines country reports** as the
   official high-frequency hunger indicator. Citing SWS is panel-defensible.

PRECEDENT REFERENCES
--------------------
- World Bank (2024) Philippines Poverty Assessment — uses SWS Hunger
- FAO (2023) Country Profile Philippines — cites SWS quarterly hunger
- Asian Development Bank (2022) PH Country Strategy — SWS Hunger as core KPI
- WFP HungerMap LIVE methodology — equivalent to SWS-style self-report

DATA STRATEGY
-------------
SWS releases each quarter's results via press release on sws.org.ph.
Page contents are static HTML — scrapeable but format varies. This
fetcher uses curated values from public SWS press releases (2020Q1–2025Q4)
with each quarter's source URL recorded per row.

OUTPUT
------
data/processed/sws_hunger.parquet — columns:
    region_code              : str (Balance of Luzon → applied to CALABARZON)
    region_name              : str
    province_code            : str (PSGC, region inherited)
    province_name            : str
    year                     : int
    quarter                  : str ("YYYY-QN")
    survey_quarter_label     : str (e.g. "2020 Q3 SWS Hunger Survey")
    pct_total_hunger         : float (% of families)
    pct_moderate_hunger      : float
    pct_severe_hunger        : float
    source_url               : str
    source_note              : str
    fetched_at               : str

TRAINING WINDOW: 2020Q1–2025Q4 strict.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.ml.corpus._coverage import CuratedCoverageError, check_coverage  # noqa: F401

logger = logging.getLogger(__name__)

OUTPUT_PATH = Path("data/processed/sws_hunger.parquet")

# Region IV-A is reported under "Balance of Luzon" (rest of Luzon outside NCR)
REGION_CODE = "PH040000000"
REGION_NAME = "Region IV-A (CALABARZON) [SWS Balance of Luzon]"

PROVINCES = [
    ("PH040100000", "Cavite"),
    ("PH040200000", "Laguna"),
    ("PH040300000", "Quezon"),
    ("PH040400000", "Rizal"),
    ("PH040500000", "Batangas"),
]

# ---------------------------------------------------------------------------
# Curated SWS Hunger Survey quarterly results — Balance of Luzon
# Source: SWS press releases at sws.org.ph (one per quarter).
# These are PUBLIC PRIMARY DATA released by SWS each quarter.
# Values reflect involuntary hunger experienced by families in past 3 months.
#
# Citation pattern: SWS Survey conducted [date]; press release URL recorded
# in source_url. Original surveys publicly archived under sws.org.ph/swsmain/.
# ---------------------------------------------------------------------------
# ===========================================================================
# REBUILT 2026-09-01, EXTENDED 2026-09-23.
#
# 2026-09-01: every value then in this table was removed as unverifiable. Seven
# quarters had been checked against SWS press releases and none agreed --
# 2024-Q4 was recorded at 10.3% against a published Balance Luzon figure of
# 25.3%, 2025-Q4 at 9.5% against an actual 16.7% -- and the 2025 block was
# annotated "projected continuation of moderating trend" while being written
# out with survey labels. Those values are not reinstated.
#
# 2026-09-23: the archive was recovered. SWS migrated to a WordPress site whose
# Hunger category holds only four releases, but the previous site
# (www.sws.org.ph/swsmain/artcldisppage/) is archived in the Wayback Machine,
# including its article index (generalArtclSrchPage, swityp=3 = Hunger). Every
# hunger release from 2019-Q3 to 2025-Q1 was retrieved and its Balance Luzon
# figures read from the release text.
#
# Each value below is stated outright in the release cited beside it. Nothing
# is interpolated, projected, averaged across releases or carried forward.
# Three independent checks were run on the result:
#
#   1. The two quarters that were already hand-verified (2024-Q3 and 2024-Q4)
#      were re-derived from the archive and matched exactly, including their
#      Moderate and Severe components.
#   2. Moderate + Severe reproduces Total to within rounding for all 23
#      quarters that publish both -- zero mismatches.
#   3. Consecutive releases agree on the overlapping quarter wherever one
#      release restates the previous quarter's figure.
#
# QUARTER ASSIGNMENT. A round is filed under the calendar quarter it was
# FIELDED in, which is the convention already used here and the one Rule 3 (No
# Look-Ahead Bias) requires: SWS's own label sometimes lags the fieldwork, and
# filing the April 2021 round as "2021-Q1" would let a label be set by data
# collected after the quarter closed. Where COVID scheduling put two rounds in
# one calendar quarter (2020-Q3, 2021-Q2, 2022-Q2) both are emitted; the
# quarter's value is their mean, which label_generator already computes with
# its existing groupby.
#
# ABSENT QUARTERS -- 2020-Q1, 2021-Q1, 2022-Q1, 2025-Q2 and 2025-Q3 have no
# SWS hunger round fielded within them. 2020-Q1 predates the pandemic mobile
# surveys; the rounds SWS labels First Quarter 2021 and First Quarter 2022 were
# fielded in late April of their years; and the published series runs March 2025
# straight to November 2025. These quarters stay absent, never estimated.
#
# Stratum: Balance Luzon (Luzon outside NCR) -- the stratum containing
# CALABARZON. National figures are recorded separately for cross-checking only.
#
# Format: (year, "Q#", total%, moderate%, severe%, survey_label, source_url)
# severe% is None where the release publishes no Balance Luzon severe figure.
# ===========================================================================
SWS_BAL_LUZON_VERIFIED = [
    # -- recovered from the Wayback-archived SWS article pages (2026-09-23) --
    (2020, "Q2", 12.6, 10.9, 1.7,
     "SWS May 4-10, 2020 Covid-19 Mobile Phone Survey (Report No. 2)",
     "https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20200521200121"),
    (2020, "Q3", 17.8, 13.6, 4.3,
     "SWS July 3-6, 2020 National Mobile Phone Survey (Report No. 5)",
     "https://web.archive.org/web/20250310125253id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20200721164746&amp;fbclid=IwAR1DIEoRlnbl8pnTRdmyslYO-IUxm7L8TzRp3TefTEgk_DoqKGS978pThxk"),
    (2020, "Q3", 23.8, 18.6, 5.2,
     "SWS September 17-20, 2020 National Mobile Phone Survey (Report No. 2)",
     "https://web.archive.org/web/20251207030124id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20200927135430&fbclid=IwAR0Ig2vMqfiRONVqHfqwxh8pfaoYDFsoF"),
    (2020, "Q4", 14.4, 11.6, 2.8,
     "Fourth Quarter 2020 SWS Survey, November 21-25, 2020",
     "https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20201216145500"),
    (2021, "Q2", 15.7, 12.3, 3.3,
     "First Quarter 2021 SWS Survey, April 28-May 2, 2021",
     "https://web.archive.org/web/20210728114049id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20210712133604"),
    (2021, "Q2", 15.0, 13.0, 2.0,
     "Second Quarter 2021 SWS Survey, June 23-26, 2021",
     "https://web.archive.org/web/20210728102749id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20210728100035"),
    (2021, "Q3", 10.3, 8.0, 2.3,
     "Third Quarter 2021 SWS Survey, September 12-16, 2021",
     "https://web.archive.org/web/20211206184548id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20211206105401&fbclid=IwAR3uFb7lHfll_A4nlDPHNtCX86VUgzBEN9mSwZ097gg3ztYe_b49pEX5vaQ"),
    (2021, "Q4", 9.2, 6.4, 2.8,
     "Fourth Quarter 2021 SWS Survey, December 12-16, 2021",
     "https://web.archive.org/web/20220325073539id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20220325064813"),
    (2022, "Q2", 11.7, 8.3, None,
     "First Quarter 2022 SWS Survey, April 19-27, 2022",
     "https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20220606102327"),
    (2022, "Q2", 11.9, 9.4, 2.5,
     "Second Quarter 2022 SWS Survey, June 26-29, 2022",
     "https://web.archive.org/web/2022id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20220910153623"),
    (2022, "Q3", 9.6, 8.1, 1.5,
     "Third Quarter 2022 SWS Survey, September 29-October 2, 2022",
     "https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20221029123738"),
    (2022, "Q4", 11.3, 9.3, 2.0,
     "Fourth Quarter 2022 SWS Survey, December 10-14, 2022",
     "https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20230119062833"),
    (2023, "Q1", 8.7, 7.7, 1.0,
     "First Quarter 2023 SWS Survey, March 26-29, 2023",
     "https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20230511073700"),
    (2023, "Q2", 11.3, 8.3, 3.0,
     "Second Quarter 2023 SWS Survey, June 28-July 1, 2023",
     "https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20230802100329"),
    (2023, "Q3", 10.3, 9.0, 1.3,
     "Third Quarter 2023 SWS Survey, September 28-October 1, 2023",
     "https://web.archive.org/web/20241119024013id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20231120143838"),
    (2023, "Q4", 14.3, 13.3, 1.0,
     "Fourth Quarter 2023 SWS Survey, December 8-11, 2023",
     "https://web.archive.org/web/20240612144748id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20240122100715"),
    (2024, "Q1", 15.3, 13.1, 2.1,
     "First Quarter 2024 SWS Survey, March 21-25, 2024",
     "https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20240430105705"),
    (2024, "Q2", 19.6, 14.5, 5.1,
     "Second Quarter 2024 SWS Survey, June 23-July 1, 2024",
     "https://web.archive.org/web/20240726183316id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20240723055730"),
    # -- read from the live sws.org.ph releases --
    (2024, "Q3", 18.1, 13.0, 5.1, "September 2024 SWS Survey",
     "https://sws.org.ph/social-weather-report-fourth-quarter-2024-social-weather-survey-"
     "hunger-rises-to-25-9-in-december-2024-from-22-9-in-september-2024/"),
    (2024, "Q4", 25.3, 16.6, 8.7, "December 2024 SWS Survey",
     "https://sws.org.ph/social-weather-report-fourth-quarter-2024-social-weather-survey-"
     "hunger-rises-to-25-9-in-december-2024-from-22-9-in-september-2024/"),
    (2025, "Q1", 24.0, 16.5, 7.4, "Stratbase-SWS March 15-20, 2025 National Survey",
     "https://sws.org.ph/social-weather-report-stratbase-sws-march-15-20-2025-national-"
     "survey-hunger-rises-to-27-2-in-march-2025/"),
    (2025, "Q4", 16.7, 12.7, 4.0, "November 2025 SWS Survey",
     "https://sws.org.ph/social-weather-report-hunger-rises-from-20-1-in-november-2025-"
     "to-23-2-in-march-2026/"),
    (2026, "Q1", 22.4, 16.6, 5.8, "March 2026 SWS Survey",
     "https://sws.org.ph/social-weather-report-hunger-rises-from-20-1-in-november-2025-"
     "to-23-2-in-march-2026/"),
    (2026, "Q2", 17.3, 13.0, 4.3, "June 2026 SWS Survey",
     "https://sws.org.ph/social-weather-report-hunger-falls-to-20-3-in-june-2026-"
     "from-23-2-in-march-2026/"),
]

# National totals from the same releases, for sanity checks only. Balance Luzon
# and National are DIFFERENT series and must never be mixed -- conflating them is
# a likely origin of the table discarded in September.
SWS_NATIONAL_REFERENCE = {
    (2024, "Q3"): 22.9, (2024, "Q4"): 25.9, (2025, "Q1"): 27.2,
    (2025, "Q4"): 20.1, (2026, "Q1"): 23.2, (2026, "Q2"): 20.3,
}


SOURCE_BASE = "https://www.sws.org.ph/swsmain/artcldisppage/"
SOURCE_NOTE = ("SWS quarterly Hunger Survey, Balance of Luzon stratum. "
               "Self-reported involuntary hunger (nagutom) past 3 months. "
               "Cited by World Bank PH Poverty Assessment, FAO PH Country Profile, "
               "ADB PH Country Strategy as canonical quarterly hunger indicator.")


SWS_COVERAGE_END = (2026, 2)


def fetch_sws_hunger(start_year: int = 2020,
                     end_year: int | None = 2025,
                     strict: bool = True) -> pd.DataFrame:
    """
    Build the CALABARZON SWS Hunger panel from VERIFIED quarters only.

    The Balance Luzon value is inherited to all five provinces: SWS publishes no
    province cut, so these rows are not independent province observations.
    Quarters with no published release are absent from the output entirely — they
    are never interpolated, projected, or carried forward.
    """
    # Defaults are the approved training window, 2020-Q1 through 2025-Q4
    # (Section 3.3.2.6). Widen them only to look outside that window.
    end_year = end_year or datetime.now(timezone.utc).year
    check_coverage(
        series="SWS hunger (Balance Luzon)",
        coverage_end=SWS_COVERAGE_END, end_year=end_year,
        reason="SWS publishes each round as a press release whose HTML layout "
               "varies between releases, so it is not safely scrapeable.",
        source_url="the release at sws.org.ph (SWS_BAL_LUZON_VERIFIED)",
        extend_hint="raise SWS_COVERAGE_END",
        strict=strict, logger=logger)

    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for year, q, total, mod, sev, label, url in SWS_BAL_LUZON_VERIFIED:
        if not (start_year <= year <= end_year):
            continue
        for prov_code, prov_name in PROVINCES:
            rows.append({
                "region_code": REGION_CODE,
                "region_name": REGION_NAME,
                "province_code": prov_code,
                "province_name": prov_name,
                "year": year,
                "quarter": f"{year}-{q}",
                "survey_quarter_label": label,
                "pct_total_hunger": float(total),
                "pct_moderate_hunger": float(mod) if mod is not None else None,
                # None where the release publishes no Balance Luzon severe
                # figure. Left as null rather than derived from total - moderate:
                # the label uses pct_total_hunger only, so a gap here costs
                # nothing and an inferred value would not be a published one.
                "pct_severe_hunger": float(sev) if sev is not None else None,
                "stratum": "balance_luzon",
                "geographic_level": "stratum_inherited",
                "verified": True,
                "source_url": url,
                "source_note": SOURCE_NOTE,
                "fetched_at": fetched_at,
            })

    df = pd.DataFrame(rows)

    expected = {f"{y}-Q{i}" for y in range(start_year, end_year + 1) for i in range(1, 5)}
    have = set(df["quarter"]) if len(df) else set()
    missing = sorted(expected - have)
    logger.info(
        "SWS Hunger: %d rows | %d of %d quarters verified in %d-%d",
        len(df), len(have), len(expected), start_year, end_year,
    )
    if missing:
        logger.warning(
            "%d quarters have NO published SWS release and are absent (not estimated): %s",
            len(missing), ", ".join(missing),
        )
        logger.warning(
            "SWS migrated their site; the pre-Dec-2024 archive is unpublished. "
            "Request the 2010-2025 Balance Luzon series from sws_info@sws.org.ph."
        )
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df = fetch_sws_hunger(2020, 2025)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"[ok] wrote {OUTPUT_PATH} — {len(df)} rows")
    print(df.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
