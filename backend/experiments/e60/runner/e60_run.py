"""E60: sensitivity of the served E49 family to (a) the Eq. 4 label, (b) an 8-quarter minimum training window at
k = 1, 2 and (c) FSSI lags + acceleration. Report only: nothing is adopted or served.
Pre-registration: ../E60_results.md (written and md5-stamped before this ran; ../preregistration_md5.txt).

    python -B backend/experiments/e60/runner/e60_run.py  -> backend/experiments/e60/E60_results.json
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E60 = Path(__file__).resolve().parents[1]
BACKEND = E60.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e59" / "runner"))
sys.path.insert(0, str(BACKEND))
import e59_run as S  # noqa: E402  (E59 run_lead / metrics / algorithm3; brings in the E49 family)

X, R, L, L6, C, np, pd = S.X, S.R, S.L, S.L6, S.C, S.np, S.pd
L7 = S.L7
L6.guard32.EXP = E60                              # writes confined to E60 (and the OS temp directory)
E = R.E                                           # e36_evaluate: signflip_two
PROVS = S.PROVS
PROTECTED = dict(S.PROTECTED) | {"data/e53/e53_record.json": "fa3d0a51939fae66d87bf77c3d15d738",
                                 "data/e53/model/E53_C2_calibration.json": "9986f6cb4b4a36a9e9d676709cb3aeee"}
E59_PRED = BACKEND / "experiments" / "e59" / "runs" / "20261017T133518Z" / "predictions.csv"
MIN_TRAIN_QUARTERS = 8
FSSI_LAGS = ["fssi_lag1", "fssi_lag2", "fssi_accel"]


def md5s() -> dict:
    out = {p: hashlib.md5((BACKEND / p).read_bytes()).hexdigest() for p in PROTECTED}
    if out != PROTECTED:
        raise SystemExit(f"protected md5 mismatch: {[p for p in out if out[p] != PROTECTED[p]]}")
    return out


# ------------------------------------------------------------------ (a) Eq. 4 label
def eq4_labels() -> dict:
    """{(province_code, quarter index): 0/1} from the repository's Eq. 4 builder, quarter list extended to 2026-Q3."""
    from app.ml.features import label_generator as G

    G.MODEL_QUARTERS = [f"{y}-Q{q}" for y in range(2020, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)]
    df = G._build_cpi_labels(BACKEND / "data" / "processed" / "psa_indicators.parquet")
    return {(r.province_code, C.qk(r.quarter)): int(r.label_cpi) for r in df.itertuples()}


class DataEq4(L.Data):
    """Served data and inputs; training and test labels replaced by Eq. 4 (rows without an Eq. 4 value dropped)."""

    def __init__(self, eq4: dict):
        super().__init__(paper=False)
        self.eq4 = eq4

    def label(self, p, target, t):
        if super().label(p, target, t) is None:          # same dates/rows as served: the L0 row must exist
            return None
        return self.eq4.get((p, target))

    def training_pairs(self, t, k):
        tr = super().training_pairs(t, k)
        if tr.empty:
            return tr
        y = [self.eq4.get((p, int(q))) for p, q in zip(tr["province_code"], tr["target_q"])]
        tr = tr.assign(y=y)
        return tr[tr["y"].notna()].assign(y=lambda x: x["y"].astype(int)).reset_index(drop=True)


# ------------------------------------------------------------------ (b) 8-quarter minimum training window
class DataWindow8(L.Data):
    def train(self, t, k=1):
        tr = super().train(t, k)
        if tr.empty or tr["target_q"].nunique() < MIN_TRAIN_QUARTERS:
            return tr.iloc[0:0]
        return tr


# ------------------------------------------------------------------ (c) FSSI lags and acceleration
class DataFssiLags(L.Data):
    def _f(self, p, t):
        n = self.nw.get((p, int(t)))
        return 0.0 if n is None or n.fssi_v2 != n.fssi_v2 else float(n.fssi_v2)   # fssi_v2's own rule

    def _lags(self, X):
        X = X.copy()
        X["fssi_lag1"] = [self._f(p, t - 1) for p, t in zip(X["province_code"], X["t"])]
        X["fssi_lag2"] = [self._f(p, t - 2) for p, t in zip(X["province_code"], X["t"])]
        X["fssi_accel"] = [self._f(p, t) - self._f(p, t - 1) for p, t in zip(X["province_code"], X["t"])]
        return X

    def train(self, t, k=1):
        tr = super().train(t, k)
        return tr if tr.empty else self._lags(tr)

    def test(self, t, k=1):
        return self._lags(super().test(t, k))


def register_lag_pool():
    L6.FEATURE_SETS["COMPACT_T5_FL"] = L6.FEATURE_SETS["COMPACT_T5"] + FSSI_LAGS
    L6.FEATURE_SETS["COMB_T5_FL"] = L6.FEATURE_SETS["COMB_T5"] + FSSI_LAGS
    L6.POOLS["E60-FL"] = ([("COMPACT_T5_FL", g) for g in L6.COMPLEXITY] + [("COMB_T5_FL", g) for g in L6.COMPLEXITY],
                          ("COMB_T5_FL", "G1"))


