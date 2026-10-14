"""E28 evaluation of Objectives 2 and 4 (E28_EVALUATION_PROTOCOL.md). Run from the E28 folder:

    python -B runner/e28_evaluate.py            -> runs/e28_eval/

The runner refuses to start if the protocol hash differs from runner/E28_PROTOCOL_SHA256.txt, or if any E25 input
differs from its hash in E25_FILES_SHA256.txt. It stops before fitting if the rebuilt labels or training folds
differ from E25's (alignment check), or if any leakage assertion fails.
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard28  # noqa: E402

guard28.install()
import e28_metrics as M  # noqa: E402

warnings.filterwarnings("ignore")
EXP = guard28.EXP
E25 = guard28.E25
RUN = E25 / "runs" / "20261014T002026Z"
INP = EXP / "backend_dev" / "data" / "inputs"
FSSI = EXP / "backend_dev" / "data" / "news_e28" / "fssi_panel.csv"
OUT = EXP / "runs" / "e28_eval"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
LEADS = [1, 2, 3, 4, 5, 6]
SEED = 20261014


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def qk(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qs(k: int) -> str:
    return f"{k // 4}-Q{k % 4 + 1}"


def origin(t: int) -> pd.Timestamp:
    """O(t) = first day of quarter t+1."""
    n = t + 1
    return pd.Timestamp(year=n // 4, month=3 * (n % 4) + 1, day=1)


# ------------------------------------------------------------------------------------------------ verification
def verify_inputs() -> dict:
    want = (HERE / "E28_PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0]
    if sha(EXP / "E28_EVALUATION_PROTOCOL.md") != want:
        raise SystemExit("protocol changed after freezing: refused")
    listed = {}
    for line in (E25 / "E25_FILES_SHA256.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            listed[parts[1].strip().lstrip("*")] = parts[0]
    checked = {}
    for name in ("predictions_T1_A.csv", "predictions_T2.csv", "fold_meta_T1_A.json", "fold_meta_T2.json",
                 "details_T1_A.csv"):
        rel = f"runs/20261014T002026Z/{name}"
        got = sha(RUN / name)
        if listed.get(rel) != got:
            raise SystemExit(f"E25 input changed: {rel}")
        checked[rel] = got
    for f in ("s1_labels.csv", "d_quarterly_panel.csv", "dnow_panel.csv", "sws_rounds.csv"):
        checked[f"backend_dev/data/inputs/{f}"] = sha(INP / f)
    checked["fssi_panel.csv"] = sha(FSSI) if FSSI.exists() else None
    checked["protocol"] = want
    return checked


# ------------------------------------------------------------------------------------------------ labels
class Target:
    """E25's label logic, reimplemented: T1 = H + 2D (H = mean of definition-A production rounds of the quarter,
    usable after the last round's publication); T2 = D. Label of q usable at O(t) iff q <= t-1 (and, for T1, the
    quarter's last round was published before O(t)). tau = median of usable labels (T1) or 0 (T2)."""

    def __init__(self, name: str, rounds: pd.DataFrame, D: pd.DataFrame):
        self.name = name
        if name == "T1_A":
            ru = rounds[rounds["definition_A"].astype(str).str.lower().eq("true")
                        & rounds["source"].str.startswith("production")].copy()
            ru["published_eff"] = pd.to_datetime(ru["published_eff"])
            H = ru.groupby("quarter")["H"].mean()
            self.maxpub = ru.groupby("quarter")["published_eff"].max()
            v = D.merge(H.rename("H").reset_index(), on="quarter", how="inner")
            v["v"] = v["H"] + 2 * v["D"]
        else:
            v = D.assign(v=D["D"])
            self.maxpub = None
        v = v[["province_code", "quarter", "v"]].copy()
        v["tq"] = v["quarter"].map(qk)
        assert v["tq"].min() >= qk("2021-Q1"), "pre-2021 label"
        self.V = v.sort_values(["tq", "province_code"]).reset_index(drop=True)
        self._pub: dict = {}

    def pub(self, q: str, t: int) -> bool:
        key = (q, t)
        if key not in self._pub:
            ok = qk(q) <= t - 1
            if ok and self.maxpub is not None:
                ok = q in self.maxpub.index and bool(self.maxpub[q] < origin(t))
            self._pub[key] = ok
        return self._pub[key]

    def published(self, t: int) -> pd.DataFrame:
        return self.V[self.V["quarter"].map(lambda q: self.pub(q, t))]

    def tau(self, t: int) -> float:
        return 0.0 if self.name == "T2" else float(self.published(t)["v"].median())

    def last_value(self, t: int, p: str) -> float:
        g = self.published(t)
        g = g[g["province_code"] == p].sort_values("tq")
        return float(g["v"].iloc[-1]) if len(g) else np.nan


