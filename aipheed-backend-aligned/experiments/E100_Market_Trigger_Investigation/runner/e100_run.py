"""E100 runner (PROTOCOL.md, frozen sha in PROTOCOL_SHA256.txt): why the Market / Prices trigger is low.

Reads only served, local files; writes only to ../out/. Run from backend/ with the backend venv:

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E100_Market_Trigger_Investigation/runner/e100_run.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["AIPHEED_LEAD2_MODEL"] = "thesis"
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
BACKEND = HERE.parents[3] / "backend"
sys.path.insert(0, str(BACKEND))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import binomtest, spearmanr  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

from app.ml.inference import thesis_system as TS  # noqa: E402

DOMS = ["A", "V", "C", "E", "N", "H"]
SHRINK_K, MIN_PAIRS, MIN_DOMAINS = 8, 6, 4
HUNGER_LINE = 11.3
EVAL_LAST_ORIGIN = "2026-Q1"           # Lead-2 evaluation origins 2021-Q4..2026-Q1 (targets 2022-Q2..2026-Q3)
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
GROUPS = {"market": ("A1", "A2", "A3"), "climate": ("C1", "C2", "C3"), "fish_kill": ("C4",), "employment": ("E1",),
          "ofw_remittance": ("E2",), "vulnerability": ("V1",), "regional_hunger": ("H1",), "news": ("N1",)}
qi, qs = TS.qi, TS.qs


def verify():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == want, "PROTOCOL.md changed after freezing"
    return got


# ------------------------------------------------------------------------------------------------ inputs
def load_history() -> pd.DataFrame:
    H = pd.read_csv(BACKEND / "data/thesis/firi2_history.csv", dtype={"province_code": str})
    H["t"] = H["origin_quarter"].map(qi)
    H["ind"] = H["indicators_json"].map(json.loads)
    H["w_stored"] = H["weights_json"].map(lambda s: json.loads(s) if s else None)
    return H


def outcome_series() -> dict[str, float]:
    s = pd.read_csv(BACKEND / "data/inputs/sws_rounds.csv")
    return s.groupby("quarter")["H"].mean().to_dict()


def level_indicator() -> pd.DataFrame:
    """L(p, t) = 100 x (food index at t-1 / food index at 2021-Q1 - 1); rows before 2021 are never read."""
    c = pd.read_parquet(BACKEND / "data/processed/cpi_full.parquet", filters=[("year", ">=", 2021)])
    assert c["year"].min() >= 2021
    c = c.dropna(subset=["province_code"])
    c = c[c["province_code"].isin(PROVS)]
    food = {(r.province_code, qi(r.quarter)): float(r.cpi_food_nab) for r in c.itertuples() if pd.notna(r.cpi_food_nab)}
    alli = {(r.province_code, qi(r.quarter)): float(r.cpi_all_items) for r in c.itertuples() if pd.notna(r.cpi_all_items)}
    q0 = qi("2021-Q1")
    rows = []
    for t in range(qi("2021-Q2"), qi("2026-Q3") + 1):
        for p in PROVS:
            a, b = food.get((p, t - 1)), food.get((p, q0))
            ra = None
            if a and b and alli.get((p, t - 1)) and alli.get((p, q0)):
                ra = 100 * ((a / alli[(p, t - 1)]) / (b / alli[(p, q0)]) - 1)
            rows.append({"t": t, "province_code": p, "L": None if not (a and b) else 100 * (a / b - 1), "REL": ra})
    D = pd.DataFrame(rows)
    D["L_score"] = None
    for t in sorted(D["t"].unique()):
        prior = D[(D["t"] < t) & D["L"].notna()]["L"].tolist()
        if len(prior) < 8:
            continue
        for i in D.index[(D["t"] == t) & D["L"].notna()]:
            x = D.at[i, "L"]
            D.at[i, "L_score"] = (sum(v < x for v in prior) + 0.5 * sum(v == x for v in prior)) / len(prior)
    return D


# ------------------------------------------------------------------------------------------------ the weights
def evidence_weights(reg_hist, known, doms):
    """firi2_evaluate.evidence_weights (151887c), over `doms`; also returns rho per domain."""
    pairs = [(dm, known[tq]) for dm, tq in reg_hist if tq in known]
    n = len(pairs)
    if n < MIN_PAIRS:
        return None, n, {}
    raw, rhos = {}, {}
    for d in doms:
        xs = [(dm.get(d), h) for dm, h in pairs if dm.get(d) is not None]
        if len(xs) < MIN_PAIRS:
            continue
        rho = spearmanr([a for a, _ in xs], [b for _, b in xs]).correlation
        rhos[d] = float(rho) if rho == rho else None
        raw[d] = max(0.0, float(rho)) if rho == rho else 0.0
    if not raw or sum(raw.values()) <= 0:
        return None, n, rhos
    tot = sum(raw.values())
    wr = {d: v / tot for d, v in raw.items()}
    eq = 1.0 / len(raw)
    w = {d: n / (n + SHRINK_K) * wr[d] + SHRINK_K / (n + SHRINK_K) * eq for d in raw}
    m = float(np.mean(list(w.values())))
    return {d: v / m for d, v in w.items()}, n, rhos


def index_of(doms_row: dict, w: dict | None, doms) -> float | None:
    avail = {d: doms_row[d] for d in doms if doms_row.get(d) is not None}
    if len(avail) < MIN_DOMAINS:
        return None
    ww = {d: (w or {}).get(d, 1.0) if w else 1.0 for d in avail}
    tot = sum(ww.values())
    return sum(ww[d] / tot * avail[d] for d in avail)


def build_arm(H: pd.DataFrame, doms, dom_override=None, exempt: set | None = None):
    """Province index per row for a domain set. dom_override(row) -> dict of domain scores replaces the stored ones.
    exempt = domains kept but excluded from evidence weighting (weight 1)."""
    exempt = exempt or set()
    rows = []
    for _, r in H.iterrows():
        dr = {d: (None if pd.isna(r[f"dom_{d}"]) else float(r[f"dom_{d}"])) for d in DOMS}
        if dom_override:
            dr.update(dom_override(r))
        rows.append((int(r["t"]), r["province_code"], r["target"], dr))
    reg_hist, out, wlog = [], {}, {}
    for t in sorted({x[0] for x in rows}):
        known = {qs(q): h for q, h in TS._posted(TS.issue_of(t)).items()}
        w, n, rhos = evidence_weights([(dm, tq) for (tt, dm, tq) in reg_hist if tt < t], known,
                                      [d for d in doms if d not in exempt])
        if w is not None:
            w = {**w, **{d: 1.0 for d in exempt}}
        wlog[qs(t)] = {"weights": w, "pairs": n, "rho": rhos}
        cur = [x for x in rows if x[0] == t]
        for (tt, code, tq, dr) in cur:
            out[(tq, code)] = index_of(dr, w, doms)
        regm = {}
        for d in doms:
            vals = [x[3][d] for x in cur if x[3].get(d) is not None]
            regm[d] = float(np.mean(vals)) if vals else None
        reg_hist.append((t, regm, qs(t + 2)))
    return out, wlog


# ------------------------------------------------------------------------------------------------ metrics
def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


def metrics(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    n = len(y)
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    recl = tn / (tn + fp) if tn + fp else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None)
    return {"n": n, "positives": int(y.sum()), "accuracy": (tp + tn) / n, "accuracy_wilson95": wilson(tp + tn, n),
            "precision_HIGH": prec, "recall_HIGH": rec, "recall_LOW": recl, "f1_HIGH": f1,
            "balanced_accuracy": None if rec is None or recl is None else (rec + recl) / 2,
            "auc_roc": float(roc_auc_score(y, p)) if 0 < y.sum() < n else None,
            "brier": float(np.mean((p - y) ** 2)), "confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn}}


def paired(y, a, b, seed=2026, n=2000):
    d = (a - y) ** 2 - (b - y) ** 2
    rng = np.random.default_rng(seed)
    bs = [float(np.mean(rng.choice(d, len(d), replace=True))) for _ in range(n)]
    w, l_ = int((d < 0).sum()), int((d > 0).sum())
    return {"mean_brier_diff_arm_minus_FULL": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)),
            float(np.percentile(bs, 97.5))], "arm_better_quarters": w, "arm_worse_quarters": l_,
            "sign_p": float(binomtest(w, w + l_, 0.5).pvalue) if w + l_ else 1.0}


# ------------------------------------------------------------------------------------------------ main
def main():
    sha = verify()
    OUT.mkdir(exist_ok=True)
    H = load_history()
    out_h = outcome_series()
    LV = level_indicator()
    lv = {(int(r.t), r.province_code): (None if r.L_score is None else float(r.L_score)) for r in LV.itertuples()}

    def ind_score(r, k):
        s = r["ind"].get(k, {}).get("score")
        return None if s is None else float(s)

    def a_with_level(r):
        vals = [ind_score(r, "A1"), lv.get((int(r["t"]), r["province_code"])), ind_score(r, "A3")]
        vals = [v for v in vals if v is not None]
        return {"A": float(np.mean(vals)) if vals else None}

    arms, wlogs = {}, {}
    arms["FULL"], wlogs["FULL"] = build_arm(H, DOMS)
    # reproduction check against the stored FIRI
    diffs = [abs(arms["FULL"][(r.target, r.province_code)] - float(r.FIRI)) for r in H.itertuples()
             if pd.notna(r.FIRI) and arms["FULL"].get((r.target, r.province_code)) is not None]
    miss = [(r.target, r.province_code) for r in H.itertuples()
            if pd.notna(r.FIRI) != (arms["FULL"].get((r.target, r.province_code)) is not None)]
    repro = {"rows_compared": len(diffs), "max_abs_diff": max(diffs), "computability_mismatches": miss}
    assert max(diffs) < 1e-6 and not miss, f"FULL does not reproduce the served FIRI: {repro}"
    for d in DOMS:
        arms[f"NO-{d}"], wlogs[f"NO-{d}"] = build_arm(H, [x for x in DOMS if x != d])
    arms["EQ-A"], wlogs["EQ-A"] = build_arm(H, DOMS, exempt={"A"})
    arms["FULL-LVL"], wlogs["FULL-LVL"] = build_arm(H, DOMS, dom_override=a_with_level)

    # province-level single-domain / single-indicator scores
    single = {"A-ONLY": lambda r: None if pd.isna(r["dom_A"]) else float(r["dom_A"]),
              "A1-ONLY": lambda r: ind_score(r, "A1"), "A2-ONLY": lambda r: ind_score(r, "A2"),
              "A3-ONLY": lambda r: ind_score(r, "A3"),
              "LVL-ONLY": lambda r: lv.get((int(r["t"]), r["province_code"]))}
    for name, f in single.items():
        arms[name] = {(r["target"], r["province_code"]): f(r) for _, r in H.iterrows()}

    # regional table
    ev = H[(H["t"] <= qi(EVAL_LAST_ORIGIN)) & H["target"].isin(out_h)]
    targets = sorted(ev["target"].unique(), key=qi)
    Q = pd.DataFrame({"target": targets})
    Q["t"] = Q["target"].map(lambda q: qi(q) - 2)
    Q["H_obs"] = Q["target"].map(out_h)
    Q["y"] = (Q["H_obs"] > HUNGER_LINE).astype(int)
    for a, vals in arms.items():
        Q[a] = [np.mean([vals[(q, p)] for p in PROVS if vals.get((q, p)) is not None])
                if any(vals.get((q, p)) is not None for p in PROVS) else np.nan for q in targets]
    Q["H1"] = [np.mean([float(r.dom_H) for r in ev[ev["target"] == q].itertuples() if pd.notna(r.dom_H)]) for q in targets]
    Q["ALWAYS"] = 1.0
    Q["CLIM"] = [np.mean([h > HUNGER_LINE for h in TS._posted(TS.issue_of(int(t))).values()]) or 0.5 for t in Q["t"]]
    Q.to_csv(OUT / "regional_lead2.csv", index=False, lineterminator="\n")

    res = {"protocolSha256": sha, "reproduction": repro, "quarters_evaluated": len(Q), "arms": {}}
    full_ok = Q.dropna(subset=["FULL"])
    for a in list(arms) + ["H1", "ALWAYS", "CLIM"]:
        g = Q.dropna(subset=["FULL", a])
        m = metrics(g["y"], g[a])
        m["spearman_with_hunger_level"] = float(spearmanr(g[a], g["H_obs"]).correlation) if g[a].nunique() > 1 else None
        m["quarters"] = int(len(g))
        if a != "FULL":
            m["vs_FULL"] = paired(g["y"].to_numpy(float), g[a].to_numpy(float), g["FULL"].to_numpy(float))
        res["arms"][a] = m
    res["full_computable_quarters"] = int(len(full_ok))

    # weights and rho per origin (served arm)
    res["weights_FULL"] = wlogs["FULL"]
    res["weights_EQA_final"] = wlogs["EQ-A"]["2026-Q3"]

    # full-sample descriptive rho of each domain / indicator with H at t+2 (all evaluated quarters)
    desc = {}
    for d in DOMS:
        reg = [np.mean([float(r[f"dom_{d}"]) for _, r in ev[ev["target"] == q].iterrows() if pd.notna(r[f"dom_{d}"])] or [np.nan])
               for q in targets]
        s = pd.Series(reg, index=targets).dropna()
        desc[f"domain_{d}"] = {"rho": float(spearmanr(s, Q.set_index("target").loc[s.index, "H_obs"]).correlation),
                               "quarters": int(len(s))} if len(s) > 3 else None
    for a in ("A1-ONLY", "A2-ONLY", "A3-ONLY", "LVL-ONLY"):
        s = Q.dropna(subset=[a])
        desc[a] = {"rho": float(spearmanr(s[a], s["H_obs"]).correlation), "quarters": int(len(s))}
    res["descriptive_rho_with_hunger_t_plus_2"] = desc

    # indicator audit (Lead-2 history rows, evaluation origins)
    aud = {}
    for k in ("A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"):
        sc = [r["ind"][k]["score"] for _, r in ev.iterrows()]
        st = [r["ind"][k]["status"] for _, r in ev.iterrows()]
        obs = [s for s in sc if s is not None]
        aud[k] = {"rows": len(sc), "scored": len(obs), "missing_share": 1 - len(obs) / len(sc),
                  "status_counts": {s: st.count(s) for s in set(st)},
                  "score_sd": float(np.std(obs)) if obs else None,
                  "share_at_bound": float(np.mean([(s >= 0.999 or s <= 0.001) for s in obs])) if obs else None}
    res["indicator_audit"] = aud
    # redundancy inside affordability (province rows, scores)
    X = pd.DataFrame([{k: r["ind"][k]["score"] for k in ("A1", "A2", "A3")} | {"L": lv.get((int(r["t"]), r["province_code"]))}
                      for _, r in ev.iterrows()]).astype(float)
    res["affordability_score_spearman"] = X.corr(method="spearman", min_periods=8).round(3).to_dict()

    # contributions: served bars, per-row pushes, cancellation (served code)
    from app.ml.inference import e41_lead2 as L2
    from app.services import dashboard as DB
    rec = L2.record()
    served_q = [q for q in sorted(H["target"].unique(), key=qi) if qi(q) >= qi("2024-Q2")]
    bars, rowsC = {}, []
    for q in served_q:
        try:
            ex = DB.explainability_region(q)
            bars[q] = {t["label"]: t["pct"] for t in ex["triggers"]}
        except Exception as e:  # noqa: BLE001
            bars[q] = {"error": str(e)}
        for p in PROVS:
            fr = TS.firi_for(rec, q, p)
            if not fr or fr["firi"] is None:
                continue
            pu = TS.pushes(fr)
            row = {"target": q, "province_code": p, "FIRI": fr["firi"]}
            for g, ks in GROUPS.items():
                vals = [pu[k] for k in ks if k in pu]
                row[f"{g}_signed"] = sum(vals)
                row[f"{g}_abs"] = sum(abs(v) for v in vals)
            row["weight_A"] = TS._norm_weights(fr).get("A")
            row["score_A1"] = fr["indicators"]["A1"]["score"]
            row["score_A2"] = fr["indicators"]["A2"]["score"]
            row["score_A3"] = fr["indicators"]["A3"]["score"]
            rowsC.append(row)
    C = pd.DataFrame(rowsC)
    C.to_csv(OUT / "contributions_by_row.csv", index=False, lineterminator="\n")
    res["dashboard_region_bars"] = bars
    tot_abs = C[[f"{g}_abs" for g in GROUPS]].sum(axis=1)
    res["mean_abs_share_of_total_push"] = {g: float((C[f"{g}_abs"] / tot_abs).mean()) for g in GROUPS}
    res["market_cancellation_ratio_mean"] = float((C["market_signed"].abs() / C["market_abs"]).replace([np.inf], np.nan).mean())
    res["weight_A_by_target"] = C.groupby("target")["weight_A"].first().round(4).to_dict()

    # LightGBM (A1) own attribution: mean |TreeSHAP log-odds| share per group over past forecasts
    acc = {}
    for p, v in rec["provinces"].items():
        for q, d in v.get("pastDrivers", {}).items():
            ft = d.get("fiveTriggerContributions", {})
            vals = {g: abs(float(ft[g]["logOddsEffect"])) for g in ft}
            vals["other_news_volume"] = abs(float((d.get("otherContribution") or {}).get("logOddsEffect") or 0))
            vals["poverty"] = abs(float((d.get("povertyContribution") or {}).get("logOddsEffect") or 0))
            s = sum(vals.values())
            if s > 0:
                for g, x in vals.items():
                    acc.setdefault(g, []).append(x / s)
            acc.setdefault("_cpi_projection_share_of_market", []).append(
                abs(float(ft.get("market", {}).get("cpiProjectionLogOdds") or 0)) / (vals.get("market") or np.nan)
                if vals.get("market") else np.nan)
    res["lightgbm_treeshap_mean_share"] = {g: float(np.nanmean(v)) for g, v in acc.items()}
    res["lightgbm_rows"] = len(acc.get("market", []))

    # level vs change series for the report (regional means)
    LV.to_csv(OUT / "price_level_indicator.csv", index=False, lineterminator="\n")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("reproduction", "quarters_evaluated", "full_computable_quarters")}, default=str))


if __name__ == "__main__":
    main()
