"""Addendum 4 (ADDENDUM_4_ONE_MODEL.md): ONE unified LightGBM on the combined target T43c across every lead, with
all 12 families, lead, world prices and hunger-onset inputs; variant U-ONE-P adds the structural offset
logit(pi_H x STRUCT_k), U-ONE-0 does not.

    python a4.py audit
    python a4.py score
    python a4.py replay
"""
from __future__ import annotations

import dataclasses
import json
import sys
import time

import l2_lib as X
import run_l2 as RL
import a2 as A2
import a3 as A3

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
OUT = X.OUT
ONSET = ["h_last", "true_horizon", "O_rice_yoy", "O_food_yoy"]
MONO = {"A1_food", "A1_gap", "A_mom", "H1", "h_last"}
VARIANTS = ("U-ONE-P", "U-ONE-0")


def _check():
    A3._check()
    want = (X.HERE / "ADDENDUM_4_SHA256.txt").read_text().strip()
    assert FM.sha256(X.L2 / "ADDENDUM_4_ONE_MODEL.md") == want, "addendum 4 changed after freezing"


def cols() -> list[str]:
    return X.base_cols(True) + ONSET


def grid() -> list[dict]:
    return X.uni_grid() + X.reg_grid()


def add_onset(S: pd.DataFrame, cpi: pd.DataFrame | None = None, hunger: dict | None = None) -> pd.DataFrame:
    """Region IV-A rice and food CPI YoY at m0 (2021+), and optionally a sample-a hunger term replacing H1."""
    cpi = A3.region_cpi() if cpi is None else cpi
    S = S.copy()
    v = {int(t): A3._cpi_at(cpi[cpi.index <= L.m0_of(int(t))], L.m0_of(int(t)), "a") for t in S["t"].unique()}
    S["O_rice_yoy"] = [v[int(t)][0] for t in S["t"]]
    S["O_food_yoy"] = [v[int(t)][1] for t in S["t"]]
    S["true_horizon"] = S["true_horizon"].astype(float)
    if hunger:
        S["H1"] = [hunger.get((int(t), int(k)), h) for t, k, h in zip(S["t"], S["lead"], S["H1"])]
    return S


def offset(rows: pd.DataFrame, price_fit: pd.DataFrame) -> np.ndarray:
    p = rows["H1"].to_numpy(float) * X.struct_prior(rows, price_fit)
    return B.logit(np.clip(p, 0.01, 0.99))


class One:
    def __init__(self, cfg: dict, use_offset: bool):
        self.cfg, self.use_offset = cfg, use_offset
        self.m = self.price_fit = None

    def fit(self, tr: pd.DataFrame, price_fit: pd.DataFrame):
        import lightgbm as lgb
        self.price_fit = price_fit
        y = tr["y"].to_numpy(int)
        if len(set(y.tolist())) < 2:
            return self
        c = self.cfg
        self.m = lgb.LGBMClassifier(objective="binary", class_weight=c["cw"], learning_rate=c["lr"],
                                    n_estimators=c["trees"], num_leaves=c["leaves"], max_depth=c["depth"],
                                    min_child_samples=c["min_child"], reg_lambda=c["l2"], reg_alpha=c["l1"],
                                    colsample_bytree=c["col"], subsample=c["sub"],
                                    subsample_freq=1 if c["sub"] < 1 else 0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=X.SEED, n_jobs=1,
                                    verbose=-1, monotone_constraints=[1 if x in MONO else 0 for x in cols()],
                                    monotone_constraints_method="basic")
        kw = {"init_score": offset(tr, price_fit)} if self.use_offset else {}
        self.m.fit(tr[cols()].astype(float), y, **kw)
        return self

    def predict(self, te: pd.DataFrame) -> np.ndarray:
        off = offset(te, self.price_fit)
        if self.m is None:
            return 1 / (1 + np.exp(-off))
        raw = self.m.predict(te[cols()].astype(float), raw_score=True)
        if self.use_offset:
            raw = raw + off
        return 1 / (1 + np.exp(-raw))