def training_pairs(T: Target, t: int, k: int, tau: float) -> pd.DataFrame:
    rows = []
    for r in T.V.itertuples():
        tp = r.tq - k
        if tp < qk("2021-Q1") or not T.pub(r.quarter, t):
            continue
        last = T.last_value(tp, r.province_code)
        rows.append({"province_code": r.province_code, "t": tp, "target_quarter": r.quarter, "v": r.v,
                     "y": int(r.v > tau), "v_last": last, "margin_last": last - tau,
                     "y_last": float(last > tau) if last == last else np.nan})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ features
NEWS = ["FSSI", "FSSI_lag1", "FSSI_accel", "log_n_fssi", "news_missing"]
GOV = ["Dnow", "D_lag1", "F_lag1", "dD"]
PERSIST = ["margin_last", "y_last"]


def feature_panel() -> pd.DataFrame:
    d = pd.read_csv(INP / "d_quarterly_panel.csv")
    dn = pd.read_csv(INP / "dnow_panel.csv")
    grid = pd.MultiIndex.from_product([PROVS, [qs(k) for k in range(qk("2021-Q1"), qk("2026-Q2") + 1)]],
                                      names=["province_code", "quarter"]).to_frame(index=False)
    grid["tq"] = grid["quarter"].map(qk)
    d["tq"] = d["quarter"].map(qk)
    lag = d.assign(tq=d["tq"] + 1).rename(columns={"D": "D_lag1", "F": "F_lag1"})[["province_code", "tq", "D_lag1", "F_lag1"]]
    X = grid.merge(lag, on=["province_code", "tq"], how="left").merge(
        dn[["province_code", "quarter", "Dnow"]], on=["province_code", "quarter"], how="left")
    X["dD"] = X["Dnow"] - X["D_lag1"]
    if FSSI.exists():
        f = pd.read_csv(FSSI)
        f = f[["province_code", "quarter", "FSSI", "FSSI_lag1", "FSSI_accel", "n_in_fssi", "evidence_status"]]
        X = X.merge(f, on=["province_code", "quarter"], how="left")
    else:
        for c in ("FSSI", "FSSI_lag1", "FSSI_accel", "n_in_fssi"):
            X[c] = np.nan
        X["evidence_status"] = "NOT_BUILT"
    X["log_n_fssi"] = np.log1p(X["n_in_fssi"].fillna(0))
    X["news_missing"] = X["FSSI"].isna().astype(float)
    return X


