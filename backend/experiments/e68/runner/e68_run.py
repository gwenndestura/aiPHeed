"""E68 model search (PROTOCOL_E68.md, md5 checked): five arms on E53-A1's own procedure, scored on E53's 65 lead-1 rows
with the thesis label, plus five-driver coverage computed with the served attribution. Writes only to
backend/experiments/e68/out (guard32 confined there)."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

E68 = Path(__file__).resolve().parents[1]
BACKEND = E68.parents[1]
ROOT = BACKEND.parent
OUT = E68 / "out"
OUT.mkdir(parents=True, exist_ok=True)
want = (ROOT / "PROTOCOL_E68.md.md5").read_text().split()[0]
assert hashlib.md5((ROOT / "PROTOCOL_E68.md").read_bytes()).hexdigest() == want, "PROTOCOL_E68.md changed"
for k in [k for k in os.environ if k.startswith("AIPHEED_")]:
    os.environ.pop(k)
os.chdir(BACKEND)
sys.dont_write_bytecode = True
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "experiments/e53/runner"))
import e53_run as E  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
L6, C, R, X = E.L6, E.C, E.R, E.X
E31 = X.live_engine()          # the target's served e31_engine.py, loaded by file path (as E53's own runner does)
L6.guard32.EXP = E68
PROVS = E.PROVS
COND = E.COND
NEWS_IN = ["news_n", "news_reg", "news_direct_share", "fssi_v2", "fssi_missing"]
GRIDS = list(L6.COMPLEXITY)                                    # G1, G4, G3, G2 (simplicity order)
FAMS = ["COMPACT_T5_C", "COMB_T5_C"]

# ---------------------------------------------------------------- arms (only what the protocol lists)
E.register()


def add_pool(name, fam_feats: dict, grid_fn):
    pool = []
    for fam, feats in fam_feats.items():
        fs = f"{fam}__{name}"
        L6.FEATURE_SETS[fs] = feats
        for g in GRIDS:
            gid = f"{g}__{name}__{fam}"
            L6.GRID[gid] = grid_fn(dict(L6.GRID[g]), feats)
            pool.append((fs, gid))
    L6.POOLS[name] = (pool, (f"COMB_T5_C__{name}", f"G1__{name}__COMB_T5_C"))


base_feats = {f: list(L6.FEATURE_SETS[f]) for f in FAMS}
trim_feats = {f: [x for x in v if x not in NEWS_IN] for f, v in base_feats.items()}
mono = lambda feats: [1 if x in COND else 0 for x in feats]
add_pool("E68-FS05", base_feats, lambda p, f: p | {"colsample_bytree": 0.5})
add_pool("E68-TRIM", trim_feats, lambda p, f: p)
add_pool("E68-MONO", base_feats, lambda p, f: p | {"monotone_constraints": mono(f)})
add_pool("E68-SLOW", base_feats, lambda p, f: p | {"n_estimators": p["n_estimators"] * 4,
                                                    "learning_rate": p["learning_rate"] / 4})
add_pool("E68-COMBO", trim_feats, lambda p, f: p | {"colsample_bytree": 0.5, "monotone_constraints": mono(f)})
ARMS = ["E53-A1", "E68-FS05", "E68-TRIM", "E68-MONO", "E68-SLOW", "E68-COMBO"]

d = E.Data(E.build_cond())
Pr, info = L6.walk_forward(d)
dates = [C.qk(x) - 1 for x in info["dates"]]
T = L6.OPERATIONAL_T
alld = dates + [T]
labels = {t: {c: int(d.label(c, t + 1, t)) for c in PROVS} for t in dates}
labels_all = {**labels, T: {c: 0 for c in PROVS}}
base_rate = {t: float((d.train(t)["y"].sum() + 1) / (len(d.train(t)) + 2)) for t in alld}
prior_of = {t: L6.eligible_prior_dates(d, t, dates) for t in alld}

# ---------------------------------------------------------------- served attribution (same rules as five_trigger_drivers)
GROUPS = {g: fs + E31.COND_GROUP_FEATURES[g] for g, fs in E31.TRIGGER_GROUP_FEATURES.items()}
sig = lambda x: 1.0 / (1.0 + math.exp(-x))


def ishares(vals):
    tot = sum(vals)
    if tot <= 0:
        return [0] * len(vals)
    ex = [v / tot * 100 for v in vals]
    fl = [int(x) for x in ex]
    for i in sorted(range(len(ex)), key=lambda i: ex[i] - fl[i], reverse=True)[:100 - sum(fl)]:
        fl[i] += 1
    return fl


def group_drivers(shap: dict, code: str, ev_q: str):
    grp = {g: sum(shap.get(f, 0.0) for f in fs) for g, fs in GROUPS.items()}
    mag = {g: abs(v) for g, v in grp.items()}
    for level, nf in E31.NEWS_FEATURES.items():
        w, _ = E31.news_topic_shares(code if level == "province" else None, ev_q)
        a = sum(abs(shap.get(f, 0.0)) for f in nf)
        s = sum(shap.get(f, 0.0) for f in nf)
        for g in GROUPS:
            mag[g] += w[g] * a
            grp[g] += w[g] * s
    return {g: round(math.copysign(mag[g], grp[g]), 4) for g in GROUPS}


def coverage(models_by_t):
    """per target quarter: province and region integer shares of the five groups."""
    out = {}
    for t, (m, feats, te) in models_by_t.items():
        q = C.qs(t + 1)
        if m is None:
            out[q] = None
            continue
        cc = L6.shap_contributions(m, te[feats])
        prov, region_abs = {}, {g: 0.0 for g in GROUPS}
        for i, code in enumerate(te["province_code"]):
            row = cc.iloc[i]
            shap = {f: round(float(row[f]), 4) for f in feats}            # the record stores 4 dp
            base = float(row["expected_value"])
            drv = group_drivers(shap, code, C.qs(t))
            pct = dict(zip(GROUPS, ishares([abs(drv[g]) for g in GROUPS])))
            prov[code] = pct
            z = base + sum(shap.values())
            sc = sig(z) * (1 - sig(z)) if abs(z - base) < 1e-9 else (sig(z) - sig(base)) / (z - base)
            for g in GROUPS:
                region_abs[g] += abs(drv[g]) * sc
        out[q] = {"provinces": prov, "region": dict(zip(GROUPS, ishares([region_abs[g] for g in GROUPS])))}
    return out


# ---------------------------------------------------------------- fit every arm at every origin
results, preds = {}, []
for arm in ARMS:
    raw, models, chosen, additivity = {}, {}, {}, 0.0
    for t in alld:
        if t == T:
            fs, g = L6.operational_choice(d, Pr, arm)[0]
        else:
            fs, g = info["selections"][arm][C.qs(t + 1)]["chosen"].split("x")
        feats = L6.FEATURE_SETS[fs]
        tr, te = d.train(t), d.test(t).reset_index(drop=True)
        ptr, pte, m = X.lgbm_arrays(tr, te, feats, g)
        raw[t] = dict(zip(te["province_code"], pte))
        models[t] = (m, feats, te)
        chosen[C.qs(t + 1)] = L6.cfg_name(fs, g)
        if m is not None:                                              # additivity on unrounded TreeSHAP
            cc = L6.shap_contributions(m, te[feats])
            z = m.booster_.predict(te[feats].astype(float), raw_score=True)
            additivity = max(additivity, float(np.max(np.abs(cc.sum(axis=1).to_numpy() - z))))
    cal, _fb, pa = R.calibrated(raw, labels_all, base_rate, prior_of, "shrink")
    for t in dates:
        for c in PROVS:
            preds.append({"arm": arm, "target_quarter": C.qs(t + 1), "province_code": c, "p": cal[t][c],
                          "p_raw": raw[t][c], "y": labels[t][c], "config": chosen[C.qs(t + 1)]})
    cov = coverage(models)
    served = {q: v for q, v in cov.items() if q != "2023-Q1"}
    worst = []
    for q, v in served.items():
        if v is None:
            worst.append((q, "no model (constant)", 0))
            continue
        for scope, pct in list(v["provinces"].items()) + [("REGION", v["region"])]:
            for g, p in pct.items():
                if p < 1:
                    worst.append((q, scope, g))
    results[arm] = {"configs": chosen, "additivity_max": additivity, "coverage": cov,
                    "coverage_failures": worst, "n_cells_below_1pct": len(worst),
                    "calibrated_2026Q4": {c: cal[T][c] for c in PROVS}}
    print(f"{arm}: coverage failures {len(worst)} | additivity {additivity:.2e}", flush=True)

pd.DataFrame(preds).to_csv(OUT / "e68_predictions.csv", index=False, float_format="%.10g")
(OUT / "e68_fits.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
print("written", OUT)
