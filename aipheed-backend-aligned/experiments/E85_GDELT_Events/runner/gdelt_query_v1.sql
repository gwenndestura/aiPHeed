-- E85: GDELT GKG 2.1 records about CALABARZON food-security shocks, 2021-01-01 .. 2026-10-14 (authorized data limit).
-- Partition filter limits the scan to the study window; no pre-2021 partition is read.
SELECT
  DATE,
  SourceCommonName,
  DocumentIdentifier,
  Themes AS V2Themes,
  Locations AS V2Locations,
  V2Tone,
  Counts AS V2Counts
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP('2021-01-01') AND _PARTITIONTIME < TIMESTAMP('2026-10-15')
  AND Locations LIKE '%#RP#%'
  AND REGEXP_CONTAINS(Locations, r'(?i)(Batangas|Cavite|Laguna|Rizal|Quezon Province|Lucena|Calabarzon|Southern Tagalog)')
  AND REGEXP_CONTAINS(Themes, r'(FOOD_SECURITY|FOOD_STAPLE|TAX_FOODSTAPLES|ECON_INFLATION|ECON_PRICE|AGRICULTURE|CROP|FAMINE|HUNGER|MALNUTRITION|POVERTY|UNEMPLOY|NATURAL_DISASTER|DROUGHT|FLOOD|TYPHOON|STORM|EL_NINO|FISH|SHORTAGE|HUMANITARIAN|AID|RELIEF|REMITTANCE)')
