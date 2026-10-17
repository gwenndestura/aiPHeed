"""E47 single run under the frozen PROTOCOL.md: rolling-origin as-of forecasts of I7-E, SL-P, SL-5T and LGBM-C
(2021-Q3..2026-Q3 origins), compared on identical rows with I7, I8, I2 and the baselines; track-record selection;
prospective 2027-Q1 freeze.

    backend/venv/Scripts/python.exe -B runner/e47_evaluate.py
      -> runs/<UTC stamp>/{predictions.csv, selections.json, results.json}; frozen/E47_PROSPECTIVE_2027Q1.json (+ .sha256)
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
import e47_lib as E  # noqa: E402

M, K, L, P2, np, pd = E.M, E.K, E.L, E.P2, E.np, E.pd
EXP = E.E47.parent
sys.path.insert(0, str(EXP / "E44_Five_Trigger_Optimization" / "runner"))
import e44_evaluate as E4  # noqa: E402

RUN1 = EXP / "E44_Five_Trigger_Optimization" / "runs" / "20261015T150213Z"
RUN7 = EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z"
RUN8 = EXP / "E46_Rice_Policy" / "runs" / "i8_20261017T001227Z"
OPER = L.qi("2026-Q3")
NEW = ["I7-E", "SL-P", "SL-5T", "LGBM-C"]
FIVE_TRIGGER = ["I7", "I7-E", "SL-5T", "LGBM-C"]
REF = ["I7", "I8", "I2", "BASE-m1.0"]
BASE = ["B-maj", "B-persist", "E38-served", "E41-M1"]


def verify() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E.E47 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def prf(S, a):
    y, h = S["y"].astype(int), S[f"{a}_yhat"].astype(int)
    tp, fp, fn = int(((h == 1) & (y == 1)).sum()), int(((h == 1) & (y == 0)).sum()), int(((h == 0) & (y == 1)).sum())
    tn = int(((h == 0) & (y == 0)).sum())
    pr = tp / (tp + fp) if tp + fp else None
    rc = tp / (tp + fn) if tp + fn else None
    return {"precision_HIGH": pr, "f1_HIGH": (2 * pr * rc / (pr + rc)) if pr and rc else None,
            "confusion": {"TP": tp, "TN": tn, "FP": fp, "FN": fn}, "share_predicted_LOW": float((h == 0).mean())}


def loqo(S, a):
    acc = lambda g: float((g[f"{a}_yhat"] == g["y"]).mean())  # noqa: E731
    qs = sorted(S["target_q"].unique())
    return {"min": min(acc(S[S["target_q"] != q]) for q in qs),
            "by_dropped_quarter": {L.qs(int(q)): acc(S[S["target_q"] != q]) for q in qs},
            "by_province": {L.NAMES[p]: acc(S[S["province_code"] == p]) for p in L.PROVS}}


def main():
    proto = verify()
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E.E47 / "runs" / stamp
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    X = E.features(d, x, origins, ev)
    B = P2.bases(d, origins)
    D = E.margin_frame(X, B)
    rows, sel, keep = [], {}, {}
    for t in origins:
        r = pd.DataFrame({"t": t, "province_code": L.PROVS})
        f = E.forecast_i7e(d, X, B, t)
        if f is not None:
            r["I7-E_p"], r["I7-E_yhat"] = f["p"], (f["p"] >= 0.5).astype(int)
            sel.setdefault("I7-E", {})[L.qs(t)] = {"food_cfg": f["food_cfg"], "gap_cfg": f["gap_cfg"]}
            if t == OPER:
                keep["I7-E"] = f
        for kind in ("SL-P", "SL-5T", "LGBM-C"):
            g = E.forecast_sl(kind, D, d, t)
            if g is None:
                continue
            r[f"{kind}_p"], r[f"{kind}_yhat"] = g["p"], (g["p"] >= g["threshold"]).astype(int)
            sel.setdefault(kind, {})[L.qs(t)] = {"threshold": g["threshold"], "n_oof": g["n_oof"],
                                                 "n_train": g["n_train"], "n_train_HIGH": g["n_train_HIGH"]}
            if t == OPER:
                keep[kind] = g
        rows.append(r)
    PN = pd.concat(rows, ignore_index=True)
    P1 = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})
    P7 = pd.read_csv(RUN7 / "predictions_i7.csv", dtype={"province_code": str})
    P8 = pd.read_csv(RUN8 / "predictions_i8.csv", dtype={"province_code": str})
    P = (P1.merge(P7[["t", "province_code", "I7_p", "I7_yhat", "BASE-m1.0_sig"]], on=["t", "province_code"], how="left")
         .merge(P8[["t", "province_code", "I8_p", "I8_yhat"]], on=["t", "province_code"], how="left")
         .merge(PN, on=["t", "province_code"], how="left"))
    P["BASE-m1.0_yhat"] = ((P["BASE-m1.0_sig"] == 1) & (P["I2_p_hunger"] >= 0.5)).astype(float)
    P.loc[P["BASE-m1.0_sig"].isna() | P["I2_p_hunger"].isna(), "BASE-m1.0_yhat"] = np.nan
    P["BASE-m1.0_p"] = P["BASE-m1.0_yhat"]
    lab = P[P["y"].notna() & (P["target_q"] <= OPER)]
    arms = NEW + REF + BASE
    S = lab.dropna(subset=[f"{a}_p" for a in arms])
    tests = E.E47 / "runs" / "tests_status.json"
    leak_ok = bool(tests.exists() and json.loads(tests.read_text()).get("passed"))
    res = {"protocol_sha256": proto, "run_utc": stamp,
           "evidence_status": "DEVELOPMENT evidence: every evaluated quarter was examined in E41-E46; the only "
                              "independent evaluation is prospective (PROTOCOL section 7).",
           "rows": int(len(S)), "independent_quarters": int(S["target_q"].nunique()), "HIGH": int(S["y"].sum()),
           "quarters": [L.qs(int(q)) for q in sorted(S["target_q"].unique())],
           "metrics": {a: {**E4.block(S, a), **prf(S, a)} for a in arms},
           "stability": {a: loqo(S, a) for a in NEW + REF}}
    # track-record selection (PROTOCOL section 5): Brier on the labelled targets <= 2026-Q2 (known at the 2027-Q1 issue)
    TR = S[S["target_q"] <= L.qi("2026-Q2")]
    res["track_record_brier"] = {a: float(((TR[f"{a}_p"] - TR["y"]) ** 2).mean()) for a in FIVE_TRIGGER}
    chosen = min(FIVE_TRIGGER, key=lambda a: (round(res["track_record_brier"][a], 10), FIVE_TRIGGER.index(a)))
    res["selected"] = chosen
    pr = E4.paired(S, chosen, [a for a in arms if a != chosen])
    res["paired_selected"] = pr
    g = E4.gates(res["metrics"][chosen], pr, leak_ok)
    res["gates_selected"] = g
    res["acceptance_rule"] = {"A0_A4": g["passes"], "min_leave_one_quarter_out_ge_0.70": res["stability"][chosen]["min"] >= 0.70}
    res["acceptance_rule"]["development_criteria_met"] = all(res["acceptance_rule"].values())
    res["forecasting_acceptance_met"] = False
    PN.to_csv(out / "predictions.csv", index=False)
    X.to_csv(out / "features_asof.csv", index=False)
    (out / "selections.json").write_text(json.dumps(sel, indent=1, default=str))
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))

    fz = E.E47 / "frozen" / "E47_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        fz.parent.mkdir(exist_ok=True)
        o = PN[PN["t"] == OPER].set_index("province_code")
        rec = {"issued_by": "E47", "origin": str(L.origin(OPER).date()), "origin_quarter": L.qs(OPER),
               "target_quarter": L.qs(OPER + 2), "lead_from_origin": 2, "protocol_sha256": proto,
               "cpi_months_used_through": L.ym_s(L.m0_of(OPER)), "selected_by_track_record": chosen,
               "energy_at_origin": E.energy_features(OPER, E.load_brent()),
               "thresholds_at_origin": {k: keep[k]["threshold"] for k in ("SL-P", "SL-5T", "LGBM-C") if k in keep},
               "provinces": {L.NAMES[p]: {c: (None if pd.isna(o.loc[p, c]) else float(o.loc[p, c]))
                                          for c in o.columns if c.endswith(("_p", "_yhat"))} for p in L.PROVS}}
        fz.write_text(json.dumps(rec, indent=1, default=str))
        (fz.parent / (fz.stem + ".sha256")).write_text(E4.sha(fz) + "  " + fz.name + "\n")

    print(stamp, "rows", res["rows"], "quarters", res["independent_quarters"], "HIGH", res["HIGH"], res["quarters"])
    for a in arms:
        m = res["metrics"][a]
        print(f"  {a:11s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal "
              f"{None if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
              f"recH {None if m['recall_HIGH'] is None else round(m['recall_HIGH'], 2)} "
              f"recL {None if m['recall_LOW'] is None else round(m['recall_LOW'], 2)} brier {m['brier']:.3f} "
              f"auc {None if m.get('roc_auc') is None else round(m['roc_auc'], 3)} {m['confusion']}")
    print("  track-record Brier:", {k: round(v, 4) for k, v in res["track_record_brier"].items()}, "-> selected", chosen)
    print("  gates:", g, "| LOQO min:", round(res["stability"][chosen]["min"], 3), "| rule:", res["acceptance_rule"])


if __name__ == "__main__":
    main()
