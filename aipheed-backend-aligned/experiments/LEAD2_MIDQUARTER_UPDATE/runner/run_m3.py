"""LEAD2_MIDQUARTER_UPDATE (PLAN.md): EXPLORATORY replay of the mid-quarter update M3 on the 65 official Lead-2 rows.
Issue date D(t) = first day of the second month of quarter t+1; CPI cutoff of every origin = newest month available at
D(t); hunger part H4 at D(t). Reuses LEAD2_POST_SWS_PRICE/runner/price_refit.py and LEAD2_POST_SWS_ISSUE/runner/score.py
read-only. Writes out/ only.

    python -B run_m3.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOTD = HERE.parent
EXP = ROOTD.parent
OUT = ROOTD / "out"
sys.path.insert(0, str(EXP / "LEAD2_POST_SWS_PRICE" / "runner"))
import price_refit as PR  # noqa: E402

SI, U, L, E, pd, np = PR.SI, PR.U, PR.L, PR.E, PR.pd, PR.np
P, R, RV = SI.P, SI.R, SI.RV


def plan_ok():
    b = (ROOTD / "PLAN.md").read_bytes()
    i = b.rfind(b"\nPLAN-SHA256:") + 1
    if hashlib.sha256(b[:i]).hexdigest() != b[i:].split(b":", 1)[1].strip().decode():
        raise SystemExit("PLAN.md changed after it was hashed")


def issue_m3(t: int) -> pd.Timestamp:
    """First day of the second month of quarter t+1."""
    n = t + 1
    return pd.Timestamp(year=n // 4, month=(n % 4) * 3 + 2, day=1)


def m0_m3(t: int) -> int:
    m = SI.cpi_newest(issue_m3(int(t)))
    if m < PR.M0_SERVED(int(t)):
        raise SystemExit("M3 cutoff before the served one")
    return m


def main():
    plan_ok()
    PR.frozen_ok()
    OUT.mkdir(exist_ok=True)
    U.setup()
    g = P.load_p0h4()
    g = g[g["lead"] == 2].copy().reset_index(drop=True)
    post = pd.read_csv(EXP / "LEAD2_POST_SWS_PRICE" / "out" / "eval_rows.csv", dtype={"province_code": str})
    g = g.merge(post[["t", "province_code", "pi_H4_post", "P0_price_post"]], on=["t", "province_code"])
    origins = sorted(int(x) for x in g["t"].unique())
    provs = sorted(g["province_code"].unique())

    # ---- price part with the M3 cutoff (training origins included), world prices pinned as served
    U.world_features = PR.world_features_at
    L.m0_of = m0_m3
    S = U.stack(PR.K)
    d0 = E.data()[0]
    audit, prices = [], []
    for t in sorted(int(x) for x in S["t"].unique()):
        D, m = issue_m3(t), m0_m3(t)
        dc = d0.cut(t)
        newest = int(max(dc.idx["ym"].max(), dc.yoy["ym"].max()))
        if not SI.cpi_newest(D) == m or newest > m or not pd.Timestamp(year=(m + 2) // 12, month=(m + 2) % 12 + 1, day=1) <= D:
            raise SystemExit(f"LEAKAGE at {L.qs(t)}: cutoff {L.ym_s(m)} newest {L.ym_s(newest)} issue {D.date()}")
        audit.append({"origin": L.qs(t), "issue": str(D.date()), "cpiCutoff": L.ym_s(m), "newestCpiInCut": L.ym_s(newest)})
    for t in origins:
        f, _ = PR.p0_origin(S, t)
        prices.append(f[f["lead"] == 2][["t", "province_code", "P0_price"]].rename(columns={"P0_price": "P0_price_m3"}))
    L.m0_of = PR.M0_SERVED                                             # restore before anything else
    g = g.merge(pd.concat(prices), on=["t", "province_code"], how="left")
    if g["P0_price_m3"].isna().any():
        raise SystemExit("M3 price missing for an official row")

    # ---- hunger part and baselines at D(t)
    X = SI.setup()
    for t in origins:
        D = issue_m3(t)
        iss = D.date().isoformat()
        h, info = SI.h4_at(X, iss, t, 2)
        if not info["newestSwsPublished"] < iss:
            raise SystemExit(f"LEAKAGE: SWS {info['newestSwsPublished']} not before {iss}")
        ps, cl = SI.persist_clim_at(X, iss, t, provs, SI.cpi_newest(D))
        k = g["t"] == t
        g.loc[k, "pi_H4_m3"], g.loc[k, "CLIM_m3"] = h, cl
        g.loc[k, "PERSIST_m3"] = g.loc[k, "province_code"].map(ps)
        next(a for a in audit if a["origin"] == L.qs(t)).update(newestSws=info["newestSwsQ"],
                                                                 swsPublished=info["newestSwsPublished"])
    g["M3"] = g["pi_H4_m3"] * g["P0_price_m3"]
    g["M0"] = g["pi_H4_post"] * g["P0_price"]
    g["M2"] = g["pi_H4_post"] * g["P0_price_post"]

    res = {"label": "EXPLORATORY (closed 2023-2026 rows; fifth Lead-2 variant scored on them)",
           "planSha256": hashlib.sha256((ROOTD / "PLAN.md").read_bytes()).hexdigest(), "leakageAudit": audit, "models": {}}
    frames = {"P0H4_served": (RV.P, "PERSIST-SI_p", "CLIM_p"), "M0": ("M0", None, None), "M2": ("M2", None, None),
              "M3_midquarter": ("M3", "PERSIST_m3", "CLIM_m3")}
    for name, (col, pcol, ccol) in frames.items():
        if name in ("M0", "M2"):
            base = post.set_index(["t", "province_code"])
            h = g.copy()
            h["PERSIST-SI_p"] = [base.loc[(t, p), "PERSIST_post"] for t, p in zip(h["t"], h["province_code"])]
            h["CLIM_p"] = [base.loc[(t, p), "CLIM_post"] for t, p in zip(h["t"], h["province_code"])]
        else:
            h = g.assign(**{"PERSIST-SI_p": g[pcol], "CLIM_p": g[ccol]})
        m = SI.metrics(h["y"], h[col])
        o = P.official_rules(h, col)
        res["models"][name] = {"cm": f"{m['TP']}/{m['FP']}/{m['FN']}/{m['TN']}", **{k: m[k] for k in (
            "accuracy", "balanced", "precision", "recall", "auc", "brier")}, "failed": o["failed"], "passesAll": o["passesAll"]}
        r = res["models"][name]
        print(f"{name:14s} CM {r['cm']} acc {r['accuracy']:.3f} bal {r['balanced']:.3f} P {r['precision'] or 0:.3f} "
              f"R {r['recall']:.3f} AUC {r['auc']:.3f} Brier {r['brier']:.4f} fails {r['failed']}", flush=True)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    g[["t", "q", "province_code", "y", "pi_H4", "pi_H4_m3", "P0_price", "P0_price_m3", "M3", "M0", "M2", RV.P,
       "PERSIST_m3", "CLIM_m3"]].to_csv(OUT / "rows.csv", index=False, lineterminator="\n", float_format="%.6f")


if __name__ == "__main__":
    main()
