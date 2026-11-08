"""FINAL_UNIFIED_LGBM Addendum 1 (post-hoc improvement arms U4, U3, U5). Frozen code in uni_lib/run_uni is reused, not
changed. Rows, labels, pi_H, baselines and R1-R7 are those of the frozen run (out/predictions.csv).

    python improve.py score       # arms + no-news twins, development selection, per-lead verdicts -> out/improved_*.{csv,json}
"""
from __future__ import annotations

import json
import sys

import uni_lib as U

C, FM, B, E, L, np, pd = U.C, U.FM, U.B, U.E, U.L, U.np, U.pd
OUT = U.OUT
GRID4 = [dict(id=100 + i, depth=d, leaves=(3 if d == 2 else 7), trees=n, cw=w)
         for i, (d, n, w) in enumerate([(d, n, w) for d in (2, 3) for n in (50, 150) for w in (None, "balanced")])]
TAUS = [round(0.20 + 0.05 * i, 2) for i in range(7)]          # 0.20 .. 0.50
ARMS = {"U4": dict(grid="G4", tau=False), "U3": dict(grid="G2", tau=True), "U5": dict(grid="G4", tau=True)}


def _check():
    assert FM.sha256(U.UNI / "PROTOCOL_UNIFIED_LGBM.md") == (U.HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert FM.sha256(U.UNI / "ADDENDUM_1_IMPROVEMENT_ARMS.md") == (U.HERE / "ADDENDUM_1_SHA256.txt").read_text().strip()


def _logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def select_fit(tr: pd.DataFrame, cols_: list[str], grid: list[dict]):
    """U.select with a given grid; also returns the chosen config's inner held-out predictions (for the cutoff)."""
    origins = sorted(tr["t"].unique())[-4:]
    folds = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o]) for o in origins]
    folds = [(f, h) for f, h in folds if f["q"].nunique() >= 3 and f["y"].nunique() == 2 and len(h)]
    if not folds:
        return grid[0], None
    best, inner = None, None
    for c in grid:
        preds = [U.UniPrice(c, cols_, True).fit(f).predict(h) for f, h in folds]
        ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
        s = _logloss(ys, np.concatenate(preds))
        if best is None or (round(s, 9), c["id"]) < best[0]:
            best = ((round(s, 9), c["id"]), c)
            inner = pd.concat([h.assign(p_inner=p) for (_, h), p in zip(folds, preds)], ignore_index=True)
    return best[1], inner


def choose_tau(inner: pd.DataFrame | None, t: int) -> float:
    """Addendum 1: maximise inner balanced accuracy of H1*pi_P vs T43c labels known at O(t), among cutoffs whose inner
    accuracy is within 0.05 of the accuracy at 0.5; ties -> larger tau."""
    if inner is None or not len(inner):
        return 0.5
    lab = C.known_t43c(t)[["province_code", "q", "y"]].rename(columns={"y": "y43"})
    d = inner.merge(lab, on=["province_code", "q"], how="inner")
    if d["y43"].nunique() < 2:
        return 0.5
    s, y = (d["H1"] * d["p_inner"]).to_numpy(), d["y43"].to_numpy(int)

    def acc_bal(tau):
        c = (s >= tau).astype(int)
        tpr = ((c == 1) & (y == 1)).sum() / max((y == 1).sum(), 1)
        tnr = ((c == 0) & (y == 0)).sum() / max((y == 0).sum(), 1)
        return float((c == y).mean()), float((tpr + tnr) / 2)
    a50 = acc_bal(0.5)[0]
    ok = [(acc_bal(tau)[1], tau) for tau in TAUS if acc_bal(tau)[0] >= a50 - 0.05]
    return max(ok)[1] if ok else 0.5


def fit_predict_arm(S, t, arm, news):
    tr = U.train_rows(S, t)
    te = S[S["t"] == t]
    if not B.eligible(tr) or not len(te):
        return None
    cc = U.cols("U2", news)
    grid = GRID4 if ARMS[arm]["grid"] == "G4" else B.GRID
    cfg, inner = select_fit(tr, cc, grid)
    mdl = U.UniPrice(cfg, cc, True).fit(tr)
    tau = choose_tau(inner, t) if ARMS[arm]["tau"] else 0.5
    return te[["t", "lead", "province_code"]].assign(pi_price=mdl.predict(te), tau=tau, cfg=cfg["id"])


