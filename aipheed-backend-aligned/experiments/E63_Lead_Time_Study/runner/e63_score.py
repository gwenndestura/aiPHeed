"""E63 step 2 (PROTOCOL sections 5-8): score the SEALED lead-1/2/3 forecasts against T43 and apply the reliability rule.
Refuses to run unless PROTOCOL.md and sealed/predictions.csv match their recorded hashes.

    backend/venv/Scripts/python.exe -B runner/e63_score.py -> tables/*.csv, out/scores.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e63_lib as H  # noqa: E402

F, L, np, pd = H.F, H.L, H.np, H.pd
from scipy.stats import binomtest  # noqa: E402

SEALED = H.E63 / "sealed" / "predictions.csv"
B_DRAWS, SEED, CLIP = 4000, 63, (0.001, 0.999)
ARMS = {"E56": "E56_p", "E58_EW": "E56_p_price", "PERSIST": "PERSIST_p", "CLIM": "CLIM_p", "MAJORITY": "MAJORITY_p",
        "PROVCLIM": "PROVCLIM_p"}
MODELS, REFS = ["E56", "E58_EW"], ["PERSIST", "CLIM"]
COMMON = [L.qs(q) for q in range(L.qi("2024-Q3"), L.qi("2026-Q3") + 1)]
CI_METRICS = ["accuracy", "balanced_accuracy", "recall_HIGH", "precision_HIGH", "brier", "log_loss"]


def verify():
    want = (H.E63 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((H.E63 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    want_s = (SEALED.parent / "predictions.csv.sha256").read_text().split()[0]
    got_s = hashlib.sha256(SEALED.read_bytes()).hexdigest()
    if got_s != want_s:
        raise SystemExit("sealed/predictions.csv changed after sealing")
    return got, got_s


# ================================================================================================ metrics
def core(y, p):
    """Point metrics that the bootstrap also needs."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    yh = (p >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    rh = tp / (tp + fn) if tp + fn else np.nan
    rl = tn / (tn + fp) if tn + fp else np.nan
    pc = np.clip(p, *CLIP)
    return {"accuracy": (tp + tn) / len(y), "balanced_accuracy": np.nanmean([rh, rl]) if np.isfinite([rh, rl]).all() else np.nan,
            "recall_HIGH": rh, "precision_HIGH": tp / (tp + fp) if tp + fp else np.nan, "recall_LOW": rl,
            "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))),
            "pred_HIGH": tp + fp, "correct": tp + tn}


def auc(y, p):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p)) if len(set(y)) == 2 else np.nan


def calibration(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    out = {"citl": float(y.mean() - p.mean()), "slope": np.nan}
    if len(set(np.round(p, 12))) > 2 and len(set(y)) == 2:
        from sklearn.linear_model import LogisticRegression
        z = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6))).reshape(-1, 1)
        try:
            out["slope"] = float(LogisticRegression(penalty=None, max_iter=5000).fit(z, y).coef_[0, 0])
        except Exception:                                     # not estimable (separation)
            pass
    return out


def bins(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    k = np.minimum((p * 5).astype(int), 4)
    return [{"bin": f"{b / 5:.1f}-{(b + 1) / 5:.1f}", "n": int((k == b).sum()),
             "mean_p": float(p[k == b].mean()) if (k == b).any() else np.nan,
             "observed_HIGH": float(y[k == b].mean()) if (k == b).any() else np.nan} for b in range(5)]


# ================================================================================================ one evaluation set
def evaluate(S: pd.DataFrame, lead: int, set_name: str):
    qs = sorted(S["target"].unique(), key=L.qi)
    idx = {q: np.where(S["target"].to_numpy() == q)[0] for q in qs}
    y = S["y"].to_numpy(float)
    P = {a: S[c].to_numpy(float) for a, c in ARMS.items()}
    rng = np.random.default_rng(SEED)
    draws = [np.concatenate([idx[q] for q in rng.choice(qs, size=len(qs), replace=True)]) for _ in range(B_DRAWS)]
    metrics, paired, rel = [], [], []
    for a in ARMS:
        m = {"lead": lead, "set": set_name, "arm": a, "n": int(len(y)), "quarters": len(qs), "actual_HIGH": int(y.sum()),
             **core(y, P[a]), "auc": auc(y, P[a]), **calibration(y, P[a])}
        boot = {k: [] for k in CI_METRICS}
        for ix in draws:
            c = core(y[ix], P[a][ix])
            for k in CI_METRICS:
                boot[k].append(c[k])
        for k in CI_METRICS:
            v = np.asarray(boot[k], float)
            v = v[np.isfinite(v)]
            m[f"{k}_lo"], m[f"{k}_hi"] = ((float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975)))
                                          if len(v) else (np.nan, np.nan))
        metrics.append(m)
        if set_name == "full":
            rel += [{"lead": lead, "arm": a, **b} for b in bins(y, P[a])]
    for mdl in MODELS:
        for ref in REFS:
            d = (P[mdl] - y) ** 2 - (P[ref] - y) ** 2
            qd = np.array([d[idx[q]].mean() for q in qs])
            wins, losses = int((qd < 0).sum()), int((qd > 0).sum())
            pv = float(binomtest(wins, wins + losses, 0.5).pvalue) if wins + losses else 1.0
            bd = np.array([d[ix].mean() for ix in draws])
            lo, hi = float(np.quantile(bd, 0.025)), float(np.quantile(bd, 0.975))
            ci_ok, sign_ok = hi < 0, (pv < 0.05 and wins > losses)
            paired.append({"lead": lead, "set": set_name, "model": mdl, "baseline": ref, "quarters": len(qs),
                           "mean_brier_diff": float(d.mean()), "ci_lo": lo, "ci_hi": hi, "quarter_wins": wins,
                           "quarter_losses": losses, "quarter_ties": int(len(qs) - wins - losses), "sign_p": pv,
                           "ci_below_0": ci_ok, "sign_test_supports": sign_ok,
                           "verdict": "supported" if ci_ok and sign_ok else
                           ("suggestive, not established" if ci_ok or sign_ok else "not supported")})
    return metrics, paired, rel


