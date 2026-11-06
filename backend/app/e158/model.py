"""
E158 thesis model, owner decision 2026-11-06: E151 required model plus PSA regional household consumption per person (E154).
income_growth joins the employment group and income_rel the poverty group. Selected after comparing five sources on the same rows (E157), so the result is slightly optimistic and retrospective.

    python -m app.e158.model eval | live
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e145 import lgu as LGU
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e150.issue import expit100
from app.e151 import OUT as O51
from app.e151 import prov as Pv
from app.e151.issue import group_of
from app.e154 import model as E154
from app.e156 import leads as LD
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
OUT = BACKEND_DIR / "data" / "e158" / "out"
EXTRA = ["income_growth", "income_rel"]
COLS = Pv.GNT_COLS + EXTRA
GROUP_EXTRA = {"income_growth": "employment", "income_rel": "poverty"}
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def task(survey, lead, H):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    if not M.released(i, Pv.ROUNDS):
        return None
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    base, _ = P.hier.predict(te, te["T"].values)
    m = Pv.Res2(COLS).fit(tr)
    mu = base + m.predict(te)
    sd, half, _ = m.scale(te["gap_q"].values)
    o = te[["key", "province", "region", "island", "survey", "T", "lead", "y_anchor", "gap_q"] + [x for x in ("y_true", "se_true", "q_true") if x in te]].copy()
    o["mu_E158"], o["E158"], o["half_E158"] = mu, norm.cdf(mu / sd), half
    return o


def evaluate():
    OUT.mkdir(parents=True, exist_ok=True)
    H = E154.income()
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in range(1, 9)) if x is not None]
    F = Pv.label_2021(pd.concat(R, ignore_index=True))
    G = pd.read_csv(O51 / "prov_oof.csv")[["key", "survey", "lead", "PERS", "mu_PERS", "half_PERS", "GNT", "mu_GNT", "half_GNT", "PSA", "LR", "LR_NEWS", "NEWS"]]
    F = F.merge(G, on=["key", "survey", "lead"])
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    rel = LD.evaluate(F, "E158", "E158")
    x = F[F["lead"] == 1].reset_index(drop=True)
    rng = np.random.default_rng(158)
    base = {b: E7.diff_ci(x, "E158", b, "q_true", rng, n=2000) for b in ("GNT", "PERS", "PSA", "NEWS", "LR_NEWS", "LR")}
    res = {"model": "E151 + PSA regional household consumption", "reliability": rel, "lead1_brier_vs": {k: {"diff": round(v["diff"], 4), "ci95": [round(a, 4) for a in v["ci95"]]} for k, v in base.items()}}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    for r in rel["leads"]:
        print(r["lead"], r["rows"], r["accuracy"], r["precision"], r["high_recall"], r["low_recall"], r["f1"], r["auc"], r["brier_soft"], r["brier_minus_persistence_ci95"], r["calibration_slope_ci95"], {k: int(v) for k, v in r["criteria"].items()}, r["confusion"])
    print("max reliable", rel["maximum_reliable_lead"], {k: (v["diff"], v["ci95"]) for k, v in res["lead1_brier_vs"].items()})


def live():
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    ISSUE = qindex("2026-Q4")
    H = E154.income()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, ISSUE, Pv.ROUNDS, "F")
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    m = Pv.Res2(COLS).fit(tr)
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)]
    rows = []
    for h in (1, 2, 3, 4):
        te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, five.assign(T=ISSUE + h, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [h], "F")), H).reset_index(drop=True)
        base, _ = P.hier.predict(te, te["T"].values)
        mu = base + m.predict(te)
        sd, half, _ = m.scale(te["gap_q"].values)
        for k in range(len(te)):
            rows.append({"province": te["province"].iloc[k], "issue": "2026-10-01", "target_quarter": qlabel(ISSUE + h), "lead": h, "latest_survey": round(float(expit100(te["y_anchor"].iloc[k])), 1), "anchor": round(float(expit100(base[k])), 1), "score": round(float(expit100(mu[k])), 1), "low90": round(float(expit100(mu[k] - half[k])), 1), "high90": round(float(expit100(mu[k] + half[k])), 1), "p_high": round(float(norm.cdf(mu[k] / sd[k])), 3), "class": "HIGH" if mu[k] >= 0 else "LOW"})
    Lv = pd.DataFrame(rows)
    C = np.abs(m.m_.booster_.predict(tr[m.use_], pred_contrib=True)[:, :-1]).mean(axis=0)
    gs = {}
    for n, v in zip(m.use_, C):
        g = GROUP_EXTRA.get(n) or group_of(n)
        gs[g] = gs.get(g, 0.0) + float(v)
    tot = sum(gs.values()) or 1.0
    q1 = Lv[Lv["lead"] == 1].set_index("province")
    lg = LGU.rank(dict(zip(q1.index, q1["p_high"])), qlabel(ISSUE + 1))
    lg.to_csv(OUT / "lgu_priority_2027-Q1.csv", index=False, lineterminator="\n")
    out = {"model": "E151 + PSA regional household consumption", "forecasts": rows, "shap_share": {k: round(v / tot, 4) for k, v in sorted(gs.items(), key=lambda t: -t[1])}, "income_shap": {n: round(float(v), 5) for n, v in zip(m.use_, C) if n in EXTRA}, "train_rows": int(len(tr))}
    (OUT / "live.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    s = OUT / "sealed_2027-Q1.json"
    if not s.exists():
        s.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **out}, indent=1, default=float), newline="\n")
    print("seal", hashlib.sha256(s.read_bytes()).hexdigest())
    print(Lv[Lv["lead"] == 1].drop(columns=["issue", "lead"]).to_string(index=False))
    print(out["shap_share"], out["income_shap"])
    print(lg.head(8)[["lgu_name", "province_name", "priority_score"]].round(4).to_string(index=False))


if __name__ == "__main__":
    {"eval": evaluate, "live": live}[sys.argv[1]]()
