"""E56 single run under the frozen PROTOCOL.md: E56-TUNED forecasts at every origin (nested selection over the 72-
configuration space), scored with E55-LGBM, the committed comparators and the Objective 4 baselines on E55's identical
45 rows; province-discrimination and calibration diagnostics; the section 5 final-model decision; the prospective freeze
when E56-TUNED is selected.

    backend/venv/Scripts/python.exe -B runner/e56_evaluate.py  -> runs/<UTC stamp>/{predictions.csv, rows.csv, selections.json, results.json}
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
import e56_lib as G  # noqa: E402

E, L, np, pd, F = G.E, G.L, G.np, G.pd, G.F
E55 = G.EXP / "E55_Food_Insecurity_LightGBM"
RUN55 = E55 / "runs" / "20261017T153947Z"
RUN7 = G.EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z" / "predictions_i7.csv"
ORIGINS = list(range(L.qi("2023-Q4"), L.qi("2026-Q3") + 1))
OPER = L.qi("2026-Q3")
BASELINES = ["B1_PERSIST", "B2_LR_GOV", "B3_LGBM_GOV", "B4_LR_NLP", "B5_LGBM_NLP", "B6_LR_COMB", "B7_E38PROC",
             "CLIM", "HIGH", "LOW"]
MODELS = ["E56-TUNED", "E55-LGBM", "I7", "I7-BASE", "E52"]
FROZEN = G.E56 / "frozen" / "E56_TUNED_PROSPECTIVE_2027Q1.json"


def verify() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((G.E56 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def full_metrics(R, arms, seed=56):
    Mb = E.block(R, arms, seed=seed)
    for a in arms:
        Mb[a]["precision_LOW"] = G.low_precision(R, a)
        Mb[a]["n_quarters"] = int(R["target"].nunique())
    return Mb


def main():
    proto = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = G.E56 / "runs" / stamp
    out.mkdir(parents=True)
    d, X, B = E.load()
    space = G.search_space()
    preds, sel = [], {}
    for t in ORIGINS:
        fx = G.tuned_forecast(d, X, B, t, space)
        if fx is None:
            continue
        sel[L.qs(t)] = {"cfg": fx["cfg"], "inner_logloss": fx["inner_logloss"], "n_train_rows": fx["n_train_rows"],
                        "n_train_q": fx["n_train_q"], "n_train_HIGH": fx["n_train_HIGH"], "p_hunger": fx["p_hunger"],
                        "is_e55_config": fx["cfg"]["id"] < 24}
        for i, p in enumerate(L.PROVS):
            preds.append({"t": t, "province_code": p, "arm": "E56-TUNED", "p": float(fx["p"][i]),
                          "p_price": float(fx["p_price"][i]), "p_hunger": float(fx["p_hunger"])})
        print("origin", L.qs(t), "cfg", fx["cfg"]["id"], flush=True)
    P = pd.DataFrame(preds)
    P["target"] = (P["t"] + 2).map(L.qs)
    P = P.sort_values(["t", "province_code"]).reset_index(drop=True)
    P.to_csv(out / "predictions.csv", index=False, float_format="%.12g")

    # ------------------------------------------------------------ identical rows (E55 primary 45 + supplementary 50)
    R = pd.read_csv(RUN55 / "rows.csv", dtype={"province_code": str})
    pm = P.set_index(["t", "province_code"])["p"]
    R["E56-TUNED_p"] = [float(pm.loc[(t, p)]) for t, p in zip(R["t"], R["province_code"])]
    R["E56-TUNED_yhat"] = (R["E56-TUNED_p"] >= 0.5).astype(int)
    keep = ["target", "t", "province_code", "y"] + [f"{a}_{s}" for a in MODELS + BASELINES for s in ("p", "yhat")]
    R = R[keep].sort_values(["target", "province_code"]).reset_index(drop=True)
    assert len(R) == 45 and int(R["y"].sum()) == 14
    R.to_csv(out / "rows.csv", index=False, float_format="%.12g")
    P55 = pd.read_csv(RUN55 / "predictions.csv", dtype={"province_code": str})
    P55 = P55[P55["arm"] == "E55-LGBM"].set_index(["t", "province_code"])["p"]
    lab = F.t43_labels(d)
    lab = {(p, int(q)): v for p, q, v in zip(lab["province_code"], lab["q"], lab["T43"]) if v == v}
    p7 = pd.read_csv(RUN7, dtype={"province_code": str}).set_index(["t", "province_code"])
    R50 = P[(P["t"] + 2 >= L.qi("2024-Q2")) & (P["t"] + 2 <= L.qi("2026-Q3"))][["t", "province_code", "target"]].copy()
    R50["y"] = [int(lab[(p, t + 2)]) for t, p in zip(R50["t"], R50["province_code"])]
    R50["E56-TUNED_p"] = [float(pm.loc[k]) for k in zip(R50["t"], R50["province_code"])]
    R50["E55-LGBM_p"] = [float(P55.loc[k]) for k in zip(R50["t"], R50["province_code"])]
    R50["I7_p"] = [float(p7.loc[k, "I7_p"]) for k in zip(R50["t"], R50["province_code"])]
    R50["E52_p"] = [float(p7.loc[k, "I7_p_price"]) for k in zip(R50["t"], R50["province_code"])]
    R50["LOW_p"] = 0.0
    for a in ("E56-TUNED", "E55-LGBM", "I7", "E52", "LOW"):
        R50[f"{a}_yhat"] = (R50[f"{a}_p"] >= 0.5).astype(int)
    assert len(R50) == 50

    arms = MODELS + BASELINES
    Mx = full_metrics(R, arms)
    M50 = full_metrics(R50, ["E56-TUNED", "E55-LGBM", "I7", "E52", "LOW"])
    cal = {a: E.calibration(R["y"], R[f"{a}_p"]) for a in arms if a not in ("HIGH", "LOW")}
    base = BASELINES

    def criteria(a):
        c = Mx[a]
        loqo = {q: float((R[R["target"] != q][f"{a}_yhat"] == R[R["target"] != q]["y"]).mean()) for q in R["target"].unique()}
        cr = {"A1_accuracy_ge_0.75": c["accuracy"] >= 0.75,
              "A2_balanced_and_recalls": (c["balanced_accuracy"] or 0) >= 0.70 and (c["recall_HIGH"] or 0) >= 0.60
              and (c["recall_LOW"] or 0) >= 0.60,
              "A3_brier_below_every_baseline": all(c["brier"] < Mx[b]["brier"] for b in base),
              "A4_balanced_above_every_baseline": all((c["balanced_accuracy"] or 0) > (Mx[b]["balanced_accuracy"] or 0) for b in base),
              "A5_min_leave_one_quarter_out_ge_0.70": min(loqo.values()) >= 0.70}
        cr["accepted_for_development"] = all(cr.values())
        return {"criteria": cr, "leave_one_quarter_out": loqo}
    crit = {a: criteria(a) for a in ("E56-TUNED", "E55-LGBM", "I7", "E52")}
    paired = {a: E.paired_brier(R, "E56-TUNED", a, seed=56) for a in arms if a != "E56-TUNED"}
    spread = {a: G.province_spread(R, a) for a in ("E56-TUNED", "E55-LGBM", "I7", "E52", "B1_PERSIST")}
    byprov = {a: G.by_province(R, a) for a in ("E56-TUNED", "E55-LGBM")}
    byq = {a: E.by_quarter_confusion(R, a) for a in ("E56-TUNED", "E55-LGBM")}
    a56, a55 = Mx["E56-TUNED"], Mx["E55-LGBM"]
    rule = {"a_brier_lower": a56["brier"] < a55["brier"],
            "b_balanced_not_worse_by_0.02": (a56["balanced_accuracy"] or 0) >= (a55["balanced_accuracy"] or 0) - 0.02}
    final = "E56-TUNED" if all(rule.values()) else "E55-LGBM"
    configs_used = {k: v["cfg"]["id"] for k, v in sel.items()}

    frozen_status = "not applicable (E55-LGBM retained; its 2027-Q1 forecast is frozen in E55)"
    if final == "E56-TUNED":
        op = P[P["t"] == OPER].set_index("province_code")
        fz = {"model": "E56-TUNED", "protocol_sha256": proto, "origin": str(L.origin(OPER).date()),
              "targetQuarter": L.qs(OPER + 2), "decision_threshold": 0.5, "selection": sel[L.qs(OPER)]["cfg"],
              "forecasts": {p: {"province": L.NAMES[p], "p": round(float(op.loc[p, "p"]), 6),
                                "p_price": round(float(op.loc[p, "p_price"]), 6),
                                "p_hunger": round(float(op.loc[p, "p_hunger"]), 6)} for p in L.PROVS}}
        FROZEN.parent.mkdir(exist_ok=True)
        if FROZEN.exists():
            assert json.loads(FROZEN.read_text())["forecasts"] == fz["forecasts"]
            frozen_status = "verified (already frozen)"
        else:
            FROZEN.write_text(json.dumps(fz, indent=1, sort_keys=True))
            (FROZEN.parent / (FROZEN.name + ".sha256")).write_text(
                hashlib.sha256(FROZEN.read_bytes()).hexdigest() + "  " + FROZEN.name + "\n")
            frozen_status = "written"

    res = {"protocol_sha256": proto, "run_utc": stamp, "search_space_size": len(space), "seed": G.SEED,
           "evidence_status": "development evidence (PROTOCOL 0); prospective 2027 quarters are the untouched test",
           "rows": int(len(R)), "quarters": sorted(R["target"].unique().tolist()), "HIGH": int(R["y"].sum()),
           "LOW": int((R["y"] == 0).sum()), "metrics": Mx, "calibration": cal, "criteria": crit,
           "paired_brier_E56_minus": paired, "province_spread": spread, "by_province": byprov,
           "by_quarter_confusion": byq, "supplementary_50_rows": {"rows": 50, "HIGH": int(R50["y"].sum()), "metrics": M50},
           "selection_rule": rule, "final_model": final, "configs_selected_by_origin": configs_used,
           "origins_with_e55_config": int(sum(v["is_e55_config"] for v in sel.values())),
           "prospective": frozen_status}
    (out / "selections.json").write_text(json.dumps(sel, indent=1, sort_keys=True, default=float))
    (out / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True, default=float))
    f = lambda v: None if v is None else round(v, 3)  # noqa: E731
    print(stamp, "rows", res["rows"], "HIGH", res["HIGH"], "final", final, rule)
    for a in arms:
        m = Mx[a]
        print(f"  {a:12s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal {f(m['balanced_accuracy'])} "
              f"recH {f(m['recall_HIGH'])} precH {f(m['precision_HIGH'])} recL {f(m['recall_LOW'])} precL {f(m['precision_LOW'])} "
              f"F1 {f(m['f1_HIGH'])} brier {m['brier']:.3f} auc {f(m['auc'])} {m['confusion']}")
    print("  criteria", {a: v["criteria"]["accepted_for_development"] for a, v in crit.items()})
    print("  paired E56-E55", paired["E55-LGBM"])
    print("  spread", {a: (f(v["within_quarter_auc"]), round(v["mean_within_quarter_sd"], 3), v["quarters_with_mixed_decisions"]) for a, v in spread.items()})
    print("  configs", configs_used, "prospective", frozen_status)


if __name__ == "__main__":
    main()
