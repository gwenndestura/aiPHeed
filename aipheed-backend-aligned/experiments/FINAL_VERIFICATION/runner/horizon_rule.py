"""The horizon decision of FINAL_TARGET_AND_EVALUATION_PROTOCOL section 7 with Addendum 3, as a pure function so it
can be tested without running a model.

- testable horizon: the longest lead meeting R1 (>= 10 target quarters and >= 40 rows)
- maximum reliable lead: the largest K such that Leads 1..K all pass R1-R7 (None if Lead 1 fails)
- individually passing leads: every lead passing R1-R7, reported as a diagnostic only
"""
from __future__ import annotations


def select_horizon(verdicts: dict) -> dict:
    """verdicts: {lead: {"criteria": {"R1": bool, ...}, "reliable": bool}} for leads >= 1 (lead 0 is a nowcast and is
    ignored). Keys may be int or str."""
    v = {int(k): d for k, d in verdicts.items() if int(k) >= 1}
    leads = sorted(v)
    best = None
    for k in leads:
        if k != (best or 0) + 1 or not v[k]["reliable"]:
            break
        best = k
    return {"leads_evaluated": leads,
            "testable_horizon_R1": max([k for k in leads if v[k]["criteria"]["R1"]], default=None),
            "max_reliable_lead": best,
            "individually_passing_leads": [k for k in leads if v[k]["reliable"]]}