def leakage_checks(X: pd.DataFrame) -> dict:
    out = {}
    # 2021-Q1 lags must be NaN (no pre-2021 values)
    q1 = X[X["quarter"] == "2021-Q1"]
    out["no_pre2021_lag_values"] = bool(q1["D_lag1"].isna().all() and q1["F_lag1"].isna().all()
                                       and q1["FSSI_lag1"].isna().all())
    # every FSSI cell is built only from articles published inside its own quarter (checked on the store)
    store = EXP / "backend_dev" / "data" / "news_e28" / "articles.jsonl"
    bad = 0
    n = 0
    if store.exists():
        for line in store.read_text(encoding="utf-8").splitlines():
            try:
                a = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += 1
            ts = pd.Timestamp(a["published_ph"])
            if f"{ts.year}-Q{(ts.month - 1) // 3 + 1}" != a["quarter"] or ts >= pd.Timestamp("2026-07-01", tz="Asia/Manila"):
                bad += 1
    out["articles_checked"] = n
    out["articles_outside_their_quarter_or_after_limit"] = bad
    out["feature_quarters_max"] = X["quarter"].max()
    for k, v in out.items():
        if (k.startswith("no_") and v is False) or (k == "articles_outside_their_quarter_or_after_limit" and v):
            raise SystemExit(f"leakage assertion failed: {k}={v}")
    return out


# ------------------------------------------------------------------------------------------------ models
def _lr(Xtr, ytr, Xte):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    med = np.nanmedian(Xtr, axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    a = np.where(np.isnan(Xtr), med, Xtr)
    b = np.where(np.isnan(Xte), med, Xte)
    keep = a.std(axis=0) > 0
    if not keep.any():
        return np.full(len(Xte), ytr.mean())
    sc = StandardScaler().fit(a[:, keep])
    m = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(a[:, keep]), ytr)
    return m.predict_proba(sc.transform(b[:, keep]))[:, 1]


LGB_FIXED = dict(num_leaves=3, min_child_samples=10, n_estimators=50, learning_rate=0.1, subsample=1.0,
                 colsample_bytree=1.0, random_state=SEED, verbose=-1)
GRID = [dict(num_leaves=nl, min_child_samples=mc, n_estimators=ne, class_weight=cw, learning_rate=0.05)
        for nl in (3, 7) for mc in (5, 10, 20) for ne in (50, 150) for cw in (None, "balanced")]


def _lgb(Xtr, ytr, Xte, cfg=None, return_model=False):
    import lightgbm as lgb

    c = dict(LGB_FIXED)
    if cfg:
        c.update(cfg)
        c.setdefault("random_state", SEED)
        c["verbose"] = -1
    m = lgb.LGBMClassifier(**c).fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    return (p, m) if return_model else p


def _nested_cfg(tr: pd.DataFrame, cols: list[str]) -> dict:
    """Inner expanding-window selection on the training target quarters only (protocol section 3, candidate 1)."""
    tqs = sorted(tr["target_quarter"].map(qk).unique())
    inner = tqs[-3:] if len(tqs) >= 6 else []
    if not inner:
        return {"cfg": GRID[0], "inner_folds": 0}
    best, best_s = GRID[0], np.inf
    for cfg in GRID:
        losses = []
        for iq in inner:
            a = tr[tr["target_quarter"].map(qk) < iq]
            b = tr[tr["target_quarter"].map(qk) == iq]
            if a["y"].nunique() < 2 or len(b) == 0:
                continue
            p = _lgb(a[cols].to_numpy(float), a["y"].to_numpy(int), b[cols].to_numpy(float), cfg)
            losses.append(float(((p - b["y"].to_numpy()) ** 2).mean()))
        s = np.mean(losses) if losses else np.inf
        if s < best_s - 1e-12:
            best, best_s = cfg, s
    return {"cfg": best, "inner_folds": len(inner), "inner_brier": float(best_s)}


ARMS_FIT = {
    "PSA_LR": ("lr", GOV), "PSA_LGBM": ("lgb", GOV),
    "NLP_LR": ("lr", NEWS), "NLP_LGBM": ("lgb", NEWS),
    "LR_COMB": ("lr", NEWS + GOV), "PROPOSED": ("lgb", NEWS + GOV),
    "PROPOSED_NESTED": ("lgb_nested", NEWS + GOV), "PROPOSED_PERSIST": ("lgb", NEWS + GOV + PERSIST),
    "LR_STRUCT": ("lr", PERSIST + ["dD", "FSSI_accel"]),
}


