"""E53 addendum I2 single run (ADDENDUM_I2.md): outer calibrators C3/C4 on R0's run-1 probabilities, shrinkage
LightGBM residual LGB-R2 (5% selection margin) and monotone LightGBM classifier LGB-C2, on the identical 50 rows.

    backend/venv/Scripts/python.exe -B runner/e53_evaluate_i2.py   -> runs/i2_<UTC stamp>/{predictions.csv, rows.csv, results.json}
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e53_lib as E  # noqa: E402

L, P2, I7, np, pd = E.L, E.P2, E.I7, E.np, E.pd
RUN1 = E.E53 / "runs" / "20261017T140057Z"
FIRST, OPER = L.qi("2023-Q4"), L.qi("2026-Q3")
BASELINES = ["B1_PERSIST", "B2_LR_GOV", "B3_LGBM_GOV", "B4_LR_NLP", "B5_LGBM_NLP", "B6_LR_COMB", "B7_E38PROC", "CLIM", "HIGH", "LOW"]
NEW = ["C3", "C4", "LGB-R2", "LGB-C2"]


def verify() -> str:
    want = (E.E53 / "runner" / "ADDENDUM_I2_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E.E53 / "ADDENDUM_I2.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("ADDENDUM_I2.md changed after freezing")
    return got


# ------------------------------------------------------------ LGB-R2
R2_FIXED = dict(E.LGB_FIXED, min_child_samples=20, reg_lambda=50.0)


class LGBRes2(E.LGBRes):
    def fit(self, X, y):
        import lightgbm as lgb
        self.m = lgb.LGBMRegressor(**dict(R2_FIXED, num_leaves=2, n_estimators=self.trees)).fit(
            X[self.cols].astype(float), np.asarray(y, float))
        return self


def _oof2(args):
    tr, c, cols_all, ycol, bfmt = args
    b = bfmt.format(c["mult"])
    tr = tr.dropna(subset=[b, ycol])
    out = []
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit, hold = tr[tr["q"].isin(fq)], tr[tr["q"] == q]
        res = 0.0
        if c["res"] is not None:
            cols = P2.PRICE_GROUPS["market"] if c["feat"] == "market" else cols_all
            res = LGBRes2(cols, 2, c["trees"]).fit(fit, fit[ycol] - fit[b]).predict(hold)
        out.append(hold[["q", "province_code"]].assign(y_true=hold[ycol].to_numpy(), y_hat=hold[b].to_numpy() + res))
    if not out:
        return float("inf"), pd.DataFrame(columns=["q", "province_code", "y_true", "y_hat"])
    o = pd.concat(out, ignore_index=True)
    return float(np.sqrt(np.mean((o["y_hat"] - o["y_true"]) ** 2))), o


def comp2(tr, te, cols_all, ycol, bfmt):
    from joblib import Parallel, delayed
    g = [{"mult": m, "res": None} for m in P2.MULTS] + [
        {"mult": m, "res": "lgb", "trees": n, "feat": f} for m in P2.MULTS for n in (25, 50, 100) for f in ("all", "market")]
    res = Parallel(n_jobs=8, backend="loky")(delayed(_oof2)((tr, c, cols_all, ycol, bfmt)) for c in g)
    simp = lambda c: (0, 0, 0, [1.0, 0.5, 0.0].index(c["mult"])) if c["res"] is None else \
        (1, c["trees"], 0 if c["feat"] == "market" else 1, [1.0, 0.5, 0.0].index(c["mult"]))  # noqa: E731
    nores = [i for i, c in enumerate(g) if c["res"] is None]
    lgbi = [i for i, c in enumerate(g) if c["res"] is not None]
    bn = min(nores, key=lambda i: (round(res[i][0], 10), simp(g[i])))
    bl = min(lgbi, key=lambda i: (round(res[i][0], 10), simp(g[i])))
    best = bl if res[bl][0] <= 0.95 * res[bn][0] else bn                     # 5% margin rule
    c, (rmse, o) = g[best], res[best]
    b = bfmt.format(c["mult"])
    trb = tr.dropna(subset=[b, ycol])
    model = None
    if c["res"] is not None:
        cols = P2.PRICE_GROUPS["market"] if c["feat"] == "market" else cols_all
        model = LGBRes2(cols, 2, c["trees"]).fit(trb, trb[ycol] - trb[b])
    hat = te[b].to_numpy() + (0.0 if model is None else model.predict(te))
    return {"cfg": c, "rmse": rmse, "oof": o, "hat": hat}


def lgbr2(d, X, B, t):
    tr, te = E.frame(d, X, B, t)
    cols = E.pcols()
    fc, gc = comp2(tr, te, cols, "F_true", "base_{}"), comp2(tr, te, cols, "G_true", "gbase_{}")
    j = fc["oof"].merge(gc["oof"], on=["q", "province_code"], suffixes=("_F", "_G"))
    rho = float(np.corrcoef(j["y_hat_F"] - j["y_true_F"], j["y_hat_G"] - j["y_true_G"])[0, 1]) if len(j) > 2 else 0.0
    rho = 0.0 if not np.isfinite(rho) else rho
    p = P2.p_price_biv(fc["hat"], gc["hat"], fc["rmse"], gc["rmse"], rho, te["province_code"])
    return p, {"food": fc["cfg"], "gap": gc["cfg"]}


# ------------------------------------------------------------ LGB-C2
def lgbc2(d, X, B, t):
    import lightgbm as lgb
    tr, te = E.frame(d, X, B, t)
    mono = [f"{k}_{m}" for m in P2.MULTS for k in ("dfood", "dgap")]
    cols = mono + E.pcols()
    cons = [1] * len(mono) + [0] * len(E.pcols())
    grid = [{"kind": "constant"}] + [{"kind": "lgb", "leaves": lv, "trees": n} for lv in (2, 4) for n in (50, 200)]

    def fp(c, fit, hold):
        prev = float(fit["PS"].mean())
        if c["kind"] == "constant" or fit["PS"].nunique() < 2:
            return np.full(len(hold), prev)
        m = lgb.LGBMClassifier(**dict(E.LGB_FIXED, num_leaves=c["leaves"], n_estimators=c["trees"],
                                      monotone_constraints=cons, monotone_constraints_method="basic")).fit(
            fit[cols].astype(float), fit["PS"].to_numpy())
        return m.predict_proba(hold[cols].astype(float))[:, 1]
    sc = []
    for c in grid:
        ll, n = 0.0, 0
        for q, fq in I7.folds(tr["q"].unique(), "forward"):
            fit, hold = tr[tr["q"].isin(fq)], tr[tr["q"] == q]
            p = np.clip(fp(c, fit, hold), 1e-6, 1 - 1e-6)
            y = hold["PS"].to_numpy()
            ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
            n += len(y)
        sc.append(ll / n if n else float("inf"))
    simp = lambda c: (0, 0, 0) if c["kind"] == "constant" else (1, c["leaves"], c["trees"])  # noqa: E731
    best = min(range(len(grid)), key=lambda i: (round(sc[i], 10), simp(grid[i])))
    return fp(grid[best], tr, te), {"cfg": grid[best], "logloss": sc[best]}


def main():
    proto = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E.E53 / "runs" / f"i2_{stamp}"
    out.mkdir(parents=True)
    P1 = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})
    d, X, B = E.load()
    rows, sel = [], {}
    for t in range(FIRST, OPER + 1):
        k = t + 2
        prior = P1[(P1["t"] + 2 <= k - 3)].copy()                       # earlier issued forecasts with published outcomes
        lab = pd.read_csv(E.EXP / "E51_Target_Definition" / "data" / "labels_cpi.csv", dtype={"province_code": str})
        prior = prior.assign(q=prior["t"] + 2).merge(lab[["province_code", "q", "PS"]], on=["province_code", "q"])
        c3 = E.fit_calibrator(prior["R0_p"], prior["PS"], "C1")
        c4 = E.fit_calibrator(prior["R0_p"], prior["PS"], "C2")
        r0 = P1[P1["t"] == t].set_index("province_code").loc[L.PROVS, "R0_p"].to_numpy()
        pr2, s2 = lgbr2(d, X, B, t)
        pc2, s3 = lgbc2(d, X, B, t)
        sel[L.qs(k)] = {"C3": c3, "C4": c4, "LGB-R2": s2, "LGB-C2": s3}
        for i, p in enumerate(L.PROVS):
            rows.append({"t": t, "target": L.qs(k), "province_code": p, "C3_p": float(E.apply_calibrator(c3, r0[i:i + 1])[0]),
                         "C4_p": float(E.apply_calibrator(c4, r0[i:i + 1])[0]), "LGB-R2_p": float(pr2[i]), "LGB-C2_p": float(pc2[i])})
        print(L.qs(t), "->", L.qs(k), "C3 b", round(c3["b"], 2), "R2", s2["food"].get("res"), s2["gap"].get("res"),
              "C2", s3["cfg"]["kind"], flush=True)
    P = pd.DataFrame(rows)
    P.to_csv(out / "predictions.csv", index=False)
    R = pd.read_csv(RUN1 / "rows.csv", dtype={"province_code": str})
    R = R.merge(P.drop(columns=["t"]), on=["target", "province_code"], how="inner")
    assert len(R) == 50
    for a in NEW:
        R[f"{a}_yhat"] = (R[f"{a}_p"] >= 0.5).astype(int)
    R.to_csv(out / "rows.csv", index=False)
    M1 = json.loads((RUN1 / "results.json").read_text())["metrics"]
    MN = E.block(R, NEW, seed=532)
    allm = {**M1, **MN}
    loqo = {a: {q: float((R[R["target"] != q][f"{a}_yhat"] == R[R["target"] != q]["y"]).mean()) for q in R["target"].unique()} for a in NEW}
    cal = {a: E.calibration(R["y"], R[f"{a}_p"]) for a in NEW}
    conf = {a: E.by_quarter_confusion(R, a) for a in NEW}
    paired = {a: E.paired_brier(R, a) for a in NEW}
    used = {"LGB-R2": sum(1 for v in sel.values() if v["LGB-R2"]["food"].get("res") or v["LGB-R2"]["gap"].get("res")),
            "LGB-C2": sum(1 for v in sel.values() if v["LGB-C2"]["cfg"]["kind"] != "constant")}

    def crit(a):
        m = allm[a]
        return {"A1": m["accuracy"] >= 0.75,
                "A2": (m["balanced_accuracy"] or 0) >= 0.70 and (m["recall_HIGH"] or 0) >= 0.60 and (m["recall_LOW"] or 0) >= 0.60,
                "A3": all(m["brier"] < allm[b]["brier"] for b in BASELINES),
                "A4": all((m["balanced_accuracy"] or 0) > (allm[b]["balanced_accuracy"] or 0) for b in BASELINES),
                "A5": min(loqo[a].values()) >= 0.70, "K1": abs(cal[a]["citl"]) <= 0.05, "K2": m["brier"] <= allm["R0"]["brier"]}
    C = {a: crit(a) for a in NEW}
    A15 = lambda a: all(C[a][k] for k in ("A1", "A2", "A3", "A4", "A5"))  # noqa: E731
    cal_pass = [a for a in ("C3", "C4") if A15(a) and C[a]["K1"] and C[a]["K2"]]
    decision = {"calibrated_replaces_R0": cal_pass[0] if cal_pass else None,
                "LightGBM_meets_requirement_for_development": [a for a in ("LGB-R2", "LGB-C2") if A15(a) and used[a] >= 6],
                "lightgbm_origins_using_trees": used}
    res = {"addendum_sha256": proto, "run_utc": stamp, "evidence_status": "Hindsight-informed development evidence "
           "(designed after run 1 on the same rows); five LightGBM attempts in E53 in total.",
           "rows": int(len(R)), "metrics": MN, "leave_one_quarter_out": loqo, "calibration": cal,
           "confusion_by_quarter": conf, "paired_brier_vs_R0": paired, "criteria": C, "decision": decision, "selections": sel}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    f3 = lambda v: None if v is None else round(v, 3)  # noqa: E731
    for a in NEW:
        m = MN[a]
        print(f"  {a:8s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal {f3(m['balanced_accuracy'])} "
              f"recH {f3(m['recall_HIGH'])} recL {f3(m['recall_LOW'])} brier {m['brier']:.3f} auc {f3(m['auc'])} "
              f"citl {f3(cal[a]['citl'])} slope {f3(cal[a]['slope'])} dBrier {f3(paired[a]['diff'])} {[round(v, 3) for v in paired[a]['ci95']]}")
    print("  criteria", json.dumps(C))
    print("  decision", json.dumps(decision))


if __name__ == "__main__":
    main()
