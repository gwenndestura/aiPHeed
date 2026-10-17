"""E46 I7 single run under the frozen ADDENDUM_I7.md (I7 + diagnostics on S44, EXT and PRICE; prospective freeze).

    backend/venv/Scripts/python.exe -B runner/e46_evaluate_i7.py
      -> runs/i7_<UTC stamp>/{predictions_i7.csv, selections_i7.json, results_i7.json}
      -> frozen/E46_I7_PROSPECTIVE_2027Q1.json (+ .sha256), written once
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
import e46_i7 as I7  # noqa: E402

M, L, K, P2, np, pd = I7.M, I7.L, I7.K, I7.P2, I7.np, I7.pd
E44 = M.E46.parent / "E44_Five_Trigger_Optimization"
sys.path.insert(0, str(E44 / "runner"))
import e44_evaluate as E4  # noqa: E402

RUN1 = E44 / "runs" / "20261015T150213Z"
RUN6 = M.E46 / "runs" / "20261016T225203Z"
OPER = L.qi("2026-Q3")
ARMS = {"I7": {}, "I7-BASE": {"force_base": True}, "I7-MKT": {"groups": ["market"]}, "I7-INT": {"intercept": True},
        "I7-LOQO": {"selection": "loqo"}}
FIXED = [f"BASE-m{m}" for m in P2.MULTS]
COMP = ["I2", "I6", "I6b", "B-maj", "B-persist", "SIM-0", "SIM-5T", "E41-M1", "E38-served"]


def verify() -> str:
    want = (HERE / "ADDENDUM_I7_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((M.E46 / "ADDENDUM_I7.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("ADDENDUM_I7.md changed after freezing")
    return got


def robustness(S, arm):
    acc = lambda g: float((g[f"{arm}_yhat"] == g["y"]).mean())  # noqa: E731
    qs = sorted(S["target_q"].unique())
    return {"leave_one_quarter_out": {L.qs(int(q)): acc(S[S["target_q"] != q]) for q in qs},
            "min_leave_one_quarter_out": min(acc(S[S["target_q"] != q]) for q in qs),
            "leave_one_province_out": {L.NAMES[p]: acc(S[S["province_code"] != p]) for p in L.PROVS},
            "by_province": {L.NAMES[p]: {"acc": acc(S[S["province_code"] == p]), "HIGH": int(S[S["province_code"] == p]["y"].sum())}
                            for p in L.PROVS},
            "confusion": {"TP": int(((S[f"{arm}_yhat"] == 1) & (S["y"] == 1)).sum()),
                          "TN": int(((S[f"{arm}_yhat"] == 0) & (S["y"] == 0)).sum()),
                          "FP": int(((S[f"{arm}_yhat"] == 1) & (S["y"] == 0)).sum()),
                          "FN": int(((S[f"{arm}_yhat"] == 0) & (S["y"] == 1)).sum())}}


def prf(S, arm):
    tp = int(((S[f"{arm}_yhat"] == 1) & (S["y"] == 1)).sum())
    fp = int(((S[f"{arm}_yhat"] == 1) & (S["y"] == 0)).sum())
    fn = int(((S[f"{arm}_yhat"] == 0) & (S["y"] == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    return {"precision_HIGH": prec, "f1_HIGH": (2 * prec * rec / (prec + rec)) if prec and rec else None}


def main():
    proto = verify()
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    th = L.e40_spec()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = M.E46 / "runs" / f"i7_{stamp}"
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
        for name, kw in ARMS.items():
            f = I7.forecast(d, X, B, t, **kw)
            if f is None:
                continue
            r[f"{name}_p"], r[f"{name}_yhat"] = f["p"], (f["p"] >= f["threshold"]).astype(int)
            r[f"{name}_p_price"], r[f"{name}_p_hunger"] = f["p_price"], f["p_hunger"]
            r[f"{name}_F_hat"], r[f"{name}_G_hat"] = f["F_hat"], f["G_hat"]
            sel.setdefault(name, {})[L.qs(t)] = {k: f[k] for k in ("food_cfg", "gap_cfg", "food_rmse", "gap_rmse", "rho",
                                                                  "hunger_alpha", "hunger_rmse", "H_hat", "n_price_train_q")}
            if name == "I7":
                sel[name][L.qs(t)].update(food_grid=f["food_grid"], gap_grid=f["gap_grid"])
            if t == OPER:
                keep[name] = f
        rows.append(r)
    P7 = pd.concat(rows, ignore_index=True)
    P1 = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})
    P6 = pd.read_csv(RUN6 / "predictions.csv", dtype={"province_code": str})
    P = P1.merge(P6, on=["t", "province_code"], how="left").merge(P7, on=["t", "province_code"], how="left")
    # hunger condition for the fixed structural rules: E44 I2's own p_hunger >= 0.5 (same information)
    for m in P2.MULTS:
        P[f"BASE-m{m}_yhat"] = ((P[f"BASE-m{m}_sig"] == 1) & (P["I2_p_hunger"] >= 0.5)).astype(float)
        P.loc[P[f"BASE-m{m}_sig"].isna() | P["I2_p_hunger"].isna(), f"BASE-m{m}_yhat"] = np.nan
        P[f"BASE-m{m}_p"] = P[f"BASE-m{m}_yhat"]          # a decision only; its Brier score is not a probability score
    lab = P[P["y"].notna() & (P["target_q"] <= OPER)]
    req1 = E4.ITER + list(E4.VARIANTS) + E4.COMPARATORS
    S = lab.dropna(subset=[f"{a}_p" for a in req1])
    arms = list(ARMS) + FIXED + COMP
    S7 = S.dropna(subset=[f"{a}_p" for a in arms])
    EXT = lab.dropna(subset=[f"{a}_p" for a in list(ARMS) + FIXED + ["I2", "B-maj", "B-persist"]])
    tests = M.E46 / "runs" / "tests_status_i7.json"
    leak_ok = bool(tests.exists() and json.loads(tests.read_text()).get("passed"))
    res = {"addendum_sha256": proto, "run_utc": stamp,
           "evidence_status": "HINDSIGHT-INFORMED development evidence (ADDENDUM_I7 section 0); acceptance is prospective "
                              "only (PROTOCOL section 5 / ADDENDUM_I7 section 6).",
           "S44_rows_identical": bool(len(S7) == len(S)), "S44": {}, "EXT": {}, "PRICE": {}}
    for nm, D in (("S44", S7), ("EXT", EXT)):
        res[nm] = {"dates": int(D["target_q"].nunique()), "rows": int(len(D)), "HIGH": int(D["y"].sum()),
                   "quarters": [L.qs(int(q)) for q in sorted(D["target_q"].unique())],
                   "metrics": {a: {**E4.block(D, a), **prf(D, a)} for a in (arms if nm == "S44" else
                                                                           list(ARMS) + FIXED + ["I2", "B-maj", "B-persist"])},
                   "robustness": {a: robustness(D, a) for a in list(ARMS) + ["I2"]}}
    res["S44"]["paired_I7"] = E4.paired(S7, "I7", [a for a in arms if a != "I7"])
    res["S44"]["gates_I7"] = E4.gates(res["S44"]["metrics"]["I7"], res["S44"]["paired_I7"], leak_ok)
    # PRICE: the province price signal alone (no SWS needed), including 2025-Q2/Q3
    F = L.quarter_F(d)
    HL = L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
    Y = F.merge(HL, on=["province_code", "q"])
    Y["ps"] = ((Y["F"] > Y["province_code"].map(th["food"])) |
               ((Y["F"] - Y["HL"]) > Y["province_code"].map(th["gap"]))).astype(int)
    PR = P.merge(Y.rename(columns={"q": "target_q"})[["province_code", "target_q", "ps"]], on=["province_code", "target_q"])
    PR = PR[(PR["target_q"] <= OPER)].dropna(subset=["I7_p_price"])
    res["PRICE"] = {"dates": int(PR["target_q"].nunique()), "rows": int(len(PR)), "signal": int(PR["ps"].sum()),
                    "accuracy": {a: float(((PR[f"{a}_p_price"] >= 0.5).astype(int) == PR["ps"]).mean()) for a in ARMS}
                    | {a: float((PR[f"{a}_sig"] == PR["ps"]).mean()) for a in FIXED},
                    "brier": {a: float(((PR[f"{a}_p_price"] - PR["ps"]) ** 2).mean()) for a in ARMS}}
    g, rb = res["S44"]["gates_I7"], res["S44"]["robustness"]["I7"]
    res["final_candidate_rule"] = {
        "gates_A0_A4": g["passes"], "EXT_accuracy_ge_0.75": res["EXT"]["metrics"]["I7"]["accuracy"] >= 0.75,
        "min_leave_one_quarter_out_ge_0.70": rb["min_leave_one_quarter_out"] >= 0.70}
    res["final_candidate_rule"]["I7_is_final_candidate"] = all(res["final_candidate_rule"].values())
    res["forecasting_acceptance_met"] = False
    (out / "selections_i7.json").write_text(json.dumps(sel, indent=1, default=str))
    P7.to_csv(out / "predictions_i7.csv", index=False)
    (out / "results_i7.json").write_text(json.dumps(res, indent=1, default=float))

    fz = M.E46 / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = P7[P7["t"] == OPER].set_index("province_code")
        k = keep["I7"]
        rec = {"issued_by": "E46 I7", "origin": str(L.origin(OPER).date()), "origin_quarter": L.qs(OPER),
               "target_quarter": L.qs(OPER + 2), "lead_from_origin": 2, "addendum_sha256": proto,
               "decision_rule": "HIGH iff p >= 0.5", "policy_features_at_origin": M.policy_features(ev, OPER),
               "selection_at_origin": {"food_cfg": k["food_cfg"], "gap_cfg": k["gap_cfg"], "food_rmse": k["food_rmse"],
                                       "gap_rmse": k["gap_rmse"], "rho": k["rho"], "hunger_alpha": k["hunger_alpha"],
                                       "H_hat": k["H_hat"], "price_features": k["pcols"], "hunger_features": k["hcols"]},
               "provinces": {L.NAMES[p]: {c: (None if pd.isna(o.loc[p, c]) else float(o.loc[p, c]))
                                          for c in o.columns if c.startswith(tuple(ARMS)) or c.startswith("BASE")}
                             for p in L.PROVS}}
        fz.write_text(json.dumps(rec, indent=1, default=str))
        (fz.parent / (fz.stem + ".sha256")).write_text(E4.sha(fz) + "  " + fz.name + "\n")

    for nm in ("S44", "EXT"):
        s = res[nm]
        print(stamp, nm, s["dates"], s["rows"], s["HIGH"], s["quarters"][0], "..", s["quarters"][-1])
        for a, m in s["metrics"].items():
            print(f"  {a:10s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal "
                  f"{None if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
                  f"recH {None if m['recall_HIGH'] is None else round(m['recall_HIGH'], 2)} "
                  f"recL {None if m['recall_LOW'] is None else round(m['recall_LOW'], 2)} brier {m['brier']:.3f} "
                  f"auc {None if m.get('roc_auc') is None else round(m['roc_auc'], 3)}")
    print("  S44 rows identical:", res["S44_rows_identical"], "| gates I7:", res["S44"]["gates_I7"])
    print("  robustness I7:", rb["min_leave_one_quarter_out"], rb["confusion"])
    print("  PRICE", res["PRICE"])
    print("  final-candidate rule:", res["final_candidate_rule"])


if __name__ == "__main__":
    main()
