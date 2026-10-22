"""E97 Q5 (PROTOCOL.md): Objective 4 on the T43 proxy label, every arm on the same E96 origins (K = 1, 2), plus LR-ALL
(the E96 framework with its LightGBM price part replaced by an L2 logistic regression). Run from backend/."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import common as C

sys.path.insert(0, str(C.EXP / "E96_Target_Formulation" / "runner"))
import run_e96 as R96  # noqa: E402

E96_RUN = C.EXP / "E96_Target_Formulation" / "runs" / "20261022T073838Z"
ARMS = {"B-PERSIST": "Naive persistence", "B-MAJ": "Majority class", "B-CLIM": "Climatology (training base rate)",
        "B-PSA": "PSA-only (logistic regression on price drivers)", "B-NLP": "News-only (logistic regression on N3)",
        "LR-ALL": "Regularized logistic regression, all framework features (E97)",
        "M-U96-POV": "Selected LightGBM framework (E94 + poverty; E96 selection)",
        "M-U96-DROP-market": "ablation: without market/prices", "M-U96-DROP-climate": "ablation: without climate",
        "M-U96-DROP-employment_remittances_ofw": "ablation: without employment/remittances",
        "M-U96-DROP-news": "ablation: without news", "M-U96-DROP-poverty_vulnerability": "ablation: without poverty"}
SIMPLE = ("B-PERSIST", "B-MAJ", "B-CLIM")


def lr_price(tr, te, cols):
    from sklearn.linear_model import LogisticRegression
    ok = tr["q"].nunique() >= 6 and tr["y_price"].sum() >= 5 and (1 - tr["y_price"]).sum() >= 5
    if not ok:
        return np.full(len(te), R96.G.freq(tr["y_price"]) if len(tr) else 0.5)
    A, B = tr[cols].astype(float), te[cols].astype(float)
    med = A.median()
    A, B = A.fillna(med).fillna(0.0), B.fillna(med).fillna(0.0)
    mu, sd = A.mean(), A.std(ddof=0).replace(0, 1.0)
    m = LogisticRegression(C=0.5, max_iter=5000).fit((A - mu) / sd, tr["y_price"].astype(int))
    return m.predict_proba((B - mu) / sd)[:, 1]


def score(P, arm):
    """E83 rule 6.1: an unissued row counts as wrong."""
    p = P[arm]
    iss = p.notna()
    pp = np.where(iss, p.clip(0, 1), 1 - P["y"])
    m = C.metrics(P["y"], pp)
    m["issued"] = int(iss.sum())
    if iss.any() and not iss.all():
        m["issued_rows_only"] = C.metrics(P.loc[iss, "y"], p[iss].clip(0, 1))
    return m


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = C.E97 / "runs" / f"{stamp}_objective4"
    o.mkdir(parents=True, exist_ok=True)
    d, _ = R96.E.data()
    T = R96.add_features(R96.A.add_news_x(R96.B.tables()))
    pc, _ = R96.cols("base", None, "n3")
    res = {"stamp": stamp, "protocol_sha256": (C.E97 / "PROTOCOL.sha256").read_text().split()[0],
           "label": "T43 proxy (regional SWS hunger > 11.3% AND provincial food-price pressure); not household food insecurity",
           "evidence_status": "development evidence (13 target quarters examined in E83-E96)", "per_k": {}}
    for k in (1, 2):
        P = pd.read_csv(E96_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
        P["LR-ALL"] = np.nan
        for t in sorted(P["t"].unique()):
            m = P["t"] == t
            ptr = R96.B.price_training(T, d, int(t))
            te = T[k][T[k]["t"] == t].set_index("province_code").loc[P.loc[m, "province_code"]].reset_index().assign(k=k)
            P.loc[m, "LR-ALL"] = P.loc[m, "M-U96-POV__ph"].to_numpy() * lr_price(ptr, te, pc)
        P.to_csv(o / f"predictions_k{k}.csv", index=False)
        g = P["target_q"].to_numpy()
        arms = {a: {"label": ARMS[a], **score(P, a)} for a in ARMS}
        best = min(SIMPLE, key=lambda a: arms[a]["brier"])
        for a in ARMS:
            pa = np.where(P[a].notna(), P[a].clip(0, 1), 1 - P["y"])
            pb = np.where(P[best].notna(), P[best].clip(0, 1), 1 - P["y"])
            dq = (pa - P["y"]) ** 2 - (pb - P["y"]) ** 2
            corr = ((pa >= 0.5).astype(int) == P["y"]).astype(float)
            per_q = pd.Series(dq).groupby(g).mean()
            arms[a]["accuracy_quarter_bootstrap95"] = C.boot_ci(g, lambda i, c=corr: float(c[i].mean()))
            arms[a]["vs_strongest_simple"] = {"baseline": best, "mean_brier_diff": float(dq.mean()),
                                              "ci95_quarter_bootstrap": C.boot_ci(g, lambda i, x=dq.to_numpy(): float(x[i].mean())),
                                              "quarters_better": int((per_q < -1e-12).sum()), "quarters_worse": int((per_q > 1e-12).sum()),
                                              "sign_p": C.sign_test(per_q)}
            arms[a]["per_quarter_accuracy"] = pd.Series(corr).groupby(g).mean().round(3).to_dict()
        for a in ("B-PSA", "B-NLP"):
            iss = P[a].notna()
            arms[a]["same_rows_comparison"] = {b: C.metrics(P.loc[iss, "y"], P.loc[iss, b].clip(0, 1))
                                               for b in (a, "M-U96-POV", "LR-ALL", "B-CLIM")}
        res["per_k"][k] = {"rows": len(P), "target_quarters": int(P["target_q"].nunique()),
                           "first_target": P["target_q"].min(), "last_target": P["target_q"].max(),
                           "positives": int(P["y"].sum()), "strongest_simple_baseline": best, "arms": arms}
        print(f"K={k} rows={len(P)} quarters={P['target_q'].nunique()} HIGH={int(P['y'].sum())} strongest simple={best}")
        for a, m in arms.items():
            v = m["vs_strongest_simple"]
            print(f"  {a:40s} acc={m['accuracy']:.3f} {np.round(m['accuracy_quarter_bootstrap95'], 3)} bal={m['balanced_accuracy'] or 0:.3f} "
                  f"P={m['precision_HIGH'] or 0:.2f} R={m['recall_HIGH'] or 0:.2f} F1={m['f1_HIGH']:.2f} auc={m['auc_roc']} brier={m['brier']:.3f} "
                  f"dB={v['mean_brier_diff']:+.3f} {np.round(v['ci95_quarter_bootstrap'], 3)} w/l={v['quarters_better']}/{v['quarters_worse']} "
                  f"p={v['sign_p']:.3f} iss={m['issued']} {m['confusion']}")
    (o / "objective4_t43.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(o)


if __name__ == "__main__":
    main()
