"""Pre-tuning verification (PROTOCOL.md section 2): the target, threshold, probability law, scoring and the
publication-time behaviour of every feature, for every hyperparameter configuration, before any tuned score exists.

    python -B runner/e35_verify.py   -> verification/VERIFICATION.json (exit 1 if any check fails)

No candidate is scored here; the E32 evaluation file is read only to confirm that its labels and Brier arithmetic
are reproduced by an independent computation.
"""
from __future__ import annotations

import copy
import json
import sys

import e35_common as E
import e35_grid as G

np, pd, C, L, P, M = E.np, E.pd, E.C, E.L, E.P, E.M
E32RUN = E.E32 / "runs" / "20261014T165201Z"
DATES = {1: ["2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"],
         2: ["2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]}
OPERATIONAL = {1: "2026-Q4", 2: "2027-Q1"}
SEED = 35


def origins():
    for k, ds in DATES.items():
        for T in ds + [OPERATIONAL[k]]:
            yield k, C.qk(T) - k, T


def v1_target(d) -> dict:
    """S1 = H + 2D: H = mean of the quarter's definition-A rounds (regional), D = province food YoY minus the
    five-province mean (F minus its cross-province mean)."""
    r = d.rounds[d.rounds["definition_A"].astype(str).str.lower() == "true"]
    H = r.groupby("quarter")["H"].mean()
    dq = E.pd.read_csv(C.INP / "d_quarterly_panel.csv", dtype={"province_code": str})
    dq["D_recomputed"] = dq["F"] - dq.groupby("quarter")["F"].transform("mean")
    s = d.S1.merge(dq, on=["province_code", "quarter"], how="left")
    s["S1_recomputed"] = s["quarter"].map(H) + 2 * s["D"]
    err_s1 = float((s["S1"] - s["S1_recomputed"]).abs().max())
    err_d = float((dq["D"] - dq["D_recomputed"]).abs().max())
    dsum = float(dq.groupby("quarter")["D"].sum().abs().max())
    dn = E.pd.read_csv(C.INP / "dnow_panel.csv", dtype={"province_code": str})
    dnsum = float(dn.groupby("quarter")["Dnow"].sum().abs().max())
    rice = max(abs(sum(d.rice.get((p, t), 0.0) for p in C.PROVS)) for t in {t for _, t in d.rice})
    ok = err_s1 < 1e-9 and err_d < 1e-9 and dsum < 1e-9 and dnsum < 1e-9 and rice < 1e-9 and s["S1_recomputed"].notna().all()
    return {"pass": bool(ok), "max_abs_S1_error": err_s1, "max_abs_D_error": err_d, "max_abs_sum_D": dsum,
            "max_abs_sum_Dnow": dnsum, "max_abs_sum_rice_rel": rice, "S1_rows": int(len(s))}


def v2_threshold_and_labels(d) -> dict:
    """tau(t) = median S1 over province-quarters <= t-1 whose definition-A rounds were ALL usable before O(t);
    label = S1(T) > tau(t) (strict). Independent recomputation, compared with the engine and with E32's file."""
    r = d.rounds[d.rounds["definition_A"].astype(str).str.lower() == "true"].copy()
    pub = E.pd.to_datetime(r["published"], errors="coerce", format="ISO8601")
    eff = E.pd.to_datetime(r["published_eff"], errors="coerce", format="ISO8601")
    r["usable"] = pub.where(r["date_type"].astype(str).str.startswith("verified") & pub.notna(), eff)
    bad, worst = [], 0.0
    for k, t, T in origins():
        o = L.origin(t)
        ok_q = [q for q, g in r.groupby("quarter") if C.qk(q) <= t - 1 and g["usable"].notna().all() and (g["usable"] < o).all()]
        tau = float(d.S1[d.S1["quarter"].isin(ok_q)]["S1"].median())
        worst = max(worst, abs(tau - d.tau(t)))
        if abs(tau - d.tau(t)) > 1e-12:
            bad.append((k, T))
    pr = E.pd.read_csv(E32RUN / "predictions.csv", dtype={"province_code": str})
    lab_bad = 0
    for x in pr.drop_duplicates(["lead", "target_quarter", "province_code"]).itertuples():
        t = C.qk(x.target_quarter) - int(x.lead)
        y = int(d.Sv[(x.province_code, C.qk(x.target_quarter))] > d.tau(t))
        lab_bad += int(y != int(x.y))
    return {"pass": not bad and lab_bad == 0, "max_abs_tau_error": worst, "tau_mismatches": bad,
            "E32_label_mismatches": lab_bad}


def v3_probability_law(d) -> dict:
    """P(S1 > tau) with S1 = H + 2D, H ~ N(mu_H, V_H), D ~ N(mu_D, s^2) independent: Monte-Carlo check of the
    closed form for every configuration at the operational lead-1 origin."""
    rng = np.random.default_rng(SEED)
    t = C.qk("2026-Q3")
    comp = G.components(d, t, 1)
    worst = 0.0
    for cfg in G.GRID:
        Dc = comp["D"][cfg.dset]
        muH = comp["mu_H"] + cfg.lam * comp["slope"] * comp["news_dev"]
        pr = G.probs(comp, cfg)
        for p in C.PROVS:
            h = rng.normal(muH, cfg.c * np.sqrt(comp["V_H"]), 400_000)
            dd = rng.normal(Dc["muD"][p], cfg.c * Dc["s"], 400_000)
            worst = max(worst, abs(float(((h + 2 * dd) > comp["tau"]).mean()) - pr[p]))
    return {"pass": worst < 0.004, "max_abs_mc_error": worst, "draws": 400_000,
            "note": "tolerance 0.004 (about 5 Monte-Carlo standard errors at p = 0.5)"}


def v4_scoring() -> dict:
    """Brier = mean (p - y)^2 per date, then the mean over dates; accuracy at the fixed 0.5 cut. Recompute E32's
    lead-1 mean per-date Brier for every arm with plain numpy and compare with its results.json."""
    pr = E.pd.read_csv(E32RUN / "predictions.csv", dtype={"province_code": str})
    res = json.loads((E32RUN / "results.json").read_text(encoding="utf-8"))
    want = res["acceptance"]["mean_per_date_brier_all_lead1"]
    worst = 0.0
    for arm, v in want.items():
        g = pr[(pr["lead"] == 1) & (pr["arm"] == arm)]
        p = np.clip(g["p"].to_numpy(float), M.EPS, 1 - M.EPS)
        b = E.pd.Series((p - g["y"].to_numpy(float)) ** 2).groupby(g["t"].to_numpy()).mean().mean()
        worst = max(worst, abs(float(b) - v))
    rows_per_date = pr[pr["lead"] == 1].groupby(["arm", "t"]).size()
    return {"pass": worst < 1e-9 and set(rows_per_date) == {5}, "max_abs_brier_error": worst,
            "tolerance": "1e-9: predictions.csv stores 10 significant digits, results.json full precision",
            "rows_per_date": sorted(set(int(x) for x in rows_per_date)),
            "note": "five provinces per date, so the per-date mean weights every row equally"}


def v5_timing(d) -> dict:
    """Every input at O(t) was released before O(t): rounds usable before O(t); latest H quarter and labelled
    quarters <= t-1; D_last = quarter t-1; Dnow / rice_rel = months 1-2 of t; news = publication quarter t; every
    D training target and every training label quarter <= t-1 and posted."""
    issues = []
    for k, t, T in origins():
        o = L.origin(t)
        rr = P.rounds_at_origin(d.rounds, o)
        if not (P._usable_from(rr) < o).all():
            issues.append((k, T, "round usable after origin"))
        X = d.features(t, k)
        if C.qk(X["H_last_quarter"].iloc[0]) > t - 1 or C.qk(X["last_label_quarter"].iloc[0]) > t - 1:
            issues.append((k, T, "H or label quarter after t-1"))
        for r in X.itertuples():
            if r.D_last != d.Dm.get((r.province_code, t - 1), np.nan) and not (r.D_last != r.D_last):
                issues.append((k, T, "D_last not quarter t-1"))
            if r.Dnow != d.Nm.get((r.province_code, t), np.nan) and not (r.Dnow != r.Dnow):
                issues.append((k, T, "Dnow not quarter t"))
            n = d.nw.get((r.province_code, t))
            if n is not None and abs(r.news_n - np.log1p(n.n_rel)) > 1e-12:
                issues.append((k, T, "news not quarter t"))
        posted = set(d.posted_quarters(o))
        if any(q > t - 1 or q not in posted for q in d.training_pairs(t, k)["target_q"].unique()):
            issues.append((k, T, "training label not posted"))
    return {"pass": not issues, "origins_checked": sum(1 for _ in origins()), "issues": issues,
            "release_assumption": "PSA CPI for month m is released in month m+1 (E25/E31 convention): D(t-1) and "
                                  "months 1-2 of t are public before O(t) = first day of t+1; D(t) is not."}


def scrambled(d0, t: int, rng) -> "L.Data":
    """A copy of the data in which everything not public at O(t) is replaced by noise."""
    d = copy.copy(d0)
    o = L.origin(t)
    d.rounds = d0.rounds.copy()
    late = ~(P._usable_from(d.rounds) < o)
    d.rounds.loc[late, "H"] = rng.uniform(1, 40, int(late.sum()))
    d.S1 = d0.S1.copy()
    posted = set(d0.posted_quarters(o))
    fut = (d.S1["tq"] >= t) | ~d.S1["tq"].isin(posted)          # not yet labelled-and-posted at O(t)
    d.S1.loc[fut, "S1"] = rng.uniform(-20, 60, int(fut.sum()))
    d.Sv = {(p, q): s for p, q, s in zip(d.S1["province_code"], d.S1["tq"], d.S1["S1"])}
    d.Dm = {key: (rng.normal(0, 9) if key[1] >= t else v) for key, v in d0.Dm.items()}
    d.Nm = {key: (rng.normal(0, 9) if key[1] >= t + 1 else v) for key, v in d0.Nm.items()}
    d.rice = {key: (rng.normal(0, 9) if key[1] >= t + 1 else v) for key, v in d0.rice.items()}
    d.nw = {key: (v._replace(n_rel=int(rng.integers(0, 500))) if key[1] >= t + 1 else v) for key, v in d0.nw.items()}
    return d                                            # method caches are keyed by instance, so d0's are not reused


def v6_scramble(d0) -> dict:
    rng = np.random.default_rng(SEED)
    worst, n = 0.0, 0
    for k, t, T in origins():
        base = G.all_probs(d0, t, k)
        for _ in range(2):
            ds = scrambled(d0, t, rng)
            got = G.all_probs(ds, t, k)
            for cid in base:
                for p in C.PROVS:
                    worst = max(worst, abs(base[cid][p] - got[cid][p]))
                    n += 1
    return {"pass": worst == 0.0, "max_abs_change": worst, "probabilities_compared": n,
            "scrambled": "SWS rounds not usable at O(t); S1 of quarters >= t or not posted at O(t); D of quarters >= t; Dnow, rice and news of quarters > t"}


def v7_default_reproduces_e32(d) -> dict:
    pr = E.pd.read_csv(E32RUN / "predictions.csv", dtype={"province_code": str})
    g = pr[pr["arm"] == "E32-PCFN"]
    worst = 0.0
    for x in g.itertuples():
        t = C.qk(x.target_quarter) - int(x.lead)
        worst = max(worst, abs(G.probs(G.components(d, t, int(x.lead)), G.DEFAULT_CFG)[x.province_code] - x.p))
    return {"pass": worst < 5e-10, "max_abs_diff_vs_E32_predictions_csv": worst, "rows": int(len(g)),
            "note": "E32 wrote probabilities with 10 significant digits"}


def main() -> int:
    d = L.Data()
    out = {"dataset_sha256": E.dataset_manifest(), "checks": {}}
    for name, fn in (("V1_target_S1_H_plus_2D", lambda: v1_target(d)),
                     ("V2_threshold_and_labels", lambda: v2_threshold_and_labels(d)),
                     ("V3_probability_law", lambda: v3_probability_law(d)),
                     ("V4_scoring_arithmetic", v4_scoring),
                     ("V5_publication_timing", lambda: v5_timing(d)),
                     ("V6_scramble_the_future_all_configs", lambda: v6_scramble(d)),
                     ("V7_default_config_equals_E32_PCFN", lambda: v7_default_reproduces_e32(d))):
        out["checks"][name] = E.C.clean(fn())
        print(name, "PASS" if out["checks"][name]["pass"] else "FAIL")
    out["all_pass"] = all(c["pass"] for c in out["checks"].values())
    E.C.write_json(E.E35 / "verification" / "VERIFICATION.json", out)
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
