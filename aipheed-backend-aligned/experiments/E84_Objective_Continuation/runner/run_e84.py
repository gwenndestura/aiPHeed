"""E84 run (PROTOCOL.md section 4): adds the E84 arms to the E83 final run's rows (same targets, origins, baselines)
and scores them with the E83 rule. Run from backend/:  python .../run_e84.py <e83_run_dir>"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e84_lib as C  # noqa: E402

E, L, np, pd = C.E, C.L, C.np, C.pd
sys.path.insert(0, str(C.E84.parent / "E83_Deep_Reconstruction" / "runner"))
import run_e83 as R  # noqa: E402
import run_round2 as R2  # noqa: E402

NEW = ["rice_yoy_now", "rice_mom3", "comp_F_hat", "comp_G_hat", "w_rice_chg3", "w_rice_chg6", "w_food_chg3", "w_food_chg6"]
ARMS = ["S-COMP", "S-COMP-NOW", "S-COMP-THR", "M-LR-W", "M-GB-W", "HYB-W"]


def add_features(X, d, x, sub, W, w, k):
    rows = []
    for t in sorted(X["t"].unique()):
        fx = x["ofw"][x["ofw"]["q"] <= t - 1].drop_duplicates("q").set_index("q")["fx_usd_php_avg"]
        wc = C.world_cut(w, t)
        a = C.simulate_comp(d.cut(t), sub, W, wc, fx, t, k, passthrough=True)
        b = C.simulate_comp(d.cut(t), sub, W, wc, fx, t, k, passthrough=False)
        ef = C.extra_features(sub[sub["ym"] <= L.m0_of(t)], wc, t).set_index("province_code")
        for p in L.PROVS:
            va, vb = a.get(p, {}), b.get(p, {})
            rows.append({"t": t, "province_code": p, "comp_p": va.get("p", np.nan), "comp_p_price": va.get("p_price", np.nan),
                         "comp_p_hunger": va.get("p_hunger", np.nan), "comp_F_hat": va.get("F_hat", np.nan),
                         "comp_G_hat": va.get("G_hat", np.nan), "comp_beta": va.get("beta", np.nan),
                         "compnow_p": vb.get("p", np.nan), "compnow_p_price": vb.get("p_price", np.nan),
                         **ef.loc[p].to_dict()})
    return X.merge(pd.DataFrame(rows), on=["t", "province_code"], how="left")


def run(e83_run: Path, k: int, d, x, sub, W, w):
    P = pd.read_csv(e83_run / f"predictions_r2_k{k}.csv", dtype={"province_code": str})
    X = pd.read_csv(e83_run / f"features_r2_k{k}.csv", dtype={"province_code": str})
    X = add_features(X, d, x, sub, W, w, k)
    base = R.cols_of(R.BASE_GROUPS)
    add = []
    for t in P["t"].unique():
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        tr = E.pairs(X, d, t, k)
        thr = R2.threshold(tr[tr["comp_p"].notna()].rename(columns={}), "comp_p")
        lr = R.fit_predict("LR", base + NEW, tr, te)
        gb = R.fit_predict("GB", base + NEW, tr, te)
        for i, p in enumerate(L.PROVS):
            cp = te["comp_p"].iloc[i]
            add.append({"t": t, "province_code": p, "S-COMP": cp, "S-COMP-NOW": te["compnow_p"].iloc[i],
                        "S-COMP-THR": R2._shift(cp, thr), "thr_comp": thr,
                        "M-LR-W": np.nan if lr is None else lr[i], "M-GB-W": np.nan if gb is None else gb[i],
                        "HYB-W": cp if gb is None else gb[i]})
    P = P.merge(pd.DataFrame(add), on=["t", "province_code"], how="left")
    return P, X


def price_diagnostic(d, X, k):
    """P(price condition at t+k) vs the price condition itself on every quarter 2023-Q1..2026-Q3 (no SWS needed)."""
    th = L.e40_spec()
    F = L.quarter_F(d, "food").merge(L.quarter_F(d, "all_items").rename(columns={"F": "HL"}), on=["province_code", "q"])
    F["y"] = ((F["F"] > F["province_code"].map(th["food"])) | ((F["F"] - F["HL"]) > F["province_code"].map(th["gap"]))).astype(int)
    F = F[(F["q"] >= E.EVAL_FROM) & (F["q"] <= L.qi("2026-Q3"))]
    M = F.merge(X.assign(q=X["t"] + k)[["province_code", "q", "sim_p_price", "comp_p_price", "compnow_p_price"]],
                on=["province_code", "q"])
    out = {"rows": len(M), "positives": int(M["y"].sum())}
    for c in ("sim_p_price", "compnow_p_price", "comp_p_price"):
        D = M[M[c].notna()]
        out[c] = E.metrics(D["y"], (D[c] >= 0.5).astype(int), D[c])
    persist = F.assign(q=F["q"] + k)[["province_code", "q", "y"]].rename(columns={"y": "y_prev"})
    Mp = F.merge(persist, on=["province_code", "q"])        # price condition k quarters earlier (known by O(t) when k>=1)
    out["persistence_k"] = E.metrics(Mp["y"], Mp["y_prev"], Mp["y_prev"].astype(float))
    return out


def alternative_outcomes(d, w, x):
    """H-BIN and H-RISE at Lead 2 (regional, one row per quarter): persistence, always-HIGH, ridge on lagged rice
    inflation and world food change, fitted on earlier pairs only."""
    from sklearn.linear_model import Ridge
    hq = L.h_quarters(d).set_index("q")["H"]
    sub, W = C.load_sub()
    rows = []
    for q in sorted(hq.index):
        t = q - 2
        c = L.h_quarters(d.cut(t)).sort_values("q")
        if not len(c):
            continue
        m0 = L.m0_of(t)
        rice = sub[(sub.group == "rice") & (sub.ym <= m0)].groupby("ym")["index"].mean().sort_index()
        ry = 100 * (rice.iloc[-1] / rice.get(m0 - 12, np.nan) - 1) if (m0 - 12) in rice.index else np.nan
        wc = C.world_cut(w, t)
        wf = wc[wc.series == "w_food"].set_index("ym")["value"].sort_index()
        rows.append({"q": q, "H": hq[q], "H_last": float(c["H"].iloc[-1]), "rice_yoy": ry,
                     "w_food_chg6": float(100 * np.log(wf.iloc[-1] / wf.iloc[-7])) if len(wf) >= 7 else np.nan})
    D = pd.DataFrame(rows)
    D["ridge"] = np.nan
    for i, r in D.iterrows():
        tr = D[(D["q"] <= r["q"] - 3)].dropna(subset=["rice_yoy", "w_food_chg6"])   # target posted before origin
        if len(tr) >= 6 and pd.notna(r["rice_yoy"]) and pd.notna(r["w_food_chg6"]):
            m = Ridge(alpha=1.0).fit(tr[["H_last", "rice_yoy", "w_food_chg6"]], tr["H"])
            D.loc[i, "ridge"] = float(m.predict(pd.DataFrame([r[["H_last", "rice_yoy", "w_food_chg6"]]]))[0])
    ev = D[D["q"] >= E.EVAL_FROM]
    yb, yr = (ev["H"] > 11.3).astype(int), (ev["H"] - ev["H_last"] > 3).astype(int)
    res = {"rows": len(ev),
           "H-BIN": {"persistence": float(((ev["H_last"] > 11.3).astype(int) == yb).mean()), "always_high": float(yb.mean()),
                     "ridge": float(((ev["ridge"] > 11.3).astype(int) == yb)[ev["ridge"].notna()].mean()),
                     "ridge_n": int(ev["ridge"].notna().sum()),
                     "mae_persistence": float((ev["H"] - ev["H_last"]).abs().mean()),
                     "mae_ridge": float((ev["H"] - ev["ridge"]).abs()[ev["ridge"].notna()].mean())},
           "H-RISE": {"prevalence": float(yr.mean()), "always_no": float(1 - yr.mean()),
                      "ridge": float(((ev["ridge"] - ev["H_last"] > 3).astype(int) == yr)[ev["ridge"].notna()].mean())}}
    return res, D


if __name__ == "__main__":
    e83 = Path(sys.argv[1])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = C.E84 / "runs" / stamp
    out.mkdir(parents=True, exist_ok=True)
    d, x = E.data()
    sub, W = C.load_sub()
    w = C.load_world()
    R.PRIMARY[:] = ARMS + ["S-SIM", "S-SIM-THR"]
    summary = {"stamp": stamp, "protocol_sha256": (C.E84 / "PROTOCOL.sha256").read_text().split()[0], "e83_run": e83.name,
               "leads": {}}
    for k in E.LEADS:
        P, X = run(e83, k, d, x, sub, W, w)
        P.to_csv(out / f"predictions_k{k}.csv", index=False)
        X.to_csv(out / f"features_k{k}.csv", index=False)
        res, tests = R.evaluate(P)
        summary["leads"][k] = {"metrics": {a: res[a] for a in R.PRIMARY + R.BASELINES if a in res}, "tests": tests,
                               "pass": {a: R.passes(res, tests, a) for a in R.PRIMARY},
                               "price_diagnostic": price_diagnostic(d, X, k)}
        print(f"k={k}", flush=True)
        for a in ["B-PERSIST", "B-STATE", "B-CLIM", "B-AL"] + R.PRIMARY:
            m, mi = res[a]["all_rows_unissued_wrong"], res[a]["issued_rows"]
            ps = summary["leads"][k]["pass"].get(a, {})
            print(f"  {a:11s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} brier={m.get('brier', float('nan')):.3f}"
                  f" recH={m['recall_HIGH'] or 0:.2f} | issued {mi['issued']} acc={mi['accuracy'] or 0:.3f}"
                  f" PASS={ps.get('PASS')}", flush=True)
        pdg = summary["leads"][k]["price_diagnostic"]
        print("  price-condition diagnostic:", {c: (round(pdg[c]["accuracy"], 3), round(pdg[c]["balanced_accuracy"] or 0, 3),
                                                   round(pdg[c].get("brier", float("nan")), 3))
                                               for c in ("sim_p_price", "compnow_p_price", "comp_p_price", "persistence_k")}, flush=True)
    alt, D = alternative_outcomes(d, w, x)
    summary["alternative_outcomes_lead2"] = alt
    D.to_csv(out / "alternative_outcomes.csv", index=False)
    print("alternative outcomes:", json.dumps(alt), flush=True)
    (out / "metrics.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(out)
