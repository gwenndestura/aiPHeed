"""E45: threshold (tau) definitions on the served model (E48-A1 features + E49-C2 shrinkage). Experiment only.

    python -B backend/experiments/e45/runner/e45_run.py  -> backend/experiments/e45/E45_results.json

S1 = H + 2D is unchanged; only tau changes. tau(t) uses only S1 of quarters <= t-1 whose definition-A SWS rounds were
ALL posted before the origin O(t) (the current rule's publication filter), from 2021-Q1 on:
  T0  median of all pooled S1 of those quarters (the current rule; must reproduce E49-C2)
  T1  median of pooled S1 over the last 4 such quarters
  T2  median of pooled S1 over the last 8 such quarters
  T3  median of THAT province's S1 over its last 8 such quarters (province-specific tau)
Fewer quarters than the window -> all available ones. tau also enters two E36 inputs (H_margin = H_last - tau,
y_last = last published S1 > tau); they are computed with the variant's own tau (per province under T3), as for T0.

Everything else is the served pipeline: E36 walk-forward (origins, training rows, grid, seed 36, nested rule) on the
E48-A1 pool (E36 inputs + five trigger proportions), then E49-C2 shrinkage p' = a*p + (1-a)*base_rate with `a` chosen on
earlier dates only (dates whose target was posted before the origin), raw p when fewer than 3 such dates.

ADOPTION (fixed before results): acceptable only if ALL of base rate 35-70% (all labelled province-quarters
2021-Q3..2026-Q3); balanced accuracy >= 0.75; AUC >= 0.80; Brier <= persistence's on the same labels; accuracy >= the
same labels' always-HIGH. Several pass -> prefer T2, then higher balanced accuracy.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E45 = Path(__file__).resolve().parents[1]
BACKEND = E45.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e49" / "runner"))
import e49_run as R  # noqa: E402  (E49 calibration helpers; brings in e48_lib / e36_lib)

L, L6, C, np, pd, M = R.L, R.L6, R.C, R.np, R.pd, R.M
L6.guard32.EXP = E45
NAMES = R.NAMES
VARIANTS = {"T0": None, "T1": 4, "T2": 8, "T3": 8}


class Data(L.Data):
    """E48 data (E36 features + trigger shares), current labels replaced by the variant's tau."""

    def __init__(self, variant: str):
        super().__init__(paper=False)
        self.variant = variant
        self._tau = {}

    def _published(self, t):
        o = L6.origin(t)
        return [q for q in self.posted_quarters(o) if C.qk("2021-Q1") <= q <= t - 1]

    def tau_p(self, p, t) -> float:
        if self.variant == "T0":
            return super().tau(t)
        key = (p if self.variant == "T3" else None, t)
        if key not in self._tau:
            qs = self._published(t)[-VARIANTS[self.variant]:]
            vals = [s for (pp, q), s in self.Sv.items() if q in qs and s == s and (self.variant != "T3" or pp == p)]
            self._tau[key] = float(np.median(vals)) if vals else float("nan")
        return self._tau[key]

    def tau(self, t):
        return self.tau_p(None, t) if self.variant in ("T0", "T1", "T2") else float("nan")

    def label(self, p, target, t):
        s = self.Sv.get((p, target))
        tau = self.tau_p(p, t)
        return None if s is None or s != s or tau != tau else int(s > tau)

    def features(self, t, k):
        X = super().features(t, k).copy()
        if self.variant == "T3":
            X["tau"] = [self.tau_p(p, t) for p in X["province_code"]]
        else:
            X["tau"] = self.tau(t)
        X["H_margin"] = X["H_last"] - X["tau"]
        last = X["last_label_quarter"].iloc[0]
        if last:
            lq = C.qk(last)
            X["y_last"] = [float(self.Sv[(p, lq)] > tv) if (p, lq) in self.Sv and self.Sv[(p, lq)] == self.Sv[(p, lq)]
                           else np.nan for p, tv in zip(X["province_code"], X["tau"])]
        return X


