"""E55 step 3, single run under the frozen PROTOCOL.md: E55-LGBM, its poverty and trigger variants, the LightGBM
factor diagnostics, the Objective 4 baselines (from step 2) and the committed comparators on the identical T43 rows;
the poverty decision; the prospective freeze.

    backend/venv/Scripts/python.exe -B runner/e55_evaluate.py
      -> runs/<UTC stamp>/{predictions.csv, rows.csv, selections.json, results.json}
      -> frozen/E55_LGBM_PROSPECTIVE_2027Q1.json (+ .sha256), written once (a repeat verifies it)
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
import e55_lib as F  # noqa: E402

E, L, np, pd = F.E, F.L, F.np, F.pd
EXP = F.EXP
RUN7 = EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z" / "predictions_i7.csv"
RUN38 = EXP / "E38_Lead2_Diagnosis_Tuning" / "runs" / "20261015T033922Z" / "predictions.csv"
ROWS52 = EXP / "E52_Objectives_Acceptance" / "runs" / "20261017T132935Z" / "rows.csv"
ORIGINS = list(range(L.qi("2023-Q4"), L.qi("2026-Q3") + 1))
OPER = L.qi("2026-Q3")
EVAL_FROM, EVAL_TO = L.qi("2024-Q2"), L.qi("2026-Q3")
ARMS = {"E55-LGBM": {}, "POV-AS": {"pov": "AS"}, "POV-LA": {"pov": "LA"}, "FE": {"pov": "FE"},
        "D-climate": {"drop": ("climate",)}, "D-fish_kill": {"drop": ("fish_kill",)},
        "D-employment": {"drop": ("employment",)}, "D-ofw_remittance": {"drop": ("ofw_remittance",)},
        "D-news": {"drop": ("news",)}, "D-policy": {"drop": ("policy",)}, "MKT-ONLY": {"feats": ("market",)}}
DIAGS = list(F.DIAG)
BASELINES = ["B1_PERSIST", "B2_LR_GOV", "B3_LGBM_GOV", "B4_LR_NLP", "B5_LGBM_NLP", "B6_LR_COMB", "B7_E38PROC",
             "CLIM", "HIGH", "LOW"]
COMPARATORS = ["I7", "I7-BASE", "E52"]   # D-2: E38-served (EQ3-T, non-equivalent) scored separately on its own rows
FROZEN = F.E55 / "frozen" / "E55_LGBM_PROSPECTIVE_2027Q1.json"


def verify() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((F.E55 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def improves(R, arm, ref, M) -> dict:
    pb = E.paired_brier(R, arm, ref, seed=55)
    a, r = M[arm], M[ref]
    imp = (pb["ci95"][1] < 0 and (a["balanced_accuracy"] or 0) >= (r["balanced_accuracy"] or 0)
           and (a["recall_HIGH"] or 0) >= (r["recall_HIGH"] or 0) - 0.05 and (a["recall_LOW"] or 0) >= (r["recall_LOW"] or 0) - 0.05)
    identical = bool(np.max(np.abs(R[f"{arm}_p"] - R[f"{ref}_p"])) < 1e-12)
    verdict = "IDENTICAL" if identical else ("IMPROVES" if imp else ("WORSENS" if pb["ci95"][0] > 0 else "NO DEMONSTRATED DIFFERENCE"))
    return {"paired_brier": pb, "verdict": verdict}


def criteria(R, arm, M) -> dict:
    c = M[arm]
    base = [b for b in BASELINES]
    loqo = {q: float((R[R["target"] != q][f"{arm}_yhat"] == R[R["target"] != q]["y"]).mean()) for q in R["target"].unique()}
    crit = {"A1_accuracy_ge_0.75": c["accuracy"] >= 0.75,
            "A2_balanced_and_recalls": (c["balanced_accuracy"] or 0) >= 0.70 and (c["recall_HIGH"] or 0) >= 0.60
            and (c["recall_LOW"] or 0) >= 0.60,
            "A3_brier_below_every_baseline": all(c["brier"] < M[b]["brier"] for b in base),
            "A4_balanced_above_every_baseline": all((c["balanced_accuracy"] or 0) > (M[b]["balanced_accuracy"] or 0) for b in base),
            "A5_min_leave_one_quarter_out_ge_0.70": min(loqo.values()) >= 0.70}
    crit["accepted_for_development"] = all(crit.values())
    return {"criteria": crit, "leave_one_quarter_out": loqo}


def main():
    proto = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = F.E55 / "runs" / stamp
    out.mkdir(parents=True)
    d, X, B = E.load()
    Y = F.t43_labels(d)
    lab = {(p, int(q)): v for p, q, v in zip(Y["province_code"], Y["q"], Y["T43"]) if v == v}
    lab_app = {(p, int(q)): v for p, q, v in zip(Y["province_code"], Y["q"], Y["T43_approved"]) if v == v}
    ps = {(p, int(q)): int(v) for p, q, v in zip(Y["province_code"], Y["q"], Y["PS"])}

    # ------------------------------------------------------------------ forecasts at every origin
    preds, sel = [], {}
    for t in ORIGINS:
        for arm, kw in ARMS.items():
            fx = F.lgbm_forecast(d, X, B, t, **kw)
            if fx is None:
                continue
            sel.setdefault(arm, {})[L.qs(t)] = {"cfg": fx["cfg"], "inner_logloss": fx["inner_logloss"],
                                                "n_train_rows": fx["n_train_rows"], "n_train_q": fx["n_train_q"],
                                                "n_train_HIGH": fx["n_train_HIGH"], "p_hunger": fx["p_hunger"],
                                                "H_hat": fx["H_hat"],
                                                "trees_nonconstant": bool(fx["model"].const is None)}
            for i, p in enumerate(L.PROVS):
                preds.append({"t": t, "province_code": p, "arm": arm, "p": float(fx["p"][i]),
                              "p_price": float(fx["p_price"][i]), "p_hunger": float(fx["p_hunger"]), "threshold": 0.5})
        for name in DIAGS:
            fx = F.diag_forecast(d, X, B, t, name)
            if fx is None:
                continue
            for i, p in enumerate(L.PROVS):
                preds.append({"t": t, "province_code": p, "arm": name, "p": float(fx["p"][i]),
                              "p_price": float(fx["p_price"][i]), "p_hunger": float(fx["p"][i] / max(fx["p_price"][i], 1e-300)),
                              "threshold": float(fx["threshold"])})
        print("origin", L.qs(t), "done", flush=True)
    P = pd.DataFrame(preds)
    P["target"] = (P["t"] + 2).map(L.qs)
    P["origin_quarter"] = P["t"].map(L.qs)
    P = P.sort_values(["t", "arm", "province_code"]).reset_index(drop=True)
    P.to_csv(out / "predictions.csv", index=False, float_format="%.12g")

    # ------------------------------------------------------------------ evaluation rows
    W = P.pivot_table(index=["t", "province_code"], columns="arm", values="p").reset_index()
    T = P.pivot_table(index=["t", "province_code"], columns="arm", values="threshold").reset_index()
    W = W[(W["t"] + 2 >= EVAL_FROM) & (W["t"] + 2 <= EVAL_TO)].copy()
    W["target"] = (W["t"] + 2).map(L.qs)
    W["y"] = [lab.get((p, t + 2), np.nan) for p, t in zip(W["province_code"], W["t"])]
    W["PS"] = [ps.get((p, t + 2), np.nan) for p, t in zip(W["province_code"], W["t"])]
    W = W.dropna(subset=["y"])
    W["y"] = W["y"].astype(int)
    assert (W["y"] == W["PS"]).all(), "T43 differs from PS on an evaluation row (hunger condition not met)"
    bl_dir = sorted(p for p in (F.E55 / "runs").glob("baselines_*"))[0]
    BL = pd.read_csv(bl_dir / "rows_baselines.csv", dtype={"province_code": str}).set_index(["target", "province_code"])
    r52 = pd.read_csv(ROWS52, dtype={"province_code": str}).set_index(["target", "province_code"])
    assert len(W) == len(r52) == 50, (len(W), len(r52))   # before the D-1 restriction
    assert all(int(r52.loc[(q, p), "y"]) == y for q, p, y in zip(W["target"], W["province_code"], W["y"])), "rows differ from E52"
    p7 = pd.read_csv(RUN7, dtype={"province_code": str})
    p7["target"] = (p7["t"] + 2).map(L.qs)
    p7 = p7.set_index(["target", "province_code"])
    p38 = pd.read_csv(RUN38, dtype={"province_code": str})
    p38 = p38[p38["arm"] == "E38-LGBM"].set_index(["target_quarter", "province_code"])
    # DEVIATIONS.md D-1: the E38-framework baselines skip a date whose as-of T43 training set has < 10 rows or one class
    # (target 2024-Q2); PROTOCOL 3 rows = where every arm AND baseline has a prediction. W50 (all 50 rows) is kept for
    # the arms that cover it (supplementary block).
    W50 = W.copy()
    W = W[[(q, p) in BL.index for q, p in zip(W["target"], W["province_code"])]].copy()
    R = W[["target", "t", "province_code", "y"]].copy()
    for a in list(ARMS) + DIAGS:
        R[f"{a}_p"] = W[a].to_numpy()
        thr = T.set_index(["t", "province_code"]).loc[list(zip(W["t"], W["province_code"])), a].to_numpy()
        R[f"{a}_yhat"] = (R[f"{a}_p"] >= thr).astype(int)
    keys = list(zip(R["target"], R["province_code"]))
    assert all(int(BL.loc[k, "y"]) == y for k, y in zip(keys, R["y"])), "baseline labels differ"
    for b in BASELINES:
        R[f"{b}_p"] = [float(BL.loc[k, f"{b}_p"]) for k in keys]
        thr = [float(BL.loc[k, "B7_E38PROC_thr"]) for k in keys] if b == "B7_E38PROC" else 0.5
        R[f"{b}_yhat"] = (R[f"{b}_p"] >= thr).astype(int)
    R["I7_p"] = [float(p7.loc[k, "I7_p"]) for k in keys]
    R["I7-BASE_p"] = [float(p7.loc[k, "I7-BASE_p"]) for k in keys]
    R["E52_p"] = [float(p7.loc[k, "I7_p_price"]) for k in keys]
    R["E38-served_p"] = [float(p38.loc[k, "p"]) if k in p38.index else np.nan for k in keys]
    R["E38-served_thr"] = [float(p38.loc[k, "threshold"]) if k in p38.index else np.nan for k in keys]
    for a in ("I7", "I7-BASE", "E52"):
        R[f"{a}_yhat"] = (R[f"{a}_p"] >= 0.5).astype(int)
    R["E38-served_yhat"] = (R["E38-served_p"] >= R["E38-served_thr"]).astype(int)
    R = R.sort_values(["target", "province_code"]).reset_index(drop=True)
    R.to_csv(out / "rows.csv", index=False, float_format="%.12g")
    keys50 = list(zip(W50["target"], W50["province_code"]))
    R50 = W50[["target", "t", "province_code", "y"]].copy()
    for a in list(ARMS) + DIAGS:
        R50[f"{a}_p"] = W50[a].to_numpy()
        thr = T.set_index(["t", "province_code"]).loc[list(zip(W50["t"], W50["province_code"])), a].to_numpy()
        R50[f"{a}_yhat"] = (R50[f"{a}_p"] >= thr).astype(int)
    for a, col in (("I7", "I7_p"), ("I7-BASE", "I7-BASE_p"), ("E52", "I7_p_price")):
        R50[f"{a}_p"] = [float(p7.loc[k, col]) for k in keys50]
        R50[f"{a}_yhat"] = (R50[f"{a}_p"] >= 0.5).astype(int)
    for a, v in (("HIGH", 1.0), ("LOW", 0.0)):
        R50[f"{a}_p"], R50[f"{a}_yhat"] = v, int(v)
    R50 = R50.sort_values(["target", "province_code"]).reset_index(drop=True)
    M50 = E.block(R50, list(ARMS) + DIAGS + ["I7", "I7-BASE", "E52", "HIGH", "LOW"], seed=55)

    # ------------------------------------------------------------------ metrics
    all_arms = list(ARMS) + DIAGS + BASELINES + COMPARATORS
    M = E.block(R, all_arms, seed=55)
    R38 = R[R["E38-served_p"].notna()]
    M38 = E.block(R38, ["E38-served", "E55-LGBM", "B1_PERSIST", "HIGH", "LOW"], seed=55)
    cal = {a: E.calibration(R["y"], R[f"{a}_p"]) for a in all_arms if a not in ("HIGH", "LOW")}
    crit = {a: criteria(R, a, M) for a in list(ARMS) + DIAGS + COMPARATORS}
    paired = {a: E.paired_brier(R, a, "E55-LGBM", seed=55) for a in all_arms if a != "E55-LGBM"}
    pov = {a: improves(R, a, "E55-LGBM", M) for a in ("POV-AS", "POV-LA", "FE")}
    abl = {a: improves(R, a, "E55-LGBM", M) for a in ARMS if a.startswith("D-") or a == "MKT-ONLY"}
    for a in abl:
        abl[a]["group_adds_information"] = abl[a]["paired_brier"]["ci95"][0] > 0
    pov_fe = E.paired_brier(R, "POV-LA", "FE", seed=55)
    served = "POV-AS" if pov["POV-AS"]["verdict"] == "IMPROVES" else "E55-LGBM"
    app = R[[lab_app.get((p, L.qi(q))) is not None for q, p in zip(R["target"], R["province_code"])]]
    M_app = E.block(app, ["E55-LGBM", "I7", "E52", "B1_PERSIST", "CLIM", "HIGH", "LOW"], seed=55)
    byq = {a: E.by_quarter_confusion(R, a) for a in ("E55-LGBM", served, "I7", "E52", "B1_PERSIST")}
    trees_used = {a: sum(v["trees_nonconstant"] for v in sel[a].values()) for a in sel}

    # ------------------------------------------------------------------ prospective freeze (written once)
    op = P[(P["t"] == OPER) & (P["arm"] == served)].set_index("province_code")
    frozen = {"model": served, "protocol_sha256": proto, "origin": str(L.origin(OPER).date()), "originQuarter": L.qs(OPER),
              "targetQuarter": L.qs(OPER + 2), "target": "T43 food-insecurity risk (PROTOCOL section 2)",
              "decision_threshold": 0.5,
              "forecasts": {p: {"province": L.NAMES[p], "p": round(float(op.loc[p, "p"]), 6),
                                "p_price": round(float(op.loc[p, "p_price"]), 6), "p_hunger": round(float(op.loc[p, "p_hunger"]), 6),
                                "decision": "HIGH" if float(op.loc[p, "p"]) >= 0.5 else "LOW"} for p in L.PROVS},
              "selection": sel[served][L.qs(OPER)]["cfg"]}
    FROZEN.parent.mkdir(exist_ok=True)
    if FROZEN.exists():
        old = json.loads(FROZEN.read_text())
        assert old["forecasts"] == frozen["forecasts"] and old["model"] == frozen["model"], "repeat differs from the frozen forecast"
        frozen_status = "verified (already frozen)"
    else:
        FROZEN.write_text(json.dumps(frozen, indent=1, sort_keys=True))
        (FROZEN.parent / (FROZEN.name + ".sha256")).write_text(sha_file(FROZEN) + "  " + FROZEN.name + "\n")
        frozen_status = "written"

    res = {"protocol_sha256": proto, "run_utc": stamp, "baselines_run": bl_dir.name,
           "evidence_status": "development evidence on quarters examined in E43-E54; not independent validation (PROTOCOL 0)",
           "rows": int(len(R)), "independent_quarters": int(R["target"].nunique()), "HIGH": int(R["y"].sum()),
           "LOW": int((R["y"] == 0).sum()), "quarters": sorted(R["target"].unique().tolist()),
           "t43_equals_ps_on_rows": True, "approved_subset": {"rows": int(len(app)), "HIGH": int(app["y"].sum()), "metrics": M_app},
           "metrics": M, "calibration": cal,
           "e38_served_non_equivalent": {"rows": int(len(R38)), "quarters": sorted(R38["target"].unique().tolist()),
                                         "metrics": M38, "note": "E38 forecasts the thesis Eq.3 label (EQ3-T), not T43; "
                                         "scored against T43 for information only; no E38 forecast for 2025-Q2/Q3"},
           "supplementary_50_rows": {"rows": int(len(R50)), "HIGH": int(R50["y"].sum()), "metrics": M50,
                                     "note": "all 50 E52 rows incl. 2024-Q2; Objective 4 baselines B1-B7 absent there (D-1)"}, "criteria": crit, "paired_brier_vs_E55_LGBM": paired,
           "poverty": pov, "poverty_LA_vs_FE": pov_fe, "trigger_ablation": abl, "served_arm": served,
           "trees_nonconstant_origins": trees_used, "by_quarter_confusion": byq,
           "prospective": {"file": FROZEN.name, "status": frozen_status, "sha256": sha_file(FROZEN)}}
    (out / "selections.json").write_text(json.dumps(sel, indent=1, sort_keys=True, default=float))
    (out / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True, default=float))
    f = lambda v: None if v is None else round(v, 3)  # noqa: E731
    print(stamp, "rows", res["rows"], "quarters", res["independent_quarters"], "HIGH", res["HIGH"], "served", served)
    for a in all_arms:
        m = M[a]
        print(f"  {a:20s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal {f(m['balanced_accuracy'])} "
              f"recH {f(m['recall_HIGH'])} recL {f(m['recall_LOW'])} F1 {f(m['f1_HIGH'])} brier {m['brier']:.3f} "
              f"auc {f(m['auc'])} {m['confusion']}")
    print("  criteria E55-LGBM", crit["E55-LGBM"]["criteria"])
    print("  poverty", {k: v["verdict"] for k, v in pov.items()})
    print("  ablation", {k: (v["verdict"], [round(x, 4) for x in v["paired_brier"]["ci95"]]) for k, v in abl.items()})
    print("  prospective", frozen_status, {L.NAMES[p]: v["p"] for p, v in frozen["forecasts"].items()})


if __name__ == "__main__":
    main()
