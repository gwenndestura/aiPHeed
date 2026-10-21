"""E83 main run (PROTOCOL.md sections 4-6): every arm, Leads 0-3, the news ablation A-F and the driver ablation.

Run from backend/:  python ../aipheed-backend-aligned/experiments/E83_Deep_Reconstruction/runner/run_e83.py
Writes runs/<stamp>/predictions_k{k}.csv, metrics.json and ablation.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e83_lib as E  # noqa: E402

L, K, np, pd = E.L, E.K, E.np, E.pd
sys.path.insert(0, str(E.BACKEND))
os.chdir(E.BACKEND)
from app.news import events as EV  # noqa: E402

TH = L.e40_spec()
FIRST_ORIGIN = L.qi("2021-Q2")
LAST_ORIGIN = L.qi("2026-Q3")
NEWS_V0 = E.DRIVERS["D5_news_v0"]
BASE_GROUPS = ["D1_prices", "D2_climate", "D3_agri_supply", "D4_household_economy", "H_history"]
N_SETS = {"B": NEWS_V0, "C": EV.N1_COLS, "D": EV.N2_COLS, "N3": EV.N3_COLS}


def cols_of(groups):
    return [c for g in groups for c in E.DRIVERS[g]]


def build(d, x, k):
    origins = list(range(FIRST_ORIGIN, LAST_ORIGIN + 1))
    X = E.features(d, x, origins, k)
    n1 = pd.DataFrame([r for t in origins for r in EV.n1_features(t)])
    n2 = pd.DataFrame([r for t in origins for r in EV.n2_features(t)])
    n3 = EV.n3_frame(origins)
    X = X.merge(n1, on=["t", "province_code"], how="left").merge(n2, on=["t", "province_code"], how="left")
    X = X.merge(n3, on=["t", "province_code"], how="left")
    sims = []
    for t in origins:
        s = E.simulate(d.cut(t), t, k)
        for p in L.PROVS:
            v = s.get(p, (np.nan, np.nan, np.nan))
            sims.append({"t": t, "province_code": p, "sim_p": v[0], "sim_p_hunger": v[1], "sim_p_price": v[2]})
    return X.merge(pd.DataFrame(sims), on=["t", "province_code"], how="left")


def learner(kind, cols):
    return (E.GB if kind == "GB" else E.LR)(cols)


def fit_predict(kind, cols, tr, te):
    if not E.eligible(tr):
        return None
    m = learner(kind, cols).fit(tr)
    return m.predict(te)


def run_lead(d, x, k, lab):
    X = build(d, x, k)
    targets = sorted(q for q in lab["q"].unique() if q >= E.EVAL_FROM)
    rows = []
    all_cols = cols_of(BASE_GROUPS) + NEWS_V0
    specs = {
        "B-PSA": ("LR", E.DRIVERS["D1_prices"]), "B-NLP": ("LR", EV.N3_COLS),
        "M-LR-ALL": ("LR", all_cols), "M-GB-ALL": ("GB", all_cols), "M-GB-S": ("GB", all_cols + ["sim_p"]),
    }
    for kind in ("LR", "GB"):
        base = cols_of(BASE_GROUPS)
        specs[f"NA-{kind}"] = (kind, base)
        for n, c in N_SETS.items():
            specs[f"N{n}-{kind}"] = (kind, base + c)
        for g in BASE_GROUPS + ["NEWS"]:
            keep = [gg for gg in BASE_GROUPS if gg != g]
            specs[f"DROP-{g}-{kind}"] = (kind, cols_of(keep) + ([] if g == "NEWS" else NEWS_V0))
            specs[f"ONLY-{g}-{kind}"] = (kind, NEWS_V0 if g == "NEWS" else E.DRIVERS[g])
    for q in targets:
        t = q - k
        if t < FIRST_ORIGIN:
            continue
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        tr = E.pairs(X, d, t, k)
        av = E.available(d, t)
        last = av.sort_values("q").groupby("province_code").last()
        y = lab[lab["q"] == q].set_index("province_code")["y"]
        prev = float(av["y"].mean()) if len(av) else np.nan
        hq = L.h_quarters(d.cut(t)).sort_values("q")
        H_last = float(hq["H"].iloc[-1]) if len(hq) else np.nan
        out = pd.DataFrame({"k": k, "t": t, "origin": str(L.origin(t).date()), "target_q": L.qs(q),
                            "province_code": te["province_code"], "y": [int(y.get(p, -1)) for p in te["province_code"]]})
        out["B-PERSIST"] = [float(last["y"].get(p, np.nan)) for p in te["province_code"]]
        st = (H_last > TH["H"]) & ((te["F_now"] > te["province_code"].map(TH["food"])) |
                                   (te["gap_now"] > te["province_code"].map(TH["gap"])))
        out["B-STATE"] = st.astype(float).where(te["F_now"].notna()).to_numpy()
        out["B-MAJ"] = float(prev >= 0.5) if np.isfinite(prev) else np.nan
        out["B-CLIM"] = prev
        out["B-AH"], out["B-AL"] = 1.0, 0.0
        out["S-SIM"] = te["sim_p"].to_numpy()
        out["n_train"], out["n_train_high"], out["train_q"] = len(tr), int(tr["y"].sum()) if len(tr) else 0, tr["q"].nunique() if len(tr) else 0
        for name, (kind, cols) in specs.items():
            p = fit_predict(kind, cols, tr, te)
            out[name] = p if p is not None else np.nan
        rows.append(out)
    P = pd.concat(rows, ignore_index=True)
    assert (P["y"] >= 0).all()
    return P, X


BASELINES = ["B-PERSIST", "B-STATE", "B-MAJ", "B-CLIM", "B-AH", "B-AL", "B-PSA", "B-NLP"]
PRIMARY = ["S-SIM", "M-LR-ALL", "M-GB-ALL", "M-GB-S"]


def score(P, arm, rows=None, fill_wrong=True):
    D = P if rows is None else P.loc[rows]
    p = D[arm]
    issued = p.notna()
    if fill_wrong:                     # protocol 6.1: an unissued row counts as wrong
        yhat = np.where(issued, (p >= 0.5).astype(int), 1 - D["y"])
        pp = np.where(issued, p.clip(0, 1), 1 - D["y"])
        m = E.metrics(D["y"], yhat, pp)
    else:
        m = E.metrics(D["y"][issued], (p[issued] >= 0.5).astype(int), p[issued].clip(0, 1))
    m["issued"] = int(issued.sum())
    return m


def per_date_brier(P, arm, ref):
    D = P[P[arm].notna() & P[ref].notna()]
    g = D.assign(da=(D[ref] - D["y"]) ** 2 - (D[arm] - D["y"]) ** 2).groupby("target_q")["da"].mean()
    return g.to_numpy()


def evaluate(P):
    res = {}
    arms = [c for c in P.columns if c.startswith(("B-", "S-", "ST-", "M-", "N", "DROP-", "ONLY-", "HYB-"))]
    for a in arms:
        r = {"all_rows_unissued_wrong": score(P, a), "issued_rows": score(P, a, fill_wrong=False)}
        rising = P["B-PERSIST"].eq(0) & P["y"].eq(1)
        if rising.any():
            r["rising_rows"] = score(P, a, rows=rising[rising].index, fill_wrong=False)
        r["by_province"] = {L.NAMES[p]: score(P, a, rows=P.index[P["province_code"] == p], fill_wrong=False)["accuracy"]
                            for p in L.PROVS}
        ci = E.date_bootstrap(P[P[a].notna()].rename(columns={}),
                              lambda s: float(((s[a] >= 0.5).astype(int) == s["y"]).mean()), B=1000)
        r["accuracy_ci95_issued"] = ci
        res[a] = r
    tests = {}
    for a in PRIMARY:
        ps = {}
        for b in ("B-PERSIST", "B-CLIM", "B-AH"):
            diffs = per_date_brier(P, a, b)
            if len(diffs):
                tests[f"{a} vs {b}"] = E.sign_flip(diffs)
                ps[b] = tests[f"{a} vs {b}"]["p_one_sided"]
        if ps:
            for b, ph in E.holm(ps).items():
                tests[f"{a} vs {b}"]["p_holm"] = ph
    return res, tests


def passes(res, tests, arm):
    m = res[arm]["all_rows_unissued_wrong"]
    best_bal = max((res[b]["all_rows_unissued_wrong"]["balanced_accuracy"] or 0) for b in BASELINES if b in res)
    c1 = (m["accuracy"] or 0) > 0.75
    c2 = (m["balanced_accuracy"] or 0) > best_bal
    c3 = all(tests.get(f"{arm} vs {b}", {}).get("mean_gain", -1) > 0 and tests.get(f"{arm} vs {b}", {}).get("p_holm", 1) < 0.10
             for b in ("B-PERSIST", "B-CLIM", "B-AH"))
    c4 = (m["recall_HIGH"] or 0) >= 0.5
    return {"acc_gt_75": c1, "bal_beats_baselines": c2, "brier_beats_sig": c3, "recall_ge_50": c4,
            "PASS": c1 and c2 and c3 and c4, "TARGET_80": c1 and c2 and c3 and c4 and m["accuracy"] >= 0.80}


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E.E83 / "runs" / stamp
    out.mkdir(parents=True, exist_ok=True)
    d, x = E.data()
    lab = E.labels_all(d)
    summary = {"stamp": stamp, "protocol_sha256": (E.E83 / "PROTOCOL.sha256").read_text().split()[0],
               "lead_status": {k: v for k, v in __import__("collections").Counter(
                   json.loads(l)["extraction_status"] for l in EV.LEADS.read_text(encoding="utf-8").splitlines()).items()},
               "leads": {}}
    for k in [int(v) for v in os.getenv("E83_LEADS", ",".join(map(str, E.LEADS))).split(",")]:
        t0 = time.time()
        P, X = run_lead(d, x, k, lab)
        P.to_csv(out / f"predictions_k{k}.csv", index=False)
        X.to_csv(out / f"features_k{k}.csv", index=False)
        res, tests = evaluate(P)
        summary["leads"][k] = {"rows": len(P), "targets": sorted(P["target_q"].unique().tolist()),
                               "prevalence": float(P["y"].mean()), "metrics": res, "tests": tests,
                               "pass": {a: passes(res, tests, a) for a in PRIMARY}}
        print(f"k={k} rows={len(P)} {time.time() - t0:.0f}s", flush=True)
        for a in BASELINES + PRIMARY + ["NA-LR", "NB-LR", "NC-LR", "ND-LR", "NN3-LR", "NA-GB", "NB-GB", "NC-GB", "ND-GB", "NN3-GB"]:
            m, mi = res[a]["all_rows_unissued_wrong"], res[a]["issued_rows"]
            print(f"  {a:10s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} brier={m.get('brier', float('nan')):.3f}"
                  f" | issued {mi['issued']:3d} acc={mi['accuracy'] or 0:.3f} bal={mi['balanced_accuracy'] or 0:.3f}"
                  f" brier={mi.get('brier', float('nan')):.3f} recH={mi['recall_HIGH'] or 0:.2f}", flush=True)
    (out / "metrics.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(out)