def decide_tau(G: pd.DataFrame, pcol: str, taucol: str | None) -> dict:
    """R1-R7 with class calls at the row's cutoff and Brier / probability tests on the raw probability."""
    raw = C.decide(G.assign(CH1_p=G[pcol]))
    if taucol is None:
        return raw
    call = C.decide(G.assign(CH1_p=(G[pcol] - G[taucol] + 0.5).clip(0, 1)))
    out = dict(call)
    out["metrics"] = {**call["metrics"], "brier": raw["metrics"]["brier"], "auc": raw["metrics"].get("auc")}
    out["brier_vs_persist_si"], out["brier_vs_clim"] = raw["brier_vs_persist_si"], raw["brier_vs_clim"]
    c = dict(call["criteria"])
    c["R5"] = raw["criteria"]["R5"]
    out["criteria"], out["reliable"] = c, all(c.values())
    out["reliable_strict"] = out["reliable"] and call["reliable_strict"]
    return out


def phase_score():
    _check()
    U.setup()
    K = int(json.loads((OUT / "testability_unified.json").read_text())["K"])
    S = U.stack(K)
    origins = [L.qi(q) for q in json.loads((OUT / "testability_unified.json").read_text())["eligible_origins"]]
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    for arm in ARMS:
        for news in (True, False):
            P = pd.concat([p for p in (fit_predict_arm(S, t, arm, news) for t in origins) if p is not None])
            tag = arm + ("" if news else "-GOV")
            D = D.merge(P.rename(columns={"pi_price": f"{tag}_price", "tau": f"{tag}_tau", "cfg": f"{tag}_cfg"}),
                        on=["t", "lead", "province_code"], how="left")
            D[f"{tag}_p"] = D["pi_h_used"] * D[f"{tag}_price"]
            print("scored", tag, flush=True)
    D["UNI_tau"] = 0.5
    dev = D[(D["q"] <= U.DEV_LAST) & (D["lead"] <= 4)]

    def dev_stats(pcol, taucol):
        accs, bals, brs = [], [], []
        for _, g in dev.groupby("lead"):
            y = g["y"].astype(int).to_numpy()
            c = (g[pcol] >= g[taucol]).astype(int).to_numpy()
            tpr = ((c == 1) & (y == 1)).sum() / max((y == 1).sum(), 1)
            tnr = ((c == 0) & (y == 0)).sum() / max((y == 0).sum(), 1)
            accs.append(float((c == y).mean()))
            bals.append(float((tpr + tnr) / 2))
            brs.append(float(np.mean((g[pcol] - y) ** 2)))
        return {"acc": float(np.mean(accs)), "bal": float(np.mean(bals)), "brier": float(np.mean(brs))}
    sel = {"UNI-FINAL": dev_stats("UNI_p", "UNI_tau"), "U4": dev_stats("U4_p", "UNI_tau"),
           "U3": dev_stats("U3_p", "U3_tau"), "U5": dev_stats("U5_p", "U5_tau")}
    cap = "U4" if sel["U4"]["brier"] < sel["UNI-FINAL"]["brier"] else "UNI-FINAL"
    cut_arm = "U5" if cap == "U4" else "U3"
    base = sel[cap]
    use_cut = sel[cut_arm]["bal"] > base["bal"] and sel[cut_arm]["acc"] >= base["acc"] - 0.03
    chosen = cut_arm if use_cut else cap
    pcol = {"UNI-FINAL": "UNI_p"}.get(chosen, f"{chosen}_p")
    gcol = {"UNI-FINAL": "UNI-GOV_p"}.get(chosen, f"{chosen}-GOV_p")
    taucol = f"{chosen}_tau" if use_cut else None
    D["IMP_p"], D["IMP-GOV_p"] = D[pcol], D[gcol]
    D["IMP_tau"] = D[taucol] if taucol else 0.5
    D.to_csv(OUT / "improved_predictions.csv", index=False, lineterminator="\n", float_format="%.6g")
    res = {"addendum_sha256": FM.sha256(U.UNI / "ADDENDUM_1_IMPROVEMENT_ARMS.md"), "status": "post-hoc (confirmation quarters seen)",
           "dev_selection": sel, "capacity_choice": cap, "cutoff_adopted": bool(use_cut), "UNI_IMPROVED": chosen,
           "leads": {}}
    for k, g in D.groupby("lead"):
        dec = decide_tau(g, "IMP_p", "IMP_tau" if use_cut else None)
        y = g["y"].astype(int).to_numpy()
        call = (g["IMP_p"] >= g["IMP_tau"]).astype(int)
        callg = (g["IMP-GOV_p"] >= g["IMP_tau"]).astype(int)
        dec["news_ablation"] = {"acc_with": float((call == y).mean()), "acc_without": float((callg == y).mean()),
                                "brier_diff": FM.boot_diff(g, (g["IMP_p"] - y) ** 2, (g["IMP-GOV_p"] - y) ** 2)}
        dec["vs_uni_final"] = {"acc_uni_final": float(((g["UNI_p"] >= .5).astype(int) == y).mean()),
                               "brier": FM.boot_diff(g, (g["IMP_p"] - y) ** 2, (g["UNI_p"] - y) ** 2)}
        cm = g[g["CH1-LEAD_p"].notna()]
        if len(cm):
            yc = cm["y"].astype(int).to_numpy()
            dec["vs_ch1_per_lead"] = {"rows": int(len(cm)), "acc_ch1": float(((cm["CH1-LEAD_p"] >= .5).astype(int) == yc).mean()),
                                      "acc_imp": float(((cm["IMP_p"] >= cm["IMP_tau"]).astype(int) == yc).mean()),
                                      "brier": FM.boot_diff(cm, (cm["IMP_p"] - yc) ** 2, (cm["CH1-LEAD_p"] - yc) ** 2)}
        conf = g[g["q"].isin(U.CONFIRM)]
        dec["confirmation_block"] = {"rows": int(len(conf)), "accuracy": float(((conf["IMP_p"] >= conf["IMP_tau"]).astype(int) == conf["y"]).mean()) if len(conf) else None,
                                     "always_low": float((conf["y"] == 0).mean()) if len(conf) else None}
        dec["tau_used"] = sorted(set(round(float(x), 2) for x in g["IMP_tau"]))
        res["leads"][int(k)] = dec
        m = dec["metrics"]
        print(f"lead {k}: acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} R {m['recall']:.2f} "
              f"brier {m['brier']:.3f} fail {[c for c, v in dec['criteria'].items() if not v]}", flush=True)
    hp = FM.holm({k: res["leads"][k]["news_ablation"]["brier_diff"]["p_two"] for k in res["leads"]})
    for k in res["leads"]:
        res["leads"][k]["news_ablation"]["holm_p"] = hp[k]
    passing = [k for k in sorted(res["leads"]) if res["leads"][k]["reliable"]]
    mrl = None
    for k in sorted(res["leads"]):
        if res["leads"][k]["reliable"]:
            mrl = k
        else:
            break
    res.update(max_reliable_lead=mrl, individually_passing_leads=passing,
               testable_horizon_R1=max(k for k in res["leads"] if res["leads"][k]["criteria"]["R1"]))
    FM.write_json(OUT / "improved_results.json", res)
    print("selection", {k: {a: round(b, 4) for a, b in v.items()} for k, v in sel.items()}, "->", chosen,
          "| max reliable", mrl, "passing", passing)


