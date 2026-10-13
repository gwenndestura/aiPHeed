"""E24v2 class B: prospective, blind forecasts from authorized data only (FROZEN_EVALUATION_PROTOCOL.md 5).

Origin O(2026-Q2) = 2026-07-01 00:00 PHT.  Information used:
  * SWS rounds with a VERIFIED publication date before the origin (all 2025 and earlier; the 2026 rounds have no
    verified date and are excluded, which also keeps the 2026-Q1 label out of the threshold);
  * quarterly D labels <= 2026-Q1; Dnow(2026-Q2) = April-May 2026 (authorized Jan-Jun 2026 CPI file);
  * nothing from July 2026 onward is opened (protected).
Targets: 2026-Q3 (k=1), 2026-Q4 (k=2), 2027-Q1 (k=3).  Outcomes are protected and unseen; score only after the
owner authorizes them (runner/score_prospective.py).  Usage: python -B runner/seal_v2.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e23_lib as L  # noqa: E402
import run_e24 as R24  # noqa: E402
import v2lib as V2  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs
ORIGIN_Q = "2026-Q2"
LEADS = (1, 2, 3)


def main():
    R24.check_frozen()
    data = V2.load_all()
    t = qk(ORIGIN_Q)
    origin = L.origin_of(t)
    S = data["V"]["T1"].rename(columns={"v": "S1"})
    tau, n_tau = L.threshold_at(S, data["rounds"], t)
    used_rounds = data["rounds"][data["rounds"]["published"] < origin]
    assert used_rounds["published"].max() < origin and used_rounds["quarter"].map(qk).max() <= qk("2025-Q4")
    assert all((p, t - 1) in data["Dm"] for p in V2.PROVS) and all((p, t) in data["Nm"] for p in V2.PROVS)
    rows, comps, cache = [], [], {}
    VT1 = data["V"]["T1"]
    for k in LEADS:
        tq = qs(t + k)
        assert qk(tq) >= qk("2026-Q3")
        # ---------------- T1
        tr_p, tr_s, pub = V2.t1_training(data, t, k, tau, cache)
        assert tr_p["target_q"].max() <= qk("2025-Q4")          # 2026 labels are not published by the rule
        te = R24.pblock(VT1, pub, pd.DataFrame({"province_code": V2.PROVS, "t": t}), tau, cache)
        sc = {"B1_naive_persistence": te["y_last"].to_numpy(float),
              "B1p_calibrated_persistence": V2.calibrated_persistence(tr_s, te["y_last"].to_numpy())}
        for name, sup in (("FINAL_V2_PCF", False), ("PCF_S_supplementary", True)):
            o = V2.pcf_t1(data, t, k, tau, sup)
            sc[name] = np.array([o[p][0] for p in V2.PROVS])
            for p in V2.PROVS:
                comps.append({"model": name, "lead": k, "target_quarter": tq, "province_code": p,
                              **{a: b for a, b in o[p][1].items() if not isinstance(b, list)}})
        p2, _, _, sel = R24.nested_lgbm(tr_s, tr_p, R24.P_COLS, te, k)
        sc["M2_lgbm_P_E24frozen"] = p2
        for m, v in sc.items():
            for i, p in enumerate(V2.PROVS):
                rows.append({"target": "T1", "lead": k, "origin": origin.date().isoformat(), "feature_quarter": ORIGIN_Q,
                             "target_quarter": tq, "province_code": p, "model": m, "score": float(v[i]),
                             "decision_HIGH": int(v[i] >= 0.5), "threshold": tau})
        # ---------------- T2
        ylast = np.array([float(data["Dm"][(p, t - 1)] > 0) for p in V2.PROVS])
        tr2 = V2.t2_training_long(data, t, k)
        mod = V2.t2_models(data, t, k)
        Vlong = data["Dall"].rename(columns={"D": "v"}).assign(tq=lambda x: x["quarter"].map(qk))
        Vlong = Vlong[Vlong["tq"] <= t - 1]                       # D(2026-Q2) is not known at the origin
        pub2 = lambda q, tt: qk(q) <= tt - 1   # noqa: E731
        grid = pd.DataFrame([(p, tt) for tt in range(qk(V2.LONG_FIRST), t) for p in V2.PROVS],
                            columns=["province_code", "t"])
        c2 = {}
        trl = R24.pairs(grid, Vlong, k)
        trl = trl[trl["target_q"] <= t - 1]
        trl = R24.pblock(Vlong, pub2, trl, 0.0, c2)
        trl["y"] = (trl["v"] > 0).astype(int)
        te2 = R24.pblock(Vlong, pub2, pd.DataFrame({"province_code": V2.PROVS, "t": t}), 0.0, c2)
        sc2 = {"B1_naive_persistence": ylast, "B1p_calibrated_persistence": V2.calibrated_persistence(tr2, ylast),
               "M1_lr_P_1995window": L.fit_lr(trl, R24.P_COLS, te2),
               "M3_pcf_D": np.array([mod["M3_pcf_D"][p][0] for p in V2.PROVS]),
               "FINAL_V2_M4_pcf_D_now": np.array([mod["M4_pcf_D_now"][p][0] for p in V2.PROVS])}
        for m, v in sc2.items():
            for i, p in enumerate(V2.PROVS):
                rows.append({"target": "T2", "lead": k, "origin": origin.date().isoformat(), "feature_quarter": ORIGIN_Q,
                             "target_quarter": tq, "province_code": p, "model": m, "score": float(v[i]),
                             "decision_HIGH": int(v[i] >= 0.5), "threshold": 0.0})
    P = pd.DataFrame(rows)
    if len(sys.argv) > 2 and sys.argv[1] == "--verify":          # recompute only; never writes a new seal
        want = json.loads((Path(sys.argv[2]) / "SEAL_PROSPECTIVE.json").read_text(encoding="utf-8"))["sha256"]
        got = hashlib.sha256(P.to_csv(index=False, lineterminator=chr(10)).encode()).hexdigest()
        print(json.dumps({"seal": str(sys.argv[2]), "expected": want, "recomputed": got, "identical": got == want}))
        return
    sid = "SEAL_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rd = EXP / "runs" / sid
    rd.mkdir(parents=True)
    b = P.to_csv(index=False, lineterminator="\n").encode()
    (rd / "prospective_forecasts.csv").write_bytes(b)
    pd.DataFrame(comps).to_csv(rd / "pcf_components.csv", index=False, lineterminator="\n")
    seal = {"sha256": hashlib.sha256(b).hexdigest(), "rows": len(P), "created_utc":
            datetime.now(timezone.utc).isoformat(timespec="seconds"), "origin": origin.isoformat() + " PHT",
            "targets": [qs(t + k) for k in LEADS], "threshold_T1": tau, "threshold_labels_used": n_tau,
            "sws_rounds_used": used_rounds[["quarter", "H", "published", "definition_A", "source"]].astype(str)
            .to_dict("records"),
            "protocol_sha256": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0],
            "inputs": [{"path": a["path"], "op": a["op"]} for a in guard.ACCESS_LOG],
            "statement": "Made before any 2026-Q3+ outcome was opened; outcomes are protected and unseen. "
                         "Score only with runner/score_prospective.py after the owner authorizes the outcome files."}
    (rd / "SEAL_PROSPECTIVE.json").write_text(json.dumps(seal, indent=1, default=str), encoding="utf-8")
    print(sid, seal["sha256"], "tau", tau)
    print(P.pivot_table(index=["target", "model"], columns=["lead", "province_code"], values="score").round(3).to_string())


if __name__ == "__main__":
    main()
