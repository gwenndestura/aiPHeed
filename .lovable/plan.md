## Scope
Layout/UI refactor only — map untouched. Five fixes:

### 1. Left sidebar → 3 floating frosted cards
Replace the solid `<aside>` panel in `Index.tsx` with an absolute-positioned column of 3 separate frosted-glass cards (no panel background — gaps show map):
- **Card 1 — RFII Score**: donut + "CALABARZON — Regional Average RFII" label, subtext "Average across all 5 provinces" (remove "469K households at risk" everywhere), quarter pill, and 3 stat boxes (HIGH/MODERATE/LIMITED).
- **Card 2 — Risk Drivers**: 4 ranked feature bars; OFW Remittance tagged "PROTECTIVE" green when SHAP < 0. No sparklines.
- **Card 3 — Province Ranking**: 5 rows with dot + label + score + horizontal bar. Remove sparklines next to province names.

When a province/municipality is selected, the left column shows the existing `RegionDetail`/`MunicipalityDetail` wrapped in one frosted card.

### 2. Right sidebar → 3 floating frosted cards
- **Card 1 — SHAP Narrative**: ⓘ glossary, badges, baseline φ₀ paragraph, push-up + pull-down lists, italic disclaimer. NO donut, NO score.
- **Card 2 — Predicted RFII + Waterfall**: dynamic `[Province Name] — Predicted RFII · [Quarter]` header, big score, donut, caption, feature waterfall.
- **Card 3 — News**: "NEWS ARTICLES ANALYZED" with count + chevron expand.

Remove duplicated province ranking from right side.

### 3. Label two RFII numbers distinctly
Left donut: "CALABARZON — Regional Average RFII" / "Average across all 5 provinces". Right donut: "[Province Name] — Predicted RFII" / "[Quarter] · Province forecast".

### 4. Time slider center + unlock
- Reposition: `position: absolute; left: 360px; right: 360px; bottom: 48px` (wider than 320 to clear 340-px card columns; user-specified 320 only works with sidebar bg removed — gives same effect with margins).
- Quarters: Q3 2025, Q4 2025, Q1 2026, Q2 2026 (current), Q3 2026 (forecast), Q4 2026 (forecast). All clickable, no `locked` flag.
- Restore `MapLegend` pill bottom-left (already present — verify position).

### 5. Visualization tab — full rewrite
Delete age/malnutrition/forecast-year. Two sub-tabs:
- **A. Province RFII Trend**: province dropdown (5 + All), From/To quarter dropdowns (Q1 2025–Q2 2026), Generate/Clear, Download PNG/PDF, line chart 0.00–1.00 with dashed lines at 0.50 (High Risk) and 0.60 (Alert), data labels, empty state.
- **B. Feature Contribution Breakdown**: province + quarter single-select, horizontal bar chart of 6 features, red = positive SHAP, green = negative, baseline marker, empty state.

### Data changes
Extend `QUARTER_IDS` and `scoresByQuarter` in `quarterData.ts` to include `2025-Q1`, `2025-Q2`. Keep existing thresholds.

### Files to edit
- `src/pages/Index.tsx` — new floating columns layout
- `src/components/LeftPanel.tsx` — split overview into 3 card components, remove HH-at-risk hero text + sparklines from rankings
- `src/components/RightAnalyticsPanel.tsx` — split into 3 cards
- `src/components/QuarterTimeSlider.tsx` — new range, all unlocked
- `src/data/quarterData.ts` — extend quarter dictionary
- `src/pages/Visualization.tsx` — full rewrite with two sub-tabs

### Out of scope
PhilippineMap, mockData, types, navbar, glossary panel — all untouched.