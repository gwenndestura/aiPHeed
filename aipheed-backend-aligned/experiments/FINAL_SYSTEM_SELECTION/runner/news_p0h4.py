"""News in the served model (P0H4): with news vs without news vs shuffled-news placebo vs simple baselines, on the
same rows, origins and information cut-offs (Leads 1 and 2 separately).

P0H4 = pi_H4 (latest Balance Luzon reading, pooled-area sigma) x pi_P (one LightGBM across leads). News enters only
pi_P (N1 = FSSI-v3 and the two GDELT columns, U.NEWS_COLS). The no-news arm refits pi_P at every origin without those
columns; each placebo refits it with the news columns permuted across issue dates (within province and lead).
The served predictions are not touched: the real arm is read from FINAL_ARCHITECTURE/out/predictions.csv.

    python news_p0h4.py nonews          # out/p0h4_nonews.csv
    python news_p0h4.py placebo 20      # out/p0h4_placebo.csv (one column per shuffle)
    python news_p0h4.py report          # out/news_p0h4.json
    python news_p0h4.py split           # out/news_p0h4_split.json (FSSI-v3 alone vs the GDELT columns alone)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
OUT = HERE.parent / "out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(EXP / "DASHBOARD_SELECTION" / "runner"))
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import compare as K  # noqa: E402
import run_l2 as RL  # noqa: E402

X, U, FM, L, np, pd = K.X, K.X.U, K.FM, K.L, K.np, K.pd
KEY = ["t", "lead", "province_code"]


def served() -> pd.DataFrame:
    D = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    return D[D["lead"] <= 2][KEY + ["q", "y", "pi_H4", "P0_price", "P0H4_p3", "ALWAYS-LOW_p", "PERSIST-SI_p", "CLIM_p"]]


def run(S: pd.DataFrame, news: bool) -> pd.DataFrame:
    fr = [f for f in (X.forecast_origin(S, t, ("P0",), news) for t in RL._origins()) if f is not None]
    return pd.concat(fr)[KEY + ["P0_price"]]


def phase_nonews():
    U.setup()
    t0 = time.time()
    S = X.add_fe(U.stack(RL._K()))
    A = run(S, False).rename(columns={"P0_price": "P0_price_nonews"})
    A.to_csv(OUT / "p0h4_nonews.csv", index=False, lineterminator="\n")
    print("no-news arm", len(A), "rows", round(time.time() - t0), "s")


def phase_placebo(n: int):
    U.setup()
    S0 = X.add_fe(U.stack(RL._K()))
    rng = np.random.default_rng(2040)
    news = list(U.NEWS_COLS)
    ts = sorted(S0["t"].unique())
    src = S0.set_index(["province_code", "t", "lead"])[news]
    res = None
    for i in range(n):
        mp = dict(zip(ts, rng.permutation(ts)))
        S = S0.copy()
        S[news] = src.reindex(list(zip(S["province_code"], S["t"].map(mp), S["lead"]))).to_numpy()
        A = run(S, True).rename(columns={"P0_price": f"shuf{i}"})
        res = A if res is None else res.merge(A, on=KEY)
        res.to_csv(OUT / "p0h4_placebo.csv", index=False, lineterminator="\n")
        print("shuffle", i, "done", flush=True)


def phase_report():
    U.setup()
    D = served().merge(pd.read_csv(OUT / "p0h4_nonews.csv", dtype={"province_code": str}), on=KEY)
    D["P0H4_nonews"] = D["pi_H4"] * D["P0_price_nonews"]
    P = pd.read_csv(OUT / "p0h4_placebo.csv", dtype={"province_code": str})
    shuf = [c for c in P if c.startswith("shuf")]
    D = D.merge(P, on=KEY, how="left")
    out = {"rows": {}, "leads": {}}
    raw_p = {}
    for k in (1, 2):
        g = D[D["lead"] == k].copy()
        y = g["y"].astype(int).to_numpy()
        arms = {"P0H4 with news (served)": "P0H4_p3", "P0H4 without news": "P0H4_nonews",
                "always-LOW": "ALWAYS-LOW_p", "PERSIST-SI": "PERSIST-SI_p", "climatology": "CLIM_p"}
        res = {n: {kk: v for kk, v in K.metrics(g, c).items() if kk != "acc_by_quarter"} for n, c in arms.items()}
        t = FM.boot_diff(g, (g["P0H4_p3"] - y) ** 2, (g["P0H4_nonews"] - y) ** 2)
        res["brier_with_minus_without"] = {"diff": t["diff"], "ci90": t["ci90"], "p_two": t["p_two"]}
        raw_p[k] = t["p_two"]
        real = float(np.mean((g["P0H4_p3"] - y) ** 2))
        sb = [float(np.mean((g["pi_H4"] * g[c] - y) ** 2)) for c in shuf if g[c].notna().all()]
        sacc = [float(((g["pi_H4"] * g[c] >= .5).astype(int) == y).mean()) for c in shuf if g[c].notna().all()]
        srec = [float(((g["pi_H4"] * g[c] >= .5) & (y == 1)).sum() / max(y.sum(), 1)) for c in shuf if g[c].notna().all()]
        res["placebo"] = {"shuffles": len(sb), "real_brier": real, "shuffle_brier_mean": float(np.mean(sb)),
                          "shuffle_brier_range": [float(np.min(sb)), float(np.max(sb))],
                          "perm_p": float(np.mean([s <= real for s in sb])),
                          "shuffle_acc_mean": float(np.mean(sacc)), "shuffle_recall_mean": float(np.mean(srec))}
        per_q = {}
        for q, h in g.groupby("q"):
            per_q[K.qs(q)] = {"high": int(h["y"].sum()),
                              "with": int(((h["P0H4_p3"] >= .5).astype(int) == h["y"]).sum()),
                              "without": int(((h["P0H4_nonews"] >= .5).astype(int) == h["y"]).sum()), "n": int(len(h))}
        res["per_quarter_correct"] = per_q
        res["rows_where_class_differs"] = int(((g["P0H4_p3"] >= .5) != (g["P0H4_nonews"] >= .5)).sum())
        out["leads"][k] = res
    holm = sorted(raw_p.items(), key=lambda kv: kv[1])
    adj, m = {}, len(holm)
    run_max = 0.0
    for i, (k, p) in enumerate(holm):
        run_max = max(run_max, min(1.0, (m - i) * p))
        adj[k] = run_max
    for k in (1, 2):
        out["leads"][k]["brier_with_minus_without"]["holm_p"] = adj[k]
    FM.write_json(OUT / "news_p0h4.json", out)
    for k in (1, 2):
        r = out["leads"][k]
        print(f"\n== Lead {k}")
        for n in ("P0H4 with news (served)", "P0H4 without news", "always-LOW", "PERSIST-SI", "climatology"):
            m_ = r[n]
            print(f"  {n:26s} acc {m_['accuracy']:15s} bal {m_['balanced']:.3f} P {m_['precision'] if m_['precision'] is None else round(m_['precision'], 2)} "
                  f"R {m_['recall']:14s} Brier {m_['brier']:.4f} onsets {m_['onsets_caught']}")
        print("  with - without Brier", json.dumps(r["brier_with_minus_without"]), "rows differing", r["rows_where_class_differs"])
        print("  placebo", json.dumps(r["placebo"]))


if __name__ == "__main__":
    ph = sys.argv[1]
    if ph == "nonews":
        phase_nonews()
    elif ph == "placebo":
        phase_placebo(int(sys.argv[2]) if len(sys.argv) > 2 else 20)
    elif ph == "report":
        phase_report()
    elif ph == "split":
        phase_split()


def phase_split():
    """Which news columns carry the Lead-1 effect: drop only N1 (FSSI-v3, the NLP index) or only the GDELT columns."""
    U.setup()
    S = X.add_fe(U.stack(RL._K()))
    full = X.base_cols(True)
    orig = X.base_cols
    out = None
    for name, drop in (("no_fssi", ["N1"]), ("no_gdelt", [c for c in U.NEWS_COLS if c != "N1"])):
        X.base_cols = lambda news=True, _d=drop: [c for c in full if c not in _d]
        A = run(S, True).rename(columns={"P0_price": f"P0_price_{name}"})
        out = A if out is None else out.merge(A, on=KEY)
    X.base_cols = orig
    out.to_csv(OUT / "p0h4_news_split.csv", index=False, lineterminator="\n")
    D = served().merge(out, on=KEY).merge(pd.read_csv(OUT / "p0h4_nonews.csv", dtype={"province_code": str}), on=KEY)
    res = {}
    for k in (1, 2):
        g = D[D["lead"] == k]
        y = g["y"].astype(int).to_numpy()
        res[k] = {}
        for name, c in (("full", "P0_price"), ("no_fssi", "P0_price_no_fssi"), ("no_gdelt", "P0_price_no_gdelt"),
                        ("no_news", "P0_price_nonews")):
            p = g["pi_H4"] * g[c]
            m = K.metrics(g.assign(_p=p), "_p")
            t = FM.boot_diff(g, (g["P0H4_p3"] - y) ** 2, (p - y) ** 2)
            res[k][name] = {"accuracy": m["accuracy"], "recall": m["recall"], "brier": m["brier"],
                            "onsets": m["onsets_caught"], "full_minus_this": t["diff"], "ci90": t["ci90"], "p_two": t["p_two"]}
            print(k, name, res[k][name])
    print("news columns:", U.NEWS_COLS)
    FM.write_json(OUT / "news_p0h4_split.json", {"news_cols": list(U.NEWS_COLS), "leads": res})
