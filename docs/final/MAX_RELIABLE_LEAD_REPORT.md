# Maximum reliable lead report

**Rule (E156, unchanged):** a lead is reliable only if it and every shorter lead pass C1–C6.
- **Tool:** `backend/app/e156/max_lead_all.py`, output `data/e156/out/max_lead_all.json`.
- **E166 longer leads:** `backend/app/e166/longer_leads.py`.
- **The dashboard must read this file, never a hardcoded lead.**

| Model | Leads evaluated | Accuracy by lead | First failing lead | Criteria failed at Lead 1 | **Max reliable lead** |
|---|---|---|---|---|---|
| E158 | 1–8 | 73.6, 73.6, 75.0, 75.0, 72.2, 68.1, 48.0, 56.0 | 1 | C1, C4 | **0** |
| E164 AUTO (withdrawn) | 1–4 | 79.2, 79.2, 76.4, 76.4 | 1 | C4 | **0** |
| E165 AUTO-FINAL | 1–2 | 73.6, 76.4 | 1 | C1, C4 | **0** |
| E166 | 1–8 | 76.4, 79.2, 76.4, 76.4, 73.6, 72.2, 68.0, 68.0 | 1 | C1, C4 | **0** |
| E167 | 1–2 | 66.7, 68.1 | 1 | C1, C4, C5 | **0** |

**Skill horizon** (consecutive leads significantly better than persistence, C2), reported separately:
- **E166: 6 quarters.**
- **E158: 5 quarters.**

Leads 7–8 have 50 rows.

**Statement for the dashboard and thesis:**
> "Forecasts are issued for one to four quarters ahead; no lead has met the predefined reliability criteria, so no reliable forecast horizon is claimed."
