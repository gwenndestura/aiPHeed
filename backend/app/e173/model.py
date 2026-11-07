"""
E173 (docs/e173/PROTOCOL.md, blob 1c4007cf): E168 with the empty `unemp_region` input filled from PSA's official regional
unemployment rates (Philippine Statistical Yearbook Table 11.1, 2014-2023). Everything else is E168: the rows are built
exactly as app.e168.lgbm_only.task builds them and passed to the frozen app.e168.lgbm_only.run_proc.

    python -m app.e173.model run    -> data/e173/out/rows.csv
    python -m app.e173.model eval   -> data/e173/out/results.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
RAW = D / "e173" / "raw" / "psa_yearbook_t11_1_unemployment_region.csv"
OUT = D / "e173" / "out"
NAME = {"ARMM": "BARMM", "Bicol": "Bicol Region", "Davao": "Davao Region", "Ilocos": "Ilocos Region"}


def region_rates() -> dict[str, dict[int, float]]:
    d = pd.read_csv(RAW)
    d["Region"] = d["Region"].str.replace(".", "", regex=False).str.strip()
    return {r["Region"]: {int(y): float(r[y]) for y in d.columns if y.isdigit() and pd.notna(r[y])} for _, r in d.iterrows()}


def usable_year(i: int) -> int:
    """Annual rate for year y is usable from the second quarter of y + 1 (app/e148/panel.py rule)."""
    return i // 4 - 1 if i % 4 >= 1 else i // 4 - 2


def fill(d: pd.DataFrame, R: dict) -> pd.DataFrame:
    d = d.copy()
    vals, years = [], []
    for reg, i in zip(d["region"], d["i"]):
        y = usable_year(int(i))
        v = R.get(NAME.get(reg, reg), {}).get(y, np.nan)
        vals.append(v)
        years.append(y if v == v else np.nan)
    d["unemp_region"], d["_unemp_region_year"] = vals, years
    return d


def task(survey: str, lead: int, H, L, S_P) -> pd.DataFrame | None:
    from app.e147 import features as Fe
    from app.e148 import model as M8
    from app.e150 import evaluate as Ev
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e164 import auto as A4
    from app.e166 import nested_source as N
    from app.e168 import lgbm_only as E
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    if not M.released(i, Pv.ROUNDS):
        return None
    P_ = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P_.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), L, H, S_P)
    tr = N.add_sources(Pv.add_inputs(S, P_.tr), L, H, S_P)
    R = region_rates()
    tr, te = fill(tr, R), fill(te, R)
    AN = A4.anchors(S, P_, tr, te)
    P, chosen, tag, _, inner, nfeat = E.run_proc(tr, te, AN)
    mu, p, half = P[chosen]
    o = te[["key", "survey", "lead", "region", "i"]].copy()
    o["mu"], o["p"], o["half"], o["cfg"], o["n_features"] = mu, p, half, tag, nfeat
    o["unemp_region"], o["unemp_region_year"] = te["unemp_region"].values, te["_unemp_region_year"].values
    o["train_unemp_region_filled"] = float(tr["unemp_region"].notna().mean())
    o["train_max_year_minus_usable"] = float(np.nanmax(tr["_unemp_region_year"] - tr["i"].map(usable_year))) if tr["unemp_region"].notna().any() else np.nan
    return o


def run():
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "rows.csv").exists():
        raise SystemExit("already run")
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    jobs = [(s, l) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for l in (1, 2, 3)]
    R = Parallel(n_jobs=9)(delayed(task)(s, l, H, L, S_P) for s, l in jobs)
    pd.concat([x for x in R if x is not None], ignore_index=True).to_csv(OUT / "rows.csv", index=False, lineterminator="\n")


def evaluate():
    from app.e147 import evaluate as E7
    X = pd.read_csv(OUT / "rows.csv")
    A = pd.concat([pd.read_csv(D / "e168" / "out" / "all_rows.csv"), pd.read_csv(D / "e168" / "out" / "all_rows_l3_8.csv")])
    A = A[A["mode"] == "main"][["key", "survey", "lead", "p"]].rename(columns={"p": "p168"})
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    res = {"protocol": "docs/e173/PROTOCOL.md blob 1c4007cf", "leads": {}}
    for L in (1, 2, 3):
        x = G[G["lead"] == L].merge(X[X["lead"] == L].drop(columns=["region"]), on=["key", "survey", "lead"]).merge(A[A["lead"] == L], on=["key", "survey", "lead"])
        y, q = (x["y_high"] == 1).values, x["q_true"].values
        acc = lambda c: round(float(((x[c] >= 0.5) == y).mean()), 3)
        d = (x["p"] - q) ** 2 - (x["p168"] - q) ** 2
        rng = np.random.default_rng(173)
        bs = [d.values[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
        vp = E7.diff_ci(x.rename(columns={"p": "E173"}), "E173", "PERS", "q_true", np.random.default_rng(168), n=2000)
        res["leads"][L] = {"n": len(x), "accuracy_E173": acc("p"), "accuracy_E168": acc("p168"), "accuracy_persistence": acc("PERS"),
                           "brier_E173": round(float(((x["p"] - q) ** 2).mean()), 4), "brier_E168": round(float(((x["p168"] - q) ** 2).mean()), 4),
                           "brier_E173_minus_E168": round(float(d.mean()), 4), "ci95": [round(float(v), 4) for v in np.percentile(bs, [2.5, 97.5])],
                           "beats_persistence": bool(vp["ci95"][1] < 0), "brier_minus_persistence_ci95": [round(z, 4) for z in vp["ci95"]],
                           "test_unemp_region_filled": round(float(x["unemp_region"].notna().mean()), 3),
                           "train_unemp_region_filled": round(float(x["train_unemp_region_filled"].mean()), 3),
                           "selected_configs": x.groupby("survey")["cfg"].first().to_dict()}
    leak = bool((X["unemp_region_year"].dropna() <= X["i"].map(lambda i: i // 4 - 1 if i % 4 >= 1 else i // 4 - 2)[X["unemp_region_year"].notna()]).all()
                and (X["train_max_year_minus_usable"].fillna(0) <= 0).all())
    l1 = res["leads"][1]
    c1 = l1["ci95"][1] < 0
    c2 = all(res["leads"][L]["accuracy_E173"] >= 0.75 and res["leads"][L]["beats_persistence"] for L in (1, 2, 3))
    res["checks"] = {"1_better_than_E168_lead1": c1, "2_project_rule_leads_1_3": c2, "3_no_unpublished_year_used": leak}
    res["decision"] = ("E173 REPLACES E168" if (c1 and c2 and leak) else
                       "E168 STAYS: regional unemployment " + ("worsens the forecast" if l1["ci95"][0] > 0 else "adds no measurable information"))
    (OUT / "results.json").write_text(json.dumps(res, indent=1), newline="\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"run": run, "eval": evaluate}[sys.argv[1]]()
