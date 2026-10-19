"""E59 audit step 1: independent reproduction of the E57 and E58 results.

Re-derives every reported figure from the SEALED prediction files and the T43 labels, using metric code written for
this audit (not the E57/E58 scorers), and re-executes the frozen E56 procedure at all 10 rolling origins to confirm the
sealed probabilities. Nothing in E55-E58 is modified.

    backend/venv/Scripts/python.exe -B runner/a1_reproduce.py  -> out/reproduction.json, E58_QUARTERLY_PREDICTIONS.csv
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A = Path(__file__).resolve().parents[1]
EXP = A.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
S57 = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
S58 = EXP / "E58_Rising_Stress_Early_Warning" / "sealed" / "predictions.csv"
EV58 = EXP / "E58_Rising_Stress_Early_Warning" / "data" / "events.csv"
REPORTED = {"E56_accuracy": 0.72, "E56_onsets_detected": 3, "EW_accuracy": 0.78, "EW_onsets_detected": 7,
            "onsets": 10, "rows": 50, "PROJ_onsets_detected": 7}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def conf(y, yhat):
    y, yhat = np.asarray(y, int), np.asarray(yhat, int)
    return {"TP": int(((yhat == 1) & (y == 1)).sum()), "TN": int(((yhat == 0) & (y == 0)).sum()),
            "FP": int(((yhat == 1) & (y == 0)).sum()), "FN": int(((yhat == 0) & (y == 1)).sum())}


def main():
    out = {"sealed_files": {}}
    for p in (S57, S58):
        want = (p.parent / "predictions.csv.sha256").read_text().split()[0]
        out["sealed_files"][str(p.relative_to(EXP))] = {"sha256": sha(p), "matches_seal": sha(p) == want}
    s57 = pd.read_csv(S57, dtype={"province_code": str})
    s58 = pd.read_csv(S58, dtype={"province_code": str})
    d, X, B = E.load()
    # labels recomputed from the source files (not from the E57/E58 row files)
    Y = F.t43_labels(d)
    lab = {(p, int(q)): int(v) for p, q, v in zip(Y["province_code"], Y["q"], Y["T43"]) if v == v}
    last = {t: F.t43_last(d, t) for t in sorted(s57["t"].unique())}
    R = s58[["t", "origin_quarter", "target", "province_code", "province", "E56_p", "E56_p_price", "E56_p_hunger",
             "BPROJ_p", "PERSIST_p", "PERSIST_from", "H_last_known"]].copy()
    R["y_T43"] = [lab[(p, t + 2)] for p, t in zip(R["province_code"], R["t"])]
    R["PS_target"] = [int(Y[(Y["province_code"] == p) & (Y["q"] == t + 2)]["PS"].iloc[0]) for p, t in zip(R["province_code"], R["t"])]
    R["latest_known_T43"] = [last[t][p][0] for t, p in zip(R["t"], R["province_code"])]
    R["onset"] = ((R["y_T43"] == 1) & (R["latest_known_T43"] == 0)).astype(int)
    R["E56_pred"] = (R["E56_p"] >= 0.5).astype(int)
    R["EW_pred"] = (R["E56_p_price"] >= 0.5).astype(int)
    R["EW_level"] = np.where(R["E56_p"] >= 0.5, "ALERT", np.where(R["E56_p_price"] >= 0.5, "EMERGING", "NONE"))
    R["PROJ_pred"] = (R["BPROJ_p"] >= 0.5).astype(int)
    R["PERSIST_pred"] = R["PERSIST_p"].fillna(0).astype(int)
    # consistency checks against the earlier records
    ev = pd.read_csv(EV58, dtype={"province_code": str}).set_index(["t", "province_code"])
    chk = {"E57_E58_sealed_E56_equal": float(np.max(np.abs(s57.set_index(["t", "province_code"])["E56_p"]
                                                         - s58.set_index(["t", "province_code"])["E56_p"]))),
           "onset_labels_equal_E58_events": bool(all(int(ev.loc[(t, p), "ONSET"]) == o for t, p, o in
                                                   zip(R["t"], R["province_code"], R["onset"]))),
           "T43_equals_PS_on_all_rows": bool((R["y_T43"] == R["PS_target"]).all())}
    # re-execute the frozen E56 procedure at every origin
    space = G.search_space()
    diffs, cfg_match = [], []
    for t, g in s57.groupby("t"):
        fx = G.tuned_forecast(d, X, B, int(t), space)
        sp = g.set_index("province_code")["E56_p"]
        diffs.append(float(np.max(np.abs(np.array([sp[p] for p in L.PROVS]) - fx["p"]))))
        cfg_match.append(int(fx["cfg"]["id"]) == int(g["E56_config"].iloc[0]))
    chk["E56_reexecution_max_abs_diff"] = max(diffs)
    chk["E56_reexecution_configs_match"] = all(cfg_match)
    rep = {}
    for k, col in (("E56", "E56_pred"), ("EW", "EW_pred"), ("PROJ", "PROJ_pred"), ("PERSIST", "PERSIST_pred")):
        c = conf(R["y_T43"], R[col])
        rep[k] = {"accuracy": (c["TP"] + c["TN"]) / len(R), **c,
                  "onsets_detected": int(((R["onset"] == 1) & (R[col] == 1)).sum())}
    only_q = sorted(R[R["E56_pred"] != R["EW_pred"]]["target"].unique().tolist())
    out.update({"checks": chk, "recomputed": rep, "onsets": int(R["onset"].sum()), "rows": int(len(R)),
                "quarters_where_EW_differs_from_E56": only_q,
                "reported": REPORTED,
                "discrepancies": [k for k, v in {
                    "E56_accuracy": abs(rep["E56"]["accuracy"] - 0.72) > 1e-9,
                    "E56_onsets": rep["E56"]["onsets_detected"] != 3,
                    "EW_accuracy": abs(rep["EW"]["accuracy"] - 0.78) > 1e-9,
                    "EW_onsets": rep["EW"]["onsets_detected"] != 7,
                    "PROJ_onsets": rep["PROJ"]["onsets_detected"] != 7}.items() if v]})
    (A / "out").mkdir(exist_ok=True)
    (A / "out" / "reproduction.json").write_text(json.dumps(out, indent=1, default=float))
    cols = ["origin_quarter", "target", "province", "province_code", "y_T43", "PS_target", "latest_known_T43", "onset",
            "E56_p", "E56_p_price", "E56_p_hunger", "E56_pred", "EW_level", "EW_pred", "BPROJ_p", "PROJ_pred",
            "PERSIST_from", "PERSIST_pred", "H_last_known"]
    R[cols].sort_values(["target", "province"]).to_csv(A / "E58_QUARTERLY_PREDICTIONS.csv", index=False, float_format="%.6f")
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
