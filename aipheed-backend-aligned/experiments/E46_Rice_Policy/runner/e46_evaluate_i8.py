"""E46 I8 single run under the frozen ADDENDUM_I8.md (issue time O'(t) = 15th of the first month of quarter t+1).

    backend/venv/Scripts/python.exe -B runner/e46_evaluate_i8.py
      -> runs/i8_<UTC stamp>/{predictions_i8.csv, selections_i8.json, results_i8.json}
      -> frozen/E46_I8_PROSPECTIVE_2027Q1.json (+ .sha256), written once
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
import e46_i8 as I8  # noqa: E402  (re-points the timing functions first)
import e46_evaluate_i7 as V7  # noqa: E402

M, L, K, P2, np, pd = I8.M, I8.L, I8.K, I8.P2, I8.np, I8.pd
E4 = V7.E4
OPER = L.qi("2026-Q3")
I7RUN = M.E46 / "runs" / "i7_20261017T000111Z"
ARMS = {"I8": {}, "I8-BASE": {"force_base": True}, "I8-MKT": {"groups": ["market"]}}
FIXED = [f"BASE-m{m}" for m in P2.MULTS]
COMP = ["I7", "I2", "B-maj", "B-persist", "SIM-0", "E41-M1", "E38-served"]


def verify() -> str:
    want = (HERE / "ADDENDUM_I8_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((M.E46 / "ADDENDUM_I8.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("ADDENDUM_I8.md changed after freezing")
    return got


def main():
    proto = verify()
    assert L.origin(L.qi("2026-Q3")) == pd.Timestamp("2026-10-15") and L.m0_of(L.qi("2026-Q3")) % 12 == 8
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    th = L.e40_spec()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = M.E46 / "runs" / f"i8_{stamp}"
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    X = M.features(d, x, origins, ev)
    B = P2.bases(d, origins)
    rows, sel, keep = [], {}, {}
    for t in origins:
        r = pd.DataFrame({"t": t, "province_code": L.PROVS})
        b = B[B["t"] == t].set_index("province_code").loc[L.PROVS]
        for m in P2.MULTS:
            sig = ((b[f"base_{m}"] > b.index.map(th["food"])) |
                   ((b[f"base_{m}"] - b[f"hl_{m}"]) > b.index.map(th["gap"]))).astype(float)
            sig[b[f"base_{m}"].isna()] = np.nan
            r[f"BASE-m{m}_sig"] = sig.to_numpy()
        pl = I8.persist_labels(d, t)
        r["B-persist-O'_yhat"] = [pl.get(p, np.nan) for p in L.PROVS]
        for name, kw in ARMS.items():
            f = I8.forecast(d, X, B, t, **kw)
            if f is None:
                continue
            r[f"{name}_p"], r[f"{name}_yhat"] = f["p"], (f["p"] >= f["threshold"]).astype(int)
            r[f"{name}_p_price"], r[f"{name}_p_hunger"] = f["p_price"], f["p_hunger"]
            r[f"{name}_F_hat"], r[f"{name}_G_hat"] = f["F_hat"], f["G_hat"]
            sel.setdefault(name, {})[L.qs(t)] = {k: f[k] for k in ("food_cfg", "gap_cfg", "food_rmse", "gap_rmse", "rho",
                                                                  "hunger_alpha", "hunger_rmse", "H_hat", "n_price_train_q")}
            if t == OPER:
                keep[name] = f
        rows.append(r)
    P8 = pd.concat(rows, ignore_index=True)
    P8["B-persist-O'_p"] = P8["B-persist-O'_yhat"]
    P1 = pd.read_csv(V7.RUN1 / "predictions.csv", dtype={"province_code": str})
    P7 = pd.read_csv(I7RUN / "predictions_i7.csv", dtype={"province_code": str})
    P7 = P7[["t", "province_code"] + [c for c in P7 if c.startswith("I7_")]]
    P = P1.merge(P7, on=["t", "province_code"], how="left").merge(P8, on=["t", "province_code"], how="left")
    for m in P2.MULTS:
        P[f"BASE-m{m}_yhat"] = ((P[f"BASE-m{m}_sig"] == 1) & (P["I8_p_hunger"] >= 0.5)).astype(float)
        P.loc[P[f"BASE-m{m}_sig"].isna() | P["I8_p_hunger"].isna(), f"BASE-m{m}_yhat"] = np.nan
        P[f"BASE-m{m}_p"] = P[f"BASE-m{m}_yhat"]
    lab = P[P["y"].notna() & (P["target_q"] <= OPER)]
    req1 = E4.ITER + list(E4.VARIANTS) + E4.COMPARATORS
    S = lab.dropna(subset=[f"{a}_p" for a in req1])
    arms = list(ARMS) + FIXED + ["B-persist-O'"] + COMP
    S8 = S.dropna(subset=[f"{a}_p" for a in arms])
    ext_arms = list(ARMS) + FIXED + ["B-persist-O'", "I7", "I2", "B-maj", "B-persist"]
    EXT = lab.dropna(subset=[f"{a}_p" for a in ext_arms])
    tests = M.E46 / "runs" / "tests_status_i8.json"
    leak_ok = bool(tests.exists() and json.loads(tests.read_text()).get("passed"))
    res = {"addendum_sha256": proto, "run_utc": stamp, "issue_time": "00:00 on the 15th of the first month of t+1",
           "evidence_status": "HINDSIGHT-INFORMED development evidence (ADDENDUM_I8 section 0); acceptance is prospective only.",
           "S44_rows_identical": bool(len(S8) == len(S))}
    for nm, D, aa in (("S44", S8, arms), ("EXT", EXT, ext_arms)):
        res[nm] = {"dates": int(D["target_q"].nunique()), "rows": int(len(D)), "HIGH": int(D["y"].sum()),
                   "quarters": [L.qs(int(q)) for q in sorted(D["target_q"].unique())],
                   "metrics": {a: {**E4.block(D, a), **V7.prf(D, a)} for a in aa},
                   "robustness": {a: V7.robustness(D, a) for a in list(ARMS) + ["I7", "I2"]}}
    res["S44"]["paired_I8"] = E4.paired(S8, "I8", [a for a in arms if a != "I8"])
    res["S44"]["gates_I8"] = E4.gates(res["S44"]["metrics"]["I8"], res["S44"]["paired_I8"], leak_ok)
    F = L.quarter_F(d)
    HL = L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
    Y = F.merge(HL, on=["province_code", "q"])
    Y["ps"] = ((Y["F"] > Y["province_code"].map(th["food"])) |
               ((Y["F"] - Y["HL"]) > Y["province_code"].map(th["gap"]))).astype(int)
    PR = P.merge(Y.rename(columns={"q": "target_q"})[["province_code", "target_q", "ps"]], on=["province_code", "target_q"])
    PR = PR[(PR["target_q"] <= OPER)].dropna(subset=["I8_p_price", "I7_p_price"])
    res["PRICE"] = {"dates": int(PR["target_q"].nunique()), "rows": int(len(PR)), "signal": int(PR["ps"].sum()),
                    "accuracy": {a: float(((PR[f"{a}_p_price"] >= 0.5).astype(int) == PR["ps"]).mean())
                                 for a in list(ARMS) + ["I7"]} | {a: float((PR[f"{a}_sig"] == PR["ps"]).mean()) for a in FIXED},
                    "brier": {a: float(((PR[f"{a}_p_price"] - PR["ps"]) ** 2).mean()) for a in list(ARMS) + ["I7"]}}
    g, rb, ms = res["S44"]["gates_I8"], res["S44"]["robustness"]["I8"], res["S44"]["metrics"]
    res["final_candidate_rule"] = {
        "gates_A0_A4": g["passes"], "EXT_accuracy_ge_0.75": res["EXT"]["metrics"]["I8"]["accuracy"] >= 0.75,
        "min_leave_one_quarter_out_ge_0.70": rb["min_leave_one_quarter_out"] >= 0.70,
        "brier_not_worse_than_B-persist-O'": ms["I8"]["brier"] <= ms["B-persist-O'"]["brier"]}
    res["final_candidate_rule"]["I8_is_final_candidate"] = all(res["final_candidate_rule"].values())
    res["forecasting_acceptance_met"] = False
    (out / "selections_i8.json").write_text(json.dumps(sel, indent=1, default=str))
    P8.to_csv(out / "predictions_i8.csv", index=False)
    X.to_csv(out / "features_asof_i8.csv", index=False)
    (out / "results_i8.json").write_text(json.dumps(res, indent=1, default=float))

    fz = M.E46 / "frozen" / "E46_I8_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = P8[P8["t"] == OPER].set_index("province_code")
        k = keep["I8"]
        rec = {"issued_by": "E46 I8", "origin": str(L.origin(OPER).date()), "origin_quarter": L.qs(OPER),
               "target_quarter": L.qs(OPER + 2), "lead_from_origin": 2, "addendum_sha256": proto,
               "cpi_months_used_through": L.ym_s(L.m0_of(OPER)),
               "sws_latest_quarter_used": L.qs(int(d.cut(OPER).sws["q"].max())),
               "decision_rule": "HIGH iff p >= 0.5", "policy_features_at_origin": M.policy_features(ev, OPER),
               "selection_at_origin": {"food_cfg": k["food_cfg"], "gap_cfg": k["gap_cfg"], "food_rmse": k["food_rmse"],
                                       "gap_rmse": k["gap_rmse"], "rho": k["rho"], "hunger_alpha": k["hunger_alpha"],
                                       "H_hat": k["H_hat"], "price_features": k["pcols"], "hunger_features": k["hcols"]},
               "provinces": {L.NAMES[p]: {c: (None if pd.isna(o.loc[p, c]) else float(o.loc[p, c]))
                                          for c in o.columns if c.startswith(("I8", "BASE", "B-persist"))}
                             for p in L.PROVS}}
        fz.write_text(json.dumps(rec, indent=1, default=str))
        (fz.parent / (fz.stem + ".sha256")).write_text(E4.sha(fz) + "  " + fz.name + "\n")

    for nm in ("S44", "EXT"):
        s = res[nm]
        print(stamp, nm, s["dates"], s["rows"], s["HIGH"], s["quarters"][0], "..", s["quarters"][-1])
        for a, m in s["metrics"].items():
            print(f"  {a:12s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal "
                  f"{None if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
                  f"recH {None if m['recall_HIGH'] is None else round(m['recall_HIGH'], 2)} "
                  f"recL {None if m['recall_LOW'] is None else round(m['recall_LOW'], 2)} brier {m['brier']:.3f} "
                  f"auc {None if m.get('roc_auc') is None else round(m['roc_auc'], 3)}")
    print("  S44 rows identical:", res["S44_rows_identical"], "| gates I8:", res["S44"]["gates_I8"])
    print("  robustness I8:", rb["min_leave_one_quarter_out"], rb["confusion"])
    print("  PRICE", res["PRICE"])
    print("  final-candidate rule:", res["final_candidate_rule"])


if __name__ == "__main__":
    main()
