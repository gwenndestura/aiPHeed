"""Independent verification of the reported CH1-LGBM results (Addendum 3, verification analyses).

    python verify.py labels      # T43c rebuilt from raw files, compared with the evaluated labels
    python verify.py metrics     # metrics recomputed from the saved audited predictions (plain numpy)
    python verify.py repro       # horizon.py predictions (fresh run) vs the saved audited predictions
    python verify.py leakage     # issue-date checks on every test row and training set + perturbation at every origin
    python verify.py all

Outputs: out/verify_*.json.
"""
from __future__ import annotations

import dataclasses
import json
import sys

from common import AUDITED, B, C, E, EXP, FM, L, OUT, np, pd, setup

RAW_CPI = EXP / "FIRI_V2_DATA_AUDIT" / "data" / "raw" / "psa_cpi_ACP22.csv"
SWS = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "sws_area_rounds_2021.csv"
SPEC = EXP / "E40_SWS_CPI_Tiers" / "label_spec.json"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LEADS = (0, 1, 2, 3, 4)


def _preds(k):
    return pd.read_csv(AUDITED / f"predictions_lead{k}.csv", dtype={"province_code": str})


# ------------------------------------------------------------------------------------------------ labels
def rebuild_labels() -> pd.DataFrame:
    """T43c from raw files only: SWS non-commissioned Balance Luzon rounds (quarter mean), PSA CPI index -> monthly
    YoY -> quarter mean of 3 months, frozen E40 thresholds. No aiPHeed library code."""
    th = json.loads(SPEC.read_text(encoding="utf-8"))["thresholds"]
    s = pd.read_csv(SWS)
    s = s[~s["commissioned"].astype(str).str.lower().isin(["true", "1", "yes"])]
    s = s[(s["quarter"] >= "2021-Q1") & (s["quarter"] <= "2026-Q3")]
    H = s.groupby("quarter")["balance_luzon"].mean()
    raw = pd.read_csv(RAW_CPI)
    name_to_code = {v: k for k, v in L.NAMES.items()}
    recs = []
    for r in raw.itertuples(index=False):
        geo = str(r[0]).strip(". ")
        if geo not in name_to_code:
            continue
        com = "food" if "FOOD" in str(r[1]) else "all_items"
        for col, v in zip(raw.columns[2:], r[2:]):
            yr, m = col.split()
            if m in MON and pd.notna(v) and str(v).strip() not in ("", "..", "-"):
                recs.append({"province_code": name_to_code[geo], "com": com, "ym": int(yr) * 12 + MON.index(m),
                             "idx": float(v)})
    I = pd.DataFrame(recs).set_index(["province_code", "com", "ym"])["idx"].sort_index()
    prev = I.copy()
    prev.index = pd.MultiIndex.from_tuples([(p, c, m + 12) for p, c, m in I.index], names=I.index.names)
    yoy = (100 * (I / prev.reindex(I.index) - 1)).dropna().reset_index(name="yoy")
    yoy = yoy[yoy["ym"] >= 2021 * 12]
    yoy["quarter"] = [f"{m // 12}-Q{(m % 12) // 3 + 1}" for m in yoy["ym"]]
    g = yoy.groupby(["province_code", "com", "quarter"])["yoy"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] == 3].pivot_table(index=["province_code", "quarter"], columns="com", values="mean").reset_index()
    g = g[g["quarter"].isin(H.index)].copy()
    g["H"] = g["quarter"].map(H)
    g["price"] = ((g["food"] > g["province_code"].map(th["food"])) |
                  ((g["food"] - g["all_items"]) > g["province_code"].map(th["gap"]))).astype(int)
    g["hunger"] = (g["H"] > th["H"]).astype(int)
    g["y"] = (g["price"] & g["hunger"]).astype(int)
    return g