def run_target(name: str, rounds, D, X, align_only: bool = False) -> tuple[pd.DataFrame, dict, dict]:
    T = Target(name, rounds, D)
    E = pd.read_csv(RUN / f"predictions_{name}.csv")
    meta = json.loads((RUN / f"fold_meta_{name}.json").read_text(encoding="utf-8"))
    b1 = E[E["model"] == "B1_naive_persistence"].copy()
    align = {"folds": 0, "train_rows_match": 0, "test_rows_match": 0, "mismatches": []}
    preds = []
    shap_rows = []
    nested_log = []
    Xi = X.set_index(["province_code", "tq"])
    for (lead, t), g in b1.groupby(["lead", "t"]):
        tk = qk(t)
        tau = T.tau(tk)
        tr = training_pairs(T, tk, int(lead), tau)
        fm = meta.get(f"{name}|k{int(lead)}|{t}")
        align["folds"] += 1
        # compare every field E25 recorded for this fold (E25's fold_meta keeps different fields per fold)
        mine = {"n_train_rows": len(tr), "n_train_quarters": int(tr["target_quarter"].nunique()) if len(tr) else 0,
                "train_HIGH": int(tr["y"].sum()) if len(tr) else 0,
                "train_LOW": int((1 - tr["y"]).sum()) if len(tr) else 0, "tau": tau,
                "test_HIGH": int(g["y"].sum()), "test_LOW": int((1 - g["y"]).sum())}
        compared = {k: (mine[k], fm[k]) for k in mine if fm is not None and k in fm}
        ok_tr = fm is not None and all((abs(a - b) < 1e-9) if isinstance(b, float) else a == b
                                       for a, b in compared.values())
        align.setdefault("fields_compared", {})
        for k in compared:
            align["fields_compared"][k] = align["fields_compared"].get(k, 0) + 1
        te = g.sort_values("province_code")
        y_mine = [int(T.V[(T.V.province_code == p) & (T.V.quarter == q)]["v"].iloc[0] > tau)
                  for p, q in zip(te["province_code"], te["target_quarter"])]
        ok_te = list(te["y"].astype(int)) == y_mine and np.allclose(te["threshold"], tau)
        align["train_rows_match"] += ok_tr
        align["test_rows_match"] += ok_te
        if not (ok_tr and ok_te):
            align["mismatches"].append({"lead": int(lead), "t": t, "train": ok_tr, "test": ok_te,
                                        "compared": compared})
            continue
        # leakage: no test (province, target) in training; no training label from a quarter >= t
        assert not set(zip(tr["province_code"], tr["target_quarter"])) & set(zip(te["province_code"], te["target_quarter"]))
        assert tr["target_quarter"].map(qk).max() <= tk - 1
        if align_only:
            continue
        Ftr = tr.join(Xi, on=["province_code", "t"])
        te2 = te.assign(tq=tk, margin_last=te["v_last"] - tau, y_last=te["y_last"].astype(float))
        Fte = te2.join(Xi, on=["province_code", "tq"], rsuffix="_x")
        ytr = Ftr["y"].to_numpy(int)
        base = {"target": name, "lead": int(lead), "t": t, "target_quarter": None}
        for i, r in enumerate(te.itertuples()):
            row = {**base, "target_quarter": r.target_quarter, "province_code": r.province_code, "y": int(r.y)}
            preds.append({**row, "arm": "B1", "p": float(r.score)})
            preds.append({**row, "arm": "ALWAYS_HIGH", "p": 1 - 1e-6})
            preds.append({**row, "arm": "CLIM", "p": float(ytr.mean())})
            preds.append({**row, "arm": "MAJ", "p": float(ytr.mean() >= 0.5)})
        for arm, (kind, cols) in ARMS_FIT.items():
            Xtr_, Xte_ = Ftr[cols].to_numpy(float), Fte[cols].to_numpy(float)
            if len(np.unique(ytr)) < 2:
                p = np.full(len(Fte), float(ytr.mean()))
            elif kind == "lr":
                p = _lr(Xtr_, ytr, Xte_)
            elif kind == "lgb":
                p, mdl = _lgb(Xtr_, ytr, Xte_, return_model=True)
                if arm == "PROPOSED":
                    contrib = mdl.predict_proba(Xte_, pred_contrib=True) if False else mdl.booster_.predict(Xte_, pred_contrib=True)
                    raw = mdl.booster_.predict(Xte_, raw_score=True)
                    for j, r in enumerate(te.itertuples()):
                        c = contrib[j]
                        shap_rows.append({"target": name, "lead": int(lead), "t": t, "province_code": r.province_code,
                                          "expected_value": float(c[-1]),
                                          **{f"shap_{col}": float(c[ci]) for ci, col in enumerate(cols)},
                                          "raw_margin": float(raw[j]),
                                          "additivity_error": float(abs(c.sum() - raw[j])), "p": float(p[j])})
            else:
                sel = _nested_cfg(Ftr.assign(y=ytr), cols)
                nested_log.append({"target": name, "lead": int(lead), "t": t, **{k: v for k, v in sel.items()}})
                p = _lgb(Xtr_, ytr, Xte_, sel["cfg"])
            for j, r in enumerate(te.itertuples()):
                preds.append({**base, "target_quarter": r.target_quarter, "province_code": r.province_code,
                              "y": int(r.y), "arm": arm, "p": float(p[j])})
        # the original E25 arms for the same rows (not refitted)
        for e_arm, my in (("PROPOSED_lgbm_combined", "PROPOSED_E25"), ("PCF21", "PCF21_E25"),
                          ("M4_21", "M4_21_E25"), ("B1p_calibrated_persistence", "B1p_E25")):
            sub = E[(E["model"] == e_arm) & (E["lead"] == lead) & (E["t"] == t)]
            for r in sub.itertuples():
                preds.append({**base, "target_quarter": r.target_quarter, "province_code": r.province_code,
                              "y": int(r.y), "arm": my, "p": float(r.score)})
    return pd.DataFrame(preds), align, {"shap": shap_rows, "nested": nested_log}


