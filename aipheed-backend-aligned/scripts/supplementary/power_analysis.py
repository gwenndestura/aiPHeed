"""
scripts/power_analysis.py
--------------------------
How many observations would the Research Question 3 comparison actually need?

The paired tests in `significance_tests.py` returned p = 0.75 against naive
persistence on 55 observations. That is not a verdict on the model; it is a
statement that the design cannot resolve a difference of the size observed.
This script asks what it would take to resolve it, so the limitation can be
quantified rather than described.

McNemar's test depends only on the discordant pairs, so the calculation runs in
two steps: the required number of discordant pairs to detect the observed split
at a given power, then the total sample that yields them at the observed
discordance rate.

It reads the stored test output and computes. It trains nothing.

    python -m scripts.power_analysis
"""

from __future__ import annotations

import json
from math import ceil, sqrt
from pathlib import Path

OUT = Path("data/supplementary/power_analysis.json")

# Standard normal quantiles: two-sided alpha = 0.05, and power 0.80 / 0.90.
Z_ALPHA = 1.959964
Z_POWER = {0.80: 0.841621, 0.90: 1.281552}

PROVINCES = 5          # CALABARZON, fixed by the approved scope
QUARTERS_PER_YEAR = 4


def required_discordant(p_model: float, power: float) -> int:
    """
    Discordant pairs needed for a binomial test of p_model against 0.5.

    Under McNemar's null the discordant pairs split evenly, so detecting a true
    split of p_model is a one-sample binomial problem.
    """
    effect = abs(p_model - 0.5)
    if effect == 0:
        return -1
    num = Z_ALPHA * sqrt(0.25) + Z_POWER[power] * sqrt(p_model * (1 - p_model))
    return ceil((num / effect) ** 2)


def main() -> dict:
    tests = json.load(open("data/supplementary/significance_tests.json"))
    rows = []

    for name, t in tests["tests"].items():
        m = t["mcnemar"]
        n_obs = tests["n"]
        n_disc = m["n_discordant"]
        rate = n_disc / n_obs                      # discordance rate
        p_model = m["b10"] / n_disc if n_disc else 0.5

        entry = {"comparison": name, "observed_n": n_obs,
                 "observed_discordant": n_disc,
                 "discordance_rate": round(rate, 4),
                 "observed_split_favouring_model": round(p_model, 4),
                 "observed_p": m["p_value"], "requirements": {}}

        for power in (0.80, 0.90):
            need_disc = required_discordant(p_model, power)
            if need_disc < 0:
                entry["requirements"][str(power)] = {"note": "no effect to detect"}
                continue
            need_n = ceil(need_disc / rate) if rate else None
            need_q = ceil(need_n / PROVINCES) if need_n else None
            entry["requirements"][str(power)] = {
                "discordant_pairs_needed": need_disc,
                "paired_observations_needed": need_n,
                "province_quarters_needed": need_n,
                "quarters_needed_at_5_provinces": need_q,
                "years_needed": round(need_q / QUARTERS_PER_YEAR, 1) if need_q else None,
            }
        rows.append(entry)

    out = {"alpha": 0.05, "provinces": PROVINCES, "comparisons": rows}
    OUT.write_text(json.dumps(out, indent=2))

    print("\nPOWER ANALYSIS FOR THE RESEARCH QUESTION 3 COMPARISON")
    print("=" * 76)
    for e in rows:
        print(f"\n{e['comparison']}")
        print(f"  observed: n={e['observed_n']}, {e['observed_discordant']} discordant "
              f"({e['discordance_rate']:.1%}), split {e['observed_split_favouring_model']:.2f} "
              f"to the model, p={e['observed_p']}")
        for power, r in e["requirements"].items():
            if "note" in r:
                print(f"  power {power}: {r['note']}")
                continue
            print(f"  to detect that split at {float(power):.0%} power:")
            print(f"     {r['discordant_pairs_needed']:>6d} discordant pairs")
            print(f"     {r['paired_observations_needed']:>6d} labelled province-quarters "
                  f"(have {e['observed_n']} evaluated)")
            print(f"     {r['quarters_needed_at_5_provinces']:>6d} quarters at 5 provinces "
                  f"= {r['years_needed']} years")
    print("=" * 76)
    print(f"written -> {OUT}")
    return out


if __name__ == "__main__":
    main()
