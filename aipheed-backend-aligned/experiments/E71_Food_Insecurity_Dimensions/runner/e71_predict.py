"""E71 step 1: compute every E71 forecast and SEAL it before any evaluation label value is read.
Training labels are read only for quarters q <= t-1 at each origin t.

    set AIPHEED_EXP=<clean export>\\aipheed-backend-aligned\\experiments
    python -B runner/e71_predict.py [--out DIR]   -> sealed/predictions.csv, sealed/prospective.csv (+ .sha256)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e71_lib as Z  # noqa: E402

H, L, np, pd = Z.H, Z.L, Z.np, Z.pd
PROSPECTIVE = {1: [L.qi("2026-Q3")], 2: [L.qi("2026-Q2"), L.qi("2026-Q3")], 3: []}


def verify_protocol():
    want = (Z.E71 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((Z.E71 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def write(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format="%.12g", lineterminator="\n")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (path.parent / f"{path.name}.sha256").write_text(f"{sha}  {path.name}\n")
    return sha


def eligible(h):
    el = json.loads((H.E63 / "out" / "eligibility.json").read_text())
    return [L.qi(q) for q in el[f"lead{h}"]["origins"]]


def main():
    out_dir = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Z.E71 / "sealed"
    if (out_dir / "predictions.csv").exists():
        raise SystemExit("already sealed")
    proto = verify_protocol()
    raw = H.load_raw()
    d, x, _ = raw
    ind = Z.indicators(d, x)
    ref = Z.reference(ind)
    S = Z.score(ind, ref)
    thr = Z.threshold(S)
    LAB = Z.labels(S, thr)[["province_code", "q", "HIGH"]]
    has_label = set(map(tuple, LAB[LAB["HIGH"].notna()][["province_code", "q"]].to_numpy()))
    rows, prow, notes = [], [], {}
    for h in (2, 1, 3):
        _, Xh, Bh = H.inputs_h(raw, h)
        allo = list(range(H.FIRST_ORIGIN, H.LAST_FEATURE_ORIGIN + 1))
        FT = pd.concat([Z.features(ind, ref, Xh, Bh, t, h, thr) for t in allo], ignore_index=True)
        for t in eligible(h) + PROSPECTIVE[h]:
            prospective = t in PROSPECTIVE[h]
            if not prospective and not all((p, t + h) in has_label for p in Z.PROVS):
                notes.setdefault(f"lead{h}_skipped_no_label", []).append(L.qs(t + h))
                continue
            known = LAB[(LAB["q"] <= t - 1) & LAB["HIGH"].notna()]
            tr = FT[FT["t"] + h <= t - 1].assign(q=lambda f: f["t"] + h).merge(known, on=["province_code", "q"])
            te = FT[FT["t"] == t].set_index("province_code").loc[Z.PROVS].reset_index()
            arms = {"LGBM": Z.fit_lgbm(tr, te, Z.FEAT_LGBM), "LGBM_NONEWS": Z.fit_lgbm(tr, te, Z.FEAT_LGBM_NONEWS),
                    "LR": Z.fit_lr(tr, te, Z.FEAT_LGBM), "PSA_LR": Z.fit_lr(tr, te, Z.FEAT_PSA),
                    "NLP_LR": Z.fit_lr(tr, te, Z.NEWS)}
            arms["DIMFUSE"], how = Z.fit_dimfuse(tr, te, thr)
            for i, p in enumerate(Z.PROVS):
                kp = known[known["province_code"] == p].sort_values("q")
                r = {"lead": h, "origin_quarter": L.qs(t), "issue_date": str(L.origin(t).date()), "target": L.qs(t + h),
                     "t": t, "province_code": p, "province": L.NAMES[p], "n_train_rows": int(len(tr)),
                     "n_train_q": int(tr["q"].nunique()), "n_train_HIGH": int(tr["HIGH"].sum()), "dimfuse_mode": how,
                     "PERSIST_p": float(kp["HIGH"].iloc[-1]) if len(kp) else np.nan,
                     "PERSIST_from": L.qs(int(kp["q"].iloc[-1])) if len(kp) else None,
                     "PROVCLIM_p": float(kp["HIGH"].mean()) if len(kp) else np.nan,
                     "MAJ_p": float(known["HIGH"].mean() >= 0.5) if len(known) else np.nan,
                     **{f"{a}_p": float(v[i]) for a, v in arms.items()},
                     **{c: float(te.loc[i, c]) for c in Z.FEAT_DIM}}
                (prow if prospective else rows).append(r)
            print(f"lead {h} origin {L.qs(t)} -> {L.qs(t + h)} train {len(tr)} rows / {int(tr['HIGH'].sum())} HIGH, "
                  f"dimfuse {how}{' (prospective)' if prospective else ''}", flush=True)
    P = pd.DataFrame(rows).sort_values(["lead", "t", "province_code"]).reset_index(drop=True)
    Q = pd.DataFrame(prow).sort_values(["lead", "t", "province_code"]).reset_index(drop=True)
    meta = {"protocol_sha256": proto, "threshold_FIR71": thr, "predictions_sha256": write(P, out_dir / "predictions.csv"),
            "prospective_sha256": write(Q, out_dir / "prospective.csv"), "rows": P.groupby("lead").size().to_dict(),
            "notes": notes, "sealed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1, default=int))
    print(json.dumps(meta, indent=1, default=int))


if __name__ == "__main__":
    main()