def forecast(S: pd.DataFrame, t: int, variant: str, d=None) -> pd.DataFrame:
    """U-ONE at origin t: one model, the rows of origin t at every lead."""
    use = variant == "U-ONE-P"
    lab = C.known_t43c(t, d)[["province_code", "q", "y"]]
    tr = S[(S["t"] < t) & (S["target_q"] <= t - 1)].rename(columns={"target_q": "q"}).merge(
        lab, on=["province_code", "q"], how="inner")
    pr = U.train_rows(S, t, d)
    te = S[S["t"] == t]
    out = te[["t", "lead", "province_code", "target_q"]].copy()
    if not B.eligible(tr):
        out[f"{variant}_p"] = 1 / (1 + np.exp(-offset(te, pr)))
        out[f"{variant}_cfg"] = "offset-only"
        return out
    origins = sorted(tr["t"].unique())[-4:]
    folds = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o], pr[pr["q"] <= o - 1]) for o in origins]
    folds = [f for f in folds if f[0]["q"].nunique() >= 3 and f[0]["y"].nunique() == 2 and len(f[1])]
    best = grid()[0]
    if folds:
        ys = np.concatenate([h["y"].to_numpy(int) for _, h, _ in folds])
        sc = {}
        for c in grid():
            ps = np.concatenate([One(c, use).fit(f, p).predict(h) for f, h, p in folds])
            p = np.clip(ps, 1e-6, 1 - 1e-6)
            sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
        best = min(grid(), key=lambda c: (round(sc[c["id"]], 9), grid().index(c)))
    out[f"{variant}_p"] = One(best, use).fit(tr, pr).predict(te)
    out[f"{variant}_cfg"] = best["id"]
    return out


def hunger_override() -> tuple[str, dict | None]:
    r3 = json.loads((OUT / "results_addendum3.json").read_text())
    h = next(x for x in ("H3a", "H4", "H0") if r3["selection"]["adopted"].endswith(x))
    if h == "H0":
        return "H0", None
    return h, None  # resolved in build() with the issue-time functions


def build(K: int, d=None, x=None, last_origin=None, w=None, cpi=None, rice=None) -> tuple[pd.DataFrame, str]:
    h, _ = hunger_override()
    S = U.stack(K) if d is None else U.stack(K, d, x, last_origin, w)
    S = X.add_fe(S, d, rice)
    hm = None
    if h != "H0":
        fn = (lambda t, k: A3.h4(t, k)) if h == "H4" else (lambda t, k: A3.h3(t, k, "a", cpi))
        hm = {}
        for t, k in S[["t", "lead"]].drop_duplicates().itertuples(index=False):
            v = fn(int(t), int(k))
            if not np.isnan(v):
                hm[(int(t), int(k))] = v
    return add_onset(S, cpi, hm), h


