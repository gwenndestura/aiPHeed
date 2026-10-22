"""E95 (PROTOCOL.md): root-cause correction of the unified news-informed LightGBM's price component; K = 1..4; plus
the measured-food-insecurity research target (regional SWS hunger). Run from backend/.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
E95 = HERE.parent
EXP = E95.parent
sys.path.insert(0, str(EXP / "E94_Final_Unified_LightGBM" / "runner"))
import run_e94 as A  # noqa: E402

B, G, U, E, L, np, pd = A.B, A.G, A.U, A.E, A.L, A.np, A.pd
KS = A.KS
TH = A.TH
E94_RUN = EXP / "E94_Final_Unified_LightGBM" / "runs" / "20261022T061502Z"

REGIME_MEMORY = ["cumF4", "enso_run3", "tc_run3", "enso_x_rice"] + [f"run2_{c}" for c in B.NEWS_DIR]
CORE_PRICE = ["k", "F_rel", "G_rel", "F_hat_rel", "G_hat_rel", "compF_rel", "compG_rel", "mom3", "dF1", "dG1",
              "rice_yoy_now", "rice_mom3", "rice_acc"] + list(B.NEWS)
GB_CORE = dict(B.GB, min_child_samples=10, n_estimators=80)


def price_cols(arm: str) -> list[str]:
    pc, _ = B.arm_cols(True, True)
    if arm == "base":
        return pc
    if arm == "prune":
        return [c for c in pc if c not in REGIME_MEMORY]
    return CORE_PRICE


def price_part(tr, te, cols, core: bool):
    ok = tr["q"].nunique() >= 6 and tr["y_price"].sum() >= 5 and (1 - tr["y_price"]).sum() >= 5
    if not ok:
        return np.full(len(te), G.freq(tr["y_price"]) if len(tr) else 0.5)
    from lightgbm import LGBMClassifier
    mono = [1 if c in G.MONO_UP else 0 for c in cols]
    m = LGBMClassifier(**(GB_CORE if core else B.GB), monotone_constraints=mono).fit(tr[cols].astype(float), tr["y_price"])
    return m.predict_proba(te[cols].astype(float))[:, 1]


def run(d, Ps, T) -> dict:
    _, hc = B.arm_cols(True, True)
    cols = {a: price_cols(a) for a in ("base", "prune", "core")}
    out = {k: Ps[k].copy() for k in KS}
    origins = sorted({int(t) for k in KS for t in Ps[k]["t"]})
    for k in KS:
        for c in ("M-U95-BASE", "M-U95-PRUNE", "M-U95-CORE", "ph", "pp_base", "pp_prune", "pp_core"):
            out[k][c] = np.nan
    for t in origins:
        ptr = B.price_training(T, d, t)
        htr = B.hunger_rows(T, d, t, hc)
        for k in KS:
            m = out[k]["t"] == t
            if not m.any():                                   # D1: origin without rows at this K
                continue
            te = T[k][T[k]["t"] == t].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k)
            te_row = te[[c for c in hc if c != "k"]].mean().to_frame().T.assign(k=k)
            ph, _, _ = B.hunger_lin(htr, te_row, hc, d, t, k, recency=False)
            out[k].loc[m, "ph"] = ph
            for a in ("base", "prune", "core"):
                pp = price_part(ptr, te, cols[a], core=(a == "core"))
                out[k].loc[m, f"pp_{a}"] = pp
                out[k].loc[m, f"M-U95-{a.upper()}"] = ph * pp
    return out


def research_hunger_target(P: pd.DataFrame, d) -> dict:
    """Separate research target: measured regional food insecurity = SWS involuntary hunger > 11.3 at t+K (one row per
    target quarter). The framework's hunger component vs persistence, climatology (share of posted quarters above the
    line) and always-HIGH; paired per-quarter Brier sign-flip tests."""
    hq = L.h_quarters(d).set_index("q")["H"]
    g = P.groupby("target_q").agg(p=("ph", "first"), t=("t", "first")).reset_index()
    g["y"] = [int(hq[L.qi(q)] > TH["H"]) for q in g["target_q"]]
    pers, clim = [], []
    for t in g["t"]:
        h = L.h_quarters(d.cut(int(t))).sort_values("q")["H"]
        pers.append(float(h.iloc[-1] > TH["H"]))
        clim.append(float((h > TH["H"]).mean()))
    g["persist"], g["clim"], g["ah"] = pers, clim, 1.0
    res = {"n": len(g), "high": int(g["y"].sum())}
    for c in ("p", "persist", "clim", "ah"):
        res[c] = E.metrics(g["y"], (g[c] >= 0.5).astype(int), g[c])
    tests = {}
    for b in ("persist", "clim", "ah"):
        tests[b] = E.sign_flip(((g[b] - g["y"]) ** 2 - (g["p"] - g["y"]) ** 2).to_numpy())
    holm = E.holm({b: v["p_one_sided"] for b, v in tests.items()})
    res["tests"] = {b: {**tests[b], "p_holm": holm[b]} for b in tests}
    return res


SELECTABLE = ["M-U95-BASE", "M-U95-PRUNE", "M-U95-CORE"]


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E95 / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    _, Ps = U.load_tables()
    T = A.add_news_x(B.tables())
    out = run(d, Ps, T)
    summ = {"stamp": stamp, "protocol_sha256": (E95 / "PROTOCOL.sha256").read_text().split()[0], "per_k": {}, "baselines": {},
            "research_hunger_target": {}}
    for k in KS:
        P = out[k]
        P94 = pd.read_csv(E94_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
        P["M-E94-U94"], P["M-E92-DEC-S"] = P94["M-U94"].to_numpy(), P94["M-E92-DEC-S"].to_numpy()
        if k == 1:
            summ["e94_reproduced_max_abs_diff"] = float(np.nanmax(np.abs(P["M-U95-BASE"] - P["M-E94-U94"])))
        P.to_csv(o / f"predictions_k{k}.csv", index=False)
        arms = SELECTABLE + ["M-E92-DEC-S", "S-COV"]
        summ["per_k"][k], summ["baselines"][k] = U.evaluate_k(P, arms)
        summ["research_hunger_target"][k] = research_hunger_target(P, d)
    sel = {a: float(np.mean([summ["per_k"][k][a]["selection_block_brier"] for k in (1, 2, 3)])) for a in SELECTABLE}
    chosen = min(sel, key=sel.get)
    summ["selection_mean_brier"], summ["selected"] = sel, chosen
    summ["K"] = {a: U.k_validated(summ["per_k"], a) for a in SELECTABLE}
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print("E94 reproduced (max |diff|, K=1):", summ["e94_reproduced_max_abs_diff"])
    print("selection (mean Brier K=1..3, targets <= 2024-Q4):", {a: round(v, 4) for a, v in sel.items()}, "->", chosen)
    for k in KS:
        print(f"K={k}")
        for b in ("B-PERSIST", "B-CLIM", "B-AL"):
            m = summ["baselines"][k][b]
            print(f"  {b:14s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} brier={m['brier']:.3f}")
        for a in SELECTABLE + ["M-E92-DEC-S", "S-COV"]:
            r = summ["per_k"][k][a]
            m, g, ps = r["metrics"], r["generalization"], r["pass"]
            th = {b: round(v.get("p_holm", 1), 3) for b, v in r["tests"].items()}
            print(f"  {a:14s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} P/R/F1={m['precision'] or 0:.2f}/"
                  f"{m['recall_HIGH'] or 0:.2f}/{m['f1']:.2f} TP/FP/FN/TN={m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} "
                  f"brier={m['brier']:.3f} PASS={ps['PASS']} {[c for c, v in ps.items() if not v and c not in ('PASS', 'TARGET_80')]} "
                  f"holm={th} W/L={g['wins']}/{g['losses']} e/l={g['early_acc']:.2f}/{g['late_acc']:.2f} "
                  f"conf={r.get('confirmation_block', {}).get('accuracy', float('nan')):.2f}/{r.get('confirmation_block', {}).get('brier', float('nan')):.3f} chg={g['changing_acc']:.2f}", flush=True)
        h = summ["research_hunger_target"][k]
        print(f"  [research: SWS hunger>11.3, n={h['n']}, high={h['high']}] model acc={h['p']['accuracy']:.3f} brier={h['p']['brier']:.3f} | "
              f"persist {h['persist']['accuracy']:.3f}/{h['persist']['brier']:.3f} clim {h['clim']['accuracy']:.3f}/{h['clim']['brier']:.3f} "
              f"AH {h['ah']['accuracy']:.3f}/{h['ah']['brier']:.3f} holm={ {b: round(v['p_holm'], 3) for b, v in h['tests'].items()} }")
    print("K:", {a: v["K"] for a, v in summ["K"].items()})
    print(o)
