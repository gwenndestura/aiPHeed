"""E53 single run under the frozen PROTOCOL.md (+ DEVIATIONS.md D-1, explanation only).

    backend/venv/Scripts/python.exe -B runner/e53_evaluate.py
      -> runs/<UTC stamp>/{predictions.csv, rows.csv, selections.json, results.json}
      -> frozen/E53_<arm>_PROSPECTIVE_2027Q1.json (+ .sha256) for each arm that passes its rule, written once
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e53_lib as E  # noqa: E402

L, P2, np, pd = E.L, E.P2, E.np, E.pd
E52 = E.EXP / "E52_Objectives_Acceptance"
E52_RUN = E52 / "runs" / "20261017T132935Z"
I7_RUN = E.EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z" / "predictions_i7.csv"
I7_FROZEN = E.EXP / "E46_Rice_Policy" / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json"
FIRST, OPER = L.qi("2023-Q4"), L.qi("2026-Q3")
E52_ARMS = ["E52PS", "B1_PERSIST", "B2_LR_GOV", "B3_LGBM_GOV", "B4_LR_NLP", "B5_LGBM_NLP", "B6_LR_COMB", "B7_E38PROC",
            "CLIM", "HIGH", "LOW"]
BASELINES = [a for a in E52_ARMS if a != "E52PS"]
NOT_NEWS = [g for g in P2.ALL_GROUPS if g != "news"]
ABLATIONS = {"A-climate": dict(groups=[g for g in P2.ALL_GROUPS if g != "climate"]),
             "A-fish_kill": dict(groups=[g for g in P2.ALL_GROUPS if g != "fish_kill"]),
             "A-employment": dict(groups=[g for g in P2.ALL_GROUPS if g != "employment"]),
             "A-ofw_remittance": dict(groups=[g for g in P2.ALL_GROUPS if g != "ofw_remittance"]),
             "A-news": dict(groups=NOT_NEWS),
             "A-policy": dict(policy=False),
             "A-mkt": dict(groups=["market"], policy=False)}
NEW = ["R0", "C1", "C2", "LGB-R", "LGB-RL", "LGB-C"] + list(ABLATIONS)


def verify() -> str:
    want = (E.E53 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E.E53 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def main():
    proto = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E.E53 / "runs" / stamp
    out.mkdir(parents=True)
    committed = pd.read_csv(I7_RUN, dtype={"province_code": str}).set_index(["t", "province_code"])["I7_p_price"]
    frozen7 = json.loads(I7_FROZEN.read_text())
    d, X, B = E.load()
    preds, sel = [], {}
    for t in range(FIRST, OPER + 1):
        q = L.qs(t + 2)
        r0 = E.price_forecast(d, X, B, t)
        ref = np.array([committed[(t, p)] if (t, p) in committed.index and committed[(t, p)] == committed[(t, p)]
                        else frozen7["provinces"][L.NAMES[p]]["I7_p_price"] for p in L.PROVS])
        if np.max(np.abs(r0["p"] - ref)) > 1e-9:
            raise SystemExit(f"R0 does not reproduce E52 at origin {L.qs(t)}: {r0['p']} vs {ref}")
        c1 = E.fit_calibrator(r0["oof"]["p_oof"], r0["oof"]["y_oof"], "C1")
        c2 = E.fit_calibrator(r0["oof"]["p_oof"], r0["oof"]["y_oof"], "C2")
        lr = E.price_forecast(d, X, B, t, learner="lgb")
        ll = E.price_forecast(d, X, B, t, learner="lgb_linear")
        lc = E.lgbc_forecast(d, X, B, t)
        arms = {"R0": r0["p"], "C1": E.apply_calibrator(c1, r0["p"]), "C2": E.apply_calibrator(c2, r0["p"]),
                "LGB-R": lr["p"], "LGB-RL": ll["p"], "LGB-C": lc["p"]}
        abl = {}
        for a, kw in ABLATIONS.items():
            fx = E.price_forecast(d, X, B, t, **kw)
            arms[a] = fx["p"]
            abl[a] = {"food": fx["food_cfg"], "gap": fx["gap_cfg"]}
        sel[q] = {"origin": str(L.origin(t).date()), "R0": {"food": r0["food_cfg"], "gap": r0["gap_cfg"], "rho": r0["rho"],
                                                          "inner_rows": int(len(r0["oof"]))},
                  "C1": c1, "C2": c2, "LGB-R": {"food": lr["food_cfg"], "gap": lr["gap_cfg"], "food_rmse": lr["food_rmse"],
                                                "gap_rmse": lr["gap_rmse"]},
                  "LGB-RL": {"food": ll["food_cfg"], "gap": ll["gap_cfg"]}, "LGB-C": {"cfg": lc["cfg"], "logloss": lc["logloss"]},
                  "R0_rmse": {"food": r0["food_rmse"], "gap": r0["gap_rmse"]}, "ablations": abl}
        for i, p in enumerate(L.PROVS):
            preds.append({"t": t, "target": q, "province_code": p, **{f"{a}_p": float(v[i]) for a, v in arms.items()}})
        print(L.qs(t), "->", q, {a: np.round(v, 3).tolist() for a, v in arms.items() if a in ("R0", "C1", "C2", "LGB-R", "LGB-C")},
              flush=True)
    P = pd.DataFrame(preds)
    P.to_csv(out / "predictions.csv", index=False)
    R = pd.read_csv(E52_RUN / "rows.csv", dtype={"province_code": str})
    n0 = len(R)
    R = R.merge(P.drop(columns=["t"]), on=["target", "province_code"], how="inner")
    assert len(R) == n0 == 50, (len(R), n0)
    assert np.max(np.abs(R["R0_p"] - R["E52PS_p"])) < 1e-9
    for a in NEW:
        R[f"{a}_yhat"] = (R[f"{a}_p"] >= 0.5).astype(int)
    R.to_csv(out / "rows.csv", index=False)

    M52 = E.block(R, E52_ARMS, seed=51)                                   # reproduces E52 (same seed and order)
    old = json.loads((E52_RUN / "results.json").read_text())["metrics"]
    for a in E52_ARMS:
        for k in ("accuracy", "balanced_accuracy", "brier", "auc", "accuracy_ci95"):
            assert old[a][k] == M52[a][k] or (k == "auc" and old[a][k] is None and M52[a][k] is None), (a, k)
    MN = E.block(R, NEW, seed=53)
    allm = {**M52, **MN}
    loqo = {a: {q: float((R[R["target"] != q][f"{a}_yhat"] == R[R["target"] != q]["y"]).mean()) for q in R["target"].unique()}
            for a in ["E52PS"] + NEW}
    cal = {a: E.calibration(R["y"], R[f"{a}_p"]) for a in E52_ARMS + NEW if a not in ("HIGH", "LOW")}
    conf = {a: E.by_quarter_confusion(R, a) for a in ["E52PS"] + NEW}
    paired = {a: E.paired_brier(R, a) for a in NEW if a != "R0"}

    def crit(a):
        m = allm[a]
        return {"A1": m["accuracy"] >= 0.75,
                "A2": (m["balanced_accuracy"] or 0) >= 0.70 and (m["recall_HIGH"] or 0) >= 0.60 and (m["recall_LOW"] or 0) >= 0.60,
                "A3": all(m["brier"] < allm[b]["brier"] for b in BASELINES),
                "A4": all((m["balanced_accuracy"] or 0) > (allm[b]["balanced_accuracy"] or 0) for b in BASELINES),
                "A5": min(loqo[a].values()) >= 0.70,
                "K1": abs(cal[a]["citl"]) <= 0.05, "K2": m["brier"] <= allm["R0"]["brier"]}
    C = {a: crit(a) for a in ["R0", "C1", "C2", "LGB-R", "LGB-RL", "LGB-C"]}
    A15 = lambda a: all(C[a][k] for k in ("A1", "A2", "A3", "A4", "A5"))  # noqa: E731
    cal_pass = [a for a in ("C1", "C2") if A15(a) and C[a]["K1"] and C[a]["K2"]]
    decision = {
        "calibrated_replaces_R0": cal_pass[0] if cal_pass else None,
        "LGB-R_meets_LightGBM_requirement_for_development": A15("LGB-R"),
        "secondary_LightGBM_passing": [a for a in ("LGB-C", "LGB-RL") if A15(a)],
        "trigger_adds_reliable_information": {a: paired[a]["ci95"][0] > 0 for a in ABLATIONS},
    }
    res = {"protocol_sha256": proto, "run_utc": stamp,
           "evidence_status": "Development evidence on quarters already examined in E46-E52; not independent validation.",
           "rows": int(len(R)), "quarters": sorted(R["target"].unique().tolist()), "HIGH": int(R["y"].sum()),
           "e52_reproduced": True, "metrics": allm, "leave_one_quarter_out": loqo, "calibration": cal,
           "confusion_by_quarter": conf, "paired_brier_vs_R0": paired, "criteria": C, "decision": decision}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    (out / "selections.json").write_text(json.dumps(sel, indent=1, default=str))

    passing = ([decision["calibrated_replaces_R0"]] if decision["calibrated_replaces_R0"] else []) + \
              (["LGB-R"] if A15("LGB-R") else []) + decision["secondary_LightGBM_passing"]
    fz_dir = E.E53 / "frozen"
    fz_dir.mkdir(exist_ok=True)
    op = P[P["t"] == OPER].set_index("province_code")
    for a in passing:
        f = fz_dir / f"E53_{a}_PROSPECTIVE_2027Q1.json"
        if f.exists():
            continue
        f.write_text(json.dumps({"issued_by": f"E53 {a}", "origin": str(L.origin(OPER).date()), "target_quarter": L.qs(OPER + 2),
                                 "target": "PS (food-price pressure)", "decision_rule": "HIGH iff p >= 0.5",
                                 "information": "only data published before the origin (I7 as-of frame, E47 cutoffs)",
                                 "protocol_sha256": proto, "run": stamp,
                                 "provinces": {L.NAMES[p]: {"p": float(op.loc[p, f"{a}_p"]),
                                                            "decision": "HIGH" if op.loc[p, f"{a}_p"] >= 0.5 else "LOW"}
                                               for p in L.PROVS}}, indent=1))
        (fz_dir / (f.stem + ".sha256")).write_text(hashlib.sha256(f.read_bytes()).hexdigest() + "  " + f.name + "\n")

    f3 = lambda v: None if v is None else round(v, 3)  # noqa: E731
    print(stamp, "rows", len(R), "HIGH", int(R["y"].sum()))
    for a in E52_ARMS + NEW:
        m = allm[a]
        cc = cal.get(a, {})
        print(f"  {a:16s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal {f3(m['balanced_accuracy'])} "
              f"recH {f3(m['recall_HIGH'])} recL {f3(m['recall_LOW'])} brier {m['brier']:.3f} auc {f3(m['auc'])} "
              f"citl {f3(cc.get('citl'))} slope {f3(cc.get('slope'))} "
              f"dBrier {f3(paired[a]['diff']) if a in paired else ''} {[round(v, 3) for v in paired[a]['ci95']] if a in paired else ''}")
    print("  criteria", json.dumps(C))
    print("  decision", json.dumps(decision))


if __name__ == "__main__":
    main()