def phase_audit():
    _check()
    U.setup()
    sys.path.insert(0, str(C.HERE))
    import run_ch1 as RC
    K = RL._K()
    rng = np.random.default_rng(X.SEED + 4)
    d, x = E.data()
    o_rounds, o_gkg = C.FM.rounds.__wrapped__, C.NF.gkg.__wrapped__
    w0, rice0, cpi0 = U.pinksheet(), X.rice_cpi(), A3.region_cpi()

    def run(t, dd, w, rice, cpi):
        S, _ = build(K, dd, x, t, w, cpi, rice)
        f = pd.concat([forecast(S, t, v, dd).set_index(["province_code", "lead"])[f"{v}_p"] for v in VARIANTS], axis=1)
        return f.round(10)

    def clear():
        RC._clear()
        U._rounds.cache_clear()
        E._CACHE.clear()

    res = []
    for q in ("2023-Q2", "2023-Q4", "2024-Q2", "2024-Q4", "2025-Q3", "2026-Q2"):
        t = L.qi(q)
        clear()
        base = run(t, d, w0, rice0, cpi0)
        iss, m0 = E.issue(t), L.m0_of(t)
        r0 = o_rounds("primary").copy()
        fut = r0["published"] >= iss
        r0.loc[fut, "H"] = rng.uniform(0, 50, int(fut.sum()))
        yo, ix = d.yoy.copy(), d.idx.copy()
        yo.loc[yo["ym"] > m0, "yoy"] = rng.uniform(-10, 20, int((yo["ym"] > m0).sum()))
        ix.loc[ix["ym"] > m0, "index"] = rng.uniform(80, 160, int((ix["ym"] > m0).sum()))
        dp = dataclasses.replace(d, yoy=yo, idx=ix)
        g0 = o_gkg().copy()
        gf = g0["published"] >= pd.Timestamp(iss)
        for c in C.NF.CATS + ["anticipatory", "food_event"]:
            g0.loc[gf, c] = rng.permutation(g0.loc[gf, c].to_numpy())
        wp = w0.copy()
        fm = wp.index > m0
        num = [c for c in wp.columns if c != "month"]
        wp.loc[fm, num] = wp.loc[fm, num] * rng.uniform(0.5, 2.0, size=(int(fm.sum()), len(num)))
        rp = rice0.copy()
        rp[rp.index > m0] = rng.uniform(80, 200, int((rp.index > m0).sum()))
        cp = cpi0.copy()
        cp.loc[cp.index > m0] = rng.uniform(-20, 40, size=cp.loc[cp.index > m0].shape)
        C.FM.rounds = lambda dataset="primary", _p=r0: _p if dataset == "primary" else o_rounds(dataset)
        C.FM.rounds.cache_clear = lambda: None
        C.NF.gkg = lambda _g=g0: _g
        C.NF.gkg.cache_clear = lambda: None
        clear()
        try:
            pert = run(t, dp, wp, rp, cp)
        finally:
            C.FM.rounds = C.FM.functools.lru_cache(maxsize=2)(o_rounds)
            C.NF.gkg = C.FM.functools.lru_cache(maxsize=1)(o_gkg)
            clear()
        same = bool(base.equals(pert))
        res.append({"origin": q, "values": int(base.notna().sum().sum()), "identical": same})
        print(res[-1], flush=True)
    ok = all(r["identical"] and r["values"] for r in res)
    FM.write_json(OUT / "leakage_audit_addendum4.json", {"passed": ok, "origins": res})
    assert ok


