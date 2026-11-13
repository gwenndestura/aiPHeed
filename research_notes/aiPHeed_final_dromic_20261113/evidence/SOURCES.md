# DROMIC and SAP: sources, access, coverage (checked 2026-11-13)

## DSWD DROMIC (Disaster Response Operations Monitoring and Information Center), https://dromic.dswd.gov.ph

| Period | Where the reports are | Format | Access from this machine | Verified |
|---|---|---|---|---|
| 2013 (Typhoon Yolanda/Haiyan) | **Not in DROMIC.** The archive starts with 2014 | — | — | Verified: archive page and folder listing |
| 2014 | "2014–2016 Archives", Google Drive folder `0B8i5maPfj84oaW5DNHFmX0Q0LXc` ("2014 Disaster") | Drive files | Folder lists: TS Glenda, TS Luis, TS Mario, TS Ruby, Volcanic Activities | Verified (listing only; not compiled: no 2014 window is needed for 2015-anchored transitions) |
| 2015 | Archive Drive folders `0B8i5maPfj84oV1g5LW9obXJPY1E`, `0B8i5maPfj84oTmp5dmVES0NLZms` | — | Return no listing (link broken or private) | Verified (unavailable) |
| 2016–2017 | Incident pages under `/category/situation-reports/2016|2017/`, linking Google Docs (dswd.gov.ph / icab.gov.ph domains) | Google Docs; public `export?format=docx` works | Yes | Verified (sample: STS Odette 2017) |
| 2018–2021 | Incident pages, files under `/wp-content/uploads/YYYY/MM/` | .docx (1,254 files), some .pdf (31) | Yes | Verified (sample: Typhoon Quinta terminal report, 16 April 2021) |

**Report content (verified on the Quinta terminal report and the Odette reports)**
- Tables by region → province → municipality:
  - affected barangays, families and persons;
  - displaced families and persons inside evacuation centres (cumulative and current);
  - displaced families and persons outside evacuation centres;
  - damaged houses (total, totally, partially);
  - cost of assistance by source (DSWD, LGU, NGOs, others, grand total).
- Each report carries its own "as of" date in its title and link text.

**Not in the reports at province level:** the date of assistance (only the report date) and assistance type by item (food packs vs cash). These fields from the brief cannot be extracted reliably and are not invented.

**Index:** `DROMIC_index.csv` lists 2016–2021 incidents (crawled at 0.7 s per request).
- Hydro-meteorological family: 2016 19, 2017 34, 2018 20, 2019 41, 2020 41, 2021 68.
- Armed-conflict family: 2016 4, 2017 20, 2018 15, 2019 24, 2020 18, 2021 14.

**Known gaps (uniform; recorded, not imputed)**
- 2015-Q3 to 2015-12 events (e.g. Lando, Nona) are missing for every 2015-anchored window.
- Typhoon Yolanda (2013) is missing, so the requested 2013→2015 test cannot be run with DSWD provincial assistance.

## Yolanda (2013) alternatives searched
- **DSWD totals (secondary, from search summaries; not opened):**
  - relief assistance ₱358.2 M to 696,807 families;
  - Emergency Shelter Assistance ₱18.78 B to 1,015,737 families in Regions IV-B, VI, VII, VIII.
  - These are regional or national totals, not provincial values.
- **NDRRMC situation reports:** ndrrmc.gov.ph refuses automated access (HTTP 403).
- **ReliefWeb API:** v1 is retired; v2 requires an approved application name (registration not done without owner approval).
- **Field-office report:** DSWD FO VI has a municipal ESA/CRRP report for Western Visayas only (one region). Not used.

## SAP 2020 (Social Amelioration Program, Emergency Subsidy)
- **No provincial dataset found.** The only provincial request found is an FOI request (December 2021; not answered publicly). The owner forbids sending data requests.
- **2nd-tranche coverage**, reported in secondary press summaries (Inquirer, Manila Bulletin; the Inquirer article returned HTTP 403 to direct reading):
  - NCR;
  - Region III except Aurora;
  - CALABARZON;
  - Benguet, Pangasinan, Iloilo, Cebu Province, Albay;
  - the cities of Bacolod, Davao and Zamboanga.
- **Status: UNVERIFIED.** The list is not used as an input.
- **Cannot be learned retrospectively:** SAP has no historical counterpart (2013–2019 transitions have no SAP), so it cannot be learned or confirmed on non-2021 transitions.
