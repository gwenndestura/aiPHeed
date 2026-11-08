"""
E163 candidates C1 (RSS), C2 (RSS + LightGBM residual), C3 (RSS + ridge residual), controls, evaluation and live 2027-Q1,
per docs/e163/CRITERIA.md (fixed before results).

    python -m app.e163.model eval | live
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e158 import model as E8
from app.e160 import arms as A
from app.e162 import rank as R2
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e163" / "out"
CAND = ["C1", "C2", "C3"]
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
QGRID = (0.0, 0.005, 0.01, 0.02, 0.05, 0.1)
GROUPS5 = ["market", "climate", "employment", "remittance", "poverty"]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


# ---------- five-group mapping (news inside groups) ----------
def gmap(c: str) -> str | None:
    if c in ("gap_q", "lead"):
        return None
    for g, cols in M.GROUPS.items():
        if c in cols:
            return g
    if c == "income_growth":
        return "employment"
    if c == "income_rel":
        return "poverty"
    if c in Pv.NEWS_ALL:
        for g in GROUPS5:
            if f"_{g}" in c:
                return g
        return "poverty"          # general food-stress / hunger news = food access = social vulnerability
    if c == "h2":
        return "poverty"
    return None


NEWS_COLS = [c for c in E8.COLS if c in Pv.NEWS_ALL]


# ---------- C1 relative state space ----------
class RSS:
    def __init__(self, hp):
        b = hp.b.copy()
        self.hp = hp
        pairs = [x * y for _, g in b.groupby("key") for k, x in enumerate(g["rel"].values) for y in g["rel"].values[k + 1:]]
        tot = float(np.mean(b["rel"] ** 2 - b["se_y"] ** 2))
        tau2 = max(0.005, float(np.mean(pairs))) if pairs else max(0.005, 0.5 * tot)
        self.sig2 = max(0.0, tot - tau2)
        b["v"] = b["se_y"] ** 2 + self.sig2
        self.obs = {k: g.sort_values("year")[["year", "rel", "v"]].values for k, g in b.groupby("key")}
        km = {k: (float(np.sum(o[:, 1] / o[:, 2]) / np.sum(1 / o[:, 2])), float(1 / np.sum(1 / o[:, 2]))) for k, o in self.obs.items()}
        self.km = km
        self.reg = b.drop_duplicates("key").set_index("key")["region"].to_dict()
        devs, vm = [], []
        for r, ks in pd.Series(self.reg).groupby(lambda k: self.reg[k]):
            ks = list(ks.index)
            if len(ks) >= 2:
                m = np.array([km[k][0] for k in ks])
                devs += list(m - m.mean())
                vm += [km[k][1] for k in ks]
        self.tau2_w = max(0.005, float(np.mean(np.square(devs)) - np.mean(vm))) if devs else 0.005
        allm = np.array([v[0] for v in km.values()])
        self.tau2_all = max(0.005, float(np.var(allm) - np.mean([v[1] for v in km.values()])))
        self.q = self._choose_q()

    def prior(self, key, region):
        others = [k for k, r in self.reg.items() if r == region and k != key]
        pool, t2 = (others, self.tau2_w) if others else ([k for k in self.km if k != key], self.tau2_all)
        w = np.array([1 / (self.km[k][1] + t2) for k in pool])
        m = np.array([self.km[k][0] for k in pool])
        return float(np.sum(w * m) / np.sum(w)), float(t2 + 1 / np.sum(w))

    @staticmethod
    def kalman(o, q, m, v, year):
        t = None
        for yr, y, s in o:
            if t is not None:
                v += q * (yr - t)
            k = v / (v + s)
            m, v, t = m + k * (y - m), (1 - k) * v, yr
        return m, v + (q * max(0.0, year - t) if t is not None else 0.0)

    def _choose_q(self):
        best, bq = np.inf, 0.0
        for q in QGRID:
            ll = 0.0
            for k, o in self.obs.items():
                m0, v0 = self.prior(k, self.reg[k])
                for j in range(1, len(o)):
                    m, v = self.kalman(o[:j], q, m0, v0, o[j, 0])
                    s = v + o[j, 2]
                    ll += 0.5 * (np.log(s) + (o[j, 1] - m) ** 2 / s)
            if ll < best:
                best, bq = ll, q
        return bq

    def predict(self, key, region, T, own=True):
        m0, v0 = self.prior(key, region)
        o = self.obs.get(key) if own else None
        if o is None or not len(o):
            return self.hp.last_n + m0, v0
        m, v = self.kalman(o, self.q, m0, v0, float(T) / 4.0)
        return self.hp.last_n + m, v


class RCache:
    def __init__(self, S):
        self.C, self.r = A.Cache(S), {}

    def get(self, i):
        hp, _, rel = self.C.get(i)
        if rel not in self.r:
            self.r[rel] = RSS(hp)
        return self.r[rel]


def rss_rows(RC, d, own=True):
    mu, var, q = [], [], []
    for r in d[["key", "region", "i", "T"]].itertuples(index=False):
        m = RC.get(int(r.i))
        a, v = m.predict(r.key, r.region, r.T, own)
        mu.append(a)
        var.append(v)
        q.append(m.q)
    return np.array(mu), np.array(var), np.array(q)


# ---------- C3 ridge residual ----------
class RidgeRes:
    ALPHAS = (1.0, 10.0, 100.0, 1000.0)

    def __init__(self, cols):
        self.cols = list(cols)

    def _X(self, d):
        return ((d[self.use_] - self.med_) / self.sd_).fillna(0.0).values

    def fit(self, d):
        d = d.reset_index(drop=True)
        self.use_ = [c for c in self.cols if c in d and d[c].notna().any() and d[c].nunique() > 1]
        self.med_, self.sd_ = d[self.use_].median(), d[self.use_].std().replace(0, 1).fillna(1)
        X, y = self._X(d), d["e"].values
        w = (1.0 / (d["se_true"] ** 2 + 0.05)).values
        folds = list(GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]))
        best = (np.inf, None, None)
        for a in self.ALPHAS:
            pred = np.zeros(len(d))
            for tr, te in folds:
                pred[te] = Ridge(alpha=a).fit(X[tr], y[tr], sample_weight=w[tr]).predict(X[te])
            sse = float(np.sum(w * (y - pred) ** 2))
            if sse < best[0]:
                best = (sse, a, y - pred)
        self.alpha_, self.oof_ = best[1], best[2]
        self.gap_ = d["gap_q"].values.astype(float)
        self.m_ = Ridge(alpha=self.alpha_).fit(X, y, sample_weight=w)
        return self

    def predict(self, X):
        return self.m_.predict(self._X(X))

    scale = Pv.Res2.scale


def shuffle_cols(fr, cols, seed):
    fr = fr.copy()
    r = np.random.default_rng(seed)
    for _, g in fr.groupby(["survey", "lead"]):
        fr.loc[g.index, cols] = fr.loc[r.permutation(g.index.values), cols].values
    return fr


def with_res(model_cls, cols, tr, te, a_tr, a_te):
    m = model_cls(cols).fit(tr.assign(e=tr["y_true"].values - a_tr))
    mu = a_te + m.predict(te)
    sd, half, _ = m.scale(te["gap_q"].values)
    return mu, norm.cdf(mu / sd), half


# ---------- task ----------
def task(survey, lead, H, corrupt=False, controls=False):
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
    RC = RCache(S)
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    a_tr, _, _ = rss_rows(RC, tr)
    a_te, v_te, q_te = rss_rows(RC, te)
    sd1 = float(np.sqrt(np.mean((tr["y_true"].values - a_tr) ** 2)))
    out = te[["key", "survey", "lead"]].copy()
    out["corrupt"], out["q_per_year"], out["var_C1"] = corrupt, q_te, v_te
    out["mu_C1"], out["C1"], out["half_C1"] = a_te, norm.cdf(a_te / sd1), 1.645 * sd1
    a0, _, _ = rss_rows(RC, te, own=False)
    out["mu_C1_noown"], out["C1_noown"], out["half_C1_noown"] = a0, norm.cdf(a0 / sd1), 1.645 * sd1
    for name, cls in (("C2", Pv.Res2), ("C3", RidgeRes)):
        out[f"mu_{name}"], out[name], out[f"half_{name}"] = with_res(cls, E8.COLS, tr, te, a_tr, a_te)
    if controls and not corrupt:
        for g in GROUPS5:
            gc = [c for c in E8.COLS if gmap(c) == g]
            keep = [c for c in E8.COLS if c not in gc]
            out[f"mu_C3_drop_{g}"], out[f"C3_drop_{g}"], _ = with_res(RidgeRes, keep, tr, te, a_tr, a_te)
            ps = [with_res(RidgeRes, E8.COLS, shuffle_cols(tr, gc, s), shuffle_cols(te, gc, s), a_tr, a_te)[1] for s in (1, 2, 3)]
            out[f"C3_shuf_{g}"] = np.mean(ps, axis=0)
        keep = [c for c in E8.COLS if c not in NEWS_COLS]
        out["mu_C3_nonews"], out["C3_nonews"], _ = with_res(RidgeRes, keep, tr, te, a_tr, a_te)
        out["C3_shufnews"] = np.mean([with_res(RidgeRes, E8.COLS, shuffle_cols(tr, NEWS_COLS, s), shuffle_cols(te, NEWS_COLS, s), a_tr, a_te)[1] for s in (1, 2, 3)], axis=0)
        allc = [c for c in E8.COLS if gmap(c) is not None]
        for name, cls in (("C2", Pv.Res2), ("C3", RidgeRes)):
            out[f"{name}_shufall"] = np.mean([with_res(cls, E8.COLS, shuffle_cols(tr, allc, s), shuffle_cols(te, allc, s), a_tr, a_te)[1] for s in (1, 2, 3)], axis=0)
    return out


# ---------- evaluation ----------
def cls_metrics(g, a, rng):
    y = g["y_high"].values == 1
    p = g[a].values >= .5
    tp, fp, fn, tn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
    mu, yt = g[f"mu_{a}"].values, g["y_true"].values
    sl = float(np.polyfit(mu, yt, 1)[0]) if np.std(mu) > 0 else np.nan
    e = pct(mu) - pct(yt)
    L = LD.evaluate(g, a, a)["leads"][0]
    return {"accuracy": L["accuracy"], "balanced_accuracy": L["balanced_accuracy"], "high_precision": round(tp / max(1, tp + fp), 3), "high_recall": L["high_recall"], "low_precision": round(tn / max(1, tn + fn), 3), "low_recall": L["low_recall"],
            "f1": L["f1"], "auc": L["auc"], "brier": L["brier_soft"], "calibration_slope": round(sl, 3), "calibration_slope_ci95": L["calibration_slope_ci95"], "mae_pts": round(float(np.mean(np.abs(e))), 2), "mean_signed_pts": round(float(np.mean(e)), 2),
            "false_alarm_rate": round(fp / max(1, fp + tn), 3), "missed_high_rate": round(fn / max(1, fn + tp), 3), "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "criteria": L["criteria"], "reliable": L["reliable"]}


def bias(x, a, rng):
    e = pd.Series(pct(x[f"mu_{a}"]) - pct(x["y_true"]))
    out = {}
    for name, mk in [("overall", np.ones(len(x), bool)), *[(f"island:{k}", (x["island"] == k).values) for k in ("Luzon", "Visayas", "Mindanao")], ("observed:HIGH", (x["y_high"] == 1).values), ("observed:LOW", (x["y_high"] == 0).values)]:
        ev, rg = e.values[mk], x["region"].values[mk]
        gs = list(pd.Series(range(len(ev))).groupby(rg).indices.values())
        v = [np.mean(ev[np.concatenate([gs[j] for j in rng.integers(0, len(gs), len(gs))])]) for _ in range(2000)]
        ci = [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
        out[name] = {"n": int(mk.sum()), "mean": round(float(np.mean(ev)), 2), "ci95": ci, "BIAS": bool((ci[0] > 0 or ci[1] < 0) and abs(np.mean(ev)) > 3)}
    out["calabarzon_rows"] = {f"{p}|{s}": round(float(v), 1) for p, s, v in zip(x["province"], x["survey"], e) if p in CAL}
    return out


def evaluate():
    OUT.mkdir(parents=True, exist_ok=True)
    H = E154.income()
    jobs = [(s, h, False, h == 1) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in (1, 2, 3, 4)] + [(s, 1, True, False) for s in ("ENNS2018", "ENNS2019", "ENNS2021")]
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, c, k) for s, h, c, k in jobs) if x is not None]
    Al = pd.concat(R, ignore_index=True)
    clean, bad = Al[~Al["corrupt"]].drop(columns="corrupt"), Al[Al["corrupt"]].drop(columns="corrupt")
    k = ["key", "survey", "lead"]
    mm = clean[clean["lead"] == 1].merge(bad, on=k, suffixes=("", "_c"))
    res = {"leakage_max_abs_change": {a: float(np.max(np.abs(mm[f"mu_{a}"] - mm[f"mu_{a}_c"]))) for a in CAND + ["C1_noown"]}}
    G = pd.read_csv(D / "e160" / "out" / "oof_arms.csv")
    F = G[G["lead"] <= 4].merge(clean, on=k, how="inner")
    assert len(F) == len(G[G["lead"] <= 4])
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(163)
    arms = ["E158"] + CAND + ["C1_noown"]
    res["leads"] = {}
    for L in (1, 2, 3, 4):
        x = F[F["lead"] == L].reset_index(drop=True)
        res["leads"][L] = {"class": {a: cls_metrics(x, a, rng) for a in arms}, "brier_minus_E158": {a: {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]} for a in CAND for d in [E7.diff_ci(x, a, "E158", "q_true", rng, n=2000)]}}
        P, rk = R2.rank_measures(x, arms)
        sp = {}
        for a in arms:
            r_ = []
            for _, g in x.groupby(["survey", "region"]):
                if len(g) >= 2 and np.std(pct(g["y_true"])) > 0:
                    r_.append(np.std(pct(g[f"mu_{a}"])) / np.std(pct(g["y_true"])))
            sp[a] = round(float(np.median(r_)), 2)
        rk["spread_ratio_median"] = sp
        res["leads"][L]["ranking"] = rk
        if L == 1:
            x1, P1 = x, P
    # province-evidence held-out control (S7)
    Q = P1[["cluster"]].copy()
    for a in CAND:
        Q[a + "_diff"] = P1[a] - P1["C1_noown"]
    res["own_evidence_control"] = R2.boot(Q, [a + "_diff" for a in CAND], np.random.default_rng(162))
    # group, NLP, all-shuffle controls
    ctl = {}
    for g in GROUPS5:
        for kind in ("drop", "shuf"):
            c = f"C3_{kind}_{g}"
            d = E7.diff_ci(x1, "C3", c, "q_true", rng, n=2000)
            ctl[c] = {"brier": round(float(np.mean((x1[c] - x1["q_true"]) ** 2)), 4), "C3_minus_this": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]], "n_cols": len([cc for cc in E8.COLS if gmap(cc) == g])}
    for c in ("C3_nonews", "C3_shufnews", "C2_shufall", "C3_shufall"):
        base = c.split("_")[0]
        d = E7.diff_ci(x1, base, c, "q_true", rng, n=2000)
        ctl[c] = {"brier": round(float(np.mean((x1[c] - x1["q_true"]) ** 2)), 4), f"{base}_minus_this": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]}
    res["controls"] = ctl
    res["group_columns"] = {g: [c for c in E8.COLS if gmap(c) == g] for g in GROUPS5}
    res["group_coverage_train_lead1"] = None
    # nested selection by Brier
    picks, hits = {}, []
    for s in sorted(x1["survey"].unique()):
        trn, tst = x1[x1["survey"] != s], x1[x1["survey"] == s]
        best = min(["E158"] + CAND, key=lambda a: float(np.mean((trn[a] - trn["q_true"]) ** 2)))
        picks[s] = best
        hits += list(((tst[best] >= .5) == (tst["y_high"] == 1)).values)
    res["nested"] = {"picks": picks, "nested_accuracy": round(float(np.mean(hits)), 3)}
    res["bias"] = {a: bias(x1, a, np.random.default_rng(161)) for a in ["E158"] + CAND}
    # gates
    e = res["leads"][1]
    base = e["class"]["E158"]
    gates = {}
    for a in CAND:
        c, r = e["class"][a], e["ranking"]
        b = res["bias"][a]
        gates[a] = {"S1": c["brier"] <= base["brier"] and not (e["brier_minus_E158"][a]["ci95"][0] > 0),
                    "S2": (c["calibration_slope_ci95"][0] <= 1 <= c["calibration_slope_ci95"][1]) or abs(c["calibration_slope"] - 1) < abs(base["calibration_slope"] - 1),
                    "S3": c["confusion"]["fp"] <= base["confusion"]["fp"] + 2 and c["confusion"]["fn"] <= base["confusion"]["fn"],
                    "S4": r["concordance"][a]["est"] > r["concordance"]["E158"]["est"] and r["concordance"][a]["ci95"][0] > 0.5,
                    "S5": abs(b["overall"]["mean"]) <= abs(res["bias"]["E158"]["overall"]["mean"]) + 1 and b["island:Luzon"]["mean"] <= res["bias"]["E158"]["island:Luzon"]["mean"] and not any(b[f"island:{k}"]["BIAS"] and not res["bias"]["E158"][f"island:{k}"]["BIAS"] for k in ("Luzon", "Visayas", "Mindanao")),
                    "S6": all(v[a] >= 0.5 for v in r["per_round_concordance"].values()),
                    "S7": res["own_evidence_control"][a + "_diff"]["ci95"][0] > 0}
        gates[a]["all"] = all(gates[a].values())
    ok = [a for a in CAND if gates[a]["all"]]
    res["gates"] = gates
    res["adopted"] = min(ok, key=lambda a: e["class"][a]["brier"]) if ok else None
    res["groups_contribute"] = {a: bool(ctl[f"{a}_shufall"]["ci95"][1] < 0) for a in ("C2", "C3")}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps({k: res[k] for k in ("leakage_max_abs_change", "gates", "adopted", "groups_contribute", "nested", "own_evidence_control")}, indent=1, default=float))
    for L in (1, 2, 3, 4):
        r = res["leads"][L]
        print(f"\nLead {L}")
        print(pd.DataFrame({a: {kk: r["class"][a][kk] for kk in ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_recall", "f1", "auc", "brier", "calibration_slope", "mae_pts", "mean_signed_pts", "false_alarm_rate", "missed_high_rate")} | {"conc": r["ranking"]["concordance"][a]["est"], "conc_lo": r["ranking"]["concordance"][a]["ci95"][0], "pos_err": r["ranking"]["position_error"][a], "spread": r["ranking"]["spread_ratio_median"][a], "C1-6": "".join(str(int(v)) for v in r["class"][a]["criteria"].values())} for a in arms}).T.to_string())
        print("brier vs E158", r["brier_minus_E158"])
        print("per round conc", r["ranking"]["per_round_concordance"])
    print(json.dumps(ctl, indent=1))
    print(json.dumps(res["bias"], indent=1))


# ---------- live ----------
def live():
    from app.e160.trace import build
    S, P, tr, m, te = build()
    RC = RCache(S)
    a_tr, _, _ = rss_rows(RC, tr)
    a_te, v_te, q_te = rss_rows(RC, te)
    sd1 = float(np.sqrt(np.mean((tr["y_true"].values - a_tr) ** 2)))
    arms = {"C1": (a_te, norm.cdf(a_te / sd1), np.full(len(te), 1.645 * sd1))}
    for name, cls in (("C2", Pv.Res2), ("C3", RidgeRes)):
        arms[name] = with_res(cls, E8.COLS, tr, te, a_tr, a_te)
    res = json.loads((OUT / "results.json").read_text())
    E = pd.read_csv(D / "e160" / "out" / "live_arms_2027-Q1.csv")
    e158 = E[E["arm"] == "E158"].set_index("province")
    rng = np.random.default_rng(163)
    rows = []
    for a, (mu, p, half) in arms.items():
        draw = mu[None, :] + rng.standard_normal((10000, len(te))) * np.sqrt(v_te)[None, :]
        top = np.bincount(draw.argmax(axis=1), minlength=len(te)) / 10000
        for k in range(len(te)):
            rows.append({"arm": a, "province": te["province"].iloc[k], "score": round(float(pct(mu[k])), 1), "low90": round(float(pct(mu[k] - half[k])), 1), "high90": round(float(pct(mu[k] + half[k])), 1), "p_high": round(float(p[k]), 3), "class": "HIGH" if mu[k] >= 0 else "LOW", "p_highest": round(float(top[k]), 3)})
    for prov, r in e158.iterrows():
        rows.append({"arm": "E158", "province": prov, **{c: r[c] for c in ("score", "low90", "high90", "p_high", "class", "p_highest")}})
    Lv = pd.DataFrame(rows)
    Lv.to_csv(OUT / "live_2027-Q1.csv", index=False, lineterminator="\n")
    win = res["adopted"]
    rk = res["leads"]["1"]["ranking"] if "1" in res["leads"] else res["leads"][1]["ranking"]
    out = {"q_per_year": float(q_te[0]), "rss_prior_and_state": [{"province": te["province"].iloc[k], "rel_state": round(float(a_te[k] - RC.get(int(te["i"].iloc[k])).hp.last_n), 3), "state_var": round(float(v_te[k]), 4)} for k in range(len(te))], "adopted": win}
    if win:
        w = Lv[Lv["arm"] == win].set_index("province")
        lead_p = w["p_highest"].idxmax()
        g = res["gates"][win]
        out["display"] = {"arm": win, "most_likely_highest": lead_p, "p": float(w.at[lead_p, "p_highest"]), "rank_first_shown": bool(g["S4"] and g["S6"] and g["S7"] and w.at[lead_p, "p_highest"] >= 0.80)}
    (OUT / "live.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(Lv.pivot(index="province", columns="arm", values="score").to_string())
    print(Lv.pivot(index="province", columns="arm", values="p_highest").to_string())
    print(Lv.pivot(index="province", columns="arm", values="p_high").to_string())
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"eval": evaluate, "live": live}[sys.argv[1]]()
