"""Step 1 of the horizon directive: which leads can be evaluated at all, from data availability only.

For every lead k it counts, without fitting or scoring any model, the target quarters whose origin t = q - k is in the
study window, whose training set (price labels complete before O(t), origins >= 2021-Q1) meets the frozen eligibility
minimum (6 quarters, 5 HIGH, 5 LOW price labels) and whose T43c label exists (SWS round, quarter <= 2026-Q3). It also
reports how many A1 base months exist and the true SWS horizon. Outcomes of the evaluated quarters are not read.

    python testability.py      # out/testability.json
"""
from common import B, C, E, FM, L, OUT, np, pd, setup

KMAX = 12


def main():
    setup()
    obs = C.labels()
    quarters = sorted(q for q in obs["q"].unique() if q <= E.LAST_OUTCOME)
    out = {}
    for k in range(1, KMAX + 1):
        X = C.build_X(k)
        ev, th, a1 = [], [], []
        for q in quarters:
            t = q - k
            if t < E.FIRST_ORIGIN:
                continue
            tr = B.price_rows(X, t, k)
            te = X[X["t"] == t]
            if not B.eligible(tr) or not len(te) or te["H1"].isna().any():
                continue
            ev.append(L.qs(q))
            th.append(int(te["true_horizon"].iloc[0]))
            a1.append(float(te["A1_food"].notna().mean()))
        out[k] = {"evaluable_quarters": len(ev), "rows": 5 * len(ev), "quarters": ev,
                  "true_sws_horizon": sorted(set(th)), "A1_available_share": float(np.mean(a1)) if a1 else None,
                  "A1_base_months_possible": len(E.projection_bases(E.LAST_ORIGIN, k)),
                  "R1_possible": len(ev) >= 10 and 5 * len(ev) >= 40}
        print(k, out[k]["evaluable_quarters"], out[k]["true_sws_horizon"], out[k]["A1_available_share"],
              out[k]["A1_base_months_possible"])
    FM.write_json(OUT / "testability.json", {"kmax_checked": KMAX, "leads": out,
                                             "longest_evaluable_lead": max([k for k in out if out[k]["rows"]], default=None),
                                             "longest_R1_lead": max([k for k in out if out[k]["R1_possible"]], default=None)})


if __name__ == "__main__":
    main()
