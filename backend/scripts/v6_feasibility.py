"""
v6 Stage 2 feasibility (docs/aipheed/v6/FEASIBILITY.md). Every route's target and tolerance is defined here from
measurement properties BEFORE its oracle is computed. Oracle = perfect knowledge of the current true (latent) hunger
level, with the true level a random walk of innovation variance q estimated (a) on all data and (b) on calm-period data
(rounds published before 2024-01-01). Route filter (declared in the v6 directive): pursue only if the Lead-2 oracle is
>= 0.85 on BOTH (a) and (b).

ROUTES (fixed before computing):
  R1 frozen        target: area quarter value          tol 1.645 x binomial SE (lock T1)
  R2 pub-SE        target: area quarter value          tol 1.645 x SE implied by published margin (lock T1 sensitivity)
  R3 pub-MoE       target: area quarter value          tol 1.96 x SE_pub = SWS's published 95 % margin
  R4 nowcast h=1   target: next quarter after newest reading (P-REL-like); tol as R1 / R3
  R5 latent        target: Kalman-filtered true level at the target quarter (all rounds up to it); tol 1.645 x its filter SD
  R6 semiannual    target: mean of the two quarters D+1, D+2 (Lead 2 and 3); tol 1.645 x SE of that mean
  R7 national      target: unweighted mean of the 4 areas; tol 1.645 x SE of the mean (q re-estimated on the mean series)

    python -I backend/scripts/v6_feasibility.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.models import S2_GRID  # noqa: E402
from app.forecasting.v2 import models as V  # noqa: E402

OUT = REPO / "docs" / "aipheed" / "v6" / "results"
Z90, Z95 = T.Z90, 1.959963984540054
CALM_CUTOFF = date(2024, 1, 1)


def within(tol, sd) -> float:
    return float(np.mean(2 * stats.norm.cdf(np.asarray(tol) / np.asarray(sd)) - 1))


def q_hat(rr, cutoff=None) -> float:
    qt = T.quarter_table(rr) if cutoff is None else T.known_at(rr, cutoff)
    return V.fit("LL", qt).q


def filtered_P(qt: pd.DataFrame, q: float) -> dict:
    """Filtered state variance at each observed (area, quarter), local level with known R = SE^2."""
    out = {}
    for a in qt.area.unique():
        idx, y, R = V.series(qt, a, int(qt.qi.max()))
        P, started = None, False
        for t, yt, rt in zip(idx, y, R):
            if not started:
                if yt == yt:
                    P, started = rt, True
                    out[(a, t)] = P
                continue
            P = P + q
            if yt == yt:
                P = P * rt / (P + rt)
                out[(a, t)] = P
    return out


def q_national(rr, cutoff=None) -> tuple[float, pd.DataFrame]:
    qt = T.quarter_table(rr) if cutoff is None else T.known_at(rr, cutoff)
    g = qt.groupby("qi").agg(y=("y", "mean"), se=("se", lambda s: np.sqrt((s ** 2).sum()) / 4), n=("y", "size"))
    g = g[g.n == 4].reset_index()
    nat = g.assign(area="national", quarter=g.qi.map(T.qs))
    idx = np.arange(int(nat.qi.min()), int(nat.qi.max()) + 1)
    s = nat.set_index("qi").reindex(idx)
    y, R = s.y.to_numpy(float), (s.se ** 2).to_numpy(float)
    # V.fit iterates over the 4 SWS areas only, so the national series is fitted directly on the same grid
    best = max((V.kalman(y, R, q, 1.0)[2], q) for q in S2_GRID)
    return float(best[1]), nat


def main():
    rr = T.load_rounds()
    full = T.quarter_table(rr)
    su = pd.read_csv(REPO / "docs" / "aipheed" / "v2" / "results" / "v2_outer_predictions.csv")
    su = su.merge(full[["area", "qi", "se_pub"]].rename(columns={"qi": "tqi"}), on=["area", "tqi"])
    Q = {"all": q_hat(rr), "calm": q_hat(rr, CALM_CUTOFF)}
    rows = []
    for regime, q in Q.items():
        Pf = filtered_P(full, q)
        for k, g in su.groupby("lead"):
            s_now = np.sqrt(g.h * q + g.se ** 2)
            rows += [
                {"route": "R1 frozen", "regime": regime, "lead": k, "oracle": within(Z90 * g.se, s_now)},
                {"route": "R2 pub-SE", "regime": regime, "lead": k, "oracle": within(Z90 * g.se_pub, s_now)},
                {"route": "R3 pub-MoE", "regime": regime, "lead": k, "oracle": within(Z95 * g.se_pub, s_now)},
            ]
            P = np.array([Pf.get((a, t), np.nan) for a, t in zip(g.area, g.tqi)])
            rows.append({"route": "R5 latent", "regime": regime, "lead": k,
                         "oracle": within(Z90 * np.sqrt(P), np.sqrt(g.h * q + P))})
            se2 = full.set_index(["area", "qi"]).se
            nxt = np.array([se2.get((a, t + 1), np.nan) for a, t in zip(g.area, g.tqi)])
            ok = ~np.isnan(nxt)
            se_m = np.sqrt(g.se.to_numpy()[ok] ** 2 + nxt[ok] ** 2) / 2
            rows.append({"route": "R6 semiannual", "regime": regime, "lead": k,
                         "oracle": within(Z90 * se_m, np.sqrt(g.h.to_numpy()[ok] * q + q / 4 + se_m ** 2))})
        # R4 nowcast h = 1 over all consecutive area pairs
        pairs = full.sort_values("qi")
        se1 = pairs.se.to_numpy()
        rows += [{"route": "R4 nowcast h=1 (frozen tol)", "regime": regime, "lead": "h=1",
                  "oracle": within(Z90 * se1, np.sqrt(q + se1 ** 2))},
                 {"route": "R4 nowcast h=1 (pub-MoE tol)", "regime": regime, "lead": "h=1",
                  "oracle": within(Z95 * pairs.se_pub.to_numpy(), np.sqrt(q + se1 ** 2))}]
        qn, nat = q_national(rr, None if regime == "all" else CALM_CUTOFF)
        nat_full = q_national(rr)[1]
        for h in (2, 3, 4, 5):
            rows.append({"route": "R7 national", "regime": regime, "lead": {2: 1, 3: 2, 4: 3, 5: 4}[h],
                         "oracle": within(Z90 * nat_full.se, np.sqrt(h * qn + nat_full.se ** 2)), "q_national": qn})
    d = pd.DataFrame(rows)
    d["oracle"] = d.oracle.round(4)
    piv = d.pivot_table(index=["route", "lead"], columns="regime", values="oracle").reset_index()
    l2 = piv[piv.lead.astype(str).isin(["2", "h=1"])].copy()
    l2["passes_0.85_filter"] = (l2["all"] >= 0.85) & (l2["calm"] >= 0.85)
    d.to_csv(OUT / "feasibility_oracles.csv", index=False)
    l2.to_csv(OUT / "feasibility_route_filter.csv", index=False)
    (OUT / "feasibility_q.json").write_text(json.dumps(Q) + "\n", encoding="utf-8", newline="\n")
    pd.set_option("display.width", 200)
    print(piv.to_string())
    print(l2.to_string())
    print(Q)


if __name__ == "__main__":
    main()
