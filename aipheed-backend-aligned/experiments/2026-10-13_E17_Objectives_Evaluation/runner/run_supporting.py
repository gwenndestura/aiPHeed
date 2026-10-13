"""E17 supporting analysis (protocol section 6): continuous horizons k = 1..4 for regional hunger H, provincial food
inflation F and relative pressure D. Origin = start of quarter t+1; target t+k. Baseline carry-forward; model ridge
(alpha 1, training-standardized) on the latest available value. Also Objective 1 and 3 evidence tables.
Usage: python -B runner/run_supporting.py [--deliverables]"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e17_lib as L  # noqa: E402
import loaders as Ld  # noqa: E402
from run_e17 import check_frozen, jd, sha  # noqa: E402

EXP = guard.EXP
MIN_TRAIN = 6


def ridge(Xtr, ytr, Xte, alpha=1.0):
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Z, Zt = (Xtr - mu) / sd, (Xte - mu) / sd
    b = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (ytr - ytr.mean()))
    return ytr.mean() + Zt @ b


def h_series(rounds):
    return rounds.groupby("quarter").agg(H=("H", "mean"), last_pub=("published", "max"))


def h_last(rounds, origin):
    pub = rounds[rounds["published"] < origin]
    if pub.empty:
        return np.nan
    lq = max(pub["quarter"], key=L.qk)
    return float(pub.loc[pub["quarter"] == lq, "H"].mean())


def forecasts(comp, rounds, k_list=(1, 2, 3, 4)):
    hs = h_series(rounds)
    rows = []
    for k in k_list:
        for t in range(L.qk("2021-Q1"), L.qk("2025-Q4") - k + 1):
            O = L.qstart(L.qs(t + 1))
            T = L.qs(t + k)
            # ---- H (regional, all eligible rounds)
            if T in hs.index:
                tr = []
                for t2 in range(L.qk("2021-Q1"), t):
                    q2 = L.qs(t2 + k)
                    if q2 in hs.index and hs.loc[q2, "last_pub"] < O:
                        x = h_last(rounds, L.qstart(L.qs(t2 + 1)))
                        if x == x:
                            tr.append((x, hs.loc[q2, "H"], q2))
                xo = h_last(rounds, O)
                if len({q for _, _, q in tr}) >= MIN_TRAIN and xo == xo:
                    a = np.array([[x] for x, _, _ in tr]); y = np.array([v for _, v, _ in tr])
                    rows.append({"target": "H", "k": k, "target_quarter": T, "unit": "REGION", "y": float(hs.loc[T, "H"]),
                                 "cf": xo, "model": float(ridge(a, y, np.array([[xo]]))[0]), "n_train_quarters": len(tr)})
            # ---- F and D (provincial; inputs of t-1; training targets <= t-1)
            for var in ("F", "D"):
                cur = comp[comp["quarter"] == L.qs(t - 1)].set_index("province_code")[var]
                yT = comp[comp["quarter"] == T].set_index("province_code")[var]
                if cur.isna().any() or len(cur) < 5 or yT.isna().any():
                    continue
                trX, trY, trQ = [], [], []
                for t2 in range(L.qk("2021-Q2"), t):
                    q2 = L.qs(t2 + k)
                    if L.qk(q2) > t - 1:
                        continue
                    xs = comp[comp["quarter"] == L.qs(t2 - 1)].set_index("province_code")[var]
                    ys = comp[comp["quarter"] == q2].set_index("province_code")[var]
                    for pc in xs.index:
                        trX.append(xs[pc]); trY.append(ys[pc]); trQ.append(q2)
                if len(set(trQ)) < MIN_TRAIN:
                    continue
                pm = ridge(np.array(trX)[:, None], np.array(trY), cur.to_numpy()[:, None])
                for i, pc in enumerate(cur.index):
                    rows.append({"target": var, "k": k, "target_quarter": T, "unit": pc, "y": float(yT[pc]),
                                 "cf": float(cur[pc]), "model": float(pm[i]), "n_train_quarters": len(set(trQ))})
    return pd.DataFrame(rows)


def summarize(d):
    out, perq = [], []
    for (tg, k), g in d.groupby(["target", "k"]):
        g = g.assign(e_cf=(g["cf"] - g["y"]).abs(), e_m=(g["model"] - g["y"]).abs())
        q = g.groupby("target_quarter")[["e_cf", "e_m"]].mean()
        nq = len(q)
        rng = np.random.default_rng(L.SEED)
        s = g.groupby("target_quarter")[["e_cf", "e_m"]].sum()
        n = g.groupby("target_quarter").size()
        idx = rng.integers(0, nq, size=(L.N_BOOT, nq))
        diff = (s["e_m"].to_numpy()[idx].sum(1) - s["e_cf"].to_numpy()[idx].sum(1)) / n.to_numpy()[idx].sum(1)
        lo, hi = float(np.quantile(diff, 0.025)), float(np.quantile(diff, 0.975))
        better = int((q["e_m"] < q["e_cf"]).sum())
        status = ("insufficient evidence (<5 test quarters)" if nq < 5 else
                  ("beats baseline" if hi < 0 and better >= 2 * nq / 3 else "does not beat baseline"))
        out.append({"target": tg, "k": k, "test_quarters": nq, "rows": len(g),
                    "model_MAE": g["e_m"].mean(), "model_RMSE": float(np.sqrt(((g["model"] - g["y"]) ** 2).mean())),
                    "baseline_MAE": g["e_cf"].mean(), "baseline_RMSE": float(np.sqrt(((g["cf"] - g["y"]) ** 2).mean())),
                    "MAE_diff_model_minus_baseline": g["e_m"].mean() - g["e_cf"].mean(), "ci_low": lo, "ci_high": hi,
                    "quarters_model_better": better, "consistency": f"{better}/{nq}", "status": status,
                    "operational_reliability": "not determinable: no defensible error tolerance"})
        for qq, r in q.iterrows():
            perq.append({"target": tg, "k": k, "target_quarter": qq, "baseline_MAE": r["e_cf"], "model_MAE": r["e_m"]})
        if tg != "H":
            for pc, gp in g.groupby("unit"):
                perq.append({"target": tg, "k": k, "target_quarter": "ALL", "province_code": pc,
                             "baseline_MAE": gp["e_cf"].mean(), "model_MAE": gp["e_m"].mean()})
    return pd.DataFrame(out), pd.DataFrame(perq)


def objective_evidence(f, top, pov, cen):
    ev = {}
    nz = lambda c: int((f[c] != 0).sum())  # noqa: E731
    ev["objective1"] = {"province_quarters": int(len(f)), "FSSI_nonzero": nz("FSSI"),
                        "FSSI_nonzero_by_province": f.assign(nz=f["FSSI"] != 0).groupby("province_code")["nz"].sum().astype(int).to_dict(),
                        "triggers_nonzero": {c: nz(c) for c in L.NLP if c.startswith("trigger_")},
                        "topic_province_quarters": int(top[["province_code", "quarter"]].drop_duplicates().shape[0])}
    m = pov.merge(cen[["lgu_code", "density_per_km2", "density_normalized", "population_2020"]], on="lgu_code", how="inner")
    m["fallback"] = m["source_note"].str.contains("fallback", case=False, na=False)
    m["V"] = 0.6 * m["poverty_normalized"] + 0.4 * m["density_normalized"]
    prov = []
    for pc, g in m.groupby("province_code"):
        rv, rd = g["V"].rank(ascending=False), g["density_per_km2"].rank(ascending=False)
        prov.append({"province_code": pc, "province": g["province_name"].iloc[0], "lgus": int(len(g)),
                     "poverty_fallback_lgus": int(g["fallback"].sum()), "distinct_poverty_values": int(g["poverty_incidence_pct"].nunique()),
                     "spearman_V_rank_vs_density_rank": float(rv.corr(rd)),
                     "poverty_normalized_distinct": int(g["poverty_normalized"].round(9).nunique())})
    ev["objective3"] = {"lgus_matched": int(len(m)), "by_province": prov,
                        "note": "Within a province, municipal risk = province score x V. V is static (2021 poverty, 2020 census), "
                                "so the within-province order never changes between quarters."}
    return ev


def main(deliverables):
    check_frozen()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = EXP / "runs" / f"supporting_{ts}"
    out.mkdir(parents=True)
    comp = Ld.load_components()
    rounds = Ld.load_rounds()
    gov = Ld.load_governing()
    f = Ld.load_features(gov)
    top = Ld.load_topics()
    pov, cen = Ld.load_lgu()
    fies = Ld.load_fies()
    d = forecasts(comp, rounds)
    d.to_csv(out / "supporting_forecasts.csv", index=False, lineterminator="\n", float_format="%.8g")
    S, PQ = summarize(d)
    S.to_csv(out / "supporting_horizons.csv", index=False, lineterminator="\n", float_format="%.6g")
    PQ.to_csv(out / "supporting_per_quarter_province.csv", index=False, lineterminator="\n", float_format="%.6g")
    ev = objective_evidence(f, top, pov, cen)
    ev["objective5_fies_in_project"] = fies.astype(object).where(fies.notna(), None).to_dict("records")
    (out / "objective_evidence.json").write_text(json.dumps(ev, indent=1, default=jd), encoding="utf-8", newline="\n")
    if deliverables:
        S.to_csv(EXP / "SUPPORTING_HORIZONS.csv", index=False, lineterminator="\n", float_format="%.6g")
    (out / "manifest.json").write_text(json.dumps({"utc": ts, "code_sha256": {p.name: sha(p) for p in sorted((EXP / "runner").glob("*.py"))},
                                                   "outputs_sha256": {p.name: sha(p) for p in sorted(out.glob("*")) if p.name != "manifest.json"},
                                                   "access_log": guard.ACCESS_LOG}, indent=1), encoding="utf-8", newline="\n")
    print(out)
    print(S.round(3).to_string())
    print(json.dumps(ev, indent=1, default=jd)[:2500])


if __name__ == "__main__":
    main("--deliverables" in sys.argv)
