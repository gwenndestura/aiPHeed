"""E104 runner (PROTOCOL.md, frozen sha in PROTOCOL_SHA256.txt). Reads served/local files and E100-E103 outputs
(hash-checked before and after); writes ../out/ only.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E104_REL_Investigation/runner/e104_run.py
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
E103D = EXP / "E103_FB2_Verification"
sys.path.insert(0, str(E103D / "runner"))
import e103_run as E3  # noqa: E402

L, R, E101, np, pd, TS, qi, qs = E3.L, E3.R, E3.E101, E3.np, E3.pd, E3.TS, E3.qi, E3.qs
from scipy.stats import spearmanr  # noqa: E402

FAMILY = ["S-noA", "FB2", "FB2-noREL", "FB2-noPERS", "LVL-only", "PERS-only", "REL-only"]
MODELS = {"R0": ["H_last"], "R1": ["H_last", "REL"], "R2": ["H_last", "REL", "E1raw"], "R3": ["H_last", "LVL"],
          "R4": ["REL", "E1raw"]}


def verify():
    got = {}
    for f in ("PROTOCOL.md", "PROSPECTIVE_CRITERIA.md"):
        got[f] = hashlib.sha256((HERE.parent / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    want = dict(line.split()[::-1] for line in (HERE / "PROTOCOL_SHA256.txt").read_text().splitlines() if line.strip())
    assert all(want[f] == h for f, h in got.items()), "E104 protocol files changed after freezing"
    E3.verify()
    return got


def frozen_files():
    out = E3.frozen_files()
    out.update({str(p.relative_to(EXP)): E3.sha(p) for p in sorted(E103D.rglob("*")) if p.is_file() and "__pycache__" not in p.parts})
    return out


def rel_independent(t: int) -> dict:
    """REL re-derived with pandas, separately from e102_lib (audit A1)."""
    c = pd.read_parquet(R.BACKEND / "data/processed/cpi_full.parquet", filters=[("year", ">=", 2021)])
    c = c[c["province_code"].isin(L.PROVS)].set_index(["province_code", "quarter"])
    out = {}
    for p in L.PROVS:
        try:
            r1 = c.loc[(p, qs(t - 1))]
            r0 = c.loc[(p, "2021-Q1")]
        except KeyError:
            continue
        out[p] = 100 * ((r1.cpi_food_nab / r1.cpi_all_items) / (r0.cpi_food_nab / r0.cpi_all_items) - 1)
    return out


def partial_spearman(x, y, controls):
    from numpy.linalg import lstsq
    rk = lambda v: pd.Series(v).rank().to_numpy(float)  # noqa: E731
    Z = np.column_stack([np.ones(len(x))] + [rk(c) for c in controls])
    rx = rk(x) - Z @ lstsq(Z, rk(x), rcond=None)[0]
    ry = rk(y) - Z @ lstsq(Z, rk(y), rcond=None)[0]
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    sha = verify()
    before = frozen_files()
    OUT.mkdir(exist_ok=True)
    res = {"protocolSha256": sha, "leads": {}}
    cpi = L.load_cpi()
    # A1 REL formula audit
    diffs = []
    for t in range(qi("2021-Q2"), qi("2026-Q3") + 1):
        ind = rel_independent(t)
        for p, v in ind.items():
            diffs.append(abs(L.indicators_at(cpi, p, t)["REL"] - v))
    res["A1_rel_formula_max_abs_diff"] = max(diffs)
    assert max(diffs) < 1e-12
    e103 = json.loads((E103D / "out" / "results.json").read_text(encoding="utf-8"))
    e102 = json.loads((EXP / "E102_Market_Access_Forecasting" / "out" / "results.json").read_text(encoding="utf-8"))
    H = R.load_history()
    out_h = R.outcome_series()
    rel101 = E101.rel_scores(R.level_indicator())
    S63 = pd.read_csv(E101.E63, dtype={"province_code": str})
    a1_63 = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_price) for r in S63.itertuples()}
    PNL = L.panel(cpi, list(range(qi("2021-Q2"), qi("2026-Q3") + 1)))
    pct = {k: L.percentiles({key: v[k] for key, v in PNL.items()}) for k in ("REL", "PERS", "LVL")}

    for lead in (1, 2):
        rows = E101.lead_rows(H, lead, a1_63, rel101)
        relrows = [{**x, "dom": {**x["dom"], "A": pct["REL"].get((x["t"], x["code"]))}} for x in rows]
        R.MIN_DOMAINS = 4
        prov = {"SERVED": E101.served_equal(rows, lead)[0], "REL-only": E101.served_equal(relrows, lead)[0]}
        R.MIN_DOMAINS = 3
        noH = [d for d in R.DOMS if d != "H"]
        prov["REL-only-noH"], prov["REL-only-noH-EQ"] = E101.served_equal(relrows, lead, doms=noH)
        R.MIN_DOMAINS = 4
        reg = {a: {} for a in prov}
        for a, v in prov.items():
            for q in {x["target"] for x in rows}:
                vals = [v.get((q, p)) for p in L.PROVS if v.get((q, p)) is not None]
                if vals:
                    reg[a][q] = float(np.mean(vals))
        reg["P0"] = {x["target"]: x["s"]["H1"] for x in rows}
        Q = E3.RUN.regional_eval(reg, out_h, lead)
        Q = Q[Q["SERVED"].notna()].reset_index(drop=True)
        # A2 reproduction vs E103
        old = pd.read_csv(E103D / "out" / f"regional_lead{lead}.csv")
        mm = Q.merge(old[["target", "SERVED", "REL-only"]], on="target", suffixes=("", "_e103"))
        gate = {c: float((mm[c] - mm[f"{c}_e103"]).abs().max()) for c in ("SERVED", "REL-only")}
        sc = E3.score(Q, ["SERVED", "REL-only", "REL-only-noH", "REL-only-noH-EQ", "P0", "ALWAYS"], "SERVED")
        o = e103["leads"][str(lead)]["arms"]["REL-only"]
        gate["brier_equal"] = abs(sc["REL-only"]["brier"] - o["brier"]) < 1e-12
        gate["paired_equal"] = all(abs(sc["REL-only"]["vs_SERVED"][k] - o["vs_SERVED"][k]) < 1e-12 for k in ("mean_d", "perm_p"))
        gate["ci_equal"] = sc["REL-only"]["vs_SERVED"]["ci95"] == o["vs_SERVED"]["ci95"]
        assert max(gate["SERVED"], gate["REL-only"]) < 1e-9 and gate["brier_equal"] and gate["paired_equal"] and gate["ci_equal"], gate
        # A3 selection-aware max-statistic permutation over the E103 family (E103 regional values)
        old = old[old["SERVED"].notna()]
        y = old["y"].to_numpy(float)
        D = np.column_stack([(old[a] - y) ** 2 - (old["SERVED"] - y) ** 2 for a in FAMILY])
        n = len(y)
        signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
        means = signs @ D / n                                   # patterns x arms
        obs = D[:, FAMILY.index("REL-only")].mean()
        fam_p = float((means.min(axis=1) <= obs + 1e-15).mean())
        best_obs = FAMILY[int(np.argmin(D.mean(axis=0)))]
        res_l = {"quarters": int(len(Q)), "reproduction_gate": gate, "arms": sc,
                 "A3_selection_aware": {"family": FAMILY, "best_observed_arm": best_obs, "REL_only_mean_d": float(obs),
                                        "unadjusted_one_sided_p": float((means[:, FAMILY.index('REL-only')] <= obs + 1e-15).mean()),
                                        "family_wise_one_sided_p": fam_p}}
        # A4 relations
        ev = [x for x in rows if x["target"] in set(Q["target"])]
        X = pd.DataFrame([{"pREL": pct["REL"].get((x["t"], x["code"])), "A1": x["s"]["A1"], "A2": x["s"]["A2"], "A3": x["s"]["A3"],
                           "pLVL": pct["LVL"].get((x["t"], x["code"])), "pPERS": pct["PERS"].get((x["t"], x["code"]))}
                          for x in ev]).astype(float)
        res_l["A4_pREL_spearman"] = X.corr(method="spearman", min_periods=8)["pREL"].round(2).to_dict()
        feats = {qi(q): f for q, f in e102["leads"][str(lead)]["features"].items()}
        F = pd.DataFrame([{**f, "t": t, "H_target": out_h.get(qs(t + lead))} for t, f in feats.items()
                          if t <= qi(E3.RUN.EVAL_END[lead])]).dropna(subset=["H_target"])
        res_l["A4_regional_REL_spearman"] = {k: float(spearmanr(F["REL"], F[k], nan_policy="omit").correlation)
                                             for k in ("H_last", "E1raw", "A2raw", "LVL", "PERS")}
        # B1 partial correlations (exploratory)
        g = F.dropna(subset=["REL", "H_last"])
        g2 = F.dropna(subset=["REL", "H_last", "E1raw"])
        res_l["B1_partial_spearman"] = {
            "REL_vs_Htarget_raw": {"rho": float(spearmanr(g["REL"], g["H_target"]).correlation), "n": int(len(g))},
            "given_H_last": {"rho": partial_spearman(g["REL"], g["H_target"], [g["H_last"]]), "n": int(len(g))},
            "given_H_last_E1": {"rho": partial_spearman(g2["REL"], g2["H_target"], [g2["H_last"], g2["E1raw"]]), "n": int(len(g2))},
            "H_last_vs_Htarget": {"rho": float(spearmanr(g["H_last"], g["H_target"]).correlation), "n": int(len(g))}}
        # C trained hunger-level forecasts
        from sklearn.linear_model import Ridge
        fc = {a: {} for a in ["RW"] + list(MODELS)}
        ntrain = {}
        for t, f in sorted(feats.items()):
            tq = qs(t + lead)
            known = L.full_quarters_posted(TS.issue_of(t))
            if f.get("H_last") is not None:
                fc["RW"][tq] = f["H_last"]
            for a, cols in MODELS.items():
                tr = [(feats[tp], known[qs(tp + lead)]) for tp in feats if tp < t and qs(tp + lead) in known
                      and all(feats[tp].get(c) is not None for c in cols)]
                if len(tr) < L.MIN_TRAIN or any(f.get(c) is None for c in cols):
                    continue
                Xtr = np.array([[ff[c] for c in cols] for ff, _ in tr], float)
                ytr = np.array([v for _, v in tr], float)
                mu, sd = Xtr.mean(0), Xtr.std(0)
                sd[sd == 0] = 1
                mdl = Ridge(alpha=1.0).fit((Xtr - mu) / sd, ytr)
                fc[a][tq] = float(mdl.predict(((np.array([f[c] for c in cols], float) - mu) / sd).reshape(1, -1))[0])
                ntrain.setdefault(a, {})[tq] = len(tr)
        common = sorted(set.intersection(*[set(v) for v in fc.values()]) & set(out_h), key=qi)
        yv = np.array([out_h[q] for q in common])
        lev = {"quarters": common, "n": len(common), "train_pairs_first_last": {a: [ntrain[a][common[0]], ntrain[a][common[-1]]]
                                                                                  for a in MODELS} if common else {}, "models": {}}
        for a in fc:
            p = np.array([fc[a][q] for q in common])
            e = p - yv
            m = {"rmse": float(np.sqrt(np.mean(e ** 2))), "mae": float(np.mean(np.abs(e))), "mean_error": float(e.mean()),
                 "class_accuracy": float(((p > 11.3) == (yv > 11.3)).mean()), "outcome_HIGH": int((yv > 11.3).sum())}
            if a != "RW":
                rw = np.array([fc["RW"][q] for q in common])
                d = e ** 2 - (rw - yv) ** 2
                rng = np.random.default_rng(2026)
                bs = [float(np.mean(rng.choice(d, len(d)))) for _ in range(2000)]
                m["vs_RW"] = {"mean_sq_diff": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                              "perm_p": E3.permutation_p(d), "wins": int((d < -1e-12).sum()), "losses": int((d > 1e-12).sum())}
            lev["models"][a] = m
        if "R1" in lev["models"] and "R0" in lev["models"]:
            p1 = np.array([fc["R1"][q] for q in common]); p0 = np.array([fc["R0"][q] for q in common])
            d = (p1 - yv) ** 2 - (p0 - yv) ** 2
            lev["R1_vs_R0"] = {"mean_sq_diff": float(d.mean()), "perm_p": E3.permutation_p(d)}
        lev["forecasts"] = {a: {q: fc[a].get(q) for q in common} for a in fc}
        res_l["C_level_models"] = lev
        res["leads"][str(lead)] = res_l
    after = frozen_files()
    res["frozen_files_unchanged"] = before == after
    assert before == after, "a frozen file changed"
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: {kk: res["leads"][k][kk] for kk in ("reproduction_gate", "A3_selection_aware")} for k in res["leads"]}, indent=1))


if __name__ == "__main__":
    main()