def phase_labels():
    g = rebuild_labels().rename(columns={"quarter": "target_quarter"})
    out = {"independent_labelled_province_quarters": int(len(g)),
           "independent_quarters": int(g["target_quarter"].nunique()),
           "independent_high": int(g["y"].sum()), "leads": {}}
    for k in LEADS:
        P = _preds(k)
        m = P.merge(g, on=["province_code", "target_quarter"], suffixes=("", "_ind"), how="left")
        dif = m[(m["y"] != m["y_ind"]) | m["y_ind"].isna()]
        out["leads"][k] = {"rows": int(len(P)), "matched": int(m["y_ind"].notna().sum()),
                           "label_disagreements": dif[["province_code", "target_quarter", "y", "y_ind", "food",
                                                       "all_items"]].to_dict("records"),
                           "hunger_disagreements": int((m["hunger"] != m["hunger_ind"]).sum()),
                           "price_disagreements": int((m["price"] != m["price_ind"]).sum())}
        print(k, out["leads"][k]["rows"], out["leads"][k]["matched"], len(dif))
    first = min(_preds(k)["target_quarter"].min() for k in LEADS)
    out["threshold_window"] = json.loads(SPEC.read_text(encoding="utf-8"))["thresholds"]["window"]
    out["first_evaluated_target_quarter"] = first
    out["thresholds_set_before_evaluation"] = out["threshold_window"][1] < first
    FM.write_json(OUT / "verify_labels.json", out)


