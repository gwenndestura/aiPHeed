"""E31 exploratory arm (registered before running, 2026-10-15): does the validated news signal (FSSI-v2) change the
frozen E28 evaluation? The E28 protocol (d897f56d) and code are UNCHANGED; only the news panel is swapped:
  run A  FSSI-v1 rebuilt on the E31 store (same definition as E28, 2021-Q1..2026-Q2)   -> runs/e31_eval_v1/
  run B  FSSI-v2 (R1 relevance gate + v2 intensity), same quarters                    -> runs/e31_eval_v2/
Inputs = vintage 1 (ending 2026-Q2), exactly as E28. Development evidence only (every quarter was examined before);
no arm is selected or promoted on this result."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pandas as pd  # noqa: E402
import e28_evaluate as M  # noqa: E402

EXP = M.EXP
which = sys.argv[1]
M.INP = EXP / "backend_dev" / "data" / "inputs_vintage1_e29"
store = EXP / "backend_dev" / "data" / "news_e31"
src = store / ("fssi_panel.csv" if which == "v1" else "fssi_v2_panel.csv")
p = pd.read_csv(src)
p = p[p["quarter"] <= "2026-Q2"].copy()
if which == "v2":
    p = p.rename(columns={"FSSI_v2": "FSSI", "n_admitted": "n_in_fssi"})
    qi = p["quarter"].map(M.qk); idx = {(c, q): v for c, q, v in zip(p.province_code, qi, p.FSSI)}
    p["FSSI_lag1"] = [idx.get((c, q - 1)) for c, q in zip(p.province_code, qi)]
    p["FSSI_accel"] = p["FSSI"] - p["FSSI_lag1"]
dst = EXP / "runs" / f"e31_eval_{which}"
dst.mkdir(parents=True, exist_ok=True)
panel = dst / "news_panel_used.csv"
panel.write_bytes(p.to_csv(index=False, lineterminator="\n").encode())
M.FSSI = panel
M.OUT = dst
_orig = M.leakage_checks
def _leak(X):   # E28's check reads the E28 store; check the E31 store with the authorized E31 limit instead
    M_store = store / "articles.jsonl"
    import json
    bad = n = 0
    for line in M_store.read_text(encoding="utf-8").splitlines():
        a = json.loads(line); n += 1
        ts = pd.Timestamp(a["published_ph"])
        if f"{ts.year}-Q{(ts.month - 1) // 3 + 1}" != a["quarter"] or ts >= pd.Timestamp("2026-10-15", tz="Asia/Manila"):
            bad += 1
    q1 = X[X["quarter"] == "2021-Q1"]
    out = {"no_pre2021_lag_values": bool(q1["D_lag1"].isna().all() and q1["FSSI_lag1"].isna().all()),
           "articles_checked": n, "articles_outside_their_quarter_or_after_limit": bad,
           "feature_quarters_max": X["quarter"].max()}
    assert out["no_pre2021_lag_values"] and bad == 0, out
    return out
M.leakage_checks = _leak
M.main()