def drivers_q4(d, fs, g, T):
    """Driver shares at Q4 2026 with the live panel's method (app/ml/inference/e31_engine.five_trigger_drivers +
    dashboard.explainability_region): per province, magnitude = |sum of SHAP of the group's inputs| + the news inputs'
    |SHAP| split by the topics of the validated titles; CALABARZON pools the magnitudes; integer shares sum to 100."""
    import importlib.util

    # Load the LIVE engine file by path: in this process `app` is the E31 research copy (put first on sys.path by the
    # experiment libraries), so `import app.ml.inference.e31_engine` would not be the served code.
    spec = importlib.util.spec_from_file_location("live_e31_engine", BACKEND / "app" / "ml" / "inference" / "e31_engine.py")
    E31 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E31)

    def _integer_shares(values):                       # app/services/dashboard._integer_shares (largest remainder)
        total = sum(values)
        if total <= 0:
            return [0] * len(values)
        exact = [v / total * 100 for v in values]
        floors = [int(x) for x in exact]
        for i in sorted(range(len(exact)), key=lambda i: exact[i] - floors[i], reverse=True)[:100 - sum(floors)]:
            floors[i] += 1
        return floors

    feats = L6.FEATURE_SETS[fs]
    model = L6.fit_lgbm(d.train(T), feats, g)
    te = d.test(T)
    c = L6.shap_contributions(model, te[feats]).drop(columns="expected_value")
    ev = C.qs(T)                                           # evidence quarter = t (the forecast's news window)
    pooled = {k: 0.0 for k in E31.TRIGGER_GROUP_FEATURES}
    per = {}
    for i, code in enumerate(te["province_code"]):
        shap = c.iloc[i].to_dict()
        mag = {k: abs(sum(shap.get(f, 0.0) for f in fs_)) for k, fs_ in E31.TRIGGER_GROUP_FEATURES.items()}
        for level, nf in E31.NEWS_FEATURES.items():
            sh, _ = E31.news_topic_shares(code if level == "province" else None, ev)
            a = sum(abs(shap.get(f, 0.0)) for f in nf)
            for k, w in sh.items():
                mag[k] += w * a
        keys = list(mag)
        per[NAMES[code]] = dict(zip(keys, _integer_shares([mag[k] for k in keys])))
        for k in keys:
            pooled[k] += mag[k]
    keys = list(pooled)
    return {"CALABARZON": dict(zip(keys, _integer_shares([pooled[k] for k in keys]))), **per}


