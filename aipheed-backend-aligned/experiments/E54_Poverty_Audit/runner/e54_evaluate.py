"""E54 comparisons C1 (PS, E52/E53 R0) and C2 (T43, E46-I7) under the frozen PROTOCOL.md.

    backend/venv/Scripts/python.exe -B runner/e54_evaluate.py
      -> runs/c12_<UTC stamp>/{predictions.csv, rows_ps.csv, rows_t43.csv, selections.json, results.json}
      -> frozen/E54_<C1|C2>_<arm>_PROSPECTIVE_2027Q1.json (+ .sha256) only for an arm that IMPROVES, written once
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e54_lib as V  # noqa: E402

EXP = V.E54.parent
sys.path.insert(0, str(EXP / "E53_LightGBM_Calibration" / "runner"))
sys.path.insert(0, str(EXP / "E46_Rice_Policy" / "runner"))
import e53_lib as E  # noqa: E402
import e46_evaluate_i7 as EV  # noqa: E402  (module constants and E44 helpers only; its main() is not run)

I7, L, P2, np, pd = E.I7, E.L, E.P2, E.np, E.pd
E52_RUN = EXP / "E52_Objectives_Acceptance" / "runs" / "20261017T132935Z"
I7_RUN = EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z"
I7_FROZEN = EXP / "E46_Rice_Policy" / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json"
FIRST, OPER = L.qi("2023-Q4"), L.qi("2026-Q3")
E52_ARMS = ["E52PS", "B1_PERSIST", "B2_LR_GOV", "B3_LGBM_GOV", "B4_LR_NLP", "B5_LGBM_NLP", "B6_LR_COMB", "B7_E38PROC",
            "CLIM", "HIGH", "LOW"]
BASELINES = [a for a in E52_ARMS if a != "E52PS"]
T43_COMP = ["I2", "I6", "I6b", "B-maj", "B-persist", "B-clim", "SIM-0", "SIM-5T", "E41-M1", "E38-served"] + EV.FIXED


def verify() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = V.sha(V.E54 / "PROTOCOL.md")
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def price_forecast(d, X, B, t, extra, n_jobs=8):
    """e53_lib.price_forecast (ridge, R0) with the arm's poverty columns appended to the residual inputs."""
    tr, te = E.frame(d, X, B, t)
    if not E.ok(tr, te):
        return None
    cols = E.pcols() + list(extra)
    fc = I7.component(tr, te, cols, "F_true", "base_{}", False, "forward", False, n_jobs)
    gc = I7.component(tr, te, cols, "G_true", "gbase_{}", False, "forward", False, n_jobs)
    if not (np.isfinite(fc["rmse"]) and np.isfinite(gc["rmse"])):
        return None
    j = fc["oof"].merge(gc["oof"], on=["q", "province_code"], suffixes=("_F", "_G"))
    rho = float(np.corrcoef(j["y_hat_F"] - j["y_true_F"], j["y_hat_G"] - j["y_true_G"])[0, 1]) if len(j) > 2 else 0.0
    rho = 0.0 if not np.isfinite(rho) else rho
    ps = P2.p_price_biv(fc["hat"], gc["hat"], fc["rmse"], gc["rmse"], rho, te["province_code"])

    def coef(c):
        if c["model"] is None:
            return None
        k = dict(zip(c["model"].keep, c["model"].m.coef_))
        return {x: float(k[x]) if x in k else None for x in extra}
    known = (tr[list(extra)] != 0).any(axis=1) if extra else pd.Series(False, index=tr.index)
    return {"p": np.asarray(ps), "food_cfg": fc["cfg"], "gap_cfg": gc["cfg"], "food_rmse": fc["rmse"],
            "gap_rmse": gc["rmse"], "rho": rho, "food_coef": coef(fc), "gap_coef": coef(gc),
            "train_rows": int(len(tr)), "train_rows_poverty_known": int(known.sum()),
            "test_poverty": {L.NAMES[p]: {c: float(v) for c, v in r.items()} for p, r in
                             zip(te["province_code"], te[list(extra)].to_dict("records"))} if extra else {}}


