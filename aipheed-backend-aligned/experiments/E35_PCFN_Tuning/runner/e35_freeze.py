"""Freeze the E35 prospective research arm (PROTOCOL.md section 10): the configuration the nested rule selects at the
operational origin O(2026-Q3) = 2026-10-01 (inner dates posted before that origin), for 2026-Q4 (lead 1) and 2027-Q1
(lead 2). Research arm only: not served, whatever the verdict. The E32 frozen record is read, never written.

    python -B runner/e35_freeze.py runs/<primary run>   -> frozen/E35_PROSPECTIVE.json (+ .sha256); never overwritten
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import e35_common as E
import e35_grid as G
import e35_tune as TU

C, L = E.C, E.L
FROZEN = E.E35 / "frozen"
E32_FROZEN = E.E32 / "frozen" / "E32_PROSPECTIVE.json"


def main(run_dir: str) -> int:
    out_f = FROZEN / "E35_PROSPECTIVE.json"
    if out_f.exists():
        raise SystemExit("already frozen; the record is never overwritten")
    run = (E.E35 / run_dir).resolve() if not Path(run_dir).is_absolute() else Path(run_dir)
    res = json.loads((run / "results.json").read_text(encoding="utf-8"))
    e32 = json.loads(E32_FROZEN.read_text(encoding="utf-8"))
    d = L.Data()
    t = TU.OPERATIONAL_T
    rec = {"record": "E35 prospective research arm: nested-selected E32-PCFN configuration; NOT served",
           "verdict_on_development_dates": res["acceptance"]["verdict"],
           "protocol_sha256": res["protocol_sha256"], "dataset_sha256": E.dataset_manifest(),
           "source_run": run.name, "source_results_sha256": E.sha(run / "results.json"),
           "e32_frozen_record": {"path": "E32_New_Model/frozen/E32_PROSPECTIVE.json", "sha256": E.sha(E32_FROZEN)},
           "origin": str(L.origin(t).date()), "information_cutoff": "2026-09-30T23:59:59+08:00", "leads": {}}
    for k in (1, 2):
        sel = res["prospective_selection"][str(k)]
        cfg = TU.CFG[sel["selected"]]
        p_now = G.probs(G.components(d, t, k), cfg)
        p_def = G.probs(G.components(d, t, k), G.DEFAULT_CFG)
        frozen_pcfn = e32["leads"][str(k)]["arms_p_high"]["E32-PCFN"]
        assert all(abs(p_def[p] - frozen_pcfn[p]) < 1e-12 for p in C.PROVS), "default != E32 frozen PCFN"
        assert all(abs(p_now[p] - sel["p_high"][p]) < 1e-12 for p in C.PROVS), "recompute != run"
        rec["leads"][str(k)] = {"target_quarter": C.qs(t + k), "tau": d.tau(t), "inner_dates": sel["inner_dates"],
                                "selected_config": {"id": cfg.id, "lambda": cfg.lam, "D_set": list(G.D_SETS[cfg.dset]),
                                                    "c": cfg.c},
                                "equals_E32_default": cfg.id == G.DEFAULT_CFG.id,
                                "p_high": {p: p_now[p] for p in C.PROVS},
                                "decision_at_0.5": {p: ("HIGH" if p_now[p] >= 0.5 else "LOW") for p in C.PROVS},
                                "E32_PCFN_frozen_p_high": {p: frozen_pcfn[p] for p in C.PROVS}}
    body = json.dumps(C.clean(rec), indent=1).encode("utf-8")
    FROZEN.mkdir(exist_ok=True)
    out_f.write_bytes(body)
    h = hashlib.sha256(body).hexdigest()
    (FROZEN / "E35_PROSPECTIVE.sha256").write_bytes(f"{h}  E35_PROSPECTIVE.json\n".encode())
    print(h)
    for k, b in rec["leads"].items():
        print(b["target_quarter"], b["selected_config"]["id"],
              {C.NAMES[p][:3]: (round(b["p_high"][p], 3), round(b["E32_PCFN_frozen_p_high"][p], 3)) for p in C.PROVS})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