# ------------------------------------------------------------------------------------------------ scoring
REFS = ["B1", "ALWAYS_HIGH", "CLIM", "MAJ", "PSA_LR", "PSA_LGBM", "NLP_LR", "NLP_LGBM", "LR_COMB"]


def summarize(P: pd.DataFrame) -> dict:
    res = {}
    for (tg, arm), g in P.groupby(["target", "arm"]):
        d = res.setdefault(tg, {}).setdefault(arm, {"by_lead": {}, "pooled": None})
        for lead, h in g.groupby("lead"):
            m = M.point_metrics(h["y"], h["p"])
            nd = h["t"].nunique()
            d["by_lead"][int(lead)] = {**m, "dates": int(nd), "flags": M.flags(m, nd), **M.bootstrap(h)}
        pooled = g.copy()
        m = M.point_metrics(pooled["y"], pooled["p"])
        nd = pooled["t"].nunique()
        d["pooled"] = {**m, "dates": int(nd), "flags": M.flags(m, nd)}
        d["province_view"] = {p: {"n": int(len(h)), "HIGH": int(h["y"].sum()),
                                  "accuracy": float(((h["p"] >= 0.5).astype(int) == h["y"]).mean()),
                                  "label": "shared regional outcome; not an independent provincial evaluation"}
                              for p, h in g.groupby("province_code")}
    return res