# ------------------------------------------------------------------------------------------------ metrics
def _m(y, p):
    yh = (p >= 0.5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    tn, fn = int(((yh == 0) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    n = len(y)
    rec = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    return {"n": n, "correct": tp + tn, "accuracy": (tp + tn) / n, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "high": int(y.sum()), "low": int(n - y.sum()), "balanced_accuracy": (rec + spec) / 2,
            "precision": tp / (tp + fp) if tp + fp else float("nan"), "recall": rec,
            "brier": float(np.mean((np.clip(p, 0, 1) - y) ** 2))}


def phase_metrics():
    rep = json.loads((AUDITED / "results.json").read_text(encoding="utf-8"))
    out = {}
    for k in LEADS:
        P = _preds(k)
        y = P["y"].astype(int).to_numpy()
        cols = ["CH1"] + [c[:-2] for c in P.columns if c.endswith("_p") and c != "CH1_p"]
        out[k] = {c: _m(y, P[f"{c}_p"].to_numpy(float)) for c in cols}
        r = rep["leads"][str(k)]["metrics"]
        out[k]["matches_reported"] = bool(abs(out[k]["CH1"]["accuracy"] - r["accuracy"]) < 1e-9
                                          and out[k]["CH1"]["tp"] == r["tp"] and out[k]["CH1"]["fn"] == r["fn"]
                                          and abs(out[k]["CH1"]["brier"] - r["brier"]) < 1e-3)
        print(k, out[k]["CH1"]["correct"], "/", out[k]["CH1"]["n"], round(out[k]["CH1"]["accuracy"], 3),
              out[k]["matches_reported"])
    FM.write_json(OUT / "verify_metrics.json", out)


# ------------------------------------------------------------------------------------------------ reproduction
def phase_repro():
    out = {}
    for k in LEADS:
        a = _preds(k)
        b = pd.read_csv(OUT / f"horizon_predictions_lead{k}.csv", dtype={"province_code": str})
        m = a.merge(b, on=["province_code", "q"], suffixes=("_a", "_b"))
        out[k] = {"rows_saved": int(len(a)), "rows_fresh": int(len(b)), "matched": int(len(m)),
                  "max_abs_diff_CH1_p": float((m["CH1_p_a"] - m["CH1_p_b"]).abs().max()),
                  "same_labels": bool((m["y_a"] == m["y_b"]).all())}
        print(k, out[k])
    FM.write_json(OUT / "verify_repro.json", out)


# ------------------------------------------------------------------------------------------------ leakage
def _release(ym: str) -> pd.Timestamp:
    return pd.Timestamp(ym + "-01") + pd.offsets.MonthEnd(0) + pd.Timedelta(days=5)


def _last_month(q: int) -> int:
    return (q // 4) * 12 + (q % 4) * 3 + 2


def phase_leakage():
    setup()
    d, x = E.data()
    out = {"row_checks": {}, "training_checks": {}}
    for k in LEADS:
        P = _preds(k)
        iss = pd.to_datetime(P["issue_date"])
        sws_ok = pd.to_datetime(P["sws_newest_published"]) < iss
        cpi_ok = P["psa_newest_month"].map(_release) < iss
        nw = pd.to_datetime(P["news_latest_published"], errors="coerce")
        news_ok = nw.isna() | (nw < iss)
        tgt = (P["q"] == P["t"] + k)
        out["row_checks"][k] = {"rows": int(len(P)), "sws_published_before_issue": int(sws_ok.sum()),
                                "cpi_released_before_issue": int(cpi_ok.sum()), "news_before_issue": int(news_ok.sum()),
                                "target_is_origin_plus_lead": int(tgt.sum()),
                                "min_cpi_margin_days": int((iss - P["psa_newest_month"].map(_release)).dt.days.min()),
                                "min_sws_margin_days": int((iss - pd.to_datetime(P["sws_newest_published"])).dt.days.min())}
        X = C.build_X(k)
        tc = []
        for t in sorted(P["t"].unique()):
            t = int(t)
            tr = B.price_rows(X, t, k)
            tc.append({"origin": L.qs(t), "train_rows": int(len(tr)),
                       "train_origins_before_t": bool(tr["t"].max() < t),
                       "train_targets_le_t_minus_1": bool(tr["q"].max() <= t - 1),
                       "train_target_cpi_published_at_issue": bool(all(_last_month(int(q)) <= L.m0_of(t)
                                                                       for q in tr["q"]))})
        out["training_checks"][k] = {"origins": len(tc),
                                     "all_pass": all(v for c in tc for v in c.values() if isinstance(v, bool)),
                                     "detail": tc}
        print(k, out["row_checks"][k], out["training_checks"][k]["all_pass"], flush=True)
    out["perturbation"] = perturb_all(d, x)
    out["passed"] = bool(all(v["sws_published_before_issue"] == v["rows"] == v["cpi_released_before_issue"]
                             == v["news_before_issue"] == v["target_is_origin_plus_lead"]
                             for v in out["row_checks"].values())
                         and all(v["all_pass"] for v in out["training_checks"].values())
                         and out["perturbation"]["all_identical"])
    FM.write_json(OUT / "verify_leakage.json", out)
    print("leakage passed:", out["passed"])


def perturb_all(d, x) -> dict:
    """run_ch1.phase_audit's perturbation (future SWS, CPI and news randomised) at every Lead-1 and Lead-2 test origin;
    a forecast must not change."""
    sys.path.insert(0, str(C.HERE))
    import run_ch1 as RC
    rng = np.random.default_rng(C.SEED + 3)
    o_rounds, o_gkg = C.FM.rounds.__wrapped__, C.NF.gkg.__wrapped__
    res = []

    def set_rounds(pr):
        C.FM.rounds = (lambda dataset="primary", _p=pr: _p if dataset == "primary" else o_rounds(dataset)) \
            if pr is not None else C.FM.functools.lru_cache(maxsize=2)(o_rounds)
        if not hasattr(C.FM.rounds, "cache_clear"):
            C.FM.rounds.cache_clear = lambda: None

    def set_gkg(pg):
        C.NF.gkg = (lambda _g=pg: _g) if pg is not None else C.FM.functools.lru_cache(maxsize=1)(o_gkg)
        if not hasattr(C.NF.gkg, "cache_clear"):
            C.NF.gkg.cache_clear = lambda: None

    for k in (1, 2):
        for t in sorted(_preds(k)["t"].unique()):
            t = int(t)
            RC._clear()
            base = RC.forecast_at(t, k, d, x)
            iss, m0 = E.issue(t), L.m0_of(t)
            r0 = o_rounds("primary").copy()
            fut = r0["published"] >= iss
            r0.loc[fut, "H"] = rng.uniform(0, 50, int(fut.sum()))
            yo, ix = d.yoy.copy(), d.idx.copy()
            yo.loc[yo["ym"] > m0, "yoy"] = rng.uniform(-10, 20, int((yo["ym"] > m0).sum()))
            ix.loc[ix["ym"] > m0, "index"] = rng.uniform(80, 160, int((ix["ym"] > m0).sum()))
            dp = dataclasses.replace(d, yoy=yo, idx=ix)
            g0 = o_gkg().copy()
            gf = g0["published"] >= pd.Timestamp(iss)
            for c in C.NF.CATS + ["anticipatory", "food_event"]:
                g0.loc[gf, c] = rng.permutation(g0.loc[gf, c].to_numpy())
            set_rounds(r0)
            set_gkg(g0)
            RC._clear()
            try:
                pert = RC.forecast_at(t, k, dp, x)
            finally:
                set_rounds(None)
                set_gkg(None)
                RC._clear()
            res.append({"lead": k, "origin": L.qs(t), "n": len(base), "identical": base == pert})
            print(res[-1], flush=True)
    return {"origins_checked": len(res), "all_identical": all(r["identical"] and r["n"] for r in res), "detail": res}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for ph in (["labels", "metrics", "repro", "leakage"] if which == "all" else [which]):
        {"labels": phase_labels, "metrics": phase_metrics, "repro": phase_repro, "leakage": phase_leakage}[ph]()
