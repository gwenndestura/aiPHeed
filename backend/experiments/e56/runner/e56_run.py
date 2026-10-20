"""E56: compare label definitions (Eq. 3 variants) with E53-A1, lead 1. Experiment only.

    python -B backend/experiments/e56/runner/e56_run.py  -> backend/experiments/e56/E56_results.json

S1 = H + 2D is unchanged; only the HIGH rule changes. Every threshold uses only quarters whose definition-A SWS rounds
were ALL posted before the origin O(t) (the served publication filter, e32_lib.posted_quarters), 2021-Q1..t-1:
  L0  tau(t) = median of the pooled S1 of ALL such quarters (the served rule; must reproduce E53-A1:
      acc 0.785, bal 0.836, AUC 0.880, Brier 0.150, Q4 2026 CALABARZON 0.789)
  L1  tau(t) = median of the pooled S1 of the LAST 8 such quarters (rolling 2 years)
  L2  tau(t) = median of the pooled S1 of the LAST 4 such quarters (rolling 1 year)
  L3  HIGH if the province's S1 > median S1 of the five provinces in the SAME quarter (relative; H cancels, so D only).
      Uses only the target quarter's own published S1, so it needs no history.
tau enters the inputs H_margin (= H_last - tau) and y_last (= last published label); L1/L2 use the variant's tau for
both (as E45/E51). L3 has no H threshold: H_margin keeps the L0 tau, y_last = the L3 label of the last published
quarter, and every training row is relabelled with the L3 rule.

Model (identical for every label; no tuning): E53-A1 = pool (COMPACT_T5 + cond, COMB_T5 + cond) x G1/G4/G3/G2,
E36 nested walk-forward, seed 36, threshold 0.5, E49-C2 shrinkage fitted on earlier dates. Scored on the 13 E53
development quarters (65 rows). Baselines on the same rows: persistence (B1, y_last) and always-majority (the
training majority class at each origin = CLIMATOLOGY >= 0.5; also the hindsight test-set majority).

ADOPTION (fixed before results). A label is eligible only if ALL hold:
 (a) HIGH share of its labelled province-quarters 2024-Q1..2026-Q3 between 30% and 70%;
 (b) E53-A1 balanced accuracy >= 0.75 AND >= persistence balanced accuracy on the same rows;
 (c) AUC >= 0.75;
 (d) H (hunger) stays in the label -> L3 is reported but NOT eligible.
Several eligible -> prefer the longer window (L1 over L2; L0 is the incumbent). None eligible -> keep L0; no tuning.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E56 = Path(__file__).resolve().parents[1]
BACKEND = E56.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e53" / "runner"))
import e53_run as E  # noqa: E402  (E53 data, cond_* inputs, pools, attribution; brings in e50/e49/e48/e36)

X, R, L6, C, np, pd = E.X, E.R, E.L6, E.C, E.np, E.pd
L6.guard32.EXP = E56                                       # writes confined to E56
NAMES, PROVS, GROUPS = E.NAMES, E.PROVS, E.GROUPS
POOL = "E53-A1"
VARIANTS = {"L0": "all", "L1": 8, "L2": 4, "L3": "cross"}
E53_QUARTERS = ["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1",
                "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]


class Data(E.Data):
    def __init__(self, cond, variant: str):
        super().__init__(cond)
        self.variant, self.rule = variant, VARIANTS[variant]
        self._tau = {}

    def tau(self, t):
        if self.rule in ("all", "cross"):                   # L0 served rule (L3: only for H_margin)
            return super().tau(t)
        if t not in self._tau:
            qs_ = [x for x in self.posted_quarters(L6.origin(t)) if C.qk("2021-Q1") <= x <= t - 1][-self.rule:]
            vals = [s for (_p, x), s in self.Sv.items() if x in qs_ and s == s]
            self._tau[t] = float(np.median(vals)) if vals else float("nan")
        return self._tau[t]

    def cross(self, p, q):
        v = [self.Sv.get((c, q)) for c in PROVS]
        if any(s is None or s != s for s in v) or self.Sv.get((p, q)) is None:
            return None
        return int(self.Sv[(p, q)] > float(np.median(v)))

    def label(self, p, target, t):
        if self.rule == "cross":
            return self.cross(p, target)
        s = self.Sv.get((p, target))
        tau = self.tau(t)
        return None if s is None or s != s or tau != tau else int(s > tau)

    def features(self, t, k):
        Xf = super().features(t, k)                         # E53: copy + cond_*; base uses self.tau
        if self.rule == "cross":
            last = Xf["last_label_quarter"].iloc[0]
            lq = C.qk(last) if last else None
            Xf["y_last"] = [np.nan if lq is None or self.cross(p, lq) is None else float(self.cross(p, lq))
                            for p in Xf["province_code"]]
        return Xf

    def training_pairs(self, t, k):
        tr = super().training_pairs(t, k)
        if self.rule == "cross" and not tr.empty:
            ys = [self.cross(p, q) for p, q in zip(tr["province_code"], tr["target_q"])]
            tr = tr.assign(y=ys)
            tr = tr[tr["y"].notna()].astype({"y": int}).reset_index(drop=True)
        return tr


def label_stats(d: Data, dev_rows: pd.DataFrame) -> dict:
    """every labelled province-quarter 2021..2026-Q3, each labelled at its own lead-1 origin (quarter - 1)."""
    rows = []
    for (c, q), s in d.Sv.items():
        if s == s and C.qk("2021-Q1") <= q <= C.qk("2026-Q3"):
            y = d.label(c, q, q - 1)
            if y is not None:
                rows.append({"province": NAMES[c], "quarter": C.qs(q), "y": int(y)})
    la = pd.DataFrame(rows)
    la["yr"] = la["quarter"].str[:4]
    per_q = la.groupby("quarter")["y"].agg(["sum", "count"])
    all5 = per_q[(per_q["count"] == 5) & (per_q["sum"] == 5)].index.tolist()
    late = la[la["quarter"] >= "2024-Q1"]
    return {"n_labelled": int(len(la)), "share_HIGH_all": float(la["y"].mean()),
            "share_HIGH_per_year": {y: {"share": float(g["y"].mean()), "n": int(len(g))} for y, g in la.groupby("yr")},
            "share_HIGH_2024_2026": float(late["y"].mean()), "n_2024_2026": int(len(late)),
            "quarters_all5_HIGH": all5, "n_quarters_all5_HIGH": len(all5), "n_quarters_labelled": int(len(per_q)),
            "dev_rows": int(len(dev_rows)), "dev_LOW_rows": int((dev_rows["y"] == 0).sum()),
            "labels_by_quarter": {q: {r.province: r.y for r in g.itertuples()} for q, g in la.groupby("quarter")}}


def bin_metrics(pred: pd.Series, y: pd.Series) -> dict:
    pred, y = pred.astype(bool), y.astype(int)
    tpr = float((pred & (y == 1)).sum() / max(1, (y == 1).sum()))
    tnr = float((~pred & (y == 0)).sum() / max(1, (y == 0).sum()))
    return {"accuracy": float((pred == y).mean()), "balanced_accuracy": (tpr + tnr) / 2,
            "LOW_caught": int((~pred & (y == 0)).sum())}


def run_variant(name, cond, E31):
    d = Data(cond, name)
    Pr, info = L6.walk_forward(d)
    wf_dates = [C.qk(x) - 1 for x in info["dates"]]
    T = L6.OPERATIONAL_T
    alld = wf_dates + [T]
    labels = {t: {c: int(d.label(c, t + 1, t)) for c in PROVS} for t in wf_dates}
    labels_all = {**labels, T: {c: 0 for c in PROVS}}
    base = {t: float((d.train(t)["y"].sum() + 1) / (len(d.train(t)) + 2)) for t in alld}
    prior_of = {t: L6.eligible_prior_dates(d, t, wf_dates) for t in alld}
    raw, cfg, models = {}, {}, {}
    for t in alld:
        if t == T:
            fs, g = L6.operational_choice(d, Pr, POOL)[0]
        else:
            fs, g = info["selections"][POOL][C.qs(t + 1)]["chosen"].split("x")
        feats = L6.FEATURE_SETS[fs]
        tr, te = d.train(t), d.test(t)
        ptr, pte, m = X.lgbm_arrays(tr, te, feats, g)
        raw[t], cfg[t], models[t] = dict(zip(te["province_code"], pte)), L6.cfg_name(fs, g), (m, feats, te)
    cal, _fb, pa = R.calibrated(raw, labels_all, base, prior_of, "shrink")
    dev = [t for t in wf_dates if C.qs(t + 1) in E53_QUARTERS]
    g = pd.DataFrame([{"t": C.qs(t), "target_quarter": C.qs(t + 1), "province_code": c, "arm": f"{name}-A1",
                       "p": cal[t][c], "p_raw": raw[t][c], "y": labels[t][c]} for t in dev for c in PROVS])
    s = R.summary(g)
    model = {"accuracy": s["accuracy"], "balanced_accuracy": s["balanced_accuracy"], "auc": s["auc"],
             "brier": s["brier"], "LOW_caught": bin_metrics(g["p"] >= 0.5, g["y"])["LOW_caught"],
             "LOW_rows": int((g["y"] == 0).sum()), "n": int(len(g))}
    sel = Pr["target_quarter"].isin([C.qs(t + 1) for t in dev])
    pers = Pr[(Pr["arm"] == "B1_PERSISTENCE") & sel]
    clim = Pr[(Pr["arm"] == "CLIMATOLOGY") & sel]
    sp = R.summary(pers)
    persistence = {"accuracy": sp["accuracy"], "balanced_accuracy": sp["balanced_accuracy"], "auc": sp["auc"],
                   "brier": sp["brier"], "LOW_caught": bin_metrics(pers["p"] >= 0.5, pers["y"])["LOW_caught"]}
    majority_train = bin_metrics(clim["p"] >= 0.5, clim["y"])
    maj = int(g["y"].mean() >= 0.5)
    majority_test = bin_metrics(pd.Series([bool(maj)] * len(g)), g["y"]) | {"class": "HIGH" if maj else "LOW"}
    # Q4 2026 forecast and five-driver shares (E53 mapping and live news-topic allocation)
    m, feats, te = models[T]
    cc = L6.shap_contributions(m, te[feats])
    pool_mag, per = {k: 0.0 for k in GROUPS}, {}
    for i, code in enumerate(te["province_code"]):
        shap = cc.drop(columns="expected_value").iloc[i].to_dict()
        mag, _other, _direct = E.shares(E31, shap, code, C.qs(T))
        per[NAMES[code]] = dict(zip(GROUPS, X.integer_shares([mag[k] for k in GROUPS])))
        for k in GROUPS:
            pool_mag[k] += mag[k]
    q4 = {"index": {"CALABARZON": float(np.mean(list(cal[T].values()))), **{NAMES[c]: float(cal[T][c]) for c in PROVS}},
          "drivers": {"CALABARZON": dict(zip(GROUPS, X.integer_shares([pool_mag[k] for k in GROUPS]))), **per},
          "config": cfg[T], "tau": d.tau(T) if name != "L3" else None,
          "train_rows": int(len(d.train(T))), "train_HIGH_share": float(d.train(T)["y"].mean())}
    st = label_stats(d, g)
    crit = {"a_HIGH_share_2024_2026_30_70": 0.30 <= st["share_HIGH_2024_2026"] <= 0.70,
            "b_bal_ge_0.75_and_ge_persistence": (model["balanced_accuracy"] or 0) >= 0.75
                                                 and (model["balanced_accuracy"] or 0) >= (persistence["balanced_accuracy"] or 0),
            "c_auc_ge_0.75": (model["auc"] or 0) >= 0.75,
            "d_keeps_H": name != "L3"}
    return {"label_stats": st, "walk_forward_dates": info["dates"],
            "missing_dev_quarters": [q for q in E53_QUARTERS if q not in [C.qs(t + 1) for t in dev]],
            "tau_by_target": {C.qs(t + 1): (d.tau(t) if name != "L3" else None) for t in alld},
            "model": model, "persistence": persistence, "always_majority_train": majority_train,
            "always_majority_test": majority_test, "pool_configs": {C.qs(t + 1): cfg[t] for t in alld},
            "shrink_params": {C.qs(t + 1): v for t, v in pa.items()},
            "index_by_target": {C.qs(t + 1): float(np.mean(list(cal[t].values()))) for t in alld},
            "q4_2026": q4, "adoption": {"criteria": crit, "eligible": all(crit.values())}}, g


def main():
    os.chdir(BACKEND)
    E.register()
    E31 = X.live_engine()
    cond = E.build_cond()
    res, frames = {"variants": {}}, []
    for name in VARIANTS:
        print("running", name, flush=True)
        res["variants"][name], g = run_variant(name, cond, E31)
        frames.append(g)
        o = res["variants"][name]
        print(" ", name, {k: round(v, 3) if isinstance(v, float) else v for k, v in o["model"].items()},
              "Q4", round(o["q4_2026"]["index"]["CALABARZON"], 3), flush=True)
    l0 = res["variants"]["L0"]["model"]
    res["L0_reproduces_E53_A1"] = {"accuracy": l0["accuracy"], "balanced_accuracy": l0["balanced_accuracy"],
                                   "auc": l0["auc"], "brier": l0["brier"],
                                   "q4_calabarzon": res["variants"]["L0"]["q4_2026"]["index"]["CALABARZON"]}
    lab0 = res["variants"]["L0"]["label_stats"]["labels_by_quarter"]
    for v, o in res["variants"].items():
        lab = o["label_stats"]["labels_by_quarter"]
        pairs = [(lab[q][p], lab0[q][p]) for q in lab for p in lab[q] if q in lab0 and p in lab0[q]]
        o["label_stats"]["share_labels_differ_from_L0"] = float(np.mean([a != b for a, b in pairs]))
    elig = [v for v in ("L1", "L2") if res["variants"][v]["adoption"]["eligible"]]
    res["adoption"] = {"eligible": elig,
                       "chosen": elig[0] if elig else "none eligible -> keep L0",
                       "rule": "eligible = (a) and (b) and (c) and (d); prefer L1 over L2; none -> keep L0"}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E56 / "runs" / stamp
    run.mkdir(parents=True)
    pd.concat(frames).to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E56 / "E56_results.json", C.clean(res))
    print("RUN", stamp, "eligible", elig, "chosen", res["adoption"]["chosen"])


if __name__ == "__main__":
    main()
