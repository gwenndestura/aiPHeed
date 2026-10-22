"""E85 run (PROTOCOL section 4): S-COMP-G, M-LR-G, M-GB-G and H-GDELT on the E84 rows.
Run from backend/:  python .../run_e85.py <e84_run_dir>"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(EXP / "E84_Objective_Continuation" / "runner"))
sys.path.insert(0, str(EXP / "E83_Deep_Reconstruction" / "runner"))
import e85_features as G  # noqa: E402
import e84_lib as C  # noqa: E402
import run_e83 as R  # noqa: E402
import run_e84 as R4  # noqa: E402

E, L, np, pd = C.E, C.L, C.np, C.pd
from scipy.stats import norm  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402

E85 = HERE.parent
ARMS = ["S-COMP-G", "M-LR-G", "M-GB-G"]


def rw_sigma(d_cut, t, k):
    hq = L.h_quarters(d_cut).sort_values("q")
    qq, hh = hq["q"].to_numpy(), hq["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    return sig * math.sqrt(max(t + k - int(qq[-1]), 1)), float(hh[-1]), int(qq[-1])


def hunger_component(X, d, t, k):
    """Ridge of H(t'+k) on H_last(t') + regional GDELT at t' (pairs posted before O(t)); P(H>11.3) at t."""
    reg = X.drop_duplicates("t").set_index("t")
    hq_cut = L.h_quarters(d.cut(t)).set_index("q")["H"]
    rows = []
    for tp in reg.index:
        q = tp + k
        if q <= t - 1 and q in hq_cut.index and pd.notna(reg.loc[tp, "H_last"]):
            rows.append({"t": tp, "y": hq_cut[q]})
    tr = pd.DataFrame(rows)
    s_rw, H_last, _ = rw_sigma(d.cut(t), t, k)
    cols = ["H_last"] + G.G_REGIONAL
    if len(tr) < 8:
        return float(1 - norm.cdf((L.e40_spec()["H"] - H_last) / s_rw)), H_last, "random walk", len(tr)
    Z = reg.loc[tr["t"], cols].astype(float)
    keep = [c for c in cols if Z[c].notna().all() and Z[c].std() > 0 and pd.notna(reg.loc[t, c])]
    mu, sd = Z[keep].mean(), Z[keep].std(ddof=0)
    m = Ridge(alpha=1.0).fit((Z[keep] - mu) / sd, tr["y"])
    rmse = float(np.sqrt(np.mean((m.predict((Z[keep] - mu) / sd) - tr["y"]) ** 2)))
    x = reg.loc[[t], keep].astype(float).copy()
    x["H_last"] = H_last                       # the latest round posted before O(t)
    Hh = float(m.predict((x[keep] - mu) / sd)[0])
    s = max(s_rw, rmse)
    return float(1 - norm.cdf((L.e40_spec()["H"] - Hh) / s)), Hh, "ridge", len(tr)


def run(e84: Path, k: int, d, gd):
    P = pd.read_csv(e84 / f"predictions_k{k}.csv", dtype={"province_code": str})
    X = pd.read_csv(e84 / f"features_k{k}.csv", dtype={"province_code": str})
    gf = G.features(gd, sorted(X["t"].unique()), L.origin)
    X = X.merge(gf, on=["t", "province_code"], how="left")
    base = R.cols_of(R.BASE_GROUPS) + R4.NEW
    add = []
    for t in sorted(P["t"].unique()):
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        tr = E.pairs(X, d, t, k)
        ph, Hh, how, npairs = hunger_component(X, d, t, k)
        lr = R.fit_predict("LR", base + G.G_PROVINCE + G.G_REGIONAL, tr, te)
        gb = R.fit_predict("GB", base + G.G_PROVINCE + G.G_REGIONAL, tr, te)
        for i, p in enumerate(L.PROVS):
            pp = te["comp_p_price"].iloc[i]
            add.append({"t": t, "province_code": p, "S-COMP-G": ph * pp if pd.notna(pp) else np.nan, "g_p_hunger": ph,
                        "g_H_hat": Hh, "g_hunger_model": how, "g_pairs": npairs,
                        "M-LR-G": np.nan if lr is None else lr[i], "M-GB-G": np.nan if gb is None else gb[i]})
    return P.merge(pd.DataFrame(add), on=["t", "province_code"], how="left"), X


