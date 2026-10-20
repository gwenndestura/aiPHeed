"""E51: a stricter HIGH -- trailing PERCENTILE threshold instead of the median (lead 1). Experiment only.

    python -B backend/experiments/e51/runner/e51_run.py  -> backend/experiments/e51/E51_results.json

S1 = H + 2D is unchanged. tau_q(t) = q-th percentile of the pooled S1 of quarters 2021-Q1..t-1 whose SWS rounds were
ALL posted before the origin O(t) (the served rule's publication filter); only the percentile changes:
  P50  q = 0.50  (the served median; must reproduce E49-C2: acc 0.846, Brier 0.151, Q4 2026 0.778)
  P67  q = 2/3
  P75  q = 0.75
tau also enters H_margin (= H_last - tau) and y_last (= last published S1 > tau); both use the variant's tau (as E45).

Arms per variant (E36 walk-forward, nested rule, seed 36, threshold 0.5; test dates = the origins E36 can score):
  A  served pipeline: E48-A1 pool (COMPACT_T5/COMB_T5 x G1/G4/G3/G2) + E49-C2 shrinkage (fitted on earlier dates)
  B  E50-R4 paper blend: 0.4 x regularised monotone LightGBM (E50-R1 pool) + 0.4 x B3 government LR + 0.2 x LR on
     trigger proportions (constant inputs dropped); C2 shrinkage only where it lowers earlier-date Brier (a=1 otherwise)

ADOPTION (fixed before results), for P67 and P75 only (P50 is the reproduction):
  a (variant, arm) is acceptable only if ALL of
    1. HIGH share of all labelled province-quarters 2021-Q3..2026-Q3 between 25% and 60%
    2. HIGH share of the 2024-Q1..2026-Q3 labelled province-quarters <= 75%   (the index can move again)
    3. AUC >= 0.80
    4. balanced accuracy >= 0.75
    5. Brier <= persistence's Brier on the same labels and rows
    6. Brier skill score vs climatology (training base rate) > 0
    7. no test p >= 0.99
  several acceptable -> highest Brier skill score vs climatology (labels differ between variants, so raw Brier is not
  comparable); within 0.01 -> P75 before P67, then arm B (paper) before A.
  none acceptable -> keep E49-C2 (median) and say so.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E51 = Path(__file__).resolve().parents[1]
BACKEND = E51.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e50" / "runner"))
import e50_run as X  # noqa: E402  (E50 helpers: pools, blend, panel; brings in e49_run / e48_lib / e36_lib)

R, L, L6, C, np, pd = X.R, X.L, X.L6, X.C, X.np, X.pd
L6.guard32.EXP = E51
NAMES, PROVS = X.NAMES, X.PROVS
VARIANTS = {"P50": 0.50, "P67": 2 / 3, "P75": 0.75}


class Data(L.Data):
    """E48 data (E36 features + trigger shares) with tau = q-th percentile of the published pooled S1."""

    def __init__(self, q: float):
        super().__init__(paper=False)
        self.q = q
        self._tau = {}

    def tau(self, t):
        if t not in self._tau:
            o = L6.origin(t)
            qs_ = [x for x in self.posted_quarters(o) if C.qk("2021-Q1") <= x <= t - 1]
            vals = [s for (_p, x), s in self.Sv.items() if x in qs_ and s == s]
            self._tau[t] = float(np.quantile(vals, self.q)) if vals else float("nan")
        return self._tau[t]

    def label(self, p, target, t):
        s = self.Sv.get((p, target))
        tau = self.tau(t)
        return None if s is None or s != s or tau != tau else int(s > tau)

    def features(self, t, k):
        Xf = super().features(t, k).copy()
        Xf["tau"] = self.tau(t)
        Xf["H_margin"] = Xf["H_last"] - Xf["tau"]
        last = Xf["last_label_quarter"].iloc[0]
        if last:
            lq = C.qk(last)
            Xf["y_last"] = [float(self.Sv[(p, lq)] > tv) if (p, lq) in self.Sv and self.Sv[(p, lq)] == self.Sv[(p, lq)]
                            else np.nan for p, tv in zip(Xf["province_code"], Xf["tau"])]
        return Xf


def run_variant(name, q, E31):
    d = Data(q)
    Pr, info = L6.walk_forward(d)
    dates = [C.qk(x) - 1 for x in info["dates"]]
    T = L6.OPERATIONAL_T
    alld = dates + [T]
    labels = {t: {c: int(d.label(c, t + 1, t)) for c in PROVS} for t in dates}
    labels_all = {**labels, T: {c: 0 for c in PROVS}}
    base = {t: float((d.train(t)["y"].sum() + 1) / (len(d.train(t)) + 2)) for t in alld}
    prior_of = {t: L6.eligible_prior_dates(d, t, dates) for t in alld}

    def chosen(pool, t):
        if t == T:
            return L6.operational_choice(d, Pr, pool)[0]
        fs, g = info["selections"][pool][C.qs(t + 1)]["chosen"].split("x")
        return fs, g

    raw = {"A": {}, "B": {}}
    trn = {"A": {}, "B": {}}
    q4m = {}
    for t in alld:
        tr, te = d.train(t), d.test(t)
        codes = list(te["province_code"])
        fsA, gA = chosen("E48-T5", t)
        ptrA, pteA, mA = X.lgbm_arrays(tr, te, L6.FEATURE_SETS[fsA], gA)
        fs1, g1 = chosen("E50-R1", t)
        ptr1, pte1, m1 = X.lgbm_arrays(tr, te, L6.FEATURE_SETS[fs1], g1)
        ptr3, pte3, lr3 = X.lr_arrays(tr, te, L6.GOV)
        ptrT, pteT, lrT = X.lr_arrays(tr, te, X.TRIG_LR)
        raw["A"][t], trn["A"][t] = dict(zip(codes, pteA)), ptrA
        raw["B"][t] = {c: 0.4 * a + 0.4 * b + 0.2 * e for c, a, b, e in zip(codes, pte1, pte3, pteT)}
        trn["B"][t] = 0.4 * ptr1 + 0.4 * ptr3 + 0.2 * ptrT
        if t == T:
            q4m = {"A": (mA, L6.FEATURE_SETS[fsA], L6.cfg_name(fsA, gA)), "R1": (m1, L6.FEATURE_SETS[fs1], L6.cfg_name(fs1, g1)),
                   "lr3": lr3, "lrT": lrT, "te": te}
    out = {"tau_by_target": {C.qs(t + 1): d.tau(t) for t in alld}, "test_quarters": info["dates"],
           "n_test_rows": 5 * len(dates), "arms": {}}
    # labels on every labelled province-quarter (label at its own lead-1 origin)
    lab_all = []
    for (c, qq), s in d.Sv.items():
        if s == s and qq >= C.qk("2021-Q3"):
            y = d.label(c, qq, qq - 1)
            if y is not None:
                lab_all.append({"province": NAMES[c], "quarter": C.qs(qq), "y": y})
    la = pd.DataFrame(lab_all)
    la["yr"] = la["quarter"].str[:4]
    out["base_rate"] = {"all": float(la["y"].mean()), "n": int(len(la)),
                        "2024_2026": float(la[la["quarter"] >= "2024-Q1"]["y"].mean()),
                        "per_year": {y: float(g["y"].mean()) for y, g in la.groupby("yr")}}
    out["labels_all"] = lab_all
    pers = Pr[Pr["arm"] == "B1_PERSISTENCE"]
    clim = Pr[Pr["arm"] == "CLIMATOLOGY"]
    out["persistence"] = R.summary(pers)
    out["climatology_brier"] = float(((clim["p"] - clim["y"]) ** 2).mean())
    for arm in ("A", "B"):
        cal, _fb, pa = R.calibrated(raw[arm], labels_all, base, prior_of, "shrink")
        rows = [{"t": C.qs(t), "target_quarter": C.qs(t + 1), "province_code": c, "arm": f"{name}-{arm}",
                 "p": cal[t][c], "p_raw": raw[arm][t][c], "y": labels[t][c]} for t in dates for c in PROVS]
        g = pd.DataFrame(rows)
        s = R.summary(g)
        trT = d.train(T)
        tm = X.train_metrics(X.shrink(trn[arm][T], pa.get(T)), trT["y"])
        # attribution at Q4 2026 (arm A exact TreeSHAP; arm B weighted component attributions, approximate)
        te = q4m["te"]
        if arm == "A":
            m, feats, _ = q4m["A"]
            cc = L6.shap_contributions(m, te[feats])
            ev = float(cc["expected_value"].iloc[0])
            shap = {c: cc.drop(columns="expected_value").iloc[i].to_dict() for i, c in enumerate(te["province_code"])}
        else:
            m, feats, _ = q4m["R1"]
            cc = L6.shap_contributions(m, te[feats])
            ev = 0.4 * float(cc["expected_value"].iloc[0]) + 0.4 * q4m["lr3"]["intercept"] + 0.2 * q4m["lrT"]["intercept"]
            shap = {}
            for i, c in enumerate(te["province_code"]):
                acc = {f: 0.4 * v for f, v in cc.drop(columns="expected_value").iloc[i].to_dict().items()}
                for f, v in q4m["lr3"]["shap"][i].items():
                    acc[f] = acc.get(f, 0.0) + 0.4 * v
                for f, v in q4m["lrT"]["shap"][i].items():
                    acc[f] = acc.get(f, 0.0) + 0.2 * v
                shap[c] = acc
        bss = 1 - s["brier"] / out["climatology_brier"]
        o = {"metrics": {k: s[k] for k in ("accuracy", "accuracy_ci95", "balanced_accuracy", "auc", "brier", "log_loss",
                                            "max_p", "mean_p", "reliability_5bin", "confident_mistakes")},
             "brier_skill_vs_climatology": bss, "n_test_p_ge_0.99": int((g["p"] >= 0.99).sum()),
             "n_test_p_ge_0.95": int((g["p"] >= 0.95).sum()), "train_Q4_origin": tm,
             "shap_expected_value_logodds": ev, "train_label_rate_Q4_origin": float(trT["y"].mean()),
             "q4_config": q4m["A"][2] if arm == "A" else f"0.4*{q4m['R1'][2]} + 0.4*B3 + 0.2*LR{q4m['lrT']['features']}",
             "shrink_params": {C.qs(t + 1): v for t, v in pa.items()},
             "index": {C.qs(t + 1): {"CALABARZON": float(np.mean(list(cal[t].values()))),
                                     **{NAMES[c]: float(cal[t][c]) for c in PROVS}} for t in alld},
             "observed_share_HIGH": {C.qs(t + 1): float(np.mean(list(labels[t].values()))) for t in dates},
             "drivers_q4_2026": X.panel(E31, shap, C.qs(T)),
             "predictions": rows}
        if name != "P50":
            crit = {"base_rate_25_60": 0.25 <= out["base_rate"]["all"] <= 0.60,
                    "base_rate_2024_2026_le_75": out["base_rate"]["2024_2026"] <= 0.75,
                    "auc_ge_0.80": (s["auc"] or 0) >= 0.80,
                    "balanced_accuracy_ge_0.75": (s["balanced_accuracy"] or 0) >= 0.75,
                    "brier_le_persistence": s["brier"] <= out["persistence"]["brier"] + 1e-12,
                    "brier_skill_gt_0": bss > 0,
                    "no_test_p_ge_0.99": o["n_test_p_ge_0.99"] == 0}
            o["adoption"] = {"criteria": crit, "acceptable": all(crit.values())}
        out["arms"][arm] = o
    return out


def main():
    os.chdir(BACKEND)
    X.register()
    E31 = X.live_engine()
    res = {"variants": {}}
    for name, q in VARIANTS.items():
        print("running", name, flush=True)
        res["variants"][name] = run_variant(name, q, E31)
    lab0 = {(r["province"], r["quarter"]): r["y"] for r in res["variants"]["P50"]["labels_all"]}
    for v, o in res["variants"].items():
        lab = {(r["province"], r["quarter"]): r["y"] for r in o.pop("labels_all")}
        o["pct_labels_differ_from_P50"] = float(np.mean([lab[k] != lab0[k] for k in lab if k in lab0]))
    ok = [(v, a) for v in ("P67", "P75") for a in ("A", "B") if res["variants"][v]["arms"][a]["adoption"]["acceptable"]]
    pick = None
    if ok:
        bss = {k: res["variants"][k[0]]["arms"][k[1]]["brier_skill_vs_climatology"] for k in ok}
        best = max(bss.values())
        near = [k for k in ok if bss[k] >= best - 0.01]
        pref = [("P75", "B"), ("P75", "A"), ("P67", "B"), ("P67", "A")]
        pick = next(k for k in pref if k in near)
    res["adoption"] = {"acceptable": [f"{v}-{a}" for v, a in ok],
                       "chosen": f"{pick[0]}-{pick[1]}" if pick else "keep E49-C2 (median)"}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E51 / "runs" / stamp
    run.mkdir(parents=True)
    preds = [r for o in res["variants"].values() for a in o["arms"].values() for r in a.pop("predictions")]
    pd.DataFrame(preds).to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E51 / "E51_results.json", C.clean(res))
    print("RUN", stamp, "acceptable", res["adoption"]["acceptable"], "chosen", res["adoption"]["chosen"])


if __name__ == "__main__":
    main()
