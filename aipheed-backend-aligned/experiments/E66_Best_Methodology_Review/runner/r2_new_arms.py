"""E66 r2 (PROTOCOL 2.2): the new arms N1 LR-MATCHED and N2 LR-PROJ (L2 logistic regression for the price part on the
E56 training frame at each E57 origin) and N3 RW-HUNGER (E56 P_price x E61 random-walk hunger part).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r2_new_arms.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e66_lib as H  # noqa: E402

sys.path.insert(0, str(H.EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

np, pd = H.np, H.pd
F, L, E = G.F, G.L, G.E
EVAL_ORIGINS = list(range(L.qi("2023-Q4"), L.qi("2026-Q1") + 1))
FORWARD_ORIGINS = [L.qi("2026-Q2"), L.qi("2026-Q3")]
PROJ = ["dfood_0.0", "dgap_0.0"]
ARMS = {"N1": PROJ + F.feature_cols("market"), "N2": PROJ}


def lr_fit_predict(tr: pd.DataFrame, te: pd.DataFrame, cols: list[str]) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    fit = tr.dropna(subset=["PS"] + PROJ)
    y = fit["PS"].to_numpy(int)
    if len(set(y)) < 2:
        return np.full(len(te), y.mean())
    Xtr, Xte = fit[cols].astype(float).copy(), te[cols].astype(float).copy()
    med = Xtr.median()
    for c in cols:                                   # median imputation + missing indicator (training statistics)
        if Xtr[c].isna().any() or Xte[c].isna().any():
            Xtr[c + "_na"], Xte[c + "_na"] = Xtr[c].isna().astype(float), Xte[c].isna().astype(float)
        Xtr[c], Xte[c] = Xtr[c].fillna(med[c] if np.isfinite(med[c]) else 0.0), Xte[c].fillna(med[c] if np.isfinite(med[c]) else 0.0)
    keep = [c for c in Xtr.columns if Xtr[c].std() > 0]
    sc = StandardScaler().fit(Xtr[keep])
    m = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xtr[keep]), y)
    return m.predict_proba(sc.transform(Xte[keep]))[:, 1]


def main():
    H.verify_protocol()
    H.verify_sealed()
    d, X, B = E.load()
    S = pd.read_csv(H.SEALED["E57"], dtype={"province_code": str})
    rows = []
    for t in EVAL_ORIGINS + FORWARD_ORIGINS:
        tr, te = F.frame(d, X, B, t, "AS")
        if not E.ok(tr, te):
            raise SystemExit(f"origin {L.qs(t)} not eligible")
        hc = F.hunger(d, X, t)
        assert list(te["province_code"]) == list(L.PROVS)
        out = {a: lr_fit_predict(tr, te, cols) for a, cols in ARMS.items()}
        for i, p in enumerate(L.PROVS):
            r = {"t": t, "origin_quarter": L.qs(t), "target": L.qs(t + 2), "province_code": p,
                 "p_hunger": float(hc["p"]), "n_train_rows": int(len(tr)), "n_train_PS": int(tr["PS"].sum())}
            for a in ARMS:
                r[f"{a}_p_price"] = float(out[a][i])
                r[f"{a}_p"] = float(hc["p"] * out[a][i])
            rows.append(r)
        print(L.qs(t), {a: np.round(v, 3).tolist() for a, v in out.items()}, flush=True)
    R = pd.DataFrame(rows)
    # the hunger part must equal E56's sealed hunger part on the evaluation rows
    chk = R.merge(S[["t", "province_code", "E56_p_hunger"]], on=["t", "province_code"])
    err = float((chk["p_hunger"] - chk["E56_p_hunger"]).abs().max())
    if err > 1e-9:
        raise SystemExit(f"hunger part differs from the sealed E56 hunger part ({err})")
    hv = pd.read_csv(H.E61_HUNGER)[["target", "H2_p_hunger"]]
    R = R.merge(hv, on="target", how="left")
    S2 = S[["t", "province_code", "E56_p_price"]]
    R = R.merge(S2, on=["t", "province_code"], how="left")
    R["N3_p"] = R["E56_p_price"] * R["H2_p_hunger"]
    H.write_csv(R, H.TABLES / "r2_new_arm_predictions.csv")
    H.dump({"protocol_sha256": H.verify_protocol(), "hunger_part_max_abs_diff_vs_E56": err,
            "rows": int(len(R)), "arms": {a: c for a, c in ARMS.items()}}, H.OUT / "r2_new_arms.json")


if __name__ == "__main__":
    main()