def phase_placebo(n: int = 20):
    """Post-hoc diagnostic (not in the frozen protocol): UNI-FINAL refitted with the news columns permuted across
    issue quarters; Lead-1 Brier of pi_H x pi_P against the real model. Permutation p = share of placebos at least as good."""
    _check()
    U.setup()
    K = int(json.loads((OUT / "testability_unified.json").read_text())["K"])
    S = U.stack(K)
    origins = [L.qi(q) for q in json.loads((OUT / "testability_unified.json").read_text())["eligible_origins"]]
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    D1 = D[D["lead"] == 1][["t", "lead", "province_code", "y", "H1", "UNI_p"]]
    real = float(np.mean((D1["UNI_p"] - D1["y"]) ** 2))
    rng = np.random.default_rng(U.SEED)
    ts = sorted(S["t"].unique())
    vals = []
    for i in range(n):
        perm = dict(zip(ts, rng.permutation(ts)))
        key = S.set_index(["t", "province_code", "lead"])[U.NEWS_COLS]
        Sp = S.copy()
        src = pd.MultiIndex.from_arrays([Sp["t"].map(perm), Sp["province_code"], Sp["lead"]])
        Sp[U.NEWS_COLS] = key.reindex(src).to_numpy()
        P = pd.concat([p for p in (U.fit_predict(Sp, t, "U2", True) for t in origins) if p is not None])
        M = D1.merge(P[P["lead"] == 1][["t", "lead", "province_code", "pi_price"]], on=["t", "lead", "province_code"])
        vals.append(float(np.mean((M["H1"] * M["pi_price"] - M["y"]) ** 2)))
        print(i, round(vals[-1], 4), flush=True)
    v = np.array(vals)
    out = {"status": "post-hoc diagnostic", "lead": 1, "real_brier": real, "placebo_mean": float(v.mean()),
           "placebo_min": float(v.min()), "permutation_p": float((np.sum(v <= real) + 1) / (len(v) + 1)), "n": n}
    FM.write_json(OUT / "news_placebo.json", out)
    print(out)


