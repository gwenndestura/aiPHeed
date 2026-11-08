# News annotation guide (written before any headline was read)

**Unit.** One headline (title only; article bodies are not available offline), with its date and outlet.

**Reviewer.** Claude, a single AI reviewer, not a human annotator, with **no access to either pipeline's labels** while annotating (blind file `out/news_review_blind.csv`).
- **Pass 1:** in file order.
- **Pass 2:** a fresh reshuffled order (seed 2035) without looking at pass 1.

Agreement between the passes (Cohen's κ) measures consistency. **It is not two-person reliability.** Disagreements are adjudicated by re-reading against this guide; the adjudicated label is the reference.

## Label 1: TYPE (exactly one; the most specific that applies)

| Code | Meaning | Examples | Not this |
|---|---|---|---|
| **DIRECT** | Reports hunger, people going without food, inadequate food intake, malnutrition, or households unable to obtain food (food access failure), including a food shortage experienced by people | "Families go hungry after…", "Malnutrition cases rise…", "Residents line up for scarce rice" | price changes alone |
| **PRICE** | Food or rice price movement, inflation, price caps or tariffs, with no direct statement that people cannot obtain food | – | – |
| **SUPPLY** | Agricultural or fisheries production, crop or fish damage, El Niño/drought or pest effects on food production, food imports and stocks | – | – |
| **DISASTER** | Typhoon, flood, earthquake, eruption, damage or evacuation, with no explicit food-supply or food-access content | – | – |
| **LIVELIHOOD** | Jobs, income, poverty, remittances, wages, layoffs | – | – |
| **ASSIST** | Food aid or relief distribution, feeding programmes, subsidies or vouchers delivering food | – | – |
| **OTHER** | Unrelated to food security | – | – |

## Label 2: RELEVANT (Y/N)

**Y** if TYPE ∈ {DIRECT, PRICE, SUPPLY, LIVELIHOOD, ASSIST}, or TYPE = DISASTER **with** plausible food-security consequences for Philippine households (e.g., crop or fishing losses, displacement). Pure infrastructure, politics or weather forecasts without impact → **N**.

## Label 3: GEO

| Code | Meaning |
|---|---|
| CALA | names CALABARZON or one of its provinces, cities or municipalities |
| PH | national or unspecified Philippines |
| OTHER_PH | another Philippine region only |
| FOREIGN | outside the Philippines |

## Label 4: EVIDENCE

| Code | Meaning |
|---|---|
| EVENT | an actual occurrence that happened |
| FORECAST | an official forecast or warning of a future threat |
| GENERAL | discussion, opinion, policy talk without a specific event |

## Reference classes used in scoring

| Class | Definition |
|---|---|
| Food-security relevant | RELEVANT = Y |
| Food insecurity (direct) | TYPE = DIRECT |
| Price-only | TYPE = PRICE |
