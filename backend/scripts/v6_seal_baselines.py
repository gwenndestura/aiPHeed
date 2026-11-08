"""
v6 Stage 5 prerequisite: sealed forecasts for the research baselines that had none at the P-DASH cutoff, so the
"beats every model" test can be complete. Issues 2026-07-01 and 2026-10-01 (information = rounds and covariates
published before 00:00 PHT of the issue); only targets with no published SWS round.

  RIDGE-ALL  E131 runner code (features(), fit_predict('ridge'), training = earlier P-DASH issues of the same lead
             whose target was published before the issue), reproduced first on historical issues against E136.
  HFM-X      E133 runner code (predict() with the rice/b30/oni drivers), reproduced first against E136.

Write-once. Run with the research runners imported read-only.

    python -I backend/scripts/v6_seal_baselines.py
"""
from __future__ import annotations

import hashlib
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[2]
EXP = REPO / "aipheed-backend-aligned" / "experiments"
sys.path.insert(0, str(EXP / "E133_Forecasting_Breakthrough" / "runner"))
import e133_run as R  # noqa: E402

X, L = R.X, R.L              # X = E131 runner module, L = E130 lib
SEALED = REPO / "docs" / "aipheed" / "v6" / "sealed"
OUT = SEALED / "V6_BASELINE_SEAL.csv"
ISSUES = (date(2026, 7, 1), date(2026, 10, 1))
E136 = EXP / "E136_Methodology_Review" / "out" / "e136_predictions.csv"


def ridge_at(rr, qt, cpi, reg, pov, issue: date, lead: int, sched) -> dict:
    final = qt.set_index(["area", "quarter"])
    D = L.quarter_of(issue)
    target = L.qi(D) - 1 + lead
    ev = X.features(issue, rr, cpi, reg, pov, target)
    tr = []
    for D2, iss2 in sched:
        if iss2 >= issue:
            continue
        T2 = L.qs(L.qi(D2) - 1 + lead)
        F = X.features(iss2, rr, cpi, reg, pov, L.qi(T2))
        if F.empty:
            continue
        pub = [final.loc[(a, T2), "published"] if (a, T2) in final.index else None for a in F.area]
        F["y_true"] = [final.loc[(a, T2), "y"] if (a, T2) in final.index else np.nan for a in F.area]
        F = F[[isinstance(p, date) and p < issue for p in pub]]
        tr.append(F.assign(delta=F.y_true - F.y_latest, target=T2))
    tr = pd.concat(tr, ignore_index=True) if tr else pd.DataFrame()
    if len(tr) < 20 or tr["target"].nunique() < 8:          # E131: >= 20 training rows and >= 8 training quarters
        return {}
    p, _, _ = X.fit_predict("ridge", X.feat_cols(None), tr, ev)
    return dict(zip(ev.area, ev.y_latest.to_numpy() + p))


def main():
    if OUT.exists():
        sys.exit(f"{OUT} exists: write-once")
    rr = X.rounds()
    qt = X.quarter_table(rr)
    cpi, reg, pov = X.cpi_quarterly(), X.regional_covariates(), X.poverty_area()
    # RIDGE-ALL as used in E132-E136 and in the v2/v4 baseline tables is E132's version: E132 main() swaps in its own
    # feature builder (area income, rice affordability) and column list. Reproduce that setup exactly.
    S = R.S
    S.INCOME, S.RICE = S.income_area(), S.rice_affordability()
    X.features = S.features132
    S.GROUPS132.update({k: list(v) for k, v in X.GROUPS.items()})
    S.GROUPS132["A"] = S.GROUPS132["A"] + ["riceaff_chg4"]
    S.GROUPS132["E"] = S.GROUPS132["E"] + S.INC
    X.feat_cols = S.feat_cols132
    sched = X.schedule(rr, "P-DASH")
    drv = {"rice": R.Drivers("rice"), "b30": R.Drivers("b30"), "oni": R.Drivers("rice", "oni_quarter_mean")}
    # reproduction check on 3 historical P-DASH issues against E136 (same research code, same rows)
    P = pd.read_csv(E136)
    P = P[(P.policy == "P-DASH") & (P.lead == 2) & P["f_RIDGE-ALL"].notna()]
    chk = []
    for issue in sorted(P.issue.unique())[-3:]:
        d = date.fromisoformat(issue)
        rg = ridge_at(rr, qt, cpi, reg, pov, d, 2, sched)
        res = R.predict(X.asof(rr, d), d, L.qi(L.quarter_of(d)) + 1, drv)
        for r in P[P.issue == issue].itertuples():
            chk.append({"issue": issue, "area": r.area})
            chk[-1].update({"ridge_e136": float(P.loc[r.Index, "f_RIDGE-ALL"]), "ridge_v6": rg.get(r.area),
                            "hfmx_e136": float(P.loc[r.Index, "f_HFM-X"]), "hfmx_v6": float(res["HFM-X"][0][X.AREAS.index(r.area)])})
    c = pd.DataFrame(chk)
    print(c.to_string())
    d_r, d_h = (c.ridge_e136 - c.ridge_v6).abs().max(), (c.hfmx_e136 - c.hfmx_v6).abs().max()
    print("reproduction max abs diff: RIDGE-ALL", d_r, "HFM-X", d_h)
    if not (d_r < 1e-6 and d_h < 1e-6):
        sys.exit("baselines not reproduced: refusing to seal")
    published = set(qt.quarter)
    rows = []
    for issue in ISSUES:
        qa = X.asof(rr, issue)
        for k in L.LEADS:
            target = L.qi(L.quarter_of(issue)) - 1 + k
            if L.qs(target) in published:
                continue
            rg = ridge_at(rr, qt, cpi, reg, pov, issue, k, sched)
            res = R.predict(qa, issue, target, drv)
            for j, a in enumerate(X.AREAS):
                rows.append({"issue": issue.isoformat(), "lead": k, "target": L.qs(target), "area": a, "model": "RIDGE-ALL",
                             "f": round(float(rg[a]), 6) if a in rg else None})
                rows.append({"issue": issue.isoformat(), "lead": k, "target": L.qs(target), "area": a, "model": "HFM-X",
                             "f": round(float(res["HFM-X"][0][j]), 6)})
    S = pd.DataFrame(rows)
    SEALED.mkdir(parents=True, exist_ok=True)
    S.to_csv(OUT, index=False, lineterminator="\n")
    h = hashlib.sha256(OUT.read_bytes()).hexdigest()
    (SEALED / "V6_BASELINE_SEAL_SHA256.txt").write_text(f"{h}  V6_BASELINE_SEAL.csv\n", encoding="utf-8", newline="\n")
    c.to_csv(REPO / "docs" / "aipheed" / "v6" / "results" / "baseline_reproduction.csv", index=False)
    print(S.to_string())
    print(h)


if __name__ == "__main__":
    main()
