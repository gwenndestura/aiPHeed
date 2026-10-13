"""E15: size the prospective validation from E13's retrospective per-quarter results (2023-Q2..2025-Q4).

Method (fixed in PROSPECTIVE_VALIDATION_PROTOCOL.md):
  per-quarter MAE difference d_q = MAE_q(candidate) - MAE_q(carry-forward), mean delta, SD s (ddof=1);
  n80 = ceil(((z_{1-a} + z_{0.80}) * s / |delta|)^2) with a = 0.025 (Holm first step for 2 candidates);
  also at half the observed effect (the retrospective effect is likely optimistic);
  exact sign-flip floor: smallest n with 2^-n < a.
H1 uses E13's B2 (D) results directly. H2 rebuilds S1 forecasts as H_last_A + 2 * D_forecast, where H_last_A is
the latest production-series (definition_A) round value published before the origin (same rule as E13's h_last),
and scores them against realized S1 (labelled quarters only). Writes runs/sizing_<utc>/sizing.json (new)."""
from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import json  # noqa: E402
from statistics import NormalDist  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import loaders  # noqa: E402

ALPHA = 0.025
POWER = 0.80
Z = NormalDist().inv_cdf(1 - ALPHA) + NormalDist().inv_cdf(POWER)


def origin(q: str) -> pd.Timestamp:
    y, n = q.split("-Q")
    return pd.Timestamp(int(y), 3 * (int(n) - 1) + 1, 1)


def h_last(rounds: pd.DataFrame, as_of: pd.Timestamp):
    pub = rounds[rounds["published"] < as_of]
    if pub.empty:
        return None
    lastq = max(pub["quarter"], key=loaders.qkey)
    return float(pub.loc[pub["quarter"] == lastq, "H"].mean())


def size(d: np.ndarray) -> dict:
    delta, s = float(np.mean(d)), float(np.std(d, ddof=1))
    n_obs = math.ceil((Z * s / abs(delta)) ** 2) if delta != 0 else None
    n_half = math.ceil((Z * s / abs(delta / 2)) ** 2) if delta != 0 else None
    return {"quarters": int(len(d)), "mean_diff": delta, "sd_diff": s, "quarters_better": int((d < 0).sum()),
            "n80_at_observed_effect": n_obs, "n80_at_half_effect": n_half}


def main():
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = guard.EXP / "runs" / f"sizing_{ts}"
    out.mkdir(parents=True)
    hashes = guard.verify_allowlist()
    m = loaders.load_e13_metrics()
    sc = loaders.load_e13_scored()
    comp = loaders.load_components()
    rounds = loaders.load_rounds()

    res = {"alpha_one_sided": ALPHA, "power": POWER, "z_sum": Z,
           "sign_flip_floor_quarters": next(n for n in range(1, 30) if 2 ** -n < ALPHA)}
    b2 = m["results"]["B2|primary"]
    res["H1_B2"] = {}
    for arm in ["B2_ridge_D", "B2_ridge_DP"]:
        pq = b2["comparisons"][arm]["per_quarter_diff_vs_best"]       # best baseline was B2_cf
        assert b2["best_baseline"] == "B2_cf"
        res["H1_B2"][arm] = {"vs": "B2_cf", **size(np.array(list(pq.values()), float))}

    # H2: S1 forecasts from D forecasts
    rA = rounds[rounds["definition_A"]]
    d = sc[(sc["target"] == "B2") & (sc["analysis"] == "primary") & (sc["status"] == "OK")]
    wide = d.pivot_table(index=["quarter", "province_code"], columns="arm", values="forecast").reset_index()
    wide = wide.merge(comp[["quarter", "province_code", "S1"]], on=["quarter", "province_code"], how="left")
    wide = wide[wide["S1"].notna()].copy()
    wide["H_last_A"] = wide["quarter"].map(lambda q: h_last(rA, origin(q)))
    arms = {"S1_shrink_D": "B2_ridge_D", "S1_shrink_DP": "B2_ridge_DP", "S1_origin_rule": "B2_cf",
            "S1_meanD": "B2_zero"}
    for a, src in arms.items():
        wide[a] = wide["H_last_A"] + 2 * wide[src]
    mae = {a: float((wide[a] - wide["S1"]).abs().mean()) for a in arms}
    perq = {a: wide.assign(e=(wide[a] - wide["S1"]).abs()).groupby("quarter")["e"].mean() for a in arms}
    best = min(["S1_origin_rule", "S1_meanD"], key=lambda a: mae[a])
    res["H2_S1"] = {"quarters": sorted(wide["quarter"].unique().tolist(), key=loaders.qkey), "rows": int(len(wide)),
                    "MAE": mae, "best_baseline": best,
                    "note": "S1_meanD uses the pooled training-mean D, which is 0 by construction for complete "
                            "quarters (identical to E13's B2_zero)."}
    for a in ["S1_shrink_D", "S1_shrink_DP"]:
        res["H2_S1"][a] = {"vs": best, **size((perq[a] - perq[best]).to_numpy(float))}
    res["allowlist_sha256"] = hashes
    res["access_log"] = guard.ACCESS_LOG
    (out / "sizing.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(out)
    print(json.dumps({k: v for k, v in res.items() if k not in ("access_log", "allowlist_sha256")}, indent=1,
                     default=float))


if __name__ == "__main__":
    main()
