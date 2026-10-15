"""E31 step 1b: freeze the P45 (and Chapter I baseline-model) forecasts for 2026-Q3 at LEAD 2, before any 2026-Q3
outcome is retrieved.

Lead 2 from origin O(2026-Q1) = 2026-04-01 needs only inputs the P45 2026 extension already built and verified:
the 2026-Q1 news row (news_2026Q1.csv, sha pinned) and 2025-Q4 government values (t-1 rule, pinned feature file).
Lead 1 (origin 2026-07-01) would need a 2026-Q2 news row and 2026-Q1 government features, which do not exist; it is
not produced.

Procedure: the UNCHANGED frozen walk-forward code of the extension (E25 e23_lib / e25lib / run_e25; seed 42;
inner_select; no tuning, no new arm). The only addition is the unlabeled test frame for target 2026-Q3 (the label
is unknown, so E25 test_rows would return None); it is built with E25's own last_values(), exactly as test_rows
builds labeled rows. As a procedure check, the lead-1 2026-Q1 predictions are recomputed and compared with the
extension's run 20261014T105026Z.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E31 = Path(__file__).resolve().parents[1]
EXPS = E31.parent
EXT = EXPS / "2026-10-14_P45_2026_Extension"
E25 = EXPS / "E25_Reliable_Forecasts_2021_2026"
sys.path.insert(0, str(E25 / "runner"))
sys.path.insert(0, str(EXT / "runner"))
import guard  # noqa: E402  (E25 guard: protected trees refused; only pinned, window-masked reads allowed)

_base = guard.decide


def _d31(path, write):
    p = guard._resolve(path)
    if p is not None and guard._under(p, E31 / "frozen"):
        return "allow"
    if write:
        return "deny"
    if p is not None and (guard._under(p, EXT) or guard._under(p, E31)):
        return "allow"
    return _base(path, write)


guard.decide = _d31
guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import run_extension as X  # noqa: E402  (installs its own decide on top; writes outside its folder fall to _d31)

L, E, R = X.L, X.E, X.R
qk, qs = E.qk, E.qs


def unlabeled_rows(T, t: int, k: int) -> pd.DataFrame:
    lv = E.last_values(T, t)
    rows = []
    for p in sorted(lv):
        last, m4, dif = lv[p]
        rows.append({"province_code": p, "t": t, "target_quarter": qs(t + k), "target_q": t + k, "v": np.nan,
                     "y": -1, "v_last": last, "margin_last": last - T.tau(t),
                     "y_last": float(last > T.tau(t)) if last == last else np.nan, "v_mean4": m4, "v_diff": dif})
    return pd.DataFrame(rows)


def main():
    data = R.load_real()
    T = data["targets"]["T1_A"]
    Xf = X.extended_X(data)
    N, G = L.NLP, data["gov_cols"] + ["sws_hunger"]
    cols = {"P45": N + G, "F12": X.F12, "F12_SWS": X.F12 + ["sws_hunger"], "B2_lr_combined": N + G,
            "B3_lr_gov_only": G, "B4_lr_nlp_only": N, "B5_lgbm_gov_only": G, "B6_lgbm_nlp_only": N}
    cache, out, check = {}, {}, {}
    t = qk("2026-Q1")
    for k, frame in ((1, "labeled"), (2, "unlabeled")):
        tau = T.tau(t)
        te = E.test_rows(T, t, k, tau) if frame == "labeled" else unlabeled_rows(T, t, k)
        tr = E.training_pairs(T, t, k, tau, cache)
        assert tr["target_q"].max() <= t - 1 and all(T.pub(q, t) for q in tr["target_quarter"].unique())
        tr_s, tr_p = R.feature_frames(T, Xf, t, k, tau, cache)
        teX = te.merge(Xf.drop(columns=["quarter"]), on=["province_code", "t"], how="left")
        assert len(teX) == 5
        res = {}
        for arm, c in cols.items():
            if arm.startswith(("B2", "B3", "B4")):
                p = L.fit_lr(tr_s, c, teX)
            else:
                sel = L.inner_select(tr_s, tr_p, c, k)
                p, _, _ = L.lgbm_predict(tr_s, tr_p, c, sel["config"], teX, k)
            res[arm] = {r.province_code: float(p[i]) for i, r in te.reset_index(drop=True).iterrows()}
        if frame == "labeled":
            old = pd.read_csv(EXT / "runs" / "20261014T105026Z" / "predictions.csv", dtype={"province_code": str})
            old = old[(old.lead == 1) & (old.t == "2026-Q1")]
            diffs = [abs(res[r.model][r.province_code] - r.score) for r in old.itertuples() if r.model in res]
            check = {"lead1_2026Q1_rows_compared": len(diffs), "max_abs_diff": float(max(diffs))}
            assert check["max_abs_diff"] < 1e-9, check
        else:
            out = {"origin": "2026-04-01", "reference_quarter": "2026-Q1", "lead": 2, "target_quarter": "2026-Q3",
                   "information_cutoff": "2026-03-31T23:59:59+08:00", "tau_at_origin": float(tau),
                   "training_pairs": int(len(tr)), "arms_p_high": res}
    rec = {"record": "E31 frozen 2026-Q3 P45 and Chapter I model-baseline forecasts, lead 2 (retrospective-blind)",
           "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "procedure": "unchanged E25 / P45-extension walk-forward; seed 42; no tuning",
           "procedure_check": check, "news_2026Q1_sha256": X.NEWS_SHA, "forecast": out,
           "not_produced": "lead 1 (origin 2026-07-01): needs a 2026-Q2 news row and 2026-Q1 government features"}
    body = json.dumps(rec, indent=1).encode("utf-8")
    (E31 / "frozen" / "E31_FROZEN_Q3_P45_LEAD2.json").write_bytes(body)
    h = hashlib.sha256(body).hexdigest()
    (E31 / "frozen" / "E31_FROZEN_Q3_P45_LEAD2.sha256").write_bytes(f"{h}  E31_FROZEN_Q3_P45_LEAD2.json\n".encode())
    print(h, json.dumps(check))
    print({a: {p[-7:-5]: round(v, 3) for p, v in d.items()} for a, d in out["arms_p_high"].items()})


if __name__ == "__main__":
    main()
