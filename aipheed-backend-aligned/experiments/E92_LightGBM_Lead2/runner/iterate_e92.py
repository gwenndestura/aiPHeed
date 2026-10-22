"""E92 round 2 (POST-HOC, reported as such; cannot replace the pre-registered selection). Run from backend/.

M-LGB-LIN: the hunger part becomes a LightGBM regressor with linear trees (linear_tree=True, which can extrapolate
beyond the training range) on the hunger change H(t+k) - H_last, pooled over horizons, with news as a required input.
P(hunger > 11.3) = Phi((H_last + predicted change - 11.3) / s), s = training residual RMSE (at least the posted-history
step sd scaled by the gap). Price part: the selected LightGBM price classifier with news (M-LGB-DEC-S). Below 8
training rows the predicted change is the training mean change.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_e92 as G  # noqa: E402

U, E, L, np, pd = G.U, G.E, G.L, G.np, G.pd
from scipy.stats import norm  # noqa: E402

RUN = Path(sys.argv[1])
REG = dict(objective="regression", num_leaves=4, max_depth=2, n_estimators=100, learning_rate=0.05, min_child_samples=3,
           reg_lambda=5.0, linear_tree=True, linear_lambda=1.0, random_state=92, deterministic=True, n_jobs=1,
           force_row_wise=True, verbosity=-1)


def hunger_lin(T, d, t, te_row, hf, k):
    from lightgbm import LGBMRegressor
    hs = L.h_quarters(d.cut(t)).sort_values("q")
    hq = hs.set_index("q")["H"]
    qq, hh = hs["q"].to_numpy(), hs["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    s_min = sig * math.sqrt(max(t + k - int(qq[-1]), 1))
    rows = []
    for kk in G.KS_TRAIN:
        R = T[kk][T[kk]["t"] + kk <= t - 1]
        g = R.groupby("t")[hf[1:]].mean().reset_index()
        for _, r in g.iterrows():
            q = int(r["t"]) + kk
            if q in hq.index:
                rows.append({**r.to_dict(), "k": kk, "dH": hq[q] - (r["H_rel"] + G.TH["H"])})
    tr = pd.DataFrame(rows)
    H_last = float(te_row["H_rel"].iloc[0]) + G.TH["H"]
    if len(tr) < 8:
        return float(1 - norm.cdf((G.TH["H"] - (H_last + (tr["dH"].mean() if len(tr) else 0.0))) / s_min)), False
    A, B = tr[hf].astype(float), te_row[hf].astype(float)
    med = A.median()
    A, B = A.fillna(med).fillna(0.0), B.fillna(med).fillna(0.0)
    m = LGBMRegressor(**REG).fit(A, tr["dH"])
    rmse = float(np.sqrt(np.mean((tr["dH"] - m.predict(A)) ** 2)))
    Hh = H_last + float(m.predict(B)[0])
    return float(1 - norm.cdf((G.TH["H"] - Hh) / max(s_min, rmse))), True


if __name__ == "__main__":
    d, _ = E.data()
    T = {k: G.prep(pd.read_csv(U.TABLES / f"features_k{k}.csv", dtype={"province_code": str})) for k in (1, 2, 3)}
    hf = G.HUNGER_F + G.NEWS
    out = {}
    for k in G.LEADS:
        P = pd.read_csv(RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
        P["M-LGB-LIN"], P["fit_lin"] = np.nan, False
        for t in sorted(P["t"].unique()):
            m = P["t"] == t
            te = T[k][T[k]["t"] == t].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k)
            te_row = te[hf[1:]].mean().to_frame().T.assign(k=k)
            ph, f = hunger_lin(T, d, int(t), te_row, hf, k)
            P.loc[m, "M-LGB-LIN"] = ph * P.loc[m, "p_price_lgb_s"].to_numpy()
            P.loc[m, "fit_lin"] = f
        P.to_csv(RUN / f"predictions_round2_k{k}.csv", index=False)
        r, base = U.evaluate_k(P, ["M-LGB-LIN", "M-LGB-DEC-S", "S-COV"])
        out[k] = r
        print(f"Lead {k} fitted share {P['fit_lin'].mean():.2f}")
        for a in ["M-LGB-LIN", "M-LGB-DEC-S", "S-COV"]:
            mm, g, ps = r[a]["metrics"], r[a]["generalization"], r[a]["pass"]
            th = {b: round(v.get("p_holm", 1), 3) for b, v in r[a]["tests"].items()}
            print(f"  {a:12s} acc={mm['accuracy']:.3f} bal={mm['balanced_accuracy'] or 0:.3f} R={mm['recall_HIGH'] or 0:.2f} "
                  f"TP/FP/FN/TN={mm['TP']}/{mm['FP']}/{mm['FN']}/{mm['TN']} brier={mm['brier']:.3f} PASS={ps['PASS']} "
                  f"{[c for c, v in ps.items() if not v and c not in ('PASS', 'TARGET_80')]} holm={th} "
                  f"W/L={g['wins']}/{g['losses']} early/late={g['early_acc']:.2f}/{g['late_acc']:.2f}", flush=True)
    (RUN / "round2_posthoc.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
