"""E24v2 second prospective seal (PROTOCOL_AMENDMENTS.md A3): PCF_NOW for T1, same origin (2026-07-01) and the same
authorized information set as SEAL_20261013T164218Z.  Usage: python -B runner/seal_v2_a3.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import pandas as pd  # noqa: E402

import e23_lib as L  # noqa: E402
import run_e24 as R24  # noqa: E402
import v2lib as V2  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs


def main():
    R24.check_frozen()
    am = (EXP / "runner" / "AMENDMENTS_SHA256.txt").read_text(encoding="utf-8").split()
    assert hashlib.sha256((EXP / am[1]).read_bytes()).hexdigest() == am[0], "amendments file changed"
    data = V2.load_all()
    t = qk("2026-Q2")
    origin = L.origin_of(t)
    S = data["V"]["T1"].rename(columns={"v": "S1"})
    tau, n_tau = L.threshold_at(S, data["rounds"], t)
    rows, comps = [], []
    for k in (1, 2, 3):
        o = V2.pcf_t1(data, t, k, tau, use_now=True)
        for p in V2.PROVS:
            rows.append({"target": "T1", "lead": k, "origin": origin.date().isoformat(), "feature_quarter": "2026-Q2",
                         "target_quarter": qs(t + k), "province_code": p, "model": "PCF_NOW_A3", "score": o[p][0],
                         "decision_HIGH": int(o[p][0] >= 0.5), "threshold": tau})
            comps.append({"model": "PCF_NOW_A3", "lead": k, "target_quarter": qs(t + k), "province_code": p,
                          **{a: b for a, b in o[p][1].items() if not isinstance(b, list)}})
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
            "targets": [qs(t + k) for k in (1, 2, 3)], "threshold_T1": tau, "threshold_labels_used": n_tau,
            "amendment": "A3", "amendments_sha256": am[0],
            "protocol_sha256": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0],
            "statement": "Made before any 2026-Q3+ outcome was opened; same information set as the first seal."}
    (rd / "SEAL_PROSPECTIVE.json").write_text(json.dumps(seal, indent=1, default=str), encoding="utf-8")
    print(sid, seal["sha256"])
    print(P.pivot_table(index="lead", columns="province_code", values="score").round(3).to_string())


if __name__ == "__main__":
    main()
