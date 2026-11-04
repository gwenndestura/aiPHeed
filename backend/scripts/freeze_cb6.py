"""
scripts/freeze_cb6.py
---------------------
ONE-TIME step, run once on a development machine and never by the scheduler: fit C-B6 at origin 2026-Q3 with the exact
procedure of OBJECTIVES_AUDIT/runner/cb6_model._origin, save that one booster, and prove it reproduces the stored forecasts.

    cd backend && python -m scripts.freeze_cb6

Writes backend/data/cb6_auto/frozen/{model.txt, manifest.json}. Refuses to overwrite an existing freeze: the quarterly job
scores this booster for good, so a second freeze would be a new model. The experiment code is imported read only; it lives
outside the Docker build context, so production cannot run this script at all.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
EXP = BACKEND.parent / "aipheed-backend-aligned" / "experiments"
OUT = BACKEND / "data" / "cb6_auto" / "frozen"
FREEZE_ORIGIN = "2026-Q3"
SERVED_P_2027Q1_LEAD2 = 0.955803          # backend/data/foodinsecurity_engine_cb6/rows.csv, issue 2026-10-01


def main() -> int:
    if (OUT / "manifest.json").exists():
        print(f"refused: {OUT / 'manifest.json'} exists; the frozen model is never replaced")
        return 1
    sys.path.insert(0, str(EXP / "OBJECTIVES_AUDIT" / "runner"))
    import cb6_model as CB6                                                    # read only; checks its pre-registration
    N, V, H = CB6.N, CB6.V, CB6.H

    prereg = CB6.check()
    CB6._init()
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    cols = CB6.PC.CB + CB6.ST
    t = H.qi(FREEZE_ORIGIN)

    # cb6_model._origin, line for line, keeping the fitted model
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(N.TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                         on=["area", "q"], how="inner")
    assert H.eligible(tr[tr["area"] == "BL"])
    cfg = H.lgbm_select(tr, cols, mono=False)
    m = H.LGBM(cfg, cols, False).fit(tr)
    p_fit = m.predict(te)

    # 1. the in-memory fit equals the stored walk-forward forecasts of this origin, every lead
    stored = pd.read_csv(CB6.OUT / "cb6_fits.csv")
    stored = stored[(stored["name"] == CB6.NAME) & (stored["t"] == t)].set_index("lead").sort_index()
    te = te.sort_values("lead")
    p_fit = m.predict(te)
    diff_fit = float(np.abs(p_fit - stored.loc[te["lead"], "p"].to_numpy()).max())
    assert diff_fit < 1e-12, f"refit differs from cb6_fits.csv by {diff_fit}"
    assert int(stored["cfg"].iloc[0]) == int(cfg["id"]), (stored["cfg"].iloc[0], cfg["id"])

    # 2. the saved text booster, reloaded with no sklearn wrapper, gives the same probabilities and SHAP
    import lightgbm as lgb

    OUT.mkdir(parents=True, exist_ok=True)
    model_path = OUT / "model.txt"
    m.m.booster_.save_model(str(model_path))
    model_path.write_bytes(model_path.read_bytes().replace(b"\r\n", b"\n"))
    b = lgb.Booster(model_file=str(model_path))
    X = te[cols].astype(float)
    p_loaded = b.predict(X)
    diff_loaded = float(np.abs(p_loaded - stored.loc[te["lead"], "p"].to_numpy()).max())
    assert diff_loaded < 1e-12, f"reloaded booster differs by {diff_loaded}"
    shap_loaded = np.asarray(b.predict(X, pred_contrib=True))[:, :-1]
    shap_stored = stored.loc[te["lead"], [f"shap_{c}" for c in cols]].to_numpy(float)
    diff_shap = float(np.abs(shap_loaded - shap_stored).max())
    assert diff_shap < 1e-9, f"SHAP differs by {diff_shap}"
    assert list(b.feature_name()) == cols, (b.feature_name(), cols)

    p = dict(zip(te["lead"].astype(int), p_loaded))
    assert round(float(p[2]), 6) == SERVED_P_2027Q1_LEAD2, p[2]

    manifest = {
        "model": CB6.NAME, "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origin": FREEZE_ORIGIN, "issue_date": H.issue(t), "config": {k: cfg[k] for k in ("id", "depth", "leaves", "trees", "cw")},
        "seed": H.SEED_LGBM, "columns": cols, "n_train": int(len(tr)),
        "train_target_quarters": [H.qs(int(tr["q"].min())), H.qs(int(tr["q"].max()))],
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "prereg_sha256": prereg, "lightgbm": lgb.__version__,
        "reproduction": {"max_abs_diff_fit_vs_cb6_fits": diff_fit, "max_abs_diff_loaded_vs_cb6_fits": diff_loaded,
                         "max_abs_diff_shap_loaded_vs_cb6_fits": diff_shap,
                         "stored_p_by_lead": {str(int(k)): float(stored.loc[k, "p"]) for k in stored.index},
                         "loaded_p_by_lead": {str(k): float(v) for k, v in p.items()},
                         "served_rows_csv_p_2027Q1_lead2": SERVED_P_2027Q1_LEAD2},
        "reference_inputs_origin": {str(int(r["lead"])): {c: (None if pd.isna(r[c]) else float(r[c])) for c in cols}
                                    for _, r in te.iterrows() if int(r["lead"]) in (1, 2)},
        "note": ("Weights fixed at this one fit; never retrained or reselected by the quarterly job. The development evidence "
                 "(walk-forward, refit at every origin) was not produced by these fixed weights."),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: manifest[k] for k in ("origin", "config", "n_train", "model_sha256", "reproduction")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
