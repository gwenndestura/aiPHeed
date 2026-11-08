# E110 source log (read 2026-10-25; facts written as found)

All URLs are recorded per round in `data/sws_area_rounds.csv` (`source`, `source_type`).

## SWS releases on the current site (sws.org.ph, accessed 2026-10-25)

**Hunger in March 2023 → September 2026.**
- **Values:** area values (Metro Manila, Balance Luzon, Visayas, Mindanao, national) for every non-commissioned round.
- **Releases read directly:**
  - June 2023, Sept 2023, Dec 2023;
  - Mar 2024, Jun 2024, Sep 2024, Dec 2024 (`?p=982`);
  - Apr 2025, Jun 2025, Sep 2025, Nov 2025;
  - Mar 2026, Jun 2026, Sep 2026.
- **Release index:** https://sws.org.ph/?s=hunger (pages 1–5).
- **Retired pages:** the old `swsmain/artcldisppage` pages for 2021–2022 return HTTP 404. Their values come from search-result text of those pages and from news reports of the releases (Inquirer, ABS-CBN, Rappler, GMA, PNA).

**Sample design, as stated in the releases:**
- national 1,200 (300 per area) or 1,500 (Balance Luzon 600);
- December 2024: 2,160 (Balance Luzon 1,080);
- area margins ±5.7–6% at n = 300, ±4% at n = 600, ±3% at n = 1,080.
- **Pattern in 2025–2026:** March, April and September rounds are 1,500 surveys (Balance Luzon 600); June and November rounds are 1,200 surveys (Balance Luzon 300).

**Excluded or extra rounds:**
- **Stratbase-SWS, March 2025:** commissioned, 1,800 registered voters.
- **April 11–15, 2025:** registered voters; Balance Luzon 20.5, Metro Manila 26.0, Visayas 14.3, Mindanao 17.3. Commission status unclear: SWS separately "confirms April 2025 Survey items for Stratbase Consultancy". Not in the project file; used in sensitivity S-VOTERS only.

**Inferred values (four 2021 cells, flagged):**
- **June 2021 Metro Manila 14.0:** taken from the September 2021 release text "stayed at 14.0%".
- **June 2021 Visayas 8.3 and Mindanao 15.0:** taken from "fell by … from" statements in the September 2021 release, via news reports.
- **September 2022 national:** not found (left blank; not used).

## Peer-reviewed reference

Mangahas, M. and Torres, C. B. (2024). "The SWS Surveys of Philippine Hunger, 1998–2024." *Asian Journal of Agriculture and Development* 21(2): 85–92. https://doi.org/10.37801/ajad2024.21.2.6
- Journal page: https://ajad.searca.org/article?p=5053
- **The abstract states:**
  - quarterly face-to-face interviews, hunger since 1998;
  - hunger is "most prevalent in Mindanao and among self-identified poor and food-poor households";
  - a sharp resurgence from late 2023.
- **Thresholds:** the abstract defines no high/low threshold.
- **Full text:** not read (PDF only; no PDF text extraction is available here).
- **Window:** no pre-2021 values were used.
