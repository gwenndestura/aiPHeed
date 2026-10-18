"""E58 step 3 (PROTOCOL section 3): candidate warning probabilities at every E57 rolling origin, SEALED before any
outcome is read. E56 quantities are taken from the sealed E57 forecasts; C2, C3, C4, B-RECENT-RISE and B-PROJ are
computed here from data published before each origin.

    backend/venv/Scripts/python.exe -B runner/e58_predict.py  -> sealed/predictions.csv (+ .sha256)
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E58 = Path(__file__).resolve().parents[1]
EXP = E58.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, I7, L, np, pd = G.E, G.F, G.I7, G.L, G.np, G.pd
E57_SEALED = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
SEALED = E58 / "sealed" / "predictions.csv"
TAUS = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
RISE_PTS = 1.0
C4_LGB = dict(F.LGB_BASE, num_leaves=2, n_estimators=40, learning_rate=0.05, min_child_samples=10, reg_lambda=10.0,
              random_state=58)


def verify():
    want = (E58 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    if hashlib.sha256((E58 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    seal57 = (E57_SEALED.parent / "predictions.csv.sha256").read_text().split()[0]
    if hashlib.sha256(E57_SEALED.read_bytes()).hexdigest() != seal57:
        raise SystemExit("E57 sealed forecasts changed")


def c2_tau(tr, c):
    """Training-only threshold: F2 of the price part's inner forward-chaining OOF probabilities vs PS labels."""
    cols = G.cols_for(c)
    oof = []
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit = tr[tr["q"].isin(fq)].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if len(fit) and len(hold):
            oof.append(hold.assign(p_oof=G.PriceLGB2(cols, c).fit(fit).predict(hold)))
    if not oof:
        return 0.5, 0
    o = pd.concat(oof)
    y = o["PS"].to_numpy()

    def f2(tau):
        yh = (o["p_oof"].to_numpy() >= tau).astype(int)
        tp, fp, fn = ((yh == 1) & (y == 1)).sum(), ((yh == 1) & (y == 0)).sum(), ((yh == 0) & (y == 1)).sum()
        return 5 * tp / (5 * tp + 4 * fn + fp) if tp else 0.0
    return max(TAUS, key=lambda tau: (round(f2(tau), 10), tau)), int(len(o))


def rise_label(c_cut, tprime, p, F_true, G_true):
    """RISEP for a training row issued at O(tprime): target value vs the latest complete CPI quarter at that origin (t'-1)."""
    Fq = L.quarter_F(c_cut).set_index(["province_code", "q"])["F"]
    Hq = L.quarter_F(c_cut, "all_items").set_index(["province_code", "q"])["F"]
    k = (p, tprime - 1)
    if k not in Fq.index or k not in Hq.index:
        return np.nan
    return float((F_true - Fq[k] >= RISE_PTS) or ((G_true) - (Fq[k] - Hq[k]) >= RISE_PTS))


def main():
    verify()
    if SEALED.exists():
        raise SystemExit("already sealed")
    S = pd.read_csv(E57_SEALED, dtype={"province_code": str})
    d, X, B = E.load()
    space = G.search_space()
    cw_space = [c for c in space if c["cw"] == "balanced"]
    out = []
    for t, g in S.groupby("t"):
        t = int(t)
        c = space[int(g["E56_config"].iloc[0])]
        tr, te = F.frame(d, X, B, t, "AS")
        tau, n_oof = c2_tau(tr, c)
        c3 = G.tuned_forecast(d, X, B, t, cw_space)
        # C4 stage 1: rising-price classifier on as-of RISEP labels of training targets <= t-1
        cut = d.cut(t)
        trr = tr.copy()
        trr["RISEP"] = [rise_label(cut, int(tp), p, ft, gt) for tp, p, ft, gt in
                        zip(trr["t"], trr["province_code"], trr["F_true"], trr["G_true"])]
        trr = trr.dropna(subset=["RISEP"])
        rcols = F.feature_cols("all") + ["proj_dF", "proj_dG"]
        for fr in (trr, te):
            fr["proj_dF"] = fr["base_0.0"] - fr["F_now"]
            fr["proj_dG"] = fr["gbase_0.0"] - fr["gap_now"]
        npos, nneg = int(trr["RISEP"].sum()), int((trr["RISEP"] == 0).sum())
        if npos >= 10 and nneg >= 10:
            import lightgbm as lgb
            m4 = lgb.LGBMClassifier(**{k: v for k, v in C4_LGB.items() if k != "objective"}, objective="binary")
            m4.fit(trr[rcols].astype(float), trr["RISEP"].astype(int))
            p_rise = m4.predict_proba(te[rcols].astype(float))[:, 1]
        else:
            p_rise = np.full(len(te), np.nan)
        # B-PROJ: structural projection probability (m = 1.0), scale from training rows
        fit1 = tr.dropna(subset=["base_1.0", "gbase_1.0", "F_true", "G_true"])
        p_proj = F._sig(F.struct_logit(te, 1.0, F.struct_scale(fit1, 1.0)))
        # B-RECENT-RISE: latest complete quarter (t-1) vs the one before (t-2), as published at O(t)
        Fq = L.quarter_F(cut).set_index(["province_code", "q"])["F"]
        Hq = L.quarter_F(cut, "all_items").set_index(["province_code", "q"])["F"]
        te = te.set_index("province_code")
        for r in g.itertuples():
            p = r.province_code
            f1, f2_, h1, h2 = (Fq.get((p, t - 1)), Fq.get((p, t - 2)), Hq.get((p, t - 1)), Hq.get((p, t - 2)))
            recent = float((f1 - f2_ >= RISE_PTS) or ((f1 - h1) - (f2_ - h2) >= RISE_PTS)) if None not in (f1, f2_, h1, h2) else np.nan
            i = list(L.PROVS).index(p)
            out.append({"t": t, "origin_quarter": L.qs(t), "target": L.qs(t + 2), "province_code": p, "province": L.NAMES[p],
                        "E56_p": r.E56_p, "E56_p_price": r.E56_p_price, "E56_p_hunger": r.E56_p_hunger,
                        "C2_tau": tau, "C2_n_oof": n_oof, "C3_p": float(c3["p"][i]), "C3_config": int(c3["cfg"]["id"]),
                        "C4_p_rise": float(p_rise[i]), "C4_train_pos": npos, "C4_train_neg": nneg,
                        "BPROJ_p": float(p_proj[i]), "BRECENT_flag": recent,
                        "PERSIST_p": r.PERSIST_p, "PERSIST_from": r.PERSIST_from, "CLIM_p": r.CLIM_p,
                        "H_last_known": r.H_last_known})
        print("origin", L.qs(t), "tau", tau, "C3 cfg", c3["cfg"]["id"], "C4 train", npos, nneg, flush=True)
    SEALED.parent.mkdir(exist_ok=True)
    pd.DataFrame(out).sort_values(["t", "province_code"]).to_csv(SEALED, index=False, float_format="%.12g")
    (SEALED.parent / "predictions.csv.sha256").write_text(hashlib.sha256(SEALED.read_bytes()).hexdigest() + "  predictions.csv\n")
    print("sealed", len(out))


if __name__ == "__main__":
    main()
