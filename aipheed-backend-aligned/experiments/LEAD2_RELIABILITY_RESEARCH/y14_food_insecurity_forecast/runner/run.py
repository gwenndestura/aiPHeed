"""Y14 (EXPERIMENT_PLAN.md sections 3-6): FIRI-analog, drivers-only, parsimonious logistic and continuous hunger models
vs the hunger-persistence probability H1 for TFI-2 (BL hunger > 11.3 at t+2). Development on 2001-2020 targets with the
frozen gate; then the 17 official FIRI Lead-2 rows (confirmatory only for gate-passers; otherwise descriptive); then the
descriptive domain analysis of the served FIRI v2.
Writes out/dev_rows.csv, out/dev_results.json, out/confirm_rows.csv, out/confirm_results.json, out/firi_domains.json.

    python -B run.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import warnings
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
Y14 = HERE.parent
RES = Y14.parent
EXP = RES.parent
OUT = Y14 / "out"
sys.path.insert(0, str(RES / "common"))
sys.path.insert(0, str(EXP / "FIRI_LEAD2_FEASIBILITY" / "runner"))
import p2lib as P  # noqa: E402
import hmodels as HM  # noqa: E402

R = P.R
SEED, B = 2036, 5000
CONT = ("A2", "A3", "C2", "C3", "C4", "E1")
DOMS = {"A": ("A2", "A3"), "C": ("C1", "C2", "C3", "C4"), "E": ("E1", "E2"), "H": ("H1",), "V": ("V1",)}
DEV_FIRST, DEV_LAST = R.qi("2001-Q1"), R.qi("2020-Q4")


def plan_ok():
    want = (HERE / "PLAN_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((Y14 / "EXPERIMENT_PLAN.md").read_bytes()).hexdigest() == want, "plan changed after freezing"


# ================================================================================================ inputs
def frame(ind: pd.DataFrame | None = None) -> pd.DataFrame:
    d = (pd.read_csv(OUT / "indicators.csv") if ind is None else ind.copy()).set_index("t")
    obs = R.observed()
    rr = R.rounds()
    pub = rr[rr["area"] == "BL"].groupby("q")["published"].max()
    # FIRI v2 percentile scoring against strictly earlier origins (>= 8)
    for k in CONT:
        sc = []
        for t in d.index:
            prior = d.loc[d.index < t, k].dropna().to_numpy()
            x = d.loc[t, k]
            if pd.isna(x) or len(prior) < 8:
                sc.append(np.nan)
            else:
                sc.append(float(((prior < x).sum() + 0.5 * (prior == x).sum()) / len(prior)))
        d[f"s_{k}"] = sc
    for k in ("C1", "H1", "V1", "E2"):
        d[f"s_{k}"] = d[k].clip(0, 1)
    for dm, ks in DOMS.items():
        d[f"dom_{dm}"] = d[[f"s_{k}" for k in ks]].mean(1, skipna=True)

    def firi(row, doms):
        av = [row[f"dom_{x}"] for x in doms if pd.notna(row[f"dom_{x}"])]
        return float(np.mean(av)) if len(av) >= 4 else np.nan
    d["F1"] = d.apply(lambda r: firi(r, "ACEHV"), axis=1)
    d["F2"] = d.apply(lambda r: firi(r, "ACEV"), axis=1)
    d["H_target"] = [obs.get(("BL", t + 2), np.nan) for t in d.index]
    d["y"] = (d["H_target"] > R.H_LINE).astype(float).where(d["H_target"].notna())
    d["pub_target"] = [pub.get(t + 2, pd.NaT) for t in d.index]
    d["PERSIST"] = (d["H_last"] > R.H_LINE).astype(float).where(d["H_last"].notna())
    d["m_known"] = [float(np.mean(list(R.known("BL", R.issue(t)).values()))) if R.known("BL", R.issue(t)) else np.nan
                    for t in d.index]
    clim = []
    for t in d.index:
        iss = R.issue(t)
        kq = [q for q, p in pub.items() if p < iss]
        clim.append(float(np.mean([obs[("BL", q)] > R.H_LINE for q in kq])) if kq else np.nan)
    d["CLIM"] = clim
    return d


# ================================================================================================ models
def z(p):
    return np.clip(norm.ppf(np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)), -4, 4)


def fit_predict(d: pd.DataFrame, t: int) -> dict:
    iss = R.issue(t)
    tr = d[(d.index < t) & d["y"].notna() & (d["pub_target"] < iss) & d["H1"].notna()].copy()
    x0 = d.loc[t]
    out = {"trainRows": len(tr)}
    cols = ["dom_A", "dom_C", "dom_E"]
    # in-fold mean; 0.5 (the neutral percentile) when the fold has no value yet (E before 2006-Q3). Disclosed deviation.
    mu = tr[cols].mean().fillna(0.5)
    X = np.column_stack([z(tr["H1"]), tr[cols].fillna(mu).to_numpy()])
    xx = np.r_[z([x0["H1"]]), x0[cols].fillna(mu).to_numpy(float)].reshape(1, -1)
    y = tr["y"].to_numpy(int)
    if len(tr) >= 30 and y.sum() >= 5 and (1 - y).sum() >= 5:
        out["M1"] = float(LogisticRegression(C=1.0, max_iter=3000).fit(X, y).predict_proba(xx)[0, 1])
        out["M1_0"] = float(LogisticRegression(C=1.0, max_iter=3000).fit(X[:, :1], y).predict_proba(xx[:, :1])[0, 1])
        out["M1_fallback"] = 0
    else:
        out["M1"] = out["M1_0"] = float(x0["H1"])
        out["M1_fallback"] = 1
    if len(tr) >= 30:
        dy = (tr["H_target"] - tr["H_last"]).to_numpy(float)
        dev = (tr["H_last"] - tr["m_known"]).to_numpy(float)
        for name, A, a in (("M2", np.column_stack([np.ones(len(tr)), dev, tr[cols].fillna(mu).to_numpy()]),
                            np.r_[1.0, x0["H_last"] - x0["m_known"], x0[cols].fillna(mu).to_numpy(float)]),
                           ("M2_0", np.column_stack([np.ones(len(tr)), dev]), np.r_[1.0, x0["H_last"] - x0["m_known"]])):
            b = np.linalg.lstsq(A, dy, rcond=None)[0]
            sig = max(math.sqrt(float(np.mean((dy - A @ b) ** 2))), 0.5)
            mu_h = x0["H_last"] + float(a @ b)
            out[name], out[f"{name}_mu"] = float(norm.cdf((mu_h - R.H_LINE) / sig)), mu_h
        out["M2_fallback"] = 0
    else:
        out["M2"] = out["M2_0"] = float(x0["H1"])
        out["M2_mu"] = out["M2_0_mu"] = float(x0["H_last"])
        out["M2_fallback"] = 1
    out["KAL"] = HM.kalman("BL", int(t), 2, tuple(R.AREAS))
    return out


# ================================================================================================ evaluation
def metrics(y, p, mu=None, lvl=None) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= .5).astype(int)
    tp, fp, fn, tn = [int(((yh == a) & (y == b)).sum()) for a, b in ((1, 1), (1, 0), (0, 1), (0, 0))]
    r = lambda a, b: a / b if b else None  # noqa: E731
    rec, spec, prec = r(tp, tp + fn), r(tn, tn + fp), r(tp, tp + fp)
    out = {"n": len(y), "pos": int(y.sum()), "TP": tp, "FP": fp, "FN": fn, "TN": tn, "accuracy": (tp + tn) / len(y),
           "balanced": (rec + spec) / 2 if rec is not None and spec is not None else None, "precision": prec, "recall": rec,
           "specificity": spec, "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0,
           "auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else None, "brier": float(np.mean((p - y) ** 2))}
    if mu is not None:
        out["mae"] = float(np.mean(np.abs(np.asarray(mu, float) - np.asarray(lvl, float))))
    return out


def boot(d, a, b, block=1):
    l = ((d[a] - d["y"]) ** 2 - (d[b] - d["y"]) ** 2).to_numpy()
    n = len(l)
    rng = np.random.default_rng(SEED)
    if block == 1:
        bs = l[rng.integers(0, n, size=(B, n))].mean(1)
    else:
        nb = math.ceil(n / block)
        st = rng.integers(0, n - block + 1, size=(B, nb))
        bs = l[(st[:, :, None] + np.arange(block)).reshape(B, -1)[:, :n]].mean(1)
    return {"diff": float(l.mean()), "p_one_sided": float(np.mean(bs >= 0))}


def holm(ps: dict) -> dict:
    out, run = {}, 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = run
    return out


def calib(y, p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    m = LogisticRegression(C=1e6, max_iter=3000).fit(np.log(p / (1 - p)).reshape(-1, 1), np.asarray(y, int))
    return {"slope": round(float(m.coef_[0, 0]), 3), "intercept": round(float(m.intercept_[0]), 3)}


def leading(d: pd.DataFrame) -> dict:
    d = d.assign(dH=d["H_target"] - d["H_last"])
    out = {}
    rng = np.random.default_rng(SEED)
    for k in ("A2", "A3", "C1", "C2", "C3", "C4", "E1", "dom_A", "dom_C", "dom_E"):
        conc = d[k].reindex(d.index + 2).to_numpy()
        g = pd.DataFrame({"x": d[k].to_numpy(), "c": conc, "dH": d["dH"].to_numpy()}).dropna(subset=["dH"])
        res = {}
        for lab, col in (("leading", "x"), ("concurrent", "c")):
            h = g.dropna(subset=[col])
            v = [h.iloc[rng.integers(0, len(h), len(h))][[col, "dH"]].corr().iloc[0, 1] for _ in range(1000)]
            res[lab] = {"r": round(float(h[col].corr(h["dH"])), 3), "CI90": [round(float(np.nanquantile(v, .05)), 3),
                                                                           round(float(np.nanquantile(v, .95)), 3)], "n": len(h)}
        out[k] = res
    return out


CANDS = ("F1", "F2", "M1", "M2")
ALLC = ("PERSIST", "CLIM", "H1", "F1", "F2", "M1", "M1_0", "M2", "M2_0", "KAL")


def main():
    plan_ok()
    d = frame()
    preds = []
    for t in d.index:
        if t + 2 < DEV_FIRST or pd.isna(d.loc[t, "H1"]):
            continue
        preds.append({"t": t, **fit_predict(d, t)})
    p = pd.DataFrame(preds).set_index("t")
    d = d.join(p)
    d["target"] = [R.qs(t + 2) for t in d.index]
    dev = d[(d.index + 2 >= DEV_FIRST) & (d.index + 2 <= DEV_LAST) & d["y"].notna()].dropna(subset=list(ALLC))
    res = {"rows": len(dev), "period": f"{dev['target'].min()}..{dev['target'].max()}", "prevalence": float(dev["y"].mean()),
           "fallbackRows": {"M1": int(dev["M1_fallback"].sum()), "M2": int(dev["M2_fallback"].sum())},
           "domainsAvailable_F1": dev[[f"dom_{x}" for x in "ACEHV"]].notna().sum(1).value_counts().to_dict()}
    for c in ALLC:
        res[c] = metrics(dev["y"], dev[c], dev[f"{c}_mu"] if f"{c}_mu" in dev else (dev["H_last"] if c in ("H1", "PERSIST") else None),
                         dev["H_target"])
    res["vsH1"] = {c: {"iid": boot(dev, c, "H1"), "block4": boot(dev, c, "H1", 4)} for c in ALLC if c != "H1"}
    hp = holm({c: res["vsH1"][c]["iid"]["p_one_sided"] for c in CANDS})
    g3 = {"F1": res["vsH1"]["F1"]["iid"]["diff"] < 0, "F2": boot(dev, "F2", "CLIM"), "M1": boot(dev, "M1", "M1_0"),
          "M2": boot(dev, "M2", "M2_0")}
    gate = {}
    for c in CANDS:
        g3c = g3[c] if isinstance(g3[c], bool) else (g3[c]["diff"] < 0 and g3[c]["p_one_sided"] < 0.10)
        gate[c] = {"G1": res["vsH1"][c]["iid"]["diff"] < 0 and hp[c] < 0.10,
                   "G2": (res[c]["balanced"] or 0) >= (res["H1"]["balanced"] or 0), "G3": bool(g3c)}
        gate[c]["passes"] = all(gate[c].values())
    res["holm"], res["G3_tests"], res["gate"] = hp, {k: v for k, v in g3.items() if not isinstance(v, bool)}, gate
    res["passedGate"] = [c for c in CANDS if gate[c]["passes"]]
    res["calibration"] = {c: calib(dev["y"], dev[c]) for c in ("H1", "M1", "M2", "KAL")}
    res["leadingTest"] = leading(d[(d.index + 2 >= DEV_FIRST) & (d.index + 2 <= DEV_LAST)])
    OUT.mkdir(exist_ok=True)
    (OUT / "dev_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    dev.reset_index().to_csv(OUT / "dev_rows.csv", index=False, lineterminator="\n", float_format="%.5f")

    # ---------------------------------------------------------------- 2021-2026: the 17 official FIRI rows
    import score_firi_l2 as F
    fr = pd.read_csv(EXP / "FIRI_LEAD2_FEASIBILITY" / "out" / "firi_l2_rows.csv")
    fr["q"] = fr["target"].map(R.qi)
    fr["t"] = fr["q"] - 2
    fr["ALWAYS-HIGH"], fr["ALWAYS-LOW"] = 1.0, 0.0
    cr = {"status": "confirmatory for gate-passers " + str(res["passedGate"]) if res["passedGate"] else
          "DESCRIPTIVE ONLY: no candidate passed the development gate; nothing is selected from these rows"}
    # served FIRI v2 is the stored "F2" column of the FIRI rows; Y14's drivers-only candidate is also called F2, so the
    # two are keyed explicitly (served_* vs Y14_*)
    for name, src in [("served_FIRI_v2", "served"), ("H1_firi_rows", "H1row")] + \
                     [(f"Y14_{c}", c) for c in CANDS + ("H1", "M1_0", "M2_0", "KAL")]:
        g = fr.copy()
        vals = g["F2"] if src == "served" else g["H1"] if src == "H1row" else g["t"].map(d[src])
        g["F2"] = vals.to_numpy()
        if g["F2"].isna().any():
            cr[name] = {"undefinedRows": int(g["F2"].isna().sum())}
            continue
        r = F.rules(g)["rules"]
        cr[name] = {"metrics": metrics(g["y"], g["F2"]), "failed": [k.split()[0] for k, v in r.items() if not v["pass"]],
                    "passesAll": all(v["pass"] for v in r.values()), "rules": r}
    (OUT / "confirm_results.json").write_text(json.dumps(cr, indent=1, default=str), encoding="utf-8")
    fr.assign(**{f"Y14_{c}": fr["t"].map(d[c]) for c in CANDS + ("M1_0", "M2_0", "KAL")}).to_csv(
        OUT / "confirm_rows.csv", index=False, lineterminator="\n", float_format="%.4f")

    # ---------------------------------------------------------------- served FIRI v2 by domain (descriptive)
    h = pd.read_csv(R.ROOT / "backend" / "data" / "thesis" / "firi2_history.csv")
    h = h[h["kind"] == "backtest"] if "kind" in h else h
    reg = h.groupby("target")[[c for c in h.columns if c.startswith("dom_")] + ["FIRI"]].mean()
    yv = fr.set_index("target")["y"]
    reg = reg[reg.index.isin(yv.index)]
    dom = {c: {"rows": int(reg[c].notna().sum()),
               "auc": round(float(roc_auc_score(yv[reg[c].dropna().index], reg[c].dropna())), 3)
               if reg[c].notna().sum() > 3 and yv[reg[c].dropna().index].nunique() == 2 else None,
               "meanWhenHIGH": round(float(reg[c][yv[reg.index] == 1].mean()), 3) if reg[c].notna().any() else None,
               "meanWhenLOW": round(float(reg[c][yv[reg.index] == 0].mean()), 3) if reg[c].notna().any() else None}
           for c in reg.columns}
    (OUT / "firi_domains.json").write_text(json.dumps(dom, indent=1), encoding="utf-8")

    # ---------------------------------------------------------------- print
    print({k: res[k] for k in ("rows", "period", "prevalence", "fallbackRows", "domainsAvailable_F1")})
    for c in ALLC:
        m = res[c]
        tail = f" vsH1 {res['vsH1'][c]['iid']['diff']:+.4f} p {res['vsH1'][c]['iid']['p_one_sided']:.3f} (blk {res['vsH1'][c]['block4']['p_one_sided']:.3f})" if c != "H1" else ""
        print(f"{c:8s} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} spec {m['specificity'] or 0:.2f} "
              f"F1 {m['f1']:.3f} AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f}" + (f" MAE {m['mae']:.2f}" if "mae" in m else "") + tail)
    print("holm", hp)
    print("G3 tests", res["G3_tests"])
    print("gate", gate, "passed:", res["passedGate"])
    print("calibration", res["calibration"])
    for k, v in res["leadingTest"].items():
        print(f"lead {k:6s} leading r {v['leading']['r']:+.3f} {v['leading']['CI90']} n {v['leading']['n']} | concurrent r {v['concurrent']['r']:+.3f} {v['concurrent']['CI90']}")
    print("CONFIRM:", cr["status"])
    for k, v in cr.items():
        if isinstance(v, dict) and "metrics" in v:
            m = v["metrics"]
            print(f"  {k:16s} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} "
                  f"AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f} CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} fails {v['failed']}")
        elif isinstance(v, dict):
            print(" ", k, v)
    print("served FIRI v2 domains (2021+, descriptive):", json.dumps(dom))


if __name__ == "__main__":
    main()
