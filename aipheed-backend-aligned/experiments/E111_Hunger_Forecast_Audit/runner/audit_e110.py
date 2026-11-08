"""E111 step 1: independent audit of E110 from its saved predictions, data and code (no new model is chosen here).
Writes ../out/audit_e110.json."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E111 = HERE.parent
E110R = E111.parent / "E110_Hunger_Generalization" / "runner"
sys.path.insert(0, str(E110R))
import e110_lib as F  # noqa: E402

E, H9, np, pd = F.E, F.H9, F.np, F.pd
E110_OUT = E110R.parent / "out"
METHODS = F.PANEL_METHODS


def recompute_metrics(res: dict) -> dict:
    out = {}
    for k in (1, 2, 3, 4):
        df = pd.read_csv(E110_OUT / f"panel_lead{k}.csv")
        rep = res["panel"][str(k)]["continuous"]
        same_rows = bool(df[METHODS].notna().all().all())
        mae = {m: float(np.abs(df[m] - df["y"]).mean()) for m in METHODS}
        dq = {m: F.quarter_diff(df, m) for m in ("LLR", "COMB")}
        dm = {m: F._dm_signed(dq[m].to_numpy(), k) for m in dq}
        # moving-block bootstrap of the mean quarter difference (block = max(k, 2)), seed 2026
        rng = np.random.default_rng(2026)
        boot = {}
        for m, s in dq.items():
            v, n, b = s.to_numpy(), len(s), max(k, 2)
            st = np.arange(n - b + 1)
            draws = [v[np.concatenate([np.arange(i, i + b) for i in rng.choice(st, math.ceil(n / b))])[:n]].mean()
                     for _ in range(4000)]
            boot[m] = [float(np.percentile(draws, 5)), float(np.percentile(draws, 95))]
        out[str(k)] = {"rows": len(df), "quarters": int(df["q"].nunique()), "all_methods_on_same_rows": same_rows,
                       "mae_recomputed": mae, "mae_reported": {m: rep[m]["mae"] for m in METHODS},
                       "max_abs_discrepancy": float(max(abs(mae[m] - rep[m]["mae"]) for m in METHODS)),
                       "dm_recomputed": {m: dm[m].get("p") for m in dm},
                       "dm_reported": {m: res["panel"][str(k)]["decision"][m]["dm"].get("p") for m in dq},
                       "mean_diff_block_bootstrap_90": boot}
    return out


def cutoff_check() -> dict:
    """Every RW value used at an origin must come from rounds published before that origin's issue date."""
    a = pd.read_csv(F.AREA_FILE)
    viol, n = 0, 0
    for k in (1, 2, 3, 4):
        df = pd.read_csv(E110_OUT / f"panel_lead{k}.csv")
        for r in df.itertuples():
            pubs = a.loc[a["quarter"] == r.h_last_quarter, "published"]
            n += 1
            if not (pubs.astype(str).str[:10] < E.issue(int(r.t))).any():
                viol += 1
            f = F.forecast("LLR", int(r.t), k, r.area)
            if abs(f["forecast"] - r.LLR) > 1e-6:
                viol += 1
    return {"rows_checked": n, "violations": viol}


def inferred_cells() -> dict:
    cells = [("2021-Q2 (Jun 2021)", "NCR"), ("2021-Q2 (Jun 2021)", "VIS"), ("2021-Q2 (Jun 2021)", "MIN")]
    first_eval = min(int(pd.read_csv(E110_OUT / f"panel_lead{k}.csv")["q"].min()) for k in (1, 2, 3, 4))
    return {"inferred": [f"{q} {a}" for q, a in cells] + ["2021-Q4 all areas: from search-result text of the retired SWS page"],
            "used_as_evaluation_outcomes": False, "first_evaluated_target": E.qs(first_eval),
            "role": "training history only (known values, pooled Q of the LLR filter)"}


def area_dependence() -> dict:
    a = pd.read_csv(F.AREA_FILE)
    q = a.groupby("quarter")[list(F.AREAS.values())].mean()
    ch = q.diff().dropna()
    corr = ch.corr()
    df1 = pd.read_csv(E110_OUT / "panel_lead1.csv")
    err = df1.assign(e=df1["RW"] - df1["y"]).pivot(index="q", columns="area", values="e")
    ec = err.corr()
    off = ec.to_numpy()[~np.eye(4, dtype=bool)]
    rho = float(np.mean(off))
    return {"change_correlation": corr.round(3).to_dict(), "rw_error_correlation_lead1": ec.round(3).to_dict(),
            "mean_offdiag_error_corr": rho,
            "effective_areas_per_quarter": float(4 / (1 + 3 * max(rho, 0))),
            "note": "areas share survey-wide shocks; inference must be by quarter (E110 averaged within quarter)"}


