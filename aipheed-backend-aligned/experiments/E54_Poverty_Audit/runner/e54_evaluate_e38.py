"""E54 comparison C3 (E38 label, production-default procedure) under the frozen PROTOCOL.md.

Runs in its own process: importing e38_lib installs the E32 data guard (production data trees unreadable, writes
confined to the experiment), which is redirected here to E54.

    backend/venv/Scripts/python.exe -B runner/e54_evaluate_e38.py
      -> runs/c3_<UTC stamp>/{predictions.csv, results.json}
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e54_lib as V  # noqa: E402

E38 = V.E54.parent / "E38_Lead2_Diagnosis_Tuning"
sys.path.insert(0, str(E38 / "runner"))
import e38_lib as L  # noqa: E402
import e38_evaluate as EE  # noqa: E402

L.L7.L6.guard32.EXP = V.E54                 # writes confined to E54 (and the OS temp directory)
np, pd = L.np, L.pd
COMMITTED = E38 / "runs" / "20261015T033922Z" / "predictions.csv"
REFS = EE.BASELINES + EE.DIAG
BASE_SETS = dict(L.FEATURE_SETS)


class PData(L.Data):
    """E38 data with the arm's poverty columns attached to every training and test frame (by origin quarter t)."""
    arm = "R"

    def train(self, t, k=L.K):
        tr = super().train(t, k)
        return tr if tr.empty else V.add(tr, self.arm, "t")

    def test(self, t, k=L.K):
        return V.add(super().test(t, k), self.arm, "t")


def run_arm(d: PData, arm: str):
    d.arm = arm
    L.FEATURE_SETS = {fs: cols + V.cols(arm) for fs, cols in BASE_SETS.items()}
    try:
        P, info = L.walk_forward(d)
    finally:
        L.FEATURE_SETS = dict(BASE_SETS)
    return P[P["arm"] == "E38-LGBM"].assign(arm=arm), info


def m_of(g: pd.DataFrame) -> dict:
    m = EE.metrics(g)
    m["recall_HIGH"], m["recall_LOW"] = m["recall"], m["specificity"]
    return m


def main():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    proto = V.sha(V.E54 / "PROTOCOL.md")
    if proto != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    inputs = V.verify_inputs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = PData()
    rows, paths = [], {}
    for a in V.ARMS:
        P, info = run_arm(d, a)
        rows.append(P)
        paths[a] = {q: {"chosen": v["chosen"], "threshold": v["threshold"]} for q, v in info["path"].items()}
        print(a, {q: (v["chosen"], v["threshold"]) for q, v in paths[a].items()}, flush=True)
    Pr = pd.concat(rows, ignore_index=True)
    C = pd.read_csv(COMMITTED, dtype={"province_code": str})
    ce = C[C["arm"] == "E38-LGBM"].merge(Pr[Pr["arm"] == "R"], on=["t", "province_code"], suffixes=("_c", "_r"))
    if len(ce) != 55 or np.max(np.abs(ce["p_c"] - ce["p_r"])) > 1e-9 or (ce["threshold_c"] != ce["threshold_r"]).any():
        raise SystemExit(f"C3 stopped: R does not reproduce the committed E38-LGBM ({len(ce)} rows)")
    out = V.E54 / "runs" / f"c3_{stamp}"
    out.mkdir(parents=True)
    Pr = Pr.sort_values(["arm", "target_quarter", "province_code"])
    (out / "predictions.csv").write_bytes(Pr.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode())

    met = {a: m_of(Pr[Pr["arm"] == a]) for a in V.ARMS}
    for r in REFS:
        met[r] = m_of(C[C["arm"] == r])
    W = Pr.pivot_table(index=["target_quarter", "province_code"], columns="arm", values="p").reset_index()
    W.columns = [c if c in ("target_quarter", "province_code") else f"{c}_p" for c in W.columns]
    W = W.merge(Pr[Pr["arm"] == "R"][["target_quarter", "province_code", "y"]], on=["target_quarter", "province_code"])
    dec, pbs = {}, {}
    for a in V.ARMS[1:]:
        pbs[a] = V.paired_brier(W, a, "R", "target_quarter")
        dec[a] = V.decide(met[a], met["R"], pbs[a], bool(np.max(np.abs(W[f"{a}_p"] - W["R_p"])) < 1e-12))
    res = {"protocol_sha256": proto, "inputs_sha256": inputs, "run_utc": stamp,
           "evidence_status": "Development evidence on quarters already examined in E37/E38; not independent validation.",
           "rows": int(len(W)), "HIGH": int(W["y"].sum()), "quarters": sorted(W["target_quarter"].unique().tolist()),
           "reproduced_committed_E38": True, "metrics": met, "paths": paths, "paired_brier_vs_R": pbs, "decision": dec,
           "poverty_vs_FE": {a: V.paired_brier(W, a, "FE", "target_quarter") for a in V.POVERTY_ARMS
                             if dec[a]["status"] == "IMPROVES"}}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    f3 = lambda v: None if v is None else round(v, 3)  # noqa: E731
    print(stamp, "C3 rows", res["rows"], "HIGH", res["HIGH"])
    for a in V.ARMS + REFS:
        m = met[a]
        pb = pbs.get(a)
        print(f"  {a:16s} {m['correct']}/{m['n']} acc {m['accuracy']:.3f} bal {f3(m['balanced_accuracy'])} "
              f"recH {f3(m['recall_HIGH'])} recL {f3(m['recall_LOW'])} brier {m['brier']:.4f}"
              + (f" dBrier {pb['diff']:+.4f} {[round(v, 4) for v in pb['ci95']]} {dec[a]['status']}" if pb else ""))


if __name__ == "__main__":
    main()
