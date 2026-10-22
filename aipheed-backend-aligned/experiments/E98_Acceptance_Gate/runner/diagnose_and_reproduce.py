"""E98 Questions P and R (PROTOCOL.md sections 3-4).
P: where PSA-only beats the LightGBM framework on its eligible Lead-1 rows (E97 Objective 4 predictions).
R: E97 metrics reproduce exactly from a fresh run (run the E97 scripts, move their new run folders into
   E98/runs/repro_e97/, then run this); served artifacts and serving
   code are unchanged since E97 (060fceb), with their SHA-256 recorded. Run from backend/."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
E98 = HERE.parent
EXP = E98.parent
E97 = EXP / "E97_Validation_Completion"
E97_COMMIT = "060fceb"
SERVED = ["data/thesis/firi2_history.csv", "data/thesis/firi2_evaluation.json", "data/thesis/firi2_reference.json",
          "data/thesis/firi_anchors.json", "data/thesis/final_evaluation.json", "data/e58/e58_record.json",
          "data/inputs/sws_rounds.csv", "data/inputs/lgu_vulnerability.csv",
          "app/ml/inference/thesis_system.py", "app/ml/inference/firi.py", "app/ml/inference/e41_lead2.py",
          "app/services/dashboard.py", "app/quarterly/target.py", "app/quarterly/lgu_poverty.py"]
COMMITTED = {"firi": "20261022T080842Z/firi_validation.json", "obj4": "20261022T081133Z_objective4/objective4_t43.json"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k != "stamp"}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def question_p() -> dict:
    P = pd.read_csv(E97 / "runs" / "20261022T081133Z_objective4" / "predictions_k1.csv", dtype={"province_code": str})
    S = P[P["B-PSA"].notna()].copy()
    rows = []
    for q, g in S.groupby("target_q"):
        rows.append({"target_q": q, "rows": len(g), "HIGH": int(g["y"].sum()),
                     "acc_PSA": float(((g["B-PSA"] >= 0.5).astype(int) == g["y"]).mean()),
                     "acc_LGBM": float(((g["M-U96-POV"] >= 0.5).astype(int) == g["y"]).mean()),
                     "brier_PSA": float(((g["B-PSA"] - g["y"]) ** 2).mean()),
                     "brier_LGBM": float(((g["M-U96-POV"] - g["y"]) ** 2).mean()),
                     "mean_ph_hunger_part": float(g["M-U96-POV__ph"].mean()), "mean_pp_price_part": float(g["M-U96-POV__pp"].mean())})
    T = pd.DataFrame(rows)
    T["acc_gap_PSA_minus_LGBM"] = T["acc_PSA"] - T["acc_LGBM"]
    ineligible = sorted(set(P["target_q"]) - set(S["target_q"]))
    return {"eligible_quarters": T["target_q"].tolist(), "ineligible_quarters": ineligible,
            "per_quarter": T.round(4).to_dict(orient="records"),
            "gap_quarters": T.loc[T["acc_gap_PSA_minus_LGBM"].abs() > 1e-9, "target_q"].tolist(),
            "reading": ("PSA-only is a logistic regression on the price drivers, trained on the T43 label directly. It "
                        "needs complete price-driver history, so it issues only the later quarters. The LightGBM framework "
                        "multiplies a hunger part by a price part; where T43 equals price pressure (every evaluated "
                        "row), the hunger factor can only shrink the probability.")}


def question_r() -> dict:
    out = {}
    for key, rel in COMMITTED.items():
        old = json.loads(subprocess.run(["git", "show", f"{E97_COMMIT}:aipheed-backend-aligned/experiments/E97_Validation_Completion/runs/{rel}"],
                                        capture_output=True, text=True, encoding="utf-8", check=True, cwd="..").stdout)
        pattern = "*_objective4" if key == "obj4" else "*Z"
        fresh = sorted(p for p in (E98 / "runs" / "repro_e97").glob(pattern) if p.is_dir())
        if not fresh:
            out[key] = {"reproduced": None, "reason": "no fresh run found"}
            continue
        new = json.loads((fresh[-1] / rel.split("/")[1]).read_text(encoding="utf-8"))
        a, b = strip(old), strip(new)
        out[key] = {"fresh_run": fresh[-1].name, "identical_excluding_stamp": json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)}
    changed = subprocess.run(["git", "diff", "--name-only", E97_COMMIT, "--", *[f"backend/{p}" for p in SERVED]],
                             capture_output=True, text=True, check=True, cwd="..").stdout.split()
    out["served_artifacts"] = {p: sha(Path(p)) for p in SERVED}
    out["changed_since_e97"] = changed
    out["version_identity"] = not changed
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E98 / "runs" / f"{stamp}_diag_repro"
    o.mkdir(parents=True, exist_ok=True)
    res = {"stamp": stamp, "protocol_sha256": (E98 / "PROTOCOL.sha256").read_text().split()[0],
           "P": question_p(), "R": question_r()}
    (o / "diagnose_and_reproduce.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"P": {k: v for k, v in res["P"].items() if k != "reading"}, "R": {k: v for k, v in res["R"].items() if k != "served_artifacts"}}, indent=1, default=float))
    print(o)


if __name__ == "__main__":
    sys.exit(main())
