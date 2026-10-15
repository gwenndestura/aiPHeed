"""E34 fix, applied identically to E31 backend_dev and the promoted backend/:

D1  /quarters dropped quarters the E31 record has no row for (2025-Q2/Q3; 2026-Q4 in the forecast view) without saying
    so, so the slider jumped 2025-Q1 -> 2025-Q4. The main backend (1658d31) listed such quarters as "unavailable" with a
    reason, and the promoted frontend renders exactly that. Restored: the Quarter schema regains `reason`, and the E31
    timeline lists every quarter in its range, with a data-derived reason for each gap. A forecast view still never shows
    a nowcast value: 2026-Q4 is listed there as unavailable, pointing to the nowcast view.
D2  /forecast and /forecast/timeseries hard-coded isForecast=False ("nothing is ever a forecast quarter"), which is false
    for the E31 record: 2026-Q4 (nowcast) and 2027-Q1 (forecast) have no outcome yet. isForecast now follows the row's
    mode, consistent with /config quarterRange.forecastQuarters.
usage: PY -B runner/e34_patch_timeline.py <backend_dir> [<backend_dir> ...]
"""
from __future__ import annotations

import sys
from pathlib import Path


def sub(p: Path, old: str, new: str, count: int = 1):
    s = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    if new in s:
        return "already"
    assert s.count(old) == count, (p, old[:60], s.count(old))
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
    return "patched"


SCHEMA_OLD = '''    state: str  # "actual" | "current"
'''
SCHEMA_NEW = '''    state: str  # "actual" | "current" | "forecast" | "unavailable"
    # Why an "unavailable" quarter has no score; None on every other state (main backend 1658d31, restored in E34).
    reason: str | None = None
'''

TL_OLD = '''            "state": state,
        })
    return out
'''
TL_NEW = '''            "state": state,
        })
    if e31_active() and out:
        out = _e31_fill_gaps(out, horizon)
    return out


def _e31_unavailable_reason(quarter: str, horizon: str) -> str:
    """Why the E31 record has no row for this quarter in this view (E34, D1). Derived from the data, never assumed."""
    other = NOWCAST if horizon == FORECAST else FORECAST
    if quarter in available_quarters(other):
        return (f"{quarter} is the quarter under way; its estimate is a same-quarter nowcast, shown in the nowcast "
                "view. A forecast view never shows a nowcast.")
    p = Path("data/inputs/sws_rounds.csv")
    if p.exists():
        r = pd.read_csv(p)
        r = r[r["quarter"] == quarter]
        if len(r) and not r["definition_A"].astype(str).str.lower().eq("true").any():
            return (f"No estimate for {quarter}: its SWS hunger rounds are recorded as supplementary, not as the "
                    "approved (definition A) series, so the quarter has no approved label to estimate or score. "
                    "This is missing data, not a low score.")
        if not len(r):
            return (f"No estimate for {quarter}: no SWS hunger round is recorded for it. This is missing data, not a "
                    "low score.")
    return f"The E31 record holds no estimate for {quarter}. This is missing data, not a low score."


def _e31_fill_gaps(rows: list[dict], horizon: str) -> list[dict]:
    """List every quarter between the first and last served one; gaps become "unavailable" with a reason (E34, D1)."""
    have = {r["id"]: r for r in rows}
    idx = [ref.quarter_index(r["id"]) for r in rows]
    out = []
    for i in range(min(idx), max(idx) + 1):
        q = f"{i // 4}-Q{i % 4 + 1}"
        if q in have:
            out.append(have[q])
            continue
        year, qn = ref.quarter_parts(q)
        out.append({"id": q, "year": year, "q": qn, "label": f"Q{qn}", "monthsLabel": ref.QUARTER_MONTHS[qn],
                    "state": "unavailable", "reason": _e31_unavailable_reason(q, horizon)})
    return out


def is_estimate_quarter(quarter: str) -> bool:
    """E31: True for the quarters whose outcome is not yet known (the 2026-Q4 nowcast, the 2027-Q1 forecast); False for
    backtests and the scored 2026-Q3. Same rule as /config quarterRange.forecastQuarters (E34, D2)."""
    if not e31_active():
        return False
    row = E31.quarter_row(quarter, NOWCAST)
    return bool(row) and row["mode"] in ("FORECAST", "NOWCAST")
'''

FC1_OLD = '''        # Nothing is ever a forecast quarter: the model scores quarters whose
        # production volumes PSA has already published.
        isForecast=False,
'''
FC1_NEW = '''        # E34: true for a quarter whose outcome is not yet known (E31 nowcast/forecast); backtests are false.
        isForecast=svc.is_estimate_quarter(q),
'''
FC2_OLD = '''            "isForecast": False,
'''
FC2_NEW = '''            "isForecast": svc.is_estimate_quarter(q),
'''


def main(dirs):
    for d in map(Path, dirs):
        print(d)
        print(" schema", sub(d / "app/schemas/public.py", SCHEMA_OLD, SCHEMA_NEW))
        print(" timeline", sub(d / "app/services/dashboard.py", TL_OLD, TL_NEW))
        print(" forecast", sub(d / "app/api/v1/forecast.py", FC1_OLD, FC1_NEW))
        print(" timeseries", sub(d / "app/api/v1/forecast.py", FC2_OLD, FC2_NEW))


if __name__ == "__main__":
    main(sys.argv[1:])