def phase_score():
    _check()
    assert json.loads((OUT / "leakage_audit_addendum4.json").read_text())["passed"]
    U.setup()
    K = RL._K()
    t0 = time.time()
    S, h = build(K)
    fr = []
    for t in RL._origins():
        fr.append(pd.concat([forecast(S, t, v).set_index(["t", "lead", "province_code", "target_q"]) for v in VARIANTS],
                            axis=1).reset_index())
        print("origin", L.qs(t), round(time.time() - t0), "s", flush=True)
    P = pd.concat(fr, ignore_index=True).drop(columns=["target_q"])
    D = pd.read_csv(OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    n0 = len(D)
    D = D.merge(P, on=["t", "lead", "province_code"], how="left")
    assert len(D) == n0 and D[[f"{v}_p" for v in VARIANTS]].notna().all().all(), "rows differ"
    D.to_csv(OUT / "predictions_addendum4.csv", index=False, lineterminator="\n", float_format="%.6g")
    dev = D[(D["q"] <= U.DEV_LAST) & (D["lead"] <= 4)]
    sel = {v: float(np.mean([A2._brier(g[f"{v}_p"], g["y"]) for _, g in dev.groupby("lead")])) for v in VARIANTS}
    chosen = "U-ONE-P" if sel["U-ONE-P"] < sel["U-ONE-0"] - 0.0005 else "U-ONE-0"
    lab = C.labels().set_index(["province_code", "q"])["y"]
    res = {"addendum4_sha256": FM.sha256(X.L2 / "ADDENDUM_4_ONE_MODEL.md"), "hunger_input": h,
           "selection": {"dev_brier_mean_leads_1_4": sel, "chosen": chosen}, "models": {}}
    for v in list(VARIANTS) + ["UNI-FINAL"]:
        col = f"{v}_p" if v != "UNI-FINAL" else "P0H0_p"
        leads, mrl, r17 = {}, None, 0
        for k, g in D.groupby("lead"):
            dec = RL.lead_report(g, col)
            dec["surge_block"] = A2.block(g[g["q"].isin(A2.SURGE)], col)
            lb = A2.block(g[g["q"].isin(A2.LATER)], col)
            dec["later_block"], dec["later_check"] = lb, A2.later_check(lb)
            ons = g[[lab.get((p, q - 1), None) == 0 and yy == 1 for p, q, yy in zip(g["province_code"], g["q"], g["y"])]]
            dec["onsets"] = {"n": int(len(ons)), "caught": int((ons[col] >= .5).sum())}
            yv = g["y"].astype(int).to_numpy()
            dec["vs_uni_brier"] = FM.boot_diff(g, (g[col] - yv) ** 2, (g["P0H0_p"] - yv) ** 2)
            dec["verdict"] = "promising_not_yet_verified" if dec["reliable"] and dec["later_check"] else "not_reliable"
            leads[int(k)] = dec
        for k in sorted(leads):
            if leads[k]["verdict"] == "promising_not_yet_verified":
                mrl = k
            else:
                break
        for k in sorted(leads):
            if leads[k]["reliable"]:
                r17 = k
            else:
                break
        res["models"][v] = {"max_promising_lead": mrl, "max_r1_r7_lead": r17,
                            "testable_horizon_R1": max(k for k, x in leads.items() if x["criteria"]["R1"]),
                            "leads": leads}
        for k in (1, 2, 3):
            m = leads[k]["metrics"]
            print(f"{v:9s} L{k}: acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} "
                  f"R {m['recall']:.2f} AUC {m['auc']:.2f} Brier {m['brier']:.3f} FN {leads[k]['confusion']['fn']} "
                  f"onsets {leads[k]['onsets']['caught']}/{leads[k]['onsets']['n']} surge "
                  f"{leads[k]['surge_block']['tp']}/{leads[k]['surge_block']['high']} later "
                  f"{leads[k]['later_block']['acc']:.2f} fail {[c for c, z in leads[k]['criteria'].items() if not z]} "
                  f"| vsUNI {leads[k]['vs_uni_brier']['diff']:+.4f} p {leads[k]['vs_uni_brier']['p_less']:.3f}", flush=True)
        print(f"   {v}: max promising {mrl}, max R1-R7 {r17}", flush=True)
    M = res["models"][chosen]
    t1 = M["leads"][1]["vs_uni_brier"]
    res["serve_rule"] = {"reliable_lead1": M["leads"][1]["reliable"], "max_reliable_ge_1": M["max_r1_r7_lead"] >= 1,
                         "lead1_not_worse_than_uni": not (t1["diff"] > 0 and (1 - t1["p_less"]) < 0.10)}
    res["serve_rule"]["serve"] = all(res["serve_rule"].values())
    FM.write_json(OUT / "results_addendum4.json", res)
    print("chosen", chosen, sel, "| serve", res["serve_rule"])


def phase_replay():
    U.setup()
    K = RL._K()
    D = pd.read_csv(OUT / "predictions_addendum4.csv", dtype={"province_code": str})
    chosen = json.loads((OUT / "results_addendum4.json").read_text())["selection"]["chosen"]
    d, x = E.data()
    out = []
    for q in ("2023-Q4", "2024-Q4", "2026-Q1"):
        t = L.qi(q)
        S, _ = build(K, d, x, t)
        assert S["t"].max() == t
        f = forecast(S, t, chosen, d)
        m = f.merge(D[D["t"] == t][["lead", "province_code", f"{chosen}_p"]], on=["lead", "province_code"],
                    suffixes=("_replay", ""))
        out.append({"origin": q, "rows_compared": int(len(m)),
                    "max_abs_diff": float((m[f"{chosen}_p_replay"] - m[f"{chosen}_p"]).abs().max())})
        print(out[-1], flush=True)
    FM.write_json(OUT / "historical_replay_addendum4.json",
                  {"identical": all(o["max_abs_diff"] < 1e-5 and o["rows_compared"] for o in out), "model": chosen,
                   "origins": out})


if __name__ == "__main__":
    {"audit": phase_audit, "score": phase_score, "replay": phase_replay}[sys.argv[1]]()