def paired(P: pd.DataFrame, tg: str, arm: str, leads=None) -> dict:
    sub = P[(P["target"] == tg)] if leads is None else P[(P["target"] == tg) & (P["lead"].isin(leads))]
    out = {}
    a = sub[sub["arm"] == arm]
    if a.empty:
        return out
    # per date (origin): mean over all leads and provinces issued at that origin (E27 M1 unit)
    la = M.per_date_losses(a)
    for ref in REFS:
        if ref == arm:
            continue
        r = sub[sub["arm"] == ref]
        if r.empty:
            continue
        lr = M.per_date_losses(r)
        j = la.join(lr, lsuffix="_a", rsuffix="_r", how="inner")
        out[ref] = {"dates": int(len(j)),
                    "acc_diff_mean": float((j["err_r"] - j["err_a"]).mean()),
                    "brier_diff_mean": float((j["bri_r"] - j["bri_a"]).mean()),
                    "p_acc": M.signflip_p(j["err_r"] - j["err_a"]),
                    "p_brier": M.signflip_p(j["bri_r"] - j["bri_a"])}
    ha = M.holm({k: v["p_acc"] for k, v in out.items()})
    hb = M.holm({k: v["p_brier"] for k, v in out.items()})
    for k in out:
        out[k]["holm_acc"], out[k]["holm_brier"] = ha[k], hb[k]
    return out


def reliable_lead(P, S, tg, arm, lead) -> dict:
    """C6 (E23/E25): evaluable (>= 8 dates, >= 5 HIGH, >= 5 LOW), AUC bootstrap lower bound > 0.5, Brier beats B1
    with one-sided sign-flip p < 0.05."""
    s = S[tg].get(arm, {}).get("by_lead", {}).get(lead)
    if s is None:
        return {"reliable": False, "why": "no rows"}
    ev = s["dates"] >= 8 and s["HIGH"] >= 5 and s["LOW"] >= 5
    why = []
    if not ev:
        why.append(f"not evaluable: dates={s['dates']} HIGH={s['HIGH']} LOW={s['LOW']} (needs >= 8, >= 5, >= 5)")
    lo = (s.get("auc_ci95") or [None])[0]
    auc_ok = lo is not None and lo > 0.5
    if not auc_ok:
        why.append(f"AUC bootstrap lower bound {lo}")
    pt = paired(P, tg, arm, leads=[lead]).get("B1", {})
    br_ok = pt.get("p_brier") is not None and pt["p_brier"] < 0.05 and pt["brier_diff_mean"] > 0
    if not br_ok:
        why.append(f"Brier vs B1 p={pt.get('p_brier')} diff={pt.get('brier_diff_mean')}")
    return {"evaluable": ev, "auc_lower": lo, "brier_vs_B1": pt, "reliable": bool(ev and auc_ok and br_ok), "why": why}


def reachability(S, tg, lead) -> dict:
    s = S[tg]["B1"]["by_lead"].get(lead)
    if s is None:
        return {}
    return {"dates": s["dates"], "HIGH": s["HIGH"], "LOW": s["LOW"],
            "C6_evaluable_possible": bool(s["dates"] >= 8 and s["HIGH"] >= 5 and s["LOW"] >= 5),
            "missing_LOW_rows": max(0, 5 - s["LOW"]), "missing_HIGH_rows": max(0, 5 - s["HIGH"]),
            "missing_dates": max(0, 8 - s["dates"])}


