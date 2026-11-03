"""
E138 section 9: CALABARZON differentiation and the sealed prediction (procedure fixed in PROTOCOL.md before the run).

    python -m app.e138.calabarzon acquire   PSA FY Table 3 (subsistence incidence among FAMILIES, 2018-2023), the
                                            definition used in training (E137's external check used population)
    python -m app.e138.calabarzon run       -> data/e138/out/calabarzon.json and sealed_prediction.json

Latest public values as of the seal date (release rule: poverty round R public from 1 January of R+2, census C from
1 January of C+2): poverty statistics 2023, census 2024. Market and climate features are built only if the selected
model uses them (it is recorded in results.json).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm

from app.e137 import RAW as RAW137
from app.e137 import external as X137
from app.e137 import features as F
from app.e137 import outcomes as O
from app.e137.acquire import PX, _get
from app.e138 import OUT, RAW
from app.e138 import models as M
from app.e138 import where as WH

CAL = ["batangas", "cavite", "laguna", "quezon", "rizal"]
SEAL_DATE = pd.Timestamp("2026-11-04")
N_BOOT = 500


def acquire() -> None:
    (RAW / "psa").mkdir(parents=True, exist_ok=True)
    path = "DB/1F/FY/0051F3DF030.px"
    meta = json.loads(_get(PX + path, timeout=120))
    q = [{"code": v["code"], "selection": {"filter": "item", "values": v["values"]} if "values" in v
          else {"filter": "all", "values": ["*"]}} for v in meta["variables"]]
    body = _get(PX + path, json.dumps({"query": q, "response": {"format": "csv"}}).encode())
    f = RAW / "psa" / "subsistence_families_2018_2023.csv"
    f.write_bytes(body)
    (RAW / "MANIFEST.csv").write_text("file,source_url,retrieved,sha256\n"
                                      f"psa/{f.name},{PX + path},{datetime.now().date()},{hashlib.sha256(body).hexdigest()}\n")


def _series(fname: str, pat: str, year: str, base=RAW137 / "y2023" / "psa") -> pd.Series:
    d = pd.read_csv(base / fname, dtype=str, encoding="latin-1")
    d["k"] = X137._clean_geo(d.iloc[:, 0])
    col = next(c for c in d.columns if re.search(pat, c) and c.strip().endswith(year))
    s = pd.Series(pd.to_numeric(d[col], errors="coerce").values, index=d["k"])
    return s[~s.index.duplicated()]


def latest_features(keys: list[str], cols: list[str]) -> pd.DataFrame:
    need_other = [c for c in cols if c not in M.P + M.D + M.A]
    if need_other:
        raise NotImplementedError(f"latest market/climate features not built: {need_other}")
    pov = _series("poverty_pop_2018_2023.csv", r"Poverty Incidence", "2023")
    sub = _series("subsistence_families_2018_2023.csv", r"Subsistence Incidence", "2023", base=RAW / "psa")
    gap = _series("poverty_gap_2018_2023.csv", r"Estimate", "2023")
    cen = pd.read_csv(RAW137 / "psa" / "population_2010_2024.csv", dtype=str, encoding="latin-1")
    cen = cen[cen.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
    cen["k"] = cen.iloc[:, 0].str.replace("*", "", regex=False).map(F.nospace)
    pop24 = pd.to_numeric(cen.set_index("k").filter(like="2024)").iloc[:, 0], errors="coerce")
    pop24 = pop24[~pop24.index.duplicated()]
    area = F._census()["area"]
    rows = []
    for k in keys:
        r = {c: np.nan for c in F.FEATURES}
        r["p_poverty"] = float(F._logit(pov[k])) if k in pov.index else np.nan
        r["p_subsistence"] = float(F._logit(sub[k])) if k in sub.index else np.nan
        r["p_poverty_gap"] = float(gap[k]) if k in gap.index else np.nan
        if k in pop24.index and k in area.index:
            r["p_density"] = float(np.log(pop24[k] / area[k]))
        rows.append({"k": k, **r})
    return pd.DataFrame(rows)


def measured() -> dict:
    d = O.load()
    c = d[d["key"].isin(CAL) & d["has_value"]]
    out = {"rows": c[["province", "survey", "p", "se_p", "y", "se_y", "status"]].round(3).to_dict(orient="records")}
    r15 = c[c["survey"] == "FNRI2015"].set_index("province")
    w = 1 / r15["se_p"] ** 2
    pbar = float((w * r15["p"]).sum() / w.sum())
    Q = float((w * (r15["p"] - pbar) ** 2).sum())
    out["fnri2015_cochran_q"] = {"Q": Q, "df": len(r15) - 1, "p": float(chi2.sf(Q, len(r15) - 1))}
    out["fnri2015_pairwise"] = [{"a": a, "b": b, "diff_pp": float(r15.at[a, "p"] - r15.at[b, "p"]),
                                 "z": float((r15.at[a, "p"] - r15.at[b, "p"]) / np.hypot(r15.at[a, "se_p"], r15.at[b, "se_p"])),
                                 "p": float(2 * norm.sf(abs((r15.at[a, "p"] - r15.at[b, "p"]) / np.hypot(r15.at[a, "se_p"], r15.at[b, "se_p"]))))}
                                for a, b in combinations(r15.index, 2)]
    psa = {}
    for name, fname, pat, base in (("poverty_population", "poverty_pop_2018_2023.csv", "Poverty Incidence", RAW137 / "y2023" / "psa"),
                                   ("subsistence_families", "subsistence_families_2018_2023.csv", "Subsistence Incidence", RAW / "psa")):
        psa[name] = {}
        for yr in ("2018", "2021", "2023"):
            v, se = _series(fname, pat, yr, base), _series(fname, r"Standard Error", yr, base)
            vals = {k: (float(v.get(k, np.nan)), float(se.get(k, np.nan))) for k in CAL}
            q = vals["quezon"]
            psa[name][yr] = {"values": vals, "quezon_vs_others": {
                k: float(2 * norm.sf(abs((q[0] - x[0]) / np.hypot(q[1], x[1])))) for k, x in vals.items() if k != "quezon"}}
    out["psa_with_se"] = psa
    return out


def model_uncertainty(sel: str, X: pd.DataFrame, Z: pd.DataFrame, rng) -> dict:
    regs = X["region"].unique()
    P = []
    for _ in range(N_BOOT):
        s = pd.concat([X[X["region"] == r] for r in rng.choice(regs, len(regs))]).reset_index(drop=True)
        P.append(M.make(sel).fit(s).predict_proba(Z))
    P = np.asarray(P)
    names = Z["k"].tolist()
    first = pd.Series(names).iloc[P.argmax(axis=1)].value_counts(normalize=True).to_dict()
    pair = {f"{a}>{b}": float((P[:, i] > P[:, j]).mean()) for (i, a), (j, b) in combinations(enumerate(names), 2)}
    distinct = [a for i, a in enumerate(names)
                if all((P[:, i] > P[:, j]).mean() >= 0.95 or (P[:, i] > P[:, j]).mean() <= 0.05 for j in range(len(names)) if j != i)]
    return {"p_point": dict(zip(names, M.make(sel).fit(X).predict_proba(Z).round(4))),
            "p_interval90": {a: [float(np.percentile(P[:, i], 5)), float(np.percentile(P[:, i], 95))] for i, a in enumerate(names)},
            "p_rank_first": first, "pairwise_p_greater": pair, "distinct": distinct}


def run() -> dict:
    res = json.loads((OUT / "results.json").read_text())
    sel = res["selection"]["selected"]
    rng = np.random.default_rng(M.SEED)
    X = WH.data()
    out = {"selected": sel, "seal_date": SEAL_DATE.date().isoformat(), "measured": measured()}
    if sel in ("NAT", "REG", "PERS"):
        out["model"] = "selected model has no indicator inputs"
    else:
        cols = M.make(sel).cols
        Z = latest_features(CAL, cols)
        out["features_latest"] = Z.round(4).to_dict(orient="records")
        out["model"] = model_uncertainty(sel, X, Z, rng)
        allk = sorted(set(O.load()["key"].str.replace(" ", "")))
        Za = latest_features(allk, cols)
        fit = M.make(sel).fit(X)
        Za["p_elevated"] = fit.predict_proba(Za)
        seal = {"model": sel, "trained_rows": int(len(X)), "protocol": "E138-P1", "sealed_utc": datetime.now(timezone.utc).isoformat(),
                "feature_vintage": "PSA poverty statistics 2023 (families for subsistence), POPCEN 2024",
                "target": "P(province HFIAS/FIES moderate-or-severe significantly above national) at the next provincial round",
                "predictions": Za[["k", "p_elevated"] + cols].round(5).to_dict(orient="records")}
        body = json.dumps(seal, indent=1, sort_keys=True)
        (OUT / "sealed_prediction.json").write_text(body)
        out["sealed_prediction_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    (OUT / "calabarzon.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    {"acquire": acquire, "run": run}[sys.argv[1]]()
