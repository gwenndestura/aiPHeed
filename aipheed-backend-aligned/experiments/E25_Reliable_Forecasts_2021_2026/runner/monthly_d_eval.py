"""E25 monthly-origin evaluation of the provincial price component (FROZEN_EVALUATION_PROTOCOL.md 4.4, idea 9).

d(p,m) = provincial food YoY - five-province mean, months 2022-01..2026-06 (2021 YoY would need 2020 indices).
Origin O_m = 15th of month m+1 (month m released). Target y = 1[mean d(p, m+1..m+3) > 0].
Training origins m' with m'+3 <= m (target fully released before O_m), at least 12.
Baselines: SIGN_PERSIST, CAL_PERSIST, CLIM. Candidates: AR_M (FINAL_M), HIER_M.
Tests: per-origin Brier/accuracy differences averaged within non-overlapping blocks of 3 consecutive origins
(overlapping targets), exact one-sided sign-flip over blocks; Holm over the three baselines.
Usage: python -B runner/monthly_d_eval.py [--synthetic SEED]   -> runs/MONTHLY_<id>/"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402

import e23_lib as L  # noqa: E402
import e25lib as E  # noqa: E402

EXP = guard.EXP
MIN_TRAIN = 12
BASE = ["SIGN_PERSIST", "CAL_PERSIST", "CLIM"]
CANDS = ["AR_M", "HIER_M"]
FINAL = "AR_M"


def ymstr(ym):
    return f"{ym // 12}-{ym % 12 + 1:02d}"


def build(mon: pd.DataFrame) -> pd.DataFrame:
    w = mon.pivot(index="ym", columns="province_code", values="d").sort_index()
    yms = list(w.index)
    assert yms == list(range(yms[0], yms[-1] + 1)), "monthly series has gaps"
    rows = []
    for i, m in enumerate(yms):
        if i < 2 or i + 3 >= len(yms):
            continue
        for p in w.columns:
            rows.append({"ym": m, "province_code": p, "d_m": w.loc[m, p], "d_mean3": w.loc[yms[i - 2]:m, p].mean(),
                         "target_mean": w.loc[yms[i + 1]:yms[i + 3], p].mean()})
    f = pd.DataFrame(rows)
    f["y"] = (f["target_mean"] > 0).astype(int)
    return f, w


def predict(f: pd.DataFrame, w: pd.DataFrame):
    out = []
    origins = sorted(f["ym"].unique())
    for m in origins:
        tr = f[f["ym"] + 3 <= m]
        if tr["ym"].nunique() < MIN_TRAIN:
            continue
        assert (tr["ym"] + 3).max() <= m                       # every training target released before O_m
        te = f[f["ym"] == m].sort_values("province_code")
        s = {"SIGN_PERSIST": (te["d_m"] > 0).astype(float).to_numpy()}
        sp = []
        for v in (te["d_m"] > 0).to_numpy():
            g = tr[(tr["d_m"] > 0) == v]
            sp.append((g["y"].sum() + 1) / (len(g) + 2))
        s["CAL_PERSIST"] = np.asarray(sp)
        s["CLIM"] = np.full(5, (tr["y"].sum() + 1) / (len(tr) + 2))
        X, y = tr[["d_m", "d_mean3"]].to_numpy(), tr["target_mean"].to_numpy()
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        sig = float(np.sqrt(np.sum((y - X @ beta) ** 2) / max(len(y) - 2, 1)))
        s["AR_M"] = norm.cdf((te[["d_m", "d_mean3"]].to_numpy() @ beta) / sig)
        # HIER_M: province means of d up to month m shrunk toward 0, regression on deviations
        hist = w.loc[:m]
        mp, n, s2 = hist.mean(), hist.count(), hist.var(ddof=1)
        between = max(0.0, float(mp.var(ddof=1) - (s2 / n).mean()))
        mu = {p: (between / (between + s2[p] / n[p]) if between > 0 else 0.0) * mp[p] for p in hist.columns}
        trm = tr["province_code"].map(mu)
        Xh = np.column_stack([tr["d_m"] - trm, tr["d_mean3"] - trm])
        bh, *_ = np.linalg.lstsq(Xh, tr["target_mean"] - trm, rcond=None)
        rh = (tr["target_mean"] - trm).to_numpy() - Xh @ bh
        sh = float(np.sqrt(np.sum(rh ** 2) / max(len(rh) - 2, 1)))
        tem = te["province_code"].map(mu).to_numpy()
        muh = tem + np.column_stack([te["d_m"] - tem, te["d_mean3"] - tem]) @ bh
        s["HIER_M"] = norm.cdf(muh / sh)
        for mdl, v in s.items():
            for i, r in enumerate(te.itertuples()):
                out.append({"origin_month": ymstr(m), "ym": m, "province_code": r.province_code, "model": mdl,
                            "score": float(v[i]), "y": int(r.y), "n_train_origins": int(tr["ym"].nunique())})
    return pd.DataFrame(out)


def blocked_test(per: pd.Series, block=3):
    v = per.sort_index().to_numpy()
    nb = len(v) // block
    b = v[:nb * block].reshape(nb, block).mean(1)
    t = L.signflip_brier(b)
    return {"n_blocks": nb, "p_one_sided": t["p_one_sided"], "blocks_better": t["origins_better"],
            "blocks_worse": t["origins_worse"], "mean_diff": float(b.mean())}


def score(P: pd.DataFrame) -> dict:
    res = {"n_origins": int(P["ym"].nunique()), "first_origin": P["origin_month"].min(),
           "last_origin": P["origin_month"].max(), "HIGH": int(P[P["model"] == FINAL]["y"].sum()),
           "LOW": int((1 - P[P["model"] == FINAL]["y"]).sum()), "metrics": {}, "tests": {}}
    for m, g in P.groupby("model"):
        mm = L.cls_metrics(g["y"], g["score"])
        mm["balanced_accuracy"] = None if mm["recall"] is None or mm["specificity"] is None else (mm["recall"] + mm["specificity"]) / 2
        res["metrics"][m] = mm
    res["strongest_baseline_brier"] = min(BASE, key=lambda b: res["metrics"][b]["Brier"])
    for a in CANDS:
        res["tests"][a] = {}
        for b in BASE:
            ga = P[P["model"] == a].sort_values(["ym", "province_code"])
            gb = P[P["model"] == b].sort_values(["ym", "province_code"])
            y = ga["y"].to_numpy()
            db = pd.Series((ga["score"].to_numpy() - y) ** 2 - (gb["score"].to_numpy() - y) ** 2).groupby(ga["ym"].to_numpy()).mean()
            ca = ((ga["score"].to_numpy() >= .5) == y).astype(float)
            cb = ((gb["score"].to_numpy() >= .5) == y).astype(float)
            da = pd.Series(cb - ca).groupby(ga["ym"].to_numpy()).mean()
            res["tests"][a][b] = {"brier": blocked_test(db), "accuracy": blocked_test(da),
                                  "brier_unblocked_mc": L.signflip_brier(db.to_numpy())["p_one_sided"]}
        h = L.holm({b: res["tests"][a][b]["brier"]["p_one_sided"] for b in BASE})
        for b in BASE:
            res["tests"][a][b]["brier"]["p_holm"] = h[b]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", type=int, default=None)
    a = ap.parse_args()
    runid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if a.synthetic is not None:
        rng = np.random.default_rng(a.synthetic)
        rows = []
        x = np.zeros(5)
        for ym in range(2022 * 12, 2026 * 12 + 6):
            x = 0.8 * x + rng.normal(0, 0.6, 5)
            x = x - x.mean()
            for j, p in enumerate(E.PROVS):
                rows.append({"province_code": p, "ym": ym, "d": x[j]})
        mon = pd.DataFrame(rows)
        rd = EXP / "runs" / f"SYNTH_MONTHLY_{runid}"
    else:
        rounds = None  # noqa: F841  (monthly evaluation uses only the CPI series)
        comp, c26, D = E.load_components()
        mon, _, cmp = E.load_monthly(c26, comp)
        rd = EXP / "runs" / f"MONTHLY_{runid}"
    rd.mkdir(parents=True)
    f, w = build(mon)
    P = predict(f, w)
    b = P.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode()
    (rd / "predictions_monthly.csv").write_bytes(b)
    seal = hashlib.sha256(b).hexdigest()
    res = score(pd.read_csv(rd / "predictions_monthly.csv", dtype={"province_code": str}))
    res["seal"] = seal
    res["final"] = FINAL
    (rd / "results_monthly.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(rd.name, seal)
    print(json.dumps({k: res[k] for k in ("n_origins", "first_origin", "last_origin", "HIGH", "LOW",
                                          "strongest_baseline_brier")}))


if __name__ == "__main__":
    main()
