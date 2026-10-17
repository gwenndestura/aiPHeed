"""E46 I9 under the frozen ADDENDUM_I9.md: I8's probabilities with the decision HIGH iff p >= pi_t (training prevalence
of T43 among the labels available at O'(t)). No refit.

    backend/venv/Scripts/python.exe -B runner/e46_evaluate_i9.py
      -> runs/i9_<UTC stamp>/{predictions_i9.csv, results_i9.json}; frozen/E46_I9_PROSPECTIVE_2027Q1.json (+ .sha256)
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
import e46_i8 as I8  # noqa: E402  (O'(t) timing)
import e46_evaluate_i7 as V7  # noqa: E402

M, L, K, np, pd = I8.M, I8.L, I8.K, I8.np, I8.pd
E4 = V7.E4
OPER = L.qi("2026-Q3")
RUN8 = M.E46 / "runs" / "i8_20261017T001227Z"
COMP = ["I8", "I8-MKT", "BASE-m0.5", "B-persist-O'", "I7", "I2", "B-maj", "B-persist", "SIM-0", "E41-M1", "E38-served"]


def verify() -> str:
    want = (HERE / "ADDENDUM_I9_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((M.E46 / "ADDENDUM_I9.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("ADDENDUM_I9.md changed after freezing")
    return got


def main():
    proto = verify()
    d = L.load()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = M.E46 / "runs" / f"i9_{stamp}"
    out.mkdir(parents=True)
    P8 = pd.read_csv(RUN8 / "predictions_i8.csv", dtype={"province_code": str})
    pi = {int(t): float(K.available_labels(d, int(t))["y"].mean()) for t in sorted(P8["t"].unique())}
    P9 = P8[["t", "province_code", "I8_p"]].rename(columns={"I8_p": "I9_p"}).copy()
    P9["pi_t"] = P9["t"].map(pi)
    P9["I9_yhat"] = np.where(P9["I9_p"].isna(), np.nan, (P9["I9_p"] >= P9["pi_t"]).astype(float))
    th = L.e40_spec()
    P8 = P8.copy()
    P8["B-persist-O'_p"] = P8["B-persist-O'_yhat"]
    P1 = pd.read_csv(V7.RUN1 / "predictions.csv", dtype={"province_code": str})
    P7 = pd.read_csv(M.E46 / "runs" / "i7_20261017T000111Z" / "predictions_i7.csv", dtype={"province_code": str})
    P7 = P7[["t", "province_code"] + [c for c in P7 if c.startswith("I7_")]]
    P = (P1.merge(P7, on=["t", "province_code"], how="left").merge(P8, on=["t", "province_code"], how="left")
         .merge(P9.drop(columns=["pi_t"]), on=["t", "province_code"], how="left"))
    m = 0.5
    P[f"BASE-m{m}_yhat"] = ((P[f"BASE-m{m}_sig"] == 1) & (P["I8_p_hunger"] >= 0.5)).astype(float)
    P.loc[P[f"BASE-m{m}_sig"].isna() | P["I8_p_hunger"].isna(), f"BASE-m{m}_yhat"] = np.nan
    P[f"BASE-m{m}_p"] = P[f"BASE-m{m}_yhat"]
    lab = P[P["y"].notna() & (P["target_q"] <= OPER)]
    req1 = E4.ITER + list(E4.VARIANTS) + E4.COMPARATORS
    S = lab.dropna(subset=[f"{a}_p" for a in req1])
    arms = ["I9"] + COMP
    S9 = S.dropna(subset=[f"{a}_p" for a in arms])
    ext_arms = ["I9", "I8", "I8-MKT", "BASE-m0.5", "B-persist-O'", "I7", "I2", "B-maj", "B-persist"]
    EXT = lab.dropna(subset=[f"{a}_p" for a in ext_arms])
    leak_ok = bool(json.loads((M.E46 / "runs" / "tests_status_i8.json").read_text()).get("passed"))
    res = {"addendum_sha256": proto, "run_utc": stamp, "pi_t": {L.qs(t): v for t, v in pi.items()},
           "evidence_status": "HINDSIGHT-INFORMED development evidence (ADDENDUM_I9 section 0); acceptance is prospective only.",
           "S44_rows_identical": bool(len(S9) == len(S))}
    for nm, D, aa in (("S44", S9, arms), ("EXT", EXT, ext_arms)):
        res[nm] = {"dates": int(D["target_q"].nunique()), "rows": int(len(D)), "HIGH": int(D["y"].sum()),
                   "quarters": [L.qs(int(q)) for q in sorted(D["target_q"].unique())],
                   "metrics": {a: {**E4.block(D, a), **V7.prf(D, a)} for a in aa},
                   "robustness": {a: V7.robustness(D, a) for a in ["I9", "I8", "I7", "I2"]}}
    res["S44"]["paired_I9"] = E4.paired(S9, "I9", [a for a in arms if a != "I9"])
    res["S44"]["gates_I9"] = E4.gates(res["S44"]["metrics"]["I9"], res["S44"]["paired_I9"], leak_ok)
    rb, ms = res["S44"]["robustness"]["I9"], res["S44"]["metrics"]
    res["windows"] = {w: {a: E4.block(S9[(S9["target_q"] >= L.qi(lo)) & (S9["target_q"] <= L.qi(hi))], a)
                          for a in ["I9", "I8", "B-maj"]}
                      for w, (lo, hi) in {"2024-Q3..2025-Q1": ("2024-Q3", "2025-Q1"),
                                          "2025-Q4..2026-Q3": ("2025-Q4", "2026-Q3")}.items()}
    res["final_candidate_rule"] = {
        "gates_A0_A4": res["S44"]["gates_I9"]["passes"], "EXT_accuracy_ge_0.75": res["EXT"]["metrics"]["I9"]["accuracy"] >= 0.75,
        "min_leave_one_quarter_out_ge_0.70": rb["min_leave_one_quarter_out"] >= 0.70,
        "brier_not_worse_than_B-persist-O'": ms["I9"]["brier"] <= ms["B-persist-O'"]["brier"]}
    res["final_candidate_rule"]["I9_is_final_candidate"] = all(res["final_candidate_rule"].values())
    res["forecasting_acceptance_met"] = False
    P9.to_csv(out / "predictions_i9.csv", index=False)
    (out / "results_i9.json").write_text(json.dumps(res, indent=1, default=float))

    fz = M.E46 / "frozen" / "E46_I9_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = P9[P9["t"] == OPER].set_index("province_code")
        rec = {"issued_by": "E46 I9", "origin": str(L.origin(OPER).date()), "origin_quarter": L.qs(OPER),
               "target_quarter": L.qs(OPER + 2), "lead_from_origin": 2, "addendum_sha256": proto,
               "probabilities_from": "frozen/E46_I8_PROSPECTIVE_2027Q1.json (I8_p)",
               "decision_rule": "HIGH iff p >= pi_t", "pi_t": pi[OPER],
               "provinces": {L.NAMES[p]: {"p": float(o.loc[p, "I9_p"]), "decision": "HIGH" if o.loc[p, "I9_yhat"] == 1 else "LOW"}
                             for p in L.PROVS}}
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
    print("  pi_t:", {k: round(v, 3) for k, v in res["pi_t"].items()})
    print("  gates I9:", res["S44"]["gates_I9"], "| robustness:", rb["min_leave_one_quarter_out"], rb["confusion"])
    print("  final-candidate rule:", res["final_candidate_rule"])


if __name__ == "__main__":
    main()
