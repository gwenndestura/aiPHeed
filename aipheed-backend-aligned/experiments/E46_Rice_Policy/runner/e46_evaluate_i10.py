"""E46 I10 single run under the frozen ADDENDUM_I10.md (I8 timing; trigger groups admitted by inner validation).

    backend/venv/Scripts/python.exe -B runner/e46_evaluate_i10.py
      -> runs/i10_<UTC stamp>/{predictions_i10.csv, selections_i10.json, results_i10.json}
      -> frozen/E46_I10_PROSPECTIVE_2027Q1.json (+ .sha256), written once
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
import e46_i10 as I10  # noqa: E402  (imports e46_i8 first: O'(t) timing)
import e46_evaluate_i7 as V7  # noqa: E402

M, L, K, P2, np, pd = I10.M, I10.L, I10.K, I10.P2, I10.np, I10.pd
E4 = V7.E4
OPER = L.qi("2026-Q3")
RUN7 = M.E46 / "runs" / "i7_20261017T000111Z"
RUN8 = M.E46 / "runs" / "i8_20261017T001227Z"
COMP = ["I8", "I8-MKT", "I7", "I2", "BASE-m0.5", "B-persist-O'", "B-maj", "B-persist", "SIM-0", "E41-M1", "E38-served"]


def verify() -> str:
    want = (HERE / "ADDENDUM_I10_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((M.E46 / "ADDENDUM_I10.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("ADDENDUM_I10.md changed after freezing")
    return got


def main():
    proto = verify()
    assert L.origin(OPER) == pd.Timestamp("2026-10-15")
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = M.E46 / "runs" / f"i10_{stamp}"
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    X = M.features(d, x, origins, ev)
    B = P2.bases(d, origins)
    rows, sel, keep = [], {}, None
    for t in origins:
        f = I10.forecast(d, X, B, t)
        if f is None:
            continue
        rows.append(pd.DataFrame({"t": t, "province_code": L.PROVS, "I10_p": f["p"],
                                  "I10_yhat": (f["p"] >= f["threshold"]).astype(int), "I10_p_price": f["p_price"],
                                  "I10_p_hunger": f["p_hunger"], "I10_F_hat": f["F_hat"], "I10_G_hat": f["G_hat"]}))
        sel[L.qs(t)] = {k: f[k] for k in ("food_cfg", "gap_cfg", "food_rmse", "gap_rmse", "food_groups", "gap_groups",
                                          "food_path", "gap_path", "rho", "hunger_alpha", "H_hat", "n_price_train_q")}
        if t == OPER:
            keep = f
    P10 = pd.concat(rows, ignore_index=True)
    P1 = pd.read_csv(V7.RUN1 / "predictions.csv", dtype={"province_code": str})
    P7 = pd.read_csv(RUN7 / "predictions_i7.csv", dtype={"province_code": str})
    P7 = P7[["t", "province_code"] + [c for c in P7 if c.startswith("I7_")]]
    P8 = pd.read_csv(RUN8 / "predictions_i8.csv", dtype={"province_code": str})
    P = (P1.merge(P7, on=["t", "province_code"], how="left").merge(P8, on=["t", "province_code"], how="left")
         .merge(P10, on=["t", "province_code"], how="left"))
    P["BASE-m0.5_yhat"] = ((P["BASE-m0.5_sig"] == 1) & (P["I8_p_hunger"] >= 0.5)).astype(float)
    P.loc[P["BASE-m0.5_sig"].isna() | P["I8_p_hunger"].isna(), "BASE-m0.5_yhat"] = np.nan
    P["BASE-m0.5_p"] = P["BASE-m0.5_yhat"]
    lab = P[P["y"].notna() & (P["target_q"] <= OPER)]
    req1 = E4.ITER + list(E4.VARIANTS) + E4.COMPARATORS
    S = lab.dropna(subset=[f"{a}_p" for a in req1])
    arms = ["I10"] + COMP
    S10 = S.dropna(subset=[f"{a}_p" for a in arms])
    ext_arms = ["I10", "I8", "I8-MKT", "I7", "I2", "BASE-m0.5", "B-persist-O'", "B-maj", "B-persist"]
    EXT = lab.dropna(subset=[f"{a}_p" for a in ext_arms])
    tests = M.E46 / "runs" / "tests_status_i10.json"
    leak_ok = bool(tests.exists() and json.loads(tests.read_text()).get("passed"))
    res = {"addendum_sha256": proto, "run_utc": stamp,
           "evidence_status": "HINDSIGHT-INFORMED development evidence (ADDENDUM_I10 section 0); acceptance is prospective only.",
           "S44_rows_identical": bool(len(S10) == len(S))}
    for nm, D, aa in (("S44", S10, arms), ("EXT", EXT, ext_arms)):
        res[nm] = {"dates": int(D["target_q"].nunique()), "rows": int(len(D)), "HIGH": int(D["y"].sum()),
                   "quarters": [L.qs(int(q)) for q in sorted(D["target_q"].unique())],
                   "metrics": {a: {**E4.block(D, a), **V7.prf(D, a)} for a in aa},
                   "robustness": {a: V7.robustness(D, a) for a in ["I10", "I8", "I7", "I2"]}}
    res["S44"]["paired_I10"] = E4.paired(S10, "I10", [a for a in arms if a != "I10"])
    res["S44"]["gates_I10"] = E4.gates(res["S44"]["metrics"]["I10"], res["S44"]["paired_I10"], leak_ok)
    rb, ms = res["S44"]["robustness"]["I10"], res["S44"]["metrics"]
    res["groups_selected"] = {q: {"food": s["food_groups"] if s["food_cfg"]["alpha"] is not None else [],
                                  "gap": s["gap_groups"] if s["gap_cfg"]["alpha"] is not None else []}
                              for q, s in sel.items()}
    res["final_candidate_rule"] = {
        "gates_A0_A4": res["S44"]["gates_I10"]["passes"],
        "EXT_accuracy_ge_0.75": res["EXT"]["metrics"]["I10"]["accuracy"] >= 0.75,
        "min_leave_one_quarter_out_ge_0.70": rb["min_leave_one_quarter_out"] >= 0.70,
        "brier_not_worse_than_B-persist-O'": ms["I10"]["brier"] <= ms["B-persist-O'"]["brier"]}
    res["final_candidate_rule"]["I10_is_final_candidate"] = all(res["final_candidate_rule"].values())
    res["forecasting_acceptance_met"] = False
    (out / "selections_i10.json").write_text(json.dumps(sel, indent=1, default=str))
    P10.to_csv(out / "predictions_i10.csv", index=False)
    (out / "results_i10.json").write_text(json.dumps(res, indent=1, default=float))

    fz = M.E46 / "frozen" / "E46_I10_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = P10[P10["t"] == OPER].set_index("province_code")
        k = keep
        rec = {"issued_by": "E46 I10", "origin": str(L.origin(OPER).date()), "origin_quarter": L.qs(OPER),
               "target_quarter": L.qs(OPER + 2), "lead_from_origin": 2, "addendum_sha256": proto,
               "cpi_months_used_through": L.ym_s(L.m0_of(OPER)), "decision_rule": "HIGH iff p >= 0.5",
               "policy_features_at_origin": M.policy_features(ev, OPER),
               "selection_at_origin": {kk: k[kk] for kk in ("food_cfg", "gap_cfg", "food_rmse", "gap_rmse", "food_groups",
                                                            "gap_groups", "rho", "hunger_alpha", "H_hat")},
               "provinces": {L.NAMES[p]: {c: float(o.loc[p, c]) for c in o.columns if c.startswith("I10")} for p in L.PROVS}}
        fz.write_text(json.dumps(rec, indent=1, default=str))
        (fz.parent / (fz.stem + ".sha256")).write_text(E4.sha(fz) + "  " + fz.name + "\n")

    for nm in ("S44", "EXT"):
        s = res[nm]
        print(stamp, nm, s["dates"], s["rows"], s["HIGH"], s["quarters"][0], "..", s["quarters"][-1])
        for a, mm in s["metrics"].items():
            print(f"  {a:12s} acc {mm['accuracy']:.3f} {[round(v, 2) for v in mm['accuracy_ci95']]} bal "
                  f"{None if mm['balanced_accuracy'] is None else round(mm['balanced_accuracy'], 3)} "
                  f"recH {None if mm['recall_HIGH'] is None else round(mm['recall_HIGH'], 2)} "
                  f"recL {None if mm['recall_LOW'] is None else round(mm['recall_LOW'], 2)} brier {mm['brier']:.3f} "
                  f"auc {None if mm.get('roc_auc') is None else round(mm['roc_auc'], 3)}")
    print("  groups selected:", res["groups_selected"])
    print("  gates I10:", res["S44"]["gates_I10"], "| robustness:", rb["min_leave_one_quarter_out"], rb["confusion"])
    print("  final-candidate rule:", res["final_candidate_rule"])


if __name__ == "__main__":
    main()
