"""Y10 development (EXPERIMENT_PLAN_PHASE2_ADDENDUM_B.md): world commodity prices (Pink Sheet) as leading indicators of
the Region IV-A price condition at Lead 2. Same target, rows, gate and comparators as Y8 (imported from it).
Writes data_acquired/pinksheet_monthly.csv (snapshot), out/y10_dev.json, out/y10_dev_rows.csv.

    python -B run_dev.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import warnings
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import log_loss  # noqa: E402

import p2lib as P  # noqa: E402

warnings.filterwarnings("ignore")
R = P.R
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SRC = HERE / "data_acquired" / "CMO-Historical-Data-Monthly.xlsx"
SRC_SHA = "bd89b83eeceadaecb803018c104f76b316d2df3fae28ef7afde48021100c7e11"
SERIES = {"Rice, Thai 5% ": "rice", "Crude oil, average": "crude", "Urea ": "urea", "Maize": "maize",
          "Wheat, US HRW": "wheat", "Palm oil": "palm"}
_s = importlib.util.spec_from_file_location("y8", P.RES / "y8_price_condition" / "run_dev.py")
Y8 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(Y8)


def plan_ok():
    want = (P.RES / "common" / "PLAN2B_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((P.RES / "EXPERIMENT_PLAN_PHASE2_ADDENDUM_B.md").read_bytes()).hexdigest() == want
    assert hashlib.sha256(SRC.read_bytes()).hexdigest() == SRC_SHA, "Pink Sheet file changed"


def world() -> pd.DataFrame:
    d = pd.read_excel(SRC, "Monthly Prices", header=4)
    d = d.rename(columns={d.columns[0]: "month"})
    d = d[d["month"].astype(str).str.match(r"^\d{4}M\d{2}$")]
    d["ym"] = d["month"].str[:4].astype(int) * 12 + d["month"].str[5:].astype(int) - 1
    w = d[["month", "ym"] + list(SERIES)].rename(columns=SERIES)
    for c in SERIES.values():
        w[c] = pd.to_numeric(w[c], errors="coerce")
    w.to_csv(HERE / "data_acquired" / "pinksheet_monthly.csv", index=False, lineterminator="\n")
    return w.set_index("ym")


W = None


def wfeats(t: int) -> dict:
    m = R.m0(t)
    out = {}
    for c in SERIES.values():
        for k in (6, 12):
            ok = m in W.index and m - k in W.index and W.loc[m, c] > 0 and W.loc[m - k, c] > 0
            out[f"{c}_d{k}"] = float(np.log(W.loc[m, c] / W.loc[m - k, c])) if ok else np.nan
    return out


X1 = ["xF", "xG"] + [f"{c}_d{k}" for c in ("rice", "crude", "urea") for k in (6, 12)]
X2 = X1 + [f"{c}_d{k}" for c in ("maize", "wheat", "palm") for k in (6, 12)]


def logit_fit(tr, x0, cols):
    y = tr["y"].to_numpy(int)
    if len(tr) < 20 or y.sum() < 3 or (1 - y).sum() < 3:
        return np.nan
    X, z = Y8._std(tr, x0, cols)
    a, b = Y8._split(tr)
    best, bc = np.inf, Y8.C_GRID[0]
    if len(set(y[a])) == 2:
        for c in Y8.C_GRID:
            m = LogisticRegression(C=c, max_iter=2000).fit(X[a], y[a])
            ll = log_loss(y[b], m.predict_proba(X[b])[:, 1], labels=[0, 1])
            if ll < best:
                best, bc = ll, c
    return float(LogisticRegression(C=bc, max_iter=2000).fit(X, y).predict_proba(z)[0, 1])


def main():
    global W
    plan_ok()
    W = world()
    allr = {}
    for t in range(R.qi("1995-Q1"), Y8.T_LAST + 1):
        r = Y8.row(t)
        if r is not None:
            allr[t] = {**r, **wfeats(t)}
    rows = []
    for t in range(Y8.T_FIRST, Y8.T_LAST + 1):
        if t not in allr or "y" not in allr[t]:
            continue
        tr = pd.DataFrame([r for tt, r in allr.items() if tt <= t - 3 and "y" in r])
        x0 = allr[t]
        p = Y8.fit_predict(tr, x0)
        rows.append({"t": t, "target": R.qs(t + 2), "y": x0["y"], "pers_bin": x0["pers_bin"], "PERS_PROB": p["PERS_PROB"],
                     "LOGW": logit_fit(tr, x0, X1), "LOGW2": logit_fit(tr, x0, X2), "trainRows": len(tr)})
    d = pd.DataFrame(rows).dropna(subset=["PERS_PROB", "LOGW", "LOGW2"])
    res = {"rows": len(d), "prevalence": float(d["y"].mean()), "period": f"{d['target'].min()}..{d['target'].max()}",
           "pinkSheetVintage": "Updated on January 03, 2025", "pinkSheetSha256": SRC_SHA}
    for c in ("pers_bin", "PERS_PROB", "LOGW", "LOGW2"):
        res[c] = R.metrics(d["y"], d[c])
    for c in ("LOGW", "LOGW2"):
        res[f"{c}_vs_PERS_PROB"] = {"iid": Y8.boot(d, c, "PERS_PROB"), "block4": Y8.boot(d, c, "PERS_PROB", 4)}
        res[f"{c}_gate"] = {"G1": res[f"{c}_vs_PERS_PROB"]["iid"]["diff"] < 0 and res[f"{c}_vs_PERS_PROB"]["iid"]["p_one_sided"] < .10,
                            "G2": (res[c]["balanced"] or 0) >= (res["PERS_PROB"]["balanced"] or 0)}
    res["passedGate"] = [c for c in ("LOGW", "LOGW2") if all(res[f"{c}_gate"].values())]
    # descriptive: univariate leading correlation of each world feature with the target-quarter food YoY minus F3
    full = pd.DataFrame([r for r in allr.values() if "y" in r and Y8.T_FIRST <= r["t"] <= Y8.T_LAST])
    full["dF_target"] = full["F_tgt"] - full["F3"]
    res["leadingCorr_with_change_in_food_yoy"] = {c: round(float(full[c].corr(full["dF_target"])), 3)
                                                  for c in X2[2:]}
    OUT.mkdir(exist_ok=True)
    (OUT / "y10_dev.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    d.to_csv(OUT / "y10_dev_rows.csv", index=False, lineterminator="\n", float_format="%.5f")
    print({k: res[k] for k in ("rows", "prevalence", "period")})
    for c in ("pers_bin", "PERS_PROB", "LOGW", "LOGW2"):
        m = res[c]
        print(f"{c:10s} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} "
              f"spec {m['specificity'] or 0:.2f} AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f}")
    for c in ("LOGW", "LOGW2"):
        print(c, res[f"{c}_vs_PERS_PROB"], res[f"{c}_gate"])
    print("leading corr:", res["leadingCorr_with_change_in_food_yoy"])
    print("passed gate:", res["passedGate"])


if __name__ == "__main__":
    main()