def hunger_outcomes(P2, d):
    """H-BIN / H-RISE at Lead 2, one row per target quarter."""
    hq = L.h_quarters(d).set_index("q")["H"]
    D = P2.drop_duplicates("t")[["t", "target_q", "g_H_hat", "g_hunger_model"]].copy()
    D["q"] = D["t"] + 2
    D["H"] = D["q"].map(hq)
    D["H_last"] = [rw_sigma(d.cut(t), t, 2)[1] for t in D["t"]]
    D = D.dropna(subset=["H"])
    yb, yr = (D["H"] > 11.3).astype(int), (D["H"] - D["H_last"] > 3).astype(int)
    fit = D["g_hunger_model"] == "ridge"
    return {"rows": len(D), "ridge_rows": int(fit.sum()),
            "H-BIN": {"persistence": float(((D["H_last"] > 11.3).astype(int) == yb).mean()), "always_high": float(yb.mean()),
                      "gdelt": float(((D["g_H_hat"] > 11.3).astype(int) == yb).mean()),
                      "gdelt_on_ridge_rows": float(((D["g_H_hat"] > 11.3).astype(int) == yb)[fit].mean()) if fit.any() else None,
                      "mae_persistence": float((D["H"] - D["H_last"]).abs().mean()),
                      "mae_gdelt": float((D["H"] - D["g_H_hat"]).abs().mean())},
            "H-RISE": {"prevalence": float(yr.mean()),
                       "gdelt": float(((D["g_H_hat"] - D["H_last"] > 3).astype(int) == yr).mean())}}, D


if __name__ == "__main__":
    e84 = Path(sys.argv[1])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E85 / "runs" / stamp
    out.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    gd = G.load()
    R.PRIMARY[:] = ARMS + ["S-COMP", "S-SIM"]
    summary = {"stamp": stamp, "protocol_sha256": (E85 / "PROTOCOL.sha256").read_text().split()[0], "e84_run": e84.name,
               "gdelt_records": len(gd), "leads": {}}
    for k in (1, 2, 3):
        P, X = run(e84, k, d, gd)
        P.to_csv(out / f"predictions_k{k}.csv", index=False)
        X[["t", "province_code"] + G.G_REGIONAL + G.G_PROVINCE].to_csv(out / f"gdelt_features_k{k}.csv", index=False)
        res, tests = R.evaluate(P)
        news = R2_test = {}
        D = P[P["S-COMP-G"].notna() & P["S-COMP"].notna()]
        g = D.assign(da=(D["S-COMP"] - D["y"]) ** 2 - (D["S-COMP-G"] - D["y"]) ** 2).groupby("target_q")["da"].mean()
        news = E.sign_flip(g.to_numpy())
        summary["leads"][k] = {"metrics": {a: res[a] for a in R.PRIMARY + R.BASELINES if a in res}, "tests": tests,
                               "pass": {a: R.passes(res, tests, a) for a in R.PRIMARY},
                               "gdelt_vs_scomp_brier": news,
                               "recall_HIGH": {a: res[a]["issued_rows"]["recall_HIGH"] for a in ("S-COMP", "S-COMP-G")}}
        if k == 2:
            summary["hunger_outcomes_lead2"], HD = hunger_outcomes(P, d)
            HD.to_csv(out / "hunger_outcomes_lead2.csv", index=False)
        print(f"k={k}", flush=True)
        for a in ["B-PERSIST", "B-STATE", "B-CLIM", "B-AL"] + R.PRIMARY:
            m, mi = res[a]["all_rows_unissued_wrong"], res[a]["issued_rows"]
            print(f"  {a:10s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} brier={m.get('brier', float('nan')):.3f}"
                  f" recH={m['recall_HIGH'] or 0:.2f} | issued {mi['issued']} acc={mi['accuracy'] or 0:.3f}"
                  f" PASS={summary['leads'][k]['pass'].get(a, {}).get('PASS')}", flush=True)
        print("  GDELT vs S-COMP paired Brier:", {a: round(b, 4) for a, b in news.items()}, flush=True)
    print("hunger outcomes:", json.dumps(summary.get("hunger_outcomes_lead2")), flush=True)
    (out / "metrics.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(out)
