"""
E165 AUTO-FINAL, per docs/e165/PROTOCOL.md (fixed before results). Evaluated once.

    python -m app.e165.final eval | live
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest, norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e162 import rank as R2
from app.e163 import model as C
from app.e164 import auto as A4
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e165" / "out"
GNT = list(Pv.GNT_COLS)
NEWS = [c for c in GNT if c in Pv.NEWS_ALL]
NAT = pd.read_csv(D / "e163" / "out" / "group_audit.csv").query("granularity == 'national/constant'")["column"].tolist()
G5 = ["market", "climate", "employment", "remittance", "poverty"]
TRIG = [c for c in GNT if C.gmap(c) is not None]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def fs_for(drop=()):
    return {"GOV": [c for c in GNT if c not in NEWS and c not in drop], "FULL": [c for c in GNT if c not in drop]}


def soft_platt(x, q):
    X = np.concatenate([x, x]).reshape(-1, 1)
    yy = np.concatenate([np.ones(len(x)), np.zeros(len(x))])
    w = np.concatenate([q, 1 - q])
    return LogisticRegression(C=1.0).fit(X, yy, sample_weight=w)


def run_final(tr, te, AN, anchors=("H", "RP", "OH", "RSS"), drop=()):
    FS = fs_for(drop)
    tr = tr.reset_index(drop=True)
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfgs = [(a, "NONE", None) for a in anchors] + [(a, l, f) for a in anchors for l in A4.LEARNERS for f in FS]
    best = None
    for a, l, f in cfgs:
        atr = AN[a][0]
        if l == "NONE":
            oof = atr.copy()
        else:
            oof = np.zeros(len(tr))
            for i_tr, i_te in folds:
                oof[i_te] = atr[i_te] + A4.LEARNERS[l](FS[f]).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        sd, _ = A4.scale(y - oof, gap, gap)
        cand = {"id": norm.cdf(oof / sd)}
        lin = np.zeros(len(tr))
        pl = np.zeros(len(tr))
        for i_tr, i_te in folds:
            Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
            ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
            lin[i_te] = ab[0] + ab[1] * oof[i_te]
            pl[i_te] = soft_platt(oof[i_tr], q[i_tr]).predict_proba(oof[i_te].reshape(-1, 1))[:, 1]
        sdl, _ = A4.scale(y - lin, gap, gap)
        cand["lin"], cand["platt"] = norm.cdf(lin / sdl), pl
        for c, p in cand.items():
            b = float(np.mean((p - q) ** 2))
            if best is None or b < best["brier"]:
                best = {"brier": b, "cfg": (a, l, f), "cal": c, "oof": oof, "lin": lin, "p_oof": p}
    a, l, f = best["cfg"]
    atr, ate = AN[a]
    mu = ate if l == "NONE" else ate + A4.LEARNERS[l](FS[f]).fit(tr.assign(e=y - atr)).predict(te)
    oof = best["oof"]
    if best["cal"] == "lin":
        Z = np.column_stack([np.ones(len(tr)), oof]) * np.sqrt(w)[:, None]
        ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
        mu = ab[0] + ab[1] * mu
        sd, half = A4.scale(y - best["lin"], gap, te["gap_q"].values)
        p = norm.cdf(mu / sd)
    else:
        sd, half = A4.scale(y - oof, gap, te["gap_q"].values)
        p = soft_platt(oof, q).predict_proba(mu.reshape(-1, 1))[:, 1] if best["cal"] == "platt" else norm.cdf(mu / sd)
    yh = (y >= 0).astype(int)
    po = best["p_oof"]
    ts = np.unique(np.round(po, 3))
    j = [(np.mean(po[yh == 1] >= t) if yh.any() else 0) - (np.mean(po[yh == 0] >= t) if (1 - yh).any() else 0) for t in ts]
    thr = float(ts[int(np.argmax(j))]) if len(ts) else 0.5
    return mu, p, half, sd, f"{a}|{l}|{f or '-'}|{best['cal']}", thr


def task(survey, lead, H, mode):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if not rel:
        return None
    if mode == "corrupt":
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    AN = A4.anchors(S, P, tr, te)
    kw = {}
    if mode == "SH":
        kw["anchors"] = ("H",)
    elif mode == "nonews":
        kw["drop"] = tuple(NEWS)
    elif mode == "nonat":
        kw["drop"] = tuple(NAT)
    elif mode.startswith("shuf_"):
        _, g, sd_ = mode.split("_")
        cols = TRIG if g == "all" else [c for c in GNT if C.gmap(c) == g]
        tr, te = C.shuffle_cols(tr, cols, int(sd_)), C.shuffle_cols(te, cols, int(sd_))
    mu, p, half, sd, tag, thr = run_final(tr, te, AN, **kw)
    out = te[["key", "survey", "lead"]].copy()
    out["mode"], out["mu"], out["p"], out["half"], out["cfg"], out["thr_youden"] = mode, mu, p, half, tag, thr
    return out


def prob_cal(x, a, rng, n=2000):
    p = np.clip(x[a].values, 1e-4, 1 - 1e-4)
    z, yv = np.log(p / (1 - p)), x["y_high"].values
    def fit(ii):
        if len(np.unique(yv[ii])) < 2:
            return np.nan, np.nan
        m = LogisticRegression(C=1e6).fit(z[ii].reshape(-1, 1), yv[ii])
        return float(m.coef_[0, 0]), float(m.intercept_[0])
    s0, i0 = fit(np.arange(len(x)))
    regs = list(x.groupby("region").indices.values())
    bs = [fit(np.concatenate([regs[j] for j in rng.integers(0, len(regs), len(regs))]))[0] for _ in range(n)]
    bs = [b for b in bs if b == b]
    return {"slope": round(s0, 3), "intercept": round(i0, 3), "slope_ci95": [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]}


def evaluate():
    OUT.mkdir(parents=True, exist_ok=True)
    H = E154.income()
    modes1 = ["main", "SH", "nonews", "nonat", "corrupt"] + [f"shuf_all_{s}" for s in (1, 2, 3)] + [f"shuf_{g}_{s}" for g in G5 for s in (1, 2, 3)]
    jobs = [(s, 1, m) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for m in modes1] + [(s, 2, "main") for s in ("ENNS2018", "ENNS2019", "ENNS2021")]
    if (OUT / "all_rows.csv").exists() and "--rerun" not in sys.argv:
        Al = pd.read_csv(OUT / "all_rows.csv")          # analysis only; the runs are not repeated
    else:
        R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, m) for s, h, m in jobs) if x is not None]
        Al = pd.concat(R, ignore_index=True)
        Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    k = ["key", "survey", "lead"]
    G = pd.read_csv(D / "e164" / "out" / "oof.csv")
    res = {"mcnemar": {}, "leads": {}}
    for L in (1, 2):
        x = G[G["lead"] == L].reset_index(drop=True)
        mm = Al[(Al["lead"] == L) & (Al["mode"] == "main")][k + ["mu", "p", "half", "cfg", "thr_youden"]].rename(columns={"mu": "mu_FINAL", "p": "FINAL", "half": "half_FINAL", "cfg": "cfg_FINAL"})
        x = x.merge(mm, on=k)
        assert len(x) == 72, len(x)
        if L == 1:
            for m in [m for m in modes1 if m != "main"]:
                v = Al[(Al["lead"] == 1) & (Al["mode"] == m)][k + ["mu", "p"]].rename(columns={"mu": f"mu_{m}", "p": m})
                x = x.merge(v, on=k)
            x["SHUF_ALL"] = x[[f"shuf_all_{s}" for s in (1, 2, 3)]].mean(axis=1)
            for g in G5:
                x[f"SHUF_{g}"] = x[[f"shuf_{g}_{s}" for s in (1, 2, 3)]].mean(axis=1)
            x1 = x
        rng = np.random.default_rng(165)
        arms = ["PERS", "E158", "AUTO", "FINAL"]
        cm = {}
        for a in arms:
            m_ = C.cls_metrics(x, a, rng)
            yv, pv = x["y_high"].values == 1, x[a].values >= .5
            f_low = 2 * m_["low_precision"] * m_["low_recall"] / max(1e-9, m_["low_precision"] + m_["low_recall"])
            m_["macro_f1"] = round((m_["f1"] + f_low) / 2, 3)
            m_["pr_auc"] = round(float(average_precision_score(yv, x[a])), 3)
            m_["prob_calibration"] = prob_cal(x, a, rng)
            b = pd.cut(x[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
            m_["reliability"] = x.groupby(b, observed=False).agg(n=("y_high", "size"), mean_p=(a, "mean"), observed=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")
            cm[a] = m_
        d = {a: E7.diff_ci(x, a, "E158", "q_true", rng, n=2000) for a in ("FINAL", "AUTO")}
        cF, cE = (x["FINAL"] >= .5) == (x["y_high"] == 1), (x["E158"] >= .5) == (x["y_high"] == 1)
        bb, cc = int((cF & ~cE).sum()), int((~cF & cE).sum())
        res["mcnemar"][L] = {"final_right_e158_wrong": bb, "final_wrong_e158_right": cc, "p_exact": round(float(binomtest(bb, bb + cc, 0.5).pvalue), 4) if bb + cc else 1.0}
        per = {s: {a: {"accuracy": round(float(((g[a] >= .5) == (g["y_high"] == 1)).mean()), 3), "brier": round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4)} for a in ("E158", "FINAL")} for s, g in x.groupby("survey")}
        P_, rk = R2.rank_measures(x, ["E158", "AUTO", "FINAL"])
        rel = LD.evaluate(x, "FINAL", "FINAL")["leads"][0]
        yd = x["y_high"].values == 1
        thr_acc = float(np.mean((x["FINAL"].values >= x["thr_youden"].values) == yd))
        res["leads"][L] = {"class": cm, "brier_minus_E158": {a: {"diff": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]} for a, v in d.items()}, "per_round": per, "ranking": rk,
                           "reliability_C1_C6": rel["criteria"], "reliable": rel["reliable"], "cfg": x.groupby("survey")["cfg_FINAL"].first().to_dict(), "youden_threshold_sensitivity": {"thresholds": x.groupby("survey")["thr_youden"].first().round(3).to_dict(), "accuracy": round(thr_acc, 3)}}
    x = x1
    rng = np.random.default_rng(165)
    ctl = {}
    for c in ["SHUF_ALL"] + [f"SHUF_{g}" for g in G5] + ["SH", "nonews", "nonat"]:
        v = E7.diff_ci(x, "FINAL", c, "q_true", rng, n=2000)
        ctl[c] = {"brier": round(float(np.mean((x[c] - x["q_true"]) ** 2)), 4), "accuracy": round(float(((x[c] >= .5) == (x["y_high"] == 1)).mean()), 3), "FINAL_minus_this": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]}
    res["controls"] = ctl
    res["leakage_max_abs_change"] = float(np.max(np.abs(x["mu_FINAL"] - x["mu_corrupt"])))
    res["bias"] = {a: C.bias(x, a, np.random.default_rng(161)) for a in ("E158", "AUTO", "FINAL")}
    l1 = res["leads"][1]
    f, e = l1["class"]["FINAL"], l1["class"]["E158"]
    b = res["bias"]["FINAL"]
    rkc = l1["ranking"]["concordance"]["FINAL"]
    gates = {"F1": res["leakage_max_abs_change"] < 1e-9, "F2": ctl["SHUF_ALL"]["ci95"][1] < 0,
             "F3": f["brier"] <= e["brier"] and l1["brier_minus_E158"]["FINAL"]["ci95"][1] < 0.02,
             "F4": f["high_recall"] >= 0.75 and f["low_recall"] >= 0.65 and f["balanced_accuracy"] >= 0.76,
             "F5": abs(b["overall"]["mean"]) <= 3 and all(abs(b[f"island:{k_}"]["mean"]) <= 5 for k_ in ("Luzon", "Visayas", "Mindanao")),
             "F6": f["prob_calibration"]["slope_ci95"][0] <= 1 <= f["prob_calibration"]["slope_ci95"][1],
             "F7": all(v["FINAL"]["accuracy"] >= v["E158"]["accuracy"] - 0.05 for v in l1["per_round"].values()) and sum(v["FINAL"]["brier"] <= v["E158"]["brier"] for v in l1["per_round"].values()) >= 2,
             "F8": ctl["SHUF_ALL"]["ci95"][1] < 0,
             "F9_ranks_displayable": rkc["ci95"][0] > 0.5,
             "F10": bool(l1["reliable"])}
    res["gates"] = gates
    res["lead2_reliable"] = bool(res["leads"][2]["reliable"])
    res["status"] = "validated" if all(gates[g] for g in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F10")) else ("improved, Lead 1 not reliable" if all(gates[g] for g in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")) else "not accepted")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    print(json.dumps({kk: res[kk] for kk in ("gates", "status", "lead2_reliable", "leakage_max_abs_change", "mcnemar", "controls")}, indent=1, default=str))
    for L in (1, 2):
        r = res["leads"][L]
        print(f"\nLead {L} cfg {r['cfg']} C1-C6 {r['reliability_C1_C6']} brier-E158 {r['brier_minus_E158']} youden {r['youden_threshold_sensitivity']}")
        cols = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_precision", "low_recall", "f1", "macro_f1", "auc", "pr_auc", "brier", "calibration_slope", "mae_pts", "false_alarm_rate", "missed_high_rate")
        print(pd.DataFrame({a: {c: v.get(c) for c in cols} | {"pcal_slope": v["prob_calibration"]["slope"], "pcal_ci": v["prob_calibration"]["slope_ci95"], "conf": v["confusion"]} for a, v in r["class"].items()}).T.to_string())
        print("per round", r["per_round"], "conc", {a: v for a, v in r["ranking"]["concordance"].items()})
        print("reliability FINAL", r["class"]["FINAL"]["reliability"])
    print(json.dumps(res["bias"], indent=1))


def live():
    from app.e160.trace import build
    S, P, tr, m, te = build()
    AN = A4.anchors(S, P, tr, te)
    mu, p, half, sd, tag, thr = run_final(tr, te, AN)
    res = json.loads((OUT / "results.json").read_text())
    rng = np.random.default_rng(165)
    draw = mu[None, :] + rng.standard_normal((10000, len(te))) * (sd * np.sqrt(1 - 0.726))[None, :]
    top = np.bincount(draw.argmax(axis=1), minlength=len(te)) / 10000
    rows = [{"province": te["province"].iloc[k], "score": round(float(pct(mu[k])), 1), "low90": round(float(pct(mu[k] - half[k])), 1), "high90": round(float(pct(mu[k] + half[k])), 1), "p_high": round(float(p[k]), 3), "class": "HIGH" if p[k] >= .5 else "LOW", "p_highest": round(float(top[k]), 3)} for k in range(len(te))]
    frozen = {"model": "AUTO-FINAL (E165)", "status": res["status"], "gates": res["gates"], "config": tag, "feature_list": {"GOV": fs_for()["GOV"], "FULL": fs_for()["FULL"]}, "threshold_p_high": 0.5,
              "training_data_cutoff": "survey rounds released by issue 2026-Q4 (NNS2013, FNRI2015, ENNS2018, ENNS2019, ENNS2021); quarterly inputs as of 2026-Q4", "train_rows": int(len(tr)),
              "issue": "2026-10-01", "target_quarter": "2027-Q1", "lead": 1, "forecasts": rows, "ranks_displayed": bool(res["gates"]["F9_ranks_displayable"] and max(r["p_highest"] for r in rows) >= 0.80), "code": "backend/app/e165/final.py"}
    (OUT / "frozen_model.json").write_text(json.dumps(frozen, indent=1, default=str), newline="\n")
    sp = OUT / "sealed_2027-Q1.json"
    if not sp.exists():
        sp.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **frozen}, indent=1, default=str), newline="\n")
    print("seal", hashlib.sha256(sp.read_bytes()).hexdigest())
    print(json.dumps(frozen, indent=1, default=str))


if __name__ == "__main__":
    {"eval": evaluate, "live": live}[sys.argv[1]]()
