"""
E149 locked evaluation, HIGH at 50 % (docs/e149/PROTOCOL.md).

    python -m app.e149.evaluate lock | run

The threshold is set per process through app.e147.features.LT, which E148's model and row builders read at call time, so E148's code
and files stay as locked. Everything is written under data/e149/out.
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
from scipy.stats import norm, spearmanr

from app.e145 import lgu as LGU
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e148 import OUT as O148
from app.e148 import evaluate as E8
from app.e148 import model as M
from app.e149 import OUT, PROTOCOL_VERSION, VERSION
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
THRESHOLD = 50.0
LT = 0.0                                                     # logit(0.50)
SEED = 149
N_BOOT = 2000
LEADS = E8.LEADS
ARMS = E8.ARMS
PROTOCOL = BACKEND_DIR.parent / "docs" / "e149" / "PROTOCOL.md"
T = {"threshold_pct": THRESHOLD, "R1_accuracy": 0.75, "R2_auc": 0.70, "R3_recall": 0.50, "R3_precision": 0.50, "R8_low_recall": 0.50, "seed": SEED, "n_boot": N_BOOT, "leads": LEADS, "n_placebo": 30}


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app"
    return {"protocol": _sha(PROTOCOL), "evaluate": _sha(here / "e149" / "evaluate.py"), "e148_model": _sha(here / "e148" / "model.py"), "e148_evaluate": _sha(here / "e148" / "evaluate.py"),
            "e148_results": _sha(O148 / "results.json"), "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists():
        raise RuntimeError("E149 is already locked")
    p.write_text(json.dumps({"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": _hashes(), "thresholds": T}, indent=2), newline="\n")


def _set():
    Fe.LT = LT


def task(*a, **k):
    _set()
    return E8.task(*a, **k)


def labels_2021() -> pd.DataFrame:
    L = pd.read_csv(Lb.SEALED)
    return L[L["fs_survey_category"] == "Food Insecure Households"].drop_duplicates("key")[["key", "pct"]]


def extra(m) -> dict:
    c = m["confusion"]
    low = c["tn"] / (c["tn"] + c["fp"]) if c["tn"] + c["fp"] else None
    m["low_recall"] = low
    m["balanced_accuracy"] = (m["recall"] + low) / 2 if low is not None else None
    return m


def met(g, a):
    return extra(E7.metrics(g[a].fillna(0.5), g["y_high"], g["q_true"]))


def run():
    _set()
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    # development
    Dv = pd.concat([x for x in Parallel(n_jobs=12)(delayed(task)(o, t, h) for o, t in E8.TESTS.items() for h in LEADS) if x is not None], ignore_index=True)
    Dv["y_high"] = (Dv["y_true"] >= LT).astype(int)
    Dv.to_csv(OUT / "oof_dev.csv", index=False, lineterminator="\n")
    dev = {}
    for h, g in Dv.groupby("lead"):
        e = {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "always_high_accuracy": float(g["y_high"].mean()), "metrics": {a: met(g, a) for a in ARMS if a in g}}
        for x, y in (("Q-G", "PERS"), ("Q-G", "DRIFT"), ("Q-GNB", "Q-G"), ("Q-GN", "Q-G")):
            e[f"{x}_minus_{y}"] = E7.diff_ci(g, x, y, "q_true", rng)
        z = g.dropna(subset=["Q-frozen"])
        e["Q-G_minus_Q-frozen"] = E7.diff_ci(z, "Q-G", "Q-frozen", "q_true", rng)
        dev[f"L{h}"] = e
    sel = "Q-GNB" if dev["L1"]["Q-GNB_minus_Q-G"]["ci95"][1] < 0 else "Q-G"
    # 2021, previously opened by E148
    F = pd.concat(Parallel(n_jobs=8)(delayed(task)("F", "ENNS2021", h) for h in LEADS), ignore_index=True).merge(labels_2021(), on="key", how="left")
    F = F[F["pct"].notna()].copy()
    F["y_true"], F["y_high"] = Fe._logit(F["pct"]), (F["pct"] >= THRESHOLD).astype(int)
    F["q_true"] = norm.cdf((F["y_true"] - LT) / (0.03 / (F["pct"] / 100 * (1 - F["pct"] / 100))))
    F.to_csv(OUT / "oof_2021.csv", index=False, lineterminator="\n")
    old = pd.read_csv(O148 / "oof_2021.csv")
    chk = F[["key", "lead", "mu_Q-G", "sigma_Q-G"]].merge(old[["key", "lead", "mu_Q-G", "sigma_Q-G"]], on=["key", "lead"], suffixes=("", "_148"))
    res = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(), "threshold_pct": THRESHOLD, "selected_arm": sel, "evidence_status": "2021 labels previously opened by E148; not an untouched test",
           "same_continuous_forecast_as_E148": {"max_abs_diff_logit": float((chk["mu_Q-G"] - chk["mu_Q-G_148"]).abs().max()), "rows": int(len(chk))}, "development": dev, "by_lead": {}}
    mrl, stop, news_p = 0, False, {}
    for h, g in F.groupby("lead"):
        e = {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "n_low": int((1 - g["y_high"]).sum()), "always_high_accuracy": float(g["y_high"].mean()), "metrics": {a: met(g, a) for a in ARMS}, "train_surveys": g["train_surveys"].iloc[0]}
        for x, y in ((sel, "PERS"), (sel, "DRIFT"), ("Q-GNB", "Q-G"), ("Q-GN", "Q-G")):
            e[f"{x}_minus_{y}"] = E7.diff_ci(g, x, y, "q_true", rng)
        z = g.dropna(subset=["Q-frozen"])
        e["Q-G_minus_Q-frozen"] = E7.diff_ci(z, "Q-G", "Q-frozen", "q_true", rng)
        news_p[int(h)] = e["Q-GNB_minus_Q-G"]["p_ge_0"]
        pc, dy = (g["mu_" + sel] - g["y_anchor"]).values, (g["y_true"] - g["y_anchor"]).values
        gs, v = list(g.groupby("region").indices.values()), []
        for _ in range(1000):
            i = np.concatenate([gs[j] for j in rng.integers(0, len(gs), len(gs))])
            v.append(spearmanr(pc[i], dy[i]).statistic)
        chg = {"rho": float(spearmanr(pc, dy).statistic), "ci95": [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]}
        pp = g[sel].values
        ece95 = float(np.percentile([E7.metrics(pp, (rng.random(len(pp)) < pp).astype(int))["ece"] for _ in range(2000)], 95))
        m = e["metrics"][sel]
        nir = max(e["always_high_accuracy"], 1 - e["always_high_accuracy"])
        ck = {"R1_accuracy": m["accuracy"] >= T["R1_accuracy"], "R2_auc": (m["auc"] or 0) >= T["R2_auc"], "R3_recall_precision": m["recall"] >= T["R3_recall"] and m["precision"] >= T["R3_precision"], "R4_beats_persistence": e[f"{sel}_minus_PERS"]["ci95"][1] < 0,
              "R5_calibration": m["ece"] <= ece95, "R6_predicts_change": chg["ci95"][0] > 0, "R7_beats_no_information": m["accuracy"] > nir, "R8_low_recall": (m["low_recall"] or 0) >= T["R8_low_recall"]}
        e["reliability"] = {"checks": {k: bool(x) for k, x in ck.items()}, "passes": bool(all(ck.values())), "change": chg, "ece_95th_perfect_calibration": ece95}
        e["provinces"] = g[["province", "pct", "y_high", sel, "PERS", "mu_" + sel]].sort_values("pct", ascending=False).round(3).to_dict(orient="records")
        res["by_lead"][f"L{h}"] = e
        if e["reliability"]["passes"] and not stop:
            mrl = int(h)
        else:
            stop = True
    res["maximum_reliable_lead"] = mrl
    order, st, holm = sorted([1, 2, 3, 4], key=lambda h: news_p[h]), False, {}
    for k, h in enumerate(order):
        a = 0.05 / (4 - k)
        ok = (not st) and news_p[h] < a / 2
        st = st or not ok
        holm[f"L{h}"] = {"p_ge_0": news_p[h], "level": 1 - a, "news_improves": ok}
    res["news_holm"] = holm
    pl = Parallel(n_jobs=16)(delayed(task)("F", "ENNS2021", 1, E8.Pn.ANCHOR_LAG, 4000 + d, ["Q-GNB"]) for d in range(T["n_placebo"]))
    g1 = F[F["lead"] == 1].set_index("key")
    vals = [E7.eb(x.set_index("key").loc[g1.index, "Q-GNB"].values, g1["q_true"].values) - E7.eb(g1["Q-G"].values, g1["q_true"].values) for x in pl]
    real = res["by_lead"]["L1"]["Q-GNB_minus_Q-G"]["diff"]
    res["placebo_L1"] = {"real_diff": real, "share_placebo_better_or_equal": float(np.mean(np.array(vals) <= real))}
    res["news_claim_L1"] = bool(holm["L1"]["news_improves"] and res["placebo_L1"]["share_placebo_better_or_equal"] <= 0.05)
    res["gates_passed"] = bool(mrl >= 1 and res["news_claim_L1"])
    # provincial rows on all measured HFIAS rounds through 2021, CALABARZON
    res["independent_sws_check_inherited_from_E148"] = json.loads((O148 / "dev_results.json").read_text())["independent_sws_check"]
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    issue(res)
    print(json.dumps({k: res[k] for k in ("selected_arm", "maximum_reliable_lead", "news_claim_L1", "gates_passed", "same_continuous_forecast_as_E148")}, indent=1))


def issue(res):
    """Regenerated from a fresh fit at 50 %, with 2021 as an anchor. Forecast percentages should equal E148's; classes differ."""
    _set()
    S = M.Store()
    base = S.base.drop_duplicates("key").set_index("key")
    e = labels_2021()
    e = e[e["key"].isin(base.index)].copy()
    e["survey"], e["year"], e["ref_quarter"], e["p"], e["se_p"] = "ENNS2021", 2021, "2021-Q3", e["pct"], 3.0
    e["y"] = Fe._logit(e["p"])
    e["se_y"] = 0.03 / (e["p"] / 100 * (1 - e["p"] / 100))
    e["q_high"] = norm.cdf((e["y"] - LT) / e["se_y"])
    for c in ("province", "region", "sws_area", "island"):
        e[c] = e["key"].map(base[c])
    S.base = pd.concat([S.base, e[S.base.columns]], ignore_index=True)
    i = qindex("2026-Q4")
    tr = M.rows_for(S, M.targets(S, E8.ALL_TRAIN + ["ENNS2021"]), LEADS, "F")
    m = M.QModel(M.SETS["Q-G"]).fit(tr)
    five = S.base.drop_duplicates("key")
    five = five[five["province"].isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])]
    rows = []
    for h in (1, 2, 3, 4):
        te = M.rows_for(S, five.assign(T=i + h, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [h], "F")
        mu, sd = m.mu(te), m.sigma(te)
        for k in range(len(te)):
            lo, hi = 100 / (1 + np.exp(-(mu[k] - 1.645 * sd[k]))), 100 / (1 + np.exp(-(mu[k] + 1.645 * sd[k])))
            f = 100 / (1 + np.exp(-mu[k]))
            rows.append({"province": te["province"].iloc[k], "issue_quarter": qlabel(i), "target_quarter": qlabel(i + h), "lead": h, "anchor_quarter": qlabel(int(te["rq_anchor"].iloc[k])), "anchor_pct": round(100 / (1 + np.exp(-te["y_anchor"].iloc[k])), 1), "forecast_pct": round(f, 1), "low90": round(lo, 1), "high90": round(hi, 1),
                         "p_high_ge50": round(float(norm.cdf((mu[k] - LT) / sd[k])), 3), "class_ge50": "HIGH" if f >= THRESHOLD else "LOW", "not_distinguishable_from_50": bool(lo < THRESHOLD < hi), "row_type": "forecast"})
    Lv = pd.DataFrame(rows)
    (OUT / "issue").mkdir(exist_ok=True)
    Lv.to_csv(OUT / "issue" / "five_province_forecasts.csv", index=False, lineterminator="\n")
    q1 = Lv[Lv["lead"] == 1]
    r = LGU.rank(dict(zip(q1["province"], q1["p_high_ge50"])), qlabel(i + 1))
    r.to_csv(OUT / "issue" / f"lgu_priority_{qlabel(i + 1)}.csv", index=False, lineterminator="\n")
    print(Lv[Lv["lead"] == 1].to_string(index=False))
    print(len(r), r.head(5)[["lgu_name", "province_name", "priority_score"]].round(3).to_dict(orient="records"))
    print(r.groupby("province_name")["priority_rank_in_region"].median().to_dict())


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