# ================================================================================================ Addendum 2 (U6)
def _seasonal_proj(s: pd.Series, t: int, k: int) -> float:
    """Mean YoY over the target months of t+k with index(m) = index(m0) * exp(mean past log change m0->m, same calendar
    months, both months published at O(t) and >= 2021-01); fallback = flat (Addendum 2)."""
    m0 = L.m0_of(t)
    if m0 not in s.index:
        return float("nan")
    ls = np.log(s)
    vals = []
    for b in E.projection_bases(t, k):
        m = b + 12
        n = m - m0
        ch = [ls[a + n] - ls[a] for a in (m0 - 12 * j for j in range(1, 8))
              if a >= L.FIRST_YM and a + n <= m0 and a in ls.index and a + n in ls.index]
        proj = s[m0] * float(np.exp(np.mean(ch))) if ch else s[m0]
        if b in s.index:
            vals.append(100 * (proj / s[b] - 1))
    return float(np.mean(vals)) if len(vals) >= 2 else float("nan")


def add_seasonal(S: pd.DataFrame) -> pd.DataFrame:
    d, _ = E.data()
    cache = {}
    adj_f, adj_g = [], []
    for t, k, p in zip(S["t"], S["lead"], S["province_code"]):
        t, k = int(t), int(k)
        if t not in cache:
            cache[t] = d.cut(t)
        dc = cache[t]
        sf, sh = L._series(dc, p, "food"), L._series(dc, p, "all_items")
        f, h = E.projection(dc, t, k, p, "food"), E.projection(dc, t, k, p, "all_items")
        fs, hs = _seasonal_proj(sf, t, k), _seasonal_proj(sh, t, k)
        adj_f.append(fs - f if np.isfinite(fs) and np.isfinite(f) else 0.0)
        adj_g.append((fs - hs) - (f - h) if all(np.isfinite(v) for v in (fs, hs, f, h)) else 0.0)
    return S.assign(A1_food_s=S["A1_food"] + np.array(adj_f), A1_gap_s=S["A1_gap"] + np.array(adj_g))


def _u6_cols(news: bool) -> list[str]:
    return [{"A1_food": "A1_food_s", "A1_gap": "A1_gap_s"}.get(c, c) for c in U.cols("U2", news)]


def fit_predict_u6(S, t, news):
    tr = U.train_rows(S, t)
    te = S[S["t"] == t]
    if not B.eligible(tr) or not len(te):
        return None
    cc = _u6_cols(news)
    cfg, _ = U.select(tr, cc, True)
    mdl = U.UniPrice(cfg, cc, True).fit(tr)
    return te[["t", "lead", "province_code"]].assign(pi_price=mdl.predict(te))