def run_variant(v):
    d = Data(v)
    Pr, info = L6.walk_forward(d)
    dates = [C.qk(q) - 1 for q in info["dates"]]
    T = L6.OPERATIONAL_T
    labels = {t: {c: int(d.label(c, t + 1, t)) for c in L.PROVS} for t in dates}
    base = {}
    for t in dates + [T]:
        tr = d.train(t)
        base[t] = float((tr["y"].sum() + 1) / (len(tr) + 2))
    prior_of = {t: L6.eligible_prior_dates(d, t, dates) for t in dates + [T]}
    raw = {t: {c: float(x) for c, x in Pr[(Pr["arm"] == "E48-T5") & (Pr["t"] == C.qs(t))].set_index("province_code")["p"].items()}
           for t in dates}
    (fs, g), _ = L6.operational_choice(d, Pr, "E48-T5")
    op = L6.lgbm_predict(d.train(T), d.test(T), L6.FEATURE_SETS[fs], g)
    cal, fb, params = R.calibrated({**raw, T: {c: float(op[c]) for c in L.PROVS}},
                                   {**labels, T: {c: 0 for c in L.PROVS}}, base, prior_of, "shrink")
    fr = R.frame({t: cal[t] for t in dates}, labels, v)
    out = {"test_quarters": info["dates"], "operational": L6.cfg_name(fs, g),
           "fallback_raw": [C.qs(t + 1) for t in fb if t != T],
           "shrink_params": {C.qs(t + 1): p for t, p in params.items()},
           "metrics": R.summary(fr), "metrics_raw": R.summary(R.frame(raw, labels, v + "-raw"))}
    for b in ("B1_PERSISTENCE", "ALWAYS_HIGH"):
        out[b] = R.summary(Pr[Pr["arm"] == b])
    out["n_p_ge_0.95"] = int((fr["p"] >= 0.95).sum())
    out["base_rate_test_rows"] = float(fr["y"].mean())
    out["index"] = {C.qs(t + 1): {"CALABARZON": float(np.mean(list(cal[t].values()))), **{NAMES[c]: cal[t][c] for c in L.PROVS}}
                    for t in dates + [T]}
    out["tau_by_target"] = {C.qs(t + 1): ({NAMES[c]: d.tau_p(c, t) for c in L.PROVS} if v == "T3" else d.tau(t))
                            for t in dates + [T]}
    out["drivers_q4_2026"] = drivers_q4(d, fs, g, T)
    # base rate on every labelled province-quarter (label at its lead-1 origin)
    rows = []
    for (c, q), s in d.Sv.items():
        if s == s and q >= C.qk("2021-Q3"):
            y = d.label(c, q, q - 1)
            if y is not None:
                rows.append({"province": NAMES[c], "quarter": C.qs(q), "y": y})
    out["labels_all"] = rows
    return out


def main():
    import os

    os.chdir(BACKEND)                                  # the live engine's record/news paths are relative to backend/
    R.register()
    res = {"variants": {}}
    for v in VARIANTS:
        print("running", v, flush=True)
        res["variants"][v] = run_variant(v)
    lab0 = {(r["province"], r["quarter"]): r["y"] for r in res["variants"]["T0"]["labels_all"]}
    for v, o in res["variants"].items():
        df = pd.DataFrame(o["labels_all"])
        df["yr"] = df["quarter"].str[:4]
        o["base_rate"] = {"overall": float(df["y"].mean()), "n": int(len(df)),
                          "per_year": {y: float(g["y"].mean()) for y, g in df.groupby("yr")},
                          "test_rows": o["base_rate_test_rows"]}
        lab = {(r["province"], r["quarter"]): r["y"] for r in o["labels_all"]}
        same = [k for k in lab if k in lab0]
        o["pct_differ_from_T0"] = float(np.mean([lab[k] != lab0[k] for k in same]))
        o["labels_compared_with_T0"] = len(same)
        m, pe, ah = o["metrics"], o["B1_PERSISTENCE"], o["ALWAYS_HIGH"]
        crit = {"base_rate_35_70": 0.35 <= o["base_rate"]["overall"] <= 0.70,
                "balanced_accuracy_ge_0.75": (m["balanced_accuracy"] or 0) >= 0.75,
                "auc_ge_0.80": (m["auc"] or 0) >= 0.80,
                "brier_le_persistence": m["brier"] <= pe["brier"] + 1e-12,
                "accuracy_ge_always_high": m["accuracy"] >= ah["accuracy"] - 1e-12}
        o["adoption"] = {"criteria": crit, "acceptable": all(crit.values())}
    ok = [v for v, o in res["variants"].items() if o["adoption"]["acceptable"]]
    pick = "T2" if "T2" in ok else (max(ok, key=lambda v: res["variants"][v]["metrics"]["balanced_accuracy"]) if ok else None)
    res["adoption"] = {"acceptable": ok, "chosen": pick}
    for o in res["variants"].values():
        o.pop("labels_all")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    res["run"] = stamp
    C.write_json(E45 / "E45_results.json", C.clean(res))
    print("RUN", stamp, "acceptable", ok, "chosen", pick)


if __name__ == "__main__":
    main()
