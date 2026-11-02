"""Independent audit of FI9-R: recomputes the reassessment metrics from wf_predictions.csv with separate code (the
explicit counting in app.fi9.audit), and checks timing, protection of production, the register and the pin.

    python -m app.fi9r.audit run         # writes data/fi9r/out/audit.json; exit 1 on failure
"""
from __future__ import annotations

import hashlib
import json
import sys

import pandas as pd

from app.fi9 import MODEL
from app.fi9 import OUT as FI9OUT
from app.fi9 import quarters as Q
from app.fi9.audit import _recompute
from app.fi9r import OUT
from app.paths import BACKEND_DIR


def run() -> dict:
    from app.fi9 import prospective as PR
    from app.fi9r.protocol import check
    W = pd.read_csv(OUT / "wf_predictions.csv")
    S = json.loads((OUT / "reassessment.json").read_text())
    A = json.loads((OUT / "adoption.json").read_text())
    C: dict = {}
    C["protocol_lock_matches"] = check() == S["protocol_sha256"]
    yr = W["target_quarter"].str[:4].astype(int)
    worst = 0.0
    for per, m in {"full": yr > 0, "A_development": yr <= 2017, "B_previously_examined": yr >= 2018}.items():
        for tag, g in W[m].groupby("tag"):
            mine, rep = _recompute(g), S["periods"][per]["models"][tag]
            for k, v in mine.items():
                if v is not None and rep[k] is not None:
                    worst = max(worst, abs(v - rep[k]))
    C["metrics_recomputed_match"] = worst < 1e-6
    C["every_target_is_next_quarter"] = bool((W["target_quarter"].map(Q.index) == W["issue_quarter"].map(Q.index) + 1).all())
    C["training_targets_published_by_issue"] = bool((pd.to_datetime(W["train_max_target_published"].dropna()) <=
                                                     pd.to_datetime(W.loc[W["train_max_target_published"].notna(), "issue_date"])).all())
    C["no_duplicate_forecasts"] = not W.duplicated(["tag", "target_quarter"]).any()
    C["c0_reproduces_fi9_exactly"] = S["reproduces_fi9"]["c0_vs_fi9_max_abs_p_diff"] < 1e-9 and S["reproduces_fi9"]["c0_vs_fi9_class_mismatches"] == 0
    C["rows_reproduce_fi9_dataset"] = max(S["reproduces_fi9"]["rows_max_abs_diff"].values()) < 1e-9
    adopted = [t for t, v in A.items() if isinstance(v, dict) and v.get("adopt")]
    pin = json.loads((BACKEND_DIR / "data" / "fi9" / "PRODUCTION_PIN.json").read_text())
    art = json.loads((MODEL / "lead1_model.json").read_text())
    C["production_model_unchanged_unless_adopted"] = bool(adopted) or (art["model"] == pin["model"] and art["kind"] == pin["kind"])
    C["production_artifact_matches_pin"] = art["sha256"] == pin["artifact_sha256_at_pin"]
    C["interval_change_follows_rule"] = ("conformal_halfwidth_95" in art["params"]) == A["interval"]["replace_with_conformal"]
    base = BACKEND_DIR / "data" / "fi9" / "baseline_20261103"
    sums = dict(reversed(line.split(" *")) for line in (base / "SHA256SUMS").read_text().splitlines() if line.strip())
    C["baseline_snapshot_intact"] = all(hashlib.sha256((base / f).read_bytes()).hexdigest() == h for f, h in sums.items())
    C["prospective_register_intact"] = PR.verify()
    f = json.loads((FI9OUT / "forecast.json").read_text())
    C["served_forecast_uses_pinned_artifact"] = f["artifact_sha256"] == pin["artifact_sha256_at_pin"]
    res = {"checks": {k: bool(v) for k, v in C.items()}, "max_metric_difference": worst, "adopted_models": adopted}
    res["all_passed"] = all(res["checks"].values())
    (OUT / "audit.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__" and sys.argv[1:] == ["run"]:
    r = run()
    print(json.dumps(r, indent=1))
    sys.exit(0 if r["all_passed"] else 1)
