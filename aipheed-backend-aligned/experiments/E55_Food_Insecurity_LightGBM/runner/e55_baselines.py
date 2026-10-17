"""E55 step 2 under the frozen PROTOCOL.md (section 7): the Chapter 1 Objective 4 baselines refitted on the T43
food-insecurity labels (E52's baseline code with T43 labels and T43 persistence). Runs inside the E32 data guard (via
E51's script); writes confined to E55.

    backend/venv/Scripts/python.exe -B runner/e55_baselines.py   -> runs/baselines_<UTC stamp>/rows_baselines.csv
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E55 = Path(__file__).resolve().parents[1]
EXP = E55.parent
sys.path.insert(0, str(EXP / "E51_Target_Definition" / "runner"))
import e51_compare as V  # noqa: E402  (installs the E32 guard; D-1 threshold guard)

E, np, pd, qk, qs, PROVS = V.E, V.np, V.pd, V.qk, V.qs, V.PROVS
E.L7.L6.guard32.EXP = E55
L36 = E.L6
EVAL = [f"{y}-Q{q}" for y in (2024, 2025, 2026) for q in (1, 2, 3, 4)]
EVAL = [x for x in EVAL if "2024-Q2" <= x <= "2026-Q3"]


def verify() -> str:
    want = (E55 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E55 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def main():
    proto = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E55 / "runs" / f"baselines_{stamp}"
    out.mkdir(parents=True)
    lab_df = pd.read_csv(E55 / "data" / "labels_t43.csv", dtype={"province_code": str})
    pers_df = pd.read_csv(E55 / "data" / "persistence_t43.csv", dtype={"province_code": str})
    lab = {(p, int(q)): int(y) for p, q, y in zip(lab_df["province_code"], lab_df["q"], lab_df["T43"]) if y == y}
    pers = {(int(t), p): (np.nan if pd.isna(v) else float(v)) for t, p, v in
            zip(pers_df["t"], pers_df["province_code"], pers_df["T43_last"])}
    dl = V.DataLabel(lab, pers)
    Pr, info = E.walk_forward(dl)
    g = Pr[Pr["arm"] == "E38-LGBM"]
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
            if r.target_quarter not in EVAL:
                continue
            pv = yl.loc[r.province_code]
            row = {"target": r.target_quarter, "t_label": r.t, "province_code": r.province_code, "y": int(r.y),
                   "B1_PERSIST_p": clim if pv != pv else float(pv), "B7_E38PROC_p": r.p, "B7_E38PROC_thr": r.threshold,
                   "CLIM_p": clim, "HIGH_p": 1.0, "LOW_p": 0.0, "n_train": int(len(tr)), "n_train_HIGH": int(tr["y"].sum())}
            for k, v in preds.items():
                row[f"{k}_p"] = float(v[r.province_code])
            rows.append(row)
    R = pd.DataFrame(rows).sort_values(["target", "province_code"]).reset_index(drop=True)
    R.to_csv(out / "rows_baselines.csv", index=False)
    (out / "meta.json").write_text(json.dumps({"protocol_sha256": proto, "run_utc": stamp, "rows": int(len(R)),
                                               "quarters": sorted(R["target"].unique().tolist()),
                                               "HIGH": int(R["y"].sum())}, indent=1))
    print(stamp, "baseline rows", len(R), "quarters", R["target"].nunique(), "HIGH", int(R["y"].sum()))


if __name__ == "__main__":
    main()
