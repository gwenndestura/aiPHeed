"""E69 r2 (PROTOCOL 2, 3): province-specific skill of the existing provincial model, the Scale-2 evidence-fusion tier
(history, descriptive) and the sealed forward outlook. Also a POST-HOC sensitivity (declared after r1): the random walk
from all posted SWS rounds instead of approved rounds only.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E69_Food_Insecurity_Risk_Framework/runner/r2_province_fusion.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e69_lib as K  # noqa: E402

H, L, E, F, R, np, pd, CW = K.H, K.L, K.E, K.F, K.R, K.np, K.pd, K.CW
E68T = K.EXP / "E68_Resolve_E67_Critical_Failures" / "tables"
SUBS = K.EXP / "E27_Resolve_Forecasting_Failures" / "acquisition" / "validated" / "psa_subsistence_population_2021_2023.csv"
SAE = K.EXP / "E55_Food_Insecurity_LightGBM" / "data" / "sae2021_calabarzon_municipal.csv"


def icc(W, col):
    g = W.groupby("target")[col]
    k = 5
    msb = k * g.mean().var(ddof=1)
    msw = g.var(ddof=1).mean()
    return float((msb - msw) / (msb + (k - 1) * msw)) if (msb + (k - 1) * msw) > 0 else float("nan")


def within_auc(W, col):
    num = den = 0.0
    for _, g in W.groupby("target"):
        p, y = g[col].to_numpy(), g["HIGH"].to_numpy()
        for i in np.where(y == 1)[0]:
            for j in np.where(y == 0)[0]:
                den += 1
                num += 1.0 if p[i] > p[j] else 0.5 if p[i] == p[j] else 0.0
    return num / den if den else float("nan")


def province_skill():
    W = pd.read_csv(E68T / "r3_rows50.csv", dtype={"province_code": str})
    W["HIGH"] = W["T43"].astype(int)
    rho = icc(W, "HIGH")
    out = {"icc_T43": rho, "design_effect": 1 + 4 * rho, "n_eff": 50 / (1 + 4 * rho), "rows": 50, "quarters": 10}
    rows = []
    for a in ("A0", "N1", "K1"):
        W[f"{a}_qm"] = W.groupby("target")[f"{a}_p"].transform("mean")
        for col, lab in ((f"{a}_p", a), (f"{a}_qm", f"{a}-QMEAN")):
            yh = (W[col] >= 0.5).astype(int)
            rows.append({"reading": lab, "correct": int((yh == W["HIGH"]).sum()),
                         "brier": float(np.mean((W[col] - W["HIGH"]) ** 2)),
                         "within_quarter_auc": within_auc(W, col) if not lab.endswith("QMEAN") else 0.5})
    S = pd.DataFrame(rows)
    a0, qm = S.set_index("reading").loc["A0"], S.set_index("reading").loc["A0-QMEAN"]
    out["A0_province_skill_demonstrable"] = bool(not (abs(a0["correct"] - qm["correct"]) <= 1 and abs(a0["brier"] - qm["brier"]) <= 0.01))
    H.write_csv(S, K.TABLES / "r2_province_skill.csv")
    return out, S


def vulnerability():
    S = pd.read_csv(SUBS, dtype={"province_code": str})
    S = S[S["province_code"].isin(L.PROVS)]
    A = pd.read_csv(SAE)
    pov = A.groupby("province")["poverty_incidence_2021"].mean()
    out = {}
    for p in L.PROVS:
        s = S[S["province_code"] == p].set_index("reference_year")
        out[p] = {"province": L.NAMES[p], "subsistence2021": float(s.loc[2021, "subsistence_incidence_pct"]),
                  "subsistence2021_cv": float(s.loc[2021, "cv_pct"]), "subsistence2023": float(s.loc[2023, "subsistence_incidence_pct"]),
                  "subsistence2023_cv": float(s.loc[2023, "cv_pct"]),
                  "poverty2021_lgu_mean": round(float(pov.get(L.NAMES[p], np.nan)), 2)}
    return out


def tiers(d, X, Fh, P58):
    """Scale-2 tier at every origin with inputs (descriptive) and at the forward origins (sealed)."""
    rows = []
    for _, f in Fh.iterrows():
        t = int(f["t"])
        issue = f["issue_date"]
        h_known = np.isfinite(f["R0_RW_p_elev"])
        Hc = bool(f["R0_RW_p_elev"] >= 0.5) if h_known else None
        haz, status = CW.hazard(issue)
        for p in L.PROVS:
            xr = X[(X["t"] == t) & (X["province_code"] == p)]
            if xr.empty:
                continue
            xr = xr.iloc[0]
            headline = float(xr["F_now"] - xr["gap_now"])
            pp = P58.get((t, p))
            prods = [v for v in (xr["palay_yoy"], xr["corn_yoy"]) if np.isfinite(v)]
            Xexp = None if not prods else bool(min(prods) <= -10.0)
            A = bool((pp is not None and pp >= 0.5) or headline > R.HEADLINE_P60[p])
            if Hc is None:
                tier = "INSUFFICIENT DATA"
            elif Hc and (A or (haz and Xexp)):
                tier = "ELEVATED"
            elif Hc and haz:
                tier = "WATCH"
            else:
                tier = "NO ELEVATED SIGNAL"
            rows.append({"t": t, "origin_quarter": L.qs(t), "issue_date": issue, "target": L.qs(t + 2), "province_code": p,
                         "province": L.NAMES[p], "H_hat": f["R0_RW_hat"], "P_hunger_elevated": f["R0_RW_p_elev"],
                         "H_component": Hc, "P_price": pp, "headline_at_issue": headline, "headline_usual": R.HEADLINE_P60[p],
                         "A_component": A, "C_component": bool(haz), "C_status": status, "X_component": Xexp,
                         "palay_yoy": xr["palay_yoy"], "corn_yoy": xr["corn_yoy"], "tier": tier})
    return pd.DataFrame(rows)


def main():
    K.verify_protocol()
    d, X, B = E.load()
    skill, S = province_skill()
    Fh = pd.read_csv(K.TABLES / "r1_regional_hunger_forecasts.csv")
    # P_price of the served model where available: sealed E57 rows (eval origins) and the E58 record / E68 seal (forward)
    E57 = pd.read_csv(H.SEALED["E57"], dtype={"province_code": str})
    P58 = {(int(r.t), r.province_code): float(r.E56_p_price) for r in E57.itertuples()}
    Sx = pd.read_csv(K.EXP / "E68_Resolve_E67_Critical_Failures" / "sealed" / "prospective.csv", dtype={"province_code": str})
    for r in Sx[Sx["arm"] == "A0"].itertuples():
        P58[(L.qi(r.origin_quarter), r.province_code)] = float(r.p_price)
    T = tiers(d, X, Fh, P58)
    Y = R.labels(d).set_index(["province_code", "quarter"])
    T["T43"] = [Y.loc[(p, q), "T43"] if (p, q) in Y.index else np.nan for p, q in zip(T["province_code"], T["target"])]
    T["TAFF"] = [Y.loc[(p, q), "TAFF"] if (p, q) in Y.index else np.nan for p, q in zip(T["province_code"], T["target"])]
    Hq = K.outcome()
    T["E1_observed"] = T["target"].map(lambda q: (Hq.get(L.qi(q), np.nan) > K.C_ELEV) if L.qi(q) in Hq.index else np.nan)
    hist = T[T["t"].isin(K.ORIGINS)]
    fwd = T[T["t"].isin(K.FORWARD)].copy()
    xt43 = pd.crosstab(hist["tier"], hist["T43"].fillna(-1)).to_dict()
    xtaff = pd.crosstab(hist["tier"], hist["TAFF"].fillna(-1)).to_dict()
    by_year = hist.assign(year=hist["target"].str[:4]).groupby(["year", "tier"]).size().unstack(fill_value=0)
    H.write_csv(hist, K.TABLES / "r2_tier_history.csv")
    H.write_csv(by_year.reset_index(), K.TABLES / "r2_tier_by_year.csv")
    vul = vulnerability()
    # POST-HOC sensitivity (declared after r1): random walk from all posted rounds (approved + supplementary)
    Yo = K.outcome()
    ph = []
    for t in K.ORIGINS:
        hs_all = R.P2.h_series(d, t, True)
        b_all = K.base(hs_all, t)
        if (t + 2) in Yo.index:
            ph.append({"target": L.qs(t + 2), "H_true": float(Yo[t + 2]), "RW_approved": K.base(K.posted(d, t), t),
                       "RW_all_rounds": b_all})
    PH = pd.DataFrame(ph)
    post_hoc = {"MAE_RW_approved": float(np.mean(np.abs(PH["H_true"] - PH["RW_approved"]))),
                "MAE_RW_all_rounds": float(np.mean(np.abs(PH["H_true"] - PH["RW_all_rounds"]))), "quarters": int(len(PH)),
                "note": "post hoc, not used for selection"}
    H.write_csv(PH, K.TABLES / "r2_posthoc_rw_all_rounds.csv")
    # seal the forward outlook: Scale-1 forecasts of every candidate + Scale-2 tiers
    f1 = Fh[Fh["t"].isin(K.FORWARD)]
    seal = K.SEALED / "outlook_forward.csv"
    if seal.exists():
        raise SystemExit("forward outlook already sealed; never re-seal")
    sealed = fwd.merge(f1[["t"] + [c for c in f1.columns if c.startswith("R")]], on="t", how="left")
    H.write_csv(sealed, seal)
    (K.SEALED / "outlook_forward.csv.sha256").write_text(hashlib.sha256(seal.read_bytes()).hexdigest() + "  outlook_forward.csv\n")
    H.dump({"protocol_sha256": K.verify_protocol(), "province_skill": skill, "vulnerability": vul,
            "tier_vs_T43": {str(k): {str(a): int(b) for a, b in v.items()} for k, v in xt43.items()},
            "tier_vs_TAFF": {str(k): {str(a): int(b) for a, b in v.items()} for k, v in xtaff.items()},
            "post_hoc_rw": post_hoc, "sealed_sha256": hashlib.sha256(seal.read_bytes()).hexdigest(),
            "forward_tiers": {f"{r.target} {r.province}": r.tier for r in fwd.itertuples()}}, K.OUT / "r2_province_fusion.json")
    pd.set_option("display.width", 250)
    print(S.round(3).to_string()); print(skill)
    print(by_year.to_string()); print(pd.crosstab(hist["tier"], hist["T43"])); print(pd.crosstab(hist["tier"], hist["TAFF"]))
    print(fwd[["target", "province", "P_hunger_elevated", "P_price", "headline_at_issue", "headline_usual", "A_component",
               "C_component", "X_component", "tier"]].round(3).to_string())
    print(json.dumps(vul, indent=1)); print(post_hoc)


if __name__ == "__main__":
    main()
