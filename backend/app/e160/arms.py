"""
E160 arms, validation, leakage check, live 2027-Q1 and LGU-v2, per docs/e160/CRITERIA.md (fixed before results).

    python -m app.e160.arms eval | live
"""
from __future__ import annotations

import json
import sys
import warnings
from itertools import combinations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm, spearmanr

from app.e145 import lgu as LGU
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e158 import model as E8
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e160" / "out"
RQ_INV = {v: k for k, v in M8.RQ.items()}
NEW = ["RP", "OH", "RP_R", "OH_R"]
ALL = ["E158", "PERS"] + NEW
SHARED = 0.726
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


# ---------- anchors ----------
class Cache:
    """Hier2 fits keyed by the set of released rounds; own-history moments per fit."""

    def __init__(self, S):
        self.S, self.h = S, {}

    def get(self, i):
        rel = tuple(M.released(i, Pv.ROUNDS))
        assert all(M8.RQ[s] + M8.Pn.ANCHOR_LAG <= i for s in rel)
        if rel not in self.h:
            hp = Pv.Hier2().fit(self.S, list(rel))
            b = hp.b
            pairs = [x * y for _, g in b.groupby("key") for k, x in enumerate(g["rel"].values) for y in g["rel"].values[k + 1:]]
            tot = float(np.mean(b["rel"] ** 2 - b["se_y"] ** 2))
            tau2 = max(0.005, float(np.mean(pairs))) if pairs else max(0.005, 0.5 * tot)
            sig2 = max(0.0, tot - tau2)
            own = {}
            for key, g in b.groupby("key"):
                v = g["se_y"].values ** 2 + sig2
                pm = np.sum(g["rel"].values / v) / np.sum(1 / v)
                own[key] = (pm, tau2 / (tau2 + 1 / np.sum(1 / v)))
            self.h[rel] = (hp, own, rel)
        return self.h[rel]


def anchors(C: Cache, d: pd.DataFrame) -> pd.DataFrame:
    rp, oh, used = [], [], []
    for r in d[["key", "i", "y_anchor", "rq_anchor"]].itertuples(index=False):
        hp, own, rel = C.get(int(r.i))
        s = RQ_INV[int(r.rq_anchor)]
        assert s in rel, "anchor round not released"
        rp.append(r.y_anchor - hp.N[s] + hp.last_n)
        pm, w = own.get(r.key, (0.0, 0.0))
        oh.append(hp.last_n + w * pm)
        used.append(max(M8.RQ[x] for x in rel))
    return pd.DataFrame({"a_RP": rp, "a_OH": oh, "last_round_rq": used}, index=d.index)


def fit_arms(C, tr, te):
    """Returns mu and probability per new arm for te."""
    A_tr, A_te = anchors(C, tr), anchors(C, te)
    o = {}
    for a in ("RP", "OH"):
        e = tr["y_true"].values - A_tr[f"a_{a}"].values
        sd = float(np.sqrt(np.mean(e ** 2)))
        mu = A_te[f"a_{a}"].values
        o[a] = (mu, norm.cdf(mu / sd), np.full(len(mu), 1.645 * sd), np.full(len(mu), sd))
        m = Pv.Res2(E8.COLS).fit(tr.assign(e=e))
        mu2 = mu + m.predict(te)
        s2, half, _ = m.scale(te["gap_q"].values)
        o[f"{a}_R"] = (mu2, norm.cdf(mu2 / s2), half, s2)
    return o, A_te


# ---------- validation ----------
def task(survey, lead, H, corrupt=False):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if not rel:
        return None
    if corrupt:
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
    C = Cache(S)
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    o, A = fit_arms(C, tr, te)
    out = te[["key", "province", "region", "survey", "lead", "gap_q"]].copy()
    out["last_round_rq"] = A["last_round_rq"].values
    for a, (mu, p, half, sd) in o.items():
        out[f"mu_{a}"], out[a], out[f"half_{a}"] = mu, p, half
    out["corrupt"] = corrupt
    return out


