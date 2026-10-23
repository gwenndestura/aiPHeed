"""E103 runner (PROTOCOL.md, frozen sha in PROTOCOL_SHA256.txt): reproduce E102, decompose FB2, sensitivity, separate
evaluations. Reads only served/local files and E100-E102 outputs (hash-checked before and after); writes ../out/ only.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E103_FB2_Verification/runner/e103_run.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
EXP = HERE.parents[1]
E102 = EXP / "E102_Market_Access_Forecasting"
sys.path.insert(0, str(E102 / "runner"))
import e102_lib as L  # noqa: E402
import e102_run as RUN  # noqa: E402  (also extends E101 lead-1 origins to 2026-Q3, as E102 did)

R, E101, np, pd, TS, qi, qs = L.R, L.E101, L.np, L.pd, L.TS, L.qi, L.qs
from scipy.stats import binomtest, spearmanr  # noqa: E402

TOL = 1e-12
PERIOD_SPLIT = "2024-Q1"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_files():
    return {str(p.relative_to(EXP)): sha(p) for d in ("E100_Market_Trigger_Investigation", "E101_Access_Informed_Weighting",
                                                       "E102_Market_Access_Forecasting")
            for p in sorted((EXP / d).rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def verify():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == want, "PROTOCOL.md changed after freezing"
    RUN.verify()
    return got


# ------------------------------------------------------------------------------------------------ indicators
def pers_variant(cpi, p, t, th, w):
    y = cpi["yoy"]
    vals = [y.get((p, q)) for q in range(t - w, t) if q >= qi(L.BASE_Q) and q <= t - 1]
    vals = [v for v in vals if v is not None]
    return sum(v > th for v in vals) / len(vals) if len(vals) >= 2 else None


def rel8(cpi, p, t):
    f, a = cpi["food"], cpi["all"]
    ratio = [f[(p, q)] / a[(p, q)] for q in range(t - 8, t) if q >= qi(L.BASE_Q) and (p, q) in f and (p, q) in a]
    last = (f.get((p, t - 1)), a.get((p, t - 1)))
    if len(ratio) < 4 or not all(last):
        return None
    return 100 * ((last[0] / last[1]) / float(np.mean(ratio)) - 1)


# ------------------------------------------------------------------------------------------------ statistics
def permutation_p(d: np.ndarray) -> float:
    """Exact two-sided sign-flip permutation p for the mean of d."""
    n = len(d)
    signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
    means = (signs * d).mean(axis=1)
    return float((np.abs(means) >= abs(d.mean()) - 1e-15).mean())


def paired(y, a, b, seed=2026, n=2000):
    d = (a - y) ** 2 - (b - y) ** 2
    rng = np.random.default_rng(seed)
    bs = [float(np.mean(rng.choice(d, len(d), replace=True))) for _ in range(n)]
    w, l_ = int((d < -TOL).sum()), int((d > TOL).sum())
    return {"mean_d": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "wins": w, "losses": l_, "ties": int(len(d) - w - l_),
            "sign_p": float(binomtest(w, w + l_, 0.5).pvalue) if w + l_ else 1.0, "perm_p": permutation_p(d),
            "quarters": int(len(d))}


def cal_slope(y, p):
    if len(set(y)) < 2:
        return None
    from sklearn.linear_model import LogisticRegression
    z = np.log(np.clip(p, .01, .99) / (1 - np.clip(p, .01, .99))).reshape(-1, 1)
    return float(LogisticRegression(C=1e6, max_iter=1000).fit(z, y).coef_[0, 0])


def score(Q, names, ref="SERVED", extra_refs=()):
    out = {}
    for a in names:
        g = Q.dropna(subset=[a])
        m = L.metrics(g["y"], g[a])
        m["quarters"] = int(len(g))
        m["calibration_slope"] = cal_slope(g["y"].to_numpy(int), g[a].to_numpy(float))
        for r in (ref,) + tuple(extra_refs):
            if a == r or r not in Q:
                continue
            gg = g.dropna(subset=[r])
            y = gg["y"].to_numpy(float)
            m[f"vs_{r}"] = paired(y, gg[a].to_numpy(float), gg[r].to_numpy(float))
            for per, sel in (("transition", gg["target"].map(qi) < qi(PERIOD_SPLIT)), ("2024+", gg["target"].map(qi) >= qi(PERIOD_SPLIT))):
                s = gg[sel]
                d = (s[a] - s["y"]) ** 2 - (s[r] - s["y"]) ** 2
                m[f"vs_{r}"][f"period_{per}"] = {"quarters": int(len(s)), "mean_d": float(d.mean()) if len(s) else None,
                                                 "wins": int((d < -TOL).sum()), "losses": int((d > TOL).sum())}
        out[a] = m
    return out


# ------------------------------------------------------------------------------------------------ main
def main():
    sha_p = verify()
    before = frozen_files()
    OUT.mkdir(exist_ok=True)
    H = R.load_history()
    out_h = R.outcome_series()
    LV = R.level_indicator()
    rel101 = E101.rel_scores(LV)
    S63 = pd.read_csv(E101.E63, dtype={"province_code": str})
    a1_63 = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_price) for r in S63.itertuples()}
    cpi = L.load_cpi()
    origins = list(range(qi("2021-Q2"), qi("2026-Q3") + 1))
    PNL = L.panel(cpi, origins)
    pct = {k: L.percentiles({key: v[k] for key, v in PNL.items()}) for k in ("REL", "PERS", "LVL")}
    sens_raw = {f"PERS_{th}_{w}": {(t, p): pers_variant(cpi, p, t, th, w) for t in origins for p in L.PROVS}
                for th in (3.0, 4.0, 5.0, 6.0) for w in (2, 4, 6)}
    sens_raw["REL8"] = {(t, p): rel8(cpi, p, t) for t in origins for p in L.PROVS}
    sens_pct = {k: L.percentiles(v) for k, v in sens_raw.items()}
    e102 = json.loads((E102 / "out" / "results.json").read_text(encoding="utf-8"))
    res = {"protocolSha256": sha_p, "leads": {}}

    def m(v):
        v = [x for x in v if x is not None]
        return float(np.mean(v)) if v else None

    for lead in (1, 2):
        rows = E101.lead_rows(H, lead, a1_63, rel101)

        def with_A(fn):
            out = []
            for x in rows:
                y = {**x, "s": dict(x["s"]), "dom": dict(x["dom"])}
                key = (x["t"], x["code"])
                y["dom"]["A"] = fn(x["s"], key)
                out.append(y)
            return out
        P = lambda name: (lambda key: pct[name].get(key))  # noqa: E731
        specs = {"SERVED": None,
                 "S-noA2": lambda s, k: m([s["A1"], s["A3"]]),
                 "S-A1only": lambda s, k: s["A1"],
                 "FB2": lambda s, k: m([s["A1"], P("REL")(k), P("PERS")(k)]),
                 "FB2-noREL": lambda s, k: m([s["A1"], P("PERS")(k)]),
                 "FB2-noPERS": lambda s, k: m([s["A1"], P("REL")(k)]),
                 "LVL-only": lambda s, k: P("LVL")(k), "PERS-only": lambda s, k: P("PERS")(k),
                 "REL-only": lambda s, k: P("REL")(k)}
        prov = {}
        R.MIN_DOMAINS = 4
        for name, fn in specs.items():
            rr = rows if fn is None else with_A(fn)
            prov[name] = E101.served_equal(rr, lead)[0]
        fb2rows = with_A(specs["FB2"])
        prov["FB2-noH4"] = E101.served_equal(fb2rows, lead, doms=[d for d in R.DOMS if d != "H"])[0]
        R.MIN_DOMAINS = 3
        prov["S-noA"] = E101.served_equal(rows, lead, doms=[d for d in R.DOMS if d != "A"])[0]
        s3, e3 = E101.served_equal(fb2rows, lead, doms=[d for d in R.DOMS if d != "H"])
        prov["FB2-noH3"], prov["FB2-noH-EQ"] = s3, e3
        R.MIN_DOMAINS = 4
        # sensitivity inside FB2
        for k in sens_pct:
            if k.startswith("PERS"):
                fn = lambda s, key, k=k: m([s["A1"], P("REL")(key), sens_pct[k].get(key)])
            else:
                fn = lambda s, key, k=k: m([s["A1"], sens_pct[k].get(key), P("PERS")(key)])
            prov[f"FB2[{k}]"] = E101.served_equal(with_A(fn), lead)[0]
        reg = {a: {} for a in prov}
        for a, v in prov.items():
            for q in {x["target"] for x in rows}:
                vals = [v.get((q, p)) for p in L.PROVS]
                vals = [x for x in vals if x is not None]
                if vals:
                    reg[a][q] = float(np.mean(vals))
        reg["P0"] = {x["target"]: x["s"]["H1"] for x in rows}
        Q = RUN.regional_eval(reg, out_h, lead)
        Q = Q[Q["SERVED"].notna()].reset_index(drop=True)                     # SERVED's quarters (protocol 2)
        # reproduction gate vs E102
        old = pd.read_csv(E102 / "out" / f"regional_lead{lead}.csv")
        mm = Q.merge(old[["target", "SERVED", "FB2"]], on="target", suffixes=("", "_e102"))
        gate = {c: float((mm[c] - mm[f"{c}_e102"]).abs().max()) for c in ("SERVED", "FB2")}
        e = e102["leads"][str(lead)]["index_set"]["arms"]
        gate["metrics_equal"] = all(abs(L.metrics(Q["y"], Q[c])[k] - e[c][k]) < 1e-12 for c in ("SERVED", "FB2")
                                    for k in ("accuracy", "brier"))
        assert max(gate["SERVED"], gate["FB2"]) < 1e-9 and gate["metrics_equal"] and len(mm) == len(Q), gate
        Q.to_csv(OUT / f"regional_lead{lead}.csv", index=False, lineterminator="\n")
        names = [a for a in reg] + ["ALWAYS", "CLIM"]
        sc = score(Q, names, "SERVED", extra_refs=("S-A1only", "S-noA", "S-noA2"))
        coverage = {a: int(Q[a].notna().sum()) for a in names}
        res["leads"][str(lead)] = {"quarters": int(len(Q)), "HIGH": int(Q["y"].sum()), "reproduction_gate": gate,
                                   "coverage": coverage, "arms": sc}
        # per-quarter Brier contribution of FB2 and the removal arms vs SERVED
        qc = Q[["target", "H_obs", "y", "rising", "SERVED", "FB2", "S-noA2", "S-A1only", "S-noA", "FB2-noREL", "FB2-noPERS"]].copy()
        for a in ("FB2", "S-noA2", "S-A1only", "S-noA", "FB2-noREL", "FB2-noPERS"):
            qc[f"d_{a}"] = (qc[a] - qc["y"]) ** 2 - (qc["SERVED"] - qc["y"]) ** 2
        qc.to_csv(OUT / f"quarter_contrib_lead{lead}.csv", index=False, lineterminator="\n", float_format="%.6f")
        # overlap (province rows at evaluated origins) and regional raw
        ev = [x for x in rows if x["target"] in set(Q["target"])]
        X = pd.DataFrame([{"A1": x["s"]["A1"], "A2": x["s"]["A2"], "A3": x["s"]["A3"],
                           **{f"p{k}": pct[k].get((x["t"], x["code"])) for k in ("LVL", "REL", "PERS")}} for x in ev]).astype(float)
        res["leads"][str(lead)]["overlap_province_scores"] = X.corr(method="spearman", min_periods=8).round(2).to_dict()
        RW = pd.DataFrame([{**{k: m([PNL[(t, p)][k] for p in L.PROVS]) for k in ("LVL", "REL", "PERS")},
                            "A2raw": m([r["ind"]["A2"]["x"] for _, r in H[H["t"] == t].iterrows()])}
                           for t in sorted({x["t"] for x in ev})]).astype(float)
        res["leads"][str(lead)]["overlap_regional_raw"] = RW.corr(method="spearman").round(2).to_dict()
        # trained-model audit (E102 features; no new model)
        feats = {qi(q): f for q, f in e102["leads"][str(lead)]["features"].items()}
        aud = []
        for t in sorted(feats):
            tr = L.training_pairs(feats, lead, t, RUN.MODEL_COLS["M3"])
            aud.append({"origin": qs(t), "target": qs(t + lead), "train_pairs": int(len(tr)),
                        "train_HIGH": int(tr["y"].sum()) if len(tr) else 0,
                        "forecast_made": bool(len(tr) >= L.MIN_TRAIN),
                        "target_HIGH": None if qs(t + lead) not in out_h else bool(out_h[qs(t + lead)] > R.HUNGER_LINE)})
        res["leads"][str(lead)]["trained_model_audit"] = aud
    # production LightGBM, separately
    fe = json.loads((R.BACKEND / "data/thesis/final_evaluation.json").read_text(encoding="utf-8"))
    res["production_lightgbm_on_price_label"] = {str(x["lead"]): {k: x["metrics"]["LightGBM E56-TUNED P(HIGH)"][k]
                                                                   for k in ("n", "accuracy", "balanced_accuracy", "auc_roc", "brier")}
                                                 for x in fe["objective2"]["leads"] if x["lead"] in (1, 2)}
    res["production_lightgbm_vs_sws"] = {L_: {k: e102["leads"][L_]["index_set"]["arms"]["PROD"][k]
                                              for k in ("quarters", "accuracy", "brier")} for L_ in ("1", "2")}
    after = frozen_files()
    res["frozen_files_unchanged"] = before == after
    assert before == after, "an E100-E102 file changed during the run"
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for lead in ("1", "2"):
        print("LEAD", lead, res["leads"][lead]["quarters"], res["leads"][lead]["reproduction_gate"])


if __name__ == "__main__":
    main()
