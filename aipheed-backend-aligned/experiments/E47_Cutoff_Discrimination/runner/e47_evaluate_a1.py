"""E47 addendum A1 single run (ADDENDUM_A1.md): PS-P and PS-5T in the product structure, compared on identical rows.

    backend/venv/Scripts/python.exe -B runner/e47_evaluate_a1.py
      -> runs/a1_<UTC stamp>/{predictions_a1.csv, results_a1.json}; frozen/E47_A1_PROSPECTIVE_2027Q1.json (+ .sha256)
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
import e47_a1 as A  # noqa: E402
import e47_evaluate as V  # noqa: E402

E, M, K, L, P2, np, pd, E4 = A.E, A.M, A.K, A.L, A.P2, A.np, A.pd, V.E4
RUNE = E.E47 / "runs" / "20261017T031323Z"
OPER = L.qi("2026-Q3")
ARMS = ["PS-P", "PS-5T"]
FIVE = ["I7", "I7-E", "PS-5T"]
REF = ["I7", "I7-E", "I8", "I2", "BASE-m1.0"]
BASE = ["B-maj", "B-persist", "E38-served", "E41-M1"]


def verify() -> str:
    want = (HERE / "ADDENDUM_A1_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E.E47 / "ADDENDUM_A1.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("ADDENDUM_A1.md changed after freezing")
    return got


def main():
    proto = verify()
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E.E47 / "runs" / f"a1_{stamp}"
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    X = E.features(d, x, origins, ev)
    D = E.margin_frame(X, P2.bases(d, origins))
    P7 = pd.read_csv(V.RUN7 / "predictions_i7.csv", dtype={"province_code": str})
    ph = P7.set_index(["t", "province_code"])["I7_p_hunger"]
    rows, taus = [], {}
    for t in origins:
        r = pd.DataFrame({"t": t, "province_code": L.PROVS})
        for kind in ARMS:
            f = A.forecast_ps(kind, D, d, t)
            if f is None:
                continue
            h = np.array([ph.get((t, p), np.nan) for p in L.PROVS])
            r[f"{kind}_p_ps"] = f["p_ps"]
            r[f"{kind}_p"] = h * f["p_ps"]
            r[f"{kind}_yhat"] = np.where(np.isnan(h), np.nan, ((h >= 0.5) & (f["p_ps"] >= f["tau"])).astype(float))
            taus.setdefault(kind, {})[L.qs(t)] = {"tau_ps": f["tau"], "n_train": f["n_train"],
                                                  "n_train_signal": f["n_train_signal"]}
        rows.append(r)
    PA = pd.concat(rows, ignore_index=True)
    P1 = pd.read_csv(V.RUN1 / "predictions.csv", dtype={"province_code": str})
    P8 = pd.read_csv(V.RUN8 / "predictions_i8.csv", dtype={"province_code": str})
    PE = pd.read_csv(RUNE / "predictions.csv", dtype={"province_code": str})
    P = (P1.merge(P7[["t", "province_code", "I7_p", "I7_yhat", "I7_p_price", "BASE-m1.0_sig"]], on=["t", "province_code"], how="left")
         .merge(P8[["t", "province_code", "I8_p", "I8_yhat"]], on=["t", "province_code"], how="left")
         .merge(PE[["t", "province_code", "I7-E_p", "I7-E_yhat"]], on=["t", "province_code"], how="left")
         .merge(PA, on=["t", "province_code"], how="left"))
    P["BASE-m1.0_yhat"] = ((P["BASE-m1.0_sig"] == 1) & (P["I2_p_hunger"] >= 0.5)).astype(float)
    P.loc[P["BASE-m1.0_sig"].isna() | P["I2_p_hunger"].isna(), "BASE-m1.0_yhat"] = np.nan
    P["BASE-m1.0_p"] = P["BASE-m1.0_yhat"]
    lab = P[P["y"].notna() & (P["target_q"] <= OPER)]
    arms = ARMS + REF + BASE
    tests = E.E47 / "runs" / "tests_status_a1.json"
    leak_ok = bool(tests.exists() and json.loads(tests.read_text()).get("passed"))
    res = {"addendum_sha256": proto, "run_utc": stamp, "tau_ps": taus,
           "evidence_status": "HINDSIGHT-INFORMED development evidence (ADDENDUM_A1 section 0); acceptance is prospective only."}
    for nm, lo in (("E47_rows", L.qi("2024-Q3")), ("EXT_rows", L.qi("2024-Q2"))):
        S = lab[lab["target_q"] >= lo].dropna(subset=[f"{a}_p" for a in arms])
        res[nm] = {"rows": int(len(S)), "independent_quarters": int(S["target_q"].nunique()), "HIGH": int(S["y"].sum()),
                   "quarters": [L.qs(int(q)) for q in sorted(S["target_q"].unique())],
                   "metrics": {a: {**E4.block(S, a), **V.prf(S, a)} for a in arms},
                   "stability": {a: V.loqo(S, a) for a in ARMS + ["I7"]}}
    S = lab[lab["target_q"] >= L.qi("2024-Q3")].dropna(subset=[f"{a}_p" for a in arms])
    TR = S[S["target_q"] <= L.qi("2026-Q2")]
    res["track_record_brier"] = {a: float(((TR[f"{a}_p"] - TR["y"]) ** 2).mean()) for a in FIVE}
    chosen = min(FIVE, key=lambda a: (round(res["track_record_brier"][a], 10), FIVE.index(a)))
    res["selected"] = chosen
    pr = E4.paired(S, chosen, [a for a in arms if a != chosen])
    g = E4.gates(res["E47_rows"]["metrics"][chosen], pr, leak_ok)
    res["gates_selected"], res["paired_selected"] = g, pr
    loq = V.loqo(S, chosen)["min"]
    res["acceptance_rule"] = {"A0_A4": g["passes"], "min_leave_one_quarter_out_ge_0.70": loq >= 0.70}
    res["acceptance_rule"]["development_criteria_met"] = all(res["acceptance_rule"].values())
    res["forecasting_acceptance_met"] = False
    # price-signal accuracy on every producible quarter (2025-Q2/Q3 included)
    Y = A.ps_labels(d, OPER + 3).rename(columns={"q": "target_q"})
    PR = P.merge(Y, on=["province_code", "target_q"]).dropna(subset=["PS-P_p_ps", "I7_p_price"])
    PR = PR[PR["target_q"] <= OPER]
    res["PRICE"] = {"rows": int(len(PR)), "quarters": int(PR["target_q"].nunique()), "signal": int(PR["ps"].sum()),
                    "accuracy": {"PS-P": float(((PR["PS-P_p_ps"] >= 0.5).astype(int) == PR["ps"]).mean()),
                                 "PS-5T": float(((PR["PS-5T_p_ps"] >= 0.5).astype(int) == PR["ps"]).mean()),
                                 "I7": float(((PR["I7_p_price"] >= 0.5).astype(int) == PR["ps"]).mean())},
                    "brier": {"PS-P": float(((PR["PS-P_p_ps"] - PR["ps"]) ** 2).mean()),
                              "PS-5T": float(((PR["PS-5T_p_ps"] - PR["ps"]) ** 2).mean()),
                              "I7": float(((PR["I7_p_price"] - PR["ps"]) ** 2).mean())}}
    PA.to_csv(out / "predictions_a1.csv", index=False)
    (out / "results_a1.json").write_text(json.dumps(res, indent=1, default=float))
    fz = E.E47 / "frozen" / "E47_A1_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = PA[PA["t"] == OPER].set_index("province_code")
        rec = {"issued_by": "E47 A1", "origin": str(L.origin(OPER).date()), "target_quarter": L.qs(OPER + 2),
               "addendum_sha256": proto, "selected_by_track_record": chosen,
               "tau_ps_at_origin": {k: taus[k][L.qs(OPER)]["tau_ps"] for k in ARMS},
               "provinces": {L.NAMES[p]: {c: (None if pd.isna(o.loc[p, c]) else float(o.loc[p, c])) for c in o.columns
                                          if c != "t"} for p in L.PROVS}}
        fz.write_text(json.dumps(rec, indent=1, default=str))
        (fz.parent / (fz.stem + ".sha256")).write_text(E4.sha(fz) + "  " + fz.name + "\n")
    for nm in ("E47_rows", "EXT_rows"):
        s = res[nm]
        print(stamp, nm, s["rows"], "rows", s["independent_quarters"], "quarters", s["HIGH"], "HIGH")
        for a in arms:
            m = s["metrics"][a]
            print(f"  {a:11s} acc {m['accuracy']:.3f} bal {None if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
                  f"recH {None if m['recall_HIGH'] is None else round(m['recall_HIGH'], 2)} "
                  f"recL {None if m['recall_LOW'] is None else round(m['recall_LOW'], 2)} brier {m['brier']:.3f} "
                  f"auc {None if m.get('roc_auc') is None else round(m['roc_auc'], 3)} {m['confusion']}")
    print("  track-record Brier:", {k: round(v, 4) for k, v in res["track_record_brier"].items()}, "-> selected", chosen)
    print("  gates:", g, "| rule:", res["acceptance_rule"])
    print("  PRICE:", res["PRICE"])


if __name__ == "__main__":
    main()