def conc(P, arms, rng, n=2000):
    cl = P["cluster"].unique()
    by = {c: P[P["cluster"] == c] for c in cl}
    bs = {a: [] for a in arms}
    for _ in range(n):
        S = pd.concat([by[c] for c in rng.choice(cl, len(cl))])
        for a in arms:
            bs[a].append(S[a].mean())
    return {a: {"est": round(float(P[a].mean()), 3), "ci95": [round(float(np.percentile(bs[a], 2.5)), 3), round(float(np.percentile(bs[a], 97.5)), 3)]} for a in arms}


def ranking(x, arms):
    rows = []
    for (s, r), g in x.groupby(["survey", "region"]):
        for a, b in combinations(g.index, 2):
            dy = x.at[a, "y_true"] - x.at[b, "y_true"]
            if dy == 0:
                continue
            o = {"cluster": f"{s}|{r}", "gap_pts": abs(pct(x.at[a, "y_true"]) - pct(x.at[b, "y_true"]))}
            for k in arms:
                d = x.at[a, f"mu_{k}"] - x.at[b, f"mu_{k}"]
                o[k] = 0.5 if d == 0 else float(np.sign(d) == np.sign(dy))
            rows.append(o)
    P = pd.DataFrame(rows)
    rng = np.random.default_rng(159)
    c = conc(P, arms, rng)
    cb = conc(P[P["gap_pts"] >= 5], arms, rng)
    sp = {s: {k: round(float(spearmanr(g[f"mu_{k}"], g["y_true"]).correlation), 3) for k in arms} for s, g in x.groupby("survey")}
    top, spread = {k: [] for k in arms}, {k: [] for k in arms}
    for _, g in x.groupby(["survey", "region"]):
        if len(g) >= 2:
            so = np.std(pct(g["y_true"]))
            for k in arms:
                spread[k].append(np.std(pct(g[f"mu_{k}"])) / so if so > 0 else np.nan)
        if len(g) >= 3:
            for k in arms:
                top[k].append(int(g[f"mu_{k}"].idxmax() == g["y_true"].idxmax()))
    return {"pairs": int(len(P)), "concordance": c, "concordance_gap5": cb, "spearman": sp,
            "top_hit": {k: f"{sum(v)}/{len(v)}" for k, v in top.items()}, "spread_ratio_median": {k: round(float(np.nanmedian(v)), 2) for k, v in spread.items()}}


