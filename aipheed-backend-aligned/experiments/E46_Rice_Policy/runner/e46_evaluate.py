"""E46 single run under the frozen PROTOCOL.md (I6, I6b, I6-MKT on E44's S44 rows; prospective freeze).

    backend/venv/Scripts/python.exe -B runner/e46_evaluate.py
      -> runs/<UTC stamp>/{predictions.csv, results.json}; frozen/E46_PROSPECTIVE_2027Q1.json (+ .sha256)
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
import e46_lib as M  # noqa: E402

L, K, P2, np, pd = M.L, M.K, M.P2, M.np, M.pd
E44 = M.E46.parent / "E44_Five_Trigger_Optimization"
sys.path.insert(0, str(E44 / "runner"))
import e44_evaluate as E4  # noqa: E402

RUN1 = E44 / "runs" / "20261015T150213Z"
OPER = L.qi("2026-Q3")
NO_NATIONAL = [g for g in P2.ALL_GROUPS if g not in ("employment", "ofw_remittance")]
ARMS = {"I6": dict(), "I6b": dict(hunger_groups=NO_NATIONAL), "I6-MKT": dict(price_groups=["market"], hunger_rw=True)}
COMP = ["I2", "B-maj", "B-persist", "B-clim", "SIM-0", "SIM-5T", "E41-M1", "E38-served"]


def verify() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((M.E46 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def main():
    proto = verify()
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = M.E46 / "runs" / stamp
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    X = M.features(d, x, origins, ev)
    B = P2.bases(d, origins)
    rows, sel, keep = [], {}, {}
    for t in origins:
        r = pd.DataFrame({"t": t, "province_code": L.PROVS})
        for name, kw in ARMS.items():
            f = M.forecast(d, X, B, t, **kw)
            if f is None:
                continue
            r[f"{name}_p"], r[f"{name}_yhat"] = f["p"], (f["p"] >= f["threshold"]).astype(int)
            r[f"{name}_F_hat"], r[f"{name}_p_hunger"], r[f"{name}_p_price"] = f["F_hat"], f["p_hunger"], f["p_price"]
            sel.setdefault(name, {})[L.qs(t)] = {"price_cfg": f["price_cfg"], "price_rmse": f["price_rmse"],
                                                 "hunger_alpha": f["hunger_alpha"], "threshold": f["threshold"],
                                                 "platt": f["platt"]}
            if t == OPER:
                keep[name] = f
        rows.append(r)
    P6 = pd.concat(rows, ignore_index=True)
    P1 = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})
    P = P1.merge(P6, on=["t", "province_code"], how="left")
    lab = P[P["y"].notna() & (P["target_q"] <= L.qi("2026-Q3"))]
    req1 = E4.ITER + list(E4.VARIANTS) + E4.COMPARATORS
    S = lab.dropna(subset=[f"{a}_p" for a in req1])
    arms = list(ARMS) + COMP
    S6 = S.dropna(subset=[f"{a}_p" for a in arms])
    tests = M.E46 / "runs" / "tests_status.json"
    leak_ok = bool(tests.exists() and json.loads(tests.read_text()).get("passed"))
    res = {"protocol_sha256": proto, "run_utc": stamp, "evidence_status":
           "HINDSIGHT-INFORMED development evidence (the policy block was designed from E45's error analysis of these "
           "quarters); not acceptance evidence. Acceptance is prospective only (PROTOCOL section 5).",
           "S44_rows_identical": bool(len(S6) == len(S)),
           "S44": {"dates": int(S6["target_q"].nunique()), "rows": int(len(S6)), "HIGH": int(S6["y"].sum()),
                   "metrics": {a: E4.block(S6, a) for a in arms},
                   "paired_I6": E4.paired(S6, "I6", [a for a in arms if a != "I6"]),
                   "paired_I6b": E4.paired(S6, "I6b", [a for a in arms if a != "I6b"])}}
    res["S44"]["gates_historical"] = {a: E4.gates(res["S44"]["metrics"][a], res["S44"][f"paired_{a}"], leak_ok)
                                      for a in ("I6", "I6b")}
    win = {"2024-Q2..2025-Q1": (L.qi("2024-Q2"), L.qi("2025-Q1")), "2025-Q4..2026-Q3": (L.qi("2025-Q4"), L.qi("2026-Q3"))}
    W = lab.dropna(subset=[f"{a}_p" for a in arms])
    res["windows"] = {w: {a: E4.block(W[(W["target_q"] >= lo) & (W["target_q"] <= hi)], a) for a in arms}
                      for w, (lo, hi) in win.items() if len(W[(W["target_q"] >= lo) & (W["target_q"] <= hi)])}
    res["by_quarter_I6"] = {L.qs(int(q)): {"rows": int(len(g)), "HIGH": int(g["y"].sum()),
                                           "correct": int((g["I6_yhat"] == g["y"]).sum())}
                            for q, g in S6.groupby("target_q")}
    (out / "selections.json").write_text(json.dumps(sel, indent=1, default=str))
    P6.to_csv(out / "predictions.csv", index=False)
    X.to_csv(out / "features_asof.csv", index=False)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))

    fz = M.E46 / "frozen" / "E46_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = P6[P6["t"] == OPER].set_index("province_code")
        rec = {"issued_by": "E46", "origin": str(L.origin(OPER).date()), "origin_quarter": L.qs(OPER),
               "target_quarter": L.qs(OPER + 2), "lead_from_origin": 2, "protocol_sha256": proto,
               "policy_features_at_origin": M.policy_features(ev, OPER),
               "selections_at_origin": {n: {"price_cfg": k["price_cfg"], "threshold": k["threshold"],
                                            "price_features": k["pcols"], "hunger_features": k["hcols"]}
                                        for n, k in keep.items()},
               "provinces": {L.NAMES[p]: {c: (None if pd.isna(o.loc[p, c]) else float(o.loc[p, c]))
                                          for c in o.columns if c.endswith(("_p", "_yhat"))} for p in L.PROVS}}
        fz.write_text(json.dumps(rec, indent=1, default=str))
        (fz.parent / (fz.stem + ".sha256")).write_text(E4.sha(fz) + "  " + fz.name + "\n")

    s = res["S44"]
    print(stamp, "S44", s["dates"], s["rows"], s["HIGH"], "identical:", res["S44_rows_identical"])
    for a in arms:
        m = s["metrics"][a]
        print(f"  {a:10s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal "
              f"{m['balanced_accuracy'] if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
              f"recH {None if m['recall_HIGH'] is None else round(m['recall_HIGH'], 2)} "
              f"recL {None if m['recall_LOW'] is None else round(m['recall_LOW'], 2)} brier {m['brier']:.3f} auc {m.get('roc_auc')}")
    print("  gates (historical, hindsight)", s["gates_historical"])
    print("  by quarter I6", res["by_quarter_I6"])


if __name__ == "__main__":
    main()