def noise_share() -> dict:
    from scipy.stats import chi2
    s = [(q, F.outcome(q, "BL")) for q in F.outcome_quarters("BL")]
    d = np.array([b[1] - a[1] for a, b in zip(s, s[1:]) if b[0] - a[0] == 1])
    n = len(d)
    v = float(d.var(ddof=1))
    lo, hi = v * (n - 1) / chi2.ppf(0.975, n - 1), v * (n - 1) / chi2.ppf(0.025, n - 1)
    out = {"n_changes": n, "var_change": v, "var_change_95ci": [lo, hi]}
    for moe in (4.0, 6.0):
        r = 2 * (moe / 1.959964) ** 2
        out[f"noise_share_moe{int(moe)}"] = {"point": r / v, "95ci": [r / hi, min(r / lo, 9.99)]}
    ac = float(np.corrcoef(d[:-1], d[1:])[0, 1])
    rng = np.random.default_rng(2026)
    bs = []
    for _ in range(4000):
        i = rng.integers(0, n - 1, n - 1)
        x, y = d[:-1][i], d[1:][i]
        if x.std() > 0 and y.std() > 0:
            bs.append(np.corrcoef(x, y)[0, 1])
    out["lag1_autocorr"] = ac
    out["lag1_autocorr_bootstrap_90"] = [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]
    out["implied_noise_share_if_rw_plus_noise"] = float(min(-2 * ac, 1.0)) if ac < 0 else 0.0
    out["assumption"] = ("SWS margins are taken as 95% simple-random-sampling margins; design effects are not published, "
                         "so the true sampling variance may be larger")
    return out


def band_coverage() -> dict:
    out = {}
    for k in (1, 2):
        df = pd.read_csv(E110_OUT / f"panel_lead{k}.csv")
        hit, width = [], []
        for r in df.itertuples():
            s = F.sigma("RW", int(r.t), k, r.area)
            hit.append(abs(r.y - r.RW) <= 1.2816 * s)
            width.append(1.2816 * s)
        bl = df["area"] == "BL"
        out[str(k)] = {"nominal": 0.80, "coverage_panel": float(np.mean(hit)), "coverage_BL": float(np.mean(np.array(hit)[bl])),
                       "mean_half_width_panel": float(np.mean(width)), "mean_half_width_BL": float(np.mean(np.array(width)[bl])),
                       "rows": len(df)}
    return out


def regime_and_design() -> dict:
    from scipy.stats import ttest_ind
    s = {q: F.outcome(q, "BL") for q in F.outcome_quarters("BL")}
    pre = [v for q, v in s.items() if q <= E.qi("2023-Q3")]
    post = [v for q, v in s.items() if q >= E.qi("2025-Q2")]
    t = ttest_ind(post, pre, equal_var=False)
    a = pd.read_csv(F.AREA_FILE)
    a = a[a["quarter"] >= "2025-Q2"]
    big, small = a[a["bl_n"] == 600], a[a["bl_n"] == 300]
    des = {}
    for ar, col in F.AREAS.items():
        tt = ttest_ind(big[col], small[col], equal_var=False)
        des[ar] = {"mean_1500_rounds": float(big[col].mean()), "mean_1200_rounds": float(small[col].mean()),
                   "welch_p": float(tt.pvalue), "n": [int(len(big)), int(len(small))]}
    return {"level_2021Q2_2023Q3_vs_2025Q2_2026Q3": {"mean_pre": float(np.mean(pre)), "mean_post": float(np.mean(post)),
                                                    "welch_p": float(t.pvalue), "status": "measured difference"},
            "design_1500_vs_1200_rounds_2025_26": des,
            "design_status": "hypothesis: direction differs by area; season and design confounded"}


def main() -> None:
    res = json.loads((E110_OUT / "results.json").read_text())
    out = {"metrics": recompute_metrics(res), "cutoff": cutoff_check(), "inferred_cells": inferred_cells(),
           "area_dependence": area_dependence(), "noise_share": noise_share(), "band_coverage": band_coverage(),
           "regime_design": regime_and_design()}
    E.write_json(E111 / "out" / "audit_e110.json", F._plain(out))
    print(json.dumps(F._plain(out), indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