def phase_seasonal():
    _check()
    assert FM.sha256(U.UNI / "ADDENDUM_2_LEAD2_SEASONAL.md") == (U.HERE / "ADDENDUM_2_SHA256.txt").read_text().strip()
    U.setup()
    for c in ("A1_food_s", "A1_gap_s"):
        if c not in U.MONO_UP:
            U.MONO_UP.append(c)
    K = int(json.loads((OUT / "testability_unified.json").read_text())["K"])
    S = add_seasonal(U.stack(K))
    print("seasonal adjustment |A1_food_s - A1_food| mean by lead:",
          S.assign(a=(S["A1_food_s"] - S["A1_food"]).abs()).groupby("lead")["a"].mean().round(2).to_dict(), flush=True)
    origins = [L.qi(q) for q in json.loads((OUT / "testability_unified.json").read_text())["eligible_origins"]]
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    for news in (True, False):
        P = pd.concat([p for p in (fit_predict_u6(S, t, news) for t in origins) if p is not None])
        tag = "U6" + ("" if news else "-GOV")
        D = D.merge(P.rename(columns={"pi_price": f"{tag}_price"}), on=["t", "lead", "province_code"], how="left")
        D[f"{tag}_p"] = D["pi_h_used"] * D[f"{tag}_price"]
        print("scored", tag, flush=True)
    dev = D[(D["q"] <= U.DEV_LAST) & (D["lead"] <= 4)]
    br = {c: float(np.mean([np.mean((g[c] - g["y"]) ** 2) for _, g in dev.groupby("lead")])) for c in ("UNI_p", "U6_p")}
    adopt = br["U6_p"] < br["UNI_p"]
    res = {"addendum2_sha256": FM.sha256(U.UNI / "ADDENDUM_2_LEAD2_SEASONAL.md"), "status": "post-hoc",
           "dev_brier": br, "adopted": bool(adopt), "leads": {}}
    for k, g in D.groupby("lead"):
        dec = C.decide(g.assign(CH1_p=g["U6_p"]))
        y = g["y"].astype(int).to_numpy()
        dec["news_ablation"] = {"brier_diff": FM.boot_diff(g, (g["U6_p"] - y) ** 2, (g["U6-GOV_p"] - y) ** 2)}
        dec["vs_uni_final"] = {"acc_uni_final": float(((g["UNI_p"] >= .5).astype(int) == y).mean()),
                               "brier": FM.boot_diff(g, (g["U6_p"] - y) ** 2, (g["UNI_p"] - y) ** 2)}
        from sklearn.metrics import roc_auc_score
        dec["price_auc"] = {"U6": float(roc_auc_score(g["price"], g["U6_price"])) if g["price"].nunique() > 1 else None,
                            "U2": float(roc_auc_score(g["price"], g["U2_price"])) if g["price"].nunique() > 1 else None}
        res["leads"][int(k)] = dec
        m = dec["metrics"]
        print(f"lead {k}: acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} R {m['recall']:.2f} "
              f"price AUC U6 {dec['price_auc']['U6']} vs U2 {dec['price_auc']['U2']} fail "
              f"{[c for c, v in dec['criteria'].items() if not v]}", flush=True)
    mrl = None
    for k in sorted(res["leads"]):
        if res["leads"][k]["reliable"]:
            mrl = k
        else:
            break
    res["max_reliable_lead"] = mrl
    res["individually_passing_leads"] = [k for k in sorted(res["leads"]) if res["leads"][k]["reliable"]]
    D.to_csv(OUT / "seasonal_predictions.csv", index=False, lineterminator="\n", float_format="%.6g")
    FM.write_json(OUT / "seasonal_results.json", res)
    print("dev Brier", {a: round(b, 4) for a, b in br.items()}, "adopted", adopt, "| max reliable", mrl,
          "passing", res["individually_passing_leads"])


if __name__ == "__main__":
    {"score": phase_score, "placebo": phase_placebo, "seasonal": phase_seasonal}[sys.argv[1]]()
