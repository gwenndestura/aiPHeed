"""How many NEW, untouched quarters are needed? Monte Carlo using the observed T1 lead-1 structure (no data read
except E24's own reproduction JSON). Persistence errs exactly on label-change rows (verified in E24 step 1).
A hypothetical model anticipates a share f of the changes and wrongly flips a share r of unchanged rows.
Power = P(one-sided sign-flip p < 0.05 on per-quarter accuracy differences AND mean difference > 0).
Also: P(the new quarters contain >= 5 LOW rows), needed for evaluability.
Usage: python -B runner/minimum_data.py"""
import json
from pathlib import Path

import numpy as np

EXP = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(20261014)
a = json.loads((EXP / "runs" / "reproduction_and_audit.json").read_text(encoding="utf-8"))["error_analysis_lead1_primary"]
P_CHANGE_QUARTER = len({r["target_quarter"] for r in a["changed_rows"]}) / a["quarters"]   # quarters with a change
P_LOW_ROW = 3 / 40                                                                         # observed lead-1 LOW share


def signflip_p(d, n_mc=4000):
    n = len(d)
    if n <= 14:
        S = 1 - 2 * ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1)
    else:
        S = rng.choice([-1, 1], size=(n_mc, n))
    obs = d.mean()
    return float(((S * d).mean(1) >= obs - 1e-12).mean())


def simulate(nq, f, r, reps=1500):
    hits = 0
    for _ in range(reps):
        d = np.zeros(nq)
        for i in range(nq):
            changes = int(rng.random() < P_CHANGE_QUARTER)          # observed: at most one change per quarter
            gain = rng.binomial(changes, f)                         # changes the model gets right (persistence wrong)
            loss = rng.binomial(5 - changes, r)                     # unchanged rows the model gets wrong
            d[i] = (gain - loss) / 5
        if d.mean() > 0 and signflip_p(d) < 0.05:
            hits += 1
    return hits / reps


def p_low(nq, need=5, reps=20000):
    return float((rng.binomial(5 * nq, P_LOW_ROW, size=reps) >= need).mean())


def main():
    rows = []
    for nq in (8, 12, 16, 20, 24, 32, 40):
        row = {"new_quarters": nq, "P(>=5 LOW rows)": p_low(nq)}
        for f, r in ((1.0, 0.0), (0.75, 0.0), (0.5, 0.0), (0.5, 0.02), (0.75, 0.05)):
            row[f"power f={f} r={r}"] = simulate(nq, f, r)
        rows.append(row)
    out = {"assumptions": {"P(quarter has a label change)": P_CHANGE_QUARTER, "P(row is LOW)": P_LOW_ROW,
                           "rows per quarter": 5, "test": "one-sided sign-flip on per-quarter accuracy difference",
                           "note": "f = share of label changes the model anticipates; r = false-flip rate on "
                                   "unchanged rows. The E23 models had f = 0 (0 of 5 changes)."},
           "table": rows}
    (EXP / "runs" / "minimum_data.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
