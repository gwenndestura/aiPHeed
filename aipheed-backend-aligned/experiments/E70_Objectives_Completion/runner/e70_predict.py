"""E70 step 1 (PROTOCOL sections 4, 8): compute and SEAL every E70 forecast before any label is read.

    set AIPHEED_EXP=<clean export>\\aipheed-backend-aligned\\experiments
    python -B runner/e70_predict.py main          -> sealed/predictions.csv  (R0, A1, A2, S0; leads 1-3)
                                                   + sealed/prospective.csv (2026-Q4 / 2027-Q1, no outcome exists)
    python -B runner/e70_predict.py ablation      -> sealed/ablations.csv    (ABL-g, ONLY-g; lead 2)
    python -B runner/e70_predict.py main --out DIR   (reproduction: write into DIR, never over the seal)

R0 must equal the sealed E63 forecasts within 1e-9 (configurations equal) or nothing is written.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e70_lib as X  # noqa: E402

H, L, np, pd = X.H, X.L, X.np, X.pd
ORDER = [2, 1, 3]


def verify_protocol() -> str:
    want = (X.E70 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((X.E70 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def write(df: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format="%.12g", lineterminator="\n")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (path.parent / f"{path.name}.sha256").write_text(f"{sha}  {path.name}\n")
    return sha


def base_row(h, t, i, p):
    return {"lead": h, "origin_quarter": L.qs(t), "issue_date": str(L.origin(t).date()), "target": L.qs(t + h),
            "t": t, "province_code": p, "province": L.NAMES[p]}


def run_main(out_dir: Path, n_jobs: int):
    raw = H.load_raw()
    d = raw[0]
    space = H.G.search_space()
    rows, prows, meta = [], [], {}
    for h in ORDER:
        _, Xf, B = H.inputs_h(raw, h)
        hist = []
        origins = X.eligible_origins(h)
        for t in origins + X.PROSPECTIVE.get(h, []):
            t0 = time.time()
            r = X.main_arms(d, Xf, B, t, h, space, hist, n_jobs)
            assert r is not None, (h, L.qs(t))
            for i, p in enumerate(L.PROVS):
                row = base_row(h, t, i, p) | {"p_hunger": r["p_hunger"], "H_hat": r["H_hat"],
                                              "n_train_q": r["n_train_q"], "n_train_rows": r["n_train_rows"]}
                for a in X.MAIN_ARMS:
                    row[f"{a}_p"] = float(r[a]["p"][i])
                    row[f"{a}_p_price"] = float(r[a]["p_price"][i])
                    row[f"{a}_cfg"] = r[a]["cfg"]
                row["A2_b"], row["A2_n_oof"] = r["A2"]["b"], r["A2"]["n_oof"]
                (rows if t in origins else prows).append(row)
            print(f"lead {h} origin {L.qs(t)} -> {L.qs(t + h)} R0 cfg {r['R0']['cfg']} A1 cfg {r['A1']['cfg']} "
                  f"A2 b {r['A2']['b']:.3f} S0 {r['S0']['cfg']} ({time.time() - t0:.0f}s)", flush=True)
    P = pd.DataFrame(rows).sort_values(["lead", "t", "province_code"]).reset_index(drop=True)
    S = pd.read_csv(H.E63 / "sealed" / "predictions.csv", dtype={"province_code": str})
    m = P.merge(S, on=["lead", "origin_quarter", "province_code"], suffixes=("", "_e63"))
    assert len(m) == len(P) == len(S) == 155, (len(m), len(P), len(S))
    diff = float(np.max(np.abs(m["R0_p"] - m["E56_p"])))
    cfg_eq = bool((m["R0_cfg"].astype(int) == m["E56_config"].astype(int)).all())
    print("R0 vs sealed E63: max abs diff", diff, "configs equal", cfg_eq, flush=True)
    if diff > 1e-9 or not cfg_eq:
        raise SystemExit("R0 reproduction FAILED: nothing written (PROTOCOL section 4)")
    meta["R0_reproduction_vs_E63"] = {"max_abs_diff": diff, "configs_equal": cfg_eq, "rows": int(len(m))}
    meta["predictions_sha256"] = write(P, out_dir / "predictions.csv")
    Q = pd.DataFrame(prows).sort_values(["lead", "t", "province_code"]).reset_index(drop=True)
    meta["prospective_sha256"] = write(Q, out_dir / "prospective.csv")
    meta["rows"] = {"historical": int(len(P)), "prospective": int(len(Q))}
    return meta


def run_ablation(out_dir: Path, n_jobs: int):
    raw = H.load_raw()
    d = raw[0]
    _, Xf, B = H.inputs_h(raw, 2)
    rows = []
    for t in X.eligible_origins(2):
        t0 = time.time()
        r = X.ablation_arms(d, Xf, B, t, 2, n_jobs)
        assert r is not None
        for i, p in enumerate(L.PROVS):
            row = base_row(2, t, i, p)
            for a, v in r.items():
                row[f"{a}_p"] = float(v["p"][i])
                row[f"{a}_cfg"] = v["cfg"]
            rows.append(row)
        print(f"ablation origin {L.qs(t)} ({time.time() - t0:.0f}s)", flush=True)
    A = pd.DataFrame(rows).sort_values(["t", "province_code"]).reset_index(drop=True)
    return {"ablations_sha256": write(A, out_dir / "ablations.csv"), "rows": int(len(A))}


def main():
    part = sys.argv[1]
    out_dir = X.E70 / "sealed"
    if "--out" in sys.argv:
        out_dir = Path(sys.argv[sys.argv.index("--out") + 1])
    n_jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 8
    proto = verify_protocol()
    target = out_dir / ("predictions.csv" if part == "main" else "ablations.csv")
    if target.exists():
        raise SystemExit(f"{target} already exists; forecasts are written once")
    t0 = time.time()
    meta = run_main(out_dir, n_jobs) if part == "main" else run_ablation(out_dir, n_jobs)
    meta |= {"protocol_sha256": proto, "library": str(X.EXP), "part": part, "seconds": round(time.time() - t0),
             "sealed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (out_dir / f"meta_{part}.json").write_text(json.dumps(meta, indent=1, default=str))
    print(json.dumps(meta, indent=1, default=str))


if __name__ == "__main__":
    main()