def main():
    inputs = verify_inputs()
    rounds = pd.read_csv(INP / "sws_rounds.csv")
    D = pd.read_csv(INP / "d_quarterly_panel.csv")
    X = feature_panel()
    leak = leakage_checks(X)
    if "--alignment-only" in sys.argv:          # no model is fitted and no outer metric is computed
        al = {tg: run_target(tg, rounds, D, X, align_only=True)[1] for tg in ("T1_A", "T2")}
        out = {"inputs": inputs, "leakage": leak, "alignment": al}
        dst = EXP / "runs" / "e28_alignment_check.json"
        dst.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        print(json.dumps({tg: {k: v for k, v in a.items() if k != "mismatches"} | {"n_mismatch": len(a["mismatches"])}
                          for tg, a in al.items()}, indent=1))
        if any(a["mismatches"] for a in al.values()):
            print(json.dumps({tg: a["mismatches"][:5] for tg, a in al.items()}, indent=1, default=str))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    allP, aligns, extras = [], {}, {}
    for tg in ("T1_A", "T2"):
        P, al, ex = run_target(tg, rounds, D, X)
        aligns[tg], extras[tg] = al, ex
        if al["mismatches"]:
            (OUT / "alignment.json").write_text(json.dumps(aligns, indent=1, default=str), encoding="utf-8")
            raise SystemExit(f"alignment check failed for {tg}: {al['mismatches'][:3]}")
        allP.append(P)
    P = pd.concat(allP, ignore_index=True)
    S = summarize(P)
    arms = sorted(P["arm"].unique())
    det = {}
    tests = {}
    for tg in ("T1_A", "T2"):
        tests[tg] = {a: paired(P, tg, a) for a in arms if a not in ("ALWAYS_HIGH",)}
        rel = {a: {L: reliable_lead(P, S, tg, a, L) for L in LEADS} for a in arms}
        qual = {}
        for a in arms:
            t = tests[tg].get(a, {})
            refs = [r for r in REFS if r != a and r in t]
            qual[a] = bool(refs) and all(t[r]["holm_acc"] is not None and t[r]["holm_acc"] < 0.05
                                         and t[r]["holm_brier"] is not None and t[r]["holm_brier"] < 0.05
                                         and t[r]["acc_diff_mean"] > 0 and t[r]["brier_diff_mean"] > 0 for r in refs)
        furthest = {a: max([L for L in LEADS if rel[a][L]["reliable"]], default=None) for a in arms}
        det[tg] = {"reachability_by_lead": {L: reachability(S, tg, L) for L in LEADS},
                   "reliable_leads": {a: [L for L in LEADS if rel[a][L]["reliable"]] for a in arms},
                   "furthest_reliable_horizon": {a: (furthest[a] if furthest[a] is not None
                                                     else "not determinable on the available outcomes") for a in arms},
                   "qualifies_E27_rule_pooled": qual,
                   "reliability_detail": rel,
                   "status": "development evidence only (every 2021-2026Q2 outcome was examined before E28)"}
    det["T2"]["note"] = "T2 (D > 0) is a constructed provincial price-pressure indicator, never a food-insecurity forecast."
    P.sort_values(["target", "arm", "lead", "t", "province_code"]).to_csv(OUT / "predictions.csv", index=False,
                                                                          lineterminator="\n")
    shap = pd.DataFrame(extras["T1_A"]["shap"] + extras["T2"]["shap"])
    shap.to_csv(OUT / "shap_proposed.csv", index=False, lineterminator="\n")
    res = {"inputs": inputs, "leakage": leak, "alignment": aligns, "summary": S, "paired_pooled": tests,
           "nested_selection": {tg: extras[tg]["nested"] for tg in extras},
           "shap_additivity_max_error": float(shap["additivity_error"].max()) if len(shap) else None}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str, sort_keys=True), encoding="utf-8")
    (OUT / "E28_DETERMINATION.json").write_text(json.dumps(det, indent=1, default=str, sort_keys=True),
                                                encoding="utf-8")
    print(json.dumps({tg: {"furthest": {a: det[tg]["furthest_reliable_horizon"][a] for a in
                                        ("PROPOSED", "PROPOSED_NESTED", "PROPOSED_PERSIST", "LR_STRUCT", "B1",
                                         "PCF21_E25", "M4_21_E25") if a in det[tg]["furthest_reliable_horizon"]},
                           "qualifies": {a: v for a, v in det[tg]["qualifies_E27_rule_pooled"].items() if v},
                           "reach": {L: det[tg]["reachability_by_lead"][L] for L in (1, 2, 3)}}
                      for tg in det}, indent=1, default=str))


if __name__ == "__main__":
    main()
