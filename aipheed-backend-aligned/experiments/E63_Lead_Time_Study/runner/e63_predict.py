"""E63 step 1 (PROTOCOL sections 3-5): run the E56-TUNED procedure at every eligible origin of leads 1-3, check the
lead-2 forecasts against the sealed E57 file, and SEAL all forecasts (with the as-of baselines) before any label is read.

    backend/venv/Scripts/python.exe -B runner/e63_predict.py  -> sealed/predictions.csv (+ .sha256)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e63_lib as H  # noqa: E402

F, L, np, pd = H.F, H.L, H.np, H.pd
SEALED = H.E63 / "sealed" / "predictions.csv"
ORDER = [2, 1, 3]                       # lead 2 first: the reproduction check gates everything else


def verify_protocol() -> str:
    want = (H.E63 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((H.E63 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def origins_for(h: int) -> list[int]:
    el = json.loads((H.E63 / "out" / "eligibility.json").read_text())
    return [L.qi(q) for q in el[f"lead{h}"]["origins"]]


def main():
    proto = verify_protocol()
    if SEALED.exists():
        raise SystemExit("already sealed; predictions are written once")
    raw = H.load_raw()
    d = raw[0]
    space = H.G.search_space()
    base = {}
    rows = []
    for h in ORDER:
        _, X, B = H.inputs_h(raw, h)
        for t in origins_for(h):
            t0 = time.time()
            fx = H.tuned_forecast_h(d, X, B, t, h, space)
            assert fx is not None, (h, L.qs(t))
            if t not in base:
                kl = H.known_labels(d, t)
                base[t] = {"last": F.t43_last(d, t), "kl": kl, "maj": float(kl["T43"].mean() >= 0.5),
                           "clim": float(kl["T43"].mean())}
            b = base[t]
            for i, p in enumerate(L.PROVS):
                kp = b["kl"][b["kl"]["province_code"] == p]
                last = b["last"][p]
                rows.append({"lead": h, "origin_quarter": L.qs(t), "issue_date": str(L.origin(t).date()),
                             "target": L.qs(t + h), "t": t, "province_code": p, "province": L.NAMES[p],
                             "E56_p": float(fx["p"][i]), "E56_p_price": float(fx["p_price"][i]),
                             "E56_p_hunger": float(fx["p_hunger"]), "E56_H_hat": float(fx["H_hat"]),
                             "E56_config": int(fx["cfg"]["id"]), "E56_pov_in_config": fx["cfg"]["pov"] == "AS",
                             "n_train_q": fx["n_train_q"], "n_train_rows": fx["n_train_rows"],
                             "PERSIST_p": last[0], "PERSIST_from": None if last[1] is None else L.qs(last[1]),
                             "MAJORITY_p": b["maj"], "CLIM_p": b["clim"],
                             "PROVCLIM_p": float(kp["T43"].mean()) if len(kp) else b["clim"],
                             "known_label_quarters": int(b["kl"]["q"].nunique())})
            print(f"lead {h} origin {L.qs(t)} -> {L.qs(t + h)} config {fx['cfg']['id']} ({time.time() - t0:.0f}s)",
                  flush=True)
        if h == 2:                                       # PROTOCOL section 4 step 2
            S = pd.DataFrame([r for r in rows if r["lead"] == 2])
            R = pd.read_csv(H.E57_SEALED, dtype={"province_code": str})
            m = S.merge(R, on=["origin_quarter", "province_code"], suffixes=("", "_e57"))
            assert len(m) == 50 == len(S), (len(m), len(S))
            diff = max(float(np.max(np.abs(m[c] - m[f"{c}_e57"]))) for c in ("E56_p", "E56_p_price", "E56_p_hunger"))
            cfg_eq = bool((m["E56_config"] == m["E56_config_e57"]).all())
            print("lead-2 reproduction vs sealed E57: max abs diff", diff, "configs equal", cfg_eq, flush=True)
            if diff > 1e-9 or not cfg_eq:
                raise SystemExit("lead-2 reproduction FAILED: nothing written (PROTOCOL section 4)")
            repro = {"max_abs_diff": diff, "configs_equal": cfg_eq, "rows": int(len(m))}
    out = pd.DataFrame(rows).sort_values(["lead", "t", "province_code"]).reset_index(drop=True)
    SEALED.parent.mkdir(exist_ok=True)
    out.to_csv(SEALED, index=False, float_format="%.12g")
    sha = hashlib.sha256(SEALED.read_bytes()).hexdigest()
    (SEALED.parent / "predictions.csv.sha256").write_text(sha + "  predictions.csv\n")
    (H.E63 / "out" / "predict_meta.json").write_text(json.dumps(
        {"protocol_sha256": proto, "sealed_sha256": sha, "rows": int(len(out)),
         "rows_per_lead": out.groupby("lead").size().to_dict(), "lead2_reproduction_vs_E57": repro,
         "sealed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=1, default=int))
    print("sealed", len(out), "forecasts sha256", sha)


if __name__ == "__main__":
    main()
