"""E42 single evaluation run under the frozen PROTOCOL.md (run once; a byte-identical repeat may follow).

    backend/venv/Scripts/python.exe -B runner/e42_evaluate.py
      -> runs/<UTC stamp>/{predictions_lead2.csv, predictions_grid.csv, e40.csv, results.json}
      -> frozen/E42_PROSPECTIVE_2027Q1.json (+ .sha256), origin 2026-10-01 (written once)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e42_lib as K  # noqa: E402
import e41_evaluate as E1  # noqa: E402  (E41 baselines, scoring blocks)

L, np, pd = K.L, K.np, K.pd
BASE = ["B0_majority", "B1_persistence", "B2_latest_month", "B3_seasonal"]
OPER = L.qi("2026-Q3")
EXPOSED = {L.qi(q) for q in ("2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3")}
E40_SEALED = K.E42.parent / "E40_SWS_CPI_Tiers" / "frozen" / "E40_HOLDOUT_FORECASTS.json"


def verify_protocol() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((K.E42 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def block(S: pd.DataFrame, arm: str) -> dict:
    g = S.dropna(subset=[f"{arm}_p", "y"]).copy()
    g[f"{arm}_yhat"] = g.get(f"{arm}_yhat", (g[f"{arm}_p"] >= 0.5).astype(int))
    m = L.cls_metrics(g["y"], g[f"{arm}_yhat"], g[f"{arm}_p"])
    m["accuracy_ci95"] = L.date_bootstrap(g, lambda s: float((s[f"{arm}_yhat"] == s["y"]).mean()))
    m["brier_ci95"] = L.date_bootstrap(g, lambda s: float(((s[f"{arm}_p"] - s["y"]) ** 2).mean()))
    m["citl_ci95"] = L.date_bootstrap(g, lambda s: float(s["y"].mean() - s[f"{arm}_p"].mean()))
    m["dates"] = int(g["target_q"].nunique())
    m.update(E1.calibration(g, arm))
    if f"{arm}_F" in g:
        e = (g[f"{arm}_F"] - g["F_true"]).dropna()
        m["MAE_F"] = float(e.abs().mean()) if len(e) else None
    return m


def per_date(S, arm):
    yh = S[f"{arm}_yhat"] if f"{arm}_yhat" in S else (S[f"{arm}_p"] >= 0.5).astype(int)
    return S.assign(acc=(yh == S["y"]).astype(float), br=(S[f"{arm}_p"] - S["y"]) ** 2).groupby("target_q")[["acc", "br"]].mean()


def paired(S, cand, others):
    out, ps = {}, {}
    c = per_date(S, cand)
    for o in others:
        b = per_date(S, o)
        out[o] = {"accuracy_gain": L.sign_flip((c["acc"] - b["acc"]).to_numpy()),
                  "brier_gain": L.sign_flip((b["br"] - c["br"]).to_numpy())}
        ps[o] = out[o]["brier_gain"]["p_one_sided"]
    for o, h in L.holm(ps).items():
        out[o]["brier_gain"]["p_one_sided_holm"] = h
    return out


def main():
    proto = verify_protocol()
    d = L.load()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = K.E42 / "runs" / stamp
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    o2 = [t for t in origins if t + 2 <= L.qi("2026-Q3")]
    X = K.features(d, origins)
    truth = L.fpp_labels(d).rename(columns={"q": "target_q", "F": "F_true"})[["province_code", "target_q", "F_true", "y"]]

    # ---------------------------------------------------------------- S-P arms and PS
    arms = {n: K.m_forecasts(d, origins, 2, m) for n, m in K.ARMS.items()}
    ps = K.prequential(d, arms, origins)
    P = pd.concat([E1.baselines(d, t, 2) for t in origins], ignore_index=True)
    for n, A in arms.items():
        P = P.merge(A[["t", "province_code", "F_hat", "p"]].rename(columns={"F_hat": f"{n}_F", "p": f"{n}_p"}),
                    on=["t", "province_code"])
        P[f"{n}_yhat"] = np.where(P[f"{n}_F"].notna(), (P[f"{n}_F"] > L.FPP_THRESHOLD).astype(float), np.nan)
    P = P.merge(ps[["t", "province_code", "p", "chosen", "platt"]].rename(columns={"p": "PS_p"}), on=["t", "province_code"])
    P["PS_yhat"] = np.where(P["PS_p"].notna(), (P["PS_p"] >= 0.5).astype(float), np.nan)
    P = P.merge(truth, on=["province_code", "target_q"], how="left")

    # ---------------------------------------------------------------- ML grid (S-C)
    specs = {f"{a}-{s}": (cls, cols) for a, cls in (("LR", K.LRModel), ("LGBM", K.GBModel)) for s, cols in K.SETS.items()}
    for g, fs in K.GROUPS.items():
        if fs:
            specs[f"LR-only_{g}"] = (K.LRModel, fs)
            specs[f"LGBM-only_{g}"] = (K.GBModel, fs)
            specs[f"LR-drop_{g}"] = (K.LRModel, [c for c in K.COMB if c not in fs])
            specs[f"LGBM-drop_{g}"] = (K.GBModel, [c for c in K.COMB if c not in fs])
    preds, models, shap = [], {}, {}
    for t in o2 + [OPER]:
        tr = L.training_pairs(X, d.cut(t), t, 2)
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        if not K.eligible(tr):
            continue
        row = te[["t", "province_code"]].copy()
        for name, (cls, cols) in specs.items():
            m = cls(cols).fit(tr)
            row[f"{name}_p"] = m.predict(te)
            if name in ("LR-COMB", "LGBM-COMB"):
                models[(name, t)] = m
        shap[L.qs(t)] = K.grouped_shap(models[("LGBM-COMB", t)], te)
        preds.append(row)
    G = pd.concat(preds, ignore_index=True)
    P = P.merge(G, on=["t", "province_code"], how="left")
    SP = P[P["t"].isin(o2)].dropna(subset=[f"{a}_yhat" for a in ["M1", "M1z", "M1h", "PS"] + BASE] + ["y"])
    grid = ["LR-GOV", "LR-NLP", "LR-COMB", "LGBM-GOV", "LGBM-NLP", "LGBM-COMB"]
    SC = SP.dropna(subset=[f"{a}_p" for a in grid])

    res_sp = {a: block(SP, a) for a in ["PS", "M1", "M1z", "M1h"] + BASE}
    cmp_sp = paired(SP, "PS", BASE + ["M1"])
    res_sc = {a: block(SC, a) for a in ["PS", "M1", "M1z"] + BASE + grid}
    cmp_sc = {"PS_vs_grid": paired(SC, "PS", grid),
              "NLP_value": {"LR-COMB_vs_LR-GOV": paired(SC, "LR-COMB", ["LR-GOV"])["LR-GOV"],
                            "LGBM-COMB_vs_LGBM-GOV": paired(SC, "LGBM-COMB", ["LGBM-GOV"])["LGBM-GOV"]}}
    diag = {n: {k: v for k, v in block(SC, n).items() if k in ("accuracy", "balanced_accuracy", "brier", "roc_auc")}
            for n in specs if "only_" in n or "drop_" in n}

    # ---------------------------------------------------------------- permutation, missing, stale, redundancy
    rng = np.random.default_rng(42)
    keyed = SC.reset_index(drop=True)
    perm, miss = {}, {}
    for mname in ("LR-COMB", "LGBM-COMB"):
        base_p = keyed[f"{mname}_p"].to_numpy()
        base_b = float(np.mean((base_p - keyed["y"]) ** 2))
        Xte = X.set_index(["t", "province_code"]).loc[list(zip(keyed["t"], keyed["province_code"]))].reset_index()

        def predict(frame):
            return np.concatenate([models[(mname, t)].predict(frame[frame["t"] == t]) for t in sorted(frame["t"].unique())])

        order = np.argsort(Xte["t"].to_numpy(), kind="stable")
        Xte, ysorted, base_sorted = Xte.iloc[order].reset_index(drop=True), keyed["y"].to_numpy()[order], base_p[order]
        perm[mname], miss[mname] = {}, {}
        for g, fs in K.GROUPS.items():
            if not fs:
                continue
            incs = []
            for _ in range(200):
                Z = Xte.copy()
                Z[fs] = Z[fs].to_numpy()[rng.permutation(len(Z))]
                incs.append(float(np.mean((predict(Z) - ysorted) ** 2)) - base_b)
            perm[mname][g] = {"mean_brier_increase": float(np.mean(incs)), "sd": float(np.std(incs))}
            Z = Xte.copy()
            Z[fs] = np.nan
            miss[mname][g] = {"mean_delta_p": float(np.mean(predict(Z) - base_sorted))}
    stale = {}
    for lab, sub in (("sws_age_gt1", SP[SP["t"].map(X.drop_duplicates("t").set_index("t")["H_age"]) > 1]),
                     ("sws_age_le1", SP[SP["t"].map(X.drop_duplicates("t").set_index("t")["H_age"]) <= 1])):
        stale[lab] = {"rows": int(len(sub)), "PS_accuracy": float((sub["PS_yhat"] == sub["y"]).mean()) if len(sub) else None}
    tr_rows = X[X["t"] + 2 <= L.qi("2026-Q3")]
    corr = tr_rows[K.COMB].corr()
    pairs_hi = [{"a": a, "b": b, "r": round(float(corr.loc[a, b]), 3)} for i, a in enumerate(K.COMB) for b in K.COMB[i + 1:]
                if pd.notna(corr.loc[a, b]) and abs(corr.loc[a, b]) >= 0.8]
    Zg = tr_rows[K.GOV].dropna()
    Zg = (Zg - Zg.mean()) / Zg.std(ddof=0).replace(0, 1)
    vif = {}
    for c in Zg:
        others = Zg.drop(columns=[c]).to_numpy()
        beta, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(Zg)), others]), Zg[c].to_numpy(), rcond=None)
        r2 = 1 - np.var(Zg[c].to_numpy() - np.column_stack([np.ones(len(Zg)), others]) @ beta) / max(np.var(Zg[c]), 1e-12)
        vif[c] = float(1 / max(1 - r2, 1e-9))

    # ---------------------------------------------------------------- hunger layer
    hq = L.h_quarters(d).set_index("q")["H"]
    hrows = []
    for t in o2:
        c = d.cut(t)
        hc = L.h_quarters(c).sort_values("q")
        if not len(hc) or (t + 2) not in hq.index:
            continue
        Xt = X[X["t"] == t].iloc[0]
        r = {"t": t, "target_q": t + 2, "H": hq[t + 2], "persist": hc["H"].iloc[-1], "mean": hc["H"].mean(), "ridge": np.nan}
        posted = set(hc["q"])
        trh = X[(X["t"] + 2).isin(posted)].drop_duplicates("t")
        trh = trh.assign(Hy=trh["t"].map(lambda s: hq[s + 2] if (s + 2) in posted else np.nan)).dropna(
            subset=["Hy", "H_last", "F_now", "ur_last"])
        if len(trh) >= 8:
            from sklearn.linear_model import Ridge
            cols = ["H_last", "F_now", "ur_last"]
            mu, sd = trh[cols].mean(), trh[cols].std(ddof=0).replace(0, 1)
            rg = Ridge(alpha=1.0).fit((trh[cols] - mu) / sd, trh["Hy"])
            r["ridge"] = float(rg.predict(((Xt[cols].astype(float) - mu) / sd).to_frame().T)[0])
        hrows.append(r)
    H = pd.DataFrame(hrows)
    Hr = H.dropna(subset=["ridge"])
    hres = {"dates": int(len(H)), "MAE_persist": float((H["persist"] - H["H"]).abs().mean()),
            "MAE_mean": float((H["mean"] - H["H"]).abs().mean()),
            "ridge_dates": int(len(Hr)), "MAE_ridge_on_its_dates": float((Hr["ridge"] - Hr["H"]).abs().mean()) if len(Hr) else None,
            "MAE_persist_on_ridge_dates": float((Hr["persist"] - Hr["H"]).abs().mean()) if len(Hr) else None}

    # ---------------------------------------------------------------- E40 label
    e40 = L.e40_labels(d).rename(columns={"q": "target_q"})[["province_code", "target_q", "y"]]
    erows = []
    for t in origins:
        if (t + 2) not in set(e40["target_q"]) or t + 2 < L.qi("2023-Q1"):
            continue
        c = d.cut(t)
        sim = L.e40_simulate(c, t)
        known = L.e40_labels(c)
        last = known.sort_values("q").groupby("province_code").last()["y"]
        for p in L.PROVS:
            yy = e40[(e40["province_code"] == p) & (e40["target_q"] == t + 2)]["y"]
            if len(yy):
                erows.append({"t": t, "target_q": t + 2, "province_code": p, "y": int(yy.iloc[0]), "SIM_p": sim.get(p, np.nan),
                              "PERSIST_p": float(last.get(p, 0)), "LOW_p": 0.0, "exposed": (t + 2) in EXPOSED})
    E = pd.DataFrame(erows).dropna(subset=["SIM_p"])
    e40res = {}
    for scope, sub in (("all_scored", E), ("not_exposed", E[~E["exposed"]]), ("exposed_only", E[E["exposed"]])):
        e40res[scope] = {a: L.cls_metrics(sub["y"], (sub[f"{a}_p"] >= 0.5).astype(int), sub[f"{a}_p"]) | {
            "dates": int(sub["target_q"].nunique())} for a in ("SIM", "PERSIST", "LOW")}
    sealed = json.loads(E40_SEALED.read_text())
    srows = []
    for f in sealed["forecasts"]:
        tq = L.qi(f["target"])
        for p, v in f["provinces"].items():
            yy = e40[(e40["province_code"] == p) & (e40["target_q"] == tq)]["y"]
            if len(yy):
                srows.append({"target_q": tq, "province_code": p, "y": int(yy.iloc[0]), "p": v["score"],
                              "yhat": int(v["band"] == "HIGH")})
    Sx = pd.DataFrame(srows)
    e40res["E40_sealed_lead1"] = (L.cls_metrics(Sx["y"], Sx["yhat"], Sx["p"]) | {
        "dates": int(Sx["target_q"].nunique()), "status": "forecasts sealed 09:30:46Z before C-1; scored after exposure",
        "methods_note_claim_all_LOW_is_false": bool(Sx["yhat"].sum() > 0)}) if len(Sx) else None

    # ---------------------------------------------------------------- gates
    leak = json.loads((K.E42 / "runs" / "tests_status.json").read_text()) if (K.E42 / "runs" / "tests_status.json").exists() else {}
    m = res_sp["PS"]
    gates = {"G0_validity": bool(leak.get("passed")),
             "G1_accuracy_ge_0.75": m["accuracy"] >= 0.75,
             "G2_not_degenerate": (m["balanced_accuracy"] or 0) >= 0.70 and (m["recall_HIGH"] or 0) >= 0.60 and (m["recall_LOW"] or 0) >= 0.60,
             "G3a": all(m["accuracy"] > res_sp[b]["accuracy"] and m["brier"] < res_sp[b]["brier"] for b in BASE),
             "G3b": cmp_sp["B1_persistence"]["brier_gain"]["p_one_sided_holm"] < 0.05,
             "G4": (m["citl_ci95"][0] is not None and m["citl_ci95"][0] <= 0 <= m["citl_ci95"][1])
             and m["slope"] is not None and 0.7 <= m["slope"] <= 1.3,
             "G5_improves_on_E41_M1": cmp_sp["M1"]["brier_gain"]["mean_gain"] > 0 and cmp_sp["M1"]["brier_gain"]["p_one_sided"] < 0.05}
    gates["G3"] = gates["G3a"] and gates["G3b"]
    if all(gates[k] for k in ("G0_validity", "G1_accuracy_ge_0.75", "G2_not_degenerate", "G3", "G4")):
        cls = "Suitable for exploratory decision-support testing"
    elif gates["G0_validity"] and gates["G3"]:
        cls = "Requires further model development (usable for a controlled system demonstration as experimental)"
    else:
        cls = "Insufficient evidence to support Lead-2 operational use"
    gates["classification"] = cls
    sel = SP.drop_duplicates("t")[["t", "chosen", "platt"]]

    results = {
        "protocol_sha256": proto, "run_utc": stamp,
        "inputs_sha256": {"fssi_v2_panel.csv": sha(K.NEWS), "e40_sealed": sha(E40_SEALED)},
        "S_P": {"dates": int(SP["target_q"].nunique()), "rows": int(len(SP)), "metrics": res_sp, "paired_PS": cmp_sp,
                "gates": gates, "PS_selection_path": {L.qs(int(t)): [c, bool(pl)] for t, c, pl in sel.to_numpy()},
                "breakdown": E1.breakdown(SP, ["PS", "M1", "M1z", "B1_persistence"])},
        "S_C": {"dates": int(SC["target_q"].nunique()), "rows": int(len(SC)),
                "first": L.qs(int(SC["target_q"].min())) if len(SC) else None, "metrics": res_sc, "paired": cmp_sc,
                "single_and_drop": diag, "permutation": perm, "missing_sensitivity": miss,
                "grouped_shap_LGBM_COMB": shap},
        "stale": stale, "redundancy": {"pairs_abs_r_ge_0.8": pairs_hi, "vif_gov": vif},
        "hunger_layer": hres, "e40": e40res,
        "coverage": {"S_P_rows": int(len(SP)), "ML_rows_with_forecast": int(G["t"].isin(o2).sum()),
                     "feature_missing_share": {c: float(X[c].isna().mean()) for c in K.COMB}},
    }
    P.to_csv(out / "predictions_lead2.csv", index=False)
    E.to_csv(out / "e40.csv", index=False)
    H.to_csv(out / "hunger.csv", index=False)
    X.to_csv(out / "features_asof.csv", index=False)
    (out / "results.json").write_text(json.dumps(results, indent=1, default=float))

    # ---------------------------------------------------------------- prospective freeze
    fz = K.E42 / "frozen" / "E42_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = P[P["t"] == OPER].set_index("province_code")
        sim = L.e40_simulate(d.cut(OPER), OPER)
        rec = {"issued_by": "E42", "origin": str(L.origin(OPER).date()), "lead2_target": L.qs(OPER + 2),
               "protocol_sha256": proto, "cpi_months_used_through": L.ym_s(L.m0_of(OPER)),
               "PS_choice": str(o["chosen"].iloc[0]), "PS_platt": bool(o["platt"].iloc[0]), "provinces": {}}
        for p in L.PROVS:
            r = o.loc[p]
            rec["provinces"][L.NAMES[p]] = {"province_code": p, "PS_p": float(r["PS_p"]),
                                            **{f"{a}_F": float(r[f"{a}_F"]) for a in K.ARMS},
                                            **{f"{a}_p": float(r[f"{a}_p"]) for a in K.ARMS},
                                            **{f"{g}_p": (None if pd.isna(r.get(f"{g}_p")) else float(r[f"{g}_p"])) for g in grid},
                                            "E40_SIM_p": sim.get(p)}
        fz.write_text(json.dumps(rec, indent=1))
        (fz.parent / (fz.stem + ".sha256")).write_text(sha(fz) + "  " + fz.name + "\n")

    print(stamp, "S-P", results["S_P"]["dates"], "dates", len(SP), "rows")
    for a in ["PS", "M1", "M1z", "M1h"] + BASE:
        mm = res_sp[a]
        print(f"  {a:16s} acc {mm['accuracy']:.3f} {[round(x, 3) for x in mm['accuracy_ci95']]} bal {mm['balanced_accuracy']:.3f} "
              f"recH {mm['recall_HIGH']:.2f} recL {mm['recall_LOW']:.2f} brier {mm['brier']:.3f} slope {mm['slope']}")
    print("  gates", gates)
    print("  S-C", results["S_C"]["dates"], {a: (round(res_sc[a]["accuracy"], 3), round(res_sc[a]["brier"], 3)) for a in res_sc})
    print("  NLP value", {k: round(v["brier_gain"]["mean_gain"], 4) for k, v in cmp_sc["NLP_value"].items()})
    print("  hunger", hres)
    print("  e40", {s: {a: (round(v[a]["accuracy"], 3), round(v[a]["brier"], 3)) for a in ("SIM", "PERSIST", "LOW")}
                    for s, v in e40res.items() if s != "E40_sealed_lead1"}, e40res["E40_sealed_lead1"])


if __name__ == "__main__":
    main()
