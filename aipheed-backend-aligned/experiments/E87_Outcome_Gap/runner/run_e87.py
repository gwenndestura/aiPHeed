"""E87 run (PROTOCOL.md): five mandatory drivers in the regional hunger component, and the five-trigger learner
ablation, on the E84 rows. Run from backend/:  python .../run_e87.py <e84_run_dir>"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
for p in ("E84_Objective_Continuation", "E83_Deep_Reconstruction", "E85_GDELT_Events"):
    sys.path.insert(0, str(EXP / p / "runner"))
import e84_lib as C  # noqa: E402
import run_e83 as R  # noqa: E402

E, L, np, pd = C.E, C.L, C.np, C.pd
from scipy.stats import norm  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402

E87 = HERE.parent
FISH = E87 / "data_derived" / "fishkill_events.csv"
DRIVERS = {
    "MKT": ["F_now", "rice_yoy_now", "comp_F_hat"],
    "EMP": ["ur_last", "ur_yoy", "under_last"],
    "CLIM": ["tc_count", "tc_max_signal", "enso"],
    "OFW": ["remit_usd_yoy", "fx_yoy"],
    "FISH": ["fk_reported", "fk_events", "fish_yoy", "aqua_yoy"],
}
FIVE = {"market": DRIVERS["MKT"] + ["F_last", "gap_now", "mom3", "rice_whsl_yoy", "comp_G_hat"],
        "employment": ["ur_last", "ur_yoy", "under_last"],
        "climate": ["tc_count", "tc_max_signal", "tc_severe", "enso", "palay_yoy", "corn_yoy"],
        "ofw_remittance": ["remit_usd_yoy", "fx_yoy"],
        "fish_kill": ["fk_reported", "fk_events", "fk_prov_reported", "fish_yoy", "aqua_yoy"]}


def fish_features(origins) -> pd.DataFrame:
    f = pd.read_csv(FISH, dtype={"province_code": str})
    f["ts"] = pd.to_datetime(f["first_report_ph"])
    f["q"] = f["ts"].dt.year * 4 + (f["ts"].dt.month - 1) // 3
    rows = []
    for t in origins:
        cur = f[(f["q"] == t) & (f["ts"] < L.origin(t))]
        rep = cur[cur["kind"] == "reported_kill"]
        for p in L.PROVS:
            rows.append({"t": t, "province_code": p, "fk_reported": float(len(rep)), "fk_events": float(len(cur)),
                         "fk_prov_reported": float((rep["province_code"] == p).sum())})
    return pd.DataFrame(rows)


def regional(X: pd.DataFrame) -> pd.DataFrame:
    cols = sorted({c for v in DRIVERS.values() for c in v} | {"H_last"})
    return X.groupby("t")[[c for c in cols if c in X]].mean()


def hunger_p(reg, d, t, k, cols):
    hq_cut = L.h_quarters(d.cut(t)).set_index("q")["H"]
    hq = L.h_quarters(d.cut(t)).sort_values("q")
    qq, hh = hq["q"].to_numpy(), hq["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    s_rw, H_last = sig * math.sqrt(max(t + k - int(qq[-1]), 1)), float(hh[-1])
    th = L.e40_spec()["H"]
    tr = [(tp, hq_cut[tp + k]) for tp in reg.index if tp + k <= t - 1 and (tp + k) in hq_cut.index]
    if not cols or len(tr) < 8:
        return float(1 - norm.cdf((th - H_last) / s_rw)), H_last, False
    T = pd.DataFrame(tr, columns=["t", "y"])
    use = ["H_last"] + cols
    Z = reg.loc[T["t"], use].astype(float)
    ok = Z["H_last"].notna().to_numpy()
    Z, T = Z[ok], T[ok]
    keep = ["H_last"] + [c for c in cols if c in Z and Z[c].notna().all() and Z[c].std() > 0 and pd.notna(reg.loc[t, c])]
    if len(T) < 8:
        return float(1 - norm.cdf((th - H_last) / s_rw)), H_last, False
    mu, sd = Z[keep].mean(), Z[keep].std(ddof=0).replace(0, 1)
    m = Ridge(alpha=1.0).fit((Z[keep] - mu) / sd, T["y"])
    rmse = float(np.sqrt(np.mean((m.predict((Z[keep] - mu) / sd) - T["y"]) ** 2)))
    x = reg.loc[[t], keep].astype(float).copy()
    x["H_last"] = H_last
    Hh = float(m.predict((x[keep] - mu) / sd)[0])
    return float(1 - norm.cdf((th - Hh) / max(s_rw, rmse))), Hh, True


def run(e84: Path, k: int, d):
    P = pd.read_csv(e84 / f"predictions_k{k}.csv", dtype={"province_code": str})
    X = pd.read_csv(e84 / f"features_k{k}.csv", dtype={"province_code": str})
    X = X.merge(fish_features(sorted(X["t"].unique())), on=["t", "province_code"], how="left")
    reg = regional(X)
    arms = {"HUN-RW": []} | {f"HUN-{g}": DRIVERS[g] for g in DRIVERS} | {"HUN-ALL5": sorted({c for v in DRIVERS.values() for c in v})}
    add, hun = [], []
    for t in sorted(P["t"].unique()):
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        tr = E.pairs(X, d, t, k)
        row = {}
        for a, cols in arms.items():
            ph, Hh, fitted = hunger_p(reg, d, t, k, cols)
            row[a] = (ph, Hh, fitted)
            hun.append({"t": t, "arm": a, "p_hunger": ph, "H_hat": Hh, "fitted": fitted})
        learn = {}
        for kind in ("LR", "GB"):
            allc = [c for g in FIVE.values() for c in g]
            learn[f"F5-{kind}"] = R.fit_predict(kind, allc, tr, te)
            for g, cols in FIVE.items():
                learn[f"F5only-{g}-{kind}"] = R.fit_predict(kind, cols, tr, te)
                learn[f"F5drop-{g}-{kind}"] = R.fit_predict(kind, [c for gg, cc in FIVE.items() if gg != g for c in cc], tr, te)
        for i, p in enumerate(L.PROVS):
            pp = te["comp_p_price"].iloc[i]
            r = {"t": t, "province_code": p}
            for a in arms:
                r[a] = row[a][0] * pp if pd.notna(pp) else np.nan
            for a, v in learn.items():
                r[a] = np.nan if v is None else v[i]
            add.append(r)
    return P.merge(pd.DataFrame(add), on=["t", "province_code"], how="left"), pd.DataFrame(hun), X


def hunger_scorecard(H, d, k):
    hq = L.h_quarters(d).set_index("q")["H"]
    out = {}
    for a, g in H.groupby("arm"):
        g = g.assign(q=g["t"] + k)
        g = g[g["q"].isin(hq.index) & (g["q"] >= E.EVAL_FROM)]
        y = (g["q"].map(hq) > 11.3).astype(int)
        m = E.metrics(y, (g["p_hunger"] >= 0.5).astype(int), g["p_hunger"])
        m["mae"] = float((g["q"].map(hq) - g["H_hat"]).abs().mean())
        m["fitted_share"] = float(g["fitted"].mean())
        out[a] = m
    return out


if __name__ == "__main__":
    e84 = Path(sys.argv[1])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E87 / "runs" / stamp
    out.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    arms = ["HUN-RW", "HUN-MKT", "HUN-EMP", "HUN-CLIM", "HUN-OFW", "HUN-FISH", "HUN-ALL5"]
    R.PRIMARY[:] = [f"S-{a}" for a in arms]
    summary = {"stamp": stamp, "protocol_sha256": (E87 / "PROTOCOL.sha256").read_text().split()[0], "leads": {}}
    for k in (1, 2, 3):
        P, H, X = run(e84, k, d)
        P.to_csv(out / f"predictions_k{k}.csv", index=False)
        H.to_csv(out / f"hunger_k{k}.csv", index=False)
        res, tests = R.evaluate(P.rename(columns={c: c.replace("HUN-", "S-HUN-") for c in arms}).rename(
            columns={f"S-HUN-{x}": f"S-HUN-{x}" for x in []}))
        resP = {a: res[f"S-{a}"] for a in arms}
        pd_tests = {}
        for a in arms[1:]:
            D = P[P[a].notna() & P["HUN-RW"].notna()]
            g = D.assign(da=(D["HUN-RW"] - D["y"]) ** 2 - (D[a] - D["y"]) ** 2).groupby("target_q")["da"].mean()
            pd_tests[a] = E.sign_flip(g.to_numpy())
        learners = {c: res[c]["issued_rows"] for c in P.columns if c.startswith("F5") and c in res}
        summary["leads"][k] = {"T43": {a: resP[a]["all_rows_unissued_wrong"] for a in arms},
                               "T43_issued": {a: resP[a]["issued_rows"] for a in arms},
                               "vs_RW_paired_brier": pd_tests, "hunger_scorecard": hunger_scorecard(H, d, k),
                               "learners_issued": learners}
        print(f"k={k}")
        for a in arms:
            m, mi = resP[a]["all_rows_unissued_wrong"], resP[a]["issued_rows"]
            hs = summary["leads"][k]["hunger_scorecard"][a]
            t = pd_tests.get(a, {})
            print(f"  {a:9s} T43 acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} recH={m['recall_HIGH'] or 0:.2f} "
                  f"brier={m['brier']:.3f} | issued {mi['issued']} acc={mi['accuracy'] or 0:.3f} || H-BIN acc={hs['accuracy']:.3f} "
                  f"mae={hs['mae']:.2f} fitted={hs['fitted_share']:.2f} | vsRW gain={t.get('mean_gain', 0):+.4f} p={t.get('p_one_sided', float('nan')):.3f}",
                  flush=True)
        for kind in ("LR", "GB"):
            print(f"  learners {kind}: " + "; ".join(f"{c.replace('-' + kind, '')} {v['issued']}/{v['accuracy'] or 0:.2f}/{v.get('brier', float('nan')):.3f}"
                                                   for c, v in learners.items() if c.endswith(kind)), flush=True)
    (out / "metrics.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(out)