def evaluate():
    OUT.mkdir(parents=True, exist_ok=True)
    H = E154.income()
    jobs = [(s, h, False) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in (1, 2, 3, 4)] + [(s, 1, True) for s in ("ENNS2018", "ENNS2019", "ENNS2021")]
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, c) for s, h, c in jobs) if x is not None]
    A = pd.concat(R, ignore_index=True)
    clean, bad = A[~A["corrupt"]].drop(columns="corrupt"), A[A["corrupt"]].drop(columns="corrupt")
    # leakage: corruption of unreleased rounds must not move any forecast
    k = ["key", "survey", "lead"]
    m = clean[clean["lead"] == 1].merge(bad, on=k, suffixes=("", "_c"))
    leak = {a: float(np.max(np.abs(m[f"mu_{a}"] - m[f"mu_{a}_c"]))) for a in NEW}
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    F = G[G["lead"] <= 4].merge(clean.drop(columns=["province", "region", "gap_q"]), on=k, how="inner")
    assert len(F) == len(G[G["lead"] <= 4]), (len(F), len(G[G["lead"] <= 4]))
    F["mu_PERS"] = F["y_anchor"]
    F.to_csv(OUT / "oof_arms.csv", index=False, lineterminator="\n")
    res = {"leakage_max_abs_change": leak, "leads": {}}
    for L in (1, 2, 3, 4):
        x = F[F["lead"] == L].reset_index(drop=True)
        rk = ranking(x, ALL)
        cls = {a: LD.evaluate(x, a, a)["leads"][0] for a in ALL}
        rng = np.random.default_rng(160)
        brier_vs = {a: E7.diff_ci(x, a, "E158", "q_true", rng, n=2000) for a in NEW}
        res["leads"][L] = {"ranking": rk, "class": {a: {kk: cls[a][kk] for kk in ("accuracy", "precision", "high_recall", "low_recall", "f1", "auc", "brier_soft", "error_points", "criteria", "reliable")} for a in ALL},
                           "brier_minus_E158": {a: {"diff": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]} for a, v in brier_vs.items()}}
    l1 = res["leads"][1]
    gates = {}
    for a in ("RP_R", "OH_R"):
        gates[a] = {"G1": l1["ranking"]["concordance"][a]["ci95"][0] > 0.5, "G2": all(v[a] > 0 for v in l1["ranking"]["spearman"].values()), "G3": not (l1["brier_minus_E158"][a]["ci95"][0] > 0), "G4": bool(l1["class"][a]["criteria"]["C3"])}
        gates[a]["all"] = all(gates[a].values())
    ok = [a for a in gates if gates[a]["all"]]
    win = sorted(ok, key=lambda a: (-l1["ranking"]["concordance"][a]["est"], l1["class"][a]["brier_soft"]))[0] if ok else None
    res["gates"], res["adopted"] = gates, win
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print("leakage", leak)
    for L in (1, 2, 3, 4):
        r = res["leads"][L]
        print(f"\nLead {L}")
        print(pd.DataFrame({a: {"acc": r["class"][a]["accuracy"], "brier": r["class"][a]["brier_soft"], "auc": r["class"][a]["auc"], "hr": r["class"][a]["high_recall"], "lr": r["class"][a]["low_recall"], "pts": r["class"][a]["error_points"], "conc": r["ranking"]["concordance"][a]["est"], "conc_ci": r["ranking"]["concordance"][a]["ci95"], "conc5": r["ranking"]["concordance_gap5"][a]["est"], "top": r["ranking"]["top_hit"][a], "spread": r["ranking"]["spread_ratio_median"][a]} for a in ALL}).T.to_string())
        print("spearman", r["ranking"]["spearman"])
        print("brier vs E158", r["brier_minus_E158"])
    print("gates", gates, "adopted", win)


# ---------- live ----------
def lgu_v2(prov: pd.DataFrame, target_quarter: str, tiebreak: str | None) -> pd.DataFrame:
    d = pd.read_csv(LGU.BASE)[["province_name", "lgu_psgc", "lgu_name", "lgu_type", "population_2024", "poverty_incidence_2021", "density_2024", "pct_poverty", "pct_density"]].copy()
    d["vulnerability"] = LGU.W_POVERTY * d["pct_poverty"] + LGU.W_DENSITY * d["pct_density"]
    p = prov.set_index("province")
    d["province_class"] = d["province_name"].map(p["class"])
    d["province_score"] = d["province_name"].map(p["score"])
    d["province_p_high"] = d["province_name"].map(p["p_high"])
    d["tier"] = (d["province_class"] == "HIGH").map({True: 0, False: 1})
    keys = ["tier", "vulnerability"] + ([tiebreak] if tiebreak else [])
    asc = [True, False] + ([False] if tiebreak else [])
    d = d.sort_values(keys, ascending=asc, kind="mergesort").reset_index(drop=True)
    d["priority_rank_in_region"] = np.arange(1, len(d) + 1)
    d["priority_rank_in_province"] = d.groupby("province_name").cumcount() + 1
    d["target_quarter"], d["label"] = target_quarter, LGU.LABEL
    return d