def per_quarter(S, lead):
    out = []
    for q, g in S.groupby("target", sort=False):
        y = g["y"].to_numpy(float)
        r = {"lead": lead, "issue_quarter": g["origin_quarter"].iloc[0], "target": q, "n": len(g),
             "actual_HIGH": int(y.sum())}
        for a in ("E56", "E58_EW", "PERSIST", "CLIM"):
            c = core(y, g[ARMS[a]].to_numpy(float))
            r[f"{a}_pred_HIGH"], r[f"{a}_accuracy"], r[f"{a}_brier"] = c["pred_HIGH"], c["accuracy"], c["brier"]
        r["E56_mean_p"] = float(g["E56_p"].mean())
        r["E56_p_hunger"] = float(g["E56_p_hunger"].iloc[0])
        out.append(r)
    return out


# ================================================================================================ rule (section 8)
def verdicts(paired: pd.DataFrame, set_name: str, model: str) -> dict:
    out = {}
    for h in H.LEADS:
        g = paired[(paired["lead"] == h) & (paired["set"] == set_name) & (paired["model"] == model)]
        if not len(g):
            out[h] = {"reliable": False, "reason": "not computable under the pre-registered cutoffs (PROTOCOL 1)"}
            continue
        v = {r.baseline: r.verdict for r in g.itertuples()}
        out[h] = {"reliable": all(x == "supported" for x in v.values()), "vs": v}
    rel = [h for h in H.LEADS if out[h]["reliable"]]
    far = max(rel) if rel else None
    return {"per_lead": out, "furthest_reliable_lead": far,
            "all_shorter_leads_reliable": (all(out[h]["reliable"] for h in range(1, far)) if far else None)}


def main():
    proto, sealed = verify()
    S = pd.read_csv(SEALED, dtype={"province_code": str})
    Y = F.t43_labels(L.load())                                   # full data to 2026-10-14; labels read only here
    lab = Y.set_index(["province_code", "quarter"])["T43"]
    S["y"] = [lab.get((p, q), np.nan) for p, q in zip(S["province_code"], S["target"])]
    assert S["y"].notna().all(), "a sealed row has no T43 label"
    assert S[list(ARMS.values())].notna().all().all(), "a sealed probability is missing"
    common = set.intersection(*[set(S.loc[S["lead"] == h, "target"]) for h in (1, 2, 3)])
    assert sorted(common, key=L.qi) == COMMON, sorted(common)
    M, Pd, R, Q = [], [], [], []
    for h in sorted(S["lead"].unique()):
        g = S[S["lead"] == h].reset_index(drop=True)
        for name, sub in (("full", g), ("common", g[g["target"].isin(COMMON)].reset_index(drop=True))):
            m, p, r = evaluate(sub, int(h), name)
            M += m
            Pd += p
            R += r
        Q += per_quarter(g, int(h))
    M, Pd, R, Q = pd.DataFrame(M), pd.DataFrame(Pd), pd.DataFrame(R), pd.DataFrame(Q)
    T = H.E63 / "tables"
    M.to_csv(T / "lead_metrics.csv", index=False, float_format="%.6g")
    Pd.to_csv(T / "paired_tests.csv", index=False, float_format="%.6g")
    R.to_csv(T / "reliability_bins.csv", index=False, float_format="%.6g")
    Q.to_csv(T / "per_quarter.csv", index=False, float_format="%.6g")
    res = {"protocol_sha256": proto, "sealed_sha256": sealed, "bootstrap": {"draws": B_DRAWS, "seed": SEED},
           "rule": {f"{mdl}_{s}": verdicts(Pd, s, mdl) for mdl in MODELS for s in ("full", "common")}}
    (H.E63 / "out" / "scores.json").write_text(json.dumps(res, indent=1, default=str))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    show = ["lead", "arm", "n", "quarters", "actual_HIGH", "accuracy", "accuracy_lo", "accuracy_hi", "balanced_accuracy",
            "recall_HIGH", "precision_HIGH", "brier", "brier_lo", "brier_hi", "log_loss", "auc", "citl", "slope"]
    print(M[M["set"] == "full"][show].round(3).to_string(index=False))
    print(Pd.round(4).to_string(index=False))
    print(json.dumps(res["rule"], indent=1, default=str))


if __name__ == "__main__":
    main()
