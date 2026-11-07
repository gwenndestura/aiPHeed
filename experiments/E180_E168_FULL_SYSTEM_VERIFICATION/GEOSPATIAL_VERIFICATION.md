# E180: geospatial reliability

| Check | Status | Evidence |
|---|---|---|
| Province polygons | VERIFIED | `frontend/public/ph-provinces.json`: 81 provinces; 5 CALABARZON polygons; all 5 API province ids resolve |
| Municipality polygons | VERIFIED | `calabarzon-municities.json`: 142 features with province_id |
| API ↔ map join | **VERIFIED** | The frontend joins on a normalised `provinceId::name` key (`PhilippineMap.tsx` muniKey). 142 / 142 API LGUs match, 0 unmatched either way. 20 ids differ literally ("batangas-lipa" vs "batangas-city-of-lipa"), but the name-key join resolves them |
| Province forecasts | VERIFIED | Each province's value is its own E168 forecast from provincial inputs (CPI, climate, production, poverty, density, province news) plus national/area inputs shared across provinces |
| Provincial differentiation | PARTIALLY VERIFIED | Employment, remittance, ONI and national news are national: they shift all provinces together. Provincial differences come from provincial inputs and each province's own survey anchor |
| Municipal values | VERIFIED (method) / qualify (claim) | Algorithm 5 ranking: province P(HIGH) × (0.6 poverty + 0.4 density), min-max within province (PSA 2021 SAE, 2020 census). Not municipal forecasts; one poverty vintage for every quarter |
| Spatial precision | Qualify | Municipal colours show relative vulnerability under the province's risk, not observed municipal food insecurity |
