"""E44 iteration I5 (ADDENDUM_I5.md): run once + byte-identical repeat; scored on run 1's S44 rows.

    backend/venv/Scripts/python.exe -B runner/e44_evaluate_i5.py
      -> runs/i5_<UTC stamp>/{predictions_i5.csv, results_i5.json}; frozen/E44_I5_PROSPECTIVE_2027Q1.json
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
import e44_evaluate as E  # noqa: E402

P2, C, K, L, np, pd = E.P2, E.C, E.K, E.L, E.np, E.pd
RUN1 = E.E44 / "runs" / "20261015T150213Z"
VARIANTS = {"I5-MKT": dict(groups=["market"], hunger_rw=True)}
for g in P2.ALL_GROUPS:
    VARIANTS[f"I5-drop_{g}"] = dict(groups=[x for x in P2.ALL_GROUPS if x != g])


def verify():
    E.verify_protocol()
    want = (HERE / "ADDENDUM_I5_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E.E44 / "ADDENDUM_I5.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("ADDENDUM_I5.md changed after freezing")
    return got


def main():
    add = verify()
    d, x = L.load(), K.load_extra()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E.E44 / "runs" / f"i5_{stamp}"
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), E.OPER + 1))
    X = P2.features(d, x, origins)
    B = P2.bases(d, origins)
    rows, sel, keep = [], {}, None
    for t in origins:
        r = pd.DataFrame({"t": t, "province_code": L.PROVS})
        for name, kw in [("I5", {})] + list(VARIANTS.items()):
            f = P2.forecast_i5(d, X, B, t, **kw)
            if f is None:
                continue
            r[f"{name}_p"], r[f"{name}_yhat"] = f["p"], (f["p"] >= f["threshold"]).astype(int)
            if name == "I5":
                r["I5_p_hunger"], r["I5_p_price"], r["I5_F_hat"], r["I5_G_hat"] = f["p_hunger"], f["p_price"], f["F_hat"], f["G_hat"]
                sel[L.qs(t)] = {k: f[k] for k in ("food_cfg", "gap_cfg", "food_rmse", "gap_rmse", "rho", "hunger_alpha",
                                                  "hunger_rmse", "threshold", "platt", "H_hat")}
                if t == E.OPER:
                    keep = f
        rows.append(r)
    P4 = pd.concat(rows, ignore_index=True)
    P1 = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})
    P = P1.merge(P4, on=["t", "province_code"], how="left")
    lab = P[P["y"].notna() & (P["target_q"] <= L.qi("2026-Q3"))]
    req1 = E.ITER + list(E.VARIANTS) + E.COMPARATORS
    S = lab.dropna(subset=[f"{a}_p" for a in req1])                     # run-1 S44 rows exactly
    arms = ["I5"] + list(VARIANTS) + ["I1", "I2", "I3", "I2-MKT"] + E.COMPARATORS
    S4 = S.dropna(subset=[f"{a}_p" for a in arms])
    leak = E.E44 / "runs" / "tests_status.json"
    leak_ok = bool(leak.exists() and json.loads(leak.read_text()).get("passed"))
    res = {"addendum_sha256": add, "run_utc": stamp, "S44_rows_identical_to_run1": bool(len(S4) == len(S)),
           "S44": {"dates": int(S4["target_q"].nunique()), "rows": int(len(S4)), "HIGH": int(S4["y"].sum()),
                   "metrics": {a: E.block(S4, a) for a in arms}}}
    res["S44"]["paired_I5"] = E.paired(S4, "I5", [a for a in arms if a != "I5"])
    res["S44"]["gates_I5"] = E.gates(res["S44"]["metrics"]["I5"], res["S44"]["paired_I5"], leak_ok)
    res["final_candidate"] = "I5" if res["S44"]["gates_I5"]["passes"] else "I2"
    res["forecasting_acceptance_met"] = bool(res["S44"]["gates_I5"]["passes"])
    L4 = lab.dropna(subset=["I5_p"] + [f"{a}_p" for a in E.COMPARATORS])
    res["I5_long"] = {"dates": int(L4["target_q"].nunique()), "rows": int(len(L4)), "HIGH": int(L4["y"].sum()),
                      "metrics": {a: E.block(L4, a) for a in ["I5"] + E.COMPARATORS}}
    (out / "selections_i5.json").write_text(json.dumps(sel, indent=1, default=str))
    P4.to_csv(out / "predictions_i5.csv", index=False)
    (out / "results_i5.json").write_text(json.dumps(res, indent=1, default=float))

    fz = E.E44 / "frozen" / "E44_I5_PROSPECTIVE_2027Q1.json"
    if not fz.exists() and keep is not None:
        o = P4[P4["t"] == E.OPER].set_index("province_code")
        rec = {"issued_by": "E44-I5", "origin": str(L.origin(E.OPER).date()), "origin_quarter": L.qs(E.OPER),
               "target_quarter": L.qs(E.OPER + 2), "lead_from_origin": 2, "addendum_sha256": add,
               "final_candidate": res["final_candidate"], "forecasting_acceptance_met": res["forecasting_acceptance_met"],
               "selection_at_origin": {k: keep[k] for k in ("food_cfg", "gap_cfg", "food_rmse", "gap_rmse", "rho",
                                                            "hunger_alpha", "hunger_rmse", "threshold", "platt", "H_hat")},
               "price_features": keep["pcols"], "hunger_features": keep["hcols"],
               "provinces": {L.NAMES[p]: {"province_code": p, **{c: (None if pd.isna(o.loc[p, c]) else float(o.loc[p, c]))
                                                                 for c in o.columns if c.startswith("I5")}}
                             for p in L.PROVS}}
        fz.write_text(json.dumps(rec, indent=1, default=str))
        (fz.parent / (fz.stem + ".sha256")).write_text(E.sha(fz) + "  " + fz.name + "\n")

    s = res["S44"]
    print(stamp, "S44", s["dates"], s["rows"], s["HIGH"], "identical rows:", res["S44_rows_identical_to_run1"])
    for a in arms:
        m = s["metrics"][a]
        print(f"  {a:18s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal {m['balanced_accuracy'] if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
              f"recH {None if m['recall_HIGH'] is None else round(m['recall_HIGH'], 2)} recL {None if m['recall_LOW'] is None else round(m['recall_LOW'], 2)} brier {m['brier']:.3f} auc {m.get('roc_auc')}")
    print("  gates I5", s["gates_I5"], "final", res["final_candidate"])
    lg = res["I5_long"]
    print("  I5 long", lg["dates"], lg["rows"], lg["HIGH"], {a: (round(m["accuracy"], 3), round(m["balanced_accuracy"] or 0, 3), round(m["brier"], 3)) for a, m in lg["metrics"].items()})


if __name__ == "__main__":
    main()