def t43_rows(P7: pd.DataFrame):
    """S44 and EXT rows exactly as e46_evaluate_i7.main builds them, from the committed I7 run."""
    th = L.e40_spec()
    del th
    P1 = pd.read_csv(EV.RUN1 / "predictions.csv", dtype={"province_code": str})
    P6 = pd.read_csv(EV.RUN6 / "predictions.csv", dtype={"province_code": str})
    P = P1.merge(P6, on=["t", "province_code"], how="left").merge(P7, on=["t", "province_code"], how="left")
    for m in P2.MULTS:
        P[f"BASE-m{m}_yhat"] = ((P[f"BASE-m{m}_sig"] == 1) & (P["I2_p_hunger"] >= 0.5)).astype(float)
        P.loc[P[f"BASE-m{m}_sig"].isna() | P["I2_p_hunger"].isna(), f"BASE-m{m}_yhat"] = np.nan
        P[f"BASE-m{m}_p"] = P[f"BASE-m{m}_yhat"]
    lab = P[P["y"].notna() & (P["target_q"] <= OPER)]
    req1 = EV.E4.ITER + list(EV.E4.VARIANTS) + EV.E4.COMPARATORS
    S = lab.dropna(subset=[f"{a}_p" for a in req1])
    S7 = S.dropna(subset=[f"{a}_p" for a in list(EV.ARMS) + EV.FIXED + EV.COMP])
    EXT = lab.dropna(subset=[f"{a}_p" for a in list(EV.ARMS) + EV.FIXED + ["I2", "B-maj", "B-persist"]])
    return P, S7, EXT


def t43_metrics(D, arm):
    m = EV.E4.block(D, arm)
    m.update(EV.prf(D, arm))
    return m


