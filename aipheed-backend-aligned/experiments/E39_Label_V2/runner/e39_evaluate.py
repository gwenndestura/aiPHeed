"""E39 one-time evaluation (scoring_v2_spec.json): Label A, Targets B and C, leads 1 and 2. Verifies the freeze first
and refuses to run twice (a run directory already present stops it).

    <backend venv python> -B runner/e39_evaluate.py   -> runs/eval_<UTC>/{predictions.csv, results.json}
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e39_lib as L  # noqa: E402

np, pd, M = L.np, L.pd, L.M
E39 = L.E39
PRIMARY = ["persistence", "climatology"]
SECONDARY = {"A": ["seasonal_naive", "AR1", "always_LOW", "always_HIGH", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP",
                   "B5_LGBM_GOV", "B6_LGBM_NLP"],
             "B": ["seasonal_naive", "AR1", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP", "B5_LGBM_GOV", "B6_LGBM_NLP"]}
SECONDARY["C"] = SECONDARY["B"]


def verify_freeze() -> dict:
    fr = json.loads((E39 / "frozen" / "E39_FREEZE.json").read_text())
    for f, h in fr["sha256"].items():
        got = hashlib.sha256((E39 / f).read_bytes()).hexdigest()
        if got != h:
            raise SystemExit(f"{f} changed after freezing")
    return fr


def two_sided(diff) -> float | None:
    d = np.asarray(diff, float)
    if len(d) == 0:
        return None
    return float(min(1.0, 2 * min(M.signflip_p(d), M.signflip_p(-d))))


def score(P: pd.DataFrame, kind: str, k: int, meta: dict) -> dict:
    s = P[(P["status"] == "Scored") & P["pred"].notna()].copy()
    s["y"] = s["y"].astype(float)
    arms = sorted(s["arm"].unique())
    out = {"dates": sorted(s["target_quarter"].unique()), "n_dates": int(s["target_quarter"].nunique()),
           "rows_model": int((s["arm"] == "model").sum()),
           "withheld": [q for q, m in meta.items() if m["status"] == "Withheld"],
           "missing_round": [q for q, m in meta.items() if m["status"] == "Missing round"],
           "forecast_only": [q for q, m in meta.items() if m["status"] == "No outcome yet"]}
    if out["n_dates"] == 0:
        out["verdict"] = "not evaluable (no scored date)"
        return out
    loss = {a: L.per_date_loss(s[s["arm"] == a], kind) for a in arms}
    if kind == "A":
        m = s[s["arm"] == "model"]
        hi_dates = int(m.groupby("target_quarter")["y"].sum().gt(0).sum())
        out["HIGH_dates"] = hi_dates
        out["evaluable"] = hi_dates >= 3
        out["brier"] = {a: float(v.mean()) for a, v in loss.items()}
        out["pooled"] = {}
        for a in ["model"] + PRIMARY + SECONDARY["A"]:
            g = s[s["arm"] == a]
            pb = L.pooled_binary(g)
            pb["balanced_accuracy_ci95"] = L.boot_dates(g, lambda x: L.pooled_binary(x)["balanced_accuracy"])
            pb["auc_ci95"] = L.boot_dates(g, lambda x: L.pooled_binary(x)["auc"])
            out["pooled"][a] = pb
        raw = m.assign(pred=m["raw"])
        out["calibration"] = {"methods_used": m.drop_duplicates("target_quarter")["calibration"].value_counts().to_dict(),
                              "brier_raw": float(L.per_date_loss(raw, "A").mean()),
                              "brier_calibrated": out["brier"]["model"],
                              "mean_p": float(m["pred"].mean()), "observed_rate": float(m["y"].mean()),
                              "reliability": [{"bin": [lo, hi], "n": int(((m.pred >= lo) & (m.pred < hi)).sum()),
                                               "mean_p": float(m.pred[(m.pred >= lo) & (m.pred < hi)].mean()) if ((m.pred >= lo) & (m.pred < hi)).any() else None,
                                               "observed": float(m.y[(m.pred >= lo) & (m.pred < hi)].mean()) if ((m.pred >= lo) & (m.pred < hi)).any() else None}
                                              for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01))]}
    else:
        out["MAE"] = {a: float(v.mean()) for a, v in loss.items()}
        rm = {a: float(((s[s["arm"] == a]["pred"] - s[s["arm"] == a]["y"]) ** 2).groupby(s[s["arm"] == a]["target_quarter"]).mean().pow(.5).mean()) for a in arms}
        out["RMSE"] = rm
        scale = {q: meta[q]["naive_scale"] for q in out["dates"]}
        out["MASE"] = {a: float(np.mean([loss[a][q] / scale[q] for q in out["dates"] if scale[q]])) for a in arms}
        m = s[s["arm"] == "model"]
        iv = m[m["lo"].notna()]
        out["interval"] = {"rows_with_interval": int(len(iv)), "dates_with_interval": int(iv["target_quarter"].nunique()),
                           "coverage_80": float(((iv["y"] >= iv["lo"]) & (iv["y"] <= iv["hi"])).mean()) if len(iv) else None,
                           "coverage_ci95": L.boot_dates(iv.assign(pred=0), lambda x: float(((x["y"] >= x["lo"]) & (x["y"] <= x["hi"])).mean())) if len(iv) else None}
        if kind == "B":
            sp, top = [], []
            for q, g in m.groupby("target_quarter"):
                if g["pred"].nunique() > 1 and g["y"].nunique() > 1:
                    sp.append(g["pred"].rank().corr(g["y"].rank()))
                pt = set(g.sort_values("pred", ascending=False)["province_code"][:2])
                ot = set(g.sort_values("y", ascending=False)["province_code"][:2])
                top.append(len(pt & ot) / 2)
            out["ranking"] = {"spearman_mean": float(np.mean(sp)) if sp else None, "spearman_dates": len(sp),
                              "top2_hit_rate": float(np.mean(top)), "chance": 0.4,
                              "top2_ci95": L.boot_dates(m, lambda x: float(np.mean([
                                  len(set(g.sort_values("pred", ascending=False)["province_code"][:2]) &
                                      set(g.sort_values("y", ascending=False)["province_code"][:2])) / 2
                                  for _, g in x.groupby("target_quarter")])))}
    # skill and paired tests over the declared comparison set
    comp = PRIMARY + SECONDARY[kind]
    tests, raw_p = {}, {}
    for ref in comp:
        if ref not in loss:
            continue
        common = loss["model"].index.intersection(loss[ref].index)
        lm, lr = loss["model"][common], loss[ref][common]
        skill = float(1 - lm.mean() / lr.mean()) if lr.mean() > 0 else None
        diff = (lr - lm).to_numpy()
        g = s[s["arm"].isin(["model", ref])]

        def sk(x, ref=ref):
            a, b = L.per_date_loss(x[x.arm == "model"], kind).mean(), L.per_date_loss(x[x.arm == ref], kind).mean()
            return float(1 - a / b) if b > 0 else None
        tests[ref] = {"dates": int(len(common)), "skill": skill, "skill_ci95": L.boot_dates(g, sk),
                      "p_two_sided": two_sided(diff), "primary": ref in PRIMARY}
        raw_p[ref] = tests[ref]["p_two_sided"]
    for ref, v in M.holm(raw_p).items():
        tests[ref]["p_holm"] = v
    out["comparisons"] = tests
    shown = all(tests.get(r, {}).get("skill") is not None and tests[r]["skill"] > 0 and (tests[r].get("p_holm") or 1) < 0.05
                for r in PRIMARY)
    if kind == "A" and not out["evaluable"]:
        out["verdict"] = "not evaluable (HIGH on fewer than 3 independent scored dates)"
    else:
        out["verdict"] = "skill shown" if shown else "not demonstrated"
    return out


def main():
    fr = verify_freeze()
    if any((E39 / "runs").glob("eval_*")):
        raise SystemExit("an evaluation run already exists; the protocol allows exactly one run")
    d = L.Data()
    allP, res = [], {"freeze": fr, "results": {}, "meta": {}}
    for k in (1, 2):
        for kind in L.TARGETS:
            P, meta = L.walk_forward(d, kind, k)
            allP.append(P)
            res["meta"][f"{kind}_lead{k}"] = meta
            res["results"][f"{kind}_lead{k}"] = score(P, kind, k, meta)
            r = res["results"][f"{kind}_lead{k}"]
            print(kind, k, r.get("n_dates"), r.get("verdict"))
    Pr = pd.concat(allP, ignore_index=True)
    # D: A's decision vs B's predicted F above 4, same rows
    for k in (1, 2):
        a = Pr[(Pr.target == "A") & (Pr.lead == k) & (Pr.arm == "model") & Pr.pred.notna()]
        b = Pr[(Pr.target == "B") & (Pr.lead == k) & (Pr.arm == "model") & Pr.pred.notna()]
        j = a.merge(b, on=["target_quarter", "province_code"], suffixes=("_a", "_b"))
        res["results"][f"A_vs_B_lead{k}"] = {"rows": int(len(j)), "disagree": int(((j.pred_a >= .5) != (j.pred_b > L.THRESHOLD)).sum()),
                                             "note": "separate outputs; no coherence is claimed"}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E39 / "runs" / f"eval_{stamp}"
    run.mkdir(parents=True)
    Pr.to_csv(run / "predictions.csv", index=False, float_format="%.10g", lineterminator="\n")
    (run / "results.json").write_bytes(json.dumps(L.C.clean(res), indent=1, default=float).encode())
    print(run.name, hashlib.sha256((run / "predictions.csv").read_bytes()).hexdigest()[:16])


if __name__ == "__main__":
    main()
