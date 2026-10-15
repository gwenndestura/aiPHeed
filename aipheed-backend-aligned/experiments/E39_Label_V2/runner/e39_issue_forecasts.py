"""E39 forecast issuance (NOT an evaluation): the forecasts at the latest origin O(2026-Q3) = 2026-10-01, i.e.
2026-Q4 (lead 1) and 2027-Q1 (lead 2, the dashboard target), for Label A, Targets B and C. Writes
frozen/E39_FORECASTS_2026Q4_2027Q1.json (+ .sha256). Refuses to overwrite.

DEVIATIONS.md D-1: the evaluation runner's lead-2 walk-forward stopped at origin 2026-07-01, so it issued no
2027-Q1 forecast. This script reruns the same deterministic walk-forward up to the 2026-10-01 origin and ASSERTS
that every prediction the evaluation run already made is reproduced exactly; it adds only the missing forecast-only
rows. No score is computed here.

    <backend venv python> -B runner/e39_issue_forecasts.py runs/eval_<stamp>
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
import e39_lib as L  # noqa: E402

np, pd = L.np, L.pd
OP_T = L.qk("2026-Q3")


def walk_to(d, kind, k):
    """The evaluation walk-forward with the last origin moved to O(2026-Q3) (the only change)."""
    saved = L.LAST_OBS
    try:
        L.LAST_OBS = OP_T - 1 + k             # makes last_t = OP_T inside walk_forward
        P, meta = L.walk_forward(d, kind, k)
    finally:
        L.LAST_OBS = saved
    # statuses must use the real last observed quarter
    obs_last = saved
    for q, m in meta.items():
        if L.qk(q) > obs_last and m["status"] == "Scored":
            m["status"] = "No outcome yet"
    P.loc[P["target_quarter"].map(L.qk) > obs_last, "status"] = P.loc[
        P["target_quarter"].map(L.qk) > obs_last, "status"].replace("Scored", "No outcome yet")
    return P, meta


def main(run_dir: str):
    run = Path(run_dir)
    ev = pd.read_csv(run / "predictions.csv", dtype={"province_code": str})
    d = L.Data()
    out = {"issued_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "origin": "2026-10-01",
           "information_cutoff": "2026-10-01T00:00:00+08:00 (exclusive)", "name": "Food Price Pressure (exploratory)",
           "note": json.loads((L.E39 / "label_v2_spec.json").read_text())["framing"], "evaluation_run": run.name,
           "forecasts": {}}
    for k in (1, 2):
        for kind in L.TARGETS:
            P, meta = walk_to(d, kind, k)
            old = ev[(ev.target == kind) & (ev.lead == k) & ev.pred.notna()]
            j = old.merge(P[P.pred.notna()], on=["target_quarter", "province_code", "arm"], suffixes=("_ev", "_new"))
            assert len(j) == len(old), (kind, k, "rows lost")
            assert np.allclose(j["pred_ev"].astype(float), j["pred_new"].astype(float), atol=1e-12), (kind, k)
            q = L.qs(OP_T + k)
            g = P[(P.target_quarter == q)]
            m = g[g.arm == "model"]
            rec = {"target_quarter": q, "lead": k, "status": meta[q]["status"], "meta": meta[q], "provinces": {}}
            ranks, tied = L.avg_rank(dict(zip(m.province_code, m.pred))) if kind == "B" and m.pred.notna().all() else ({}, {})
            for p in L.PROVS:
                r = m[m.province_code == p].iloc[0].to_dict()
                rec["provinces"][p] = {
                    "province": L.NAMES[p], "pred": None if pd.isna(r["pred"]) else float(r["pred"]),
                    **({"raw": float(r["raw"]), "calibration": r["calibration"]} if kind == "A" and not pd.isna(r.get("pred")) else {}),
                    **({"interval": None if pd.isna(r.get("lo")) else [float(r["lo"]), float(r["hi"])]} if kind != "A" else {}),
                    **({"rank": ranks.get(p), "tied": bool(tied.get(p, False))} if kind == "B" else {}),
                    "baselines": {a: float(v) for a, v in zip(g[(g.province_code == p) & (g.arm != "model")]["arm"],
                                                              g[(g.province_code == p) & (g.arm != "model")]["pred"])}}
            out["forecasts"][f"{kind}_lead{k}"] = rec
    path = L.E39 / "frozen" / "E39_FORECASTS_2026Q4_2027Q1.json"
    if path.exists():
        raise SystemExit("refusing to overwrite issued forecasts")
    b = json.dumps(L.C.clean(out), indent=1, sort_keys=True, allow_nan=False).encode()
    path.write_bytes(b)
    h = hashlib.sha256(b).hexdigest()
    path.with_suffix(".sha256").write_bytes(f"{h}  {path.name}\n".encode())
    print(path.name, h[:16])
    for key, rec in out["forecasts"].items():
        print(key, rec["target_quarter"], rec["status"], {v["province"]: (None if v["pred"] is None else round(v["pred"], 3))
                                                         for v in rec["provinces"].values()})


if __name__ == "__main__":
    main(sys.argv[1])
