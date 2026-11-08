# FI9 API (read-only)

Prefix `/api/v1/fi9`. Source: `backend/app/api/v1/fi9.py`. These routes only read files written offline. Nothing
is trained on a request. A missing file returns 503.

| Method and path | Returns | Errors |
|---|---|---|
| `GET /fi9/outlook` | The current Lead-1 outlook: current/issue/target quarter, horizon, issue date, class, probability (if calibrated) and its note, projected hunger and 95 % range, significance line, latest reading and its publication date, latest input publication date, model, version, artifact sha256, training cutoff, validation status and checks, geographic scope, measurement type, explanation, five-domain context, the inputs used | **503 `stale`** when the stored forecast was issued in an earlier quarter (a stale forecast is never shown as current); **503 `unavailable`** when the issue found invalid or missing inputs; both include the re-issue command |
| `GET /fi9/quarters?date=YYYY-MM-DD` | Issue and target quarter for a date (default: the serving clock) | 422 for an invalid date |
| `GET /fi9/evaluation?period=full\|development\|test\|full_without_sawtooth` | All Lead-1 metrics per model, the selection and its checks, the sawtooth quarters, the FI7 reproduction check | 422 for an unknown period |
| `GET /fi9/model` | The served artifact (parameters, formula, training rows and cutoff, sha256) and the locked protocol | |
| `GET /fi9/audit` | The independent audit (18 checks) | |
| `GET /fi9/priority?province=&lgu_psgc=&limit=` | The 142-LGU vulnerability-adjusted priority and province summaries (a priority, not measured or forecast hunger). Weights: provinces 0.65 poverty / 0.35 density (since 2026-11-03, owner-approved, FI9-X validation); LGUs 0.5 / 0.5. Each row has a `weights` column | 404 for an unknown province or LGU code |
| `GET /fi9/priority/alternatives?province=` | Read-only comparison of weighting scenarios (current, moderate, strong, poverty-only, density-only), FNRI 2015 validation, LGU top-third probabilities under SAE uncertainty | 404 for an unknown province |

Serving clock: the `AIPHEED_NOW` environment variable (ISO date) when set, else today's date.

## Example (2026-11-03)

```json
{"status": "provisional", "current_quarter": "2026-Q4", "issue_date": "2026-11-03", "target_quarter": "2027-Q1",
 "horizon": "Lead 1 (next calendar quarter)", "model": "Damped persistence (statistical)",
 "forecast": {"class": "HIGH", "p_high": 0.44, "projected_hunger_pct": 20, "projected_hunger_interval95_pct": [11, 28],
              "significance_line_pct": 20.2, "decision_threshold_tau": 0.12}}
```

The existing dashboard routes (`/api/v1/final/*`, `/forecast`, `/provinces`, …) and the FI5–FI7 routes are unchanged.
