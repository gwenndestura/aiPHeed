"""E96 (PROTOCOL.md): four distinct questions on the unified news-informed LightGBM framework. Run from backend/.

Q1 formulation: forecast the measured regional outcome (SWS involuntary hunger, continuous) with the framework's
   linear-tree hunger component, versus the random walk (last posted reading) and climatology; plus deterioration events.
Q2 false alarms: replace the raw 4-quarter cumulative inflation (cumF4) by a decaying, direction-gated inflation memory
   whose half-life is chosen per origin by inner chronological validation on training labels only.
Q3 signal availability: drop each of the five required indicator groups from the selected T43 arm.
Q4 news: compare, all else equal, no news / the ten N3 indicators / plus de-duplicated event-based food-access news with
   novelty / plus news x hunger and news x market interactions; counterfactual effect of news on individual forecasts.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
E96 = HERE.parent
EXP = E96.parent
sys.path.insert(0, str(EXP / "E94_Final_Unified_LightGBM" / "runner"))
import run_e94 as A  # noqa: E402

B, G, U, E, L, np, pd = A.B, A.G, A.U, A.E, A.L, A.np, A.pd
from scipy.stats import norm  # noqa: E402

KS = A.KS
TH = A.TH
E94_RUN = EXP / "E94_Final_Unified_LightGBM" / "runs" / "20261022T061502Z"
HALF_LIVES = (1.0, 2.0, 4.0)
EVENT_RISE = 3.0
EV_G = ("prices", "climate", "supply", "household")
NEWS_IMP = ["fa_idx", "fa_idx_run2", "ev_resp", "z_fa_idx"] + [f"ev_adv_{g}" for g in EV_G] + [f"z_adv_{g}" for g in EV_G]
NEWS_INT = ["nx_fa_H", "nx_supply_rice", "nx_climate_enso", "nx_resp_H"]
GROUPS5 = {
    "market": ["mom3", "F_hat_rel", "G_hat_rel", "compF_rel", "compG_rel", "rice_yoy_now", "rice_mom3", "w_rice_chg3",
               "w_rice_chg6", "w_food_chg3", "w_food_chg6", "D_now", "rice_whsl_yoy", "tariff_yoy_regime",
               "import_suspension_share", "price_ceiling_share", "food_emergency_share", "dF1", "dF2", "dG1", "rice_acc",
               "cumF4", "rice_x_H", "enso_x_rice"] + [f"mem_h{int(h)}" for h in HALF_LIVES] + [f"memdir_h{int(h)}" for h in HALF_LIVES],
    "climate": ["enso", "tc_count", "enso_run3", "tc_run3"],
    "employment_remittances_ofw": ["ur_yoy", "under_last", "remit_usd_yoy", "d_ur", "d_remit"],
    "news": list(B.NEWS) + list(B.NEWS_DIR_F) + NEWS_IMP + NEWS_INT,
    "poverty_vulnerability": ["pov"],
}


# ------------------------------------------------------------------------------------------------ features
def add_features(T: dict) -> dict:
    """pov: PSA SAE 2021 provincial mean, centred, known from 2025-01-01 (E54 POV-AS). mem_h: exponentially decayed mean
    of the province's past food YoY relative to its threshold over origins <= t (half-life h quarters). memdir_h: the
    same memory switched off while food YoY has fallen over the last two origins (dF2 < 0). News (Q4): de-duplicated,
    severity-weighted event rates per 100 collected articles known before O(t) (E83 events), a food-access index, its
    2-origin persistence, novelty z-scores against the regional history before t, and four interactions."""
    pv = U.pov_values()
    base = T[1][["t", "province_code", "F_rel", "dF2"]].sort_values("t")
    mem = []
    for p, g in base.groupby("province_code"):
        g = g.set_index("t")
        f = pd.DataFrame(index=g.index)
        for h in HALF_LIVES:
            f[f"mem_h{int(h)}"] = g["F_rel"].ewm(halflife=h, adjust=True, ignore_na=True).mean()
            f[f"memdir_h{int(h)}"] = f[f"mem_h{int(h)}"] * (g["dF2"].fillna(0) >= 0).astype(float)
        mem.append(f.reset_index().assign(province_code=p))
    M = pd.concat(mem, ignore_index=True)
    N = T[1][["t", "province_code"] + [f"ev_adv_{g}" for g in EV_G]].copy()
    N["fa_idx"] = N["ev_adv_supply"] + N["ev_adv_household"] + N["ev_adv_prices"]
    N = N.sort_values("t")
    N["fa_idx_run2"] = N.groupby("province_code")["fa_idx"].transform(lambda s: s.rolling(2, min_periods=1).sum())
    R = N.groupby("t")[["fa_idx"] + [f"ev_adv_{g}" for g in EV_G]].mean().sort_index()
    Z = pd.DataFrame(index=R.index)
    for c, zc in [("fa_idx", "z_fa_idx")] + [(f"ev_adv_{g}", f"z_adv_{g}") for g in EV_G]:
        mu = R[c].expanding().mean().shift(1)
        sd = R[c].expanding().std(ddof=1).shift(1)
        n = R[c].expanding().count().shift(1)
        Z[zc] = ((R[c] - mu) / sd.replace(0, np.nan)).where(n >= 4)
    N = N.merge(Z.reset_index(), on="t", how="left")
    M = M.merge(N[["t", "province_code", "fa_idx", "fa_idx_run2"] + list(Z.columns)], on=["t", "province_code"])
    out = {}
    for k in KS:
        X = T[k].merge(M, on=["t", "province_code"], how="left")
        X["pov"] = X["province_code"].map(pv)
        X.loc[X["t"].map(L.origin) < U.POV_KNOWN_FROM, "pov"] = np.nan
        X["nx_fa_H"] = X["fa_idx"] * X["H_rel"]
        X["nx_supply_rice"] = X["ev_adv_supply"] * X["rice_acc"]
        X["nx_climate_enso"] = X["ev_adv_climate"] * X["enso_run3"]
        X["nx_resp_H"] = X["ev_resp"] * X["H_rel"]
        out[k] = X
    return out


def cols(variant: str, drop: str | None = None, news: str = "n3"):
    pc, hc = B.arm_cols(True, True)
    pc, hc = pc + ["pov"], hc + ["pov"]
    extra = NEWS_IMP if news == "imp" else NEWS_IMP + NEWS_INT if news == "int" else []
    pc, hc = pc + extra, hc + extra
    if variant == "decay":
        pc = [c for c in pc if c != "cumF4"]
    if drop:
        pc = [c for c in pc if c not in GROUPS5[drop]]
        hc = [c for c in hc if c not in GROUPS5[drop]]
    return pc, hc


# ------------------------------------------------------------------------------------------------ price part
def _fit(cols_, tr, te):
    from lightgbm import LGBMClassifier
    mono = [1 if c in G.MONO_UP else 0 for c in cols_]
    m = LGBMClassifier(**B.GB, monotone_constraints=mono).fit(tr[cols_].astype(float), tr["y_price"])
    return m.predict_proba(te[cols_].astype(float))[:, 1]


def price_part(tr, te, pc, decay: bool):
    ok = tr["q"].nunique() >= 6 and tr["y_price"].sum() >= 5 and (1 - tr["y_price"]).sum() >= 5
    if not ok:
        return np.full(len(te), G.freq(tr["y_price"]) if len(tr) else 0.5), None
    if not decay:
        return _fit(pc, tr, te), None
    h_sel = 2.0
    qs = sorted(tr["q"].unique())
    inner, hold = tr[tr["q"] < qs[-3]], tr[tr["q"] >= qs[-3]]
    if inner["y_price"].nunique() == 2 and hold["y_price"].nunique() == 2 and inner["q"].nunique() >= 4:
        ll = {h: B._logloss(hold["y_price"].to_numpy(), _fit(pc + [f"mem_h{int(h)}", f"memdir_h{int(h)}"], inner, hold))
              for h in HALF_LIVES}
        h_sel = min(HALF_LIVES, key=lambda h: (round(ll[h], 10), h))
    return _fit(pc + [f"mem_h{int(h_sel)}", f"memdir_h{int(h_sel)}"], tr, te), h_sel


# ------------------------------------------------------------------------------------------------ hunger part
def hunger_point(tr, te_row, hc, d, t, k):
    """Linear-tree LightGBM hunger-change regressor (E93 hunger_lin): point forecast Ĥ, random-walk sd, P(H > 11.3)."""
    from lightgbm import LGBMRegressor
    hs = L.h_quarters(d.cut(t)).sort_values("q")
    qq, hh = hs["q"].to_numpy(), hs["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    s_min = sig * math.sqrt(max(t + k - int(qq[-1]), 1))
    H_last = float(te_row["H_rel"].iloc[0]) + TH["H"]
    if len(tr) < 8:
        Hh = H_last + (float((tr["H"] - tr["H_rel"] - TH["H"]).mean()) if len(tr) else 0.0)
        return Hh, s_min, float(1 - norm.cdf((TH["H"] - Hh) / s_min))
    y = tr["H"] - (tr["H_rel"] + TH["H"])
    med = tr[hc].median()
    Ax, Bx = tr[hc].astype(float).fillna(med).fillna(0.0), te_row[hc].astype(float).fillna(med).fillna(0.0)
    m = LGBMRegressor(**B.REG).fit(Ax, y)
    rmse = float(np.sqrt(np.mean((y - m.predict(Ax)) ** 2)))
    Hh = H_last + float(m.predict(Bx)[0])
    return Hh, s_min, float(1 - norm.cdf((TH["H"] - Hh) / max(s_min, rmse)))


def run(d, Ps, T, arms: dict) -> dict:
    """arms: name -> (variant, dropped group or None, news representation). One fit per origin per part, pooled
    K = 1..4, issues all K."""
    out = {k: Ps[k].copy() for k in KS}
    origins = sorted({int(t) for k in KS for t in Ps[k]["t"]})
    for name in arms:
        for k in KS:
            out[k][name] = np.nan
    for name, (variant, drop, news) in arms.items():
        pc, hc = cols(variant, drop, news)
        for t in origins:
            ptr = B.price_training(T, d, t)
            htr = B.hunger_rows(T, d, t, hc)
            for k in KS:
                m = out[k]["t"] == t
                if not m.any():
                    continue
                te = T[k][T[k]["t"] == t].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k)
                te_row = te[[c for c in hc if c != "k"]].mean().to_frame().T.assign(k=k)
                pp, h_sel = price_part(ptr, te, pc, variant == "decay")
                Hh, s, ph = hunger_point(htr, te_row, hc, d, t, k)
                out[k].loc[m, name] = ph * pp
                out[k].loc[m, f"{name}__ph"], out[k].loc[m, f"{name}__pp"] = ph, pp
                out[k].loc[m, f"{name}__Hhat"], out[k].loc[m, f"{name}__Hlast"] = Hh, float(te_row["H_rel"].iloc[0]) + TH["H"]
                out[k].loc[m, f"{name}__half_life"] = h_sel if h_sel is not None else np.nan
    return out


# ------------------------------------------------------------------------------------------------ evaluations
def hunger_eval(P: pd.DataFrame, d, name: str) -> dict:
    """Q1: measured regional outcome, one row per target quarter."""
    hq = L.h_quarters(d).set_index("q")["H"]
    g = P.groupby("target_q").agg(Hhat=(f"{name}__Hhat", "first"), Hlast=(f"{name}__Hlast", "first"),
                                  p=(f"{name}__ph", "first"), t=("t", "first")).reset_index()
    g["H"] = [float(hq[L.qi(q)]) for q in g["target_q"]]
    g["clim"] = [float(L.h_quarters(d.cut(int(t)))["H"].mean()) for t in g["t"]]
    err = {c: g[c] - g["H"] for c in ("Hhat", "Hlast", "clim")}
    res = {"n": len(g), "rmse": {c: float(np.sqrt(np.mean(e ** 2))) for c, e in err.items()},
           "mae": {c: float(np.mean(np.abs(e))) for c, e in err.items()}}
    tests = {b: E.sign_flip((err[b] ** 2 - err["Hhat"] ** 2).to_numpy()) for b in ("Hlast", "clim")}
    holm = E.holm({b: v["p_one_sided"] for b, v in tests.items()})
    res["sq_error_tests"] = {b: {**tests[b], "p_holm": holm[b]} for b in tests}
    y = (g["H"] > TH["H"]).astype(int)
    res["threshold"] = {"model": E.metrics(y, (g["p"] >= 0.5).astype(int), g["p"]),
                        "persistence": E.metrics(y, (g["Hlast"] > TH["H"]).astype(int), (g["Hlast"] > TH["H"]).astype(float))}
    ev = ((g["H"] - g["Hlast"]) >= EVENT_RISE).astype(int)
    pr = ((g["Hhat"] - g["Hlast"]) >= EVENT_RISE).astype(int)
    res["deterioration_events"] = {"events": int(ev.sum()), "predicted": int(pr.sum()), "hit": int((ev & pr).sum()),
                                   "false": int((pr & (1 - ev)).sum()),
                                   "event_quarters": g.loc[ev == 1, "target_q"].tolist(),
                                   "hit_quarters": g.loc[(ev & pr) == 1, "target_q"].tolist()}
    res["per_quarter"] = g[["target_q", "H", "Hhat", "Hlast", "clim"]].round(2).to_dict(orient="records")
    return res


def news_effect(P: pd.DataFrame, a: str, b: str = "M-U96-DROP-news") -> dict:
    """Q4: paired per-quarter Brier gain of a news arm over the otherwise identical no-news arm (one-sided sign-flip)."""
    g = P.assign(da=(P[b] - P.y) ** 2 - (P[a] - P.y) ** 2).groupby("target_q")["da"].mean()
    t = E.sign_flip(g.to_numpy())
    return {"mean_brier_gain_vs_no_news": float(g.mean()), "quarters_better": int((g > 1e-12).sum()),
            "quarters_worse": int((g < -1e-12).sum()), "p_one_sided": t["p_one_sided"], "per_quarter": g.round(4).to_dict()}


def counterfactual(T, d, variant: str, news: str, cases: list[tuple[str, int]]) -> list[dict]:
    """Q4: the same fitted framework at an origin, predicting with the news features as observed versus set to their
    training medians (a realistic 'ordinary news' value); the change in P(T43) and P(hunger)."""
    pc, hc = cols(variant, None, news)
    nf = set(GROUPS5["news"])
    out = []
    for q, k in cases:
        t = L.qi(q) - k
        ptr, htr = B.price_training(T, d, t), B.hunger_rows(T, d, t, hc)
        te = T[k][T[k]["t"] == t].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k)
        te0 = te.copy()
        for c in pc:
            if c in nf:
                te0[c] = ptr[c].median()
        row = te[[c for c in hc if c != "k"]].mean().to_frame().T.assign(k=k)
        row0 = row.copy()
        for c in hc:
            if c in nf and c in htr:
                row0[c] = htr[c].median()
        pp, _ = price_part(ptr, te, pc, variant == "decay")
        pp0, _ = price_part(ptr, te0, pc, variant == "decay")
        _, _, ph = hunger_point(htr, row, hc, d, t, k)
        _, _, ph0 = hunger_point(htr, row0, hc, d, t, k)
        for i, p in enumerate(L.PROVS):
            out.append({"target_q": q, "K": k, "province": L.NAMES[p], "p_with_news": float(ph * pp[i]),
                        "p_news_at_median": float(ph0 * pp0[i]), "p_hunger_with": ph, "p_hunger_median": ph0})
    return out


SELECTABLE = ["M-U96-POV", "M-U96-DECAY"]
NEWS_ARMS = ["M-U96-NEWS-N3", "M-U96-NEWS-IMP", "M-U96-NEWS-INT"]


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E96 / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    _, Ps = U.load_tables()
    T = add_features(A.add_news_x(B.tables()))
    out = run(d, Ps, T, {"M-U96-POV": ("base", None, "n3"), "M-U96-DECAY": ("decay", None, "n3")})
    for k in KS:
        out[k]["M-E94-U94"] = pd.read_csv(E94_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})["M-U94"].to_numpy()

    def selb(arms):
        return {a: float(np.mean([U.evaluate_k(out[k], [a])[0][a]["selection_block_brier"] for k in (1, 2, 3)])) for a in arms}
    sel_a = selb(SELECTABLE)
    stage_a = min(sel_a, key=sel_a.get)
    variant = "decay" if stage_a == "M-U96-DECAY" else "base"
    news_arms = {"M-U96-NEWS-IMP": (variant, None, "imp"), "M-U96-NEWS-INT": (variant, None, "int")}
    abl = {f"M-U96-DROP-{g}": (variant, g, "n3") for g in GROUPS5}
    out = run(d, out, T, {**news_arms, **abl})
    for k in KS:
        out[k]["M-U96-NEWS-N3"] = out[k][stage_a]
        for c in ("__ph", "__pp", "__Hhat", "__Hlast", "__half_life"):
            out[k][f"M-U96-NEWS-N3{c}"] = out[k][f"{stage_a}{c}"]
    sel_n = selb(NEWS_ARMS)
    chosen = min(sel_n, key=sel_n.get)
    arms = SELECTABLE + NEWS_ARMS + ["M-E94-U94"] + list(abl) + ["S-COV"]
    summ = {"stamp": stamp, "protocol_sha256": (E96 / "PROTOCOL.sha256").read_text().split()[0], "per_k": {}, "baselines": {},
            "stage_a_selection": sel_a, "stage_a": stage_a, "news_selection": sel_n, "selected": chosen}
    for k in KS:
        out[k].to_csv(o / f"predictions_k{k}.csv", index=False)
        summ["per_k"][k], summ["baselines"][k] = U.evaluate_k(out[k], arms)
        summ["per_k"][k]["_hunger_measured"] = {a: hunger_eval(out[k], d, a) for a in dict.fromkeys([chosen, "M-U96-NEWS-N3", "M-U96-DROP-news"])}
        summ["per_k"][k]["_news_effect"] = {a: news_effect(out[k], a) for a in NEWS_ARMS}
        summ["per_k"][k]["_half_life_choice"] = out[k][f"{chosen}__half_life"].dropna().value_counts().to_dict()
    nv = "imp" if chosen.endswith("IMP") else "int" if chosen.endswith("INT") else "n3"
    cases = [("2023-Q4", 2), ("2023-Q4", 1), ("2024-Q2", 2), ("2024-Q2", 1), ("2025-Q4", 1)]
    summ["news_counterfactual"] = counterfactual(T, d, variant, nv, cases)
    summ["K"] = {a: U.k_validated(summ["per_k"], a) for a in SELECTABLE + NEWS_ARMS + list(abl)}
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print("stage A:", {a: round(v, 4) for a, v in sel_a.items()}, "->", stage_a, "| news:", {a: round(v, 4) for a, v in sel_n.items()}, "->", chosen)
    for k in KS:
        print(f"K={k} half-life:", summ["per_k"][k]["_half_life_choice"])
        for a in arms:
            r = summ["per_k"][k][a]
            m, g, ps = r["metrics"], r["generalization"], r["pass"]
            cb = r.get("confirmation_block", {})
            th = {b: round(v.get("p_holm", 1), 3) for b, v in r["tests"].items()}
            print(f"  {a:34s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} R={m['recall_HIGH'] or 0:.2f} "
                  f"TP/FP/FN/TN={m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} brier={m['brier']:.3f} PASS={ps['PASS']} "
                  f"{[c for c, v in ps.items() if not v and c not in ('PASS', 'TARGET_80')]} holm={th} "
                  f"e/l={g['early_acc']:.2f}/{g['late_acc']:.2f} conf={cb.get('accuracy', float('nan')):.2f}/{cb.get('brier', float('nan')):.3f}",
                  flush=True)
        for a, v in summ["per_k"][k]["_news_effect"].items():
            print(f"  [news vs none] {a}: gain={v['mean_brier_gain_vs_no_news']:+.4f} better/worse={v['quarters_better']}/{v['quarters_worse']} p={v['p_one_sided']:.3f}")
        for a, h in summ["per_k"][k]["_hunger_measured"].items():
            print(f"  [measured hunger {a}] RMSE model/rw/clim={h['rmse']['Hhat']:.2f}/{h['rmse']['Hlast']:.2f}/{h['rmse']['clim']:.2f} "
                  f"holm={ {b: round(v['p_holm'], 3) for b, v in h['sq_error_tests'].items()} } thr acc={h['threshold']['model']['accuracy']:.3f}"
                  f"/{h['threshold']['persistence']['accuracy']:.3f} events={ {x: h['deterioration_events'][x] for x in ('events', 'predicted', 'hit', 'false')} }")
    for c in summ["news_counterfactual"]:
        print("  cf", {k_: (round(v, 3) if isinstance(v, float) else v) for k_, v in c.items()})
    print("K:", {a: v["K"] for a, v in summ["K"].items()})
    print(o)