def main():
    proto = verify()
    inputs = V.verify_inputs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = V.E54 / "runs" / f"c12_{stamp}"
    out.mkdir(parents=True)
    P7c = pd.read_csv(I7_RUN / "predictions_i7.csv", dtype={"province_code": str})
    committed = P7c.set_index(["t", "province_code"])["I7_p_price"]
    frozen7 = json.loads(I7_FROZEN.read_text())
    d, X0, B = E.load()
    Xa = {a: V.add(X0, a) for a in V.ARMS}
    preds, sel = [], {}
    for t in range(FIRST, OPER + 1):
        q = L.qs(t + 2)
        fx = {a: price_forecast(d, Xa[a], B, t, V.cols(a)) for a in V.ARMS}
        ref = np.array([committed[(t, p)] if (t, p) in committed.index and committed[(t, p)] == committed[(t, p)]
                        else frozen7["provinces"][L.NAMES[p]]["I7_p_price"] for p in L.PROVS])
        if np.max(np.abs(fx["R"]["p"] - ref)) > 1e-9:
            raise SystemExit(f"R does not reproduce E52 / I7_p_price at origin {L.qs(t)}: {fx['R']['p']} vs {ref}")
        sel[q] = {"origin": str(L.origin(t).date()),
                  **{a: {k: v for k, v in f.items() if k != "p"} for a, f in fx.items()}}
        for i, p in enumerate(L.PROVS):
            preds.append({"t": t, "target": q, "province_code": p, **{f"{a}_p": float(f["p"][i]) for a, f in fx.items()}})
        print(L.qs(t), "->", q, "known poverty rows (POV-AS, SUB-AS):",
              fx["POV-AS"]["train_rows_poverty_known"], fx["SUB-AS"]["train_rows_poverty_known"], flush=True)
    P = pd.DataFrame(preds)
    P.to_csv(out / "predictions.csv", index=False)

    # ---------------------------------------------------------------- C1: PS on the 50 E52 rows
    R = pd.read_csv(E52_RUN / "rows.csv", dtype={"province_code": str})
    n0 = len(R)
    R = R.merge(P.drop(columns=["t"]), on=["target", "province_code"], how="inner")
    assert len(R) == n0 == 50
    assert np.max(np.abs(R["R_p"] - R["E52PS_p"])) < 1e-9
    for a in V.ARMS:
        R[f"{a}_yhat"] = (R[f"{a}_p"] >= 0.5).astype(int)
    R.to_csv(out / "rows_ps.csv", index=False)
    M52 = E.block(R, E52_ARMS, seed=51)
    old = json.loads((E52_RUN / "results.json").read_text())["metrics"]
    for a in E52_ARMS:
        for k in ("accuracy", "balanced_accuracy", "brier", "auc"):
            o_, n_ = old[a][k], M52[a][k]
            assert (o_ is None and n_ is None) or abs(o_ - n_) < 1e-12, (a, k, o_, n_)
    MN = E.block(R, V.ARMS, seed=V.SEED)
    allm = {**M52, **MN}
    cal = {a: E.calibration(R["y"], R[f"{a}_p"]) for a in V.ARMS}
    loqo = {a: {q: float((R[R["target"] != q][f"{a}_yhat"] == R[R["target"] != q]["y"]).mean())
                for q in R["target"].unique()} for a in V.ARMS}

    def crit(a):
        m = allm[a]
        return {"A1": m["accuracy"] >= 0.75,
                "A2": (m["balanced_accuracy"] or 0) >= 0.70 and (m["recall_HIGH"] or 0) >= 0.60 and (m["recall_LOW"] or 0) >= 0.60,
                "A3": all(m["brier"] < allm[b]["brier"] for b in BASELINES),
                "A4": all((m["balanced_accuracy"] or 0) > (allm[b]["balanced_accuracy"] or 0) for b in BASELINES),
                "A5": min(loqo[a].values()) >= 0.70}
    c1 = {"rows": int(len(R)), "HIGH": int(R["y"].sum()), "quarters": sorted(R["target"].unique().tolist()),
          "metrics": allm, "calibration": cal, "leave_one_quarter_out": loqo,
          "e52_acceptance_A1_A5": {a: crit(a) for a in V.ARMS}, "paired_brier_vs_R": {}, "decision": {}}
    for a in V.ARMS[1:]:
        pb = V.paired_brier(R, a, "R", "target")
        ident = bool(np.max(np.abs(R[f"{a}_p"] - R["R_p"])) < 1e-12)
        c1["paired_brier_vs_R"][a] = pb
        c1["decision"][a] = V.decide(allm[a], allm["R"], pb, ident)
    c1["poverty_vs_FE"] = {a: V.paired_brier(R, a, "FE", "target") for a in V.POVERTY_ARMS
                           if c1["decision"][a]["status"] == "IMPROVES"}

    # ---------------------------------------------------------------- C2: T43 = committed I7 hunger x arm price
    P7 = P7c.copy()
    Pa = P[["t", "province_code"] + [f"{a}_p" for a in V.ARMS]].rename(columns={f"{a}_p": f"{a}_pp" for a in V.ARMS})
    P7 = P7.merge(Pa, on=["t", "province_code"], how="left")
    for a in V.ARMS:
        P7[f"{a}_p"] = P7["I7_p_hunger"] * P7[f"{a}_pp"]
        P7[f"{a}_yhat"] = (P7[f"{a}_p"] >= 0.5).astype(float)
        P7.loc[P7[f"{a}_p"].isna(), f"{a}_yhat"] = np.nan
    chk = P7.dropna(subset=["R_p", "I7_p"])
    assert len(chk) and np.max(np.abs(chk["R_p"] - chk["I7_p"])) < 1e-9
    P7 = P7.drop(columns=[f"{a}_pp" for a in V.ARMS])
    _, S7, EXT = t43_rows(P7)
    assert (len(S7), int(S7["y"].sum()), len(EXT), int(EXT["y"].sum())) == (35, 9, 40, 13), (len(S7), len(EXT))
    S7.to_csv(out / "rows_t43.csv", index=False)
    c2 = {}
    for nm, D in (("S44", S7), ("EXT", EXT)):
        D = D.dropna(subset=[f"{a}_p" for a in V.ARMS])
        comp = [a for a in T43_COMP if f"{a}_p" in D and D[f"{a}_p"].notna().all()]
        met = {a: t43_metrics(D, a) for a in V.ARMS + comp}
        blk = {"rows": int(len(D)), "HIGH": int(D["y"].sum()),
               "quarters": [L.qs(int(q)) for q in sorted(D["target_q"].unique())], "metrics": met,
               "paired_brier_vs_R": {}, "decision": {}}
        for a in V.ARMS[1:]:
            pb = V.paired_brier(D, a, "R", "target_q")
            ident = bool(np.max(np.abs(D[f"{a}_p"] - D["R_p"])) < 1e-12)
            blk["paired_brier_vs_R"][a] = pb
            blk["decision"][a] = V.decide(met[a], met["R"], pb, ident)
        blk["poverty_vs_FE"] = {a: V.paired_brier(D, a, "FE", "target_q") for a in V.POVERTY_ARMS
                                if blk["decision"][a]["status"] == "IMPROVES"}
        c2[nm] = blk

    improves = {"C1": [a for a in V.POVERTY_ARMS if c1["decision"][a]["status"] == "IMPROVES"],
                "C2": [a for a in V.POVERTY_ARMS if c2["S44"]["decision"][a]["status"] == "IMPROVES"]}
    res = {"protocol_sha256": proto, "inputs_sha256": inputs, "run_utc": stamp,
           "evidence_status": "Development evidence on quarters already examined in E46-E53; not independent validation.",
           "poverty_values": {"POV_raw": {L.NAMES[p]: v for p, v in V.pov_values().items()},
                              "SUB_raw": {f"{L.NAMES[p]}_{y}": v for (p, y), v in V.sub_values().items()},
                              "POV_known_from": str(V.POV_KNOWN_FROM.date()), "SUB_published": str(V.sub_published().date())},
           "reproduced": {"R_equals_E52_and_I7_p_price": True, "R_T43_equals_I7_p": True, "E52_metrics": True},
           "C1_PS": c1, "C2_T43": c2,
           "primary": {"question": "C1 POV-AS vs R", "status": c1["decision"]["POV-AS"]["status"]},
           "improving_arms": improves,
           "claim_poverty_improves_past_quarters": any(a in V.AS_ARMS for a in improves["C1"] + improves["C2"])}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    (out / "selections.json").write_text(json.dumps(sel, indent=1, default=str))

    fz = V.E54 / "frozen"
    op = P[P["t"] == OPER].set_index("province_code")
    h_op = P7c[P7c["t"] == OPER].set_index("province_code")["I7_p_hunger"]
    for comp, arms in improves.items():
        for a in arms:
            f = fz / f"E54_{comp}_{a}_PROSPECTIVE_2027Q1.json"
            if f.exists():
                continue
            prob = {p: float(op.loc[p, f"{a}_p"]) * (float(h_op.loc[p]) if comp == "C2" else 1.0) for p in L.PROVS}
            f.write_text(json.dumps({"issued_by": f"E54 {comp} {a}", "origin": str(L.origin(OPER).date()),
                                     "target_quarter": L.qs(OPER + 2), "target": "PS" if comp == "C1" else "T43",
                                     "decision_rule": "HIGH iff p >= 0.5", "protocol_sha256": proto, "run": stamp,
                                     "provinces": {L.NAMES[p]: {"p": v, "decision": "HIGH" if v >= 0.5 else "LOW"}
                                                   for p, v in prob.items()}}, indent=1))
            (fz / (f.stem + ".sha256")).write_text(V.sha(f) + "  " + f.name + "\n")

    f3 = lambda v: None if v is None else round(v, 3)  # noqa: E731
    print(stamp, "C1 rows", c1["rows"], "HIGH", c1["HIGH"])
    for a in V.ARMS + BASELINES:
        m = allm[a]
        pb = c1["paired_brier_vs_R"].get(a)
        print(f"  {a:12s} acc {m['accuracy']:.3f} bal {f3(m['balanced_accuracy'])} recH {f3(m['recall_HIGH'])} "
              f"recL {f3(m['recall_LOW'])} brier {m['brier']:.4f} auc {f3(m['auc'])}"
              + (f" dBrier {pb['diff']:+.4f} {[round(v, 4) for v in pb['ci95']]} {c1['decision'][a]['status']}" if pb else ""))
    for nm, blk in c2.items():
        print(stamp, "C2", nm, "rows", blk["rows"], "HIGH", blk["HIGH"])
        for a, m in blk["metrics"].items():
            pb = blk["paired_brier_vs_R"].get(a)
            print(f"  {a:12s} acc {m['accuracy']:.3f} bal {f3(m['balanced_accuracy'])} recH {f3(m['recall_HIGH'])} "
                  f"recL {f3(m['recall_LOW'])} brier {m['brier']:.4f}"
                  + (f" dBrier {pb['diff']:+.4f} {[round(v, 4) for v in pb['ci95']]} {blk['decision'][a]['status']}" if pb else ""))
    print("  primary", res["primary"], "improving", improves)


if __name__ == "__main__":
    main()
