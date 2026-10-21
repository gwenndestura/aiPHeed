# E84 Priority 1 and 3: outcome and information sources examined (2026-10-21)

| Source | What it is | Usable as outcome / input? | Why |
|---|---|---|---|
| SWS involuntary hunger, Balance Luzon (quarterly) | Direct household hunger observation, regional | Outcome (direct, regional only) | Already used. About 22 rounds in 2021–26. No provincial figure. |
| OCTA Tugon ng Masa hunger | Direct observation, Balance Luzon | Independent check only | 9 rounds (E73). Too few, and regional. |
| FNRI ENNS/NNS FIES | Experience-based food insecurity | Face-validity reference | Regional in 2025 (secondary reporting); provincial estimates not published. 2019 is outside the window. |
| PSA FIES (Family Income and Expenditure Survey) 2021/2023 | Income-based food/poverty thresholds, provincial, triennial | Context, not outcome | Income poverty, not experienced food insecurity; 2 points in the window. |
| PSA SAE municipal poverty 2021 | Small-area income poverty | Vulnerability input (LGU ranking) | Static; CV > 20% for 25 LGUs. |
| CBMS 2024 (PSA RSSO IV-A) | Municipal household module | **Best candidate for a local outcome** | Not public. Needs a data request to PSA RSSO IV-A. |
| WFP HungerMap LIVE (Philippines) | Insufficient food consumption | **Not an observation** | The Philippines is marked "PREDICTED": a model output. Using it as ground truth would be circular. |
| PSA provincial CPI subgroups, monthly (OpenStat 0012M4ACP22) | Rice, corn, meat, fish, oils, fruits, vegetables, sugar | **Added in E84** (affordability) | Same publication lag as food CPI. |
| IMF PCPS world prices via FRED (rice, maize, wheat, palm oil, sugar, food index) | World staple prices | **Added in E84** (leading affordability) | 2021+ rows requested only. Published with about a 2.5–3 month lag, so used with a 4-month rule. |
| NDRRMC situation reports | Dated agricultural damage by region | Not reachable | Cloudflare challenge on ndrrmc.gov.ph; never bypassed. |
| ReliefWeb API (OCHA) | Full-text situation reports, disaster records | Not reachable without registration | The API host's robots.txt disallows all paths; it requires a pre-approved appname. A registration request is needed from the researcher. |
| GDELT GKG (themes, locations, tone from full text) | Structured event signals from full articles | Not feasible without cost approval | Raw 15-minute files for 2021–26 are about 1 TB. BigQuery scans would bill the researcher's GCP project. Needs explicit approval. |
| Publisher article bodies (Inquirer, GMA, MB, Philstar, PNA, ABS-CBN, Rappler) | Full text | Not reachable lawfully | Bot challenges, robots disallow, or no permitted route (E83 LEAD_TEXT_REPORT). Needs licensed access. |

**Conclusion.** No legitimate provincial or higher-frequency food-insecurity outcome exists for 2021–2026 in public
sources. The approved T43 and the regional SWS series remain the only outcomes. A real local outcome needs CBMS 2024.
