"""E41 single evaluation run under the frozen PROTOCOL.md (run once; a byte-identical repeat may follow).

    backend/venv/Scripts/python.exe -B runner/e41_evaluate.py
      -> runs/<UTC stamp>/{predictions_lead2.csv, predictions_lead1.csv, results.json}
      -> frozen/E41_PROSPECTIVE_2027Q1.json (+ .sha256)   origin 2026-10-01

Prints aggregate metrics only (CONTAMINATION_LOG.md C-1).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

sys.dont_write_bytecode = True
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e41_lib as L  # noqa: E402

np, pd = L.np, L.pd
BASE = ["B0_majority", "B1_persistence", "B2_latest_month", "B3_seasonal"]
OPERATIONAL_T = L.qi("2026-Q3")                                    # O = 2026-10-01
E40_DEV = (L.qi("2023-Q1"), L.qi("2025-Q1"))


def verify_protocol() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((L.E41 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------- forecasts
def baselines(d, t: int, k: int) -> pd.DataFrame:
    c = d.cut(t)
    lab = L.fpp_labels(c)
    F = lab.set_index(["province_code", "q"])["F"]
    yl = lab.set_index(["province_code", "q"])["y"]
    tr = lab[lab["q"] <= t - 1]
    rate = (tr["y"].sum() + 1) / (len(tr) + 2)
    X = L.features(c, t).set_index("province_code")
    rows = []
    for p in L.PROVS:
        fl, fn = F.get((p, t - 1), np.nan), X.loc[p, "F_now"]
        ys = yl.get((p, t + k - 4), np.nan)
        rows.append({"t": t, "target_q": t + k, "province_code": p,
                     "B0_majority_p": rate, "B0_majority_yhat": int(rate > 0.5),
                     "B1_persistence_F": fl, "B1_persistence_yhat": int(fl > L.FPP_THRESHOLD) if pd.notna(fl) else np.nan,
                     "B2_latest_month_F": fn, "B2_latest_month_yhat": int(fn > L.FPP_THRESHOLD) if pd.notna(fn) else np.nan,
                     "B3_seasonal_yhat": ys})
    b = pd.DataFrame(rows)
    for m in ("B1_persistence", "B2_latest_month", "B3_seasonal"):
        b[f"{m}_p"] = b[f"{m}_yhat"].astype(float)
    return b


def forecasts(d, origins: list[int], k: int, X_all: pd.DataFrame, ml: bool) -> tuple[pd.DataFrame, dict]:
    m1 = L.m1_forecasts(d, origins, k)
    m1z = L.m1_forecasts(d, origins, k, zero_drift=True)
    P = m1[["t", "target_q", "province_code", "F_hat", "s", "s_theory", "s_track", "p", "n_drift"]].rename(
        columns={"F_hat": "M1_F", "s": "M1_s", "s_theory": "M1_s_theory", "s_track": "M1_s_track", "p": "M1_p"})
    P["M1_yhat"] = np.where(P["M1_F"].notna(), (P["M1_F"] > L.FPP_THRESHOLD).astype(float), np.nan)
    P = P.merge(m1z[["t", "province_code", "F_hat", "p"]].rename(columns={"F_hat": "M1z_F", "p": "M1z_p"}),
                on=["t", "province_code"])
    P["M1z_yhat"] = np.where(P["M1z_F"].notna(), (P["M1z_F"] > L.FPP_THRESHOLD).astype(float), np.nan)
    P = P.merge(pd.concat([baselines(d, t, k) for t in origins]), on=["t", "target_q", "province_code"])
    diag = {"shap_by_origin": {}, "ablation_rows": [], "single_rows": []}
    if ml:
        P["M2_p"] = np.nan
        P["M3_p"] = np.nan
        for t in origins:
            c = d.cut(t)
            tr = L.training_pairs(X_all, c, t, k)
            te = X_all[X_all["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
            sel = P["t"] == t
            pl = L.fit_predict_lr(tr, te)
            if pl is not None:
                P.loc[sel, "M2_p"] = pl
            mdl = L.fit_lgbm(tr, L.FEATURES)
            if mdl is not None:
                P.loc[sel, "M3_p"] = mdl.predict_proba(te[L.FEATURES].astype(float))[:, 1]
                diag["shap_by_origin"][L.qs(t)] = L.group_shap(mdl, te, L.FEATURES)
                for g, fs in L.GROUPS.items():
                    if not fs:
                        continue
                    cols = [f for f in L.FEATURES if f not in fs]
                    ma = L.fit_lgbm(tr, cols)
                    ms = L.fit_lgbm(tr, fs)
                    for name, mm, cc, store in ((f"drop_{g}", ma, cols, "ablation_rows"), (f"only_{g}", ms, fs, "single_rows")):
                        pv = mm.predict_proba(te[cc].astype(float))[:, 1] if mm is not None else [np.nan] * 5
                        for pcode, v in zip(te["province_code"], pv):
                            diag[store].append({"arm": name, "t": t, "target_q": t + k, "province_code": pcode, "p": v})
        for m in ("M2", "M3"):
            P[f"{m}_yhat"] = np.where(P[f"{m}_p"].notna(), (P[f"{m}_p"] >= 0.5).astype(float), np.nan)
    return P, diag


def attach_truth(P: pd.DataFrame, d) -> pd.DataFrame:
    lab = L.fpp_labels(d).rename(columns={"q": "target_q", "F": "F_true", "y": "y"})
    return P.merge(lab, on=["province_code", "target_q"], how="left")


# --------------------------------------------------------------------------------------------- scoring
def arm_block(S: pd.DataFrame, arm: str, cont: bool) -> dict:
    g = S.dropna(subset=[f"{arm}_yhat", "y"])
    m = L.cls_metrics(g["y"], g[f"{arm}_yhat"], g[f"{arm}_p"])
    m["accuracy_ci95"] = L.date_bootstrap(g, lambda s: float((s[f"{arm}_yhat"] == s["y"]).mean()))
    m["balanced_ci95"] = L.date_bootstrap(
        g, lambda s: L.cls_metrics(s["y"], s[f"{arm}_yhat"])["balanced_accuracy"])
    m["brier_ci95"] = L.date_bootstrap(g, lambda s: float(((s[f"{arm}_p"] - s["y"]) ** 2).mean()))
    m["citl_ci95"] = L.date_bootstrap(g, lambda s: float(s["y"].mean() - s[f"{arm}_p"].mean()))
    m["dates"] = int(g["target_q"].nunique())
    if cont and f"{arm}_F" in g:
        e = (g[f"{arm}_F"] - g["F_true"]).dropna()
        m["MAE_F"], m["RMSE_F"] = float(e.abs().mean()), float(np.sqrt((e ** 2).mean()))
    return m


def per_date(S: pd.DataFrame, arm: str) -> pd.DataFrame:
    g = S.assign(acc=(S[f"{arm}_yhat"] == S["y"]).astype(float), br=(S[f"{arm}_p"] - S["y"]) ** 2)
    return g.groupby("target_q")[["acc", "br"]].mean()


def compare(S: pd.DataFrame, cand: str, others: list[str]) -> dict:
    out, pb = {}, {}
    c = per_date(S, cand)
    for o in others:
        b = per_date(S, o)
        acc = L.sign_flip((c["acc"] - b["acc"]).to_numpy())
        br = L.sign_flip((b["br"] - c["br"]).to_numpy())
        out[o] = {"accuracy_gain": acc, "brier_gain": br}
        pb[o] = br["p_one_sided"]
    for o, ph in L.holm(pb).items():
        out[o]["brier_gain"]["p_one_sided_holm"] = ph
    return out


def calibration(S: pd.DataFrame, arm: str) -> dict:
    from sklearn.linear_model import LogisticRegression
    g = S.dropna(subset=[f"{arm}_p", "y"])
    p = np.clip(g[f"{arm}_p"].to_numpy(float), 1e-4, 1 - 1e-4)
    lg = np.log(p / (1 - p)).reshape(-1, 1)
    slope = float(LogisticRegression(C=1e6, max_iter=5000).fit(lg, g["y"]).coef_[0][0]) if g["y"].nunique() == 2 else None
    bands = []
    for lo, hi, name in ((0, 1 / 3, "Low"), (1 / 3, 2 / 3, "Watch"), (2 / 3, 1.01, "High")):
        b = g[(g[f"{arm}_p"] >= lo) & (g[f"{arm}_p"] < hi)]
        bands.append({"band": name, "n": int(len(b)), "mean_p": float(b[f"{arm}_p"].mean()) if len(b) else None,
                      "observed_HIGH_rate": float(b["y"].mean()) if len(b) else None})
    return {"slope": slope, "bands": bands}


def breakdown(S: pd.DataFrame, arms: list[str]) -> dict:
    out = {"province": {}, "year": {}}
    for p in L.PROVS:
        g = S[S["province_code"] == p]
        out["province"][L.NAMES[p]] = {a: float((g[f"{a}_yhat"] == g["y"]).mean()) for a in arms} | {
            "n": int(len(g)), "HIGH": int(g["y"].sum())}
    for y in sorted({q // 4 for q in S["target_q"]}):
        g = S[S["target_q"] // 4 == y]
        out["year"][str(y)] = {a: float((g[f"{a}_yhat"] == g["y"]).mean()) for a in arms} | {
            "n": int(len(g)), "HIGH": int(g["y"].sum())}
    return out


def gates(res: dict, cmp: dict, leakage_ok: bool) -> dict:
    m = res["M1"]
    g = {"G0_validity": leakage_ok,
         "G1_accuracy_ge_0.75": m["accuracy"] >= 0.75,
         "G2_not_degenerate": (m["balanced_accuracy"] or 0) >= 0.70 and (m["recall_HIGH"] or 0) >= 0.60
         and (m["recall_LOW"] or 0) >= 0.60,
         "G3a_point_better_than_all_baselines": all(m["accuracy"] > res[b]["accuracy"] and m["brier"] < res[b]["brier"]
                                                    for b in BASE),
         "G3b_brier_gain_vs_persistence_holm_p_lt_0.05": cmp["B1_persistence"]["brier_gain"]["p_one_sided_holm"] < 0.05,
         "G4_citl_ci_contains_0": m["citl_ci95"][0] is not None and m["citl_ci95"][0] <= 0 <= m["citl_ci95"][1]}
    g["G3_beats_baselines"] = g["G3a_point_better_than_all_baselines"] and g["G3b_brier_gain_vs_persistence_holm_p_lt_0.05"]
    allp = all(g[k] for k in ("G0_validity", "G1_accuracy_ge_0.75", "G2_not_degenerate", "G3_beats_baselines",
                              "G4_citl_ci_contains_0"))
    g["verdict"] = ("suitable for decision-support testing (development evidence; prospective confirmation pending)"
                    if allp else "experimental (failed: " + ", ".join(k for k, v in g.items() if v is False) + ")")
    return g


def diag_scores(S_keys: pd.DataFrame, rows: list[dict]) -> dict:
    if not rows:
        return {}
    D = pd.DataFrame(rows).merge(S_keys, on=["t", "target_q", "province_code"])
    out = {}
    for arm, g in D.groupby("arm"):
        g = g.dropna(subset=["p"])
        out[arm] = L.cls_metrics(g["y"], (g["p"] >= 0.5).astype(int), g["p"]) | {"dates": int(g["target_q"].nunique())}
    return out


# ------------------------------------------------------------------------------------------------- E40
def e40_dev(d) -> dict:
    dev_cut = d.cut(E40_DEV[1] + 1)                     # data through 2025-Q1 only; holdout never computed
    truth = L.e40_labels(dev_cut)
    truth = truth[(truth["q"] >= E40_DEV[0]) & (truth["q"] <= E40_DEV[1])].set_index(["province_code", "q"])["y"]
    rows = []
    for t in range(E40_DEV[0] - 2, E40_DEV[1] - 1):
        c = d.cut(t)
        sim = L.e40_simulate(c, t)
        known = L.e40_labels(c)
        last = known.sort_values("q").groupby("province_code").last()["y"]
        rate = (known["y"].sum() + 1) / (len(known) + 2)
        for p in L.PROVS:
            if (p, t + 2) not in truth.index:
                continue
            rows.append({"t": t, "target_q": t + 2, "province_code": p, "y": int(truth[(p, t + 2)]),
                         "SIM_p": sim.get(p, np.nan), "PERSIST_p": float(last.get(p, 0)), "LOW_p": rate})
    E = pd.DataFrame(rows)
    withheld = E[E["SIM_p"].isna()]
    E = E.dropna(subset=["SIM_p"]).copy()               # no forecast -> not scored (PROTOCOL 4.4); common rows only
    E["SIM_yhat"] = (E["SIM_p"] >= 0.5).astype(int)
    E["PERSIST_yhat"] = E["PERSIST_p"].astype(int)
    E["LOW_yhat"] = 0
    out = {a: L.cls_metrics(E["y"], E[f"{a}_yhat"], E[f"{a}_p"]) for a in ("SIM", "PERSIST", "LOW")}
    out["paired_brier_SIM_vs"] = {o: L.sign_flip((per_date(E, o)["br"] - per_date(E, "SIM")["br"]).to_numpy())
                                  for o in ("PERSIST", "LOW")}
    out["dates"] = int(E["target_q"].nunique())
    out["withheld_rows"] = int(len(withheld))
    out["withheld_targets"] = sorted({L.qs(int(q)) for q in withheld["target_q"]})
    return out, E


# ------------------------------------------------------------------------------------------------ main
def main():
    proto = verify_protocol()
    d = L.load()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = L.E41 / "runs" / stamp
    out.mkdir(parents=True)

    all_origins = list(range(L.qi("2021-Q3"), OPERATIONAL_T + 1))
    X_all = L.feature_table(d, all_origins)

    # ---- lead 2 (primary)
    o2 = list(range(L.qi("2021-Q3"), L.qi("2026-Q1") + 1))
    P2, diag = forecasts(d, o2, 2, X_all, ml=True)
    P2 = attach_truth(P2, d)
    arms2 = ["M1", "M1z"] + BASE
    SP = P2.dropna(subset=[f"{a}_yhat" for a in ["M1"] + BASE] + ["y"])
    SML = SP.dropna(subset=["M2_yhat", "M3_yhat"])
    res2 = {a: arm_block(SP, a, cont=True) for a in arms2}
    cmp2 = compare(SP, "M1", BASE)
    res_ml = {a: arm_block(SML, a, cont=True) for a in ["M1", "M2", "M3"] + BASE}
    cmp_ml = compare(SML, "M1", ["M2", "M3"])
    keys = SML[["t", "target_q", "province_code", "y"]]

    # ---- lead 1 (context)
    o1 = list(range(L.qi("2021-Q4"), L.qi("2026-Q2") + 1))
    P1, _ = forecasts(d, o1, 1, X_all, ml=False)
    P1 = attach_truth(P1, d)
    S1 = P1.dropna(subset=[f"{a}_yhat" for a in ["M1"] + BASE] + ["y"])
    res1 = {a: arm_block(S1, a, cont=True) for a in ["M1", "M1z"] + BASE}
    cmp1 = compare(S1, "M1", BASE)

    # ---- hunger layer
    H = L.h_forecasts(d, o2, 2).dropna(subset=["H"])
    hres = {"dates": int(len(H)), "MAE_persist": float((H["H_persist"] - H["H"]).abs().mean()),
            "MAE_mean": float((H["H_mean"] - H["H"]).abs().mean())}

    # ---- E40 label, development quarters only
    e40, E = e40_dev(d)

    # ---- leakage (G0): recorded from the test run file written by pytest (tests/test_e41.py)
    lk = L.E41 / "runs" / "leakage_tests.json"
    leakage_ok = bool(lk.exists() and json.loads(lk.read_text()).get("passed"))

    results = {
        "protocol_sha256": proto, "run_utc": stamp,
        "inputs_sha256": {"cpi_index_ACP22.csv": sha(L.ACQ / "cpi_index_ACP22.csv"), "cpi_yoy (E40)": sha(L.YOY_FILE),
                          "sws_rounds.csv": sha(L.SWS_FILE), "palay_corn": sha(L.ACQ / "palay_corn_production.csv"),
                          "fisheries": sha(L.ACQ / "fisheries_production.csv"),
                          "lfs": sha(L.ACQ / "lfs_rates_national.csv"), "news_composition (E40)": sha(L.NEWS_FILE)},
        "lead2": {"S_P": {"dates": int(SP["target_q"].nunique()), "rows": int(len(SP)),
                          "first": L.qs(int(SP["target_q"].min())), "last": L.qs(int(SP["target_q"].max())),
                          "metrics": res2, "paired_vs_baselines": cmp2, "calibration_M1": calibration(SP, "M1"),
                          "breakdown": breakdown(SP, ["M1", "B1_persistence", "B2_latest_month", "B0_majority"]),
                          "gates": gates(res2, cmp2, leakage_ok)},
                  "S_ML": {"dates": int(SML["target_q"].nunique()), "rows": int(len(SML)),
                           "first": L.qs(int(SML["target_q"].min())) if len(SML) else None,
                           "metrics": res_ml, "paired_M1_vs_ML": cmp_ml,
                           "trigger_shap_M3": diag["shap_by_origin"],
                           "ablation_drop_group": diag_scores(keys, diag["ablation_rows"]),
                           "single_group": diag_scores(keys, diag["single_rows"])},
                  "M1_s_track_used_rows": int(SP["M1_s_track"].notna().sum())},
        "lead1_context": {"dates": int(S1["target_q"].nunique()), "rows": int(len(S1)), "metrics": res1,
                          "paired_vs_baselines": cmp1},
        "hunger_layer_lead2": hres,
        "e40_label_dev_only": e40,
        "feature_missingness_share": {c: float(X_all[c].isna().mean()) for c in L.FEATURES},
        "feature_corr_training_rows": X_all[X_all["t"] <= L.qi("2025-Q4")][L.FEATURES].corr().round(3)
        .where(lambda m: m.abs() >= 0.8).stack().reset_index().query("level_0 < level_1")
        .rename(columns={0: "r"}).to_dict("records"),
    }
    P2.to_csv(out / "predictions_lead2.csv", index=False)
    P1.to_csv(out / "predictions_lead1.csv", index=False)
    E.to_csv(out / "e40_dev_predictions.csv", index=False)
    X_all.to_csv(out / "features_asof.csv", index=False)
    (out / "results.json").write_text(json.dumps(results, indent=1, default=float))

    # ---- prospective freeze (origin 2026-10-01)
    t = OPERATIONAL_T
    fz = L.E41 / "frozen" / "E41_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        c = d.cut(t)
        m2 = L.m1_forecasts(d, list(range(L.qi("2021-Q3"), t + 1)), 2)
        m2 = m2[m2["t"] == t].set_index("province_code")
        m1l = L.m1_forecasts(d, list(range(L.qi("2021-Q4"), t + 1)), 1)
        m1l = m1l[m1l["t"] == t].set_index("province_code")
        X = L.features(c, t).set_index("province_code")
        sim = L.e40_simulate(c, t)
        hq = L.h_quarters(c).sort_values("q")
        rec = {"issued_by": "E41", "origin": str(L.origin(t).date()), "origin_quarter_t": L.qs(t),
               "lead2_target": L.qs(t + 2), "lead1_target": L.qs(t + 1), "protocol_sha256": proto,
               "cpi_months_used_through": L.ym_s(L.m0_of(t)),
               "sws_latest_quarter": L.qs(int(hq["q"].iloc[-1])), "sws_latest_H": float(hq["H"].iloc[-1]),
               "score_types": {"fpp_probability": "P(provincial food inflation in the target quarter > 4.0%), "
                                                  "price pressure, NOT food insecurity",
                               "e40_probability": "P(E40 exploratory food-stress label HIGH), component simulation, "
                                                  "exploratory, not validated"},
               "provinces": {}}
        for p in L.PROVS:
            pr = float(m2.loc[p, "p"])
            rec["provinces"][L.NAMES[p]] = {
                "province_code": p,
                "lead2_F_hat": float(m2.loc[p, "F_hat"]), "lead2_s": float(m2.loc[p, "s"]),
                "lead2_F_80pct": [float(m2.loc[p, "F_hat"] - 1.2816 * m2.loc[p, "s"]),
                                  float(m2.loc[p, "F_hat"] + 1.2816 * m2.loc[p, "s"])],
                "lead2_fpp_probability": pr,
                "lead2_band": "High" if pr >= 2 / 3 else ("Watch" if pr >= 1 / 3 else "Low"),
                "lead1_F_hat": float(m1l.loc[p, "F_hat"]), "lead1_fpp_probability": float(m1l.loc[p, "p"]),
                "lead2_e40_probability": sim.get(p),
                "evidence": {k: (None if pd.isna(X.loc[p, k]) else float(X.loc[p, k])) for k in L.FEATURES}}
        fz.write_text(json.dumps(rec, indent=1))
        (fz.parent / (fz.stem + ".sha256")).write_text(sha(fz) + "  " + fz.name + "\n")

    # ---- console: aggregate only
    print(stamp, "lead2 S-P dates", results["lead2"]["S_P"]["dates"], "rows", len(SP))
    for a in arms2:
        m = res2[a]
        print(f"  {a:16s} acc {m['accuracy']:.3f} {m['accuracy_ci95']} bal {m['balanced_accuracy']:.3f} "
              f"recH {m['recall_HIGH']:.2f} recL {m['recall_LOW']:.2f} brier {m['brier']:.3f} MAE {m.get('MAE_F', float('nan')):.2f}")
    print("  gates", results["lead2"]["S_P"]["gates"])
    print("  S-ML", {a: round(res_ml[a]["accuracy"], 3) for a in res_ml}, "dates", results["lead2"]["S_ML"]["dates"])
    print("  lead1", {a: round(res1[a]["accuracy"], 3) for a in res1})
    print("  hunger", hres)
    print("  E40 dev", {a: (round(e40[a]["accuracy"], 3), round(e40[a]["brier"], 3)) for a in ("SIM", "PERSIST", "LOW")})


if __name__ == "__main__":
    main()