def live():
    from app.e160.trace import build
    S, P, tr, m, te = build()
    ISSUE = qindex("2026-Q4")
    C = Cache(S)
    o, A = fit_arms(C, tr, te)
    base, _ = P.hier.predict(te, te["T"].values)
    mu = base + m.predict(te)
    sd, half, _ = m.scale(te["gap_q"].values)
    o["E158"] = (mu, norm.cdf(mu / sd), half, sd)
    dy = (tr["y_true"] - tr["y_anchor"]).values
    sp = float(np.sqrt(np.mean(dy ** 2)))
    o["PERS"] = (te["y_anchor"].values, norm.cdf(te["y_anchor"].values / sp), np.full(len(te), 1.645 * sp), np.full(len(te), sp))
    res = json.loads((OUT / "results.json").read_text())
    rng = np.random.default_rng(160)
    rows = []
    for a in ALL:
        mu_, p_, h_, s_ = o[a]
        draw = mu_[None, :] + rng.standard_normal((10000, len(te))) * (s_ * np.sqrt(1 - SHARED))[None, :]
        top = np.bincount(draw.argmax(axis=1), minlength=len(te)) / 10000
        for k in range(len(te)):
            rows.append({"arm": a, "province": te["province"].iloc[k], "score": round(float(pct(mu_[k])), 1), "low90": round(float(pct(mu_[k] - h_[k])), 1), "high90": round(float(pct(mu_[k] + h_[k])), 1), "p_high": round(float(p_[k]), 3), "class": "HIGH" if mu_[k] >= 0 else "LOW", "p_highest": round(float(top[k]), 3)})
    Lv = pd.DataFrame(rows)
    Lv.to_csv(OUT / "live_arms_2027-Q1.csv", index=False, lineterminator="\n")
    win = res["adopted"]
    use = Lv[Lv["arm"] == (win or "E158")][["province", "score", "low90", "high90", "p_high", "class", "p_highest"]]
    tq = qlabel(ISSUE + 1)
    old = pd.read_csv(D / "e158" / "out" / "lgu_priority_2027-Q1.csv")
    new = lgu_v2(use, tq, "province_score" if win else None)
    new.to_csv(OUT / "lgu_priority_v2_2027-Q1.csv", index=False, lineterminator="\n")
    o20, n20 = old.head(20), new.head(20)
    ent = n20[~n20["lgu_psgc"].isin(o20["lgu_psgc"])]
    lef = o20[~o20["lgu_psgc"].isin(n20["lgu_psgc"])]
    cmp_ = {"old_top20_by_province": o20["province_name"].value_counts().to_dict(), "new_top20_by_province": n20["province_name"].value_counts().to_dict(),
            "entered": ent[["lgu_name", "province_name", "poverty_incidence_2021", "density_2024", "vulnerability", "priority_rank_in_region"]].round(3).to_dict("records"),
            "left": lef.merge(new[["lgu_psgc", "priority_rank_in_region"]].rename(columns={"priority_rank_in_region": "new_rank"}), on="lgu_psgc")[["lgu_name", "province_name", "poverty_incidence_2021", "density_2024", "vulnerability", "priority_rank_in_region", "new_rank"]].round(3).to_dict("records"),
            "first_rank_by_province_old": old.groupby("province_name")["priority_rank_in_region"].min().to_dict(), "first_rank_by_province_new": new.groupby("province_name")["priority_rank_in_region"].min().to_dict()}
    (OUT / "live.json").write_text(json.dumps({"adopted": win, "province_display_arm": win or "E158", "ranking_validated": bool(win), "arms": rows, "lgu_compare": cmp_}, indent=1, default=float), newline="\n")
    print(Lv.pivot(index="province", columns="arm", values="score").to_string())
    print(Lv.pivot(index="province", columns="arm", values="p_highest").to_string())
    print(json.dumps(cmp_, indent=1, default=float))
    print(new.head(20)[["priority_rank_in_region", "lgu_name", "province_name", "poverty_incidence_2021", "density_2024", "vulnerability"]].round(3).to_string(index=False))


if __name__ == "__main__":
    {"eval": evaluate, "live": live}[sys.argv[1]]()
