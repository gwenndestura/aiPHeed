"""E69 r1 (PROTOCOL 1): Lead-2 forecasts of the observed SWS Balance Luzon hunger outcome by R0-R5, scored on every
eligible quarter; paired comparison against R0; selection for Scale 2.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E69_Food_Insecurity_Risk_Framework/runner/r1_regional_hunger.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e69_lib as K  # noqa: E402

H, L, E, np, pd = K.H, K.L, K.E, K.np, K.pd
from scipy.stats import binomtest  # noqa: E402


def score(D, m):
    g = D.dropna(subset=[f"{m}_hat", "H_true"])
    y, yh = g["H_true"].to_numpy(float), g[f"{m}_hat"].to_numpy(float)
    e1, p1 = (y > K.C_ELEV).astype(int), g[f"{m}_p_elev"].to_numpy(float)
    d1 = (p1 >= 0.5).astype(int)
    rise = (y - g["base"].to_numpy(float) >= K.C_RISE).astype(int)
    prise = (g[f"{m}_p_rise"].to_numpy(float) >= 0.5).astype(int)
    tp, tn = int(((d1 == 1) & (e1 == 1)).sum()), int(((d1 == 0) & (e1 == 0)).sum())
    return {"model": m, "quarters": int(len(g)), "MAE": float(np.mean(np.abs(y - yh))),
            "RMSE": float(np.sqrt(np.mean((y - yh) ** 2))), "E1_events": int(e1.sum()),
            "E1_accuracy": float((d1 == e1).mean()), "E1_correct": int((d1 == e1).sum()),
            "E1_recall_elevated": tp / max(e1.sum(), 1), "E1_recall_not": tn / max((1 - e1).sum(), 1),
            "E1_balanced": 0.5 * (tp / max(e1.sum(), 1) + tn / max((1 - e1).sum(), 1)) if 0 < e1.sum() < len(e1) else float("nan"),
            "E1_brier": float(np.mean((p1 - e1) ** 2)), "E2_events": int(rise.sum()),
            "E2_hits": int(((prise == 1) & (rise == 1)).sum()), "E2_false_alarms": int(((prise == 1) & (rise == 0)).sum()),
            "noise_floor_MAE": float(np.sqrt(2) * K.NOISE_SE * np.sqrt(2 / np.pi))}


def paired(D, m, ref="R0_RW", n_boot=2000, seed=69):
    g = D.dropna(subset=[f"{m}_hat", f"{ref}_hat", "H_true"])
    d = np.abs(g["H_true"] - g[f"{m}_hat"]).to_numpy() - np.abs(g["H_true"] - g[f"{ref}_hat"]).to_numpy()
    rng = np.random.default_rng(seed)
    boots = [float(np.mean(rng.choice(d, len(d)))) for _ in range(n_boot)]
    w, l_ = int((d < -1e-9).sum()), int((d > 1e-9).sum())
    p = binomtest(w, w + l_, 0.5, alternative="greater").pvalue if w + l_ else 1.0
    return {"model": m, "reference": ref, "quarters": int(len(d)), "mean_abs_err_diff": float(d.mean()),
            "ci95_lo": float(np.quantile(boots, .025)), "ci95_hi": float(np.quantile(boots, .975)),
            "wins": w, "losses": l_, "sign_p": float(p), "better_than_RW": bool(np.quantile(boots, .975) < 0 and p < 0.05)}


def main():
    K.verify_protocol()
    d, X, B = E.load()
    Y = K.outcome()
    rows = []
    for t in K.ORIGINS + K.FORWARD:
        f = K.forecast(d, X, t)
        r = {"t": t, "origin_quarter": L.qs(t), "issue_date": str(L.origin(t).date()), "target": L.qs(t + 2),
             "H_true": float(Y[t + 2]) if (t + 2) in Y.index and t not in K.FORWARD else np.nan,
             "base": f["base"], "n_pairs": f["n_pairs"]}
        for m in K.MODELS:
            v = f[m]
            if v is None:
                r[f"{m}_hat"] = r[f"{m}_sigma"] = r[f"{m}_p_elev"] = r[f"{m}_p_rise"] = np.nan
                continue
            r[f"{m}_hat"], r[f"{m}_sigma"] = v
            r[f"{m}_p_elev"] = K.p_above(v[0], v[1], K.C_ELEV)
            r[f"{m}_p_rise"] = K.p_above(v[0], v[1], f["base"] + K.C_RISE)
        rows.append(r)
        print(r["origin_quarter"], r["target"], r["H_true"], round(r["base"], 1),
              {m: round(r[f"{m}_hat"], 1) for m in K.MODELS if np.isfinite(r[f"{m}_hat"])}, flush=True)
    D = pd.DataFrame(rows)
    ev = D[D["t"].isin(K.ORIGINS) & D["H_true"].notna()]
    excluded = D[D["t"].isin(K.ORIGINS) & D["H_true"].isna()]["target"].tolist()
    common = ev.dropna(subset=[f"{m}_hat" for m in K.MODELS])
    S_all = pd.DataFrame([score(ev, m) for m in K.MODELS])
    S_com = pd.DataFrame([score(common, m) for m in K.MODELS])
    P = pd.DataFrame([paired(common, m) for m in K.MODELS[1:]])
    best = S_com.sort_values(["MAE"]).iloc[0]["model"]
    selected = best if (best != "R0_RW" and bool(P.set_index("model").loc[best, "better_than_RW"])) else "R0_RW"
    H.write_csv(D, K.TABLES / "r1_regional_hunger_forecasts.csv")
    H.write_csv(S_all, K.TABLES / "r1_scores_all_available.csv")
    H.write_csv(S_com, K.TABLES / "r1_scores_common_origins.csv")
    H.write_csv(P, K.TABLES / "r1_paired_vs_RW.csv")
    # sampling-noise share: how many observed quarter-to-quarter changes exceed the 5-point noise band
    s = K.outcome().sort_index()
    ch = s.diff().dropna()
    ch = ch[(s.index[1:] - s.index[:-1]) == 1]
    H.dump({"protocol_sha256": K.verify_protocol(), "eligible_quarters": int(len(ev)), "common_quarters": int(len(common)),
            "excluded_targets_no_round": excluded, "lowest_MAE_common": best, "selected_for_scale2": selected,
            "consecutive_changes": int(len(ch)), "changes_beyond_5pts": int((ch.abs() >= K.C_RISE).sum()),
            "E1_base_rate_common": float((common["H_true"] > K.C_ELEV).mean())}, K.OUT / "r1_regional_hunger.json")
    pd.set_option("display.width", 250)
    print(S_all.round(3).to_string()); print(S_com.round(3).to_string()); print(P.round(3).to_string())
    print("selected", selected, "common", len(common), "eligible", len(ev), "excluded", excluded)


if __name__ == "__main__":
    main()
