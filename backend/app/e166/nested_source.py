"""
E166: E164 AUTO with the data-source choice moved inside the training-only selection (docs/e166/PROTOCOL.md). E165 gates.

    python -m app.e166.nested_source eval | live
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
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import panel as sun_panel
from app.e156 import leads as LD
from app.e157.sources import SOURCES
from app.e162 import rank as R2
from app.e163 import model as C
from app.e164 import auto as A4
from app.e165 import final as F5
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e166" / "out"
GNT = list(Pv.GNT_COLS)
NEWS = [c for c in GNT if c in Pv.NEWS_ALL]
BASE = {"GOV": [c for c in GNT if c not in NEWS], "FULL": GNT}
SRC = {"none": []} | SOURCES
SRC_COLS = sorted({c for v in SOURCES.values() for c in v})
TRIG = [c for c in GNT if C.gmap(c) is not None] + SRC_COLS
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def add_sources(d, L, H, S_P):
    n = len(d)
    d = d.merge(L, left_on=["key", "i"], right_on=["key", "qi"], how="left", suffixes=("", "_l")).drop(columns=["qi_l"], errors="ignore")
    d = E154.add_income(d, H)
    d = d.merge(S_P, left_on=["key", "i"], right_on=["key", "qi"], how="left", suffixes=("", "_s")).drop(columns=["qi_s"], errors="ignore")
    assert len(d) == n
    for c in SRC_COLS:
        if c not in d:
            d[c] = np.nan
    return d.reset_index(drop=True)


def run_proc(tr, te, AN):
    tr = tr.reset_index(drop=True)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    FS = {f"{b}+{s}": BASE[b] + SRC[s] for b in BASE for s in SRC}
    cfgs = [(a, "NONE", None) for a in AN] + [(a, l, f) for a in AN for l in A4.LEARNERS for f in FS]
    best = None
    for a, l, f in cfgs:
        atr = AN[a][0]
        if l == "NONE":
            oof = atr.copy()
        else:
            oof = np.zeros(len(tr))
            for i_tr, i_te in folds:
                oof[i_te] = atr[i_te] + A4.LEARNERS[l](FS[f]).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        cal = np.zeros(len(tr))
        for i_tr, i_te in folds:
            Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
            ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
            cal[i_te] = ab[0] + ab[1] * oof[i_te]
        for c, o in (("id", oof), ("lin", cal)):
            sse = float(np.sum(w * (y - o) ** 2))
            if best is None or sse < best["sse"]:
                best = {"sse": sse, "cfg": (a, l, f), "cal": c, "oof": o, "oof_id": oof}
    a, l, f = best["cfg"]
    atr, ate = AN[a]
    mdl = None
    if l == "NONE":
        mu = ate.copy()
    else:
        mdl = A4.LEARNERS[l](FS[f]).fit(tr.assign(e=y - atr))
        mu = ate + mdl.predict(te)
    if best["cal"] == "lin":
        Z = np.column_stack([np.ones(len(tr)), best["oof_id"]]) * np.sqrt(w)[:, None]
        ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
        mu = ab[0] + ab[1] * mu
    sd, half = A4.scale(y - best["oof"], gap, te["gap_q"].values)
    src = f.split("+")[1] if f else "none"
    miss = float(te[SRC[src]].isna().all(axis=1).mean()) if SRC.get(src) else 0.0
    return mu, norm.cdf(mu / sd), half, sd, f"{a}|{l}|{f or '-'}|{best['cal']}", src, miss


def task(survey, lead, H, L, S_P, mode):
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
    te = add_sources(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), L, H, S_P)
    if te.empty:
        return None
    tr = add_sources(Pv.add_inputs(S, P.tr), L, H, S_P)
    AN = A4.anchors(S, P, tr, te)
    if mode.startswith("shuf"):
        s_ = int(mode[4:])
        tr, te = C.shuffle_cols(tr, TRIG, s_), C.shuffle_cols(te, TRIG, s_)
    mu, p, half, sd, tag, src, miss = run_proc(tr, te, AN)
    out = te[["key", "survey", "lead"]].copy()
    out["mode"], out["mu"], out["p"], out["half"], out["cfg"], out["source"], out["src_missing_test"] = mode, mu, p, half, tag, src, miss
    return out


def evaluate():
    OUT.mkdir(parents=True, exist_ok=True)
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    jobs = [(s, h, "main") for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in (1, 2)] + [(s, 1, m) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for m in ("shuf1", "shuf2", "shuf3", "corrupt")]
    if (OUT / "all_rows.csv").exists() and "--rerun" not in sys.argv:
        Al = pd.read_csv(OUT / "all_rows.csv")
    else:
        Al = pd.concat([x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, L, S_P, m) for s, h, m in jobs) if x is not None], ignore_index=True)
        Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    k = ["key", "survey", "lead"]
    G = pd.read_csv(D / "e164" / "out" / "oof.csv")
    res = {"mcnemar": {}, "leads": {}}
    for Ld in (1, 2):
        x = G[G["lead"] == Ld].reset_index(drop=True).merge(Al[(Al["lead"] == Ld) & (Al["mode"] == "main")][k + ["mu", "p", "half", "cfg", "source", "src_missing_test"]].rename(columns={"mu": "mu_E166", "p": "E166", "half": "half_E166", "cfg": "cfg_E166"}), on=k)
        assert len(x) == 72
        if Ld == 1:
            for m in ("shuf1", "shuf2", "shuf3", "corrupt"):
                x = x.merge(Al[(Al["lead"] == 1) & (Al["mode"] == m)][k + ["mu", "p"]].rename(columns={"mu": f"mu_{m}", "p": m}), on=k)
            x["SHUF"] = x[["shuf1", "shuf2", "shuf3"]].mean(axis=1)
            x1 = x
        rng = np.random.default_rng(166)
        cm = {}
        for a in ("PERS", "E158", "AUTO", "E166"):
            m_ = C.cls_metrics(x, a, rng)
            f_low = 2 * m_["low_precision"] * m_["low_recall"] / max(1e-9, m_["low_precision"] + m_["low_recall"])
            m_["macro_f1"] = round((m_["f1"] + f_low) / 2, 3)
            m_["pr_auc"] = round(float(average_precision_score(x["y_high"], x[a])), 3)
            m_["prob_calibration"] = F5.prob_cal(x, a, rng)
            b = pd.cut(x[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
            m_["reliability"] = x.groupby(b, observed=False).agg(n=("y_high", "size"), mean_p=(a, "mean"), observed=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")
            cm[a] = m_
        d = E7.diff_ci(x, "E166", "E158", "q_true", rng, n=2000)
        cF, cE = (x["E166"] >= .5) == (x["y_high"] == 1), (x["E158"] >= .5) == (x["y_high"] == 1)
        bb, cc = int((cF & ~cE).sum()), int((~cF & cE).sum())
        res["mcnemar"][Ld] = {"e166_right_e158_wrong": bb, "e166_wrong_e158_right": cc, "p_exact": round(float(binomtest(bb, bb + cc, 0.5).pvalue), 4) if bb + cc else 1.0}
        per = {s: {a: {"accuracy": round(float(((g[a] >= .5) == (g["y_high"] == 1)).mean()), 3), "brier": round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4)} for a in ("E158", "E166")} for s, g in x.groupby("survey")}
        _, rk = R2.rank_measures(x, ["E158", "AUTO", "E166"])
        rel = LD.evaluate(x, "E166", "E166")["leads"][0]
        res["leads"][Ld] = {"class": cm, "brier_minus_E158": {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]}, "per_round": per, "ranking": rk, "C1_C6": rel["criteria"], "reliable": rel["reliable"],
                            "selected": x.groupby("survey")[["cfg_E166", "source", "src_missing_test"]].first().to_dict("index")}
    x = x1
    rng = np.random.default_rng(166)
    v = E7.diff_ci(x, "E166", "SHUF", "q_true", rng, n=2000)
    res["shuffle"] = {"brier": round(float(np.mean((x["SHUF"] - x["q_true"]) ** 2)), 4), "accuracy": round(float(((x["SHUF"] >= .5) == (x["y_high"] == 1)).mean()), 3), "E166_minus_shuffled": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]}
    res["leakage_max_abs_change"] = float(np.max(np.abs(x["mu_E166"] - x["mu_corrupt"])))
    res["bias"] = {a: C.bias(x, a, np.random.default_rng(161)) for a in ("E158", "E166")}
    l1 = res["leads"][1]
    f, e = l1["class"]["E166"], l1["class"]["E158"]
    b = res["bias"]["E166"]
    g = {"F1": res["leakage_max_abs_change"] < 1e-9, "F2": res["shuffle"]["ci95"][1] < 0,
         "F3": f["brier"] <= e["brier"] and l1["brier_minus_E158"]["ci95"][1] < 0.02,
         "F4": f["high_recall"] >= 0.75 and f["low_recall"] >= 0.65 and f["balanced_accuracy"] >= 0.76,
         "F5": abs(b["overall"]["mean"]) <= 3 and all(abs(b[f"island:{k_}"]["mean"]) <= 5 for k_ in ("Luzon", "Visayas", "Mindanao")),
         "F6": f["prob_calibration"]["slope_ci95"][0] <= 1 <= f["prob_calibration"]["slope_ci95"][1],
         "F7": all(v_["E166"]["accuracy"] >= v_["E158"]["accuracy"] - 0.05 for v_ in l1["per_round"].values()) and sum(v_["E166"]["brier"] <= v_["E158"]["brier"] for v_ in l1["per_round"].values()) >= 2,
         "F8": res["shuffle"]["ci95"][1] < 0, "F9_ranks_displayable": l1["ranking"]["concordance"]["E166"]["ci95"][0] > 0.5, "F10": bool(l1["reliable"])}
    res["gates"] = g
    res["lead2_reliable"] = bool(res["leads"][2]["reliable"])
    core = all(g[q] for q in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"))
    res["status"] = "validated" if core and g["F10"] else ("improved, Lead 1 not reliable" if core else "not accepted")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    print(json.dumps({kk: res[kk] for kk in ("gates", "status", "lead2_reliable", "leakage_max_abs_change", "mcnemar", "shuffle")}, indent=1, default=str))
    for Ld in (1, 2):
        r = res["leads"][Ld]
        print(f"\nLead {Ld} selected {r['selected']} C1-C6 {r['C1_C6']} brier-E158 {r['brier_minus_E158']}")
        cols = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_precision", "low_recall", "macro_f1", "auc", "pr_auc", "brier", "calibration_slope", "false_alarm_rate", "missed_high_rate")
        print(pd.DataFrame({a: {c: v_.get(c) for c in cols} | {"pcal": v_["prob_calibration"]["slope"], "pcal_ci": v_["prob_calibration"]["slope_ci95"], "conf": v_["confusion"]} for a, v_ in r["class"].items()}).T.to_string())
        print("per round", r["per_round"], "conc", r["ranking"]["concordance"]["E166"], "reliab", r["class"]["E166"]["reliability"])
    print({a: {g_: (v_["mean"], v_["ci95"]) for g_, v_ in res["bias"][a].items() if g_ != "calabarzon_rows"} | {"CAL": res["bias"][a]["calabarzon_rows"]} for a in res["bias"]})


def live():
    from app.e160.trace import build
    S, P, tr, m, te = build()
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    tr, te = add_sources(tr, L, H, S_P), add_sources(te, L, H, S_P)
    AN = A4.anchors(S, P, tr, te)
    mu, p, half, sd, tag, src, miss = run_proc(tr, te, AN)
    res = json.loads((OUT / "results.json").read_text())
    avail = {s: round(float(te[c].notna().all(axis=1).mean()), 2) for s, c in SOURCES.items()}
    rng = np.random.default_rng(166)
    draw = mu[None, :] + rng.standard_normal((10000, len(te))) * (sd * np.sqrt(1 - 0.726))[None, :]
    top = np.bincount(draw.argmax(axis=1), minlength=len(te)) / 10000
    rows = [{"province": te["province"].iloc[k], "score": round(float(pct(mu[k])), 1), "low90": round(float(pct(mu[k] - half[k])), 1), "high90": round(float(pct(mu[k] + half[k])), 1), "p_high": round(float(p[k]), 3), "class": "HIGH" if p[k] >= .5 else "LOW", "p_highest": round(float(top[k]), 3)} for k in range(len(te))]
    out = {"model": "E166 (E164 AUTO + nested source selection)", "status": res["status"], "config": tag, "source_selected_live": src, "source_inputs_missing_at_issue": miss, "live_source_availability_share": avail, "issue": "2026-10-01", "target_quarter": "2027-Q1", "lead": 1, "forecasts": rows}
    (OUT / "live.json").write_text(json.dumps(out, indent=1, default=str), newline="\n")
    if res["status"] != "not accepted":
        sp = OUT / "sealed_2027-Q1.json"
        if not sp.exists():
            sp.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **out}, indent=1, default=str), newline="\n")
        print("seal", hashlib.sha256(sp.read_bytes()).hexdigest())
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    {"eval": evaluate, "live": live}[sys.argv[1]]()
