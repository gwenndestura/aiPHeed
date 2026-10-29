"""PROTOCOL_LEAD2_FINAL_SIGNAL (hash checked). Stages, run in order:

    python final_signal.py study    # price predictability study + gates      -> ../out/study.json, ../out/method_rows.csv
    python final_signal.py fit      # gated candidates, selection on DEV only  -> ../out/candidates.json, ../out/candidate_rows.csv
    python final_signal.py sens     # S-EARLY, S-LAG on B0 (and the selected candidate, if any) -> ../out/sensitivity.json
    python final_signal.py groups   # five-group refitted ablation (selected candidate or B0)   -> ../out/groups.json
    python final_signal.py audit    # one post-selection audit + deliverable CSVs

Nothing is adopted, served or resealed. The 65-row Lead-2 set never selects anything.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal
from sklearn.linear_model import Ridge

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LTR = ROOT.parent / "LEAD2_FIVE_TRIGGER" / "runner"
sys.path.insert(0, str(LTR))
import final as FN  # noqa: E402
import lt_lib as T  # noqa: E402
import asof_reeval as A  # noqa: E402
import lead2_rootcause as RCII  # noqa: E402
from cr_resolve import GROUPS5, boot, holm  # noqa: E402

F, KEY = T.F, T.KEY
OUT = ROOT / "out"
DEV_LAST = F.DEV_LAST
NAMES = A.NAMES
SEED = 2031
RIDGE_X = ["A1_food", "A1_gap", "mf_l1", "mg_l1", "mf_l2", "mg_l2", "A_mom", "W_rice_yoy", "W_cereal_yoy", "W_crude_yoy"]
CONT = ["M0", "M1", "M3", "M4", "M5"]
INPUTS = {"stack_l2.csv": T.DATA / "stack_l2.csv", "asof_reeval_rows.csv": T.OUT / "asof_reeval_rows.csv",
          "labels_t43c.csv": T.EXP / "FORECAST_RESEARCH" / "data" / "labels_t43c.csv",
          "known_price_l2.csv": T.DATA / "known_price_l2.csv"}


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check():
    assert sha(ROOT / "PROTOCOL_LEAD2_FINAL_SIGNAL.md") == (HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "protocol changed"


def load():
    Lb = RCII.labels()
    E = pd.read_csv(T.OUT / "asof_reeval_rows.csv", dtype={"province_code": str})
    S = T.stack().copy()
    m = {(p, int(q)): (a, b, int(c)) for p, q, a, b, c in zip(Lb["province_code"], Lb["q"], Lb["mf"], Lb["mg"], Lb["price"])}
    get = lambda p, q, i: m[(p, q)][i] if (p, q) in m else np.nan  # noqa: E731
    S["mf_l1"] = [get(p, int(t) - 1, 0) for t, p in zip(S["t"], S["province_code"])]
    S["mg_l1"] = [get(p, int(t) - 1, 1) for t, p in zip(S["t"], S["province_code"])]
    S["mf_l2"] = [get(p, int(t) - 2, 0) for t, p in zip(S["t"], S["province_code"])]
    S["mg_l2"] = [get(p, int(t) - 2, 1) for t, p in zip(S["t"], S["province_code"])]
    S["pc_l1"] = [get(p, int(t) - 1, 2) for t, p in zip(S["t"], S["province_code"])]
    sq = S["target_q"] - 4
    known = sq <= S["t"] - 1                                    # seasonal analogue already published at O(t)
    S["mf_s"] = [get(p, int(q), 0) if k else np.nan for p, q, k in zip(S["province_code"], sq, known)]
    S["mg_s"] = [get(p, int(q), 1) if k else np.nan for p, q, k in zip(S["province_code"], sq, known)]
    S = S.merge(Lb[["province_code", "q", "mf", "mg", "price"]].rename(columns={"q": "target_q"}), on=["province_code", "target_q"], how="left")
    return Lb, E, S


# ------------------------------------------------------------------------------------------------- method forecasts
def ridge_forecasts(S: pd.DataFrame, leads) -> tuple[pd.DataFrame, list]:
    out, log = [], []
    for k in leads:
        g = S[S["lead"] == k]
        for t in sorted(g["t"].unique()):
            tr = g[(g["target_q"] <= t - 1) & g["mf"].notna()].dropna(subset=RIDGE_X)
            te = g[g["t"] == t]
            if len(tr) < 15:
                continue
            mu, sd = tr[RIDGE_X].mean(), tr[RIDGE_X].std().replace(0, 1)
            r = Ridge(alpha=10.0).fit((tr[RIDGE_X] - mu) / sd, tr[["mf", "mg"]])
            ok = te.dropna(subset=RIDGE_X)
            if len(ok):
                pr = r.predict((ok[RIDGE_X] - mu) / sd)
                out.append(ok[KEY].assign(M5_f=pr[:, 0], M5_g=pr[:, 1]))
            log.append({"lead": int(k), "origin": int(t), "train_rows": int(len(tr)), "train_max_target": int(tr["target_q"].max())})
    return pd.concat(out, ignore_index=True), log


def method_table(S, leads=(1, 2)):
    R, rlog = ridge_forecasts(S, leads)
    X = S[S["lead"].isin(leads)].merge(R, on=KEY, how="left")
    X["M0_f"], X["M0_g"] = X["A1_food"], X["A1_gap"]
    X["M1_f"], X["M1_g"] = X["mf_l1"], X["mg_l1"]
    X["M3_f"], X["M3_g"] = X["mf_s"], X["mg_s"]
    X["M4_f"] = X["mf_l1"] + .5 * (X["lead"] + 1) * (X["mf_l1"] - X["mf_l2"])
    X["M4_g"] = X["mg_l1"] + .5 * (X["lead"] + 1) * (X["mg_l1"] - X["mg_l2"])
    slog = []
    for mth in CONT:                                            # sigma / rho from the method's own earlier errors
        X[f"{mth}_P"] = np.nan
        for k in leads:
            g = X[X["lead"] == k]
            for t in sorted(g["t"].unique()):
                h = g[(g["target_q"] <= t - 1) & g["mf"].notna() & g[f"{mth}_f"].notna()]
                if len(h) < 6:
                    continue
                e = np.c_[h["mf"] - h[f"{mth}_f"], h["mg"] - h[f"{mth}_g"]]
                cov = np.cov(e.T) + np.eye(2) * 1e-6
                mvn = multivariate_normal([0, 0], cov)
                idx = g.index[(g["t"] == t) & g[f"{mth}_f"].notna()]
                X.loc[idx, f"{mth}_P"] = [1 - mvn.cdf([-a, -b]) for a, b in zip(X.loc[idx, f"{mth}_f"], X.loc[idx, f"{mth}_g"])]
                slog.append({"method": mth, "lead": int(k), "origin": int(t), "errors_used": int(len(h)), "max_error_target": int(h["target_q"].max())})
    X["M2_P"] = X["pc_l1"]
    kn = {}
    X["CLIMP_P"] = np.nan
    for t in sorted(X["t"].unique()):
        kn[t] = None
    return X, rlog, slog


def clim_price(Lb, t):
    k = Lb[Lb["q"] <= t - 1]
    return float(k["price"].mean()) if len(k) else np.nan


def cls(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float)
    k = (p >= .5).astype(int)
    tp, fp, fn, tn = int(((k == 1) & (y == 1)).sum()), int(((k == 1) & (y == 0)).sum()), int(((k == 0) & (y == 1)).sum()), int(((k == 0) & (y == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else np.nan
    spec = tn / (tn + fp) if tn + fp else np.nan
    prec = tp / (tp + fp) if tp + fp else np.nan
    f1 = 2 * prec * rec / (prec + rec) if tp else 0.0
    return {"n": int(len(y)), "high": int(y.sum()), "brier": float(np.mean((p - y) ** 2)), "accuracy": float((k == y).mean()),
            "balanced_accuracy": float(np.nanmean([rec, spec])), "precision": prec, "recall": rec, "f1": f1,
            "false_alarms": fp, "missed_high": fn, "tp_fp_fn_tn": [tp, fp, fn, tn]}


def study():
    check()
    Lb, E, S = load()
    X, rlog, slog = method_table(S)
    X["CLIMP_P"] = [clim_price(Lb, int(t)) for t in X["t"]]
    V = E[E["lead"].isin([1, 2])][KEY + ["q", "y", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "B0_price", "B0_p", "P0H4_p", "CRVER_p", "CRVER_price"]]
    V = V.merge(X[KEY + ["mf", "mg", "price"] + [f"{m}_{s}" for m in CONT for s in ("f", "g")] + [f"{m}_P" for m in CONT + ["M2", "CLIMP"]]], on=KEY, how="left")
    V["M6_P"] = V["B0_price"]
    V["split"] = np.where(V["q"] <= DEV_LAST, "DEV", "CONF")
    V["near"] = np.abs(V[["mf", "mg"]].max(axis=1)) < 1
    V["year"] = V["q"] // 4
    V.to_csv(OUT / "method_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    meths = CONT + ["M2", "M6", "CLIMP"]
    res = {"protocol_sha256": sha(ROOT / "PROTOCOL_LEAD2_FINAL_SIGNAL.md"), "input_sha256": {k: sha(v) for k, v in INPUTS.items()},
           "ridge_log": rlog, "sigma_log_max_error_target_lt_origin": all(r["max_error_target"] <= r["origin"] - 1 for r in slog),
           "ridge_train_max_target_lt_origin": all(r["train_max_target"] <= r["origin"] - 1 for r in rlog)}
    assert res["sigma_log_max_error_target_lt_origin"] and res["ridge_train_max_target_lt_origin"]
    tab = {}
    for k in (1, 2):
        for sp in ("DEV", "CONF", "ALL"):
            g = V[V["lead"] == k] if sp == "ALL" else V[(V["lead"] == k) & (V["split"] == sp)]
            for mth in meths:
                h = g[g[f"{mth}_P"].notna()]
                if not len(h):
                    continue
                pr = cls(h["price"], h[f"{mth}_P"])
                t43 = cls(h["y"], h["pi_H_AB"] * h[f"{mth}_P"])
                rm = float(np.sqrt(np.mean((h["mf"] - h[f"{mth}_f"]) ** 2))) if mth in CONT else None
                tab[f"L{k}|{sp}|{mth}"] = {"rows": int(len(h)), "coverage": float(len(h) / len(g)), "rmse_food_margin": rm,
                                          "price": pr, "t43": t43}
    res["methods"] = tab
    # same-row comparison at Lead 2 DEV (rows where every method is defined)
    g = V[(V["lead"] == 2) & (V["split"] == "DEV")].dropna(subset=[f"{m}_P" for m in meths])
    res["lead2_dev_common_rows"] = {"rows": int(len(g)), **{m: cls(g["price"], g[f"{m}_P"])["brier"] for m in meths}}
    # crossings, patterns
    cr = {}
    for k in (1, 2):
        P = Lb.sort_values("q").copy()
        P["last_known"] = P.groupby("province_code")["price"].shift(k + 1)
        P = P[P["last_known"].notna() & (P["q"] >= 8085)]
        P["cross"] = P["price"] != P["last_known"]
        P["near"] = np.abs(P[["mf", "mg"]].max(axis=1)) < 1
        cr[k] = {"rate": float(P["cross"].mean()), "rows": int(len(P)),
                 "by_year": P.groupby(P["q"] // 4)["cross"].mean().round(3).to_dict(),
                 "by_province": {NAMES[p]: round(float(v), 3) for p, v in P.groupby("province_code")["cross"].mean().items()},
                 "rate_near_threshold": float(P.loc[P["near"], "cross"].mean()), "rate_separated": float(P.loc[~P["near"], "cross"].mean()),
                 "share_rows_near": float(P["near"].mean()), "share_crossings_near": float(P.loc[P["cross"], "near"].mean())}
    res["crossings"] = cr
    W = Lb.pivot(index="q", columns="province_code", values="mf").sort_index()
    res["patterns"] = {"autocorr_mf_lag": {L: float(np.nanmean([W[c].autocorr(L) for c in W])) for L in (1, 2, 3, 4)},
                       "quarter_of_year_mean_change_mf": {int(qq + 1): float(v) for qq, v in W.diff().stack().groupby(lambda i: i[0] % 4).mean().items()},
                       "year_mean_mf": {int(y): float(v) for y, v in W.stack().groupby(lambda i: i[0] // 4).mean().items()},
                       "year_mean_price_high_share": {int(y): float(v) for y, v in Lb.groupby(Lb["q"] // 4)["price"].mean().items()}}
    # near vs separated, by year, by province at Lead 2 (ALL rows, for description only)
    g2 = V[V["lead"] == 2]
    res["lead2_strata"] = {m: {"near": cls(g2.loc[g2["near"], "price"], g2.loc[g2["near"], f"{m}_P"].fillna(.5))["accuracy"],
                               "separated": cls(g2.loc[~g2["near"], "price"], g2.loc[~g2["near"], f"{m}_P"].fillna(.5))["accuracy"],
                               "by_year_brier": {int(y): float(((h[f"{m}_P"] - h["price"]) ** 2).mean()) for y, h in g2.dropna(subset=[f"{m}_P"]).groupby("year")}}
                           for m in meths}
    res["lead2_near_rows"] = int(g2["near"].sum())
    dev2 = lambda m: tab.get(f"L2|DEV|{m}", {}).get("price", {}).get("brier", np.inf)  # noqa: E731
    res["gates"] = {"K-A": bool(min(dev2("M1"), dev2("M3")) < dev2("M0")),
                    "K-B": bool(dev2("M5") < dev2("M0") and dev2("M5") < dev2("M6")),
                    "K-E": False}
    s = T.stack()
    s2 = s[s["lead"] == 2]
    dv = s2[s2["target_q"] <= DEV_LAST]
    res["news"] = {"N1_nan_iff_articles_lt5": bool(((s2["N1"].isna()) == (s2["N1_articles"].fillna(0) < 5)).mean() > .99),
                   "nan_iff_share": float(((s2["N1"].isna()) == (s2["N1_articles"].fillna(0) < 5)).mean()),
                   "dev_coverage": float(dv["N1"].notna().mean()),
                   "coverage_by_origin_year": {int(y): float(v) for y, v in s2.groupby(s2["t"] // 4)["N1"].apply(lambda x: x.notna().mean()).items()},
                   "mean_articles_by_origin_year": {int(y): float(v) for y, v in s2.groupby(s2["t"] // 4)["N1_articles"].mean().items()}}
    res["gates"]["K-E"] = bool(res["news"]["dev_coverage"] >= .30)
    # fold-by-fold (origin) Lead-2 DEV Brier per method on the T43c target
    folds = []
    for (k, t), h in V.groupby(["lead", "t"]):
        for m in meths:
            hh = h.dropna(subset=[f"{m}_P"])
            if len(hh):
                folds.append({"lead": int(k), "origin": F.qs(int(t)), "target": F.qs(int(t) + int(k)), "split": hh["split"].iloc[0],
                              "model": f"price-method {m}", "rows": int(len(hh)), "high": int(hh["y"].sum()),
                              "t43_brier": float(((hh["pi_H_AB"] * hh[f"{m}_P"] - hh["y"]) ** 2).mean()),
                              "price_brier": float(((hh[f"{m}_P"] - hh["price"]) ** 2).mean())})
        for c in ("B0_p", "P0H4_p", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "CRVER_p"):
            folds.append({"lead": int(k), "origin": F.qs(int(t)), "target": F.qs(int(t) + int(k)), "split": h["split"].iloc[0],
                          "model": c.replace("_p", "").replace("_AB", ""), "rows": int(len(h)), "high": int(h["y"].sum()),
                          "t43_brier": float(((h[c] - h["y"]) ** 2).mean()), "price_brier": None})
    pd.DataFrame(folds).to_csv(OUT / "folds_methods.csv", index=False, lineterminator="\n", float_format="%.6g")
    (OUT / "study.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({"gates": res["gates"], "lead2_dev_common_rows": res["lead2_dev_common_rows"], "crossings": {k: {x: v[x] for x in ("rate", "rate_near_threshold", "rate_separated", "share_crossings_near")} for k, v in cr.items()},
                      "patterns": res["patterns"]["autocorr_mf_lag"], "news": {k: res["news"][k] for k in ("nan_iff_share", "dev_coverage")}}, indent=1, default=float))
    for key, v in tab.items():
        if key.startswith("L2|DEV") or key.startswith("L2|CONF"):
            print(key, v["rows"], round(v["coverage"], 2), v["rmse_food_margin"] and round(v["rmse_food_margin"], 2),
                  "price brier", round(v["price"]["brier"], 3), "acc", round(v["price"]["accuracy"], 3),
                  "| t43 brier", round(v["t43"]["brier"], 3), "rec", v["t43"]["recall"], "FA", v["t43"]["false_alarms"])


# ------------------------------------------------------------------------------------------------------ candidates
def aug(S, which):
    S = S.copy()
    if which == "K-A":
        S["LM_f"], S["LM_g"], S["SM_f"], S["SM_g"] = S["mf_l1"], S["mg_l1"], S["mf_s"], S["mg_s"]
        return S, ["LM_f", "LM_g", "SM_f", "SM_g"]
    if which == "K-B":
        R, _ = ridge_forecasts(S, sorted(S["lead"].unique()))
        S = S.merge(R.rename(columns={"M5_f": "RF_f", "M5_g": "RF_g"}), on=KEY, how="left")
        return S, ["RF_f", "RF_g"]
    if which == "K-E":
        return S, ["N1_articles"]
    raise ValueError(which)


def dev_select(ev_b, ev_c, Eb):
    b, c = ev_b["leads"], ev_c["leads"]
    g = Eb[(Eb["lead"] == 2) & (Eb["q"] <= DEV_LAST)]
    per_q = {F.qs(int(q)): float(((h["C_p"] - h["y"]) ** 2).mean() < ((h["B0_p"] - h["y"]) ** 2).mean()) for q, h in g.groupby("q")}
    pb = float(((g["B0_price"] - g["price"]) ** 2).mean())
    pc = float(((g["C_price"] - g["price"]) ** 2).mean())
    rule = {"1_L2_dev_brier_le_B0_minus_0.005": c[2]["dev"]["brier"] <= b[2]["dev"]["brier"] - .005,
            "2_L2_dev_balanced_ge_B0": c[2]["dev"]["balanced_accuracy"] >= b[2]["dev"]["balanced_accuracy"] - 1e-12,
            "3_L1_dev_brier_le_B0_plus_0.005": c[1]["dev"]["brier"] <= b[1]["dev"]["brier"] + .005,
            "4_L2_dev_price_brier_lt_B0": pc < pb,
            "5_better_in_ge_4_of_7_dev_quarters": sum(per_q.values()) >= 4,
            "6_L2_dev_beats_persistence_and_climatology": c[2]["dev"]["brier"] < min(float(((g["PERS_AB"] - g["y"]) ** 2).mean()), float(((g["CLIM_p"] - g["y"]) ** 2).mean())),
            "7_base_cutoff_features_only": True}
    return rule, {"dev_L2_brier": c[2]["dev"]["brier"], "B0_dev_L2_brier": b[2]["dev"]["brier"], "dev_L2_price_brier": pc,
                  "B0_dev_L2_price_brier": pb, "quarters_better": per_q, "dev_L1_brier": c[1]["dev"]["brier"], "B0_dev_L1_brier": b[1]["dev"]["brier"],
                  "dev_L2_balanced": c[2]["dev"]["balanced_accuracy"], "B0_dev_L2_balanced": b[2]["dev"]["balanced_accuracy"]}


def fit():
    check()
    st = json.loads((OUT / "study.json").read_text())
    Lb, E, S = load()
    origins = sorted(E["t"].unique())
    res = {"gates": st["gates"], "cands": {}}
    rows = E[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "B0_price", "B0_p"]].copy()
    evB = FN.lead_eval(rows, "B0")
    for c, ok in st["gates"].items():
        if not ok:
            res["cands"][c] = {"fitted": False, "reason": "gate failed (protocol §4)"}
            continue
        S2, new = aug(S, c)
        P = T.run(T.U2 + new, origins, S=S2)
        X = rows.merge(P[KEY + ["pi_P"]].rename(columns={"pi_P": "C_price"}), on=KEY, how="left")
        X["C_p"] = X["pi_H_AB"] * X["C_price"]
        rule, info = dev_select(evB, FN.lead_eval(X, "C"), X)
        res["cands"][c] = {"fitted": True, "new_columns": new, "coverage_lead2": {n: float(S2.loc[S2["lead"] == 2, n].notna().mean()) for n in new},
                           "rule": rule, "dev": info, "passes": all(rule.values())}
        rows[f"{c}_price"], rows[f"{c}_p"] = X["C_price"].to_numpy(), X["C_p"].to_numpy()
        print(c, json.dumps(rule), json.dumps({k: v for k, v in info.items() if k != "quarters_better"}, default=float), flush=True)
    ok = [c for c, v in res["cands"].items() if v.get("passes")]
    res["selected"] = min(ok, key=lambda c: res["cands"][c]["dev"]["dev_L2_brier"]) if ok else None
    rows.to_csv(OUT / "candidate_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    (OUT / "candidates.json").write_text(json.dumps(res, indent=1, default=float))
    print("selected:", res["selected"])


# ---------------------------------------------------------------------------------------------------- sensitivities
def run_filtered(cols, origins, S, keep_train):
    out = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        tr = tr[keep_train(tr)]
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        cfg, _ = T.select(tr, cols)
        out.append(te[KEY].assign(pi_P=T.Uni(cfg, cols).fit(tr).predict(te)))
    return pd.concat(out, ignore_index=True)


def sens():
    check()
    Lb, E, S = load()
    cand = json.loads((OUT / "candidates.json").read_text())
    origins = sorted(E["t"].unique())
    rows = E[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "B0_price", "B0_p"]].copy()
    targets = [("B0", S, T.U2)]
    if cand["selected"]:
        S2, new = aug(S, cand["selected"])
        targets.append((cand["selected"], S2, T.U2 + new))
    res = {}
    lagc = ["A3", "C3", "C4", "E1", "E2"]
    for name, SS, cols in targets:
        res[name] = {}
        P = run_filtered(cols, origins, SS, lambda tr: tr["issue_date"] >= "2023-01-06")
        prev = SS.groupby(["t", "province_code"])[lagc].first().reset_index()
        prev["t"] = prev["t"] + 1
        SL = SS.drop(columns=lagc).merge(prev, on=["t", "province_code"], how="left")
        Q = T.run(cols, origins, S=SL)
        for tag, R in (("S-EARLY", P), ("S-LAG", Q)):
            X = rows.merge(R[KEY + ["pi_P"]].rename(columns={"pi_P": "X_price"}), on=KEY, how="inner")
            X["X_p"] = X["pi_H_AB"] * X["X_price"]
            out = {}
            for k in (1, 2):
                for sp, h in (("DEV", X[(X["lead"] == k) & (X["q"] <= DEV_LAST)]), ("CONF", X[(X["lead"] == k) & (X["q"] > DEV_LAST)])):
                    base = cls(h["y"], h["B0_p"] if name == "B0" else h["pi_H_AB"] * h["B0_price"])
                    out[f"L{k}_{sp}"] = {"rows": int(len(h)), "brier": cls(h["y"], h["X_p"])["brier"], "reference_brier_same_rows": base["brier"],
                                         "accuracy": cls(h["y"], h["X_p"])["accuracy"], "recall": cls(h["y"], h["X_p"])["recall"]}
            res[name][tag] = out
        print(name, json.dumps(res[name], default=float), flush=True)
    (OUT / "sensitivity.json").write_text(json.dumps(res, indent=1, default=float))


# ----------------------------------------------------------------------------------------------------------- groups
def groups():
    check()
    Lb, E, S = load()
    cand = json.loads((OUT / "candidates.json").read_text())
    origins = sorted(E["t"].unique())
    name, SS, cols = "B0", S, T.U2
    rows = E[KEY + ["q", "y", "pi_H_AB", "B0_p"]].copy()
    full = "B0_p"
    if cand["selected"]:
        name = cand["selected"]
        SS, new = aug(S, name)
        cols = T.U2 + new
        cr = pd.read_csv(OUT / "candidate_rows.csv", dtype={"province_code": str})
        rows = rows.merge(cr[KEY + [f"{name}_p"]], on=KEY)
        full = f"{name}_p"
    out, csv = {"model": name}, []
    for g, gc in GROUPS5.items():
        Q = T.run([c for c in cols if c not in gc], origins, S=SS)
        X = rows.merge(Q[KEY + ["pi_P"]], on=KEY)
        X["x_p"] = X["pi_H_AB"] * X["pi_P"]
        out[g] = {}
        for k in (1, 2):
            for sp, h in (("DEV", X[(X["lead"] == k) & (X["q"] <= DEV_LAST)]), ("CONF", X[(X["lead"] == k) & (X["q"] > DEV_LAST)])):
                b = boot(h["q"], (h["x_p"] - h["y"]) ** 2, (h[full] - h["y"]) ** 2)
                a, f = cls(h["y"], h["x_p"]), cls(h["y"], h[full])
                out[g][f"L{k}_{sp}"] = b | {"recall_change": (a["recall"] or 0) - (f["recall"] or 0), "false_alarm_change": a["false_alarms"] - f["false_alarms"],
                                           "rows": int(len(h)), "high_quarters": int(h.loc[h["y"] == 1, "q"].nunique())}
        print(g, json.dumps({k: round(v["diff"], 4) for k, v in out[g].items()}), flush=True)
    for key in ("L1_DEV", "L2_DEV", "L1_CONF", "L2_CONF"):
        hp = holm({g: out[g][key]["p_hurts"] for g in GROUPS5})
        for g in GROUPS5:
            out[g][key]["holm_p"] = hp[g]
            d = out[g][key]
            csv.append({"model": name, "group": g, "lead": key[:2], "split": key[3:], "rows": d["rows"], "high_quarters": d["high_quarters"],
                        "delta_brier_removed_minus_full": d["diff"], "ci90_low": d["ci90"][0], "ci90_high": d["ci90"][1],
                        "p_group_helps": d["p_hurts"], "holm_p": d["holm_p"], "recall_change": d["recall_change"],
                        "false_alarm_change": d["false_alarm_change"],
                        "reading": "adds value" if d["ci90"][0] > 0 and d["holm_p"] < .10 else "possible noise" if d["ci90"][1] < 0 else "not established"})
    pd.DataFrame(csv).to_csv(ROOT / "LEAD2_TRIGGER_CONTRIBUTIONS.csv", index=False, lineterminator="\n", float_format="%.6g")
    (OUT / "groups.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"study": study, "fit": fit, "sens": sens, "groups": groups}[sys.argv[1]]()
