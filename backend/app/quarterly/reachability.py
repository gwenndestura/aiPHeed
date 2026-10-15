"""
app/quarterly/reachability.py  (E29, OBJECTIVE_2_REACHABILITY.md)
-----------------------------------------------------------------
How far each lead is from being evaluable under C6, which new outcomes may count, and how much evidence would be
needed to show skill (a different and larger quantity).

C6 (E23/E25, researcher-declared, adviser approval pending): lead k is evaluable iff >= 8 dates, >= 5 HIGH rows and
>= 5 LOW rows; reliable iff also the date-bootstrap AUC lower bound > 0.5 and Brier beats persistence with a one-sided
sign-flip p < 0.05.

Dependence. Under T1 the five provinces of one date share one regional hunger value, so five LOW rows on one date
are one regional event, not five independent outcomes. C6 as written counts rows; this module reports both the
as-written count and a dependence-aware count (LOW DATES), and never counts a shared regional value as five
independent provincial outcomes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

C6_MIN_DATES, C6_MIN_HIGH, C6_MIN_LOW = 8, 5, 5


@dataclass
class OutcomeCheck:
    eligible: bool
    reason: str


def check_new_outcome(quarter: str, target_id: str, published: pd.Timestamp | None, sealed_at: pd.Timestamp | None,
                      window: tuple[str, str], existing_quarters: set[str], approved_targets=("T1_A",),
                      quarter_end: pd.Timestamp | None = None) -> OutcomeCheck:
    """May a newly published outcome be counted as unseen evidence for a sealed forecast?"""
    from app.quarterly.targets import TARGETS

    if target_id not in TARGETS:
        return OutcomeCheck(False, "UNKNOWN_TARGET")
    if target_id not in approved_targets:
        return OutcomeCheck(False, f"TARGET_NOT_APPROVED ({TARGETS[target_id]['status']})")
    lo, hi = window
    if not (lo <= quarter <= hi):
        return OutcomeCheck(False, "OUTSIDE_AUTHORIZED_WINDOW")
    if quarter in existing_quarters:
        return OutcomeCheck(False, "DUPLICATE_QUARTER (a second round of a quarter is averaged into its one label)")
    if published is None:
        return OutcomeCheck(False, "PUBLICATION_DATE_UNKNOWN")
    if sealed_at is None:
        return OutcomeCheck(False, "NO_SEALED_FORECAST")
    if sealed_at >= published:
        return OutcomeCheck(False, "FORECAST_SEALED_AFTER_OUTCOME_PUBLICATION")
    if quarter_end is not None and sealed_at > quarter_end:
        return OutcomeCheck(False, "FORECAST_SEALED_AFTER_TARGET_QUARTER_ENDED")
    return OutcomeCheck(True, "ELIGIBLE (one regional date; its five province rows are dependent)")


def lead_counts(b1_rows: pd.DataFrame) -> pd.DataFrame:
    """Per lead: dates, rows, HIGH/LOW rows, LOW dates (dates with >= 1 LOW row), LOW rows per LOW date."""
    out = []
    for lead, g in b1_rows.groupby("lead"):
        low_dates = g[g["y"] == 0]["t"].nunique()
        n_low = int((g["y"] == 0).sum())
        out.append({"lead": int(lead), "dates": int(g["t"].nunique()), "rows": int(len(g)),
                    "HIGH_rows": int(g["y"].sum()), "LOW_rows": n_low, "LOW_dates": int(low_dates),
                    "LOW_rows_per_LOW_date": round(n_low / low_dates, 3) if low_dates else None})
    return pd.DataFrame(out)


def c6_gap(row: dict) -> dict:
    """Minimum additional observations for C6 as written (rows) and dependence-aware (dates)."""
    add_dates = max(0, C6_MIN_DATES - row["dates"])
    add_low_rows = max(0, C6_MIN_LOW - row["LOW_rows"])
    add_high_rows = max(0, C6_MIN_HIGH - row["HIGH_rows"])
    # dependence-aware: 5 LOW outcomes on DIFFERENT dates (regional events), not 5 province rows of one event
    add_low_dates = max(0, C6_MIN_LOW - row["LOW_dates"])
    return {"lead": row["lead"],
            "as_written": {"additional_dates": add_dates, "additional_LOW_rows": add_low_rows,
                           "additional_HIGH_rows": add_high_rows,
                           "minimum_new_quarters": max(add_dates, 1 if add_low_rows else 0)},
            "dependence_aware": {"additional_LOW_dates": add_low_dates, "additional_dates": add_dates,
                                 "minimum_new_quarters": max(add_dates, add_low_dates)}}


def quarters_to_evaluable(row: dict, p_low_date: float, rows_per_low_date: float, dependence_aware: bool,
                          q_max: int = 80, sims: int = 20000, seed: int = 20261014) -> dict:
    """Monte Carlo: future quarters until the lead is C6-evaluable, if each new date is a LOW date with probability
    p_low_date (and, as written, contributes rows_per_low_date LOW rows). Returns median and 80th percentile."""
    import numpy as np

    rng = np.random.default_rng(seed)
    need = []
    for _ in range(sims):
        d, lr, ld, hr = row["dates"], row["LOW_rows"], row["LOW_dates"], row["HIGH_rows"]
        q = 0
        while q < q_max:
            ok = d >= C6_MIN_DATES and hr >= C6_MIN_HIGH and ((ld >= C6_MIN_LOW) if dependence_aware else (lr >= C6_MIN_LOW))
            if ok:
                break
            q += 1
            d += 1
            if rng.random() < p_low_date:
                ld += 1
                k = max(1, int(round(rng.normal(rows_per_low_date, 0.8))))
                k = min(k, 5)
                lr += k
                hr += 5 - k
            else:
                hr += 5
        need.append(q)
    a = np.array(need)
    return {"median_quarters": float(np.median(a)), "p80_quarters": float(np.percentile(a, 80)),
            "share_not_reached_by_q_max": float((a >= q_max).mean()), "p_low_date": p_low_date}


def dates_for_skill(win_prob: float, alpha: float = 0.05, power: float = 0.8, n_max: int = 200) -> int | None:
    """Smallest number of independent dates at which a one-sided exact sign test (the sign-flip test's lower bound in
    information) rejects at `alpha` with probability >= `power`, if the arm beats persistence on a date with
    probability win_prob. This is the evidence needed to SHOW skill; meeting C6's counts does not provide it."""
    from math import comb

    for n in range(1, n_max + 1):
        # critical value: smallest k with P(K >= k | p=.5) <= alpha
        tail, k_crit = 0.0, None
        for k in range(n, -1, -1):
            tail += comb(n, k) / 2 ** n
            if tail > alpha:
                k_crit = k + 1
                break
        if k_crit is None or k_crit > n:
            continue
        pw = sum(comb(n, k) * win_prob ** k * (1 - win_prob) ** (n - k) for k in range(k_crit, n + 1))
        if pw >= power:
            return n
    return None


def min_dates_any_significance(alpha: float = 0.05) -> int:
    """With n dates the smallest attainable one-sided exact p is 2^-n; p < alpha needs n >= this."""
    return math.ceil(math.log(1 / alpha, 2))