# ------------------------------------------------------------------ reporting
def low_caught(g):
    low = g[g["y"] == 0]
    return f"{int((low['p'] < 0.5).sum())}/{len(low)}"


def paired(g: pd.DataFrame, ref: pd.DataFrame) -> dict:
    """Arm vs reference on the common (target quarter, province) rows, both scored against the ARM's labels."""
    j = g.merge(ref[["target_quarter", "province_code", "p"]], on=["target_quarter", "province_code"],
                suffixes=("", "_ref"))
    j["b_arm"], j["b_ref"] = (j["p"] - j["y"]) ** 2, (j["p_ref"] - j["y"]) ** 2
    per = j.groupby("target_quarter")[["b_arm", "b_ref"]].mean()
    diff = (per["b_ref"] - per["b_arm"]).to_numpy()            # > 0 = arm better
    acc_a = ((j["p"] >= .5).astype(int) == j["y"]).mean()
    acc_r = ((j["p_ref"] >= .5).astype(int) == j["y"]).mean()
    return {"common_rows": int(len(j)), "common_dates": int(len(per)),
            "arm_brier": float(j["b_arm"].mean()), "ref_brier": float(j["b_ref"].mean()),
            "brier_diff_arm_minus_ref": float(j["b_arm"].mean() - j["b_ref"].mean()),
            "accuracy_arm": float(acc_a), "accuracy_ref": float(acc_r),
            "signflip_p_two_sided": E.signflip_two(diff)}


def block(r: dict, g: pd.DataFrame | None, ref: pd.DataFrame | None, pers: dict | None = None) -> dict:
    out = dict(r)
    if g is not None:
        out["LOW_caught"] = low_caught(g)
        if pers is not None:
            out["persistence"] = pers
        if ref is not None:
            out["vs_reference"] = paired(g, ref)
    return out


def main():
    os.chdir(BACKEND)
    res = {"md5_start": md5s(), "preregistration": (E60 / "preregistration_md5.txt").read_text().split()}
    X.register()
    e59 = pd.read_csv(E59_PRED, dtype={"province_code": str})
    ref = {k: e59[e59["arm"] == f"k{k}"] for k in (1, 2)}
    frames = []

    # ---- (a) Eq. 4 label, lead 1, served pool
    print("(a) Eq. 4 label", flush=True)
    eq4 = eq4_labels()
    da = DataEq4(eq4)
    S.POOL = "E48-T5"
    ra, ga = S.run_lead(da, 1)
    ga = ga.assign(arm="a_eq4")
    # Eq. 4 persistence: the province's Eq. 4 label in quarter t-1 (all its CPI months published at O(t))
    gp = ga.assign(p=[float(eq4.get((p, C.qk(t) - 1), 0.5)) for p, t in zip(ga["province_code"], ga["t"])])
    pers_a = {k: v for k, v in S.metrics(gp).items() if k in ("accuracy", "balanced_accuracy", "brier")}
    pers_a["LOW_caught"] = low_caught(gp)
    pers_a["definition"] = "Eq. 4 label of quarter t-1"
    ra["persistence_L0_input_diagnostic"] = ra.pop("persistence")    # E59's B1 uses y_last (L0), not Eq. 4
    res["a_eq4"] = block(ra, ga, ref[1], pers_a)
    res["a_eq4"]["reference_note"] = "served E49 probabilities scored against the Eq. 4 labels on the same rows"
    res["a_eq4"]["vs_persistence"] = paired(ga, gp)
    res["a_eq4"]["label_HIGH_share_on_rows"] = float(ga["y"].mean())
    frames.append(ga)

    # ---- (b) 8-quarter minimum window, k = 1 and 2, served pool
    db = DataWindow8(paper=False)
    res["b_window8"] = {"leads": []}
    for k in (1, 2):
        print(f"(b) window 8, k = {k}", flush=True)
        rb, gb = S.run_lead(db, k)
        if gb is not None:
            gb = gb.assign(arm=f"b_w8_k{k}")
            frames.append(gb)
        res["b_window8"]["leads"].append(block(rb, gb, ref[k]))
    res["b_window8"]["algorithm3"] = S.algorithm3(res["b_window8"]["leads"], ci=False)
    res["b_window8"]["algorithm3_ci"] = S.algorithm3(res["b_window8"]["leads"], ci=True)

    # ---- (c) FSSI lags + acceleration, lead 1, pool E60-FL
    print("(c) FSSI lags", flush=True)
    register_lag_pool()                         # only now: (a) and (b) fit the served pools alone
    dc = DataFssiLags(paper=False)
    S.POOL = "E60-FL"
    rc, gc = S.run_lead(dc, 1)
    gc = gc.assign(arm="c_fssi_lags")
    frames.append(gc)
    res["c_fssi_lags"] = block(rc, gc, ref[1])
    S.POOL = "E48-T5"

    res["md5_end"] = md5s()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E60 / "runs" / stamp
    run.mkdir(parents=True)
    pd.concat(frames).to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E60 / "E60_results.json", C.clean(res))
    print("RUN", stamp)


if __name__ == "__main__":
    main()
