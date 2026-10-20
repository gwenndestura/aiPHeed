"""E73 WS1 (PROTOCOL section 1): independent-reference validation of the served news layer. Run with cwd = backend.

1a trigger counts vs official event measures; 1b bias correction (served FSSI-v3 vs uncorrected vs empirical Bayes)
against the official event composite, plus the volume-artifact check; 1c coverage; 1e regional news value for SWS
hunger at Lead 2. Official measures come from E71 out/labels.csv (PSA CPI, PSA fisheries, PAGASA, LFS, BSP)."""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, ".")
HERE = Path(__file__).resolve().parent
E73 = HERE.parent
sys.path.insert(0, str(E73.parent / "E70_Objectives_Completion" / "runner"))
import e70_metrics as MT  # noqa: E402
from scipy.stats import binomtest, spearmanr  # noqa: E402

from app.news import pipeline_v3 as P  # noqa: E402

np, pd = MT.np, MT.pd
RNG = np.random.default_rng(73)
LAB = pd.read_csv(E73.parent / "E71_Food_Insecurity_Dimensions" / "out" / "labels.csv", dtype={"province_code": str})
Q0, Q1 = P.qi("2021-Q1"), P.qi("2026-Q3")


def boot(df, x, y, B=4000, demean=False):
    d = df.dropna(subset=[x, y]).copy()
    if demean:
        for c in (x, y):
            d[c] = d[c] - d.groupby("province_code")[c].transform("mean")
    qs = d["q"].unique()
    g = {q: d[d["q"] == q] for q in qs}
    est = float(spearmanr(d[x], d[y])[0])
    bs = []
    for _ in range(B):
        s = pd.concat([g[q] for q in RNG.choice(qs, len(qs), replace=True)])
        if s[x].nunique() > 1 and s[y].nunique() > 1:
            bs.append(spearmanr(s[x], s[y])[0])
    return {"n": int(len(d)), "quarters": int(len(qs)), "rho": est, "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}


def boot_diff(df, a, b, y, B=4000):
    d = df.dropna(subset=[a, b, y])
    qs = d["q"].unique()
    g = {q: d[d["q"] == q] for q in qs}
    est = float(spearmanr(d[a], d[y])[0] - spearmanr(d[b], d[y])[0])
    bs = []
    for _ in range(B):
        s = pd.concat([g[q] for q in RNG.choice(qs, len(qs), replace=True)])
        if s[a].nunique() > 1 and s[b].nunique() > 1 and s[y].nunique() > 1:
            bs.append(spearmanr(s[a], s[y])[0] - spearmanr(s[b], s[y])[0])
    return {"diff": est, "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}


def main():
    adm = list(P.admitted())
    rows, nat = [], defaultdict(Counter)
    for t in range(Q0, Q1 + 1):
        arts = [a for a in P.asof(t) if P.qi(a["quarter"]) == t]
        for a in arts:
            nat[t][a["trigger"]] += 1
            nat[t]["_all"] += 1
        for p in P.PROVINCE_CODES:
            f = P.fssi_v3(p, t, arts)
            mine = Counter(a["trigger"] for a in arts if a["province_code"] == p)
            rows.append({"province_code": p, "q": t, "quarter": P.qs(t), "n": f["n"], "fssi": f["fssi"],
                         "mean_intensity": f["mean_intensity"], "bias_weight": f["bias_weight"],
                         **{f"hits_{k}": mine.get(k, 0) for k in P.TRIGGERS}})
    N = pd.DataFrame(rows).merge(LAB[["province_code", "q", "a1", "a2", "a3", "v2", "s1", "FIR71", "ACCESS",
                                      "AVAILABILITY", "STABILITY"]], on=["province_code", "q"], how="left")
    N["neg_v2"] = -N["v2"]
    out = {"articles_admitted": len(adm)}
    # ---- 1a provincial triggers
    a = {"climate_vs_typhoons": boot(N, "hits_climate", "s1"), "climate_vs_typhoons_within": boot(N, "hits_climate", "s1", demean=True),
         "market_vs_food_cpi": boot(N, "hits_market", "a1"), "market_vs_food_cpi_within": boot(N, "hits_market", "a1", demean=True),
         "fish_kill_vs_fish_drop": boot(N, "hits_fish_kill", "neg_v2"), "fish_kill_vs_fish_drop_within": boot(N, "hits_fish_kill", "neg_v2", demean=True)}
    # national triggers at quarter level
    QN = pd.DataFrame([{"q": t, "employment": nat[t]["employment"], "ofw_remittance": nat[t]["ofw_remittance"], "all": nat[t]["_all"]}
                       for t in range(Q0, Q1 + 1)])
    qref = LAB.groupby("q")[["a2", "a3"]].first().reset_index()
    QN = QN.merge(qref, on="q", how="left")
    for k, ref, sign in (("employment", "a2", 1), ("ofw_remittance", "a3", -1)):
        g = QN.dropna(subset=[ref])
        rho = spearmanr(g[k], sign * g[ref])[0] if g[k].nunique() > 1 else float("nan")
        idx = np.arange(len(g))
        bs = [spearmanr(g[k].to_numpy()[i], sign * g[ref].to_numpy()[i])[0] for i in (RNG.choice(idx, len(idx)) for _ in range(4000))
              if g[k].to_numpy()[i].std() > 0 and g[ref].to_numpy()[i].std() > 0]
        a[f"{k}_vs_official"] = {"n": int(len(g)), "rho": float(rho), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}
    for k, v in a.items():
        v["pass"] = v["ci95"][0] > 0
    out["1a"] = a
    # ---- 1b bias correction
    S = N[N["n"] > 0].copy()
    k = statistics.median(S["n"])
    qmean = S.groupby("q")["mean_intensity"].transform("mean")
    S["eb"] = (S["n"] / (S["n"] + k)) * S["mean_intensity"] + (k / (S["n"] + k)) * qmean
    b = {"cells_with_articles": int(len(S)), "k": float(k),
         "served_vs_composite": boot(S, "fssi", "FIR71"), "uncorrected_vs_composite": boot(S, "mean_intensity", "FIR71"),
         "eb_vs_composite": boot(S, "eb", "FIR71"),
         "served_minus_uncorrected": boot_diff(S, "fssi", "mean_intensity", "FIR71"),
         "eb_minus_served": boot_diff(S, "eb", "fssi", "FIR71"), "eb_minus_uncorrected": boot_diff(S, "eb", "mean_intensity", "FIR71"),
         "volume_artifact": {"rho_fssi_vs_n": float(spearmanr(S["fssi"], S["n"])[0]),
                             "rho_uncorrected_vs_n": float(spearmanr(S["mean_intensity"], S["n"])[0]),
                             "rho_bias_weight_vs_n": float(spearmanr(S["bias_weight"], S["n"])[0]),
                             "bias_weight_range": [float(S["bias_weight"].min()), float(S["bias_weight"].max())]}}
    b["served_validated"] = b["served_minus_uncorrected"]["ci95"][0] > 0
    b["eb_adopt"] = b["eb_minus_served"]["ci95"][0] > 0 and b["eb_minus_uncorrected"]["ci95"][0] > 0
    out["1b"] = b
    # ---- 1c coverage
    fil = set("ang mga sa ng na nang para presyo bigas gutom kagutuman tulong magsasaka mangingisda ayuda tumaas bumaba".split())
    import re
    lang = Counter("fil" if len(set(re.findall(r"[a-z]+", x["title"].lower())) & fil) >= 2 else "eng_or_mixed" for x in adm)
    out["1c"] = {"by_province": {P.qs(0) if False else p: int((N["province_code"] == p).mul(N["n"]).sum()) for p in P.PROVINCE_CODES},
                 "national": int(sum(1 for x in adm if not x["province_code"])),
                 "sufficient_cells": int((N["n"] >= P.MIN_ARTICLES).sum()), "cells": int(len(N)),
                 "zero_cells_by_province": N[N["n"] == 0].groupby("province_code").size().to_dict(),
                 "by_trigger": dict(Counter(x["trigger"] for x in adm)), "language": dict(lang),
                 "outlets": len(Counter(x["outlet"] for x in adm))}
    # ---- 1e regional news value for SWS hunger, Lead 2
    r = pd.read_csv("data/inputs/sws_rounds.csv")
    r = r[r["definition_A"].astype(str) == "True"].assign(q=lambda f: f["quarter"].map(P.qi), pub=lambda f: pd.to_datetime(f["published"]))
    Hq = r.groupby("q").agg(H=("H", "mean"), pub=("pub", "max"))
    cnt = QN.set_index("q")["all"]
    pairs = []
    for t in range(Q0, Q1 - 1):
        O = pd.Timestamp(P.origin(t))
        known = Hq[Hq["pub"] < O]
        if not len(known) or (t + 2) not in Hq.index:
            continue
        pairs.append({"t": t, "H_last": float(known.loc[known.index.max(), "H"]), "H_true": float(Hq.loc[t + 2, "H"]),
                      "news": float(cnt.get(t, np.nan)), "target_pub": Hq.loc[t + 2, "pub"], "O": O})
    E = []
    for i, p in enumerate(pairs):
        tr = [x for x in pairs if x["target_pub"] < p["O"]]
        rw = p["H_last"]
        if len(tr) >= 6:
            z = np.array([x["news"] for x in tr])
            mu, sd = z.mean(), z.std() or 1.0
            dz = (z - mu) / sd
            dy = np.array([x["H_true"] - x["H_last"] for x in tr])
            slope = float((dz * dy).sum() / ((dz * dz).sum() or 1.0))
            nw = rw + slope * (p["news"] - mu) / sd
            E.append({"t": P.qs(p["t"]), "target": P.qs(p["t"] + 2), "rw_err": abs(rw - p["H_true"]), "news_err": abs(nw - p["H_true"])})
    E = pd.DataFrame(E)
    wins = int((E["news_err"] < E["rw_err"]).sum())
    losses = int((E["news_err"] > E["rw_err"]).sum())
    out["1e"] = {"quarters": int(len(E)), "mae_rw": float(E["rw_err"].mean()), "mae_rw_plus_news": float(E["news_err"].mean()),
                 "news_better_quarters": wins, "news_worse_quarters": losses,
                 "sign_p": float(binomtest(wins, wins + losses, .5).pvalue) if wins + losses else 1.0, "rows": E.to_dict("records")}
    out["1e"]["pass"] = out["1e"]["mae_rw_plus_news"] < out["1e"]["mae_rw"] and wins > losses and out["1e"]["sign_p"] < 0.05
    (E73 / "out").mkdir(exist_ok=True)
    (E73 / "out" / "news_validation.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "1e"}, indent=1, default=str)[:6000])
    print("1e", {k: v for k, v in out["1e"].items() if k != "rows"})


if __name__ == "__main__":
    main()
