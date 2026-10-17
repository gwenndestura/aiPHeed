"""E52 single run under the frozen PROTOCOL.md: the E52-PS candidate (E46 I7 price component, committed predictions)
against every Chapter 1 Objective 4 baseline on identical PS rows. Runs inside the E32 data guard (via E51's script);
writes confined to E52.

    backend/venv/Scripts/python.exe -B runner/e52_baselines.py   -> runs/<UTC stamp>/{rows.csv, results.json}
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E52 = Path(__file__).resolve().parents[1]
EXP = E52.parent
sys.path.insert(0, str(EXP / "E51_Target_Definition" / "runner"))
import e51_compare as V  # noqa: E402  (installs the E32 guard; D-1 threshold guard)

E, np, pd, qk, qs, PROVS, L6 = V.E, V.np, V.pd, V.qk, V.qs, V.PROVS, V.L6
E.L7.L6.guard32.EXP = E52
RUN7 = EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z" / "predictions_i7.csv"
L36 = E.L6                      # E36 library (lr_predict, lgbm_predict, GOV, NLP, COMB)


def verify() -> str:
    want = (E52 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E52 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def main():
    proto = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E52 / "runs" / stamp
    out.mkdir(parents=True)
    cpi = pd.read_csv(EXP / "E51_Target_Definition" / "data" / "labels_cpi.csv", dtype={"province_code": str})
    pcpi = pd.read_csv(EXP / "E51_Target_Definition" / "data" / "persistence_cpi.csv", dtype={"province_code": str})
    lab = {(p, int(q)): int(y) for p, q, y in zip(cpi["province_code"], cpi["q"], cpi["PS"])}
    pers = {(int(t), p): (np.nan if pd.isna(v) else float(v)) for t, p, v in zip(pcpi["t"], pcpi["province_code"], pcpi["PS_last"])}
    dl = V.DataLabel(lab, pers)
    Pr, info = E.walk_forward(dl)
    g = Pr[Pr["arm"] == "E38-LGBM"]
    P7 = pd.read_csv(RUN7, dtype={"province_code": str})
    P7["target"] = (P7["t"] + 2).map(qs)
    cand = P7[P7["I7_p_price"].notna()].set_index(["target", "province_code"])["I7_p_price"]
    rows = []
    for t_s, gg in g.groupby("t"):
        t = qk(t_s)
        tr, te = dl.train(t, 2), dl.test(t, 2)
        preds = {"B2_LR_GOV": L36.lr_predict(tr, te, L36.GOV), "B3_LGBM_GOV": L36.lgbm_predict(tr, te, L36.GOV, "G1"),
                 "B4_LR_NLP": L36.lr_predict(tr, te, L36.NLP), "B5_LGBM_NLP": L36.lgbm_predict(tr, te, L36.NLP, "G1"),
                 "B6_LR_COMB": L36.lr_predict(tr, te, L36.COMB)}
        clim = float(tr["y"].mean())
        yl = te.set_index("province_code")["y_last"]
        for r in gg.itertuples():
            key = (r.target_quarter, r.province_code)
            if key not in cand.index:
                continue
            pv = yl.loc[r.province_code]
            row = {"target": r.target_quarter, "t": r.t, "province_code": r.province_code, "y": int(r.y),
                   "E52PS_p": float(cand.loc[key]), "B1_PERSIST_p": clim if pv != pv else float(pv),
                   "B7_E38PROC_p": r.p, "B7_E38PROC_thr": r.threshold, "CLIM_p": clim, "HIGH_p": 1.0, "LOW_p": 0.0}
            for k, v in preds.items():
                row[f"{k}_p"] = float(v[r.province_code])
            rows.append(row)
    R = pd.DataFrame(rows)
    arms = ["E52PS", "B1_PERSIST", "B2_LR_GOV", "B3_LGBM_GOV", "B4_LR_NLP", "B5_LGBM_NLP", "B6_LR_COMB", "B7_E38PROC",
            "CLIM", "HIGH", "LOW"]
    for a in arms:
        thr = R["B7_E38PROC_thr"] if a == "B7_E38PROC" else 0.5
        R[f"{a}_yhat"] = (R[f"{a}_p"] >= thr).astype(int)
    M = V.block(R, arms)
    c = M["E52PS"]
    base = [a for a in arms if a != "E52PS"]
    loqo = {q: float((R[R["target"] != q]["E52PS_yhat"] == R[R["target"] != q]["y"]).mean()) for q in R["target"].unique()}
    crit = {"A1_accuracy_ge_0.75": c["accuracy"] >= 0.75,
            "A2_balanced_and_recalls": (c["balanced_accuracy"] or 0) >= 0.70 and (c["recall_HIGH"] or 0) >= 0.60
            and (c["recall_LOW"] or 0) >= 0.60,
            "A3_brier_below_every_baseline": all(c["brier"] < M[b]["brier"] for b in base),
            "A4_balanced_above_every_baseline": all((c["balanced_accuracy"] or 0) > (M[b]["balanced_accuracy"] or 0) for b in base),
            "A5_min_leave_one_quarter_out_ge_0.70": min(loqo.values()) >= 0.70}
    crit["accepted_for_development"] = all(crit.values())
    res = {"protocol_sha256": proto, "run_utc": stamp,
           "evidence_status": "Confirmation against the Objective 4 baselines; candidate seen in E51 and designed on these "
                              "quarters (PROTOCOL 0); not independent validation.",
           "rows": int(len(R)), "independent_quarters": int(R["target"].nunique()), "HIGH": int(R["y"].sum()),
           "quarters": sorted(R["target"].unique().tolist()), "metrics": M, "leave_one_quarter_out": loqo,
           "calibration_in_the_large": float(R["y"].mean() - R["E52PS_p"].mean()), "criteria": crit}
    R.to_csv(out / "rows.csv", index=False)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    print(stamp, "rows", res["rows"], "quarters", res["independent_quarters"], "HIGH", res["HIGH"])
    f = lambda v: None if v is None else round(v, 3)  # noqa: E731
    for a in arms:
        m = M[a]
        print(f"  {a:12s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal {f(m['balanced_accuracy'])} "
              f"recH {f(m['recall_HIGH'])} recL {f(m['recall_LOW'])} prec {f(m['precision_HIGH'])} F1 {f(m['f1_HIGH'])} "
              f"brier {m['brier']:.3f} auc {f(m['auc'])} {m['confusion']}")
    print("  LOQO min", round(min(loqo.values()), 3), "CITL", round(res["calibration_in_the_large"], 3))
    print("  criteria", crit)


if __name__ == "__main__":
    main()
